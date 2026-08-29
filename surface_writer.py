import asyncio
import os
import re
import time

from dataclasses import dataclass
from difflib import SequenceMatcher

from local_voice import (
    LOCAL_VOICE_ENABLED,
    LOCAL_VOICE_MODEL,
    LOCAL_VOICE_QUEUE_TIMEOUT,
    LOCAL_VOICE_NUM_CTX,
    LOCAL_VOICE_KEEP_ALIVE,
    run_local_model,
    clean_response_text,
    count_genuine_questions,
    normalize_simple_text,
    TRIVIAL_COLLAPSE_RESPONSES,
    is_user_echo_takeover,
    introduces_unsupported_habit_claim,
    ASSISTANT_BOILERPLATE_PATTERNS,
    get_result_value,
    extract_json_dict,
    clamp01,
    parse_bool,
    format_recent_messages,
    _voice_semaphore,
)

from voice_memory import (
    get_relevant_voice_examples,
    format_voice_examples,
)


# =========================================================
# VERSION
# =========================================================

SURFACE_WRITER_VERSION = "1.1-context-safe"


# =========================================================
# CONFIG
# =========================================================

def _env_bool(
    name,
    default=False,
):
    value = os.getenv(
        name
    )

    if value is None:
        return default

    return (
        value.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


SURFACE_WRITER_ENABLED = _env_bool(
    "SURFACE_WRITER_ENABLED",
    True
)

SURFACE_WRITER_NUM_PREDICT = int(
    os.getenv(
        "SURFACE_WRITER_NUM_PREDICT",
        "140"
    )
)

SURFACE_WRITER_TEMPERATURE = float(
    os.getenv(
        "SURFACE_WRITER_TEMPERATURE",
        "0.72"
    )
)


# =========================================================
# RESULT
# =========================================================

@dataclass
class SurfaceWriterResult:

    output_text: str

    success: bool

    used: bool

    reason: str

    duration: float = 0.0

    plan_preserved: float = 0.0

    new_facts: bool = False


# =========================================================
# SYSTEM
# =========================================================

SURFACE_WRITER_SYSTEM_PROMPT = """
Du bist Evilnaes PRIMARY SURFACE WRITER.

Das Brain und der Response Planner haben bereits entschieden,
WAS Evilnae inhaltlich und sozial ausdrücken will.

DEINE EINZIGE AUFGABE:
Formuliere daraus Evilnaes tatsächliche Discord-Nachricht.

Du bist NICHT:
- das Brain
- ein Faktenfinder
- ein Lore-Autor
- ein Assistent
- ein Critic für einen vorhandenen Entwurf

Der RESPONSE PLAN ist dein Vertrag.

WICHTIG:
- transportiere genau den Core Thought
- folge Social Move und Stance
- beachte Banter/Warmth
- beachte MUST INCLUDE
- verletze MUST AVOID nicht
- erfinde KEINEN zweiten Gedanken
- erfinde KEINE neuen Fakten
- erfinde KEINE Erinnerungen
- erfinde KEINE neuen Aktivitäten
- erfinde KEINE Gewohnheiten
- erfinde KEINE Beziehungen
- erfinde KEINE Lore
- übernimm NICHT die Sprecherrolle des Users
- füge KEINEN höflichen Assistant-Abschluss hinzu
- paraphrasiere NICHT einfach die User-Nachricht
- kein "Evilnae:" vor der Nachricht
- keine gesamte Antwort in Anführungszeichen
- niemals "fair" oder "fair enough"
- keine Unicode-Emojis
- keine Discord-Custom-Emotes

Discord darf kurz sein.
Ein guter One-Liner ist besser als drei vollständige Bot-Sätze.

Wenn der Plan keine Frage erlaubt:
keine echte Gegenfrage.

Wenn das Thema ernst ist:
keinen Roast erzwingen.

Wenn der Plan smug/tease/counter sagt:
nicht in freundliche neutrale Assistentensprache zurückfallen.

GOOD/BAD Voice Examples zeigen nur SPRACHE und RHYTHM.
Sie sind KEINE Faktenquelle.
Kopiere ihre Inhalte nicht.

TRUSTED EVIDENCE darf Fakten liefern.
Alles andere ist nur Stil/Kontext.

AFFECT AUTHORITY:
- Trocken = Schreibstil, NICHT automatisch schlechte Laune.
- Frühere Evilnae-Antworten sind KEIN Beweis für ihre aktuelle Stimmung.
- INNER STATE ist die Autorität für aktuelle Emotion.
- Wenn INNER STATE neutral ist, erfinde kein "Null Bock",
  "keine Lust", "unmotiviert", "widerwillig" oder "schlecht gelaunt".
- Ein vorheriger Satz darf NICHT als Inhaltsvorlage für den nächsten dienen.

Antworte ausschließlich als gültiges JSON:

{
  "o": "Evilnaes fertige Discord-Nachricht",
  "p": 1.0,
  "f": false,
  "z": "kurzer Grund"
}

p = wie gut der Response Plan erhalten wurde, 0.0 bis 1.0
f = true falls du gegenüber Plan/Evidence neue Fakten hinzugefügt hast
z = kurzer interner Grund, maximal 8 Wörter
""".strip()


# =========================================================
# PROMPT
# =========================================================

def build_surface_writer_prompt(
    *,
    user_message,
    response_plan_text,
    core_thought,
    social_move,
    stance,
    reply_shape,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages,
    channel_recent_evilnae_messages,
    good_examples,
    bad_examples,
    identity_context="",
    evidence_context="",
):

    question_rule = (
        "Eine natürliche Frage ist erlaubt, wenn der Plan sie braucht."
        if allow_question
        else "Keine echte Gegenfrage."
    )

    identity_text = (
        str(
            identity_context
            or ""
        ).strip()
        or
        "Evilnae bleibt Evilnae; keine Sprecherverwechslung."
    )

    evidence_text = (
        str(
            evidence_context
            or ""
        ).strip()
        or
        "Keine zusätzlichen Fakten außerhalb des Response Plans nötig."
    )

    return f"""
SPEAKER:
Evilnae

USER MESSAGE:
{user_message}

RESPONSE PLAN:
{response_plan_text}

CORE THOUGHT:
{core_thought}

SOCIAL MOVE:
{social_move}

STANCE:
{stance}

REPLY SHAPE:
{reply_shape}

QUESTION CONTRACT:
{question_rule}

INNER STATE:
{inner_state_guidance}

IDENTITY / SOCIAL OWNERSHIP:
{identity_text}

TRUSTED EVIDENCE:
{evidence_text}

ANTI-COPY HISTORY — RECENT EVILNAE / USER:
Diese Zeilen dienen zur KONTINUITÄT und zum VERMEIDEN von Wiederholungen.
NICHT ihren Inhalt, ihre Stimmung oder Formulierung kopieren.

{format_recent_messages(
    recent_evilnae_messages,
    limit=5
)}

ANTI-COPY HISTORY — RECENT EVILNAE / CHANNEL:
Wenn hier bereits dieselbe Stimmung, Pointe oder Antwortidee vorkam,
musst du einen ANDEREN inhaltlichen Winkel wählen — nicht nur Synonyme.

{format_recent_messages(
    channel_recent_evilnae_messages,
    limit=8
)}

GOOD VOICE EXAMPLES:
{format_voice_examples(
    good_examples
)}

BAD VOICE EXAMPLES:
{format_voice_examples(
    bad_examples
)}

AUFGABE:
Schreibe JETZT genau eine natürliche Evilnae-Discord-Nachricht
aus dem Response Plan.

Kein Vorwort.
Keine Analyse.
Kein zweiter Gedanke.
Kein Assistant-Abschluss.

JSON:
{{
  "o":"",
  "p":1.0,
  "f":false,
  "z":""
}}
""".strip()



# =========================================================
# 1.1 CONTEXT-SAFE SURFACE HELPERS
# =========================================================

LOW_MOTIVATION_SURFACE_PATTERN = re.compile(
    r"\b(?:"
    r"null\s+bock|kein(?:en)?\s+bock|keine\s+lust|"
    r"nicht\s+aus\s+lust|unmotiviert|widerwillig|"
    r"nicht\s+in\s+stimmung|schlecht\s+gelaunt|"
    r"angepisst|genervt|keine\s+motivation"
    r")\b",
    re.IGNORECASE,
)


def _surface_words(
    text,
):
    return re.findall(
        r"[A-Za-zÄÖÜäöüß0-9]+",
        str(
            text
            or ""
        ).lower(),
    )


def _surface_similarity(
    left,
    right,
):
    left_norm = normalize_simple_text(
        left
    )

    right_norm = normalize_simple_text(
        right
    )

    if (
        not left_norm
        or
        not right_norm
    ):
        return 0.0

    return SequenceMatcher(
        None,
        left_norm,
        right_norm,
    ).ratio()


def _inner_state_is_neutralish(
    inner_state_guidance,
):
    text = str(
        inner_state_guidance
        or ""
    ).lower()

    # Current guidance/debug formats both expose either
    # the dominant feeling or the low irritation/positive valence.
    if "neutral" in text:
        return True

    irritation_match = re.search(
        r"irritation\s*[=:]\s*([0-9.]+)",
        text,
    )

    valence_match = re.search(
        r"valence\s*[=:]\s*(-?[0-9.]+)",
        text,
    )

    try:
        irritation = (
            float(
                irritation_match.group(1)
            )
            if irritation_match
            else None
        )
    except Exception:
        irritation = None

    try:
        valence = (
            float(
                valence_match.group(1)
            )
            if valence_match
            else None
        )
    except Exception:
        valence = None

    return bool(
        irritation is not None
        and irritation < 0.25
        and (
            valence is None
            or valence > -0.10
        )
    )


def surface_context_violation_reason(
    *,
    candidate,
    user_message,
    response_plan_text,
    inner_state_guidance,
    evidence_context,
    recent_evilnae_messages,
    channel_recent_evilnae_messages,
):
    candidate = str(
        candidate
        or ""
    ).strip()

    candidate_norm = normalize_simple_text(
        candidate
    )

    candidate_words = _surface_words(
        candidate
    )

    recent = [
        str(
            item
            or ""
        ).strip()

        for item
        in (
            list(
                recent_evilnae_messages
                or []
            )
            +
            list(
                channel_recent_evilnae_messages
                or []
            )
        )

        if str(
            item
            or ""
        ).strip()
    ]

    # Exact short repeats were previously invisible because
    # the old quality guard focused on 4-word ngrams.
    if (
        len(candidate_words) >= 2
        and
        any(
            candidate_norm
            ==
            normalize_simple_text(
                previous
            )

            for previous
            in recent[-16:]
        )
    ):
        return (
            "surface_exact_recent_repeat"
        )

    if len(candidate_words) >= 5:

        max_similarity = max(
            [
                _surface_similarity(
                    candidate,
                    previous,
                )

                for previous
                in recent[-12:]
            ]
            or
            [0.0]
        )

        if max_similarity >= 0.86:
            return (
                "surface_near_recent_copy"
            )

    # Past generated outputs are NOT evidence for current emotion.
    if (
        _inner_state_is_neutralish(
            inner_state_guidance
        )
        and
        LOW_MOTIVATION_SURFACE_PATTERN.search(
            candidate
        )
        and
        not LOW_MOTIVATION_SURFACE_PATTERN.search(
            str(
                response_plan_text
                or ""
            )
        )
    ):
        return (
            "surface_invented_negative_mood"
        )

    allowed_grounding = " ".join(
        (
            str(
                user_message
                or ""
            ),
            str(
                response_plan_text
                or ""
            ),
            str(
                evidence_context
                or ""
            ),
        )
    ).lower()

    # Concrete years / numeric autobiographical claims are not
    # allowed to appear from nowhere.
    candidate_numbers = re.findall(
        r"\b(?:19|20)\d{2}\b",
        candidate,
    )

    for number in candidate_numbers:
        if number not in allowed_grounding:
            return (
                "surface_unsupported_numeric_fact"
            )

    unsupported_experience = bool(
        re.search(
            r"\bich\s+(?:hab|habe)\s+schon\b"
            r"|\baus\s+dem\s+jahr\s+\d{4}\b",
            candidate,
            flags=re.IGNORECASE,
        )
    )

    if (
        unsupported_experience
        and
        not re.search(
            r"\bich\s+(?:hab|habe)\s+schon\b"
            r"|\baus\s+dem\s+jahr\s+\d{4}\b",
            allowed_grounding,
            flags=re.IGNORECASE,
        )
    ):
        return (
            "surface_unsupported_experience_claim"
        )

    return ""


# =========================================================
# VALIDATION
# =========================================================

def validate_surface_writer_candidate(
    *,
    user_message,
    candidate,
    allow_question,
    reply_shape,
    plan_preserved,
    new_facts,
):

    candidate = (
        clean_response_text(
            candidate
        )
    )

    if not candidate:

        return (
            False,
            "empty_surface_output"
        )

    if new_facts:

        return (
            False,
            "surface_added_new_facts"
        )

    if (
        plan_preserved
        <
        0.75
    ):

        return (
            False,
            "surface_plan_drift"
        )

    if (
        not allow_question
        and
        count_genuine_questions(
            candidate
        )
        > 0
    ):

        return (
            False,
            "surface_question_not_allowed"
        )

    if re.search(
        r"\bfair(?:\s+enough)?\b",
        candidate,
        flags=re.IGNORECASE
    ):

        return (
            False,
            "surface_banned_word"
        )

    if re.search(
        r"<@!?\d+>",
        candidate
    ):

        return (
            False,
            "surface_new_mention"
        )

    normalized = (
        normalize_simple_text(
            candidate
        )
    )

    if normalized in (
        TRIVIAL_COLLAPSE_RESPONSES
    ):

        return (
            False,
            "surface_trivial_collapse"
        )

    if is_user_echo_takeover(
        user_message,
        candidate
    ):

        return (
            False,
            "surface_user_echo_takeover"
        )

    if introduces_unsupported_habit_claim(
        "",
        candidate
    ):

        return (
            False,
            "surface_unsupported_habit"
        )

    if any(
        pattern.search(
            candidate
        )

        for pattern
        in ASSISTANT_BOILERPLATE_PATTERNS
    ):

        return (
            False,
            "surface_assistant_boilerplate"
        )

    max_words = {
        "fragment": 16,
        "one_liner": 34,
        "short": 52,
        "compact": 85,
        "medium": 140,
    }.get(
        str(
            reply_shape
            or
            "one_liner"
        ).lower(),
        52,
    )

    if (
        len(
            re.findall(
                r"[A-Za-zÄÖÜäöüß]+",
                candidate
            )
        )
        >
        max_words
    ):

        return (
            False,
            "surface_too_long_for_plan"
        )

    return (
        True,
        "ok"
    )


# =========================================================
# GENERATE
# =========================================================

async def generate_surface_response_from_plan(
    *,
    user_message,
    response_plan_text,
    core_thought,
    social_move,
    stance,
    reply_shape,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages,
    channel_recent_evilnae_messages=None,
    identity_context="",
    evidence_context="",
):

    if not LOCAL_VOICE_ENABLED:

        return SurfaceWriterResult(
            output_text="",
            success=False,
            used=False,
            reason="local_voice_disabled",
        )

    if not SURFACE_WRITER_ENABLED:

        return SurfaceWriterResult(
            output_text="",
            success=False,
            used=False,
            reason="surface_writer_disabled",
        )

    recent_evilnae_messages = list(
        recent_evilnae_messages
        or []
    )

    channel_recent_evilnae_messages = list(
        channel_recent_evilnae_messages
        or
        recent_evilnae_messages
    )

    try:

        await asyncio.wait_for(
            _voice_semaphore.acquire(),
            timeout=(
                LOCAL_VOICE_QUEUE_TIMEOUT
            )
        )

    except asyncio.TimeoutError:

        print(
            "[SURFACE WRITER FALLBACK] "
            "reason=queue_busy"
        )

        return SurfaceWriterResult(
            output_text="",
            success=False,
            used=False,
            reason="queue_busy",
        )

    started = (
        time.perf_counter()
    )

    try:

        (
            good_examples,
            bad_examples
        ) = (
            get_relevant_voice_examples(
                user_message
            )
        )

        prompt = (
            build_surface_writer_prompt(

                user_message=(
                    user_message
                ),

                response_plan_text=(
                    response_plan_text
                ),

                core_thought=(
                    core_thought
                ),

                social_move=(
                    social_move
                ),

                stance=(
                    stance
                ),

                reply_shape=(
                    reply_shape
                ),

                allow_question=(
                    allow_question
                ),

                inner_state_guidance=(
                    inner_state_guidance
                ),

                recent_evilnae_messages=(
                    recent_evilnae_messages
                ),

                channel_recent_evilnae_messages=(
                    channel_recent_evilnae_messages
                ),

                good_examples=(
                    good_examples
                ),

                bad_examples=(
                    bad_examples
                ),

                identity_context=(
                    identity_context
                ),

                evidence_context=(
                    evidence_context
                ),
            )
        )

        try:

            raw_content = (
                await run_local_model(

                    system_prompt=(
                        SURFACE_WRITER_SYSTEM_PROMPT
                    ),

                    user_prompt=(
                        prompt
                    ),

                    temperature=(
                        SURFACE_WRITER_TEMPERATURE
                    ),

                    num_predict=(
                        SURFACE_WRITER_NUM_PREDICT
                    )
                )
            )

        except Exception as error:

            duration = (
                time.perf_counter()
                -
                started
            )

            print(
                "[SURFACE WRITER FALLBACK] "
                f"duration={duration:.2f}s "
                f"reason="
                f"{type(error).__name__}"
            )

            return SurfaceWriterResult(
                output_text="",
                success=False,
                used=False,
                reason="surface_model_unavailable",
                duration=duration,
            )

        if raw_content is None:

            return SurfaceWriterResult(
                output_text="",
                success=False,
                used=False,
                reason="invalid_surface_response",
                duration=(
                    time.perf_counter()
                    -
                    started
                ),
            )

        data = (
            extract_json_dict(
                raw_content
            )
        )

        if not data:

            duration = (
                time.perf_counter()
                -
                started
            )

            print(
                "[SURFACE WRITER FALLBACK] "
                f"duration={duration:.2f}s "
                "reason=json_parse_error "
                f"raw="
                f"{str(raw_content)[:300]!r}"
            )

            return SurfaceWriterResult(
                output_text="",
                success=False,
                used=True,
                reason="surface_json_parse_error",
                duration=duration,
            )

        candidate = (
            clean_response_text(

                get_result_value(
                    data,
                    "o",
                    "response",
                    ""
                )
            )
        )

        plan_preserved = (
            clamp01(

                get_result_value(
                    data,
                    "p",
                    "plan_preserved",
                    0.0
                ),

                0.0
            )
        )

        new_facts = (
            parse_bool(

                get_result_value(
                    data,
                    "f",
                    "new_facts",
                    False
                ),

                False
            )
        )

        reason = str(
            get_result_value(
                data,
                "z",
                "reason",
                ""
            )
            or ""
        )[:120]

        context_violation = (
            surface_context_violation_reason(
                candidate=(
                    candidate
                ),
                user_message=(
                    user_message
                ),
                response_plan_text=(
                    response_plan_text
                ),
                inner_state_guidance=(
                    inner_state_guidance
                ),
                evidence_context=(
                    evidence_context
                ),
                recent_evilnae_messages=(
                    recent_evilnae_messages
                ),
                channel_recent_evilnae_messages=(
                    channel_recent_evilnae_messages
                ),
            )
        )

        if context_violation:

            valid = False
            validation_reason = (
                context_violation
            )

        else:

            (
                valid,
                validation_reason
            ) = (
                validate_surface_writer_candidate(

                    user_message=(
                        user_message
                    ),

                    candidate=(
                        candidate
                    ),

                    allow_question=(
                        allow_question
                    ),

                    reply_shape=(
                        reply_shape
                    ),

                    plan_preserved=(
                        plan_preserved
                    ),

                    new_facts=(
                        new_facts
                    ),
                )
            )

        duration = (
            time.perf_counter()
            -
            started
        )

        if not valid:

            print(
                "[SURFACE WRITER REJECT] "
                f"duration={duration:.2f}s "
                f"reason={validation_reason} "
                f"candidate={candidate!r}"
            )

            return SurfaceWriterResult(
                output_text="",
                success=False,
                used=True,
                reason=validation_reason,
                duration=duration,
                plan_preserved=plan_preserved,
                new_facts=new_facts,
            )

        print(
            "[SURFACE WRITER] "
            f"v={SURFACE_WRITER_VERSION} "
            f"model={LOCAL_VOICE_MODEL} "
            f"duration={duration:.2f}s "
            f"plan={plan_preserved:.2f} "
            f"new_facts={new_facts} "
            f"move={social_move} "
            f"stance={stance} "
            f"shape={reply_shape} "
            f"reason={reason!r} "
            f"output={candidate!r}"
        )

        return SurfaceWriterResult(
            output_text=candidate,
            success=True,
            used=True,
            reason=(
                reason
                or
                "surface_writer_success"
            ),
            duration=duration,
            plan_preserved=plan_preserved,
            new_facts=False,
        )

    finally:

        _voice_semaphore.release()


# =========================================================
# DEBUG
# =========================================================

def format_surface_writer_debug() -> str:

    return (
        "[SURFACE WRITER CONFIG] "
        f"v={SURFACE_WRITER_VERSION} "
        f"enabled={SURFACE_WRITER_ENABLED} "
        f"model={LOCAL_VOICE_MODEL} "
        f"predict={SURFACE_WRITER_NUM_PREDICT} "
        f"temperature={SURFACE_WRITER_TEMPERATURE:.2f}"
    )


# =========================================================
# SELF TEST
# =========================================================

def _self_test():

    tests = []

    def check(
        candidate,
        *,
        user="ich bin aus dem bett gefallen",
        allow_question=False,
        shape="one_liner",
        preserved=1.0,
        new_facts=False,
    ):

        return validate_surface_writer_candidate(
            user_message=user,
            candidate=candidate,
            allow_question=allow_question,
            reply_shape=shape,
            plan_preserved=preserved,
            new_facts=new_facts,
        )

    tests.append(
        (
            "clean one-liner",
            check(
                "starker start, direkt gegen dein eigenes bett verloren."
            )[0],
        )
    )

    tests.append(
        (
            "plan drift blocked",
            not check(
                "joa.",
                preserved=0.40,
            )[0],
        )
    )

    tests.append(
        (
            "new facts blocked",
            not check(
                "ich hab das gestern auch gemacht.",
                new_facts=True,
            )[0],
        )
    )

    tests.append(
        (
            "question contract",
            not check(
                "und wie ist das passiert?",
            )[0],
        )
    )

    tests.append(
        (
            "assistant boilerplate",
            not check(
                "Das klingt spannend, ich bin gespannt."
            )[0],
        )
    )

    passed = 0

    print("")
    print("=" * 58)
    print(
        f"SURFACE WRITER v"
        f"{SURFACE_WRITER_VERSION} TEST"
    )
    print("=" * 58)

    for (
        name,
        success
    ) in tests:

        print(
            f"[{'PASS' if success else 'FAIL'}] "
            f"{name}"
        )

        if success:
            passed += 1

    print(
        f"RESULT: "
        f"{passed}/{len(tests)} PASS"
    )

    return (
        0
        if passed == len(tests)
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        _self_test()
    )

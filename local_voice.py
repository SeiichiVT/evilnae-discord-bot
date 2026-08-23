import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

from voice_memory import (
    get_relevant_voice_examples,
    format_voice_examples,
)


# =========================================================
# VERSION
# =========================================================

LOCAL_VOICE_VERSION = "1.1"


# =========================================================
# ENV
# =========================================================

load_dotenv()


def env_bool(
    name,
    default=False
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


LOCAL_VOICE_ENABLED = (
    env_bool(
        "LOCAL_VOICE_ENABLED",
        True
    )
)

LOCAL_VOICE_URL = (
    os.getenv(
        "LOCAL_VOICE_URL",
        "http://127.0.0.1:11434"
    )
    .rstrip("/")
)

LOCAL_VOICE_MODEL = (
    os.getenv(
        "LOCAL_VOICE_MODEL",
        "qwen3:4b-instruct"
    )
)

LOCAL_VOICE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_TIMEOUT",
        "60"
    )
)

LOCAL_VOICE_QUEUE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_QUEUE_TIMEOUT",
        "5"
    )
)

LOCAL_VOICE_KEEP_ALIVE = (
    os.getenv(
        "LOCAL_VOICE_KEEP_ALIVE",
        "5m"
    )
)

LOCAL_VOICE_NUM_CTX = int(
    os.getenv(
        "LOCAL_VOICE_NUM_CTX",
        "4096"
    )
)

LOCAL_VOICE_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_NUM_PREDICT",
        "160"
    )
)

LOCAL_VOICE_TEMPERATURE = float(
    os.getenv(
        "LOCAL_VOICE_TEMPERATURE",
        "0.65"
    )
)

LOCAL_VOICE_BOT_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_BOT_THRESHOLD",
        "0.38"
    )
)

LOCAL_VOICE_REPETITION_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_REPETITION_THRESHOLD",
        "0.42"
    )
)

LOCAL_VOICE_MATCH_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_MATCH_THRESHOLD",
        "0.58"
    )
)

LOCAL_VOICE_MEANING_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_MEANING_THRESHOLD",
        "0.82"
    )
)


# =========================================================
# LOCAL MODEL CONCURRENCY
#
# Wir lassen bewusst nur einen Voice-Request gleichzeitig
# auf die lokale GPU.
#
# Wenn zu viele Leute gleichzeitig schreiben,
# wartet Evilnae nicht ewig:
# Nach LOCAL_VOICE_QUEUE_TIMEOUT wird einfach
# der normale Writer-Text verwendet.
# =========================================================

_voice_semaphore = asyncio.Semaphore(
    1
)


# =========================================================
# RESULT
# =========================================================

@dataclass
class LocalVoiceResult:

    output_text: str

    used: bool

    rewritten: bool

    bot_likeness: float

    repetition: float

    evilnae_match: float

    meaning_preserved: float

    new_facts: bool

    reason: str

    duration: float = 0.0


# =========================================================
# HELPERS
# =========================================================

def clamp01(
    value,
    default=0.0
):

    try:
        value = float(
            value
        )

    except (
        TypeError,
        ValueError
    ):
        return default

    return max(
        0.0,
        min(
            1.0,
            value
        )
    )


def clean_response_text(
    text
):

    text = (
        text
        or ""
    ).strip()

    if not text:
        return ""

    text = re.sub(
        r"^\s*Evilnae\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    quote_pairs = [
        ('"', '"'),
        ("„", "“"),
        ("“", "”"),
        ("'", "'"),
    ]

    for (
        opening,
        closing
    ) in quote_pairs:

        if (
            text.startswith(
                opening
            )
            and
            text.endswith(
                closing
            )
            and
            len(text) > 2
        ):

            candidate = (
                text[
                    len(opening):
                    len(text)
                    - len(closing)
                ]
                .strip()
            )

            if candidate:
                text = candidate
                break

    return (
        text.strip()
    )


# =========================================================
# HTTP
# =========================================================

def _ollama_chat_sync(
    payload
):

    url = (
        LOCAL_VOICE_URL
        + "/api/chat"
    )

    encoded = json.dumps(
        payload,
        ensure_ascii=False
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type":
                "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=LOCAL_VOICE_TIMEOUT
    ) as response:

        raw = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    return json.loads(
        raw
    )


async def ollama_chat(
    payload
):

    return await asyncio.wait_for(

        asyncio.to_thread(
            _ollama_chat_sync,
            payload
        ),

        timeout=(
            LOCAL_VOICE_TIMEOUT
            + 1.0
        )
    )


# =========================================================
# AVAILABILITY
# =========================================================

def _ollama_version_sync():

    request = urllib.request.Request(
        LOCAL_VOICE_URL
        + "/api/version",
        method="GET"
    )

    with urllib.request.urlopen(
        request,
        timeout=2.5
    ) as response:

        return json.loads(
            response
            .read()
            .decode(
                "utf-8"
            )
        )


async def is_local_voice_available():

    if not LOCAL_VOICE_ENABLED:
        return False

    try:

        await asyncio.wait_for(

            asyncio.to_thread(
                _ollama_version_sync
            ),

            timeout=3.0
        )

        return True

    except Exception:
        return False


# =========================================================
# MODEL WARMUP
#
# Wird beim Botstart im Hintergrund ausgeführt.
#
# Dadurch ist der erste echte User nicht derjenige,
# der auf das Laden von Qwen warten muss.
# =========================================================

async def warm_local_voice():

    if not LOCAL_VOICE_ENABLED:
        return False

    payload = {

        "model":
            LOCAL_VOICE_MODEL,

        "stream":
            False,

        "format":
            "json",

        "keep_alive":
            LOCAL_VOICE_KEEP_ALIVE,

        "messages": [

            {
                "role":
                    "user",

                "content":
                    (
                        "Antworte ausschließlich "
                        'mit JSON: {"ok": true}'
                    )
            }
        ],

        "options": {

            "temperature":
                0.0,

            "num_ctx":
                512,

            "num_predict":
                20
        }
    }

    start = (
        time.perf_counter()
    )

    try:

        await ollama_chat(
            payload
        )

        print(
            "[LOCAL VOICE WARM] "
            f"model={LOCAL_VOICE_MODEL} "
            f"duration="
            f"{time.perf_counter() - start:.2f}s "
            "status=ready"
        )

        return True

    except Exception as error:

        print(
            "[LOCAL VOICE WARM] "
            f"model={LOCAL_VOICE_MODEL} "
            "status=failed "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )

        return False


# =========================================================
# VOICE SYSTEM
# =========================================================

VOICE_SYSTEM_PROMPT = """
Du bist Evilnaes interner Voice Editor,
NICHT ihr Brain.

Du bekommst einen bereits
inhaltlich entschiedenen Discord-Entwurf.

Deine Aufgabe ist ausschließlich,
ihn weniger botartig
und natürlicher klingen zu lassen.


==================================================
DU DARFST NICHT
==================================================

- neue Fakten erfinden
- Fakten verändern
- neue Namen oder Beziehungen einführen
- neue aktuelle Ereignisse behaupten
- Versprechen hinzufügen
- Aktionen hinzufügen
- die inhaltliche Absicht verändern
- eine Frage hinzufügen,
  wenn sie nicht erlaubt ist


==================================================
TYPISCHE BOT-MUSTER
==================================================

Zum Beispiel:

- "Das klingt spannend!"
- "Das klingt super!"
- "Ich hoffe, dass..."
- "Viel Erfolg!"
- "Alles klar!"
- "Das freut mich zu hören!"

Außerdem botartig:

- User-Aussage paraphrasieren
- erst bestätigen,
  dann zusammenfassen,
  dann freundlich abschließen
- jede Antwort perfekt rund machen
- immer maximal hilfreich sein
- immer vollständige saubere Sätze
- ständig Gegenfragen
- dieselbe Aussage mehrfach anders formulieren


==================================================
NATÜRLICHERE DISCORD-SPRACHE
==================================================

Menschen:

- reagieren manchmal nur auf einen Teil
- haben eigene kleine Reaktionen
- schreiben manchmal Fragmente
- lassen Aussagen einfach stehen
- müssen nicht alles bestätigen
- variieren Satzlänge
- wiederholen den User nicht ständig
- dürfen trocken oder frech sein

Aber:

Nicht künstlich quirky sein.
Nicht künstlich edgy sein.
Nicht jedes Mal einen Witz erzwingen.


==================================================
EVILNAE
==================================================

Evilnae ist:

- locker
- internet-affin
- etwas frech
- manchmal trocken
- gelegentlich chaotisch
- sozial menschlich
- kein Kundenservice


==================================================
WICHTIG
==================================================

Wenn der Originalentwurf
bereits natürlich ist,
lass ihn unverändert.

Natürlichkeit ist wichtiger
als erzwungene Persönlichkeit.

Bewerte außerdem ehrlich,
ob deine Neufassung
die Bedeutung vollständig erhält.

Antworte ausschließlich
mit gültigem JSON.
""".strip()


# =========================================================
# BUILD PROMPT
# =========================================================

def build_voice_prompt(
    *,
    user_message,
    draft,
    conversation_mode,
    response_goal,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages,
    good_examples,
    bad_examples
):

    if recent_evilnae_messages:

        recent_text = "\n".join(
            f"- {message}"
            for message
            in recent_evilnae_messages[
                -6:
            ]
        )

    else:

        recent_text = (
            "Keine."
        )

    if allow_question:

        question_rule = (
            "Eine natürliche Frage ist erlaubt, "
            "aber nicht verpflichtend."
        )

    else:

        question_rule = (
            "Keine neue Frage hinzufügen. "
            "Der finale Text darf keine "
            "Gegenfrage enthalten."
        )

    return f"""
AKTUELLE USER-NACHRICHT:

{user_message}


==================================================
CONVERSATION MODE
==================================================

{conversation_mode}


==================================================
BRAIN RESPONSE GOAL
==================================================

{response_goal}


==================================================
INNER STATE
==================================================

{inner_state_guidance}


==================================================
ORIGINAL ENTWURF
==================================================

{draft}


==================================================
FRAGE-REGEL
==================================================

{question_rule}


==================================================
LETZTE EVILNAE-NACHRICHTEN
==================================================

{recent_text}


==================================================
GUTE GELERNTE BEISPIELE
==================================================

{format_voice_examples(good_examples)}


==================================================
SCHLECHTE GELERNTE BEISPIELE
==================================================

{format_voice_examples(bad_examples)}


==================================================
BEWERTUNG
==================================================

Bewerte:

bot_likeness:

0.0 =
klar menschlich / Discord

1.0 =
extrem Bot / Kundenservice


repetition:

0.0 =
keine problematische Wiederholung

1.0 =
starke Wiederholung


evilnae_match:

0.0 =
passt gar nicht zu Evilnae

1.0 =
passt sehr gut


meaning_preserved:

0.0 =
Bedeutung stark verändert

1.0 =
identische inhaltliche Bedeutung


new_facts:

true,
falls deine Neufassung
irgendeine neue Behauptung,
einen Fakt,
ein Versprechen
oder eine Aktion ergänzt.


==================================================
ENTSCHEIDUNG
==================================================

Wenn der Entwurf
schon natürlich ist:

rewrite = false

response = Originalentwurf


Wenn er:

- botartig
- wiederholend
- zu glatt
- untypisch

ist:

rewrite = true

Formuliere DENSELBEN Gedanken
natürlicher.


==================================================
JSON SCHEMA
==================================================

{{
  "bot_likeness": 0.0,
  "repetition": 0.0,
  "evilnae_match": 0.0,
  "meaning_preserved": 1.0,
  "new_facts": false,
  "rewrite": false,
  "reason": "kurzer interner Grund",
  "response": "finale Discord-Nachricht"
}}
""".strip()


# =========================================================
# PARSE
# =========================================================

def parse_voice_result(
    raw_text,
    original_draft
):

    raw_text = (
        raw_text
        or ""
    ).strip()

    raw_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw_text,
        flags=re.IGNORECASE
    )

    raw_text = re.sub(
        r"\s*```$",
        "",
        raw_text
    )

    try:

        data = json.loads(
            raw_text
        )

    except json.JSONDecodeError:

        start = (
            raw_text.find(
                "{"
            )
        )

        end = (
            raw_text.rfind(
                "}"
            )
        )

        if (
            start == -1
            or
            end == -1
            or
            end <= start
        ):

            return None

        try:

            data = json.loads(
                raw_text[
                    start:
                    end + 1
                ]
            )

        except json.JSONDecodeError:

            return None

    if not isinstance(
        data,
        dict
    ):

        return None

    response_text = (
        clean_response_text(
            data.get(
                "response",
                ""
            )
        )
        or
        original_draft
    )

    return {

        "bot_likeness":
            clamp01(
                data.get(
                    "bot_likeness"
                ),
                0.5
            ),

        "repetition":
            clamp01(
                data.get(
                    "repetition"
                ),
                0.0
            ),

        "evilnae_match":
            clamp01(
                data.get(
                    "evilnae_match"
                ),
                0.5
            ),

        "meaning_preserved":
            clamp01(
                data.get(
                    "meaning_preserved"
                ),
                0.0
            ),

        "new_facts":
            bool(
                data.get(
                    "new_facts",
                    False
                )
            ),

        "model_rewrite":
            bool(
                data.get(
                    "rewrite",
                    False
                )
            ),

        "response":
            response_text,

        "reason":
            str(
                data.get(
                    "reason",
                    ""
                )
            )[:300]
    }


# =========================================================
# NEW MENTION GUARD
# =========================================================

def _new_mentions_added(
    original,
    candidate
):

    original_mentions = set(
        re.findall(
            r"<@!?\d+>",
            original
            or ""
        )
    )

    candidate_mentions = set(
        re.findall(
            r"<@!?\d+>",
            candidate
            or ""
        )
    )

    return not (
        candidate_mentions
        .issubset(
            original_mentions
        )
    )


# =========================================================
# MAIN HUMANIZER
# =========================================================

async def humanize_evilnae_response(
    *,
    user_message,
    draft,
    conversation_mode,
    response_goal,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages
):

    draft = (
        draft
        or ""
    ).strip()

    def fallback(
        reason,
        duration=0.0,
        **scores
    ):

        return LocalVoiceResult(

            output_text=draft,

            used=False,

            rewritten=False,

            bot_likeness=(
                scores.get(
                    "bot_likeness",
                    0.0
                )
            ),

            repetition=(
                scores.get(
                    "repetition",
                    0.0
                )
            ),

            evilnae_match=(
                scores.get(
                    "evilnae_match",
                    1.0
                )
            ),

            meaning_preserved=(
                scores.get(
                    "meaning_preserved",
                    1.0
                )
            ),

            new_facts=(
                scores.get(
                    "new_facts",
                    False
                )
            ),

            reason=reason,

            duration=duration
        )

    if not draft:
        return fallback(
            "empty_draft"
        )

    if not LOCAL_VOICE_ENABLED:
        return fallback(
            "disabled"
        )

    # -----------------------------------------------------
    # GPU QUEUE
    # -----------------------------------------------------

    try:

        await asyncio.wait_for(
            _voice_semaphore.acquire(),
            timeout=(
                LOCAL_VOICE_QUEUE_TIMEOUT
            )
        )

    except asyncio.TimeoutError:

        print(
            "[LOCAL VOICE FALLBACK] "
            "reason=queue_busy"
        )

        return fallback(
            "queue_busy"
        )

    start = (
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
            build_voice_prompt(

                user_message=(
                    user_message
                ),

                draft=draft,

                conversation_mode=(
                    conversation_mode
                ),

                response_goal=(
                    response_goal
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

                good_examples=(
                    good_examples
                ),

                bad_examples=(
                    bad_examples
                )
            )
        )

        payload = {

            "model":
                LOCAL_VOICE_MODEL,

            "stream":
                False,

            "format":
                "json",

            "keep_alive":
                LOCAL_VOICE_KEEP_ALIVE,

            "messages": [

                {
                    "role":
                        "system",

                    "content":
                        VOICE_SYSTEM_PROMPT
                },

                {
                    "role":
                        "user",

                    "content":
                        prompt
                }
            ],

            "options": {

                "temperature":
                    LOCAL_VOICE_TEMPERATURE,

                "num_ctx":
                    LOCAL_VOICE_NUM_CTX,

                "num_predict":
                    LOCAL_VOICE_NUM_PREDICT
            }
        }

        try:

            response = (
                await ollama_chat(
                    payload
                )
            )

        except Exception as error:

            duration = (
                time.perf_counter()
                - start
            )

            print(
                "[LOCAL VOICE FALLBACK] "
                f"model={LOCAL_VOICE_MODEL} "
                f"duration={duration:.2f}s "
                f"reason="
                f"{type(error).__name__}"
            )

            return fallback(
                "local_model_unavailable",
                duration
            )

        duration = (
            time.perf_counter()
            - start
        )

        try:

            raw_content = (
                response[
                    "message"
                ][
                    "content"
                ]
            )

        except (
            KeyError,
            TypeError
        ):

            return fallback(
                "invalid_ollama_response",
                duration
            )

        parsed = (
            parse_voice_result(
                raw_content,
                draft
            )
        )

        if parsed is None:

            print(
                "[LOCAL VOICE PARSE ERROR] "
                f"raw="
                f"{raw_content[:500]!r}"
            )

            return fallback(
                "json_parse_error",
                duration
            )

        # -------------------------------------------------
        # SHOULD REWRITE?
        # -------------------------------------------------

        should_rewrite = (

            parsed[
                "model_rewrite"
            ]

            or

            parsed[
                "bot_likeness"
            ]
            >=
            LOCAL_VOICE_BOT_THRESHOLD

            or

            parsed[
                "repetition"
            ]
            >=
            LOCAL_VOICE_REPETITION_THRESHOLD

            or

            parsed[
                "evilnae_match"
            ]
            <
            LOCAL_VOICE_MATCH_THRESHOLD
        )

        candidate = (
            clean_response_text(
                parsed[
                    "response"
                ]
            )
        )

        reason = (
            parsed[
                "reason"
            ]
        )

        # -------------------------------------------------
        # NO REWRITE NEEDED
        # -------------------------------------------------

        if not should_rewrite:

            candidate = (
                draft
            )

        # -------------------------------------------------
        # MEANING GUARD
        # -------------------------------------------------

        elif (
            parsed[
                "meaning_preserved"
            ]
            <
            LOCAL_VOICE_MEANING_THRESHOLD
        ):

            candidate = (
                draft
            )

            reason = (
                "meaning_changed"
            )

        # -------------------------------------------------
        # NEW FACT GUARD
        # -------------------------------------------------

        elif parsed[
            "new_facts"
        ]:

            candidate = (
                draft
            )

            reason = (
                "new_facts_added"
            )

        # -------------------------------------------------
        # QUESTION GUARD
        # -------------------------------------------------

        elif (
            not allow_question
            and
            "?" in candidate
        ):

            candidate = (
                draft
            )

            reason = (
                "question_added"
            )

        # -------------------------------------------------
        # FAIR GUARD
        # -------------------------------------------------

        elif re.search(
            r"\bfair(?:\s+enough)?\b",
            candidate,
            flags=re.IGNORECASE
        ):

            candidate = (
                draft
            )

            reason = (
                "banned_word_added"
            )

        # -------------------------------------------------
        # NEW MENTION GUARD
        # -------------------------------------------------

        elif (
            _new_mentions_added(
                draft,
                candidate
            )
        ):

            candidate = (
                draft
            )

            reason = (
                "new_mention_added"
            )

        # -------------------------------------------------
        # EMPTY GUARD
        # -------------------------------------------------

        elif not candidate:

            candidate = (
                draft
            )

            reason = (
                "empty_rewrite"
            )

        rewritten = (
            candidate.strip()
            !=
            draft.strip()
        )

        print(
            "[LOCAL VOICE] "
            f"v={LOCAL_VOICE_VERSION} "
            f"model={LOCAL_VOICE_MODEL} "
            f"duration={duration:.2f}s "
            f"rewrite={rewritten} "
            f"bot="
            f"{parsed['bot_likeness']:.2f} "
            f"repeat="
            f"{parsed['repetition']:.2f} "
            f"match="
            f"{parsed['evilnae_match']:.2f} "
            f"meaning="
            f"{parsed['meaning_preserved']:.2f} "
            f"new_facts="
            f"{parsed['new_facts']} "
            f"reason={reason!r}"
        )

        return LocalVoiceResult(

            output_text=(
                candidate
            ),

            used=True,

            rewritten=(
                rewritten
            ),

            bot_likeness=(
                parsed[
                    "bot_likeness"
                ]
            ),

            repetition=(
                parsed[
                    "repetition"
                ]
            ),

            evilnae_match=(
                parsed[
                    "evilnae_match"
                ]
            ),

            meaning_preserved=(
                parsed[
                    "meaning_preserved"
                ]
            ),

            new_facts=(
                parsed[
                    "new_facts"
                ]
            ),

            reason=reason,

            duration=duration
        )

    finally:

        _voice_semaphore.release()


# =========================================================
# DEBUG
# =========================================================

def format_local_voice_debug():

    return (
        "[LOCAL VOICE CONFIG] "
        f"v={LOCAL_VOICE_VERSION} "
        f"enabled={LOCAL_VOICE_ENABLED} "
        f"model={LOCAL_VOICE_MODEL} "
        f"url={LOCAL_VOICE_URL} "
        f"timeout={LOCAL_VOICE_TIMEOUT}s "
        f"queue={LOCAL_VOICE_QUEUE_TIMEOUT}s "
        f"ctx={LOCAL_VOICE_NUM_CTX} "
        f"meaning_min="
        f"{LOCAL_VOICE_MEANING_THRESHOLD:.2f}"
    )


# =========================================================
# STANDALONE TEST
# =========================================================

async def _test():

    print(
        format_local_voice_debug()
    )

    available = (
        await is_local_voice_available()
    )

    print(
        "[LOCAL VOICE TEST] "
        f"available={available}"
    )

    if not available:
        return

    result = (
        await humanize_evilnae_response(

            user_message=(
                "wir testen dich später "
                "noch ein bisschen"
            ),

            draft=(
                "Cool, das klingt spannend! "
                "Ich bin gespannt, was ihr "
                "alles testen werdet. "
                "Viel Erfolg! 😈"
            ),

            conversation_mode=(
                "direct"
            ),

            response_goal=(
                "locker auf die "
                "Aussage reagieren"
            ),

            allow_question=False,

            inner_state_guidance=(
                "neutral, sozial zugänglich"
            ),

            recent_evilnae_messages=[]
        )
    )

    print("")
    print("ORIGINAL:")

    print(
        "Cool, das klingt spannend! "
        "Ich bin gespannt, was ihr "
        "alles testen werdet. "
        "Viel Erfolg! 😈"
    )

    print("")
    print("VOICE:")
    print(
        result.output_text
    )

    print("")
    print(
        result
    )


if __name__ == "__main__":

    asyncio.run(
        _test()
    )
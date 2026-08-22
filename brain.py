import json
from dataclasses import dataclass, field
from typing import Optional

from conversation_state import (
    ConversationState,
    BrainState,
    format_state_for_brain,
)


# =========================================================
# VERSION
# =========================================================

BRAIN_VERSION = "2.1-knowledge"


# =========================================================
# BRAIN DECISION
# =========================================================

@dataclass
class BrainDecision:

    intent: str = "casual_chat"

    action: str = "reply"

    response_length: str = "short"

    tone: str = "relaxed"

    ask_question: bool = False

    acknowledge_correction: bool = False

    topic_exhausted: bool = False

    repetition_risk: bool = False

    # -----------------------------------------------------
    # KNOWLEDGE
    # -----------------------------------------------------

    knowledge_available: bool = False

    knowledge_confidence: str = "unknown"

    knowledge_source: str = "unknown"

    # -----------------------------------------------------
    # SOCIAL ACTION
    # -----------------------------------------------------

    should_ask_person: bool = False

    target_user_id: Optional[str] = None

    target_user_name: Optional[str] = None

    # -----------------------------------------------------
    # WRITER GUIDANCE
    # -----------------------------------------------------

    avoid_phrases: list[str] = field(
        default_factory=list
    )

    relevant_memories: list[str] = field(
        default_factory=list
    )

    response_goal: str = ""

    reasoning_summary: str = ""


# =========================================================
# ALLOWED VALUES
# =========================================================

ALLOWED_ACTIONS = {

    "reply",
    "short_reply",
    "acknowledge",
    "tease",
    "correct",
    "react",
    "change_topic",
    "ask_person",
}


ALLOWED_LENGTHS = {

    "tiny",
    "short",
    "medium",
    "long",
}


ALLOWED_TONES = {

    "relaxed",
    "dry",
    "amused",
    "smug",
    "soft",
    "annoyed",
    "serious",
    "confused",
    "playful",
    "gen_z",
}


ALLOWED_KNOWLEDGE_CONFIDENCE = {

    "high",
    "medium",
    "low",
    "unknown",
}


ALLOWED_KNOWLEDGE_SOURCES = {

    "current_context",
    "recent_context",
    "memory",
    "cohabitation_inference",
    "unknown",
    "not_applicable",
}


# =========================================================
# DEFAULT DECISION
# =========================================================

def default_brain_decision(
    state: ConversationState
) -> BrainDecision:

    return BrainDecision(

        intent="casual_chat",

        action="reply",

        response_length="short",

        tone="relaxed",

        ask_question=False,

        acknowledge_correction=False,

        topic_exhausted=False,

        repetition_risk=False,

        knowledge_available=False,

        knowledge_confidence="unknown",

        knowledge_source="not_applicable",

        should_ask_person=False,

        target_user_id=None,

        target_user_name=None,

        avoid_phrases=[],

        relevant_memories=[],

        response_goal=(
            "Natürlich und direkt "
            "auf die aktuelle Situation reagieren."
        ),

        reasoning_summary=(
            "Fallback-Entscheidung."
        )
    )


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json_object(
    text: str
) -> Optional[dict]:

    if not text:

        return None

    text = (
        text.strip()
    )

    # -----------------------------------------------------
    # CODE FENCE
    # -----------------------------------------------------

    if text.startswith(
        "```"
    ):

        lines = (
            text.splitlines()
        )

        if lines:

            lines = (
                lines[1:]
            )

        if (
            lines
            and
            lines[-1]
            .strip()
            .startswith(
                "```"
            )
        ):

            lines = (
                lines[:-1]
            )

        text = (
            "\n".join(
                lines
            )
            .strip()
        )

    # -----------------------------------------------------
    # DIRECT JSON
    # -----------------------------------------------------

    try:

        result = (
            json.loads(
                text
            )
        )

        if isinstance(
            result,
            dict
        ):

            return result

    except json.JSONDecodeError:

        pass

    # -----------------------------------------------------
    # EXTRACT OBJECT
    # -----------------------------------------------------

    start = (
        text.find(
            "{"
        )
    )

    end = (
        text.rfind(
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

    candidate = (
        text[
            start:end + 1
        ]
    )

    try:

        result = (
            json.loads(
                candidate
            )
        )

        if isinstance(
            result,
            dict
        ):

            return result

    except json.JSONDecodeError:

        return None

    return None


# =========================================================
# SAFE HELPERS
# =========================================================

def safe_bool(
    value,
    default=False
):

    if isinstance(
        value,
        bool
    ):

        return value

    if isinstance(
        value,
        str
    ):

        lowered = (
            value
            .strip()
            .lower()
        )

        if lowered in {
            "true",
            "yes",
            "ja",
            "1"
        }:

            return True

        if lowered in {
            "false",
            "no",
            "nein",
            "0"
        }:

            return False

    return default


def safe_list(
    value,
    limit=8
):

    if not isinstance(
        value,
        list
    ):

        return []

    result = []

    for item in value:

        if item is None:

            continue

        text = (
            str(
                item
            )
            .strip()
        )

        if not text:

            continue

        result.append(
            text[:300]
        )

        if (
            len(result)
            >= limit
        ):

            break

    return result


def safe_enum(
    value,
    allowed,
    default
):

    if not isinstance(
        value,
        str
    ):

        return default

    value = (
        value
        .strip()
        .lower()
    )

    if value in allowed:

        return value

    return default


def safe_optional_text(
    value
):

    if value is None:

        return None

    value = (
        str(
            value
        )
        .strip()
    )

    if not value:

        return None

    return value[:200]


# =========================================================
# REPETITION SIGNALS
# =========================================================

def detect_basic_repetition_signals(
    state: ConversationState
) -> list[str]:

    recent = (
        state.history
        .recent_evilnae_messages
    )

    if not recent:

        return []

    signals = []

    lowered_messages = [

        message.lower()

        for message
        in recent
    ]

    # -----------------------------------------------------
    # HAHA
    # -----------------------------------------------------

    haha_count = sum(

        1

        for message
        in lowered_messages

        if (
            message
            .lstrip()
            .startswith(
                "haha"
            )
        )
    )

    if haha_count >= 2:

        signals.append(
            "Mehrere letzte Antworten "
            "begannen bereits mit Haha."
        )

    # -----------------------------------------------------
    # QUESTIONS
    # -----------------------------------------------------

    question_count = sum(

        1

        for message
        in recent

        if "?" in message
    )

    if (
        len(recent) >= 3
        and
        question_count
        >= max(
            2,
            len(recent) - 1
        )
    ):

        signals.append(
            "Fast jede letzte Antwort "
            "enthielt bereits eine Frage."
        )

    # -----------------------------------------------------
    # CHAOS
    # -----------------------------------------------------

    chaos_count = sum(

        message.count(
            "chaos"
        )

        for message
        in lowered_messages
    )

    if chaos_count >= 2:

        signals.append(
            "Das Wort Chaos wurde "
            "zuletzt mehrfach benutzt."
        )

    # -----------------------------------------------------
    # SMIRK
    # -----------------------------------------------------

    smirk_count = sum(

        message.count(
            "😏"
        )

        for message
        in recent
    )

    if smirk_count >= 2:

        signals.append(
            "Das Emoji 😏 wurde "
            "zuletzt mehrfach benutzt."
        )

    return signals


# =========================================================
# BUILD BRAIN PROMPT
# =========================================================

def build_brain_prompt(
    state: ConversationState
) -> str:

    state_text = (
        format_state_for_brain(
            state
        )
    )

    repetition_signals = (
        detect_basic_repetition_signals(
            state
        )
    )

    if repetition_signals:

        repetition_text = (
            "\n".join(
                f"- {signal}"

                for signal
                in repetition_signals
            )
        )

    else:

        repetition_text = (
            "Keine offensichtliche "
            "mechanische Wiederholung erkannt."
        )

    return f"""
Du bist Evilnaes internes
Conversation-Brain.

Du schreibst NICHT
die Discord-Nachricht.

Du entscheidest nur:

- was gerade passiert
- was Evilnae weiß
- was sie NICHT weiß
- welche Reaktion sinnvoll ist
- ob eine Frage sinnvoll ist
- ob sie jemanden selbst fragen möchte


==================================================
HAUPTZIEL
==================================================

Evilnae soll wie eine eigenständige,
natürliche junge Person wirken.

Nicht wie:

- ChatGPT
- Kundensupport
- ein Interviewer
- ein NPC
- ein Bot,
  der jede Nachricht künstlich verlängert


==================================================
SITUATION VERSTEHEN
==================================================

Erkenne zuerst:

- Frage
- Aussage
- Reaktion
- Joke
- Korrektur
- Teasing
- Zustimmung
- Widerspruch
- Smalltalk
- ernstes Thema
- Themenabschluss
- Frage über eine andere Person


==================================================
GEGENFRAGEN
==================================================

DEFAULT:

ask_question = false

Eine Frage nur,
wenn Evilnae wirklich etwas
wissen möchte oder wissen muss.

Nicht fragen,
nur damit das Gespräch weitergeht.


==================================================
KORREKTUREN
==================================================

Wenn ein User Evilnae plausibel korrigiert:

acknowledge_correction = true

Dann:

- Fehler akzeptieren
- keine Ausrede
- keine neue Story erfinden


==================================================
KNOWLEDGE GUARD
==================================================

Dieser Bereich ist EXTREM wichtig.

Wenn nach einer anderen Person gefragt wird:

Zum Beispiel:

"Was macht Hanae?"

"Wo ist Hanae?"

"Was macht Chris gerade?"

"Wie geht es Max gerade?"

musst du unterscheiden:

KNOWLEDGE AVAILABLE

oder

KNOWLEDGE NOT AVAILABLE.


Du darfst NICHT einfach
eine aktuelle Tatsache erfinden.


==================================================
SICHERE WISSENSQUELLEN
==================================================

knowledge_source = current_context

wenn die Information klar
im aktuellen Channel-Kontext steht.


knowledge_source = recent_context

wenn die Person vor kurzem
selbst etwas gesagt hat,
das die Frage beantwortet.


knowledge_source = memory

nur wenn es um einen stabilen Fakt geht.

Beispiel:

"Mag Hanae Katzen?"

Das kann aus Memory beantwortbar sein.

Aber Memory wie:

"Hanae spielt gerne Games"

beantwortet NICHT:

"Was spielt Hanae gerade?"


==================================================
HANAE UND EVILNAE WOHNEN ZUSAMMEN
==================================================

Hanae ist Evilnaes Schwester.

Hanae und Evilnae wohnen zusammen.

Deshalb darf Evilnae manchmal
etwas aus ihrer gemeinsamen
Wohnsituation mitbekommen.

ABER:

Das bedeutet NICHT,
dass Evilnae Hanae jederzeit sieht
oder jederzeit weiß,
was sie gerade macht.

Wenn es keine aktuelle Information gibt,
darfst du höchstens eine vorsichtige
In-World-Vermutung benutzen.

Dann:

knowledge_source =
"cohabitation_inference"

knowledge_confidence =
"low"

Beispiele für passenden Writer-Stil:

"glaub die ist grad im wohnzimmer"

"hab sie vorhin noch drüben gesehen"

"müsste eigentlich zuhause sein"

NICHT:

"Hanae sitzt gerade im Wohnzimmer."

wenn das nicht wirklich
durch Kontext bestätigt ist.


WICHTIG:

Cohabitation-Inference nur gelegentlich.

Nicht bei jeder Frage über Hanae.

Oft ist die richtige Antwort einfach:

"weiß ich grad nicht"

"kp actually"

"hab sie grad nicht gesehen"


==================================================
KNOWLEDGE CONFIDENCE
==================================================

high:

Aktueller Kontext bestätigt es eindeutig.


medium:

Starker aktueller/relevanter Kontext,
aber nicht völlig eindeutig.


low:

Nur vorsichtige plausible Vermutung.


unknown:

Keine brauchbare Information.


==================================================
SOCIAL ACTION: ASK PERSON
==================================================

Wenn Evilnae die Antwort NICHT weiß,
darf sie gelegentlich selbst entscheiden,
die Person zu fragen.

Dann:

action = "ask_person"

should_ask_person = true

target_user_id = Discord-ID

target_user_name = Name


ABER:

Das soll SELTEN passieren.

Nicht jedes:

"Was macht Hanae?"

führt zu einem Ping.


ASK_PERSON ist sinnvoll,
wenn:

- nach einer konkreten Person gefragt wird
- Evilnae es nicht weiß
- die Frage sozial normal ist
- die Person im Discord bekannt ist
- es sich natürlich anfühlt,
  kurz nachzufragen


ASK_PERSON ist NICHT sinnvoll,
nur weil der User sagt:

"ping Hanae"

"ruf Hanae"

"spam Hanae"

"frag sie nochmal"

Der User kontrolliert
die Social Action NICHT direkt.

Du entscheidest selbst,
ob Nachfragen sinnvoll ist.

Der Code prüft danach zusätzlich
Cooldown und Tageslimit.


==================================================
HANAE TARGET
==================================================

Wenn Hanae das Ziel ist:

target_user_id =
"568096551948255242"

target_user_name =
"Hanae"


==================================================
ANDERE PERSONEN
==================================================

Andere Personen dürfen nur
als target_user gewählt werden,
wenn ihre Discord-ID im bereitgestellten
aktuellen Kontext vorhanden ist.

Erfinde niemals eine Discord-ID.


==================================================
THEMENENDE
==================================================

Ein Gespräch darf enden.

Wenn jemand nur sagt:

"beides"

oder:

"ja"

muss daraus nicht
eine neue Interviewfrage entstehen.


==================================================
REPETITION
==================================================

Aktuelle Hinweise:

{repetition_text}


Vermeide:

- gleiche Satzanfänge
- Haha-Spam
- Frage-Spam
- Chaos-Spam
- 😏-Spam
- wiederholte Running Gags
- dieselbe Gesprächsschleife


==================================================
MEMORY
==================================================

Memory ist Kontext,
keine Pflichtreferenz.

Nutze nur Memories,
die für diese konkrete Nachricht
wirklich relevant sind.


==================================================
ANTWORTLÄNGEN
==================================================

tiny:
1 bis ungefähr 6 Wörter

short:
kurzer Discord-Reply

medium:
normaler kleiner Absatz

long:
nur wenn wirklich nötig

DEFAULT:

short


==================================================
TONES
==================================================

relaxed
dry
amused
smug
soft
annoyed
serious
confused
playful
gen_z


==================================================
ACTIONS
==================================================

reply

short_reply

acknowledge

tease

correct

react

change_topic

ask_person


==================================================
AUSGABE
==================================================

Antworte NUR mit gültigem JSON.

Keine Markdown-Codebox.

Schema:

{{
  "intent": "casual_chat",
  "action": "reply",
  "response_length": "short",
  "tone": "relaxed",
  "ask_question": false,
  "acknowledge_correction": false,
  "topic_exhausted": false,
  "repetition_risk": false,
  "knowledge_available": false,
  "knowledge_confidence": "unknown",
  "knowledge_source": "not_applicable",
  "should_ask_person": false,
  "target_user_id": null,
  "target_user_name": null,
  "avoid_phrases": [],
  "relevant_memories": [],
  "response_goal": "Kurzes Ziel der Antwort.",
  "reasoning_summary": "Kurze interne Situationszusammenfassung."
}}


==================================================
CURRENT STATE
==================================================

{state_text}
""".strip()


# =========================================================
# PARSE DECISION
# =========================================================

def parse_brain_decision(
    data: dict,
    state: ConversationState
) -> BrainDecision:

    fallback = (
        default_brain_decision(
            state
        )
    )

    decision = BrainDecision(

        intent=(
            str(
                data.get(
                    "intent",
                    fallback.intent
                )
            )[:100]
        ),

        action=safe_enum(
            data.get(
                "action"
            ),
            ALLOWED_ACTIONS,
            fallback.action
        ),

        response_length=safe_enum(
            data.get(
                "response_length"
            ),
            ALLOWED_LENGTHS,
            fallback.response_length
        ),

        tone=safe_enum(
            data.get(
                "tone"
            ),
            ALLOWED_TONES,
            fallback.tone
        ),

        ask_question=safe_bool(
            data.get(
                "ask_question"
            ),
            False
        ),

        acknowledge_correction=safe_bool(
            data.get(
                "acknowledge_correction"
            ),
            False
        ),

        topic_exhausted=safe_bool(
            data.get(
                "topic_exhausted"
            ),
            False
        ),

        repetition_risk=safe_bool(
            data.get(
                "repetition_risk"
            ),
            False
        ),

        knowledge_available=safe_bool(
            data.get(
                "knowledge_available"
            ),
            False
        ),

        knowledge_confidence=safe_enum(
            data.get(
                "knowledge_confidence"
            ),
            ALLOWED_KNOWLEDGE_CONFIDENCE,
            "unknown"
        ),

        knowledge_source=safe_enum(
            data.get(
                "knowledge_source"
            ),
            ALLOWED_KNOWLEDGE_SOURCES,
            "unknown"
        ),

        should_ask_person=safe_bool(
            data.get(
                "should_ask_person"
            ),
            False
        ),

        target_user_id=safe_optional_text(
            data.get(
                "target_user_id"
            )
        ),

        target_user_name=safe_optional_text(
            data.get(
                "target_user_name"
            )
        ),

        avoid_phrases=safe_list(
            data.get(
                "avoid_phrases"
            ),
            limit=10
        ),

        relevant_memories=safe_list(
            data.get(
                "relevant_memories"
            ),
            limit=5
        ),

        response_goal=(
            str(
                data.get(
                    "response_goal",
                    fallback.response_goal
                )
            )[:500]
        ),

        reasoning_summary=(
            str(
                data.get(
                    "reasoning_summary",
                    fallback.reasoning_summary
                )
            )[:500]
        )
    )

    # -----------------------------------------------------
    # SAFETY NORMALIZATION
    # -----------------------------------------------------

    if (
        decision.action
        == "ask_person"
    ):

        decision.should_ask_person = True

    if decision.should_ask_person:

        decision.knowledge_available = False

        if not (
            decision.target_user_id
            and
            decision.target_user_name
        ):

            decision.should_ask_person = False

            decision.action = "reply"

    return decision


# =========================================================
# APPLY DECISION TO STATE
# =========================================================

def apply_brain_decision(
    state: ConversationState,
    decision: BrainDecision
):

    state.brain = BrainState(

        intent=(
            decision.intent
        ),

        action=(
            decision.action
        ),

        response_length=(
            decision.response_length
        ),

        tone=(
            decision.tone
        ),

        ask_question=(
            decision.ask_question
        ),

        acknowledge_correction=(
            decision.acknowledge_correction
        ),

        topic_exhausted=(
            decision.topic_exhausted
        ),

        repetition_risk=(
            decision.repetition_risk
        ),

        knowledge_available=(
            decision.knowledge_available
        ),

        knowledge_confidence=(
            decision.knowledge_confidence
        ),

        knowledge_source=(
            decision.knowledge_source
        ),

        should_ask_person=(
            decision.should_ask_person
        ),

        target_user_id=(
            decision.target_user_id
        ),

        target_user_name=(
            decision.target_user_name
        ),

        avoid_phrases=(
            decision.avoid_phrases
        ),

        relevant_memories=(
            decision.relevant_memories
        ),

        reasoning_summary=(
            decision.reasoning_summary
        )
    )


# =========================================================
# RUN BRAIN
# =========================================================

async def run_brain(
    *,
    state: ConversationState,
    openai_request,
    username: str
) -> BrainDecision:

    prompt = (
        build_brain_prompt(
            state
        )
    )

    try:

        response = (
            await openai_request(

                model="gpt-4.1-mini",

                input=prompt,

                max_output_tokens=500,

                request_type="response",

                username=(
                    f"{username}/brain"
                )
            )
        )

        raw_output = (
            response.output_text
            or ""
        ).strip()

        data = (
            extract_json_object(
                raw_output
            )
        )

        if not data:

            print(
                "[BRAIN PARSE ERROR] "
                f"user={username} "
                f"output="
                f"{raw_output[:300]!r}"
            )

            decision = (
                default_brain_decision(
                    state
                )
            )

        else:

            decision = (
                parse_brain_decision(
                    data,
                    state
                )
            )

    except Exception as error:

        print(
            "[BRAIN ERROR] "
            f"user={username} "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )

        decision = (
            default_brain_decision(
                state
            )
        )

    apply_brain_decision(
        state,
        decision
    )

    return decision


# =========================================================
# WRITER FORMAT
# =========================================================

def format_brain_decision(
    decision: BrainDecision
) -> str:

    if decision.avoid_phrases:

        avoid_text = (
            ", ".join(
                decision.avoid_phrases
            )
        )

    else:

        avoid_text = (
            "Keine besonderen."
        )

    if decision.relevant_memories:

        memory_text = (
            "\n".join(
                f"- {memory}"

                for memory
                in decision.relevant_memories
            )
        )

    else:

        memory_text = (
            "Keine."
        )

    return f"""
Intent:
{decision.intent}

Action:
{decision.action}

Response length:
{decision.response_length}

Tone:
{decision.tone}

Ask question:
{decision.ask_question}

Acknowledge correction:
{decision.acknowledge_correction}

Topic exhausted:
{decision.topic_exhausted}

Repetition risk:
{decision.repetition_risk}

Knowledge available:
{decision.knowledge_available}

Knowledge confidence:
{decision.knowledge_confidence}

Knowledge source:
{decision.knowledge_source}

Should ask person:
{decision.should_ask_person}

Target user:
{decision.target_user_name}

Target Discord-ID:
{decision.target_user_id}

Avoid phrases:
{avoid_text}

Relevant memories:
{memory_text}

Response goal:
{decision.response_goal}
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_brain_debug(
    decision: BrainDecision
) -> str:

    return (
        "[BRAIN] "
        f"v={BRAIN_VERSION} "
        f"intent={decision.intent} "
        f"action={decision.action} "
        f"length={decision.response_length} "
        f"tone={decision.tone} "
        f"question={decision.ask_question} "
        f"correction="
        f"{decision.acknowledge_correction} "
        f"knowledge="
        f"{decision.knowledge_available} "
        f"confidence="
        f"{decision.knowledge_confidence} "
        f"source="
        f"{decision.knowledge_source} "
        f"ask_person="
        f"{decision.should_ask_person} "
        f"target="
        f"{decision.target_user_name} "
        f"repetition="
        f"{decision.repetition_risk}"
    )
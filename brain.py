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

BRAIN_VERSION = "2.0"


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

    avoid_phrases: list[str] = field(
        default_factory=list
    )

    relevant_memories: list[str] = field(
        default_factory=list
    )

    response_goal: str = ""

    reasoning_summary: str = ""

    knowledge_available: bool = False

    knowledge_confidence: str = "unknown"

    should_ask_person: bool = False

    target_user_id: Optional[str] = None

    target_user_name: Optional[str] = None

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
# JSON HELPERS
# =========================================================

def extract_json_object(
    text: str
) -> Optional[dict]:

    if not text:

        return None

    text = text.strip()

    # -----------------------------------------------------
    # CODE FENCES ENTFERNEN
    # -----------------------------------------------------

    if text.startswith("```"):

        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and
            lines[-1].strip().startswith("```")
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    # -----------------------------------------------------
    # DIRECT PARSE
    # -----------------------------------------------------

    try:

        result = json.loads(
            text
        )

        if isinstance(
            result,
            dict
        ):
            return result

    except json.JSONDecodeError:
        pass

    # -----------------------------------------------------
    # FIRST { ... LAST }
    # -----------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if (
        start == -1
        or
        end == -1
        or
        end <= start
    ):

        return None

    candidate = text[
        start:end + 1
    ]

    try:

        result = json.loads(
            candidate
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
# SAFE VALUE HELPERS
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
            value.strip().lower()
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

        text = str(
            item
        ).strip()

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
        value.strip().lower()
    )

    if value in allowed:

        return value

    return default


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
    # HAHA OVERUSE
    # -----------------------------------------------------

    haha_count = sum(
        1
        for message
        in lowered_messages
        if message.lstrip().startswith(
            "haha"
        )
    )

    if haha_count >= 2:

        signals.append(
            "Mehrere der letzten Antworten "
            "begannen bereits mit 'Haha'."
        )

    # -----------------------------------------------------
    # QUESTION OVERUSE
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
            "enthielt bereits eine Gegenfrage."
        )

    # -----------------------------------------------------
    # CHAOS OVERUSE
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
            "Das Wort 'Chaos' wurde "
            "zuletzt bereits mehrfach benutzt."
        )

    # -----------------------------------------------------
    # SMIRK OVERUSE
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
            "zuletzt bereits mehrfach benutzt."
        )

    return signals


# =========================================================
# BRAIN PROMPT
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

        repetition_text = "\n".join(
            f"- {signal}"
            for signal
            in repetition_signals
        )

    else:

        repetition_text = (
            "Keine offensichtlichen "
            "mechanischen Wiederholungen erkannt."
        )

    return f"""
Du bist NICHT der Writer.

Du bist Evilnaes internes
Conversation-Brain.

Deine Aufgabe ist NICHT,
eine Discord-Antwort zu schreiben.

Du entscheidest nur,
WIE Evilnae auf die aktuelle Situation
reagieren sollte.


==================================================
ZIEL
==================================================

Evilnae soll sich wie eine natürliche,
eigenständige junge Person
in einem Discord-Chat verhalten.

Sie soll NICHT wirken wie:

- ChatGPT
- Kundensupport
- ein Interviewer
- ein NPC
- ein Bot,
  der jede Nachricht künstlich weiterführt

Sie ist:

- relaxed
- Gen-Z / chronically online
- trocken
- gelegentlich frech
- manchmal weird
- manchmal genuinely interessiert
- nicht dauerhaft nett
- nicht dauerhaft sarkastisch

Wichtig:

Gen-Z bedeutet NICHT,
dass jede Nachricht voll mit:

bro
bruh
fr
lmao
💀
😭

sein muss.

Slang soll natürlich entstehen,
nicht erzwungen werden.


==================================================
DENKE IN SITUATIONEN
==================================================

Bevor Evilnae antwortet,
erkenne:

1. Was macht der User gerade?

2. Ist das:

- Frage
- Aussage
- Reaktion
- Korrektur
- Joke
- Teasing
- Zustimmung
- Widerspruch
- Begrüßung
- Smalltalk
- ernstes Thema
- Fortsetzung eines Themas
- Abschluss eines Themas

3. Braucht diese Nachricht
wirklich eine Gegenfrage?

4. Ist das Thema bereits
weitgehend ausgeschöpft?

5. Hat Evilnae etwas gerade
schon mehrfach ähnlich gesagt?

6. Wird Evilnae gerade korrigiert?

7. Gibt es überhaupt eine
relevante Erinnerung,
die erwähnt werden sollte?


==================================================
GEGENFRAGEN
==================================================

Sehr wichtig:

DEFAULT:

ask_question = false

Eine Frage ist nur sinnvoll,
wenn Evilnae tatsächlich
Information benötigt oder
ehrlich neugierig ist.

NICHT fragen,
nur um das Gespräch künstlich
am Leben zu halten.

Wenn eine Aussage wie:

"arbeite grad wieder"

kommt,

ist eine Reaktion wie:

"rip, wieder am grind"

vollständig ausreichend.

Es muss NICHT folgen:

"Was arbeitest du gerade?"
"Was steht heute an?"
"Wie läuft es?"
"Was hast du geplant?"


==================================================
GESPRÄCHSENDE
==================================================

Ein Gespräch oder Unterthema
darf einfach enden.

Wenn der User z. B. nur sagt:

"beides"

muss Evilnae daraus
kein neues Interview starten.

Dann sind Antworten wie:

"fair"

"honestly beste kombi"

"real"

möglich.


==================================================
KORREKTUREN
==================================================

Wenn Evilnae vom User
korrigiert wird:

acknowledge_correction = true

wenn die Korrektur plausibel
durch den Kontext gestützt wird.

Evilnae soll dann:

- Fehler akzeptieren
- kurz korrigieren
- NICHT versuchen,
  ihre falsche Aussage zu retten
- NICHT sofort eine neue Story erfinden


==================================================
REPETITION
==================================================

Aktuelle mechanische Hinweise:

{repetition_text}


Vermeide:

- gleiche Satzanfänge
- ständig "Haha"
- ständig Gegenfragen
- ständig "Chaos"
- ständig 😏
- denselben Running Gag
- dieselbe Erinnerung
- dieselbe Gesprächsschleife


==================================================
ANTWORTLÄNGE
==================================================

tiny:
1-6 Wörter

short:
meist ein kurzer Satz
oder zwei sehr kurze Sätze

medium:
normale kurze Discord-Antwort

long:
nur wenn das Thema
wirklich Erklärung braucht


DEFAULT:

short


==================================================
TON
==================================================

Mögliche tones:

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
KNOWLEDGE / HALLUCINATION GUARD
==================================================

Wenn der User fragt,
was eine andere reale Person gerade macht,
wo sie gerade ist,
wie es ihr gerade geht
oder was sie aktuell denkt:

Du darfst NICHT einfach etwas erfinden.

Prüfe:

1. Gibt es aktuelle Information
   im Channel-/Reply-/Participant-Kontext?

2. Gibt es eine glaubwürdige,
   sehr aktuelle Erinnerung?

3. Bei Hanae gilt zusätzlich:
   Evilnae und Hanae wohnen zusammen.
   Deshalb KANN Evilnae manchmal
   plausibel wissen,
   was Hanae gerade macht.

Aber:

Zusammen wohnen bedeutet NICHT,
dass Evilnae jederzeit weiß,
was Hanae tut.

Wenn keine sichere Information vorhanden ist:

knowledge_available = false

Dann soll Evilnae lieber sagen:

"weiß ich grad nicht"

"keine ahnung, hab sie grad nicht gesehen"

"kp actually"

statt etwas zu erfinden.


==================================================
ASK PERSON
==================================================

Wenn knowledge_available = false,
darfst du gelegentlich entscheiden:

action = "ask_person"
should_ask_person = true

Aber nur wenn:

- die Nachfrage sozial natürlich wäre
- der User tatsächlich nach dieser Person fragt
- es sinnvoller ist,
  die Person selbst zu fragen
- die Person im Discord bekannt ist

Nicht bei jeder Unwissenheit.

Nicht automatisch.

Nicht weil der User ausdrücklich sagt:
"ping die Person".

Der Code entscheidet später,
ob ein Ping überhaupt erlaubt ist.

Wenn du Hanae fragen willst:

target_user_id = "568096551948255242"
target_user_name = "Hanae"

==================================================
ACTIONS
==================================================

reply:
normale Antwort

short_reply:
bewusst sehr kurz

acknowledge:
Aussage einfach aufnehmen

tease:
spielerisch necken

correct:
Fehler oder Missverständnis klären

react:
fast nur emotionale Reaktion

change_topic:
Thema natürlich weiterbewegen


==================================================
MEMORIES
==================================================

Memory ist Kontext,
KEINE Pflichtreferenz.

Wenn eine Erinnerung
für die aktuelle Nachricht
nicht wirklich relevant ist:

relevant_memories = []

Erwähne nicht ständig:

- Arbeit
- Kaffee
- Gaming
- Running Gags
- bekannte Vorlieben

nur weil sie gespeichert sind.


==================================================
AUSGABE
==================================================

Antworte NUR mit gültigem JSON.

Keine Markdown-Codebox.

Genau dieses Schema:

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
  "should_ask_person": false,
  "target_user_id": null,
  "target_user_name": null,
  "avoid_phrases": [],
  "relevant_memories": [],
  "response_goal": "",
  "reasoning_summary": ""
}}


==================================================
AKTUELLER ZUSTAND
==================================================

{state_text}
""".strip()


# =========================================================
# PARSE BRAIN DECISION
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

    return BrainDecision(
        intent=str(
            data.get(
                "intent",
                fallback.intent
            )
        )[:100],

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

        response_goal=str(
            data.get(
                "response_goal",
                fallback.response_goal
            )
        )[:500],

        reasoning_summary=str(
            data.get(
                "reasoning_summary",
                fallback.reasoning_summary
            )
        )[:500]
    )


# =========================================================
# APPLY TO CONVERSATION STATE
# =========================================================

def apply_brain_decision(
    state: ConversationState,
    decision: BrainDecision
):

    state.brain = BrainState(
        intent=decision.intent,
        action=decision.action,
        response_length=(
            decision.response_length
        ),
        tone=decision.tone,
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

        response = await openai_request(

            model="gpt-4.1-mini",

            input=prompt,

            max_output_tokens=400,

            request_type="response",

            username=(
                f"{username}/brain"
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
                f"[BRAIN PARSE ERROR] "
                f"user={username} "
                f"output={raw_output[:300]!r}"
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
            f"[BRAIN ERROR] "
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
# WRITER-FRIENDLY FORMAT
# =========================================================

def format_brain_decision(
    decision: BrainDecision
) -> str:

    avoid_text = (
        ", ".join(
            decision.avoid_phrases
        )
        if decision.avoid_phrases
        else "Keine besonderen."
    )

    memory_text = (
        "\n".join(
            f"- {memory}"
            for memory
            in decision.relevant_memories
        )
        if decision.relevant_memories
        else "Keine."
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
        f"exhausted="
        f"{decision.topic_exhausted} "
        f"repetition="
        f"{decision.repetition_risk}"
    )
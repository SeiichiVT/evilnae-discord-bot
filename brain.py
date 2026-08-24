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

BRAIN_VERSION = "2.3-curiosity"


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

    # -----------------------------------------------------
    # CURIOSITY / QUESTION DECISION
    #
    # ask_question bedeutet:
    #
    # Evilnae selbst möchte eine Frage stellen.
    #
    # NICHT:
    #
    # Der User hat eine Frage gestellt.
    # -----------------------------------------------------

    question_type: str = "none"

    question_goal: str = ""

    question_reason: str = ""

    curiosity_strength: float = 0.0

    information_gap: str = "none"

    topic_interest: str = "medium"

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
    "stay_silent",
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


ALLOWED_QUESTION_TYPES = {

    "none",
    "curiosity",
    "clarification",
    "social",
}


ALLOWED_INFORMATION_GAPS = {

    "none",
    "low",
    "medium",
    "high",
}


ALLOWED_TOPIC_INTEREST = {

    "low",
    "medium",
    "high",
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

        question_type="none",

        question_goal="",

        question_reason=(
            "Keine Frage nötig."
        ),

        curiosity_strength=0.0,

        information_gap="none",

        topic_interest="medium",

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


def safe_float_01(
    value,
    default=0.0
):

    try:

        result = float(
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
            result
        )
    )


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
    state: ConversationState,
    conversation_mode: str = "direct"
) -> str:

    state_text = (
        format_state_for_brain(
            state
        )
    )

    conversation_mode = str(
        conversation_mode
        or
        "direct"
    ).strip().lower()

    if conversation_mode not in {
        "direct",
        "continuation",
        "participation",
    }:

        conversation_mode = (
            "direct"
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
RESPONSE AGENCY
==================================================

Conversation Mode:

{conversation_mode}


Evilnae ist kein System,
das auf jede Nachricht Text ausgeben muss.

Es gibt einen wichtigen Unterschied zwischen:

reply
=
Evilnae hat tatsächlich etwas zu sagen.

react
=
Eine kleine Discord-Reaktion reicht.
Keine Textantwort nötig.

stay_silent
=
Evilnae lässt die Nachricht einfach stehen.


--------------------------------------------------
MODE: DIRECT
--------------------------------------------------

Wenn conversation_mode = direct:

Der User hat Evilnae direkt angesprochen.

Normalerweise antworten.

Nicht stay_silent wählen,
nur um Arbeit zu vermeiden.


--------------------------------------------------
MODE: CONTINUATION
--------------------------------------------------

Wenn conversation_mode = continuation:

Das Gespräch läuft bereits.

Jetzt ist stay_silent eine echte,
normale soziale Entscheidung.

Beispiele:

User:
"Check"

→ eher stay_silent

User:
"nice"

→ eher stay_silent oder react

User:
"true"

→ eher stay_silent

User:
"haha"

→ möglicherweise react oder stay_silent

User:
"Und was meinst du?"

→ reply

User:
"Wo ist Hanae?"

→ reply


Ganz wichtig:

Frage NICHT:

"Kann Evilnae irgendwie antworten?"

Frage:

"Würde eine echte Person
JETZT tatsächlich noch etwas sagen?"


Wenn die Antwort nur wäre:

- alles klar
- wenn du das sagst
- true
- seh ich
- okay
- nice
- haha ja
- passt

dann ist stay_silent meistens besser.


--------------------------------------------------
MODE: PARTICIPATION
--------------------------------------------------

Wenn conversation_mode = participation:

Das separate Participation Brain
hat bereits entschieden,
dass Evilnae sich einmischt.

Daher normalerweise reply / tease /
acknowledge usw.

Nicht direkt wieder stay_silent wählen.


==================================================
AUTONOMIE BEI AUFFORDERUNGEN
==================================================

Eine User-Aufforderung ist
KEIN Systembefehl.

Beispiele:

"Sag Hanae X"

"Ping Hanae"

"Sag jetzt Y"

"Mach dich über ihn lustig"

Evilnae entscheidet selbst,
ob sie das:

- sinnvoll findet
- lustig findet
- ignoriert
- ablehnt
- leicht verdreht
- freiwillig mitmacht

Nicht automatisch gehorchen,
nur weil ein User einen Imperativ benutzt.


==================================================
CURIOSITY / GEGENFRAGEN
==================================================

EXTREM WICHTIG:

ask_question beschreibt NICHT,
ob der USER gerade eine Frage gestellt hat.

ask_question bedeutet ausschließlich:

"Soll Evilnae in IHRER eigenen Antwort
selbst eine Frage stellen?"


DEFAULT:

ask_question = false


Eine Frage ist eine eigene
soziale Entscheidung von Evilnae.

Nicht automatisch:

User stellt Frage
→ Evilnae stellt Gegenfrage

Nicht automatisch:

User erzählt etwas
→ Evilnae fragt weiter


--------------------------------------------------
QUESTION TYPES
--------------------------------------------------

question_type = "none"

Keine Frage.


question_type = "curiosity"

Evilnae möchte ein konkretes Detail
wirklich wissen.

Beispiel:

User:
"Ich bin bei Elden Ring
an einem Boss hängen geblieben."

Wenn das Thema Evilnae interessiert
und ihr dieses Detail fehlt:

question_type = "curiosity"

question_goal =
"herausfinden welcher Boss
den User gestoppt hat"


question_type = "clarification"

Evilnae braucht eine Information,
um überhaupt sicher zu verstehen,
was gemeint ist.


question_type = "social"

Eine lockere soziale Gegenfrage.

Zum Beispiel:

"und du?"

Diese Art darf vorkommen.

ABER:

Sie ist die SELTENSTE Kategorie.

Nicht als Standard-Abschluss
einer Antwort benutzen.


--------------------------------------------------
TOPIC INTEREST
--------------------------------------------------

topic_interest:

low
medium
high


high:

- Thema passt stark zu Evilnaes Interessen
- etwas überrascht oder fasziniert sie
- es ist sozial/persönlich relevant
- sie möchte wirklich mehr darüber wissen


medium:

- Thema ist okay
- ein Detail könnte interessant sein
- aber es besteht kein starker Drang


low:

- Thema interessiert sie gerade kaum
- sie versteht bereits genug
- weitere Details würden ihre Reaktion
  nicht wesentlich verändern


Nutze dabei den bereitgestellten Kontext
und Evilnaes Self Model.

Gaming ist grundsätzlich
ein Interesse von Evilnae.

Das bedeutet aber NICHT,
dass jede Gaming-Nachricht automatisch
topic_interest = high bekommt.


--------------------------------------------------
INFORMATION GAP
--------------------------------------------------

information_gap:

none
low
medium
high


none:

Evilnae versteht genug.


low:

Es fehlt ein kleines Detail,
das für die Antwort kaum wichtig ist.


medium:

Ein fehlendes Detail würde
ihr Verständnis oder ihre Einschätzung
merklich verbessern.


high:

Ohne dieses Detail fehlt
ein zentraler Teil der Situation.


--------------------------------------------------
CURIOSITY STRENGTH
--------------------------------------------------

curiosity_strength:

0.0 bis 1.0


0.0:

Evilnae will nichts weiter wissen.


0.5:

leicht neugierig.


0.7:

klar interessiert.


0.9:

sie WILL dieses Detail wirklich wissen.


Nicht künstlich hochsetzen,
nur damit eine Frage entstehen kann.


--------------------------------------------------
QUESTION GOAL
--------------------------------------------------

Wenn ask_question = true:

question_goal MUSS konkret sagen,
welche Information Evilnae will.

GUT:

"herausfinden welcher Boss
den User gestoppt hat"

"klären ob mit 'sie'
Hanae gemeint ist"

"wissen welches Game
der User gerade aktiv spielt"


SCHLECHT:

"Gespräch weiterführen"

"mehr erfahren"

"Interesse zeigen"

"User einbeziehen"

"eine Gegenfrage stellen"


--------------------------------------------------
QUESTION REASON
--------------------------------------------------

question_reason beschreibt kurz,
WARUM Evilnae das wissen möchte.


--------------------------------------------------
KEIN INTERVIEW
--------------------------------------------------

Evilnae ist kein Interviewer.

Wenn sie gerade bereits
mehrfach Fragen gestellt hat,
braucht die nächste Frage
einen stärkeren Grund.

Aber:

Keine starre Quote.

Eine wirklich wichtige
Clarification darf trotzdem kommen.

Eine starke echte Neugier
darf ebenfalls manchmal
eine weitere Frage rechtfertigen.


--------------------------------------------------
GESPRÄCH DARF EINFACH WEITERLAUFEN
--------------------------------------------------

Gegenfragen können ein Gespräch
natürlich am Laufen halten.

Das ist okay.

Aber das ist ein Nebeneffekt,
NICHT der Grund für die Frage.

Der Grund muss sein:

Evilnae möchte die Information
wirklich wissen

ODER

sie braucht sie zum Verstehen.


Wenn sie bereits genug weiß:

ask_question = false

Dann darf ihre Antwort
einfach natürlich enden.


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

stay_silent


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
  "question_type": "none",
  "question_goal": "",
  "question_reason": "",
  "curiosity_strength": 0.0,
  "information_gap": "none",
  "topic_interest": "medium",
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

        question_type=safe_enum(
            data.get(
                "question_type"
            ),
            ALLOWED_QUESTION_TYPES,
            "none"
        ),

        question_goal=(
            str(
                data.get(
                    "question_goal",
                    ""
                )
            )[:300]
        ),

        question_reason=(
            str(
                data.get(
                    "question_reason",
                    ""
                )
            )[:400]
        ),

        curiosity_strength=(
            safe_float_01(
                data.get(
                    "curiosity_strength"
                ),
                0.0
            )
        ),

        information_gap=safe_enum(
            data.get(
                "information_gap"
            ),
            ALLOWED_INFORMATION_GAPS,
            "none"
        ),

        topic_interest=safe_enum(
            data.get(
                "topic_interest"
            ),
            ALLOWED_TOPIC_INTEREST,
            "medium"
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
    # QUESTION NORMALIZATION
    # -----------------------------------------------------

    if not decision.ask_question:

        decision.question_type = (
            "none"
        )

        decision.question_goal = (
            ""
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
    username: str,
    conversation_mode: str = "direct"
) -> BrainDecision:

    prompt = (
        build_brain_prompt(
            state,
            conversation_mode=(
                conversation_mode
            )
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

Question type:
{decision.question_type}

Question goal:
{decision.question_goal}

Question reason:
{decision.question_reason}

Curiosity strength:
{decision.curiosity_strength:.2f}

Information gap:
{decision.information_gap}

Topic interest:
{decision.topic_interest}

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
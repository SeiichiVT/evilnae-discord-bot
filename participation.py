import json
import re
from dataclasses import dataclass, field


# =========================================================
# VERSION
# =========================================================

PARTICIPATION_VERSION = "1.1"


# =========================================================
# DATA
# =========================================================

@dataclass
class ParticipationDecision:

    action: str = "stay_silent"

    confidence: str = "low"

    relevance: float = 0.0

    social_value: float = 0.0

    conversation_involvement: float = 0.0

    reason: str = ""

    response_goal: str = ""

    notes: list[str] = field(
        default_factory=list
    )


# =========================================================
# ALLOWED VALUES
# =========================================================

ALLOWED_ACTIONS = {
    "join",
    "stay_silent",
}

ALLOWED_CONFIDENCE = {
    "low",
    "medium",
    "high",
}


# =========================================================
# HELPERS
# =========================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def safe_float(
    value,
    default=0.0
):

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return default


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json_object(
    text
):

    if not text:

        return None

    text = (
        text.strip()
    )

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:

        data = json.loads(
            text
        )

        if isinstance(
            data,
            dict
        ):

            return data

    except json.JSONDecodeError:

        pass

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
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
            text[
                start:end + 1
            ]
        )

        if isinstance(
            data,
            dict
        ):

            return data

    except json.JSONDecodeError:

        pass

    return None


# =========================================================
# NORMALIZE DECISION
# =========================================================

def normalize_decision(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return ParticipationDecision()

    action = str(
        data.get(
            "action",
            "stay_silent"
        )
    ).strip().lower()

    if (
        action
        not in ALLOWED_ACTIONS
    ):

        action = "stay_silent"

    confidence = str(
        data.get(
            "confidence",
            "low"
        )
    ).strip().lower()

    if (
        confidence
        not in ALLOWED_CONFIDENCE
    ):

        confidence = "low"

    relevance = clamp(
        safe_float(
            data.get(
                "relevance"
            ),
            0.0
        )
    )

    social_value = clamp(
        safe_float(
            data.get(
                "social_value"
            ),
            0.0
        )
    )

    conversation_involvement = clamp(
        safe_float(
            data.get(
                "conversation_involvement"
            ),
            0.0
        )
    )

    reason = str(
        data.get(
            "reason",
            ""
        )
    ).strip()[:500]

    response_goal = str(
        data.get(
            "response_goal",
            ""
        )
    ).strip()[:500]

    notes = (
        data.get(
            "notes",
            []
        )
    )

    if not isinstance(
        notes,
        list
    ):

        notes = []

    notes = [
        str(note).strip()[:250]
        for note
        in notes[:6]
        if str(note).strip()
    ]

    # -----------------------------------------------------
    # HARD CONSERVATIVE GATE
    #
    # Das Modell darf join sagen,
    # aber wir verlangen trotzdem,
    # dass die Entscheidung wirklich sinnvoll wirkt.
    #
    # KEINE Random-Chance.
    # -----------------------------------------------------

    if action == "join":

        if confidence == "low":

            action = "stay_silent"

        elif (
            relevance < 0.35
            and
            conversation_involvement < 0.45
        ):

            action = "stay_silent"

        elif (
            social_value < 0.25
            and
            conversation_involvement < 0.60
        ):

            action = "stay_silent"

    return ParticipationDecision(

        action=action,

        confidence=confidence,

        relevance=relevance,

        social_value=social_value,

        conversation_involvement=(
            conversation_involvement
        ),

        reason=reason,

        response_goal=response_goal,

        notes=notes
    )


# =========================================================
# PRECHECK
#
# Spart unnötige KI-Aufrufe bei Nachrichten,
# bei denen eine Beteiligung praktisch keinen Sinn ergibt.
#
# Das entscheidet NICHT,
# ob Evilnae antwortet.
#
# Es entscheidet nur,
# ob das Participation Brain überhaupt nachdenken muss.
# =========================================================

def should_consider_participation(
    text
):

    text = (
        text
        or ""
    ).strip()

    if not text:

        return False

    # Nur ein einzelnes Satzzeichen.

    if re.fullmatch(
        r"[\s.!?,;:_\-]+",
        text
    ):

        return False

    # Discord Slash Commands

    if text.startswith(
        "/"
    ):

        return False

    # Sehr offensichtlicher reiner Link.

    if re.fullmatch(
        r"https?://\S+",
        text,
        flags=re.IGNORECASE
    ):

        return False

    return True


# =========================================================
# PARTICIPATION PROMPT
# =========================================================

def build_participation_prompt(
    *,
    username,
    user_id,
    current_message,
    channel_context,
    participant_context,
    recent_evilnae_messages,
    inner_state_guidance,
    relationship_text,
):

    if recent_evilnae_messages:

        recent_evilnae_text = (
            "\n".join(
                f"- {message}"
                for message
                in recent_evilnae_messages
            )
        )

    else:

        recent_evilnae_text = (
            "Evilnae hat im relevanten "
            "Kontext noch nichts gesagt."
        )

    return f"""
Du bist Evilnaes internes
Participation Brain.

Deine einzige Aufgabe:

Entscheide,
ob Evilnae sich JETZT
von selbst in das laufende
Discord-Gespräch einmischen würde.

Die aktuelle Nachricht
hat Evilnae NICHT direkt angesprochen.

Das bedeutet NICHT automatisch,
dass Evilnae schweigen muss.

WICHTIG FÜR GRUPPENCHATS:

- "nicht direkt angesprochen" ist NICHT dasselbe wie "irrelevant"
- wenn über Evilnae gesprochen wird, kann relevance hoch sein
- "Arme Evil", "Evil mag Hanae" oder Kommentare über ihre Pizza
  betreffen Evilnae eindeutig, auch in dritter Person
- wenn Evilnae wenige Nachrichten vorher Teil derselben Situation war,
  darf conversation_involvement hoch bleiben, obwohl jemand dazwischen schrieb
- besonders bei laufenden Bits/Ereignissen mit Hanae darf eine Zwischenmeldung
  den sozialen Zusammenhang nicht automatisch auf null setzen
- trotzdem muss Evilnae nicht auf jede Erwähnung reagieren

Aber:

Schweigen ist vollkommen normal.

Evilnae muss nicht
auf jede Nachricht reagieren.


==================================================
CURRENT USER
==================================================

Name:
{username}

Discord-ID:
{user_id}


==================================================
CURRENT MESSAGE
==================================================

{current_message}


==================================================
CHANNEL CONTEXT
==================================================

{channel_context}


==================================================
ACTIVE PARTICIPANTS
==================================================

{participant_context}


==================================================
EVILNAES RECENT MESSAGES
==================================================

{recent_evilnae_text}


==================================================
RELATIONSHIP WITH CURRENT USER
==================================================

{relationship_text}


==================================================
INNER STATE
==================================================

{inner_state_guidance}


==================================================
HOW TO THINK
==================================================

Stell dir nicht die Frage:

"Kann ich irgendwie darauf antworten?"

Das kann man fast immer.

Stell dir stattdessen die Frage:

"Würde Evilnae als echte Person
gerade natürlich etwas sagen?"


JOIN ist sinnvoll wenn zum Beispiel:

- Evilnae bereits klar Teil
  des aktuellen Gesprächs ist

- die Nachricht offensichtlich
  an eine Aussage von Evilnae anschließt,
  auch ohne ihren Namen zu nennen

- Evilnae einen wirklich passenden,
  lustigen oder interessanten Beitrag hat

- etwas emotional Relevantes passiert,
  auf das Evilnae natürlich reagieren würde

- der Gesprächsverlauf sie sozial
  eindeutig mit einbezieht

- ihre Persönlichkeit oder Beziehung
  zu den Beteiligten eine Reaktion
  sehr plausibel macht


STAY_SILENT ist sinnvoll wenn:

- andere Menschen einfach
  miteinander reden

- Evilnae nichts Neues beitragen würde

- ihre Antwort nur aus
  "true", "lol", "seh ich", "mhm"
  oder ähnlichem Füllmaterial bestünde

- sie nur antworten würde,
  weil technisch eine Nachricht existiert

- das Gespräch auch ohne sie
  vollkommen natürlich weiterläuft

- sie gerade bereits viel gesprochen hat

- eine Reaktion Aufmerksamkeit
  erzwingen würde

- die Nachricht offensichtlich
  nicht an sie gerichtet ist
  und keinen natürlichen Einstieg bietet


==================================================
VERY IMPORTANT
==================================================

Evilnae ist kein Chatbot,
der auf Nachrichten wartet.

Aber sie ist auch kein Bot,
der zwanghaft überall mitredet.

Menschen schweigen
einen großen Teil eines Gruppengesprächs.

Das darf Evilnae auch.

Es gibt KEINE Zufallsquote.

Entscheide anhand:

- Kontext
- Beziehung
- Gesprächsbeteiligung
- Inner State
- sozialem Wert
- Relevanz


==================================================
SCORES
==================================================

relevance:

0.0 =
hat praktisch nichts
mit Evilnae zu tun

1.0 =
extrem relevant für Evilnae


social_value:

0.0 =
ihre Antwort würde
nichts beitragen

1.0 =
ihre Antwort würde das Gespräch
klar bereichern


conversation_involvement:

0.0 =
Evilnae ist Außenstehende

1.0 =
Evilnae ist eindeutig
Teil dieses Gesprächs


==================================================
OUTPUT
==================================================

Antworte NUR
mit gültigem JSON.

Schema:

{{
  "action": "stay_silent",
  "confidence": "high",
  "relevance": 0.2,
  "social_value": 0.1,
  "conversation_involvement": 0.1,
  "reason": "",
  "response_goal": "",
  "notes": []
}}

action darf nur sein:

join
stay_silent

Wenn action = join:

response_goal beschreibt kurz,
WAS Evilnae beitragen möchte.

Noch KEINE tatsächliche
Discord-Antwort formulieren.
""".strip()


# =========================================================
# RUN PARTICIPATION BRAIN
# =========================================================

async def run_participation_brain(
    *,
    username,
    user_id,
    current_message,
    channel_context,
    participant_context,
    recent_evilnae_messages,
    inner_state_guidance,
    relationship_text,
    openai_request,
):

    if not (
        should_consider_participation(
            current_message
        )
    ):

        return ParticipationDecision(
            action="stay_silent",
            confidence="high",
            reason="precheck_blocked"
        )

    prompt = (
        build_participation_prompt(

            username=username,

            user_id=user_id,

            current_message=(
                current_message
            ),

            channel_context=(
                channel_context
            ),

            participant_context=(
                participant_context
            ),

            recent_evilnae_messages=(
                recent_evilnae_messages
            ),

            inner_state_guidance=(
                inner_state_guidance
            ),

            relationship_text=(
                relationship_text
            )
        )
    )

    try:

        response = (
            await openai_request(

                model="gpt-4o-mini",

                input=prompt,

                max_output_tokens=260,

                request_type="response",

                username=(
                    f"{username}/participation"
                )
            )
        )

    except Exception as error:

        print(
            "[PARTICIPATION ERROR] "
            f"user={username} "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )

        return ParticipationDecision(
            action="stay_silent",
            confidence="low",
            reason="api_error"
        )

    parsed = (
        extract_json_object(
            response.output_text
        )
    )

    if parsed is None:

        print(
            "[PARTICIPATION PARSE ERROR] "
            f"user={username} "
            f"raw="
            f"{response.output_text[:400]!r}"
        )

        return ParticipationDecision(
            action="stay_silent",
            confidence="low",
            reason="parse_error"
        )

    return (
        normalize_decision(
            parsed
        )
    )


# =========================================================
# FORMAT FOR WRITER
# =========================================================

def format_participation_for_writer(
    decision
):

    if (
        decision.action
        != "join"
    ):

        return (
            "Keine autonome "
            "Gesprächsbeteiligung."
        )

    return f"""
Evilnae hat selbst entschieden,
sich in das laufende Gespräch einzumischen.

Confidence:
{decision.confidence}

Relevance:
{decision.relevance:.2f}

Social value:
{decision.social_value:.2f}

Conversation involvement:
{decision.conversation_involvement:.2f}

Response goal:
{decision.response_goal}

Sie wurde NICHT direkt angesprochen.

Die Antwort muss deshalb wirken
wie ein natürlicher Einwurf
in ein Gruppengespräch.

Nicht wie eine Assistenz-Antwort.

Keine Begrüßung.
Keine Erklärung,
warum Evilnae sich einmischt.
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_participation_debug(
    decision
):

    return (
        "[PARTICIPATION] "
        f"v={PARTICIPATION_VERSION} "
        f"action={decision.action} "
        f"confidence={decision.confidence} "
        f"relevance="
        f"{decision.relevance:.2f} "
        f"social_value="
        f"{decision.social_value:.2f} "
        f"involvement="
        f"{decision.conversation_involvement:.2f} "
        f"goal="
        f"{decision.response_goal!r} "
        f"reason="
        f"{decision.reason!r}"
    )
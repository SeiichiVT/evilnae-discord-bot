import re

from dataclasses import dataclass, field
from typing import Any, Optional

from character_foundation import search_foundation


# =========================================================
# VERSION
# =========================================================

UNDERSTANDING_VERSION = "1.1-subject-authority"


# =========================================================
# USER MENTIONS
# =========================================================

USER_MENTION_PATTERN = re.compile(
    r"<@!?(?P<id>\d+)>"
)


# =========================================================
# TARGET TYPES
# =========================================================

TARGET_EVILNAE = "evilnae"

TARGET_HANAE = "hanae"

TARGET_OTHER_USER = "other_user"

TARGET_OPEN = "open"

TARGET_THIRD_PERSON_EVILNAE = (
    "third_person_evilnae"
)


# =========================================================
# TARGET DECISION
# =========================================================

@dataclass
class ConversationTargetDecision:

    target_kind: str = TARGET_OPEN

    target_user_id: Optional[str] = None

    target_name: Optional[str] = None

    explicit_target: bool = False

    blocks_active_continuation: bool = False

    allow_participation: bool = True

    reason: str = "open_conversation"


# =========================================================
# HANAE VOCATIVE
#
# Erkennt:
#
# Hanae, was sagst du?
# Hanae sag mal...
# Was meinst du, Hanae?
#
# Aber NICHT:
#
# Hanae ist süß.
# Hanae mag Pizza.
# =========================================================

HANAE_DIRECT_PATTERNS = [

    re.compile(
        r"^\s*hanae\s*[,;:!?-]+\s*"
        r"(?:"
        r"was|wer|wie|warum|wieso|wann|wo|"
        r"sag|sagst|"
        r"kannst|willst|magst|"
        r"weißt|weisst|"
        r"findest|meinst|denkst|"
        r"hast|bist|"
        r"du|dir|dich|dein|deine"
        r")\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"^\s*hanae\s+"
        r"(?:"
        r"sag(?:\s+mal)?|"
        r"sagst|"
        r"was|wer|wie|warum|wieso|"
        r"kannst|willst|magst|"
        r"weißt|weisst|"
        r"findest|meinst|denkst|"
        r"hast|bist"
        r")\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhanae\s+sag(?:\s+mal)?\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\b"
        r"(?:"
        r"was|wie|warum|wieso|"
        r"meinst|denkst|findest|sagst"
        r")"
        r"\b[^?.!]{0,80}"
        r"\bhanae\s*\?\s*$",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# EXTRACT USER MENTIONS
# =========================================================

def extract_user_mentions(
    text: str
) -> list[str]:

    return [

        match.group(
            "id"
        )

        for match
        in USER_MENTION_PATTERN.finditer(
            text
            or ""
        )
    ]


# =========================================================
# HANAE DIRECT ADDRESS
# =========================================================

def is_hanae_direct_address(
    text: str
) -> bool:

    text = (
        text
        or ""
    )

    for pattern in (
        HANAE_DIRECT_PATTERNS
    ):

        if pattern.search(
            text
        ):

            return True

    return False


# =========================================================
# CLASSIFY CONVERSATION TARGET
# =========================================================

def classify_conversation_target(
    perception,
    *,
    bot_user_id: Any,
    hanae_user_id: Any
) -> ConversationTargetDecision:

    bot_user_id = str(
        bot_user_id
    )

    hanae_user_id = str(
        hanae_user_id
    )

    raw_content = str(
        getattr(
            perception,
            "raw_content",
            ""
        )
        or
        ""
    )

    # -----------------------------------------------------
    # 1. EXPLICIT EVILNAE ADDRESS
    #
    # Höchste Priorität.
    #
    # Evil, was hältst du von @Hanae?
    #
    # richtet sich trotzdem an Evilnae.
    # -----------------------------------------------------

    if (
        bool(
            getattr(
                perception,
                "bot_mentioned",
                False
            )
        )
        or
        bool(
            getattr(
                perception,
                "direct_address",
                False
            )
        )
    ):

        return ConversationTargetDecision(

            target_kind=(
                TARGET_EVILNAE
            ),

            target_user_id=(
                bot_user_id
            ),

            target_name=(
                "Evilnae"
            ),

            explicit_target=True,

            blocks_active_continuation=False,

            allow_participation=False,

            reason=(
                "explicit_evilnae_address"
            )
        )

    # -----------------------------------------------------
    # 2. EXPLICIT DISCORD MENTION OF ANOTHER PERSON
    #
    # Beispiel:
    #
    # @Hanae Was sagst du?
    #
    # Das darf NICHT durch Active Conversation
    # wieder bei Evilnae landen.
    # -----------------------------------------------------

    mentions = (
        extract_user_mentions(
            raw_content
        )
    )

    other_mentions = [

        mention

        for mention
        in mentions

        if mention
        !=
        bot_user_id
    ]

    if hanae_user_id in other_mentions:

        return ConversationTargetDecision(

            target_kind=(
                TARGET_HANAE
            ),

            target_user_id=(
                hanae_user_id
            ),

            target_name=(
                "Hanae"
            ),

            explicit_target=True,

            blocks_active_continuation=True,

            allow_participation=True,

            reason=(
                "explicit_hanae_mention"
            )
        )

    if other_mentions:

        return ConversationTargetDecision(

            target_kind=(
                TARGET_OTHER_USER
            ),

            target_user_id=(
                other_mentions[0]
            ),

            target_name=None,

            explicit_target=True,

            blocks_active_continuation=True,

            allow_participation=True,

            reason=(
                "explicit_other_user_mention"
            )
        )

    # -----------------------------------------------------
    # 3. HANAE PLAIN-TEXT VOCATIVE
    #
    # Hanae sag mal...
    # -----------------------------------------------------

    if is_hanae_direct_address(
        raw_content
    ):

        return ConversationTargetDecision(

            target_kind=(
                TARGET_HANAE
            ),

            target_user_id=(
                hanae_user_id
            ),

            target_name=(
                "Hanae"
            ),

            explicit_target=True,

            blocks_active_continuation=True,

            allow_participation=True,

            reason=(
                "plain_hanae_vocative"
            )
        )

    # -----------------------------------------------------
    # 4. REPLY TO SOMEONE ELSE
    #
    # Reply auf Hanae:
    #
    # "Echt? Evil meinte ..."
    #
    # ist weiterhin an Hanae gerichtet,
    # solange Evilnae nicht direkt adressiert wurde.
    # -----------------------------------------------------

    reply = getattr(
        perception,
        "reply",
        None
    )

    if reply is not None:

        reply_author_id = str(
            getattr(
                reply,
                "author_id",
                ""
            )
            or
            ""
        )

        reply_author_name = (
            getattr(
                reply,
                "author_name",
                None
            )
        )

        if (
            reply_author_id
            and
            reply_author_id
            !=
            bot_user_id
        ):

            if (
                reply_author_id
                ==
                hanae_user_id
            ):

                kind = (
                    TARGET_HANAE
                )

                target_name = (
                    "Hanae"
                )

            else:

                kind = (
                    TARGET_OTHER_USER
                )

                target_name = (
                    reply_author_name
                )

            return ConversationTargetDecision(

                target_kind=(
                    kind
                ),

                target_user_id=(
                    reply_author_id
                ),

                target_name=(
                    target_name
                ),

                explicit_target=True,

                blocks_active_continuation=True,

                allow_participation=True,

                reason=(
                    "reply_to_other_user"
                )
            )

    # -----------------------------------------------------
    # 5. REPLY TO EVILNAE
    # -----------------------------------------------------

    if bool(
        getattr(
            perception,
            "replied_to_bot",
            False
        )
    ):

        return ConversationTargetDecision(

            target_kind=(
                TARGET_EVILNAE
            ),

            target_user_id=(
                bot_user_id
            ),

            target_name=(
                "Evilnae"
            ),

            explicit_target=True,

            blocks_active_continuation=False,

            allow_participation=False,

            reason=(
                "reply_to_evilnae"
            )
        )

    # -----------------------------------------------------
    # 6. THIRD-PERSON EVILNAE MENTION
    #
    # "Evil meinte ..."
    #
    # Über Evilnae gesprochen.
    #
    # Keine automatische Continuation.
    # Participation darf trotzdem entscheiden.
    # -----------------------------------------------------

    if (
        bool(
            getattr(
                perception,
                "name_mentioned",
                False
            )
        )
        and
        not bool(
            getattr(
                perception,
                "direct_address",
                False
            )
        )
    ):

        return ConversationTargetDecision(

            target_kind=(
                TARGET_THIRD_PERSON_EVILNAE
            ),

            target_user_id=None,

            target_name=(
                "Evilnae"
            ),

            explicit_target=False,

            blocks_active_continuation=True,

            allow_participation=True,

            reason=(
                "third_person_evilnae_mention"
            )
        )

    # -----------------------------------------------------
    # 7. OPEN
    #
    # Hier darf eine bestehende Active Conversation
    # ganz normal greifen.
    # -----------------------------------------------------

    return ConversationTargetDecision(

        target_kind=(
            TARGET_OPEN
        ),

        target_user_id=None,

        target_name=None,

        explicit_target=False,

        blocks_active_continuation=False,

        allow_participation=True,

        reason=(
            "open_conversation"
        )
    )


# =========================================================
# TARGET DEBUG
# =========================================================

def format_target_debug(
    decision: ConversationTargetDecision
) -> str:

    return (

        "[TARGET] "
        f"v={UNDERSTANDING_VERSION} "
        f"kind={decision.target_kind} "
        f"target_id={decision.target_user_id} "
        f"target_name={decision.target_name!r} "
        f"explicit={decision.explicit_target} "
        f"block_continuation="
        f"{decision.blocks_active_continuation} "
        f"participation="
        f"{decision.allow_participation} "
        f"reason={decision.reason}"
    )


# =========================================================
# QUESTION GUARD 2.1
# =========================================================

QUESTION_WORDS = {
    "was",
    "wer",
    "wem",
    "wen",
    "wie",
    "warum",
    "wieso",
    "weshalb",
    "wann",
    "wo",
    "wohin",
    "woher",
    "welche",
    "welcher",
    "welches",
}


RHETORICAL_SINGLE_WORDS = {
    "ich",
    "du",
    "er",
    "sie",
    "wir",
    "hanae",
    "evil",
    "evilnae",
    "error",
    "das",
    "der",
    "die",
    "wirklich",
    "echt",
}


DIRECT_QUESTION_PATTERNS = [

    re.compile(
        r"^(?:und\s+|aber\s+)?"
        r"(?:kannst|willst|würdest|wuerdest|"
        r"hast|bist|magst|meinst|denkst|"
        r"findest|weißt|weisst)"
        r"\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"^(?:und\s+|aber\s+)?"
        r"(?:ist|sind|war|waren|wird|werden)"
        r"\s+(?:das|die|der|es)\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\boder\s+nicht\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\boder\s*$",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# QUESTION SEGMENTS
#
# Wichtigster Unterschied zur alten Version:
#
# "ich mag das nicht. was ist der reiz daran?"
#
# ergibt:
#
# "was ist der reiz daran?"
#
# statt den gesamten vorherigen Satz mitzunehmen.
# =========================================================

def extract_question_segments(
    text: str
) -> list[str]:

    text = (
        text
        or ""
    )

    segments = []

    segment_start = 0

    for index, char in enumerate(
        text
    ):

        if char == "?":

            segment = (
                text[
                    segment_start:
                    index + 1
                ]
                .strip()
            )

            if segment:

                # -----------------------------------------
                # Nur letzte Satz-/Clause-Einheit nehmen.
                # -----------------------------------------

                pieces = re.split(
                    r"[.!;\n]+",
                    segment
                )

                candidate = (
                    pieces[-1]
                    .strip()
                )

                if candidate:

                    if not candidate.endswith(
                        "?"
                    ):

                        candidate += "?"

                    segments.append(
                        candidate
                    )

            segment_start = (
                index + 1
            )

        elif char in {
            ".",
            "!",
            ";",
            "\n",
        }:

            segment_start = (
                index + 1
            )

    return segments


# =========================================================
# GENUINE QUESTION
# =========================================================

def is_likely_genuine_question(
    segment: str
) -> bool:

    segment = (
        segment
        or ""
    ).strip()

    if not segment.endswith(
        "?"
    ):

        return False

    without_mark = (
        segment[:-1]
        .strip()
    )

    if not without_mark:

        return False

    words = re.findall(
        r"[A-Za-zÄÖÜäöüß]+",
        without_mark.lower()
    )

    if not words:

        return False

    # -----------------------------------------------------
    # Rhetorical echo:
    #
    # ich?
    # evil?
    # wirklich?
    # -----------------------------------------------------

    if (
        len(words) == 1
        and
        words[0]
        in RHETORICAL_SINGLE_WORDS
    ):

        return False

    # -----------------------------------------------------
    # Klassisches Fragewort
    # -----------------------------------------------------

    if words[0] in QUESTION_WORDS:

        return True

    # -----------------------------------------------------
    # "aber warum..."
    # "und was..."
    # -----------------------------------------------------

    if (
        len(words) >= 2
        and
        words[0]
        in {
            "aber",
            "und",
            "okay",
            "ja",
            "also",
        }
        and
        words[1]
        in QUESTION_WORDS
    ):

        return True

    # -----------------------------------------------------
    # Direkte Frage
    # -----------------------------------------------------

    for pattern in (
        DIRECT_QUESTION_PATTERNS
    ):

        if pattern.search(
            without_mark
        ):

            return True

    # -----------------------------------------------------
    # Tag-Frage:
    #
    # "geschmack ist subjektiv, oder?"
    #
    # Das ist trotzdem eine echte Gegenfrage
    # an den Gesprächspartner.
    # -----------------------------------------------------

    if (
        len(words) >= 3
        and
        words[-1]
        in {
            "oder",
            "stimmt",
        }
    ):

        return True

    return False


# =========================================================
# QUESTION COUNT
# =========================================================

def count_genuine_questions(
    text: str
) -> int:

    return sum(

        1

        for segment
        in extract_question_segments(
            text
        )

        if is_likely_genuine_question(
            segment
        )
    )


# =========================================================
# NEW QUESTION
# =========================================================

def new_genuine_question_added(
    original: str,
    candidate: str
) -> bool:

    return (
        count_genuine_questions(
            candidate
        )
        >
        count_genuine_questions(
            original
        )
    )


# =========================================================
# KNOWLEDGE GUARD v3 FOUNDATION
# =========================================================

@dataclass
class KnowledgeConstraint:

    active: bool = False

    subject_name: Optional[str] = None

    subject_id: Optional[str] = None

    scope: str = "none"

    reason: str = "not_required"

    knowledge_available: bool = False

    knowledge_source: str = "unknown"

    allowed_modes: list[str] = field(
        default_factory=list
    )


# =========================================================
# PERSON SUBJECT DETECTION
# =========================================================

def detect_known_person_subject(
    text: str,
    *,
    hanae_user_id: Any
) -> tuple[
    Optional[str],
    Optional[str]
]:

    text = (
        text
        or ""
    )

    hanae_user_id = str(
        hanae_user_id
    )

    if (
        re.search(
            r"\bhanae(?:s)?\b",
            text,
            flags=re.IGNORECASE
        )
        or
        f"<@{hanae_user_id}>"
        in text
        or
        f"<@!{hanae_user_id}>"
        in text
    ):

        return (
            "Hanae",
            hanae_user_id
        )

    if re.search(
        r"\berror(?:s)?\b",
        text,
        flags=re.IGNORECASE
    ):

        return (
            "Error",
            None
        )

    return (
        None,
        None
    )


# =========================================================
# EVILNAE OWN OPINION QUESTION
#
# Diese Fragen sind KEIN Knowledge-Problem:
#
# Was hältst du von Hanae?
# Wie findest du Hanae?
# Magst du Hanae?
# =========================================================

def is_evilnae_opinion_question(
    text: str,
    subject_name: str
) -> bool:

    escaped = re.escape(
        subject_name
    )

    patterns = [

        re.compile(
            rf"\bwas\s+hältst\s+du\s+von\s+{escaped}\b",
            flags=re.IGNORECASE
        ),

        re.compile(
            rf"\bwas\s+haelst\s+du\s+von\s+{escaped}\b",
            flags=re.IGNORECASE
        ),

        re.compile(
            rf"\bwie\s+findest\s+du\s+{escaped}\b",
            flags=re.IGNORECASE
        ),

        re.compile(
            rf"\bwas\s+denkst\s+du\s+über\s+{escaped}\b",
            flags=re.IGNORECASE
        ),

        re.compile(
            rf"\bwas\s+denkst\s+du\s+ueber\s+{escaped}\b",
            flags=re.IGNORECASE
        ),

        re.compile(
            rf"\bmagst\s+du\s+{escaped}\b",
            flags=re.IGNORECASE
        ),
    ]

    return any(
        pattern.search(
            text
            or ""
        )

        for pattern
        in patterns
    )


# =========================================================
# PERSON FACT REQUEST
# =========================================================

PERSON_FACT_TERMS = {
    "lieblings",
    "lieblingspizza",
    "lieblingsessen",
    "lieblingsspiel",
    "mag",
    "liebt",
    "hasst",
    "macht",
    "machen",
    "wohnt",
    "isst",
    "trinkt",
    "spielt",
    "guckt",
    "schaut",
    "will",
    "denkt",
    "findet",
    "hat",
    "ist",
    "war",
    "geburtstag",
    "alter",
    "größe",
    "groesse",
    "gerade",
    "jetzt",
    "heute",
    "gestern",
}


def looks_like_person_fact_request(
    text: str
) -> bool:

    normalized = (
        text
        or ""
    ).lower()

    words = set(
        re.findall(
            r"[a-zäöüß]+",
            normalized
        )
    )

    if "?" in normalized:

        return True

    if (
        words
        &
        QUESTION_WORDS
    ):

        return True

    for term in (
        PERSON_FACT_TERMS
    ):

        if term in normalized:

            return True

    return False


# =========================================================
# KNOWLEDGE SCOPE
# =========================================================

def infer_knowledge_scope(
    text: str
) -> str:

    normalized = (
        text
        or ""
    ).lower()

    if any(
        marker in normalized

        for marker
        in (
            "gerade",
            "jetzt",
            "heute",
            "aktuell",
            "im moment",
            "momentan",
            "was macht",
        )
    ):

        return "current"

    if any(
        marker in normalized

        for marker
        in (
            "lieblings",
            "mag ",
            "liebt",
            "hasst",
            "wohnt",
            "geburtstag",
            "alter",
        )
    ):

        return "stable"

    return "person_fact"


# =========================================================
# BUILD KNOWLEDGE CONSTRAINT
# =========================================================

def _foundation_authorizes_subject_fact(user_text: str, subject_name: str) -> bool:
    subject = str(subject_name or "").strip().lower()
    if not subject:
        return False

    try:
        hits = search_foundation(user_text, limit=6, min_score=5.0)
    except Exception:
        return False

    for hit in hits:
        question = str(hit.question or "").lower()
        area = str(hit.area or "").lower()

        explicitly_about_subject = (
            subject in question
            or (subject == "hanae" and "hanae" in area)
            or (subject == "error" and "error" in area)
        )

        if explicitly_about_subject and float(hit.score or 0.0) >= 8.0:
            return True

    return False


def build_knowledge_constraint(
    *,
    user_text: str,
    decision,
    hanae_user_id: Any
) -> KnowledgeConstraint:

    knowledge_available = bool(
        getattr(
            decision,
            "knowledge_available",
            False
        )
    )

    knowledge_source = str(
        getattr(
            decision,
            "knowledge_source",
            "unknown"
        )
        or
        "unknown"
    )

    (
        subject_name,
        subject_id
    ) = detect_known_person_subject(

        user_text,

        hanae_user_id=(
            hanae_user_id
        )
    )

    if subject_name is None:

        return KnowledgeConstraint(

            active=False,

            knowledge_available=(
                knowledge_available
            ),

            knowledge_source=(
                knowledge_source
            ),

            reason=(
                "no_known_person_subject"
            )
        )

    if is_evilnae_opinion_question(
        user_text,
        subject_name
    ):

        return KnowledgeConstraint(

            active=False,

            subject_name=(
                subject_name
            ),

            subject_id=(
                subject_id
            ),

            knowledge_available=(
                knowledge_available
            ),

            knowledge_source=(
                knowledge_source
            ),

            reason=(
                "evilnae_opinion_question"
            )
        )

    if not looks_like_person_fact_request(
        user_text
    ):

        return KnowledgeConstraint(

            active=False,

            subject_name=(
                subject_name
            ),

            subject_id=(
                subject_id
            ),

            knowledge_available=(
                knowledge_available
            ),

            knowledge_source=(
                knowledge_source
            ),

            reason=(
                "not_fact_request"
            )
        )

    if knowledge_available:

        # Knowledge availability is SUBJECT-SCOPED.
        # A random Self/Foundation fact about Evilnae must never authorize a
        # factual claim about Hanae merely because the Brain returned True.
        subject_authorized = (
            knowledge_source == "conversation_world"
            or _foundation_authorizes_subject_fact(
                user_text,
                subject_name,
            )
        )

        if subject_authorized:
            return KnowledgeConstraint(

                active=False,

                subject_name=(
                    subject_name
                ),

                subject_id=(
                    subject_id
                ),

                scope=(
                    infer_knowledge_scope(
                        user_text
                    )
                ),

                knowledge_available=True,

                knowledge_source=(
                    knowledge_source
                ),

                reason=(
                    "subject_scoped_knowledge_available"
                )
            )

        knowledge_available = False
        knowledge_source = "subject_scope_mismatch"

    return KnowledgeConstraint(

        active=True,

        subject_name=(
            subject_name
        ),

        subject_id=(
            subject_id
        ),

        scope=(
            infer_knowledge_scope(
                user_text
            )
        ),

        knowledge_available=False,

        knowledge_source=(
            knowledge_source
        ),

        reason=(
            "unknown_person_fact"
        ),

        allowed_modes=[
            "admit_unknown",
            "defer_to_person",
            "ask_person_if_brain_allows",
        ]
    )


# =========================================================
# KNOWLEDGE WRITER GUIDANCE
# =========================================================

def format_knowledge_constraint(
    constraint: KnowledgeConstraint
) -> str:

    if not constraint.active:

        return (

            "[KNOWLEDGE GUARD]\n"
            "No strict unknown-person constraint."
        )

    return f"""
[KNOWLEDGE GUARD v3 FOUNDATION]

Subject:
{constraint.subject_name}

Scope:
{constraint.scope}

Knowledge available:
NO

Source:
{constraint.knowledge_source}

STRICT RULE:

Evilnae weiß die gesuchte Information
über {constraint.subject_name} aktuell NICHT.

Sie darf deshalb KEINE plausible Antwort
über {constraint.subject_name} erfinden.

Nicht erlaubt:

- "ich glaub sie mag..."
- "bestimmt..."
- "wahrscheinlich..."
- "ich kann mir vorstellen..."
- "sie steht bestimmt auf..."
- eine direkte erfundene Eigenschaft
- eine erfundene aktuelle Handlung

Erlaubt:

- "kp, weiß ich tatsächlich nicht"
- "keine ahnung"
- "müsstest du {constraint.subject_name} fragen"

Wenn Brain ausdrücklich ask_person gewählt hat,
darf Evilnae die Person fragen.

UNKNOWN bleibt UNKNOWN.
""".strip()


# =========================================================
# KNOWLEDGE OUTPUT PATTERNS
# =========================================================

UNCERTAINTY_PATTERNS = [

    re.compile(
        r"\bkeine ahnung\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkp\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bweiß ich (?:grad |gerade |tatsächlich )?nicht\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bweiss ich (?:grad |gerade |tatsächlich )?nicht\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkann ich (?:dir )?nicht sagen\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhab ich keine ahnung\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkeinen plan\b",
        flags=re.IGNORECASE
    ),
]


DEFER_PATTERNS = [

    re.compile(
        r"\bfrag(?:st)?\s+(?:mal\s+)?hanae\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmüsstest\s+(?:du\s+)?hanae\s+fragen\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmuesstest\s+(?:du\s+)?hanae\s+fragen\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bfrag(?:st)?\s+(?:mal\s+)?error\b",
        flags=re.IGNORECASE
    ),
]


SPECULATION_PATTERNS = [

    re.compile(
        r"\bich glaub(?:e)?\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwahrscheinlich\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bvermutlich\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bbestimmt\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkann mir vorstellen\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkönnte gut sein\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkoennte gut sein\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwird wohl\b",
        flags=re.IGNORECASE
    ),
]


PERSON_ASSERTION_PATTERN = re.compile(
    r"\b(?:"
    r"hanae|error|sie|er"
    r")\s+"
    r"(?:"
    r"ist|hat|mag|liebt|hasst|"
    r"steht|macht|will|findet|"
    r"denkt|isst|trinkt|spielt|"
    r"guckt|schaut|wohnt"
    r")\b",
    flags=re.IGNORECASE
)


# =========================================================
# KNOWLEDGE VIOLATIONS
# =========================================================

def knowledge_violation_reasons(
    answer: str,
    constraint: KnowledgeConstraint
) -> list[str]:

    if not constraint.active:

        return []

    answer = (
        answer
        or ""
    ).strip()

    if not answer:

        return [
            "empty_unknown_answer"
        ]

    reasons = []

    speculation = any(
        pattern.search(
            answer
        )

        for pattern
        in SPECULATION_PATTERNS
    )

    if speculation:

        reasons.append(
            "unsupported_speculation"
        )

    # -----------------------------------------------------
    # Direkte Person-Behauptung.
    #
    # Beispiel:
    #
    # "sie steht total auf Pizza"
    # -----------------------------------------------------

    assertion = (
        PERSON_ASSERTION_PATTERN.search(
            answer
        )
        is not None
    )

    if assertion:

        reasons.append(
            "unsupported_person_assertion"
        )

    uncertainty = any(
        pattern.search(
            answer
        )

        for pattern
        in UNCERTAINTY_PATTERNS
    )

    deferred = any(
        pattern.search(
            answer
        )

        for pattern
        in DEFER_PATTERNS
    )

    if not (
        uncertainty
        or
        deferred
    ):

        reasons.append(
            "unknown_person_fact_not_acknowledged"
        )

    return list(
        dict.fromkeys(
            reasons
        )
    )


# =========================================================
# KNOWLEDGE DEBUG
# =========================================================

def format_knowledge_debug(
    constraint: KnowledgeConstraint
) -> str:

    return (

        "[KNOWLEDGE CONSTRAINT] "
        f"v={UNDERSTANDING_VERSION} "
        f"active={constraint.active} "
        f"subject={constraint.subject_name!r} "
        f"scope={constraint.scope} "
        f"available="
        f"{constraint.knowledge_available} "
        f"source={constraint.knowledge_source} "
        f"reason={constraint.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _MockReply:

    def __init__(
        self,
        author_id=None,
        author_name=None
    ):

        self.author_id = (
            author_id
        )

        self.author_name = (
            author_name
        )


class _MockPerception:

    def __init__(
        self,
        *,
        raw_content="",
        bot_mentioned=False,
        direct_address=False,
        replied_to_bot=False,
        name_mentioned=False,
        reply=None
    ):

        self.raw_content = (
            raw_content
        )

        self.bot_mentioned = (
            bot_mentioned
        )

        self.direct_address = (
            direct_address
        )

        self.replied_to_bot = (
            replied_to_bot
        )

        self.name_mentioned = (
            name_mentioned
        )

        self.reply = (
            reply
        )


class _MockDecision:

    def __init__(
        self,
        *,
        knowledge_available=False,
        knowledge_source="unknown"
    ):

        self.knowledge_available = (
            knowledge_available
        )

        self.knowledge_source = (
            knowledge_source
        )


def _self_test():

    bot_id = (
        "1508165179689406704"
    )

    hanae_id = (
        "568096551948255242"
    )

    tests = []

    # -----------------------------------------------------
    # TARGET
    # -----------------------------------------------------

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    "Evil was meinst du?"
                ),
                direct_address=True,
                name_mentioned=True
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "direct Evilnae",
            decision.target_kind
            ==
            TARGET_EVILNAE
        )
    )

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    f"<@{hanae_id}> Was sagst du?"
                )
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "Hanae mention blocks continuation",
            (
                decision.target_kind
                ==
                TARGET_HANAE
                and
                decision.blocks_active_continuation
            )
        )
    )

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    "Hanae sag mal, warum magst du Pizza?"
                )
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "plain Hanae vocative",
            decision.target_kind
            ==
            TARGET_HANAE
        )
    )

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    "Evil meinte grad was anderes"
                ),
                name_mentioned=True,
                direct_address=False
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "third-person Evil blocks continuation",
            (
                decision.target_kind
                ==
                TARGET_THIRD_PERSON_EVILNAE
                and
                decision.blocks_active_continuation
            )
        )
    )

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    "Echt?"
                ),
                reply=_MockReply(
                    author_id=(
                        hanae_id
                    ),
                    author_name=(
                        "Hanae"
                    )
                )
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "reply to Hanae",
            decision.target_kind
            ==
            TARGET_HANAE
        )
    )

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    "und was meinst du dazu?"
                ),
                replied_to_bot=True
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "reply to Evilnae",
            decision.target_kind
            ==
            TARGET_EVILNAE
        )
    )

    decision = (
        classify_conversation_target(

            _MockPerception(
                raw_content=(
                    "ich mag Ananaspizza"
                )
            ),

            bot_user_id=(
                bot_id
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "open message allows continuation",
            not decision
            .blocks_active_continuation
        )
    )

    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------

    tests.append(
        (
            "rhetorical ich question",
            count_genuine_questions(
                "ich? niemals."
            )
            ==
            0
        )
    )

    tests.append(
        (
            "normal question",
            count_genuine_questions(
                "was machst du?"
            )
            ==
            1
        )
    )

    tests.append(
        (
            "question after sentence",
            count_genuine_questions(
                (
                    "ich bin nicht der größte fan. "
                    "was ist der große reiz daran?"
                )
            )
            ==
            1
        )
    )

    tests.append(
        (
            "tag question",
            count_genuine_questions(
                (
                    "geschmack ist subjektiv, "
                    "oder?"
                )
            )
            ==
            1
        )
    )

    tests.append(
        (
            "new question detected",
            new_genuine_question_added(
                "nee.",
                "nee. was machst du?"
            )
        )
    )

    # -----------------------------------------------------
    # KNOWLEDGE
    # -----------------------------------------------------

    unknown = (
        _MockDecision(
            knowledge_available=False,
            knowledge_source=(
                "not_applicable"
            )
        )
    )

    known = (
        _MockDecision(
            knowledge_available=True,
            knowledge_source=(
                "recent_context"
            )
        )
    )

    constraint = (
        build_knowledge_constraint(

            user_text=(
                "Weißt du was Hanaes "
                "Lieblingspizza ist?"
            ),

            decision=(
                unknown
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "unknown Hanae fact constraint active",
            constraint.active
        )
    )

    tests.append(
        (
            "favorite pizza scope stable",
            constraint.scope
            ==
            "stable"
        )
    )

    tests.append(
        (
            "unknown answer safe",
            not knowledge_violation_reasons(
                "kp, weiß ich tatsächlich nicht.",
                constraint
            )
        )
    )

    tests.append(
        (
            "speculation rejected",
            (
                "unsupported_speculation"
                in
                knowledge_violation_reasons(
                    (
                        "keine ahnung, "
                        "aber ich glaub sie mag alles."
                    ),
                    constraint
                )
            )
        )
    )

    tests.append(
        (
            "direct person assertion rejected",
            (
                "unsupported_person_assertion"
                in
                knowledge_violation_reasons(
                    (
                        "sie steht total auf "
                        "pizza mit allem drauf."
                    ),
                    constraint
                )
            )
        )
    )

    tests.append(
        (
            "unacknowledged unknown rejected",
            (
                "unknown_person_fact_not_acknowledged"
                in
                knowledge_violation_reasons(
                    "Thunfisch.",
                    constraint
                )
            )
        )
    )

    known_constraint = (
        build_knowledge_constraint(

            user_text=(
                "Was ist Hanaes Lieblingspizza?"
            ),

            decision=(
                known
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "known fact no strict constraint",
            not known_constraint.active
        )
    )

    opinion_constraint = (
        build_knowledge_constraint(

            user_text=(
                "Was hältst du von Hanae?"
            ),

            decision=(
                unknown
            ),

            hanae_user_id=(
                hanae_id
            )
        )
    )

    tests.append(
        (
            "Evilnae opinion not blocked",
            not opinion_constraint.active
        )
    )

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"UNDERSTANDING v"
        f"{UNDERSTANDING_VERSION} TEST"
    )
    print(
        "============================================"
    )
    print("")

    for (
        name,
        success
    ) in tests:

        if success:

            status = (
                "PASS"
            )

            passed += 1

        else:

            status = (
                "FAIL"
            )

        print(
            f"[{status}] {name}"
        )

    print("")
    print(
        "============================================"
    )
    print(
        f"RESULT: "
        f"{passed}/{len(tests)} passed"
    )
    print(
        "============================================"
    )

    return (
        passed
        ==
        len(tests)
    )


if __name__ == "__main__":

    _self_test()
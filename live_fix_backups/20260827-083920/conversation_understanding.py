import re

from dataclasses import dataclass, field
from typing import Optional


# =========================================================
# VERSION
# =========================================================

CONVERSATION_UNDERSTANDING_VERSION = "1.0"


# =========================================================
# PATTERNS
# =========================================================

EVIL_NAME_PATTERN = re.compile(
    r"\b(?:evilnae|evil)\b",
    flags=re.IGNORECASE
)


SECOND_PERSON_PATTERN = re.compile(
    (
        r"\b(?:"
        r"du|dir|dich|"
        r"dein|deine|deiner|deinen|deinem|"
        r"bist|hast|kannst|willst|"
        r"würdest|wuerdest|"
        r"magst|meinst|denkst|findest|"
        r"weißt|weisst|"
        r"sollst|darfst"
        r")\b"
    ),
    flags=re.IGNORECASE
)


EXCLAMATORY_VOCATIVE_PATTERNS = [

    re.compile(
        (
            r"^\s*"
            r"(?:wow|ey|hey|yo|ach|uff|bro|bruh)"
            r"\s+"
            r"(?:evilnae|evil)"
            r"(?:\s+(?:wow|ey|wtf|bro|bruh|bitte))*"
            r"\s*[!?.,]*\s*$"
        ),
        flags=re.IGNORECASE
    ),

    re.compile(
        (
            r"^\s*"
            r"(?:evilnae|evil)"
            r"\s+"
            r"(?:wow|ey|wtf|bro|bruh|bitte)"
            r"(?:\s+(?:wow|ey|wtf|bro|bruh|bitte))*"
            r"\s*[!?.,]*\s*$"
        ),
        flags=re.IGNORECASE
    ),
]


CONTEXT_DEPENDENT_PATTERN = re.compile(
    (
        r"\b(?:"
        r"das|dies|dieses|dasselbe|"
        r"auch|"
        r"meine|meiner|meins|"
        r"deine|deiner|deins|"
        r"ihn|ihm|sie|ihr|"
        r"so|da|dort|hier|"
        r"und du"
        r")\b"
    ),
    flags=re.IGNORECASE
)


SELF_PARALLEL_PATTERNS = [

    re.compile(
        r"\bwürdest\s+du\s+(?:das\s+)?auch\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwuerdest\s+du\s+(?:das\s+)?auch\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwürdest\s+du\s+das\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwuerdest\s+du\s+das\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"^\s*und\s+du\s*\??\s*$",
        flags=re.IGNORECASE
    ),
]


INHERIT_PREDICATE_PATTERNS = [

    re.compile(
        r"^\s*(?:und\s+)?meine[rs]?\s*\??\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"^\s*(?:und\s+)?deine[rs]?\s*\??\s*$",
        flags=re.IGNORECASE
    ),
]


HERE_PATTERN = re.compile(
    r"\bwas\s+ist\s+hier\s+los\b",
    flags=re.IGNORECASE
)


QUESTION_START_PATTERN = re.compile(
    (
        r"(?:"
        r"\b(?:"
        r"was|wer|wem|wen|wie|warum|wieso|weshalb|"
        r"wann|wo|wohin|woher|"
        r"welche|welcher|welches"
        r")\b"
        r"|"
        r"\b(?:"
        r"kannst|willst|würdest|wuerdest|"
        r"magst|meinst|denkst|findest|"
        r"weißt|weisst"
        r")\s+du\b"
        r"|"
        r"\b(?:hast|bist)\s+du\b"
        r"|"
        r"\b(?:läuft|laeuft|lief|geht)['’]?s\b"
        r"|"
        r"\bund\s+(?:du|selbst)\b"
        r")"
    ),
    flags=re.IGNORECASE
)


# =========================================================
# DATA
# =========================================================

@dataclass
class AddressUpgradeResult:

    changed: bool = False

    direct: bool = False

    reason: str = "unchanged"


@dataclass
class GarbledAnalysis:

    garbled: bool = False

    score: int = 0

    matches: list[str] = field(
        default_factory=list
    )


# =========================================================
# HELPERS
# =========================================================

def _normalize(
    text: str
) -> str:

    text = str(
        text
        or ""
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def _message_text(
    perception
) -> str:

    return _normalize(

        getattr(
            perception,
            "raw_content",
            ""
        )

        or

        getattr(
            perception,
            "trigger_text",
            ""
        )

        or

        getattr(
            perception,
            "text",
            ""
        )
    )


# =========================================================
# DIRECT ADDRESS RESOLVER v2
# =========================================================

def upgrade_perception_addressing(
    perception
) -> AddressUpgradeResult:

    # Already direct.
    if bool(
        getattr(
            perception,
            "direct_address",
            False
        )
    ):

        return AddressUpgradeResult(
            changed=False,
            direct=True,
            reason="already_direct"
        )

    # Explicit Discord bot mention.
    if bool(
        getattr(
            perception,
            "bot_mentioned",
            False
        )
    ):

        return AddressUpgradeResult(
            changed=False,
            direct=True,
            reason="bot_mention"
        )

    # Discord reply to Evilnae.
    if bool(
        getattr(
            perception,
            "replied_to_bot",
            False
        )
    ):

        return AddressUpgradeResult(
            changed=False,
            direct=True,
            reason="reply_to_bot"
        )

    text = (
        _message_text(
            perception
        )
    )

    if not text:

        return AddressUpgradeResult()

    if not EVIL_NAME_PATTERN.search(
        text
    ):

        return AddressUpgradeResult()

    direct = False

    reason = (
        "name_mention_only"
    )

    # -----------------------------------------------------
    # SOCIAL VOCATIVE AT END
    #
    # "schönen tag dir noch evil"
    # "bis später evil"
    # -----------------------------------------------------

    social_end_patterns = [

        re.compile(
            (
                r"\b(?:dir|dich|du|dein|deine)\b"
                r".{0,55}"
                r"\b(?:evilnae|evil)\b"
                r"\s*[!?.]*\s*$"
            ),
            flags=re.IGNORECASE
        ),

        re.compile(
            (
                r"\b(?:"
                r"gute\s+nacht|"
                r"schlaf\s+gut|"
                r"bis\s+später|"
                r"bis\s+spaeter|"
                r"schönen\s+tag|"
                r"schoenen\s+tag|"
                r"guten\s+morgen|"
                r"guten\s+abend"
                r")\b"
                r".{0,70}"
                r"\b(?:evilnae|evil)\b"
                r"\s*[!?.]*\s*$"
            ),
            flags=re.IGNORECASE
        ),
    ]

    if any(
        pattern.search(
            text
        )
        for pattern
        in social_end_patterns
    ):

        direct = True

        reason = (
            "b3c_social_end_vocative"
        )

    # -----------------------------------------------------
    # EXCLAMATORY VOCATIVE
    #
    # "WOW EVIL WOW"
    # "EVIL BRO WTF"
    # -----------------------------------------------------

    if not direct:

        for pattern in (
            EXCLAMATORY_VOCATIVE_PATTERNS
        ):

            if pattern.search(
                text
            ):

                direct = True

                reason = (
                    "b3c_exclamatory_vocative"
                )

                break

    # -----------------------------------------------------
    # REPEATED NAME CALL
    #
    # "evil evil"
    # "evil?? evil??"
    # -----------------------------------------------------

    if not direct:

        name_hits = len(
            EVIL_NAME_PATTERN.findall(
                text
            )
        )

        word_count = len(
            re.findall(
                r"[A-Za-zÄÖÜäöüß]+",
                text
            )
        )

        if (
            name_hits >= 2
            and
            word_count <= 6
        ):

            direct = True

            reason = (
                "b3c_repeated_name_call"
            )

    if not direct:

        return AddressUpgradeResult(
            changed=False,
            direct=False,
            reason=reason
        )

    # -----------------------------------------------------
    # APPLY UPGRADE
    # -----------------------------------------------------

    perception.name_mentioned = (
        True
    )

    perception.direct_address = (
        True
    )

    perception.trigger_detected = (
        True
    )

    perception.should_reply = (
        True
    )

    perception.address_reason = (
        reason
    )

    return AddressUpgradeResult(

        changed=True,

        direct=True,

        reason=reason
    )


def format_address_upgrade_debug(
    result: AddressUpgradeResult
) -> str:

    return (

        "[ADDRESS UPGRADE] "
        f"v={CONVERSATION_UNDERSTANDING_VERSION} "
        f"changed={result.changed} "
        f"direct={result.direct} "
        f"reason={result.reason}"
    )


# =========================================================
# CHANNEL ITEM FORMAT
# =========================================================

def _format_item(
    item
) -> str:

    item_type = str(
        item.get(
            "type",
            ""
        )
    )

    username = str(
        item.get(
            "username",
            "Unbekannt"
        )
    )

    content = (
        _normalize(
            item.get(
                "content",
                ""
            )
        )
    )

    if len(
        content
    ) > 260:

        content = (
            content[:257]
            +
            "..."
        )

    if item_type == "bot":

        return (
            f"Evilnae: {content}"
        )

    reply_name = (
        item.get(
            "reply_to_name"
        )
    )

    if reply_name:

        return (
            f"{username} "
            f"[antwortet auf {reply_name}]: "
            f"{content}"
        )

    return (
        f"{username}: {content}"
    )


# =========================================================
# PREVIOUS ITEMS
# =========================================================

def _relevant_previous_items(
    channel_snapshot,
    *,
    current_user_id: Optional[str] = None,
    limit: int = 8
):

    if not channel_snapshot:

        return []

    # Current message is already last item.
    previous = list(
        channel_snapshot[:-1]
    )

    selected = []

    for item in reversed(
        previous
    ):

        item_type = str(
            item.get(
                "type",
                ""
            )
        )

        if item_type == "bot":

            selected.append(
                item
            )

        elif item_type == "user":

            item_user_id = str(
                item.get(
                    "user_id",
                    ""
                )
            )

            if (
                current_user_id is None
                or
                item_user_id
                ==
                str(
                    current_user_id
                )
                or
                len(
                    selected
                )
                <
                4
            ):

                selected.append(
                    item
                )

        if len(
            selected
        ) >= limit:

            break

    selected.reverse()

    return selected


# =========================================================
# REFERENCE / ELLIPSIS CONTEXT
# =========================================================

def build_reference_context(
    user_text: str,
    channel_snapshot,
    *,
    current_user_id: Optional[str] = None
) -> str:

    text = (
        _normalize(
            user_text
        )
    )

    if not text:

        return (
            "Keine besondere "
            "Reference-Resolution nötig."
        )

    context_dependent = bool(
        CONTEXT_DEPENDENT_PATTERN.search(
            text
        )
    )

    self_parallel = any(

        pattern.search(
            text
        )

        for pattern
        in SELF_PARALLEL_PATTERNS
    )

    inherit_predicate = any(

        pattern.search(
            text
        )

        for pattern
        in INHERIT_PREDICATE_PATTERNS
    )

    channel_here = bool(
        HERE_PATTERN.search(
            text
        )
    )

    if not (
        context_dependent
        or
        self_parallel
        or
        inherit_predicate
        or
        channel_here
    ):

        return (
            "Keine besondere "
            "Reference-Resolution nötig."
        )

    relevant_items = (
        _relevant_previous_items(

            channel_snapshot,

            current_user_id=(
                current_user_id
            ),

            limit=8
        )
    )

    if relevant_items:

        timeline = "\n".join(

            f"- {_format_item(item)}"

            for item
            in relevant_items
        )

    else:

        timeline = (
            "- Kein ausreichender "
            "lokaler Verlauf."
        )

    rules = []

    # -----------------------------------------------------
    # "Würdest du das auch probieren?"
    # -----------------------------------------------------

    if self_parallel:

        rules.append(
            (
                "Die aktuelle Formulierung fragt sehr "
                "wahrscheinlich danach, ob EVILNAE SELBST "
                "dieselbe zuvor genannte Sache "
                "tun/probieren würde. "
                "Nicht erneut beantworten, "
                "ob der User sie tun wird."
            )
        )

    # -----------------------------------------------------
    # "Und meine?"
    # -----------------------------------------------------

    if inherit_predicate:

        rules.append(
            (
                "Die aktuelle Kurzfrage erbt "
                "Thema/Prädikat aus der unmittelbar "
                "vorherigen Frage. "
                "Nur das Subjekt bzw. "
                "der Besitzer wechselt."
            )
        )

    # -----------------------------------------------------
    # "Was ist hier los?"
    # -----------------------------------------------------

    if channel_here:

        rules.append(
            (
                '"hier" bedeutet in dieser Formulierung '
                "primär die aktuelle Discord-/Channel-"
                "Situation. "
                "Eine gleichzeitig erwähnte externe "
                "Tätigkeit (z.B. Flugsimulator) "
                "ist nicht automatisch die Ursache "
                "des Geschehens im Channel."
            )
        )

    if (
        context_dependent
        and
        not rules
    ):

        rules.append(
            (
                "Pronomen und Kurzreferenzen wie "
                "das/auch/da/so müssen gegen den "
                "lokalen Gesprächsverlauf aufgelöst "
                "werden, nicht isoliert."
            )
        )

    rules_text = "\n".join(

        f"- {rule}"

        for rule
        in rules
    )

    return f"""
[REFERENCE RESOLUTION v{CONVERSATION_UNDERSTANDING_VERSION}]

Die aktuelle Nachricht ist kontextabhängig.

AKTUELLE NACHRICHT:
{text}

RELEVANTER LOKALER THREAD:
{timeline}

BINDING RULES:
{rules_text}

Wenn mehrere Referenten möglich sind:
Bevorzuge die unmittelbarste,
grammatisch und sozial plausible Referenz.

Nicht einfach das letzte einzelne Nomen übernehmen.
""".strip()


# =========================================================
# CURRENT CONVERSATION EPISODE
# =========================================================

def build_episode_focus(
    channel_snapshot,
    *,
    limit: int = 12
) -> str:

    if not channel_snapshot:

        return (
            "Keine aktuelle "
            "Conversation Episode."
        )

    items = list(
        channel_snapshot[
            -limit:
        ]
    )

    timeline = "\n".join(

        f"- {_format_item(item)}"

        for item
        in items
    )

    return f"""
[CURRENT CONVERSATION EPISODE v{CONVERSATION_UNDERSTANDING_VERSION}]

Behandle die folgenden Nachrichten
als eine mögliche laufende soziale Situation,
nicht als isolierte Einzelprompts:

{timeline}

WICHTIG:

- Mehrere User können Teil derselben Episode sein.
- Eine Zwischenmeldung beendet einen Gesprächsstrang nicht automatisch.
- Trenne Geschehen IM DISCORD von Dingen,
  die ein User außerhalb des Channels gerade macht.
- Wenn eine neue Nachricht auf ein laufendes Bit/Event
  Bezug nimmt, nutze dieses gemeinsame Event.
""".strip()


# =========================================================
# PARTICIPATION HINT
# =========================================================

def build_participation_hint(
    perception,
    channel_snapshot,
    *,
    hanae_user_id: Optional[str] = None
) -> str:

    notes = []

    name_mentioned = bool(
        getattr(
            perception,
            "name_mentioned",
            False
        )
    )

    direct = bool(
        getattr(
            perception,
            "direct_address",
            False
        )
    )

    user_id = str(
        getattr(
            perception,
            "user_id",
            ""
        )
    )

    # -----------------------------------------------------
    # THIRD PERSON EVILNAE MENTION
    # -----------------------------------------------------

    if (
        name_mentioned
        and
        not direct
    ):

        notes.append(
            (
                "Evilnae ist Gegenstand der aktuellen "
                "Nachricht. Das ist ein echtes "
                "Relevanzsignal. Dritte Person bedeutet "
                "NICHT 'hat nichts mit Evilnae zu tun'. "
                "Sie muss trotzdem nicht zwangsläufig "
                "antworten."
            )
        )

    recent_items = list(
        channel_snapshot[-8:]
        if channel_snapshot
        else []
    )

    evilnae_recent = any(

        str(
            item.get(
                "type",
                ""
            )
        )
        ==
        "bot"

        for item
        in recent_items
    )

    # -----------------------------------------------------
    # HANAE + CURRENT EPISODE
    # -----------------------------------------------------

    if (
        hanae_user_id
        and
        user_id
        ==
        str(
            hanae_user_id
        )
        and
        evilnae_recent
    ):

        notes.append(
            (
                "Die aktuelle Person ist Hanae und "
                "Evilnae war im unmittelbaren "
                "Channel-Verlauf aktiv. "
                "Bewerte conversation_involvement "
                "daher anhand des Geschwister-/"
                "Episode-Kontexts, nicht nur danach, "
                "ob Hanae den Namen erneut direkt benutzt."
            )
        )

    if not notes:

        return (
            "Keine zusätzlichen "
            "Participation-Signale."
        )

    return (

        f"[PARTICIPATION CONTEXT "
        f"v{CONVERSATION_UNDERSTANDING_VERSION}]\n"

        +

        "\n".join(
            f"- {note}"
            for note
            in notes
        )
    )


# =========================================================
# QUESTION SHAPE FAIL-SAFE
# =========================================================

def _clean_salvage(
    text: str
) -> str:

    text = (
        _normalize(
            text
        )
    )

    text = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        text
    )

    text = re.sub(
        r"^[,;:\-–—]+\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*[,;:\-–—]+\s*$",
        "",
        text
    )

    return text.strip()


def _remove_questions(
    answer: str
) -> str:

    text = (
        _normalize(
            answer
        )
    )

    if "?" not in text:

        return text

    chunks = (
        text.split(
            "?"
        )
    )

    kept = []

    for (
        index,
        chunk
    ) in enumerate(
        chunks
    ):

        chunk = (
            chunk.strip()
        )

        # Final non-question remainder.
        if (
            index
            ==
            len(
                chunks
            )
            -
            1
        ):

            if chunk:

                kept.append(
                    chunk
                )

            continue

        if not chunk:

            continue

        starts = list(
            QUESTION_START_PATTERN.finditer(
                chunk
            )
        )

        if starts:

            start = (
                starts[-1]
                .start()
            )

            prefix = (
                chunk[
                    :start
                ]
                .strip()
            )

            # Preserve substantive statement
            # before the illegal question.
            if len(
                re.findall(
                    r"[A-Za-zÄÖÜäöüß0-9]+",
                    prefix
                )
            ) >= 3:

                kept.append(
                    prefix
                )

            continue

        word_count = len(
            re.findall(
                r"[A-Za-zÄÖÜäöüß0-9]+",
                chunk
            )
        )

        # Tiny chunks are probably pure questions.
        if word_count <= 4:

            continue

    result = (
        " ".join(
            kept
        )
    )

    return (
        _clean_salvage(
            result
        )
    )


def salvage_question_shape(
    answer: str,
    *,
    allow_question: bool
) -> str:

    text = (
        _normalize(
            answer
        )
    )

    if not text:

        return ""

    # -----------------------------------------------------
    # NO QUESTION ALLOWED
    # -----------------------------------------------------

    if not allow_question:

        return (
            _remove_questions(
                text
            )
        )

    # -----------------------------------------------------
    # ONE QUESTION ALLOWED
    # -----------------------------------------------------

    first_question = (
        text.find(
            "?"
        )
    )

    if first_question < 0:

        return text

    prefix = (
        text[
            :first_question
            +
            1
        ]
        .strip()
    )

    rest = (
        text[
            first_question
            +
            1:
        ]
        .strip()
    )

    if not rest:

        return prefix

    declarative_rest = (
        _remove_questions(
            rest
        )
    )

    if declarative_rest:

        return (
            _clean_salvage(
                f"{prefix} "
                f"{declarative_rest}"
            )
        )

    return prefix


# =========================================================
# GARBLED OUTPUT GUARD
# =========================================================

def analyze_garbled_output(
    text: str
) -> GarbledAnalysis:

    text = (
        _normalize(
            text
        )
    )

    if not text:

        return GarbledAnalysis(

            garbled=True,

            score=4,

            matches=[
                "empty_output"
            ]
        )

    matches = []

    score = 0

    # -----------------------------------------------------
    # COMMA FRAGMENT CHAIN
    #
    # "hast, keine, ahnung"
    # "also, jetzt, sehen, machen"
    # -----------------------------------------------------

    comma_segments = [

        segment.strip()

        for segment
        in text.split(
            ","
        )

        if segment.strip()
    ]

    if len(
        comma_segments
    ) >= 3:

        short_segments = sum(

            1

            for segment
            in comma_segments

            if len(
                re.findall(
                    r"[A-Za-zÄÖÜäöüß0-9]+",
                    segment
                )
            ) <= 2
        )

        if short_segments >= 3:

            matches.append(
                "comma_fragment_chain"
            )

            score += 4

    # -----------------------------------------------------
    # ISOLATED WORD CHAIN
    # -----------------------------------------------------

    if re.search(
        (
            r"(?:"
            r"\b[A-Za-zÄÖÜäöüß]+\b"
            r"\s*,\s*"
            r"){3,}"
        ),
        text
    ):

        matches.append(
            "isolated_word_chain"
        )

        score += 3

    # -----------------------------------------------------
    # KNOWN BROKEN CASE CONSTRUCTION
    #
    # "der dich lange das leben schwer gemacht hat"
    # -----------------------------------------------------

    if re.search(
        (
            r"\bder\s+dich\b"
            r".{0,55}"
            r"\bdas\s+leben\s+"
            r"schwer\s+gemacht\b"
        ),
        text,
        flags=re.IGNORECASE
    ):

        matches.append(
            "broken_case_construction"
        )

        score += 3

    # -----------------------------------------------------
    # PUNCTUATION CHAIN
    # -----------------------------------------------------

    if re.search(
        r"[,;:]\s*[,;:]\s*[,;:]",
        text
    ):

        matches.append(
            "punctuation_chain"
        )

        score += 3

    # -----------------------------------------------------
    # COMMA DENSITY
    # -----------------------------------------------------

    words = (
        re.findall(
            r"[A-Za-zÄÖÜäöüß0-9]+",
            text
        )
    )

    comma_count = (
        text.count(
            ","
        )
    )

    if (
        comma_count >= 4
        and
        len(
            words
        ) <= 12
    ):

        matches.append(
            "comma_density"
        )

        score += 2

    return GarbledAnalysis(

        garbled=(
            score >= 3
        ),

        score=score,

        matches=list(
            dict.fromkeys(
                matches
            )
        )
    )


def format_garbled_debug(
    analysis: GarbledAnalysis
) -> str:

    return (

        "[GARBLED OUTPUT] "
        f"v={CONVERSATION_UNDERSTANDING_VERSION} "
        f"garbled={analysis.garbled} "
        f"score={analysis.score} "
        f"matches={analysis.matches}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _FakePerception:

    def __init__(
        self,
        text
    ):

        self.raw_content = (
            text
        )

        self.trigger_text = (
            text
        )

        self.text = (
            text
        )

        self.direct_address = (
            False
        )

        self.bot_mentioned = (
            False
        )

        self.replied_to_bot = (
            False
        )

        self.name_mentioned = bool(
            EVIL_NAME_PATTERN.search(
                text
            )
        )

        self.trigger_detected = (
            False
        )

        self.should_reply = (
            False
        )

        self.address_reason = (
            "ambiguous_name_mention"
        )

        self.user_id = (
            "1"
        )


def _self_test():

    tests = []

    # -----------------------------------------------------
    # 1. END VOCATIVE
    # -----------------------------------------------------

    perception = _FakePerception(
        (
            "ich bin dann weg, "
            "schönen tag dir noch evil"
        )
    )

    result = (
        upgrade_perception_addressing(
            perception
        )
    )

    tests.append(
        (
            "end-address with dir becomes direct",

            (
                result.changed
                and
                perception.should_reply
            )
        )
    )

    # -----------------------------------------------------
    # 2. WOW EVIL WOW
    # -----------------------------------------------------

    perception = _FakePerception(
        "WOW EVIL WOW"
    )

    result = (
        upgrade_perception_addressing(
            perception
        )
    )

    tests.append(
        (
            "exclamatory name call becomes direct",

            (
                result.changed
                and
                perception.should_reply
            )
        )
    )

    # -----------------------------------------------------
    # 3. THIRD PERSON STAYS THIRD PERSON
    # -----------------------------------------------------

    perception = _FakePerception(
        "Arme evil"
    )

    result = (
        upgrade_perception_addressing(
            perception
        )
    )

    tests.append(
        (
            "third-person sympathy remains non-direct",

            (
                not result.changed
                and
                not perception.should_reply
            )
        )
    )

    # -----------------------------------------------------
    # LOCAL TIMELINE
    # -----------------------------------------------------

    timeline = [

        {
            "type": "user",
            "username": "Chris",
            "user_id": "1",
            "content": (
                "Evil was hältst du von "
                "Leberwurst mit Senf"
            ),
        },

        {
            "type": "bot",
            "username": "Evilnae",
            "user_id": "EVILNAE",
            "content": (
                "die combo ist zumindest mutig"
            ),
        },

        {
            "type": "user",
            "username": "Chris",
            "user_id": "1",
            "content": (
                "ich werde das die tage probieren"
            ),
        },

        {
            "type": "bot",
            "username": "Evilnae",
            "user_id": "EVILNAE",
            "content": (
                "viel glück damit"
            ),
        },

        {
            "type": "user",
            "username": "Chris",
            "user_id": "1",
            "content": (
                "Würdest du das auch probieren"
            ),
        },
    ]

    # -----------------------------------------------------
    # 4. SELF-PARALLEL REFERENCE
    # -----------------------------------------------------

    reference = (
        build_reference_context(

            "Würdest du das auch probieren",

            timeline,

            current_user_id="1"
        )
    )

    tests.append(
        (
            "self-parallel reference detected",

            (
                "EVILNAE SELBST"
                in reference
            )
        )
    )

    # -----------------------------------------------------
    # 5. HERE = CHANNEL
    # -----------------------------------------------------

    reference = (
        build_reference_context(

            "was ist hier los",

            timeline,

            current_user_id="1"
        )
    )

    tests.append(
        (
            "channel-here reference detected",

            (
                "Discord-/Channel-Situation"
                in reference
            )
        )
    )

    # -----------------------------------------------------
    # 6. QUESTION FAILSAFE
    # -----------------------------------------------------

    salvaged = (
        salvage_question_shape(

            (
                "uhhh, pizza? "
                "jetzt hast du's geschafft, "
                "dass ich hungrig bin. "
                "lief's gut mit der Bestellung?"
            ),

            allow_question=False
        )
    )

    tests.append(
        (
            "question failsafe keeps declarative core",

            (
                "hungrig"
                in salvaged.lower()
                and
                "?"
                not in salvaged
            )
        )
    )

    # -----------------------------------------------------
    # 7. GARBLED CHAIN
    # -----------------------------------------------------

    garbled = (
        analyze_garbled_output(
            (
                "also, jetzt, befehlshab, "
                "sehen, durchhältst, rumlaberst"
            )
        )
    )

    tests.append(
        (
            "comma fragment chain blocked",

            garbled.garbled
        )
    )

    # -----------------------------------------------------
    # 8. SHORT BROKEN CHAIN
    # -----------------------------------------------------

    garbled = (
        analyze_garbled_output(
            "hast, keine, ahnung"
        )
    )

    tests.append(
        (
            "short broken comma chain blocked",

            garbled.garbled
        )
    )

    # -----------------------------------------------------
    # 9. NORMAL SHORT REPLY
    # -----------------------------------------------------

    clean = (
        analyze_garbled_output(
            (
                "jo, das klingt tatsächlich "
                "ziemlich cursed."
            )
        )
    )

    tests.append(
        (
            "normal short reply allowed",

            not clean.garbled
        )
    )

    # -----------------------------------------------------
    # 10. BROKEN BOSS GRAMMAR
    # -----------------------------------------------------

    broken = (
        analyze_garbled_output(
            (
                "congrats, welch ein boss, "
                "der dich lange das leben "
                "schwer gemacht hat, ja?"
            )
        )
    )

    tests.append(
        (
            "broken boss case construction blocked",

            broken.garbled
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
        f"CONVERSATION UNDERSTANDING "
        f"v{CONVERSATION_UNDERSTANDING_VERSION} TEST"
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
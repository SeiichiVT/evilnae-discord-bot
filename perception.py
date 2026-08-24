import re
from dataclasses import dataclass, field
from typing import Optional

import discord


# =========================================================
# PERCEPTION VERSION
# =========================================================

PERCEPTION_VERSION = "2.0.1"


# =========================================================
# REGEX
# =========================================================

CUSTOM_EMOJI_PATTERN = re.compile(
    r"<(?P<animated>a?):"
    r"(?P<name>[A-Za-z0-9_]+):"
    r"(?P<id>\d+)>"
)

USER_MENTION_PATTERN = re.compile(
    r"<@!?(?P<id>\d+)>"
)

ROLE_MENTION_PATTERN = re.compile(
    r"<@&(?P<id>\d+)>"
)

CHANNEL_MENTION_PATTERN = re.compile(
    r"<#(?P<id>\d+)>"
)


# =========================================================
# KNOWN NON-EVILNAE PHRASES
# =========================================================

NON_EVILNAE_NAME_PATTERNS = [

    re.compile(
        r"\bresident\s+evil\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bevil\s+dead\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bthe\s+evil\s+within\b",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# GREETING / VOCATIVE LEADS
# =========================================================

GREETING_LEADS = {

    "hallo",
    "hi",
    "hey",
    "ey",
    "yo",

    "moin",
    "servus",

    "tag",

    "guten tag",
    "guten morgen",
    "guten abend",

    "morgen",

    "also",
    "so",
    "na",

    "okay",
    "ok",
}


# =========================================================
# ADDRESS MODIFIERS
# =========================================================

ADDRESS_MODIFIERS = {

    "meine",
    "mein",

    "liebe",
    "lieber",

    "kleine",
    "kleiner",

    "gute",
    "guter",

    "werte",
    "werter",
}


# =========================================================
# DIRECT FOLLOWERS
#
# Wort direkt NACH Evil/Evilnae.
#
# Evil was denkst du?
# Evil kannst du...
# Evil nerv mich nicht
# =========================================================

DIRECT_FOLLOWERS = {

    # -----------------------------------------------------
    # QUESTION WORDS
    # -----------------------------------------------------

    "was",
    "wer",
    "wie",
    "warum",
    "wieso",
    "wann",
    "wo",

    "welche",
    "welcher",
    "welches",


    # -----------------------------------------------------
    # SECOND PERSON
    # -----------------------------------------------------

    "du",
    "dir",
    "dich",
    "dein",
    "deine",
    "deiner",
    "deinen",
    "deinem",


    # -----------------------------------------------------
    # QUESTIONS / ACTIONS
    # -----------------------------------------------------

    "kannst",
    "könntest",
    "koenntest",

    "willst",
    "würdest",
    "wuerdest",

    "hast",
    "bist",

    "magst",

    "meinst",
    "denkst",
    "findest",

    "weißt",
    "weisst",

    "darfst",
    "sollst",

    "sag",
    "sagst",

    "erzähl",
    "erzaehl",
    "erzählst",
    "erzaehlst",

    "mach",
    "machst",

    "komm",

    "hör",
    "hoer",

    "guck",
    "schau",

    "hilf",

    "nenn",
    "nennst",

    "lass",
    "lässt",
    "laesst",

    "spiel",
    "spielst",

    # -----------------------------------------------------
    # v2.0.1
    #
    # "Ne Evil nerv mich bitte nicht"
    #
    # Imperativ/direct action.
    #
    # "nervt" bleibt dagegen unten
    # ein Third-Person-Predicate:
    #
    # "Evil nervt Hanae"
    # -----------------------------------------------------

    "nerv",
}


# =========================================================
# THIRD PERSON PREDICATES
#
# Evil sagt da was anderes.
# Evil ist heute komisch.
# Evil nervt Hanae.
#
# -> ÜBER Evilnae gesprochen.
# =========================================================

THIRD_PERSON_PREDICATES = {

    "ist",
    "war",
    "wäre",
    "waere",

    "hat",
    "hatte",

    "sagt",
    "sagte",

    "meint",
    "meinte",

    "wird",
    "wurde",

    "bekommt",
    "bekam",

    "braucht",

    "weiß",
    "weiss",

    "kennt",

    "liebt",
    "hasst",

    "stinkt",

    "nervt",

    "glaubt",

    "denkt",

    "macht",

    "geht",

    "kommt",

    "schläft",
    "schlaeft",

    "wohnt",

    "spielt",

    "guckt",

    "schaut",

    "übernimmt",
    "uebernimmt",

    "lernt",

    "entwickelt",

    "darf",

    "soll",

    "kann",

    "muss",

    "will",

    "findet",

    "ignoriert",

    "schreibt",

    "antwortet",

    "redet",

    "plant",
}


# =========================================================
# END-OF-SENTENCE ADDRESS HINTS
# =========================================================

END_ADDRESS_HINTS = {

    "was",
    "wer",
    "wie",
    "warum",
    "wieso",
    "wann",
    "wo",

    "meinst",
    "denkst",
    "findest",

    "hältst",
    "haelst",

    "willst",

    "kannst",

    "würdest",
    "wuerdest",

    "hast",
    "bist",

    "weißt",
    "weisst",

    "sag",
    "sagst",

    "pläne",
    "plaene",

    "meinung",

    "idee",
}


# =========================================================
# DIRECT WISH / SOCIAL ADDRESS
# =========================================================

DIRECT_WISH_PATTERNS = [

    re.compile(
        r"\bgute\s+besserung\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bguten\s+morgen\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bguten\s+abend\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bgute\s+nacht\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bschlaf\s+gut\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmorgen\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmoin\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhallo\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhi\s*$",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhey\s*$",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# DATA OBJECTS
# =========================================================

@dataclass
class ParsedEmoji:

    name: str

    emoji_id: str

    animated: bool

    raw: str


@dataclass
class ReplyInfo:

    message_id: Optional[str] = None

    author_id: Optional[str] = None

    author_name: Optional[str] = None

    content: Optional[str] = None

    author_is_bot: bool = False


@dataclass
class AddressingResult:

    name_mentioned: bool = False

    direct_address: bool = False

    reason: str = "no_name"

    name_spans: list[tuple[int, int]] = field(
        default_factory=list
    )

    direct_spans: list[tuple[int, int]] = field(
        default_factory=list
    )


@dataclass
class PerceivedMessage:

    # -----------------------------------------------------
    # AUTHOR
    # -----------------------------------------------------

    user_id: str

    username: str

    # -----------------------------------------------------
    # CHANNEL
    # -----------------------------------------------------

    channel_id: str

    # -----------------------------------------------------
    # ORIGINAL MESSAGE
    # -----------------------------------------------------

    raw_content: str

    # -----------------------------------------------------
    # CLEAN TEXT
    # -----------------------------------------------------

    text: str

    # -----------------------------------------------------
    # TEXT USED FOR ADDRESS DETECTION
    # -----------------------------------------------------

    trigger_text: str

    # -----------------------------------------------------
    # EMOJIS
    # -----------------------------------------------------

    custom_emojis: list[ParsedEmoji] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # MESSAGE FLAGS
    # -----------------------------------------------------

    is_emoji_only: bool = False

    has_text: bool = False

    # -----------------------------------------------------
    # ADDRESSING
    # -----------------------------------------------------

    bot_mentioned: bool = False

    direct_address: bool = False

    name_mentioned: bool = False

    address_reason: str = "none"

    # -----------------------------------------------------
    # LEGACY COMPATIBILITY
    #
    # trigger_detected == direct_address
    # -----------------------------------------------------

    trigger_detected: bool = False

    replied_to_bot: bool = False

    should_reply: bool = False

    # -----------------------------------------------------
    # REPLY
    # -----------------------------------------------------

    reply: Optional[ReplyInfo] = None


# =========================================================
# CUSTOM EMOJI EXTRACTION
# =========================================================

def extract_custom_emojis(
    content: str
) -> list[ParsedEmoji]:

    emojis = []

    for match in (
        CUSTOM_EMOJI_PATTERN.finditer(
            content or ""
        )
    ):

        emojis.append(
            ParsedEmoji(

                name=(
                    match.group(
                        "name"
                    )
                ),

                emoji_id=(
                    match.group(
                        "id"
                    )
                ),

                animated=(
                    match.group(
                        "animated"
                    )
                    == "a"
                ),

                raw=(
                    match.group(0)
                )
            )
        )

    return emojis


# =========================================================
# REMOVE CUSTOM EMOJIS
# =========================================================

def remove_custom_emojis(
    content: str
) -> str:

    if not content:

        return ""

    return CUSTOM_EMOJI_PATTERN.sub(
        " ",
        content
    )


# =========================================================
# NORMALIZE SPACING
# =========================================================

def normalize_spacing(
    text: str
) -> str:

    if not text:

        return ""

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# NORMALIZE STRETCHED LEAD WORDS
# =========================================================

def normalize_stretched_lead_text(
    text: str
) -> str:

    if not text:

        return ""

    words = (
        text.split()
    )

    normalized_words = []

    for word in words:

        normalized_word = re.sub(
            r"(.)\1{2,}",
            r"\1",
            word,
            flags=re.IGNORECASE
        )

        normalized_words.append(
            normalized_word
        )

    return " ".join(
        normalized_words
    )


# =========================================================
# REMOVE BOT MENTION
# =========================================================

def remove_bot_mention(
    text: str,
    bot_id: int
) -> str:

    if not text:

        return ""

    text = text.replace(
        f"<@{bot_id}>",
        " "
    )

    text = text.replace(
        f"<@!{bot_id}>",
        " "
    )

    return normalize_spacing(
        text
    )


# =========================================================
# BUILD NAME PATTERN
# =========================================================

def build_trigger_pattern(
    trigger_words: list[str]
) -> str:

    sorted_triggers = sorted(
        trigger_words,
        key=len,
        reverse=True
    )

    patterns = []

    for trigger in sorted_triggers:

        escaped = (
            re.escape(
                trigger
            )
        )

        escaped = escaped.replace(
            r"\ ",
            r"\s+"
        )

        patterns.append(
            escaped
        )

    return "|".join(
        patterns
    )


# =========================================================
# NON-EVILNAE SPANS
# =========================================================

def get_non_evilnae_spans(
    text: str
) -> list[tuple[int, int]]:

    spans = []

    for pattern in (
        NON_EVILNAE_NAME_PATTERNS
    ):

        for match in (
            pattern.finditer(
                text or ""
            )
        ):

            spans.append(
                (
                    match.start(),
                    match.end()
                )
            )

    return spans


# =========================================================
# SPAN OVERLAP
# =========================================================

def spans_overlap(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int
) -> bool:

    return (
        first_start < second_end
        and
        second_start < first_end
    )


# =========================================================
# FIND EVILNAE NAME SPANS
# =========================================================

def find_name_spans(
    text: str,
    trigger_words: list[str]
) -> list[tuple[int, int]]:

    if not text:

        return []

    trigger_pattern = (
        build_trigger_pattern(
            trigger_words
        )
    )

    pattern = re.compile(
        rf"(?<![\w])"
        rf"(?:{trigger_pattern})"
        rf"(?![\w])",
        flags=re.IGNORECASE
    )

    excluded_spans = (
        get_non_evilnae_spans(
            text
        )
    )

    valid_spans = []

    for match in (
        pattern.finditer(
            text
        )
    ):

        match_start = (
            match.start()
        )

        match_end = (
            match.end()
        )

        excluded = False

        for (
            excluded_start,
            excluded_end
        ) in excluded_spans:

            if spans_overlap(
                match_start,
                match_end,
                excluded_start,
                excluded_end
            ):

                excluded = True

                break

        if excluded:

            continue

        valid_spans.append(
            (
                match_start,
                match_end
            )
        )

    return valid_spans


# =========================================================
# WORD HELPERS
# =========================================================

def first_word_after(
    text: str
) -> str:

    if not text:

        return ""

    cleaned = re.sub(
        r"^[\s,;:!?.\-–—]+",
        "",
        text
    )

    match = re.search(
        r"[A-Za-zÄÖÜäöüß]+",
        cleaned
    )

    if not match:

        return ""

    return (
        match.group(0)
        .lower()
    )


def words_before(
    text: str,
    limit: int = 12
) -> list[str]:

    words = re.findall(
        r"[A-Za-zÄÖÜäöüß]+",
        text.lower()
    )

    return (
        words[
            -limit:
        ]
    )


# =========================================================
# SECOND PERSON DETECTION
# =========================================================

def contains_second_person(
    text: str
) -> bool:

    words = set(
        re.findall(
            r"[A-Za-zÄÖÜäöüß]+",
            text.lower()
        )
    )

    second_person_words = {

        "du",
        "dir",
        "dich",

        "dein",
        "deine",
        "deiner",
        "deinen",
        "deinem",

        "bist",
        "hast",

        "kannst",
        "könntest",
        "koenntest",

        "willst",

        "würdest",
        "wuerdest",

        "magst",

        "meinst",

        "denkst",

        "findest",

        "weißt",
        "weisst",

        "sollst",

        "darfst",
    }

    return bool(
        words
        &
        second_person_words
    )


# =========================================================
# GREETING / VOCATIVE BEFORE NAME
# =========================================================

def has_greeting_before(
    before_text: str
) -> bool:

    if not before_text:

        return False

    normalized = (
        normalize_stretched_lead_text(
            before_text.lower()
        )
    )

    normalized = re.sub(
        r"[,;:!?.\-–—]+$",
        "",
        normalized
    ).strip()

    words = (
        normalized.split()
    )

    if not words:

        return False

    tail_words = (
        words[
            -5:
        ]
    )

    while (
        tail_words
        and
        tail_words[-1]
        in ADDRESS_MODIFIERS
    ):

        tail_words.pop()

    if not tail_words:

        return False

    if (
        tail_words[-1]
        in GREETING_LEADS
    ):

        return True

    if len(
        tail_words
    ) >= 2:

        last_two = (
            tail_words[-2]
            + " "
            + tail_words[-1]
        )

        if (
            last_two
            in GREETING_LEADS
        ):

            return True

    return False


# =========================================================
# DIRECT WISH BEFORE NAME
# =========================================================

def has_direct_wish_before(
    before_text: str
) -> bool:

    if not before_text:

        return False

    normalized = (
        normalize_spacing(
            before_text
        )
    )

    normalized = re.sub(
        r"[,;:!?.\-–—]+$",
        "",
        normalized
    ).strip()

    for pattern in (
        DIRECT_WISH_PATTERNS
    ):

        if pattern.search(
            normalized
        ):

            return True

    return False


# =========================================================
# QUESTION HINT BEFORE FINAL NAME
# =========================================================

def has_end_address_question_hint(
    before_text: str
) -> bool:

    words = set(
        words_before(
            before_text,
            limit=18
        )
    )

    if (
        words
        &
        END_ADDRESS_HINTS
    ):

        return True

    if contains_second_person(
        before_text
    ):

        return True

    return False


# =========================================================
# PUNCTUATION AFTER NAME
# =========================================================

def punctuation_after_name(
    after_text: str
) -> str:

    if not after_text:

        return ""

    match = re.match(
        r"\s*([,;:!?\-–—.])",
        after_text
    )

    if not match:

        return ""

    return (
        match.group(1)
    )


# =========================================================
# SUBSTANTIVE TEXT AFTER NAME
# =========================================================

def has_substantive_text(
    text: str
) -> bool:

    return bool(
        re.search(
            r"[A-Za-zÄÖÜäöüß0-9]",
            text or ""
        )
    )


# =========================================================
# CLASSIFY SINGLE NAME OCCURRENCE
# =========================================================

def classify_name_span(
    text: str,
    start: int,
    end: int
) -> tuple[
    bool,
    str
]:

    before = (
        text[
            :start
        ]
    )

    after = (
        text[
            end:
        ]
    )

    before_stripped = (
        before.strip()
    )

    first_after = (
        first_word_after(
            after
        )
    )

    punctuation = (
        punctuation_after_name(
            after
        )
    )

    at_start = (
        not bool(
            before_stripped
        )
    )

    at_end = (
        not has_substantive_text(
            after
        )
    )

    # =====================================================
    # 1. GREETING / VOCATIVE
    # =====================================================

    if has_greeting_before(
        before
    ):

        return (
            True,
            "greeting_vocative"
        )

    # =====================================================
    # 2. DIRECT SOCIAL WISH
    # =====================================================

    if has_direct_wish_before(
        before
    ):

        return (
            True,
            "direct_wish"
        )

    # =====================================================
    # 3. NAME AT START
    # =====================================================

    if at_start:

        if punctuation in {
            ",",
            ":",
            "-",
            "–",
            "—",
        }:

            return (
                True,
                "start_vocative_punctuation"
            )

        if (
            at_end
            and
            punctuation
            in {
                "?",
                "!",
            }
        ):

            return (
                True,
                "name_only_address"
            )

        if (
            first_after
            in DIRECT_FOLLOWERS
        ):

            return (
                True,
                "start_direct_follower"
            )

        if (
            first_after
            in THIRD_PERSON_PREDICATES
        ):

            return (
                False,
                "third_person_subject"
            )

        return (
            True,
            "start_name_default"
        )

    # =====================================================
    # 4. NAME AT END
    # =====================================================

    if at_end:

        before_without_spaces = (
            before.rstrip()
        )

        if (
            before_without_spaces.endswith(
                ","
            )
        ):

            return (
                True,
                "end_vocative_comma"
            )

        if has_end_address_question_hint(
            before
        ):

            return (
                True,
                "end_question_address"
            )

        if (
            punctuation
            == "?"
            and
            (
                "?"
                in text
                or
                len(
                    words_before(
                        before,
                        limit=20
                    )
                )
                <= 10
            )
        ):

            return (
                True,
                "end_question_vocative"
            )

        return (
            False,
            "end_name_mention"
        )

    # =====================================================
    # 5. NAME IN MIDDLE
    # =====================================================

    if punctuation in {
        ",",
        ":",
        "-",
        "–",
        "—",
    }:

        return (
            True,
            "middle_vocative_punctuation"
        )

    if (
        first_after
        in DIRECT_FOLLOWERS
    ):

        return (
            True,
            "middle_direct_follower"
        )

    if (
        first_after
        in THIRD_PERSON_PREDICATES
    ):

        return (
            False,
            "middle_third_person_subject"
        )

    return (
        False,
        "ambiguous_name_mention"
    )


# =========================================================
# CLASSIFY ADDRESSING
# =========================================================

def classify_addressing(
    text: str,
    trigger_words: list[str]
) -> AddressingResult:

    text = (
        normalize_spacing(
            text or ""
        )
    )

    if not text:

        return (
            AddressingResult()
        )

    name_spans = (
        find_name_spans(
            text,
            trigger_words
        )
    )

    if not name_spans:

        return (
            AddressingResult(
                name_mentioned=False,
                direct_address=False,
                reason="no_name",
                name_spans=[],
                direct_spans=[]
            )
        )

    direct_spans = []

    reasons = []

    for (
        start,
        end
    ) in name_spans:

        (
            is_direct,
            reason
        ) = (
            classify_name_span(
                text,
                start,
                end
            )
        )

        reasons.append(
            reason
        )

        if is_direct:

            direct_spans.append(
                (
                    start,
                    end
                )
            )

    direct_address = bool(
        direct_spans
    )

    if direct_address:

        direct_reason = next(
            (
                reason
                for (
                    reason,
                    span
                ) in zip(
                    reasons,
                    name_spans
                )
                if span
                in direct_spans
            ),
            "direct_name"
        )

        result_reason = (
            direct_reason
        )

    else:

        result_reason = (
            reasons[0]
            if reasons
            else
            "name_mention"
        )

    return (
        AddressingResult(

            name_mentioned=True,

            direct_address=(
                direct_address
            ),

            reason=(
                result_reason
            ),

            name_spans=(
                name_spans
            ),

            direct_spans=(
                direct_spans
            )
        )
    )


# =========================================================
# LEGACY TRIGGER DETECTION
# =========================================================

def detect_trigger(
    content_without_emojis: str,
    trigger_words: list[str]
) -> bool:

    addressing = (
        classify_addressing(
            content_without_emojis,
            trigger_words
        )
    )

    return (
        addressing.direct_address
    )


# =========================================================
# NAME MENTION DETECTION
# =========================================================

def detect_name_mention(
    content_without_emojis: str,
    trigger_words: list[str]
) -> bool:

    addressing = (
        classify_addressing(
            content_without_emojis,
            trigger_words
        )
    )

    return (
        addressing.name_mentioned
    )


# =========================================================
# REMOVE DIRECT ADDRESS ONLY
# =========================================================

def remove_direct_address(
    text: str,
    direct_spans: list[
        tuple[int, int]
    ]
) -> str:

    if not text:

        return ""

    if not direct_spans:

        return normalize_spacing(
            text
        )

    result = (
        text
    )

    for (
        start,
        end
    ) in reversed(
        direct_spans
    ):

        result = (
            result[:start]
            + " "
            + result[end:]
        )

    result = re.sub(
        r"[ \t]+",
        " ",
        result
    )

    result = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        result
    )

    result = re.sub(
        r"\s*[-–—]\s*",
        " - ",
        result
    )

    result = re.sub(
        r",\s*,",
        ",",
        result
    )

    result = normalize_spacing(
        result
    )

    result = re.sub(
        r"^[,;:\-–—]+\s*",
        "",
        result
    ).strip()

    return result


# =========================================================
# LEGACY REMOVE TRIGGER ADDRESS
# =========================================================

def remove_trigger_address(
    text: str,
    trigger_words: list[str]
) -> str:

    if not text:

        return ""

    addressing = (
        classify_addressing(
            text,
            trigger_words
        )
    )

    return (
        remove_direct_address(
            text,
            addressing.direct_spans
        )
    )


# =========================================================
# EMOJI ONLY DETECTION
# =========================================================

def detect_emoji_only(
    raw_content: str
) -> bool:

    if not raw_content:

        return False

    custom_emojis = (
        extract_custom_emojis(
            raw_content
        )
    )

    if not custom_emojis:

        return False

    without_custom = (
        remove_custom_emojis(
            raw_content
        )
    )

    without_custom = (
        normalize_spacing(
            without_custom
        )
    )

    return not bool(
        without_custom
    )


# =========================================================
# REPLY RESOLUTION
# =========================================================

async def resolve_reply_info(
    message: discord.Message,
    bot: discord.Client
) -> Optional[ReplyInfo]:

    if not message.reference:

        return None

    resolved = (
        message.reference.resolved
    )

    reply_message = None

    if isinstance(
        resolved,
        discord.Message
    ):

        reply_message = (
            resolved
        )

    else:

        message_id = (
            message.reference.message_id
        )

        if not message_id:

            return None

        try:

            reply_message = (
                await message.channel.fetch_message(
                    message_id
                )
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):

            return ReplyInfo(
                message_id=str(
                    message_id
                )
            )

    if not reply_message:

        return None

    return ReplyInfo(

        message_id=str(
            reply_message.id
        ),

        author_id=str(
            reply_message.author.id
        ),

        author_name=(
            reply_message.author.display_name
        ),

        content=(
            reply_message.content[:1000]
            if reply_message.content
            else ""
        ),

        author_is_bot=(
            bot.user is not None
            and
            reply_message.author.id
            == bot.user.id
        )
    )


# =========================================================
# MAIN PERCEPTION FUNCTION
# =========================================================

async def perceive_message(
    message: discord.Message,
    bot: discord.Client,
    trigger_words: list[str]
) -> PerceivedMessage:

    raw_content = (
        message.content
        or ""
    )

    user_id = str(
        message.author.id
    )

    username = (
        message.author.display_name
    )

    channel_id = str(
        message.channel.id
    )

    # -----------------------------------------------------
    # CUSTOM EMOJIS
    # -----------------------------------------------------

    custom_emojis = (
        extract_custom_emojis(
            raw_content
        )
    )

    # -----------------------------------------------------
    # TEXT WITHOUT CUSTOM EMOJIS
    # -----------------------------------------------------

    no_emojis = (
        remove_custom_emojis(
            raw_content
        )
    )

    no_emojis = (
        normalize_spacing(
            no_emojis
        )
    )

    # -----------------------------------------------------
    # DISCORD BOT MENTION
    # -----------------------------------------------------

    bot_mentioned = False

    if bot.user is not None:

        bot_mentioned = (
            bot.user
            in message.mentions
        )

    # -----------------------------------------------------
    # ADDRESSING
    # -----------------------------------------------------

    addressing = (
        classify_addressing(
            no_emojis,
            trigger_words
        )
    )

    direct_address = (
        addressing.direct_address
    )

    name_mentioned = (
        addressing.name_mentioned
    )

    # -----------------------------------------------------
    # LEGACY TRIGGER
    # -----------------------------------------------------

    trigger_detected = (
        direct_address
    )

    # -----------------------------------------------------
    # REPLY
    # -----------------------------------------------------

    reply = (
        await resolve_reply_info(
            message,
            bot
        )
    )

    replied_to_bot = bool(
        reply
        and
        reply.author_is_bot
    )

    # -----------------------------------------------------
    # CLEAN TEXT
    # -----------------------------------------------------

    clean_text = (
        no_emojis
    )

    if bot.user is not None:

        clean_text = (
            remove_bot_mention(
                clean_text,
                bot.user.id
            )
        )

    if direct_address:

        clean_addressing = (
            classify_addressing(
                clean_text,
                trigger_words
            )
        )

        clean_text = (
            remove_direct_address(
                clean_text,
                clean_addressing.direct_spans
            )
        )

    clean_text = (
        normalize_spacing(
            clean_text
        )
    )

    # -----------------------------------------------------
    # MESSAGE TYPE
    # -----------------------------------------------------

    is_emoji_only = (
        detect_emoji_only(
            raw_content
        )
    )

    has_text = bool(
        clean_text
    )

    # -----------------------------------------------------
    # SHOULD REPLY
    # -----------------------------------------------------

    should_reply = (

        direct_address

        or

        bot_mentioned

        or

        replied_to_bot
    )

    if (
        is_emoji_only
        and
        not bot_mentioned
        and
        not replied_to_bot
        and
        not direct_address
    ):

        should_reply = False

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    return PerceivedMessage(

        user_id=user_id,

        username=username,

        channel_id=channel_id,

        raw_content=raw_content,

        text=clean_text,

        trigger_text=no_emojis,

        custom_emojis=custom_emojis,

        is_emoji_only=is_emoji_only,

        has_text=has_text,

        bot_mentioned=bot_mentioned,

        direct_address=direct_address,

        name_mentioned=name_mentioned,

        address_reason=(
            addressing.reason
        ),

        trigger_detected=(
            trigger_detected
        ),

        replied_to_bot=(
            replied_to_bot
        ),

        should_reply=(
            should_reply
        ),

        reply=reply
    )


# =========================================================
# EMOJI CONTEXT FORMAT
# =========================================================

def format_emoji_context(
    perception: PerceivedMessage
) -> str:

    if not perception.custom_emojis:

        return (
            "Keine Discord-Custom-Emotes "
            "in dieser Nachricht."
        )

    lines = []

    for emoji in (
        perception.custom_emojis
    ):

        animation_label = (
            "animiert"
            if emoji.animated
            else "statisch"
        )

        lines.append(
            f"- {emoji.name} "
            f"(Discord-Custom-Emote, "
            f"{animation_label}, "
            f"ID {emoji.emoji_id})"
        )

    lines.append(
        ""
    )

    lines.append(
        "WICHTIG: Die Emote-Namen sind "
        "keine wörtlichen Aussagen des Users."
    )

    lines.append(
        "Nutze einen Emote-Namen niemals allein "
        "als Beweis dafür, dass ein Ereignis "
        "wirklich stattgefunden hat."
    )

    return "\n".join(
        lines
    )


# =========================================================
# DEBUG FORMAT
# =========================================================

def format_perception_debug(
    perception: PerceivedMessage
) -> str:

    emoji_names = [
        emoji.name
        for emoji
        in perception.custom_emojis
    ]

    reply_name = None

    if perception.reply:

        reply_name = (
            perception.reply.author_name
        )

    return (
        "[PERCEPTION] "
        f"v={PERCEPTION_VERSION} "
        f"user={perception.username} "
        f"id={perception.user_id} "
        f"text={perception.text!r} "
        f"emojis={emoji_names} "
        f"emoji_only={perception.is_emoji_only} "
        f"bot_mention={perception.bot_mentioned} "
        f"direct={perception.direct_address} "
        f"name_mention={perception.name_mentioned} "
        f"address_reason={perception.address_reason!r} "
        f"trigger={perception.trigger_detected} "
        f"reply_bot={perception.replied_to_bot} "
        f"reply_to={reply_name!r} "
        f"should_reply={perception.should_reply}"
    )


# =========================================================
# ADDRESSING SELF TEST
# =========================================================

def _run_addressing_self_test():

    trigger_words = [
        "evilnae",
        "evil nae",
        "evil",
    ]

    cases = [

        # -------------------------------------------------
        # DIRECT
        # -------------------------------------------------

        (
            "Evil, was sagst du dazu?",
            True,
            True
        ),

        (
            "Hallo Evil, alles gut?",
            True,
            True
        ),

        (
            "HALLO Evil - Es scheint dir besser zu gehen?",
            True,
            True
        ),

        (
            "Guten Tag Evil, wie läufts?",
            True,
            True
        ),

        (
            "Moin Evil",
            True,
            True
        ),

        (
            "Soooo meine liebe Evil, alles fit?",
            True,
            True
        ),

        (
            "Was meinst du, Evil?",
            True,
            True
        ),

        (
            "Was meinst du Evil?",
            True,
            True
        ),

        (
            "Gute Besserung Evil",
            True,
            True
        ),

        (
            "Evil kannst du mal helfen?",
            True,
            True
        ),

        (
            "Evil sag mal was",
            True,
            True
        ),

        (
            "Ne Evil nerv mich bitte nicht",
            True,
            True
        ),

        (
            "Wie ist Error eigentlich als Mitbewohner Evil?",
            True,
            True
        ),

        (
            "Schon Pläne für die Weltherrschaft Evil?",
            True,
            True
        ),

        # -------------------------------------------------
        # NAME MENTION ONLY
        # -------------------------------------------------

        (
            "Ich glaub Evil sagt da was anderes xD",
            False,
            True
        ),

        (
            "Sicher? Evil sagt da was anderes xD",
            False,
            True
        ),

        (
            "Evil sagt da was anderes.",
            False,
            True
        ),

        (
            "Evil ist heute irgendwie komisch.",
            False,
            True
        ),

        (
            "Evil hat ein eigenes Zimmer.",
            False,
            True
        ),

        (
            "Evil wird bald den Server übernehmen.",
            False,
            True
        ),

        (
            "Evil ist gut",
            False,
            True
        ),

        (
            "Evil nervt Hanae",
            False,
            True
        ),

        (
            "Ich glaube das war Evil.",
            False,
            True
        ),

        (
            "Ob Evil von Hanaes rotem 3DS weiß?",
            False,
            True
        ),

        (
            "Hana hat Evil kaputt gemacht again",
            False,
            True
        ),

        # -------------------------------------------------
        # NOT EVILNAE
        # -------------------------------------------------

        (
            "Resident Evil ist ein gutes Spiel",
            False,
            False
        ),

        (
            "Ich mag Evil Dead",
            False,
            False
        ),

        (
            "The Evil Within war nice",
            False,
            False
        ),

        (
            "Hallo zusammen",
            False,
            False
        ),
    ]

    passed = 0

    print(
        ""
    )

    print(
        "============================================"
    )

    print(
        f"PERCEPTION v{PERCEPTION_VERSION} SELF TEST"
    )

    print(
        "============================================"
    )

    print(
        ""
    )

    for (
        text,
        expected_direct,
        expected_mention
    ) in cases:

        result = (
            classify_addressing(
                text,
                trigger_words
            )
        )

        success = (

            result.direct_address
            ==
            expected_direct

            and

            result.name_mentioned
            ==
            expected_mention
        )

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
            f"[{status}] "
            f"{text!r}"
        )

        print(
            "       "
            f"direct="
            f"{result.direct_address} "
            f"mention="
            f"{result.name_mentioned} "
            f"reason="
            f"{result.reason}"
        )

    print(
        ""
    )

    print(
        "============================================"
    )

    print(
        f"RESULT: "
        f"{passed}/"
        f"{len(cases)} passed"
    )

    print(
        "============================================"
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    _run_addressing_self_test()
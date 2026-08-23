import re
from dataclasses import dataclass, field
from typing import Optional

import discord


# =========================================================
# PERCEPTION VERSION
# =========================================================

PERCEPTION_VERSION = "1.5"


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
# KNOWN NON-ADDRESS PHRASES
#
# "Evil" ist Evilnaes Spitzname.
#
# Deshalb behandeln wir ein eigenständiges
# "Evil" grundsätzlich als Anrede.
#
# Es gibt aber bekannte Titel / Namen,
# bei denen Evil NICHT Evilnae meint.
# =========================================================

NON_ADDRESS_EVIL_PATTERNS = [

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
    #
    # Evil / Evilnae wird als Anrede entfernt,
    # der restliche natürliche Text bleibt erhalten.
    # -----------------------------------------------------

    text: str

    # -----------------------------------------------------
    # TEXT USED FOR TRIGGER DETECTION
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
# BUILD TRIGGER PATTERN
#
# Aus:
#
# evilnae
# evil nae
# evil
#
# wird ein Regex,
# bei dem Leerzeichen flexibel sind.
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

        # "evil nae"
        # soll auch bei mehreren Spaces funktionieren.

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
# NON-ADDRESS SPANS
#
# Beispiel:
#
# "Ich spiel Resident Evil"
#
# Der Evil-Teil darin darf NICHT
# als Evilnae-Anrede gelten.
# =========================================================

def get_non_address_spans(
    text
):

    spans = []

    for pattern in (
        NON_ADDRESS_EVIL_PATTERNS
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
    first_start,
    first_end,
    second_start,
    second_end
):

    return (
        first_start < second_end
        and
        second_start < first_end
    )


# =========================================================
# FIND VALID EVILNAE ADDRESS SPANS
#
# DAS IST DIE NEUE ZENTRALE LOGIK.
#
# Nicht mehr:
#
# "Steht Hallo davor?"
#
# Sondern:
#
# "Steht Evil / Evilnae überhaupt
#  als eigenständiger Name im Text?"
# =========================================================

def find_address_trigger_spans(
    text,
    trigger_words
):

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
        get_non_address_spans(
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
# TRIGGER DETECTION
#
# Name-first statt Greeting-first.
#
# Beispiele:
#
# Hallo Evil
# -> True
#
# Tag Evil
# -> True
#
# Moin Evil
# -> True
#
# Sooooo meine liebe Evil
# -> True
#
# Evil was machst du?
# -> True
#
# Was denkst du Evil?
# -> True
#
# Evilnae?
# -> True
#
# Resident Evil
# -> False
#
# Evil Dead
# -> False
# =========================================================

def detect_trigger(
    content_without_emojis: str,
    trigger_words: list[str]
) -> bool:

    text = (
        normalize_spacing(
            content_without_emojis
            or ""
        )
    )

    if not text:

        return False

    spans = (
        find_address_trigger_spans(
            text,
            trigger_words
        )
    )

    return bool(
        spans
    )


# =========================================================
# REMOVE TRIGGER ADDRESS
#
# Wir entfernen Evil / Evilnae,
# aber NICHT irgendwelche Wörter davor.
#
# Dadurch hängt die Wahrnehmung nicht mehr
# von Hallo / Moin / Tag / Sooo usw. ab.
#
#
# Beispiel:
#
# "HALLO Evil - wie gehts?"
#
# wird ungefähr:
#
# "HALLO - wie gehts?"
#
#
# Das ist völlig okay:
# Der Writer bekommt weiterhin
# den natürlichen Inhalt der Nachricht.
# =========================================================

def remove_trigger_address(
    text: str,
    trigger_words: list[str]
) -> str:

    if not text:

        return ""

    spans = (
        find_address_trigger_spans(
            text,
            trigger_words
        )
    )

    if not spans:

        return normalize_spacing(
            text
        )

    result = text

    # Von hinten entfernen,
    # damit Positionswerte gültig bleiben.

    for (
        start,
        end
    ) in reversed(
        spans
    ):

        result = (
            result[:start]
            + " "
            + result[end:]
        )

    # -----------------------------------------------------
    # CLEANUP
    # -----------------------------------------------------

    result = re.sub(
        r"[ \t]+",
        " ",
        result
    )

    # Leerzeichen vor Satzzeichen entfernen.

    result = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        result
    )

    # Mehrere Bindestriche / Spaces normalisieren.

    result = re.sub(
        r"\s*-\s*",
        " - ",
        result
    )

    # Doppelte Satzzeichen,
    # die durch Entfernen des Namens entstehen können.

    result = re.sub(
        r",\s*,",
        ",",
        result
    )

    result = normalize_spacing(
        result
    )

    # -----------------------------------------------------
    # ORPHAN PUNCTUATION AT START
    # -----------------------------------------------------

    result = re.sub(
        r"^[,;:\-]+\s*",
        "",
        result
    ).strip()

    return result


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
    # BOT MENTION
    # -----------------------------------------------------

    bot_mentioned = False

    if bot.user is not None:

        bot_mentioned = (
            bot.user
            in message.mentions
        )

    # -----------------------------------------------------
    # NAME TRIGGER
    #
    # Evil / Evilnae ist jetzt
    # das primäre Signal.
    # -----------------------------------------------------

    trigger_detected = (
        detect_trigger(
            no_emojis,
            trigger_words
        )
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
    # CLEAN NATURAL TEXT
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

    if trigger_detected:

        clean_text = (
            remove_trigger_address(
                clean_text,
                trigger_words
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
    #
    # DIRECT wenn:
    #
    # - Evil / Evilnae genannt
    # - Discord-Mention
    # - Reply auf Evilnae
    #
    # Active Conversation / Participation
    # entscheidet weiterhin bot.py.
    # -----------------------------------------------------

    should_reply = (
        trigger_detected
        or
        bot_mentioned
        or
        replied_to_bot
    )

    # -----------------------------------------------------
    # EMOTE ONLY
    #
    # Ein einzelnes Emote ohne
    # direkte Ansprache erzwingt keine Antwort.
    # -----------------------------------------------------

    if (
        is_emoji_only
        and
        not bot_mentioned
        and
        not replied_to_bot
        and
        not trigger_detected
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

        trigger_detected=trigger_detected,

        replied_to_bot=replied_to_bot,

        should_reply=should_reply,

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
        f"trigger={perception.trigger_detected} "
        f"reply_bot={perception.replied_to_bot} "
        f"reply_to={reply_name!r} "
        f"should_reply={perception.should_reply}"
    )
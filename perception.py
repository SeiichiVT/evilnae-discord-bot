import re
from dataclasses import dataclass, field
from typing import Optional

import discord


# =========================================================
# REGEX
# =========================================================

# Discord Custom Emoji:
#
# <:Name:123456>
# <a:Name:123456>

CUSTOM_EMOJI_PATTERN = re.compile(
    r"<(?P<animated>a?):"
    r"(?P<name>[A-Za-z0-9_]+):"
    r"(?P<id>\d+)>"
)


# Discord User Mention:
#
# <@123>
# <@!123>

USER_MENTION_PATTERN = re.compile(
    r"<@!?(?P<id>\d+)>"
)


# Discord Role Mention:
#
# <@&123>

ROLE_MENTION_PATTERN = re.compile(
    r"<@&(?P<id>\d+)>"
)


# Discord Channel Mention:
#
# <#123>

CHANNEL_MENTION_PATTERN = re.compile(
    r"<#(?P<id>\d+)>"
)


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
    # CLEAN NATURAL-LANGUAGE CONTENT
    #
    # Custom Emojis und Bot-Anrede entfernt.
    # -----------------------------------------------------

    text: str

    # -----------------------------------------------------
    # CONTENT WITHOUT CUSTOM EMOJIS
    #
    # Wird unter anderem für Trigger Detection benutzt.
    # -----------------------------------------------------

    trigger_text: str

    # -----------------------------------------------------
    # EMOJIS
    # -----------------------------------------------------

    custom_emojis: list[ParsedEmoji] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # MESSAGE TYPE FLAGS
    # -----------------------------------------------------

    is_emoji_only: bool = False

    has_text: bool = False

    # -----------------------------------------------------
    # EVILNAE ADDRESSING
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

    for match in CUSTOM_EMOJI_PATTERN.finditer(
        content or ""
    ):

        emojis.append(
            ParsedEmoji(
                name=match.group(
                    "name"
                ),
                emoji_id=match.group(
                    "id"
                ),
                animated=(
                    match.group(
                        "animated"
                    )
                    == "a"
                ),
                raw=match.group(0)
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

    # Mehrere Spaces -> einer

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Mehr als zwei Newlines vermeiden

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
# TRIGGER DETECTION
# =========================================================

def detect_trigger(
    content_without_emojis: str,
    trigger_words: list[str]
) -> bool:

    """
    Erkennt Evilnae-Anreden ausschließlich
    im echten Text.

    Custom Emoji Namen wurden VORHER entfernt.

    Dadurch löst:

    <a:EvilnaeCool:123>

    KEINEN Trigger aus.
    """

    text = (
        content_without_emojis
        or ""
    ).lower()

    for trigger in trigger_words:

        escaped = re.escape(
            trigger.lower()
        )

        # Wort-/Namensgrenzen.
        #
        # "evil" wird erkannt in:
        #
        # Evil was geht?
        # ey evil
        # EVIL!!!
        #
        # aber nicht mitten in einem
        # beliebigen längeren Wort.

        pattern = (
            rf"(?<![a-zA-Z0-9_])"
            rf"{escaped}"
            rf"(?![a-zA-Z0-9_])"
        )

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            return True

    return False


# =========================================================
# REMOVE EVILNAE ADDRESS
# =========================================================

def remove_trigger_address(
    text: str,
    trigger_words: list[str]
) -> str:

    """
    Entfernt eine Evilnae-Anrede nur dort,
    wo sie wie eine Anrede benutzt wird.

    Beispiele:

    Evil was machst du?
    -> was machst du?

    Hey Evil, was machst du?
    -> Hey, was machst du?

    Resident Evil ist cool
    -> Resident Evil ist cool

    Wir entfernen also NICHT blind jedes
    Vorkommen von "evil".
    """

    if not text:
        return ""

    result = text

    # -----------------------------------------------------
    # TRIGGER AM ANFANG
    # -----------------------------------------------------

    sorted_triggers = sorted(
        trigger_words,
        key=len,
        reverse=True
    )

    trigger_pattern = "|".join(
        re.escape(trigger)
        for trigger in sorted_triggers
    )

    result = re.sub(
        rf"^\s*(?:{trigger_pattern})"
        rf"[\s,:;!?.\-]*",
        "",
        result,
        flags=re.IGNORECASE
    )

    # -----------------------------------------------------
    # "hey evil ..."
    # "ey evil ..."
    # "yo evil ..."
    # -----------------------------------------------------

    result = re.sub(
        rf"^\s*"
        rf"(hey|ey|yo|hallo|hi|moin|servus)"
        rf"[\s,]+"
        rf"(?:{trigger_pattern})"
        rf"[\s,:;!?.\-]*",
        r"\1 ",
        result,
        flags=re.IGNORECASE
    )

    return normalize_spacing(
        result
    )


# =========================================================
# EMOJI ONLY DETECTION
# =========================================================

def detect_emoji_only(
    raw_content: str
) -> bool:

    if not raw_content:
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

    # Wenn nach Entfernen der Discord-Custom-Emojis
    # kein echter Text übrig bleibt:
    #
    # reine Custom-Emoji-Nachricht.

    if not without_custom:

        return bool(
            extract_custom_emojis(
                raw_content
            )
        )

    return False


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
    # REMOVE CUSTOM EMOJIS BEFORE TRIGGER DETECTION
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
    # TRIGGER
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
    # -----------------------------------------------------

    should_reply = (

        bot_mentioned
        or
        trigger_detected
        or
        replied_to_bot
    )

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

    return (
        "[PERCEPTION] "
        f"user={perception.username} "
        f"id={perception.user_id} "
        f"text={perception.text!r} "
        f"emojis={emoji_names} "
        f"emoji_only={perception.is_emoji_only} "
        f"bot_mention={perception.bot_mentioned} "
        f"trigger={perception.trigger_detected} "
        f"reply_bot={perception.replied_to_bot} "
        f"should_reply={perception.should_reply}"
    )
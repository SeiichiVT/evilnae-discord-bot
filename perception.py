import re
from dataclasses import dataclass, field
from typing import Optional

import discord


# =========================================================
# PERCEPTION VERSION
# =========================================================

PERCEPTION_VERSION = "1.1"


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
# KNOWN NON-ADDRESS PHRASES
#
# Damit z. B. "Resident Evil" nicht als
# "jemand ruft Evilnae" interpretiert wird.
# =========================================================

NON_ADDRESS_EVIL_PHRASES = {
    "resident evil",
    "evil dead",
    "the evil within",
}


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
    # Custom Emojis und Evilnae-Anrede entfernt.
    # -----------------------------------------------------

    text: str

    # -----------------------------------------------------
    # TEXT WITHOUT CUSTOM EMOJIS
    #
    # Wird für Trigger Detection benutzt.
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

    for match in CUSTOM_EMOJI_PATTERN.finditer(
        content or ""
    ):

        emojis.append(
            ParsedEmoji(
                name=match.group("name"),
                emoji_id=match.group("id"),
                animated=(
                    match.group("animated")
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
# HELPER: TRIGGER PATTERN
# =========================================================

def build_trigger_pattern(
    trigger_words: list[str]
) -> str:

    sorted_triggers = sorted(
        trigger_words,
        key=len,
        reverse=True
    )

    return "|".join(
        re.escape(trigger)
        for trigger in sorted_triggers
    )


# =========================================================
# KNOWN TITLE CHECK
# =========================================================

def contains_known_non_address_phrase(
    text: str
) -> bool:

    lowered = (
        text or ""
    ).lower()

    return any(
        phrase in lowered
        for phrase in NON_ADDRESS_EVIL_PHRASES
    )


# =========================================================
# TRIGGER DETECTION
# =========================================================

def detect_trigger(
    content_without_emojis: str,
    trigger_words: list[str]
) -> bool:

    """
    Evilnae wird nur erkannt,
    wenn der Name tatsächlich wie eine Anrede
    oder direkte Ansprache benutzt wird.

    Beispiele:

    Evil was machst du?
    -> True

    Hey Evil, komm mal
    -> True

    was denkst du Evil?
    -> True

    Resident Evil ist geil
    -> False

    <a:EvilnaeCool:123>
    -> False
    """

    text = normalize_spacing(
        content_without_emojis
        or ""
    )

    if not text:
        return False

    lowered = text.lower()

    # -----------------------------------------------------
    # BEKANNTE TITEL / NICHT-ANREDEN
    # -----------------------------------------------------

    if contains_known_non_address_phrase(
        lowered
    ):

        # Falls zusätzlich irgendwo eine echte,
        # separate Anrede vorkommt, darf sie trotzdem
        # erkannt werden.
        #
        # Beispiel:
        #
        # Evil, Resident Evil ist geil
        #
        # -> True

        beginning_pattern = build_trigger_pattern(
            trigger_words
        )

        explicit_start = re.search(
            rf"^\s*"
            rf"(?:hey|ey|yo|hi|hallo|moin|servus)?"
            rf"[\s,:;!?.\-]*"
            rf"(?:{beginning_pattern})"
            rf"[\s,:;!?.\-]+",
            text,
            flags=re.IGNORECASE
        )

        if not explicit_start:
            return False

    trigger_pattern = build_trigger_pattern(
        trigger_words
    )

    # -----------------------------------------------------
    # 1. DIREKTE ANREDE AM ANFANG
    #
    # Evil was machst du
    # Evil, komm mal
    # -----------------------------------------------------

    if re.search(
        rf"^\s*"
        rf"(?:{trigger_pattern})"
        rf"(?:\s|[,.:;!?…\-]|$)",
        text,
        flags=re.IGNORECASE
    ):

        return True

    # -----------------------------------------------------
    # 2. GREETING + ANREDE
    #
    # Hey Evil
    # Ey evil komm mal
    # Hallo Evilnae
    # -----------------------------------------------------

    if re.search(
        rf"^\s*"
        rf"(?:hey|ey|yo|hi|hallo|moin|servus)"
        rf"[\s,]+"
        rf"(?:{trigger_pattern})"
        rf"(?:\s|[,.:;!?…\-]|$)",
        text,
        flags=re.IGNORECASE
    ):

        return True

    # -----------------------------------------------------
    # 3. ANREDE AM SATZENDE
    #
    # was denkst du Evil?
    # gute Nacht Evil
    # -----------------------------------------------------

    if re.search(
        rf"(?:^|[\s,])"
        rf"(?:{trigger_pattern})"
        rf"[\s.!?,:;…\-]*$",
        text,
        flags=re.IGNORECASE
    ):

        return True

    # -----------------------------------------------------
    # 4. KLARE ANREDE IN DER MITTE
    #
    # sag mal Evil, was denkst du?
    #
    # Wir verlangen Satzzeichen nach dem Namen,
    # damit nicht jedes normale "evil" im Satz feuert.
    # -----------------------------------------------------

    if re.search(
        rf"(?:^|[\s])"
        rf"(?:{trigger_pattern})"
        rf"[,!:;]"
        rf"(?:\s|$)",
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
    Entfernt Evilnae nur dort,
    wo sie als direkte Anrede benutzt wird.

    Resident Evil bleibt erhalten.
    """

    if not text:
        return ""

    result = text

    trigger_pattern = build_trigger_pattern(
        trigger_words
    )

    # -----------------------------------------------------
    # EVIL AM ANFANG
    # -----------------------------------------------------

    result = re.sub(
        rf"^\s*"
        rf"(?:{trigger_pattern})"
        rf"[\s,:;!?.…\-]*",
        "",
        result,
        flags=re.IGNORECASE
    )

    # -----------------------------------------------------
    # HEY EVIL ...
    #
    # Wir behalten "Hey" als natürlichen Satzanfang.
    # -----------------------------------------------------

    result = re.sub(
        rf"^\s*"
        rf"(hey|ey|yo|hallo|hi|moin|servus)"
        rf"[\s,]+"
        rf"(?:{trigger_pattern})"
        rf"[\s,:;!?.…\-]*",
        r"\1 ",
        result,
        flags=re.IGNORECASE
    )

    # -----------------------------------------------------
    # EVIL AM SATZENDE
    #
    # "was denkst du Evil?"
    # -> "was denkst du?"
    # -----------------------------------------------------

    result = re.sub(
        rf"[\s,]+"
        rf"(?:{trigger_pattern})"
        rf"(?P<punc>[.!?…]*)"
        rf"\s*$",
        r"\g<punc>",
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

        reply_message = resolved

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
    # TRIGGER DETECTION
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

    clean_text = no_emojis

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

    # -----------------------------------------------------
    # IMPORTANT:
    #
    # Reines Emote darf NICHT allein durch seinen
    # Namen Evilnae triggern.
    # -----------------------------------------------------

    if (
        is_emoji_only
        and
        not bot_mentioned
        and
        not replied_to_bot
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

    for emoji in perception.custom_emojis:

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

    lines.append("")
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
import re
from dataclasses import dataclass, field
from typing import Optional

import discord


# =========================================================
# PERCEPTION VERSION
# =========================================================

PERCEPTION_VERSION = "1.4"


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
# Damit z. B.:
#
# Resident Evil
# Evil Dead
#
# nicht als direkte Anrede interpretiert werden.
# =========================================================

NON_ADDRESS_EVIL_PHRASES = {
    "resident evil",
    "evil dead",
    "the evil within",
}


# =========================================================
# NATURAL ADDRESS LEAD-INS
#
# Diese Wörter können natürlich
# vor einer Evilnae-Anrede stehen.
#
# Beispiele:
#
# So Evil ...
# Soooo Evil ...
# Also Evil ...
# Okay Evil ...
# Naja Evil ...
# =========================================================

ADDRESS_LEAD_INS = {
    "so",
    "also",
    "okay",
    "ok",
    "ja",
    "na",
    "naja",
    "gut",
    "hm",
    "hmm",
    "äh",
    "ehm",
}


# =========================================================
# GREETINGS
# =========================================================

GREETING_LEAD_INS = {
    "hey",
    "ey",
    "yo",
    "hi",
    "hallo",
    "moin",
    "servus",
}


# =========================================================
# OPTIONAL ADDRESS MODIFIERS
#
# Beispiele:
#
# Soooo liebe Evil
# Hey kleine Evil
# Also meine liebe Evil
# =========================================================

ADDRESS_MODIFIERS = {
    "liebe",
    "lieber",
    "meine",
    "mein",
    "kleine",
    "kleiner",
    "gute",
    "guter",
    "werte",
    "werter",
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
    # CLEAN NATURAL TEXT
    # -----------------------------------------------------

    text: str

    # -----------------------------------------------------
    # TEXT FOR TRIGGER DETECTION
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
# STRETCHED WORD NORMALIZATION
#
# Nur für Anrede-Erkennung.
#
# User-Text selbst wird NICHT verändert.
#
# sooo   -> so
# heyyy  -> hey
# okayyy -> okay
# jaaaa  -> ja
# =========================================================

def normalize_stretched_word(
    word: str
) -> str:

    word = (
        word
        or ""
    ).strip().lower()

    if not word:

        return ""

    return re.sub(
        r"(.)\1+",
        r"\1",
        word
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
# TRIGGER PATTERN
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
        re.escape(
            trigger
        )
        for trigger
        in sorted_triggers
    )


# =========================================================
# ADDRESS MODIFIER PATTERN
# =========================================================

def build_modifier_pattern():

    return "|".join(
        re.escape(
            word
        )
        for word
        in sorted(
            ADDRESS_MODIFIERS,
            key=len,
            reverse=True
        )
    )


# =========================================================
# KNOWN TITLE CHECK
# =========================================================

def contains_known_non_address_phrase(
    text: str
) -> bool:

    lowered = (
        text
        or ""
    ).lower()

    return any(
        phrase in lowered
        for phrase
        in NON_ADDRESS_EVIL_PHRASES
    )


# =========================================================
# NATURAL LEAD-IN CLASSIFICATION
# =========================================================

def classify_lead_in(
    word
):

    normalized = (
        normalize_stretched_word(
            word
        )
    )

    if (
        normalized
        in ADDRESS_LEAD_INS
    ):

        return "address"

    if (
        normalized
        in GREETING_LEAD_INS
    ):

        return "greeting"

    return None


# =========================================================
# DIRECT START ADDRESS
# =========================================================

def detect_direct_start_address(
    text,
    trigger_words
):

    trigger_pattern = (
        build_trigger_pattern(
            trigger_words
        )
    )

    modifier_pattern = (
        build_modifier_pattern()
    )

    # -----------------------------------------------------
    # EVIL ...
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
    # NATURAL LEAD-IN + OPTIONAL MODIFIERS
    #
    # Sooo Evil
    #
    # Soooo liebe Evil
    #
    # Also meine liebe Evil
    #
    # Heyyy kleine Evil
    #
    # Okay Evil
    # -----------------------------------------------------

    match = re.search(
        rf"^\s*"
        rf"(?P<lead>[A-Za-zÄÖÜäöüß]+)"
        rf"[\s,.:;!?…\-]+"
        rf"(?:"
            rf"(?:{modifier_pattern})"
            rf"[\s,.:;!?…\-]+"
        rf"){{0,3}}"
        rf"(?:{trigger_pattern})"
        rf"(?:\s|[,.:;!?…\-]|$)",
        text,
        flags=re.IGNORECASE
    )

    if match:

        lead = (
            match.group(
                "lead"
            )
        )

        if classify_lead_in(
            lead
        ):

            return True

    # -----------------------------------------------------
    # MODIFIER DIRECTLY BEFORE EVIL
    #
    # Liebe Evil ...
    #
    # Meine liebe Evil ...
    # -----------------------------------------------------

    if re.search(
        rf"^\s*"
        rf"(?:"
            rf"(?:{modifier_pattern})"
            rf"[\s,.:;!?…\-]+"
        rf"){{1,3}}"
        rf"(?:{trigger_pattern})"
        rf"(?:\s|[,.:;!?…\-]|$)",
        text,
        flags=re.IGNORECASE
    ):

        return True

    return False


# =========================================================
# TRIGGER DETECTION
# =========================================================

def detect_trigger(
    content_without_emojis: str,
    trigger_words: list[str]
) -> bool:

    """
    Beispiele:

    Evil was machst du?
    -> True

    Hey Evil
    -> True

    Heyyy Evil
    -> True

    So Evil
    -> True

    Sooooo Evil
    -> True

    Soooo liebe Evil
    -> True

    Also meine liebe Evil
    -> True

    Liebe Evil
    -> True

    was denkst du Evil?
    -> True

    Resident Evil ist geil
    -> False
    """

    text = (
        normalize_spacing(
            content_without_emojis
            or ""
        )
    )

    if not text:

        return False

    direct_start = (
        detect_direct_start_address(
            text,
            trigger_words
        )
    )

    # -----------------------------------------------------
    # KNOWN NON-ADDRESS PHRASE
    # -----------------------------------------------------

    if (
        contains_known_non_address_phrase(
            text
        )
        and
        not direct_start
    ):

        return False

    if direct_start:

        return True

    trigger_pattern = (
        build_trigger_pattern(
            trigger_words
        )
    )

    # -----------------------------------------------------
    # NAME AT END
    #
    # was denkst du Evil?
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
    # VOCATIVE IN MIDDLE
    #
    # sag mal Evil, was denkst du?
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
# REMOVE TRIGGER ADDRESS
# =========================================================

def remove_trigger_address(
    text: str,
    trigger_words: list[str]
) -> str:

    if not text:

        return ""

    result = text

    trigger_pattern = (
        build_trigger_pattern(
            trigger_words
        )
    )

    modifier_pattern = (
        build_modifier_pattern()
    )

    # -----------------------------------------------------
    # LEAD-IN + OPTIONAL MODIFIERS + EVIL
    #
    # Sooo Evil
    # -> entfernt
    #
    # Sooo liebe Evil
    # -> entfernt
    #
    # Heyyy Evil
    # -> Heyyy bleibt
    #
    # Heyyy kleine Evil
    # -> Heyyy bleibt
    # -----------------------------------------------------

    start_pattern = re.compile(
        rf"^\s*"
        rf"(?P<lead>[A-Za-zÄÖÜäöüß]+)"
        rf"[\s,.:;!?…\-]+"
        rf"(?:"
            rf"(?:{modifier_pattern})"
            rf"[\s,.:;!?…\-]+"
        rf"){{0,3}}"
        rf"(?:{trigger_pattern})"
        rf"[\s,:;!?.…\-]*",
        flags=re.IGNORECASE
    )

    start_match = (
        start_pattern.search(
            result
        )
    )

    if start_match:

        lead = (
            start_match.group(
                "lead"
            )
        )

        lead_type = (
            classify_lead_in(
                lead
            )
        )

        if (
            lead_type
            == "address"
        ):

            result = (
                result[
                    start_match.end():
                ]
            )

        elif (
            lead_type
            == "greeting"
        ):

            result = (
                lead
                + " "
                + result[
                    start_match.end():
                ]
            )

    # -----------------------------------------------------
    # DIRECT MODIFIER + EVIL
    #
    # Liebe Evil
    # Meine liebe Evil
    # -----------------------------------------------------

    result = re.sub(
        rf"^\s*"
        rf"(?:"
            rf"(?:{modifier_pattern})"
            rf"[\s,.:;!?…\-]+"
        rf"){{1,3}}"
        rf"(?:{trigger_pattern})"
        rf"[\s,:;!?.…\-]*",
        "",
        result,
        flags=re.IGNORECASE
    )

    # -----------------------------------------------------
    # EVIL AT START
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
    # EVIL AT END
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

    # -----------------------------------------------------
    # EVIL AS VOCATIVE IN MIDDLE
    #
    # Sag mal Evil, was...
    # -> Sag mal, was...
    # -----------------------------------------------------

    result = re.sub(
        rf"(?P<before>\s)"
        rf"(?:{trigger_pattern})"
        rf"(?P<punc>[,!:;])"
        rf"(?P<after>\s*)",
        lambda match: (
            match.group(
                "punc"
            )
            +
            (
                " "
                if match.group(
                    "after"
                )
                else ""
            )
        ),
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
    # REMOVE CUSTOM EMOJIS
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
    # DIRECT RESPONSE DECISION
    #
    # WICHTIG:
    #
    # Das bedeutet nur:
    #
    # "Evilnae wurde direkt angesprochen."
    #
    # Active Conversation und Participation
    # werden später in bot.py entschieden.
    # -----------------------------------------------------

    should_reply = (
        bot_mentioned
        or
        trigger_detected
        or
        replied_to_bot
    )

    # -----------------------------------------------------
    # EMOTE-ONLY SAFETY
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
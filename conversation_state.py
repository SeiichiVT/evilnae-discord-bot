from dataclasses import dataclass, field
from typing import Optional, Any


# =========================================================
# VERSION
# =========================================================

CONVERSATION_STATE_VERSION = "1.1"


# =========================================================
# REPLY STATE
# =========================================================

@dataclass
class ReplyState:

    message_id: Optional[str] = None

    author_id: Optional[str] = None

    author_name: Optional[str] = None

    content: str = ""

    author_is_bot: bool = False


# =========================================================
# EMOJI STATE
# =========================================================

@dataclass
class EmojiState:

    name: str

    emoji_id: str

    animated: bool = False


# =========================================================
# MEMORY STATE
# =========================================================

@dataclass
class MemoryState:

    profile: str = ""

    relationship: str = ""

    recent_memories: list[str] = field(
        default_factory=list
    )

    archive: str = ""


# =========================================================
# CONVERSATION HISTORY
# =========================================================

@dataclass
class ConversationHistoryState:

    direct_history: str = ""

    channel_history: str = ""

    participant_context: str = ""

    resolved_short_context: str = ""

    recent_evilnae_messages: list[str] = field(
        default_factory=list
    )


# =========================================================
# USER STATE
# =========================================================

@dataclass
class UserState:

    user_id: str

    username: str

    is_hanae: bool = False


# =========================================================
# PERCEPTION STATE
# =========================================================

@dataclass
class PerceptionState:

    raw_content: str = ""

    clean_text: str = ""

    has_text: bool = False

    is_emoji_only: bool = False

    bot_mentioned: bool = False

    trigger_detected: bool = False

    replied_to_bot: bool = False

    emojis: list[EmojiState] = field(
        default_factory=list
    )

    reply: Optional[ReplyState] = None


# =========================================================
# MOOD STATE
# =========================================================

@dataclass
class MoodState:

    current_mood: str = "normal"


# =========================================================
# BRAIN STATE
# =========================================================

@dataclass
class BrainState:

    intent: str = "unknown"

    action: str = "reply"

    response_length: str = "auto"

    tone: str = "natural"

    ask_question: bool = False

    acknowledge_correction: bool = False

    topic_exhausted: bool = False

    repetition_risk: bool = False

    # -----------------------------------------------------
    # KNOWLEDGE GUARD
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

    reasoning_summary: str = ""


# =========================================================
# COMPLETE CONVERSATION STATE
# =========================================================

@dataclass
class ConversationState:

    user: UserState

    channel_id: str

    perception: PerceptionState

    memory: MemoryState

    history: ConversationHistoryState

    mood: MoodState

    brain: BrainState = field(
        default_factory=BrainState
    )


# =========================================================
# HELPER
# =========================================================

def _safe_text(
    value: Any,
    fallback: str = ""
) -> str:

    if value is None:

        return fallback

    value = str(
        value
    ).strip()

    if not value:

        return fallback

    return value


# =========================================================
# RECENT EVILNAE MESSAGES
# =========================================================

def extract_recent_evilnae_messages(
    user_context,
    limit: int = 6
) -> list[str]:

    messages = []

    try:

        for entry in reversed(
            list(
                user_context
            )
        ):

            if (
                entry.get(
                    "role"
                )
                != "assistant"
            ):

                continue

            content = (
                entry.get(
                    "content",
                    ""
                )
            ).strip()

            if not content:

                continue

            messages.append(
                content
            )

            if (
                len(messages)
                >= limit
            ):

                break

    except Exception:

        return []

    messages.reverse()

    return messages


# =========================================================
# BUILD STATE
# =========================================================

def build_conversation_state(
    *,
    perception,
    hanae_user_id,
    user_profile,
    social_impression,
    recent_memories,
    memory_archive,
    direct_context_text,
    group_context_text,
    participant_context_text,
    resolved_short_context_text,
    current_mood,
    user_context
) -> ConversationState:

    # -----------------------------------------------------
    # USER
    # -----------------------------------------------------

    user_state = UserState(

        user_id=(
            perception.user_id
        ),

        username=(
            perception.username
        ),

        is_hanae=(
            perception.user_id
            == hanae_user_id
        )
    )

    # -----------------------------------------------------
    # EMOJIS
    # -----------------------------------------------------

    emoji_states = []

    for emoji in (
        perception.custom_emojis
    ):

        emoji_states.append(
            EmojiState(

                name=(
                    emoji.name
                ),

                emoji_id=(
                    emoji.emoji_id
                ),

                animated=(
                    emoji.animated
                )
            )
        )

    # -----------------------------------------------------
    # REPLY
    # -----------------------------------------------------

    reply_state = None

    if perception.reply:

        reply_state = ReplyState(

            message_id=(
                perception.reply.message_id
            ),

            author_id=(
                perception.reply.author_id
            ),

            author_name=(
                perception.reply.author_name
            ),

            content=(
                perception.reply.content
                or ""
            ),

            author_is_bot=(
                perception.reply.author_is_bot
            )
        )

    # -----------------------------------------------------
    # PERCEPTION
    # -----------------------------------------------------

    perception_state = PerceptionState(

        raw_content=(
            perception.raw_content
            or ""
        ),

        clean_text=(
            perception.text
            or ""
        ),

        has_text=(
            perception.has_text
        ),

        is_emoji_only=(
            perception.is_emoji_only
        ),

        bot_mentioned=(
            perception.bot_mentioned
        ),

        trigger_detected=(
            perception.trigger_detected
        ),

        replied_to_bot=(
            perception.replied_to_bot
        ),

        emojis=(
            emoji_states
        ),

        reply=(
            reply_state
        )
    )

    # -----------------------------------------------------
    # MEMORY
    # -----------------------------------------------------

    memory_state = MemoryState(

        profile=_safe_text(
            user_profile,
            "Noch kein stabiles Profil."
        ),

        relationship=_safe_text(
            social_impression,
            (
                "Evilnae hat noch keinen "
                "stabilen sozialen Eindruck "
                "von dieser Person."
            )
        ),

        recent_memories=(
            recent_memories
            if recent_memories
            else []
        ),

        archive=_safe_text(
            memory_archive,
            "Noch kein Langzeit-Archiv."
        )
    )

    # -----------------------------------------------------
    # EVILNAES OWN RECENT OUTPUT
    # -----------------------------------------------------

    recent_evilnae_messages = (
        extract_recent_evilnae_messages(
            user_context,
            limit=6
        )
    )

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    history_state = (
        ConversationHistoryState(

            direct_history=_safe_text(
                direct_context_text,
                (
                    "Noch kein direkter "
                    "Gesprächsverlauf."
                )
            ),

            channel_history=_safe_text(
                group_context_text,
                (
                    "Noch kein kurzfristiger "
                    "Channel-Verlauf."
                )
            ),

            participant_context=_safe_text(
                participant_context_text,
                (
                    "Keine weiteren "
                    "aktiven Personen."
                )
            ),

            resolved_short_context=_safe_text(
                resolved_short_context_text,
                (
                    "Keine aufgelösten "
                    "Kurzantworten."
                )
            ),

            recent_evilnae_messages=(
                recent_evilnae_messages
            )
        )
    )

    # -----------------------------------------------------
    # MOOD
    # -----------------------------------------------------

    mood_state = MoodState(

        current_mood=(
            current_mood
            or "normal"
        )
    )

    return ConversationState(

        user=(
            user_state
        ),

        channel_id=(
            perception.channel_id
        ),

        perception=(
            perception_state
        ),

        memory=(
            memory_state
        ),

        history=(
            history_state
        ),

        mood=(
            mood_state
        )
    )


# =========================================================
# FORMAT STATE FOR BRAIN
# =========================================================

def format_state_for_brain(
    state: ConversationState
) -> str:

    # -----------------------------------------------------
    # EMOJIS
    # -----------------------------------------------------

    if state.perception.emojis:

        emoji_text = "\n".join(
            (
                f"- {emoji.name} "
                f"(animated={emoji.animated})"
            )

            for emoji
            in state.perception.emojis
        )

    else:

        emoji_text = (
            "Keine Custom-Emotes."
        )

    # -----------------------------------------------------
    # REPLY
    # -----------------------------------------------------

    if state.perception.reply:

        reply = (
            state.perception.reply
        )

        reply_text = f"""
Name:
{reply.author_name}

Discord-ID:
{reply.author_id}

Bot:
{reply.author_is_bot}

Inhalt:
{reply.content}
""".strip()

    else:

        reply_text = (
            "Keine Discord-Antwort."
        )

    # -----------------------------------------------------
    # RECENT EVILNAE OUTPUT
    # -----------------------------------------------------

    if (
        state.history
        .recent_evilnae_messages
    ):

        recent_output = (
            "\n\n".join(
                (
                    f"{index + 1}. "
                    f"{message}"
                )

                for index, message
                in enumerate(
                    state.history
                    .recent_evilnae_messages
                )
            )
        )

    else:

        recent_output = (
            "Noch keine aktuellen "
            "eigenen Antworten."
        )

    # -----------------------------------------------------
    # RECENT MEMORIES
    # -----------------------------------------------------

    if state.memory.recent_memories:

        recent_memory_text = (
            "\n".join(
                f"- {memory}"

                for memory
                in state.memory.recent_memories
            )
        )

    else:

        recent_memory_text = (
            "Keine neueren Erinnerungen."
        )

    return f"""
==================================================
CURRENT PERSON
==================================================

Name:
{state.user.username}

Discord-ID:
{state.user.user_id}

Ist Hanae:
{state.user.is_hanae}


==================================================
CURRENT MESSAGE
==================================================

{state.perception.clean_text}


==================================================
MESSAGE METADATA
==================================================

has_text:
{state.perception.has_text}

emoji_only:
{state.perception.is_emoji_only}

bot_mentioned:
{state.perception.bot_mentioned}

trigger_detected:
{state.perception.trigger_detected}

replied_to_bot:
{state.perception.replied_to_bot}


==================================================
CUSTOM EMOTES
==================================================

{emoji_text}


==================================================
CURRENT REPLY
==================================================

{reply_text}


==================================================
CURRENT MOOD
==================================================

{state.mood.current_mood}


==================================================
USER PROFILE
==================================================

{state.memory.profile}


==================================================
RELATIONSHIP
==================================================

{state.memory.relationship}


==================================================
RECENT MEMORIES
==================================================

{recent_memory_text}


==================================================
LONG TERM ARCHIVE
==================================================

{state.memory.archive}


==================================================
DIRECT USER CONVERSATION
==================================================

{state.history.direct_history}


==================================================
ACTIVE PARTICIPANTS
==================================================

{state.history.participant_context}


==================================================
RESOLVED SHORT CONTEXT
==================================================

{state.history.resolved_short_context}


==================================================
CHANNEL CONTEXT
==================================================

{state.history.channel_history}


==================================================
EVILNAES RECENT OWN MESSAGES
==================================================

{recent_output}
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_state_debug(
    state: ConversationState
) -> str:

    return (
        "[STATE] "
        f"v="
        f"{CONVERSATION_STATE_VERSION} "
        f"user="
        f"{state.user.username} "
        f"id="
        f"{state.user.user_id} "
        f"hanae="
        f"{state.user.is_hanae} "
        f"mood="
        f"{state.mood.current_mood} "
        f"recent_evilnae="
        f"{len(state.history.recent_evilnae_messages)} "
        f"memories="
        f"{len(state.memory.recent_memories)} "
        f"emojis="
        f"{len(state.perception.emojis)}"
    )
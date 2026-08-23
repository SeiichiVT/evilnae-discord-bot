import re
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional


# =========================================================
# VERSION
# =========================================================

EXPRESSION_VERSION = "1.0"


# =========================================================
# EXPRESSION PLAN
# =========================================================

@dataclass
class ExpressionPlan:

    style: str = "natural"

    slang_level: str = "light"

    emoji_level: str = "light"

    sentence_shape: str = "casual"

    lowercase_preferred: bool = True

    allow_fragmented_sentences: bool = True

    avoid_openers: list[str] = field(
        default_factory=list
    )

    avoid_words: list[str] = field(
        default_factory=list
    )

    avoid_emojis: list[str] = field(
        default_factory=list
    )

    preferred_energy: str = "relaxed"

    notes: list[str] = field(
        default_factory=list
    )


# =========================================================
# STYLE VALUES
# =========================================================

VALID_STYLES = {
    "natural",
    "dry",
    "playful",
    "soft",
    "smug",
    "chaotic",
    "serious",
    "deadpan",
    "warm",
}


# =========================================================
# TRACKED WORDS / PHRASES
# =========================================================

TRACKED_WORDS = {
    "bro",
    "bruh",
    "chill",
    "fair",
    "real",
    "actually",
    "legit",
    "wild",
    "lmao",
    "help",
    "rip",
    "digga",
    "alter",
}


TRACKED_OPENERS = {
    "haha",
    "lol",
    "oh",
    "ohh",
    "ah",
    "also",
    "naja",
    "ja okay",
    "okay",
    "wait",
    "bro",
    "bruh",
}


TRACKED_EMOJIS = {
    "😂",
    "😭",
    "💀",
    "😏",
    "💪",
    "🥲",
    "🤨",
    "😌",
    "👀",
}


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(
    text: str
) -> str:

    if not text:
        return ""

    text = text.strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# =========================================================
# EXTRACT WORD TOKENS
# =========================================================

def extract_words(
    text: str
) -> list[str]:

    normalized = (
        normalize_text(
            text
        )
    )

    return re.findall(
        r"[a-zA-ZäöüÄÖÜß]+",
        normalized
    )


# =========================================================
# DETECT OPENER
# =========================================================

def detect_opener(
    text: str
) -> Optional[str]:

    normalized = (
        normalize_text(
            text
        )
    )

    if not normalized:
        return None

    for opener in sorted(
        TRACKED_OPENERS,
        key=len,
        reverse=True
    ):

        if (
            normalized == opener
            or
            normalized.startswith(
                opener + " "
            )
            or
            normalized.startswith(
                opener + ","
            )
            or
            normalized.startswith(
                opener + "!"
            )
        ):

            return opener

    return None


# =========================================================
# COUNT EMOJIS
# =========================================================

def count_tracked_emojis(
    messages: list[str]
) -> Counter:

    counter = Counter()

    for message in messages:

        for emoji in TRACKED_EMOJIS:

            count = (
                message.count(
                    emoji
                )
            )

            if count:

                counter[
                    emoji
                ] += count

    return counter


# =========================================================
# COUNT TRACKED WORDS
# =========================================================

def count_tracked_words(
    messages: list[str]
) -> Counter:

    counter = Counter()

    for message in messages:

        words = (
            extract_words(
                message
            )
        )

        for word in words:

            lowered = (
                word.lower()
            )

            if (
                lowered
                in TRACKED_WORDS
            ):

                counter[
                    lowered
                ] += 1

    return counter


# =========================================================
# COUNT OPENERS
# =========================================================

def count_openers(
    messages: list[str]
) -> Counter:

    counter = Counter()

    for message in messages:

        opener = (
            detect_opener(
                message
            )
        )

        if opener:

            counter[
                opener
            ] += 1

    return counter


# =========================================================
# QUESTION DENSITY
# =========================================================

def get_question_density(
    messages: list[str]
) -> float:

    if not messages:
        return 0.0

    question_messages = sum(
        1
        for message
        in messages
        if "?" in message
    )

    return (
        question_messages
        / len(messages)
    )


# =========================================================
# EXCLAMATION DENSITY
# =========================================================

def get_exclamation_density(
    messages: list[str]
) -> float:

    if not messages:
        return 0.0

    count = sum(
        1
        for message
        in messages
        if "!" in message
    )

    return (
        count
        / len(messages)
    )


# =========================================================
# ANALYZE RECENT EXPRESSION
# =========================================================

def analyze_recent_expression(
    recent_messages: list[str]
) -> dict:

    recent_messages = [
        message
        for message
        in recent_messages
        if message
    ]

    return {

        "message_count":
            len(
                recent_messages
            ),

        "words":
            count_tracked_words(
                recent_messages
            ),

        "openers":
            count_openers(
                recent_messages
            ),

        "emojis":
            count_tracked_emojis(
                recent_messages
            ),

        "question_density":
            get_question_density(
                recent_messages
            ),

        "exclamation_density":
            get_exclamation_density(
                recent_messages
            ),
    }


# =========================================================
# BUILD EXPRESSION PLAN
# =========================================================

def build_expression_plan(
    *,
    recent_messages: list[str],
    tone: str,
    mood: str,
    relationship_text: str = "",
    is_hanae: bool = False
) -> ExpressionPlan:

    analysis = (
        analyze_recent_expression(
            recent_messages
        )
    )

    plan = ExpressionPlan()

    # =====================================================
    # BASE STYLE FROM TONE
    # =====================================================

    tone = (
        tone or "relaxed"
    ).lower()

    mood = (
        mood or "normal"
    ).lower()

    tone_map = {

        "relaxed":
            "natural",

        "dry":
            "dry",

        "amused":
            "playful",

        "smug":
            "smug",

        "soft":
            "soft",

        "annoyed":
            "deadpan",

        "serious":
            "serious",

        "confused":
            "natural",

        "playful":
            "playful",

        "gen_z":
            "natural",
    }

    plan.style = (
        tone_map.get(
            tone,
            "natural"
        )
    )

    # =====================================================
    # MOOD MODIFIERS
    # =====================================================

    if mood == "sleepy":

        plan.preferred_energy = "low"

        plan.sentence_shape = "short"

        plan.emoji_level = "low"

        plan.notes.append(
            "Etwas müder und knapper schreiben."
        )

    elif mood == "annoyed":

        plan.preferred_energy = "low"

        plan.sentence_shape = "short"

        plan.emoji_level = "low"

        plan.notes.append(
            "Trockener und weniger enthusiastisch."
        )

    elif mood == "chaotic":

        plan.preferred_energy = "high"

        plan.sentence_shape = "fragmented"

        plan.notes.append(
            "Etwas impulsiver, aber nicht random."
        )

    elif mood == "soft":

        plan.preferred_energy = "warm"

        plan.notes.append(
            "Etwas wärmer, ohne kitschig zu werden."
        )

    else:

        plan.preferred_energy = "relaxed"

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    relationship_lower = (
        relationship_text
        or ""
    ).lower()

    if is_hanae:

        plan.slang_level = "medium"

        plan.notes.append(
            "Mit Hanae vertrauter und direkter."
        )

    elif any(
        token in relationship_lower
        for token in [
            "vertraut",
            "locker",
            "freund",
            "guter humor",
            "teasing funktioniert",
            "enge",
        ]
    ):

        plan.slang_level = "medium"

        plan.notes.append(
            "Vertrauter Umgang erlaubt."
        )

    else:

        plan.slang_level = "light"

    # =====================================================
    # WORD OVERUSE
    # =====================================================

    word_counter = (
        analysis[
            "words"
        ]
    )

    for word, count in (
        word_counter.items()
    ):

        if count >= 2:

            plan.avoid_words.append(
                word
            )

    # =====================================================
    # OPENER OVERUSE
    # =====================================================

    opener_counter = (
        analysis[
            "openers"
        ]
    )

    for opener, count in (
        opener_counter.items()
    ):

        if count >= 2:

            plan.avoid_openers.append(
                opener
            )

    # =====================================================
    # EMOJI OVERUSE
    # =====================================================

    emoji_counter = (
        analysis[
            "emojis"
        ]
    )

    for emoji, count in (
        emoji_counter.items()
    ):

        if count >= 2:

            plan.avoid_emojis.append(
                emoji
            )

    # =====================================================
    # QUESTION OVERUSE
    # =====================================================

    if (
        analysis[
            "question_density"
        ]
        >= 0.60
    ):

        plan.notes.append(
            "Zuletzt wurden zu viele Fragen gestellt."
        )

    # =====================================================
    # EXCLAMATION OVERUSE
    # =====================================================

    if (
        analysis[
            "exclamation_density"
        ]
        >= 0.60
    ):

        plan.notes.append(
            "Weniger Ausrufezeichen benutzen."
        )

    # =====================================================
    # EMOJI LEVEL
    # =====================================================

    total_recent_emojis = sum(
        emoji_counter.values()
    )

    if total_recent_emojis >= 4:

        plan.emoji_level = "low"

    elif total_recent_emojis >= 2:

        plan.emoji_level = "light"

    else:

        plan.emoji_level = "natural"

    # =====================================================
    # CLEAN DUPLICATES
    # =====================================================

    plan.avoid_words = list(
        dict.fromkeys(
            plan.avoid_words
        )
    )

    plan.avoid_openers = list(
        dict.fromkeys(
            plan.avoid_openers
        )
    )

    plan.avoid_emojis = list(
        dict.fromkeys(
            plan.avoid_emojis
        )
    )

    return plan


# =========================================================
# FORMAT FOR WRITER
# =========================================================

def format_expression_plan(
    plan: ExpressionPlan
) -> str:

    avoid_words = (
        ", ".join(
            plan.avoid_words
        )
        if plan.avoid_words
        else "Keine."
    )

    avoid_openers = (
        ", ".join(
            plan.avoid_openers
        )
        if plan.avoid_openers
        else "Keine."
    )

    avoid_emojis = (
        " ".join(
            plan.avoid_emojis
        )
        if plan.avoid_emojis
        else "Keine."
    )

    notes = (
        "\n".join(
            f"- {note}"
            for note
            in plan.notes
        )
        if plan.notes
        else "Keine besonderen Hinweise."
    )

    return f"""
Style:
{plan.style}

Slang level:
{plan.slang_level}

Emoji level:
{plan.emoji_level}

Sentence shape:
{plan.sentence_shape}

Lowercase preferred:
{plan.lowercase_preferred}

Fragmented sentences allowed:
{plan.allow_fragmented_sentences}

Preferred energy:
{plan.preferred_energy}

Avoid words:
{avoid_words}

Avoid openers:
{avoid_openers}

Avoid emojis:
{avoid_emojis}

Notes:
{notes}
""".strip()


# =========================================================
# HARD EXPRESSION CHECK
# =========================================================

def expression_violation_reasons(
    answer: str,
    plan: ExpressionPlan
) -> list[str]:

    reasons = []

    normalized = (
        normalize_text(
            answer
        )
    )

    opener = (
        detect_opener(
            answer
        )
    )

    if (
        opener
        and
        opener
        in plan.avoid_openers
    ):

        reasons.append(
            f"overused_opener:{opener}"
        )

    words = (
        extract_words(
            answer
        )
    )

    lowered_words = {
        word.lower()
        for word
        in words
    }

    for word in plan.avoid_words:

        if word in lowered_words:

            reasons.append(
                f"overused_word:{word}"
            )

    for emoji in plan.avoid_emojis:

        if emoji in answer:

            reasons.append(
                f"overused_emoji:{emoji}"
            )

    return reasons


# =========================================================
# DEBUG
# =========================================================

def format_expression_debug(
    plan: ExpressionPlan
) -> str:

    return (
        "[EXPRESSION] "
        f"v={EXPRESSION_VERSION} "
        f"style={plan.style} "
        f"slang={plan.slang_level} "
        f"emoji={plan.emoji_level} "
        f"shape={plan.sentence_shape} "
        f"avoid_words={plan.avoid_words} "
        f"avoid_openers={plan.avoid_openers} "
        f"avoid_emojis={plan.avoid_emojis}"
    )
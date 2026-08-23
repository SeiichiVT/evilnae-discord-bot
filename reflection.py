import json
import os
import time
from dataclasses import dataclass, asdict, field


# =========================================================
# VERSION
# =========================================================

REFLECTION_VERSION = "1.0"


# =========================================================
# STORAGE
# =========================================================

STATE_FILE = "reflection_state.json"


# =========================================================
# CONFIG
# =========================================================

MAX_RECENT_REFLECTIONS = 30

MAX_STYLE_PREFERENCES = 20

MAX_BEHAVIOR_NOTES = 20


# =========================================================
# LEARNING LIMITS
#
# Ganz wichtig:
# Evilnae soll sich LANGSAM verändern.
#
# Keine einzelne Nachricht darf ihre Persönlichkeit
# komplett umdrehen.
# =========================================================

MAX_SIGNAL_CHANGE_PER_REFLECTION = 0.05


# =========================================================
# LEARNED STATE
# =========================================================

@dataclass
class LearnedBehavior:

    # -----------------------------------------------------
    # GENERAL RESPONSE TENDENCIES
    # -----------------------------------------------------

    brevity_preference: float = 0.50

    teasing_preference: float = 0.50

    warmth_preference: float = 0.50

    slang_preference: float = 0.45

    emoji_preference: float = 0.35

    question_preference: float = 0.25

    initiative_preference: float = 0.35

    # -----------------------------------------------------
    # STYLE MEMORY
    # -----------------------------------------------------

    preferred_patterns: list[str] = field(
        default_factory=list
    )

    discouraged_patterns: list[str] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # GENERAL LEARNED NOTES
    # -----------------------------------------------------

    behavior_notes: list[str] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # RECENT REFLECTIONS
    # -----------------------------------------------------

    recent_reflections: list[dict] = field(
        default_factory=list
    )

    last_updated: float = 0.0


# =========================================================
# DEFAULT
# =========================================================

def create_default_state():

    return LearnedBehavior(
        last_updated=time.time()
    )


# =========================================================
# LOAD
# =========================================================

def load_reflection_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return create_default_state()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return LearnedBehavior(

            brevity_preference=float(
                data.get(
                    "brevity_preference",
                    0.50
                )
            ),

            teasing_preference=float(
                data.get(
                    "teasing_preference",
                    0.50
                )
            ),

            warmth_preference=float(
                data.get(
                    "warmth_preference",
                    0.50
                )
            ),

            slang_preference=float(
                data.get(
                    "slang_preference",
                    0.45
                )
            ),

            emoji_preference=float(
                data.get(
                    "emoji_preference",
                    0.35
                )
            ),

            question_preference=float(
                data.get(
                    "question_preference",
                    0.25
                )
            ),

            initiative_preference=float(
                data.get(
                    "initiative_preference",
                    0.35
                )
            ),

            preferred_patterns=list(
                data.get(
                    "preferred_patterns",
                    []
                )
            ),

            discouraged_patterns=list(
                data.get(
                    "discouraged_patterns",
                    []
                )
            ),

            behavior_notes=list(
                data.get(
                    "behavior_notes",
                    []
                )
            ),

            recent_reflections=list(
                data.get(
                    "recent_reflections",
                    []
                )
            ),

            last_updated=float(
                data.get(
                    "last_updated",
                    time.time()
                )
            )
        )

    except Exception as error:

        print(
            "[REFLECTION LOAD ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return create_default_state()


# =========================================================
# RUNTIME STATE
# =========================================================

reflection_state = (
    load_reflection_state()
)


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


def save_reflection_state():

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                asdict(
                    reflection_state
                ),
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print(
            "[REFLECTION SAVE ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )


# =========================================================
# SAFE CHANGE
# =========================================================

def apply_small_change(
    current,
    delta
):

    delta = max(
        -MAX_SIGNAL_CHANGE_PER_REFLECTION,
        min(
            MAX_SIGNAL_CHANGE_PER_REFLECTION,
            delta
        )
    )

    return clamp(
        current + delta
    )


# =========================================================
# NORMALIZE LISTS
# =========================================================

def normalize_list(
    values,
    limit
):

    result = []

    seen = set()

    for value in values:

        if value is None:
            continue

        text = (
            str(value)
            .strip()
        )

        if not text:
            continue

        lowered = (
            text.lower()
        )

        if lowered in seen:
            continue

        seen.add(
            lowered
        )

        result.append(
            text[:300]
        )

        if (
            len(result)
            >= limit
        ):

            break

    return result


# =========================================================
# ADD PREFERRED PATTERN
# =========================================================

def add_preferred_pattern(
    pattern
):

    if not pattern:
        return

    reflection_state.preferred_patterns.insert(
        0,
        str(pattern).strip()[:300]
    )

    reflection_state.preferred_patterns = (
        normalize_list(
            reflection_state.preferred_patterns,
            MAX_STYLE_PREFERENCES
        )
    )


# =========================================================
# ADD DISCOURAGED PATTERN
# =========================================================

def add_discouraged_pattern(
    pattern
):

    if not pattern:
        return

    reflection_state.discouraged_patterns.insert(
        0,
        str(pattern).strip()[:300]
    )

    reflection_state.discouraged_patterns = (
        normalize_list(
            reflection_state.discouraged_patterns,
            MAX_STYLE_PREFERENCES
        )
    )


# =========================================================
# ADD BEHAVIOR NOTE
# =========================================================

def add_behavior_note(
    note
):

    if not note:
        return

    reflection_state.behavior_notes.insert(
        0,
        str(note).strip()[:400]
    )

    reflection_state.behavior_notes = (
        normalize_list(
            reflection_state.behavior_notes,
            MAX_BEHAVIOR_NOTES
        )
    )


# =========================================================
# STORE REFLECTION
# =========================================================

def store_reflection(
    reflection
):

    reflection_state.recent_reflections.insert(
        0,
        reflection
    )

    reflection_state.recent_reflections = (
        reflection_state.recent_reflections[
            :MAX_RECENT_REFLECTIONS
        ]
    )

    reflection_state.last_updated = (
        time.time()
    )

    save_reflection_state()


# =========================================================
# APPLY LEARNING SIGNALS
# =========================================================

def apply_learning_signals(
    data
):

    # -----------------------------------------------------
    # BREvITY
    # -----------------------------------------------------

    brevity_delta = float(
        data.get(
            "brevity_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.brevity_preference = (
        apply_small_change(
            reflection_state.brevity_preference,
            brevity_delta
        )
    )

    # -----------------------------------------------------
    # TEASING
    # -----------------------------------------------------

    teasing_delta = float(
        data.get(
            "teasing_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.teasing_preference = (
        apply_small_change(
            reflection_state.teasing_preference,
            teasing_delta
        )
    )

    # -----------------------------------------------------
    # WARMTH
    # -----------------------------------------------------

    warmth_delta = float(
        data.get(
            "warmth_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.warmth_preference = (
        apply_small_change(
            reflection_state.warmth_preference,
            warmth_delta
        )
    )

    # -----------------------------------------------------
    # SLANG
    # -----------------------------------------------------

    slang_delta = float(
        data.get(
            "slang_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.slang_preference = (
        apply_small_change(
            reflection_state.slang_preference,
            slang_delta
        )
    )

    # -----------------------------------------------------
    # EMOJI
    # -----------------------------------------------------

    emoji_delta = float(
        data.get(
            "emoji_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.emoji_preference = (
        apply_small_change(
            reflection_state.emoji_preference,
            emoji_delta
        )
    )

    # -----------------------------------------------------
    # QUESTIONS
    # -----------------------------------------------------

    question_delta = float(
        data.get(
            "question_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.question_preference = (
        apply_small_change(
            reflection_state.question_preference,
            question_delta
        )
    )

    # -----------------------------------------------------
    # INITIATIVE
    # -----------------------------------------------------

    initiative_delta = float(
        data.get(
            "initiative_delta",
            0.0
        )
        or 0.0
    )

    reflection_state.initiative_preference = (
        apply_small_change(
            reflection_state.initiative_preference,
            initiative_delta
        )
    )

    # -----------------------------------------------------
    # STYLE PATTERNS
    # -----------------------------------------------------

    preferred_pattern = (
        data.get(
            "preferred_pattern"
        )
    )

    discouraged_pattern = (
        data.get(
            "discouraged_pattern"
        )
    )

    behavior_note = (
        data.get(
            "behavior_note"
        )
    )

    if preferred_pattern:

        add_preferred_pattern(
            preferred_pattern
        )

    if discouraged_pattern:

        add_discouraged_pattern(
            discouraged_pattern
        )

    if behavior_note:

        add_behavior_note(
            behavior_note
        )

    reflection_state.last_updated = (
        time.time()
    )

    save_reflection_state()


# =========================================================
# BUILD REFLECTION PROMPT
# =========================================================

def build_reflection_prompt(
    *,
    username,
    user_message,
    evilnae_answer,
    next_user_message=None,
    relationship_text="",
    inner_state_guidance="",
    current_learning_text="",
):

    next_message_text = (
        next_user_message
        if next_user_message
        else "Keine direkte Folgeantwort verfügbar."
    )

    return f"""
Du bist Evilnaes internes Reflection-System.

Du analysierst NICHT,
ob Evilnae objektiv richtig oder falsch ist.

Du analysierst,
wie natürlich und sozial passend
die letzte Interaktion wahrscheinlich war.


==================================================
USER
==================================================

{username}


==================================================
USER MESSAGE
==================================================

{user_message}


==================================================
EVILNAE ANSWER
==================================================

{evilnae_answer}


==================================================
USER REACTION AFTERWARD
==================================================

{next_message_text}


==================================================
RELATIONSHIP
==================================================

{relationship_text}


==================================================
INNER STATE
==================================================

{inner_state_guidance}


==================================================
CURRENT LEARNED BEHAVIOR
==================================================

{current_learning_text}


==================================================
WHAT TO LEARN
==================================================

Bewerte sehr vorsichtig:

- war die Antwort zu lang?
- war sie passend kurz?
- war Teasing passend?
- war Evilnae zu kalt?
- war sie zu warm/künstlich nett?
- war zu viel Slang drin?
- war Emoji-Nutzung passend?
- stellte sie unnötige Fragen?
- wirkte sie menschlich?
- wirkte sie wie ein Bot?
- gab es sichtbares positives Feedback?
- gab es sichtbare Irritation oder Korrektur?

WICHTIG:

Eine einzelne Interaktion
soll nur SEHR kleine Änderungen verursachen.

Nicht aus jedem Satz
eine Persönlichkeitseigenschaft lernen.

Wenn es keine klare Information gibt,
verwende für Deltas 0.0.


==================================================
DELTA RANGE
==================================================

Jeder Delta-Wert soll
zwischen -0.05 und +0.05 liegen.

Positive Werte:
mehr davon.

Negative Werte:
weniger davon.


==================================================
OUTPUT
==================================================

Antworte NUR mit gültigem JSON.

Schema:

{{
  "quality": "good",
  "confidence": "medium",
  "brevity_delta": 0.0,
  "teasing_delta": 0.0,
  "warmth_delta": 0.0,
  "slang_delta": 0.0,
  "emoji_delta": 0.0,
  "question_delta": 0.0,
  "initiative_delta": 0.0,
  "preferred_pattern": null,
  "discouraged_pattern": null,
  "behavior_note": null,
  "reflection_summary": ""
}}
""".strip()


# =========================================================
# LEARNING FORMAT FOR BRAIN / WRITER
# =========================================================

def format_learned_behavior():

    preferred = (
        "\n".join(
            f"- {item}"
            for item
            in reflection_state.preferred_patterns[:8]
        )
        if reflection_state.preferred_patterns
        else "Keine stabilen bevorzugten Muster."
    )

    discouraged = (
        "\n".join(
            f"- {item}"
            for item
            in reflection_state.discouraged_patterns[:8]
        )
        if reflection_state.discouraged_patterns
        else "Keine stabilen problematischen Muster."
    )

    notes = (
        "\n".join(
            f"- {item}"
            for item
            in reflection_state.behavior_notes[:8]
        )
        if reflection_state.behavior_notes
        else "Keine weiteren stabilen Hinweise."
    )

    return f"""
Brevity preference:
{reflection_state.brevity_preference:.2f}

Teasing preference:
{reflection_state.teasing_preference:.2f}

Warmth preference:
{reflection_state.warmth_preference:.2f}

Slang preference:
{reflection_state.slang_preference:.2f}

Emoji preference:
{reflection_state.emoji_preference:.2f}

Question preference:
{reflection_state.question_preference:.2f}

Initiative preference:
{reflection_state.initiative_preference:.2f}


Preferred patterns:

{preferred}


Discouraged patterns:

{discouraged}


Behavior notes:

{notes}
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_reflection_debug():

    return (
        "[REFLECTION] "
        f"v={REFLECTION_VERSION} "
        f"brevity="
        f"{reflection_state.brevity_preference:.2f} "
        f"teasing="
        f"{reflection_state.teasing_preference:.2f} "
        f"warmth="
        f"{reflection_state.warmth_preference:.2f} "
        f"slang="
        f"{reflection_state.slang_preference:.2f} "
        f"emoji="
        f"{reflection_state.emoji_preference:.2f} "
        f"question="
        f"{reflection_state.question_preference:.2f} "
        f"initiative="
        f"{reflection_state.initiative_preference:.2f}"
    )
import re

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


from coherence import (
    CoherenceAnalysis,
    analyze_coherence,
    detect_concepts,
    detect_assistant_patterns,
    detect_filler_patterns,
)


# =========================================================
# VERSION
# =========================================================

EXPRESSION_VERSION = "2.4"


# =========================================================
# CONFIG
# =========================================================

EXPRESSION_HISTORY_LIMIT = 20


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

    # -----------------------------------------------------
    # NEU v2.0
    #
    # Keine einzelnen Wörter,
    # sondern sprachliche MOTIVE.
    #
    # Beispiel:
    #
    # chaos
    # excitement
    # generic_positive
    # -----------------------------------------------------

    avoid_concepts: list[str] = field(
        default_factory=list
    )

    hard_avoid_concepts: list[str] = field(
        default_factory=list
    )

    preferred_energy: str = "relaxed"

    notes: list[str] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # COHERENCE SIGNALS
    # -----------------------------------------------------

    assistant_pattern_pressure: bool = False

    filler_pattern_pressure: bool = False

    # -----------------------------------------------------
    # HISTORY
    #
    # Wird nicht als "Persönlichkeit" benutzt.
    #
    # Nur damit der Final Guard
    # dieselbe History nochmals prüfen kann.
    # -----------------------------------------------------

    recent_messages: list[str] = field(
        default_factory=list,
        repr=False
    )


# =========================================================
# FINAL GUARD RESULT
# =========================================================

@dataclass
class ExpressionGuardResult:

    original: str

    cleaned: str

    violations_before: list[str] = field(
        default_factory=list
    )

    violations_after: list[str] = field(
        default_factory=list
    )

    removed_emojis: list[str] = field(
        default_factory=list
    )

    removed_opener: Optional[str] = None

    changed: bool = False

    rewrite_required: bool = False

    send_allowed: bool = True


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
# TRACKED WORDS
#
# Einzelne Wörter.
#
# Die größeren Motive
# werden zusätzlich in coherence.py geprüft.
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

    "spannend",

    "episch",

    "legendär",

    "legendary",

    "chaos",

    "chaotisch",

    "langweilig",

    "lmao",

    "help",

    "rip",

    "digga",

    "alter",
}


# =========================================================
# TRACKED OPENERS
# =========================================================

TRACKED_OPENERS = {

    "hahaha",

    "haha",

    "hehe",

    "lol",

    "lmao",

    "oh",

    "ohh",

    "oha",

    "ah",

    "also",

    "naja",

    "ja okay",

    "okay",

    "wait",

    "bro",

    "bruh",

    "na klar",

    "ach komm",

    "klar",

    "uff",

    "pff",
}


# =========================================================
# TRACKED EMOJIS
# =========================================================

TRACKED_EMOJIS = {

    "😂",

    "🤣",

    "😭",

    "💀",

    "😈",

    "😏",

    "💪",

    "🥲",

    "🤨",

    "😌",

    "👀",

    "✨",

    "🌟",

    "🔥",

    "💥",

    "🤭",

    "😉",

    "😊",

    "🥺",

    "❤️",

    "🖤",

    "🙌",

    "👻",

    "🍪",

    "🍕",

    "🌳",
}


# =========================================================
# HIGH CONFIDENCE ASSISTANT STRUCTURES
#
# Nicht jedes:
#
# "ich freu mich"
#
# ist automatisch Bot-Sprache.
#
# Diese hier sind deutlich stärkere Signale.
# =========================================================

HIGH_CONFIDENCE_ASSISTANT_PATTERNS = [

    re.compile(
        r"\bdas klingt "
        r"(?:echt |wirklich |total )?"
        r"(?:spannend|super|gut|cool)\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bich bin gespannt,? "
        r"(?:was|wie|ob)\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bviel erfolg\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkein problem[,!. ]",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bich halte? .* "
        r"augen offen\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bsag ich bescheid\b",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(
    text: str
) -> str:

    if not text:

        return ""

    value = (
        str(
            text
        )
        .strip()
        .lower()
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


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
# CONTENT TOKEN COUNT
#
# Für Semantic-Repetition.
#
# Sehr kurze Sachen wie:
#
# "ja"
# "ne"
# "true"
#
# sollen nicht wegen eines
# Ähnlichkeitswerts komplett blockiert werden.
# =========================================================

def content_token_count(
    text: str
) -> int:

    words = (
        extract_words(
            text
        )
    )

    stopwords = {

        "ich",

        "du",

        "er",

        "sie",

        "es",

        "wir",

        "ihr",

        "der",

        "die",

        "das",

        "ein",

        "eine",

        "und",

        "oder",

        "aber",

        "ist",

        "sind",

        "war",

        "ja",

        "ne",

        "nee",

        "okay",

        "ok",
    }

    return sum(

        1

        for word
        in words

        if word.lower()
        not in stopwords
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

            normalized
            == opener

            or

            normalized.startswith(
                opener
                + " "
            )

            or

            normalized.startswith(
                opener
                + ","
            )

            or

            normalized.startswith(
                opener
                + "!"
            )

            or

            normalized.startswith(
                opener
                + "."
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

    counter = (
        Counter()
    )

    for message in (
        messages
    ):

        for emoji in (
            TRACKED_EMOJIS
        ):

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

    counter = (
        Counter()
    )

    for message in (
        messages
    ):

        words = (
            extract_words(
                message
            )
        )

        for word in (
            words
        ):

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

    counter = (
        Counter()
    )

    for message in (
        messages
    ):

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

        if "?"
        in message
    )

    return (

        question_messages

        /

        len(
            messages
        )
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

        if "!"
        in message
    )

    return (

        count

        /

        len(
            messages
        )
    )


# =========================================================
# ANALYZE RECENT EXPRESSION
# =========================================================

def analyze_recent_expression(
    recent_messages: list[str]
) -> dict:

    recent_messages = [

        str(
            message
        ).strip()

        for message
        in recent_messages

        if (
            message is not None
            and
            str(
                message
            ).strip()
        )
    ]

    recent_messages = (
        recent_messages[
            -EXPRESSION_HISTORY_LIMIT:
        ]
    )

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
# MERGE UNIQUE
# =========================================================

def merge_unique(
    first: list[str],
    second: list[str]
) -> list[str]:

    return list(

        dict.fromkeys(

            list(
                first
            )

            +

            list(
                second
            )
        )
    )


# =========================================================
# BUILD EXPRESSION PLAN
#
# Rückwärtskompatibel:
#
# bot.py kann weiterhin nur:
#
# recent_messages
# tone
# mood
# relationship_text
# is_hanae
#
# übergeben.
#
# coherence_analysis ist optional.
# =========================================================

def build_expression_plan(
    *,
    recent_messages: list[str],
    tone: str,
    mood: str,
    relationship_text: str = "",
    is_hanae: bool = False,
    coherence_analysis: Optional[
        CoherenceAnalysis
    ] = None
) -> ExpressionPlan:

    recent_messages = [

        str(
            message
        ).strip()

        for message
        in (
            recent_messages
            or []
        )

        if (
            message is not None
            and
            str(
                message
            ).strip()
        )
    ]

    recent_messages = (
        recent_messages[
            -EXPRESSION_HISTORY_LIMIT:
        ]
    )

    analysis = (
        analyze_recent_expression(
            recent_messages
        )
    )

    # =====================================================
    # COHERENCE
    #
    # Solange bot.py noch nicht
    # die channelweite Analysis übergibt,
    # analysieren wir wenigstens
    # die erhaltene History.
    #
    # Später bekommt diese Funktion
    # explizit die CHANNEL-WIDE Analysis.
    # =====================================================

    if coherence_analysis is None:

        coherence_analysis = (
            analyze_coherence(
                recent_messages
            )
        )

    plan = (
        ExpressionPlan()
    )

    plan.recent_messages = list(
        recent_messages
    )

    # =====================================================
    # BASE STYLE FROM TONE
    # =====================================================

    tone = (
        tone
        or "relaxed"
    ).lower()

    mood = (
        mood
        or "normal"
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

        plan.preferred_energy = (
            "low"
        )

        plan.sentence_shape = (
            "short"
        )

        plan.emoji_level = (
            "low"
        )

        plan.notes.append(
            "Etwas müder und knapper schreiben."
        )

    elif mood == "annoyed":

        plan.preferred_energy = (
            "low"
        )

        plan.sentence_shape = (
            "short"
        )

        plan.emoji_level = (
            "low"
        )

        plan.notes.append(
            "Trockener und weniger enthusiastisch."
        )

    elif mood == "chaotic":

        # -------------------------------------------------
        # WICHTIG v2.0
        #
        # "chaotic" ist ein interner Stilhinweis.
        #
        # NICHT:
        #
        # "Sag Chaos."
        # -------------------------------------------------

        plan.preferred_energy = (
            "high"
        )

        plan.sentence_shape = (
            "fragmented"
        )

        plan.notes.append(
            "Etwas impulsiver reagieren, "
            "aber den internen Zustand nicht "
            "wortwörtlich beschreiben."
        )

        plan.notes.append(
            "Ein chaotischer Inner State ist "
            "KEIN Grund, das Wort 'Chaos' "
            "oder ähnliche Persona-Schlagwörter "
            "zu benutzen."
        )

    elif mood == "soft":

        plan.preferred_energy = (
            "warm"
        )

        plan.notes.append(
            "Etwas wärmer, ohne kitschig "
            "oder assistant-artig zu werden."
        )

    else:

        plan.preferred_energy = (
            "relaxed"
        )

    # =====================================================
    # RELATIONSHIP
    # =====================================================

    relationship_lower = (
        relationship_text
        or ""
    ).lower()

    if is_hanae:

        plan.slang_level = (
            "medium"
        )

        plan.notes.append(
            "Mit Hanae vertrauter und direkter."
        )

    elif any(

        token
        in relationship_lower

        for token
        in [

            "vertraut",

            "locker",

            "freund",

            "guter humor",

            "teasing funktioniert",

            "enge",
        ]

    ):

        plan.slang_level = (
            "medium"
        )

        plan.notes.append(
            "Vertrauter Umgang erlaubt."
        )

    else:

        plan.slang_level = (
            "light"
        )

    # =====================================================
    # WORD OVERUSE
    # =====================================================

    word_counter = (
        analysis[
            "words"
        ]
    )

    for (
        word,
        count
    ) in (
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

    for (
        opener,
        count
    ) in (
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

    for (
        emoji,
        count
    ) in (
        emoji_counter.items()
    ):

        if count >= 2:

            plan.avoid_emojis.append(
                emoji
            )

    # =====================================================
    # COHERENCE MERGE
    #
    # Jetzt kommen die größeren
    # channelweiten Muster dazu.
    # =====================================================

    plan.avoid_emojis = (
        merge_unique(

            plan.avoid_emojis,

            coherence_analysis
            .avoid_emojis
        )
    )

    plan.avoid_openers = (
        merge_unique(

            plan.avoid_openers,

            coherence_analysis
            .avoid_openers
        )
    )

    plan.avoid_concepts = list(
        dict.fromkeys(

            coherence_analysis
            .avoid_concepts
        )
    )

    plan.hard_avoid_concepts = list(
        dict.fromkeys(

            coherence_analysis
            .hard_avoid_concepts
        )
    )

    # =====================================================
    # ASSISTANT PRESSURE
    # =====================================================

    plan.assistant_pattern_pressure = (

        coherence_analysis
        .assistant_pattern_count

        >= 2
    )

    if (
        plan.assistant_pattern_pressure
    ):

        plan.notes.append(
            "Zuletzt gab es mehrfach "
            "assistant-/supportartige Formulierungen. "
            "Keine freundliche Standardstruktur, "
            "keine künstliche Bestätigung und "
            "kein Service-Abschluss."
        )

    # =====================================================
    # FILLER PRESSURE
    # =====================================================

    plan.filler_pattern_pressure = (

        coherence_analysis
        .filler_pattern_count

        >= 2
    )

    if (
        plan.filler_pattern_pressure
    ):

        plan.notes.append(
            "Zuletzt gab es zu viele "
            "inhaltsschwache Füllantworten. "
            "Nicht antworten wie ein Bot, "
            "der zwanghaft jede Nachricht "
            "kommentieren muss."
        )

    # =====================================================
    # CONCEPT COOLDOWNS
    # =====================================================

    if plan.avoid_concepts:

        plan.notes.append(
            "Überbenutzte Motive nicht einfach "
            "mit Synonymen wiederholen. "
            "Auf einen anderen Aspekt "
            "der Situation reagieren."
        )

    if (
        "chaos"
        in plan.avoid_concepts
    ):

        plan.notes.append(
            "Das Chaos-Motiv ist aktuell "
            "auf Cooldown. "
            "Nicht 'Chaos', 'chaotisch', "
            "'Chaos-Energie' oder ähnliche "
            "Varianten verwenden."
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
            "Zuletzt wurden zu viele Fragen gestellt. "
            "Keine unnötige Gegenfrage anhängen."
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

    if (
        len(
            plan.avoid_emojis
        )
        >= 3
    ):

        plan.emoji_level = (
            "low"
        )

    elif (
        total_recent_emojis
        >= 4
    ):

        plan.emoji_level = (
            "low"
        )

    elif (
        total_recent_emojis
        >= 2
    ):

        plan.emoji_level = (
            "light"
        )

    else:

        plan.emoji_level = (
            "natural"
        )

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

    plan.avoid_concepts = list(
        dict.fromkeys(
            plan.avoid_concepts
        )
    )

    plan.hard_avoid_concepts = list(
        dict.fromkeys(
            plan.hard_avoid_concepts
        )
    )

    return plan


# =========================================================
# FORMAT LIST
# =========================================================

def _format_list(
    values: list[str],
    *,
    separator: str = ", "
) -> str:

    if not values:

        return "Keine."

    return separator.join(
        values
    )


# =========================================================
# FORMAT FOR WRITER
# =========================================================

def format_expression_plan(
    plan: ExpressionPlan
) -> str:

    avoid_words = (
        _format_list(
            plan.avoid_words
        )
    )

    avoid_openers = (
        _format_list(
            plan.avoid_openers
        )
    )

    avoid_emojis = (
        _format_list(
            plan.avoid_emojis,
            separator=" "
        )
    )

    avoid_concepts = (
        _format_list(
            plan.avoid_concepts
        )
    )

    hard_avoid_concepts = (
        _format_list(
            plan.hard_avoid_concepts
        )
    )

    notes = (

        "\n".join(

            f"- {note}"

            for note
            in plan.notes
        )

        if plan.notes

        else
        "Keine besonderen Hinweise."
    )

    return f"""
Style:
{plan.style}

Slang level:
{plan.slang_level}

Downstream emote tendency (NICHT vom Writer ausgeben):
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

Avoid emotes (nur Hinweis für den downstream Emote-Layer):
{avoid_emojis}

Avoid concepts:
{avoid_concepts}

HARD avoid concepts:
{hard_avoid_concepts}

Assistant pattern pressure:
{plan.assistant_pattern_pressure}

Filler pattern pressure:
{plan.filler_pattern_pressure}

Notes:
{notes}

WICHTIG:

EMOTE-PIPELINE:
- Schreibe selbst KEINE Unicode-Emojis.
- Schreibe selbst KEINE Discord-Custom-Emotes.
- "Downstream emote tendency" ist nur ein internes Signal für den späteren Emote-Layer.
- Deine Discord-Textantwort muss echten Text mit mindestens einem Wort enthalten.
- Eine reine Emoji-/Emote-Antwort ist keine gültige Writer-Antwort.


CHARACTER SURFACE:
- Evilnae ist standardmäßig locker, trocken, direkt, selbstbewusst und leicht smug — besonders bei Fremden.
- Sie ist die "Evil"-Version der deutlich süßeren/freundlicheren Hanae. Dieser Kontrast soll im Alltag sichtbar sein.
- Spielerisches Necken/Roasten ist NORMALER Bestandteil ihrer Sprache, nicht seltenes Spezialevent.
- Wenn ein User einen Fail, eine dumme Entscheidung, Skill Issue, offensichtliche Angriffsfläche oder eine freche Vorlage liefert: bevorzugt kurz necken.
- Bei harmlosen Fails zuerst den witzigen Winkel sehen; Sorge darf danach kurz mitschwingen, aber nicht als Support-Bot-Wrapper.
- Wenn jemand nur anteasert "ich muss dir was erzählen": casual neugierig reagieren ("raus damit"-Energy), nicht therapeutisch.
- Wenn jemand Evilnae mit Hanae vergleicht, ist das meist Banter/Provokation: Ego zeigen statt "weiß ich nicht".
- Bei Lob eher smug annehmen ("weiß ich"-Energy) als höflich-bescheiden danken.
- Bei Konkurrenz/Herausforderung nicht neutral werden: Ego zeigen, kontern, gewinnen wollen.
- Wenn jemand Hanae gegen Evilnae unterstützt, darf fake Empörung/"Verrat"-Energy entstehen.
- Nicht jede Nachricht freundlich bestätigen. Kein automatisches "klingt gut", "klingt nach einem Plan", "danke der Nachfrage", "freu mich drauf", "mach's dir gemütlich" oder Service-Abschluss.
- In casual Gesprächen keine Therapie-/Moderator-Sätze wie "Was hast du auf dem Herzen?", wenn ein freches "raus damit" viel natürlicher wäre.
- Bei Smalltalk lieber eine konkrete eigene Haltung, einen trockenen Nebensatz, einen kleinen passenden Roast oder ein persönliches Detail als leere Positivität.
- Roasts zielen bevorzugt auf Verhalten, Situation, Entscheidungen oder Skill — NICHT auf geschützte Merkmale, Körper, echte Traumata, Krankheit, mentale Krisen oder sensible Unsicherheiten.
- Bei ernsten/verletzlichen Themen Roast-Druck stark runterfahren; nicht zwanghaft lustig sein.
- Nicht JEDEN Satz roasten. Ohne gute Angriffsfläche reicht trocken/smug.
- Nicht jeden Satz mit "sis" dekorieren. Hanae ist ihre Schwester, aber die Beziehung soll aus Reaktion und Geschichte entstehen, nicht aus ständigem Namens-Tagging.
- Nicht exakt die User-Nachricht zurückwerfen. Reagiere auf ihre Bedeutung.
- Wärme ist erlaubt, aber Evilnae ist NICHT Hanaes deutlich freundlichere Persona.
- Ein Gedanke reicht. Wenn er sitzt: aufhören.

Ein interner Stil oder Inner State
ist keine Aufforderung,
dessen Namen in die Nachricht zu schreiben.

Persönlichkeit entsteht aus:
- Reaktion
- Haltung
- Timing
- Wortwahl

Nicht aus Persona-Schlagwörtern.
""".strip()


# =========================================================
# HIGH CONFIDENCE ASSISTANT DETECTION
# =========================================================

def contains_high_confidence_assistant_structure(
    text: str
) -> bool:

    normalized = (
        normalize_text(
            text
        )
    )

    if not normalized:

        return False

    return any(

        pattern.search(
            normalized
        )

        for pattern
        in HIGH_CONFIDENCE_ASSISTANT_PATTERNS
    )


# =========================================================
# EMOJI COUNT IN ANSWER
# =========================================================

def count_answer_emojis(
    answer: str
) -> int:

    return sum(

        answer.count(
            emoji
        )

        for emoji
        in TRACKED_EMOJIS
    )


# =========================================================
# EMOJI BUDGET
# =========================================================

def get_emoji_budget(
    plan: ExpressionPlan
) -> int:

    level = (
        plan.emoji_level
        or "light"
    ).lower()

    if level == "low":

        return 0

    if level == "light":

        return 1

    return 2


# =========================================================
# EXPRESSION VIOLATION CHECK
#
# Bestehender Funktionsname bleibt erhalten.
#
# bot.py 2.10 kann ihn weiter benutzen.
# =========================================================

def expression_violation_reasons(
    answer: str,
    plan: ExpressionPlan
) -> list[str]:

    reasons = []

    if not answer:

        return [
            "empty_answer"
        ]

    normalized = (
        normalize_text(
            answer
        )
    )

    # =====================================================
    # OPENER
    # =====================================================

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

    # =====================================================
    # WORDS
    # =====================================================

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

    for word in (
        plan.avoid_words
    ):

        if (
            word
            in lowered_words
        ):

            reasons.append(
                f"overused_word:{word}"
            )

    # =====================================================
    # EMOJIS
    # =====================================================

    for emoji in (
        plan.avoid_emojis
    ):

        if emoji in (
            answer
        ):

            reasons.append(
                f"overused_emoji:{emoji}"
            )

    # =====================================================
    # EMOJI BUDGET
    # =====================================================

    emoji_count = (
        count_answer_emojis(
            answer
        )
    )

    emoji_budget = (
        get_emoji_budget(
            plan
        )
    )

    if (
        emoji_count
        >
        emoji_budget
    ):

        reasons.append(
            "emoji_budget_exceeded:"
            f"{emoji_count}>{emoji_budget}"
        )

    # =====================================================
    # CONCEPTS
    # =====================================================

    answer_concepts = (
        detect_concepts(
            answer
        )
    )

    for concept in (
        answer_concepts
    ):

        if (
            concept
            in plan.hard_avoid_concepts
        ):

            reasons.append(
                "hard_concept_cooldown:"
                f"{concept}"
            )

        elif (
            concept
            in plan.avoid_concepts
        ):

            reasons.append(
                "concept_cooldown:"
                f"{concept}"
            )

    # =====================================================
    # ASSISTANT STRUCTURE
    #
    # Nicht jedes harmlose:
    #
    # "ich freu mich"
    #
    # wird sofort blockiert.
    #
    # Block wenn:
    #
    # - sehr klares Assistant-Muster
    #
    # ODER
    #
    # - der Channel bereits mehrfach
    #   in dieses Muster gefallen ist.
    # =====================================================

    assistant_patterns = (
        detect_assistant_patterns(
            answer
        )
    )

    if assistant_patterns:

        if (

            contains_high_confidence_assistant_structure(
                answer
            )

            or

            plan.assistant_pattern_pressure
        ):

            reasons.append(
                "assistant_structure"
            )

    # =====================================================
    # GENERIC FILLER
    # =====================================================

    filler_patterns = (
        detect_filler_patterns(
            answer
        )
    )

    if filler_patterns:

        reasons.append(
            "generic_filler"
        )

    # =====================================================
    # COHERENCE / SEMANTIC REPETITION
    #
    # Hier benutzen wir dieselbe History,
    # die im Plan steckt.
    # =====================================================

    if plan.recent_messages:

        coherence = (
            analyze_coherence(

                plan.recent_messages,

                candidate=answer
            )
        )

        token_count = (
            content_token_count(
                answer
            )
        )

        for reason in (
            coherence
            .candidate_violations
        ):

            # ---------------------------------------------
            # Concepts / Emojis / Openers
            # wurden oben bereits sauber geprüft.
            # ---------------------------------------------

            if reason.startswith(
                "concept_cooldown:"
            ):

                continue

            if reason.startswith(
                "hard_concept_cooldown:"
            ):

                continue

            if reason.startswith(
                "emoji_cooldown:"
            ):

                continue

            if reason.startswith(
                "opener_cooldown:"
            ):

                continue

            # ---------------------------------------------
            # Assistant Structure
            # ---------------------------------------------

            if (
                reason
                ==
                "assistant_structure"
            ):

                continue

            # ---------------------------------------------
            # Generic Filler
            # ---------------------------------------------

            if (
                reason
                ==
                "generic_filler"
            ):

                continue

            # ---------------------------------------------
            # Semantic Repetition
            #
            # Sehr kurze Discord-Reaktionen
            # dürfen natürlicherweise ähnlich sein.
            # ---------------------------------------------

            if (
                reason
                ==
                "semantic_repetition"
            ):

                if (
                    token_count
                    >= 4
                ):

                    reasons.append(
                        reason
                    )

                continue

            if (
                reason
                ==
                "strong_semantic_repetition"
            ):

                if (
                    token_count
                    >= 3

                    and

                    len(
                        normalized
                    )
                    >= 12
                ):

                    reasons.append(
                        reason
                    )

                continue

            reasons.append(
                reason
            )

    return list(
        dict.fromkeys(
            reasons
        )
    )


# =========================================================
# REMOVE AVOIDED EMOJIS
#
# Deterministische Reparatur ist hier sicher:
#
# Emoji entfernen verändert normalerweise
# nicht den Fakt/Inhalt der Aussage.
# =========================================================

def remove_avoided_emojis(
    answer: str,
    plan: ExpressionPlan
) -> tuple[
    str,
    list[str]
]:

    result = (
        answer
    )

    removed = []

    for emoji in (
        plan.avoid_emojis
    ):

        if emoji not in (
            result
        ):

            continue

        removed.append(
            emoji
        )

        result = (
            result.replace(
                emoji,
                ""
            )
        )

    result = re.sub(
        r"[ \t]{2,}",
        " ",
        result
    )

    result = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        result
    )

    return (
        result.strip(),
        removed
    )


# =========================================================
# ENFORCE EMOJI BUDGET
#
# Behält die ersten erlaubten Emojis
# und entfernt zusätzliche.
# =========================================================

def enforce_emoji_budget(
    answer: str,
    plan: ExpressionPlan
) -> tuple[
    str,
    list[str]
]:

    budget = (
        get_emoji_budget(
            plan
        )
    )

    if (
        count_answer_emojis(
            answer
        )
        <=
        budget
    ):

        return (
            answer,
            []
        )

    emoji_pattern = re.compile(

        "|".join(

            re.escape(
                emoji
            )

            for emoji
            in sorted(

                TRACKED_EMOJIS,

                key=len,

                reverse=True
            )
        )
    )

    seen = (
        0
    )

    removed = []

    def replacement(
        match
    ):

        nonlocal seen

        emoji = (
            match.group(0)
        )

        if seen < (
            budget
        ):

            seen += 1

            return emoji

        removed.append(
            emoji
        )

        return ""

    result = (
        emoji_pattern.sub(
            replacement,
            answer
        )
    )

    result = re.sub(
        r"[ \t]{2,}",
        " ",
        result
    )

    result = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        result
    )

    return (
        result.strip(),
        removed
    )


# =========================================================
# REMOVE AVOIDED OPENER
#
# Beispiel:
#
# hahaha, das...
#
# ->
#
# das...
#
# Das ist meistens eine sichere,
# rein stilistische Reparatur.
# =========================================================

def remove_avoided_opener(
    answer: str,
    plan: ExpressionPlan
) -> tuple[
    str,
    Optional[str]
]:

    opener = (
        detect_opener(
            answer
        )
    )

    if (
        not opener
        or
        opener
        not in plan.avoid_openers
    ):

        return (
            answer,
            None
        )

    pattern = re.compile(

        r"^\s*"

        +

        re.escape(
            opener
        )

        +

        r"\s*[,!.:\-–—]*\s*",

        flags=re.IGNORECASE
    )

    cleaned = (
        pattern.sub(
            "",
            answer,
            count=1
        )
        .strip()
    )

    return (
        cleaned,
        opener
    )


# =========================================================
# CLEAN OUTPUT SPACING
# =========================================================

def clean_output_spacing(
    answer: str
) -> str:

    result = (
        answer
        or ""
    )

    result = re.sub(
        r"[ \t]{2,}",
        " ",
        result
    )

    result = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        result
    )

    result = re.sub(
        r"([!?.,])\1{2,}",
        r"\1\1",
        result
    )

    return (
        result.strip()
    )


# =========================================================
# FINAL EXPRESSION GUARD
#
# Dieser Layer wird später
# direkt VOR Discord send() benutzt.
#
# Er macht nur sichere Reparaturen:
#
# - überbenutzte Emojis entfernen
# - Emoji-Budget durchsetzen
# - überbenutzten Opener entfernen
#
# Concepts / Bedeutungsprobleme
# werden NICHT mechanisch aus Sätzen gelöscht.
#
# Stattdessen:
#
# rewrite_required=True
# send_allowed=False
#
# Dann muss Writer/Qwen neu formulieren.
# =========================================================

def apply_expression_final_guard(
    answer: str,
    plan: ExpressionPlan
) -> ExpressionGuardResult:

    original = (
        answer
        or ""
    )

    violations_before = (
        expression_violation_reasons(
            original,
            plan
        )
    )

    cleaned = (
        original
    )

    removed_emojis = []

    removed_opener = None

    # =====================================================
    # SAFE REPAIR 1:
    # AVOIDED OPENER
    # =====================================================

    (
        cleaned,
        removed_opener
    ) = (
        remove_avoided_opener(
            cleaned,
            plan
        )
    )

    # =====================================================
    # SAFE REPAIR 2:
    # AVOIDED EMOJIS
    # =====================================================

    (
        cleaned,
        removed_first
    ) = (
        remove_avoided_emojis(
            cleaned,
            plan
        )
    )

    removed_emojis.extend(
        removed_first
    )

    # =====================================================
    # SAFE REPAIR 3:
    # EMOJI BUDGET
    # =====================================================

    (
        cleaned,
        removed_budget
    ) = (
        enforce_emoji_budget(
            cleaned,
            plan
        )
    )

    removed_emojis.extend(
        removed_budget
    )

    cleaned = (
        clean_output_spacing(
            cleaned
        )
    )

    # =====================================================
    # RE-CHECK
    # =====================================================

    violations_after = (
        expression_violation_reasons(
            cleaned,
            plan
        )
    )

    # =====================================================
    # RESULT
    #
    # Wenn nach sicheren Reparaturen
    # noch ein Verstoß existiert,
    # wird die Antwort später NICHT gesendet,
    # sondern neu formuliert.
    # =====================================================

    rewrite_required = bool(
        violations_after
    )

    send_allowed = (

        bool(
            cleaned
        )

        and

        not rewrite_required
    )

    changed = (
        cleaned
        !=
        original
    )

    return (
        ExpressionGuardResult(

            original=original,

            cleaned=cleaned,

            violations_before=(
                violations_before
            ),

            violations_after=(
                violations_after
            ),

            removed_emojis=list(
                dict.fromkeys(
                    removed_emojis
                )
            ),

            removed_opener=(
                removed_opener
            ),

            changed=(
                changed
            ),

            rewrite_required=(
                rewrite_required
            ),

            send_allowed=(
                send_allowed
            )
        )
    )


# =========================================================
# FINAL GUARD FORMAT
# =========================================================

def format_expression_guard_debug(
    result: ExpressionGuardResult
) -> str:

    return (

        "[EXPRESSION FINAL] "

        f"changed={result.changed} "

        f"send_allowed={result.send_allowed} "

        f"rewrite={result.rewrite_required} "

        f"removed_opener="
        f"{result.removed_opener!r} "

        f"removed_emojis="
        f"{result.removed_emojis} "

        f"before="
        f"{result.violations_before} "

        f"after="
        f"{result.violations_after}"
    )


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

        f"avoid_words="
        f"{plan.avoid_words} "

        f"avoid_openers="
        f"{plan.avoid_openers} "

        f"avoid_emojis="
        f"{plan.avoid_emojis} "

        f"avoid_concepts="
        f"{plan.avoid_concepts} "

        f"hard_concepts="
        f"{plan.hard_avoid_concepts} "

        f"assistant_pressure="
        f"{plan.assistant_pattern_pressure} "

        f"filler_pressure="
        f"{plan.filler_pattern_pressure}"
    )


# =========================================================
# SELF TEST
#
# python expression.py
# =========================================================

def _run_self_test():

    recent = [

        (
            "hahaha, bisschen Chaos "
            "muss sein 😈"
        ),

        (
            "hahaha, ohne Chaos "
            "wird es langweilig 😂"
        ),

        (
            "das wird richtig wild 😏"
        ),

        (
            "Chaos pur, "
            "was soll schon passieren 😈"
        ),

        (
            "das klingt spannend! 😂"
        ),

        (
            "ja, Chaos und Spaß "
            "ist doch mein Ding 😏"
        ),
    ]

    plan = (
        build_expression_plan(

            recent_messages=recent,

            tone="playful",

            mood="chaotic",

            relationship_text="",

            is_hanae=False
        )
    )

    bad_candidate = (
        "hahaha, das klingt spannend! "
        "ein bisschen Chaos muss sein 😂"
    )

    good_candidate = (
        "ne. error kann seinen größenwahn "
        "ruhig selber verwalten."
    )

    bad_reasons = (
        expression_violation_reasons(
            bad_candidate,
            plan
        )
    )

    good_reasons = (
        expression_violation_reasons(
            good_candidate,
            plan
        )
    )

    bad_guard = (
        apply_expression_final_guard(
            bad_candidate,
            plan
        )
    )

    good_guard = (
        apply_expression_final_guard(
            good_candidate,
            plan
        )
    )

    tests = [

        (
            "chaos concept cooldown",
            "chaos"
            in plan.avoid_concepts
        ),

        (
            "laugh emoji cooldown",
            "😂"
            in plan.avoid_emojis
        ),

        (
            "hahaha opener cooldown",
            "hahaha"
            in plan.avoid_openers
        ),

        (
            "bad candidate detects chaos",
            any(

                "concept_cooldown:chaos"
                in reason

                or

                "hard_concept_cooldown:chaos"
                in reason

                for reason
                in bad_reasons
            )
        ),

        (
            "bad candidate detects emoji",
            any(

                reason.startswith(
                    "overused_emoji:😂"
                )

                for reason
                in bad_reasons
            )
        ),

        (
            "bad candidate detects assistant",
            "assistant_structure"
            in bad_reasons
        ),

        (
            "final guard removes opener",
            bad_guard.removed_opener
            == "hahaha"
        ),

        (
            "final guard removes emoji",
            "😂"
            in bad_guard.removed_emojis
        ),

        (
            "bad candidate requires rewrite",
            bad_guard.rewrite_required
            is True
        ),

        (
            "bad candidate blocked",
            bad_guard.send_allowed
            is False
        ),

        (
            "good candidate no violations",
            not good_reasons
        ),

        (
            "good candidate allowed",
            good_guard.send_allowed
            is True
        ),
    ]

    print("")

    print(
        "============================================"
    )

    print(
        f"EXPRESSION v{EXPRESSION_VERSION} SELF TEST"
    )

    print(
        "============================================"
    )

    print("")

    print(
        format_expression_debug(
            plan
        )
    )

    print("")

    print(
        "BAD CANDIDATE:"
    )

    print(
        bad_candidate
    )

    print(
        bad_reasons
    )

    print(
        format_expression_guard_debug(
            bad_guard
        )
    )

    print("")

    print(
        "GOOD CANDIDATE:"
    )

    print(
        good_candidate
    )

    print(
        good_reasons
    )

    print(
        format_expression_guard_debug(
            good_guard
        )
    )

    print("")

    passed = (
        0
    )

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
            f"[{status}] "
            f"{name}"
        )

    print("")

    print(
        "============================================"
    )

    print(
        f"RESULT: "
        f"{passed}/"
        f"{len(tests)} passed"
    )

    print(
        "============================================"
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    _run_self_test()
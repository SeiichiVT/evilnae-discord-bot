import re
import threading

from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Iterable, Optional


# =========================================================
# VERSION
# =========================================================

COHERENCE_VERSION = "1.0"


# =========================================================
# CONFIG
# =========================================================

CHANNEL_HISTORY_LIMIT = 30

CONCEPT_WINDOW = 12

EMOJI_WINDOW = 10

OPENER_WINDOW = 10

PHRASE_WINDOW = 12

SEMANTIC_WINDOW = 12


SEMANTIC_REPETITION_THRESHOLD = (
    0.72
)

STRONG_SEMANTIC_REPETITION_THRESHOLD = (
    0.84
)


MAX_WRITER_HISTORY = 20


DEFAULT_CONTEXT_FRESHNESS_LIMIT = (
    2
)


# =========================================================
# CONCEPT GROUPS
#
# Diese Gruppen definieren NICHT Evilnaes Persönlichkeit.
#
# Sie dienen ausschließlich dazu,
# überbenutzte sprachliche Motive zu erkennen.
#
# Beispiel:
#
# chaos_drive im Inner State
#
# darf existieren.
#
# Aber:
#
# "Chaos"
# "chaotisch"
# "Chaos-Energie"
#
# 6x hintereinander zu schreiben
# ist ein Output-Muster.
#
# Genau das erkennen wir hier.
# =========================================================

CONCEPT_PATTERNS = {

    # -----------------------------------------------------
    # CHAOS
    # -----------------------------------------------------

    "chaos": [

        r"\bchaos\b",

        r"\bchaotisch\w*\b",

        r"\bchaos[- ]?energie\b",

        r"\bchaos[- ]?pur\b",

        r"\bchaos[- ]?deluxe\b",

        r"\bchaos[- ]?modus\b",

        r"\bchaos[- ]?katze\b",

        r"\bchaos[- ]?keks\w*\b",
    ],


    # -----------------------------------------------------
    # GENERIC EXCITEMENT
    # -----------------------------------------------------

    "excitement": [

        r"\bwild\b",

        r"\bspannend\b",

        r"\bverrückt\b",

        r"\bepisch\b",

        r"\blegendär\b",

        r"\blegendary\b",

        r"\briesenspaß\b",

        r"\bmega\b",

        r"\btotal krass\b",
    ],


    # -----------------------------------------------------
    # BOREDOM
    # -----------------------------------------------------

    "boredom": [

        r"\blangweilig\b",

        r"\bnicht spannend\b",

        r"\bnichts los\b",

        r"\bnichts besonderes\b",

        r"\bnicht viel los\b",

        r"\bflacht .* ab\b",
    ],


    # -----------------------------------------------------
    # GENERIC POSITIVE REACTION
    #
    # Typische Bot-/Assistant-Struktur:
    #
    # "klingt spannend"
    # "ich bin gespannt"
    # usw.
    # -----------------------------------------------------

    "generic_positive": [

        r"\bklingt gut\b",

        r"\bklingt super\b",

        r"\bklingt spannend\b",

        r"\bdas ist cool\b",

        r"\bdas ist echt cool\b",

        r"\bfreut mich\b",

        r"\bich freu mich\b",

        r"\bich bin gespannt\b",
    ],


    # -----------------------------------------------------
    # GENERIC CLOSING
    # -----------------------------------------------------

    "generic_closing": [

        r"\bviel erfolg\b",

        r"\bviel spaß\b",

        r"\bsag ich bescheid\b",

        r"\bhalte? .* augen offen\b",

        r"\bmal sehen was .* bringt\b",
    ],


    # -----------------------------------------------------
    # PERSONA SELF-LABELING
    #
    # Persönlichkeit soll aus Verhalten entstehen.
    #
    # Nicht:
    #
    # "Chaos ist mein zweiter Vorname."
    # -----------------------------------------------------

    "persona_labeling": [

        r"\bmein ding\b",

        r"\bmein zweiter vorname\b",

        r"\bin reinkultur\b",

        r"\bpasst zu mir\b",

        r"\bdas beschreibt mich\b",
    ],


    # -----------------------------------------------------
    # REPETITIVE MENACE
    #
    # Einzelne freche/drohende Formulierungen
    # können passen.
    #
    # Wiederholt wirken sie schnell wie Persona-Template.
    # -----------------------------------------------------

    "forced_menace": [

        r"\bdas wird dir noch leid tun\b",

        r"\bdu wirst es bereuen\b",

        r"\bwarte nur ab\b",

        r"\bdu bist gewarnt\b",
    ],
}


# =========================================================
# CONCEPT LIMITS
#
# threshold:
# Ab wie vielen Vorkommen im Fenster
# ein Concept Cooldown aktiviert wird.
#
# hard_threshold:
# Ab wann das Muster massiv überbenutzt ist.
# =========================================================

CONCEPT_LIMITS = {

    "chaos": {

        "threshold":
            2,

        "hard_threshold":
            4,
    },


    "excitement": {

        "threshold":
            3,

        "hard_threshold":
            5,
    },


    "boredom": {

        "threshold":
            2,

        "hard_threshold":
            4,
    },


    "generic_positive": {

        "threshold":
            2,

        "hard_threshold":
            4,
    },


    "generic_closing": {

        "threshold":
            2,

        "hard_threshold":
            3,
    },


    "persona_labeling": {

        "threshold":
            2,

        "hard_threshold":
            3,
    },


    "forced_menace": {

        "threshold":
            2,

        "hard_threshold":
            3,
    },
}


# =========================================================
# TRACKED EMOJIS
#
# Nicht verboten.
#
# Nur Overuse erkennen.
# =========================================================

TRACKED_EMOJIS = {

    "😂",
    "🤣",

    "😈",
    "😏",

    "😭",
    "💀",

    "👀",

    "✨",
    "🌟",

    "🔥",

    "🍪",
    "🍕",

    "🌳",

    "💥",

    "🤭",
    "😉",
    "😊",

    "🥺",

    "❤️",
    "🖤",

    "🙌",

    "👻",
}


# =========================================================
# TRACKED OPENERS
#
# Satzanfänge können ebenfalls
# in Schleifen geraten.
# =========================================================

TRACKED_OPENERS = (

    "hahaha",

    "haha",

    "hehe",

    "lol",

    "lmao",

    "bruh",

    "bro",

    "oh",

    "oha",

    "naja",

    "also",

    "ja okay",

    "na klar",

    "ach komm",

    "okay",

    "klar",

    "ja",

    "uff",

    "pff",

    "ey",
)


# =========================================================
# ASSISTANT STYLE PATTERNS
#
# Diese sind nicht automatisch permanent verboten.
#
# Aber wenn Evilnae ständig so formuliert,
# ist das ein klares Bot-Signal.
# =========================================================

ASSISTANT_STYLE_PATTERNS = (

    r"\bdas klingt "
    r"(?:echt |wirklich |total )?"
    r"(?:spannend|super|gut|cool)\b",

    r"\bich hoffe(?:,| dass)\b",

    r"\bich bin gespannt\b",

    r"\bich freue mich\b",

    r"\bich freu mich\b",

    r"\bviel erfolg\b",

    r"\balles klar\b",

    r"\bdas freut mich\b",

    r"\bkein problem\b",

    r"\bsag(?:e)? ich bescheid\b",

    r"\bich halte? .* augen offen\b",
)


# =========================================================
# LOW INFORMATION / FILLER PATTERNS
#
# Dinge, die häufig nur entstehen,
# weil das System unbedingt antworten will.
# =========================================================

FILLER_PATTERNS = (

    r"^oha[,!. ]",

    r"^oh[,!. ]",

    r"^ja[,!. ]",

    r"^klar[,!. ]",

    r"^okay[,!. ]",

    r"\bwas für eine überraschung\b",

    r"\bdas ist echt "
    r"(?:crazy|wild|spannend)\b",

    r"\bmal schauen,? was noch kommt\b",
)


# =========================================================
# STOPWORDS
#
# Für einfache semantische Ähnlichkeit.
# =========================================================

STOPWORDS = {

    "aber",
    "also",
    "auch",
    "auf",
    "aus",

    "bei",

    "bin",
    "bist",

    "da",

    "das",
    "dass",

    "dein",
    "deine",

    "dem",
    "den",
    "der",
    "die",

    "dir",

    "doch",

    "du",

    "ein",
    "eine",
    "einen",
    "einer",

    "es",

    "für",

    "hab",
    "habe",
    "hat",

    "hier",

    "ich",

    "im",
    "in",

    "ist",

    "ja",

    "mal",

    "man",

    "mit",

    "noch",

    "nur",

    "oder",

    "schon",

    "sie",

    "so",

    "und",

    "uns",

    "von",

    "war",

    "was",

    "wenn",

    "wie",

    "wir",

    "wird",

    "zu",

    "zum",

    "zur",
}


# =========================================================
# DATA CLASSES
# =========================================================

@dataclass
class ConceptStat:

    name: str

    count: int = 0

    weighted_count: float = 0.0

    cooldown: bool = False

    hard_cooldown: bool = False

    examples: list[str] = field(
        default_factory=list
    )


@dataclass
class SimilarityMatch:

    score: float = 0.0

    message: str = ""

    message_index: int = -1


@dataclass
class CoherenceAnalysis:

    # -----------------------------------------------------
    # CHANNEL-WIDE EVILNAE HISTORY
    # -----------------------------------------------------

    recent_messages: list[str] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # CONCEPTS
    # -----------------------------------------------------

    concept_stats: dict[
        str,
        ConceptStat
    ] = field(
        default_factory=dict
    )

    avoid_concepts: list[str] = field(
        default_factory=list
    )

    hard_avoid_concepts: list[str] = field(
        default_factory=list
    )

    # -----------------------------------------------------
    # EXPRESSION
    # -----------------------------------------------------

    avoid_emojis: list[str] = field(
        default_factory=list
    )

    avoid_openers: list[str] = field(
        default_factory=list
    )

    repeated_assistant_patterns: list[str] = field(
        default_factory=list
    )

    emoji_counts: dict[
        str,
        int
    ] = field(
        default_factory=dict
    )

    opener_counts: dict[
        str,
        int
    ] = field(
        default_factory=dict
    )

    assistant_pattern_count: int = 0

    filler_pattern_count: int = 0

    # -----------------------------------------------------
    # CANDIDATE
    # -----------------------------------------------------

    candidate_similarity: float = 0.0

    candidate_similarity_match: str = ""

    candidate_repetition: bool = False

    candidate_strong_repetition: bool = False

    candidate_concepts: list[str] = field(
        default_factory=list
    )

    candidate_violations: list[str] = field(
        default_factory=list
    )


# =========================================================
# CHANNEL REVISION TRACKER
#
# Runtime-only.
#
# Wird später in bot.py verwendet.
#
# Beispiel:
#
# User schreibt.
#
# revision = 50
#
# Brain/Writer/Qwen brauchen 7 Sekunden.
#
# Inzwischen:
#
# revision = 55
#
# Dann wissen wir:
#
# Der Channel hat sich währenddessen
# deutlich weiterbewegt.
# =========================================================

_revision_lock = (
    threading.RLock()
)


_channel_revisions: dict[
    str,
    int
] = {}


# =========================================================
# BUMP REVISION
# =========================================================

def bump_channel_revision(
    channel_id: Any
) -> int:

    key = str(
        channel_id
    )

    with _revision_lock:

        current = (
            _channel_revisions.get(
                key,
                0
            )
        )

        current += 1

        _channel_revisions[
            key
        ] = current

        return current


# =========================================================
# GET REVISION
# =========================================================

def get_channel_revision(
    channel_id: Any
) -> int:

    key = str(
        channel_id
    )

    with _revision_lock:

        return (
            _channel_revisions.get(
                key,
                0
            )
        )


# =========================================================
# CAPTURE REVISION
# =========================================================

def capture_channel_revision(
    channel_id: Any
) -> int:

    return get_channel_revision(
        channel_id
    )


# =========================================================
# REVISION DELTA
# =========================================================

def get_revision_delta(
    channel_id: Any,
    start_revision: int
) -> int:

    current = (
        get_channel_revision(
            channel_id
        )
    )

    return max(

        0,

        current
        -
        int(
            start_revision
            or 0
        )
    )


# =========================================================
# CONTEXT FRESHNESS
# =========================================================

def is_context_fresh(
    channel_id: Any,
    start_revision: int,
    max_new_messages: int = DEFAULT_CONTEXT_FRESHNESS_LIMIT
) -> bool:

    return (

        get_revision_delta(
            channel_id,
            start_revision
        )

        <=

        max(
            0,
            int(
                max_new_messages
            )
        )
    )


# =========================================================
# NORMALIZE TEXT
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

        .lower()

        .strip()
    )

    # -----------------------------------------------------
    # CUSTOM DISCORD EMOJIS
    # -----------------------------------------------------

    value = re.sub(

        r"<a?:"
        r"[A-Za-z0-9_]+:"
        r"\d+>",

        " ",

        value
    )

    # -----------------------------------------------------
    # URLS
    # -----------------------------------------------------

    value = re.sub(

        r"https?://\S+",

        " ",

        value
    )

    # -----------------------------------------------------
    # QUOTES
    # -----------------------------------------------------

    value = re.sub(

        r"[“”„\"'`´]",

        "",

        value
    )

    # -----------------------------------------------------
    # MARKDOWN
    # -----------------------------------------------------

    value = re.sub(

        r"[_*~>#]",

        " ",

        value
    )

    # -----------------------------------------------------
    # SPACES
    # -----------------------------------------------------

    value = re.sub(

        r"\s+",

        " ",

        value
    )

    return (
        value.strip()
    )


# =========================================================
# NORMALIZE FOR SIMILARITY
# =========================================================

def normalize_for_similarity(
    text: str
) -> str:

    value = (
        normalize_text(
            text
        )
    )

    # -----------------------------------------------------
    # Unicode Emojis entfernen
    # -----------------------------------------------------

    for emoji in (
        TRACKED_EMOJIS
    ):

        value = (
            value.replace(
                emoji,
                " "
            )
        )

    # -----------------------------------------------------
    # Nur relevante Zeichen
    # -----------------------------------------------------

    value = re.sub(

        r"[^a-z0-9äöüß ]+",

        " ",

        value
    )

    value = re.sub(

        r"\s+",

        " ",

        value
    )

    return (
        value.strip()
    )


# =========================================================
# TOKEN EXTRACTION
# =========================================================

def extract_tokens(
    text: str,
    *,
    remove_stopwords: bool = True
) -> list[str]:

    normalized = (
        normalize_for_similarity(
            text
        )
    )

    tokens = re.findall(

        r"[a-z0-9äöüß]+",

        normalized
    )

    if remove_stopwords:

        tokens = [

            token

            for token
            in tokens

            if token
            not in STOPWORDS
        ]

    return tokens


# =========================================================
# CHANNEL SNAPSHOT -> EVILNAE MESSAGES
#
# Unterstützt:
#
# list[str]
#
# UND
#
# list[dict]
#
# Dadurch koppeln wir coherence.py
# nicht hart an eine einzelne bot.py-Struktur.
# =========================================================

def extract_evilnae_messages(
    channel_snapshot: Optional[
        Iterable[Any]
    ],
    *,
    limit: int = CHANNEL_HISTORY_LIMIT
) -> list[str]:

    if not channel_snapshot:

        return []

    result = []

    for item in (
        channel_snapshot
    ):

        # -------------------------------------------------
        # DIREKTER STRING
        # -------------------------------------------------

        if isinstance(
            item,
            str
        ):

            text = (
                item.strip()
            )

            if text:

                result.append(
                    text
                )

            continue

        # -------------------------------------------------
        # DICT
        # -------------------------------------------------

        if not isinstance(
            item,
            dict
        ):

            continue

        # -------------------------------------------------
        # MESSAGE TYPE
        # -------------------------------------------------

        item_type = str(

            item.get(

                "type",

                item.get(
                    "role",
                    ""
                )
            )
        ).lower()

        # -------------------------------------------------
        # AUTHOR NAME
        # -------------------------------------------------

        author_name = str(

            item.get(

                "username",

                item.get(

                    "author_name",

                    item.get(
                        "author",
                        ""
                    )
                )
            )
        ).lower()

        # -------------------------------------------------
        # BOT FLAG
        # -------------------------------------------------

        is_bot = bool(

            item.get(
                "is_bot",
                False
            )
        )

        # -------------------------------------------------
        # EVILNAE MESSAGE?
        # -------------------------------------------------

        bot_like = (

            item_type
            in {

                "bot",

                "assistant",

                "evilnae",
            }

            or

            author_name
            == "evilnae"

            or

            is_bot
        )

        if not bot_like:

            continue

        # -------------------------------------------------
        # CONTENT
        # -------------------------------------------------

        content = str(

            item.get(

                "content",

                item.get(

                    "text",

                    item.get(
                        "message",
                        ""
                    )
                )
            )
        ).strip()

        if content:

            result.append(
                content
            )

    if limit <= 0:

        return []

    return (
        result[
            -limit:
        ]
    )


# =========================================================
# DETECT CONCEPTS
# =========================================================

def detect_concepts(
    text: str
) -> list[str]:

    normalized = (
        normalize_text(
            text
        )
    )

    if not normalized:

        return []

    found = []

    for (
        concept,
        patterns
    ) in (
        CONCEPT_PATTERNS.items()
    ):

        for pattern in (
            patterns
        ):

            if re.search(

                pattern,

                normalized,

                flags=re.IGNORECASE
            ):

                found.append(
                    concept
                )

                break

    return found


# =========================================================
# RECENCY WEIGHT
#
# Neuere Antworten zählen stärker.
# =========================================================

def _recency_weight(
    index: int,
    total: int
) -> float:

    if total <= 1:

        return 1.0

    distance_from_latest = (

        total
        - 1
        - index
    )

    return max(

        0.35,

        1.0
        -
        (
            distance_from_latest
            * 0.06
        )
    )


# =========================================================
# ANALYZE CONCEPTS
# =========================================================

def analyze_concepts(
    recent_messages: list[str]
) -> dict[
    str,
    ConceptStat
]:

    window = (

        recent_messages[
            -CONCEPT_WINDOW:
        ]
    )

    stats = {

        name:
            ConceptStat(
                name=name
            )

        for name
        in CONCEPT_PATTERNS
    }

    total = (
        len(
            window
        )
    )

    for (
        index,
        message
    ) in enumerate(
        window
    ):

        concepts = (
            detect_concepts(
                message
            )
        )

        weight = (
            _recency_weight(
                index,
                total
            )
        )

        for concept in (
            concepts
        ):

            stat = (
                stats[
                    concept
                ]
            )

            stat.count += (
                1
            )

            stat.weighted_count += (
                weight
            )

            if (
                len(
                    stat.examples
                )
                < 3
            ):

                stat.examples.append(
                    message
                )

    # -----------------------------------------------------
    # COOLDOWN STATUS
    # -----------------------------------------------------

    for (
        concept,
        stat
    ) in (
        stats.items()
    ):

        limits = (
            CONCEPT_LIMITS.get(

                concept,

                {

                    "threshold":
                        3,

                    "hard_threshold":
                        5,
                }
            )
        )

        threshold = int(
            limits[
                "threshold"
            ]
        )

        hard_threshold = int(
            limits[
                "hard_threshold"
            ]
        )

        stat.cooldown = (

            stat.count
            >=
            threshold
        )

        stat.hard_cooldown = (

            stat.count
            >=
            hard_threshold
        )

    return stats


# =========================================================
# COUNT EMOJIS
# =========================================================

def count_emojis(
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
# EMOJI COOLDOWNS
# =========================================================

def get_emoji_cooldowns(
    recent_messages: list[str]
) -> tuple[
    list[str],
    dict[str, int]
]:

    window = (

        recent_messages[
            -EMOJI_WINDOW:
        ]
    )

    counts = (
        count_emojis(
            window
        )
    )

    avoid = []

    for (
        emoji,
        count
    ) in (
        counts.items()
    ):

        # -------------------------------------------------
        # Schon 2x innerhalb der letzten 10 Antworten
        # reicht für einen temporären Cooldown.
        # -------------------------------------------------

        if count >= 2:

            avoid.append(
                emoji
            )

    avoid.sort(

        key=lambda emoji:
            (
                -counts[
                    emoji
                ],
                emoji
            )
    )

    return (

        avoid,

        dict(
            counts
        )
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
# OPENER COOLDOWNS
# =========================================================

def get_opener_cooldowns(
    recent_messages: list[str]
) -> tuple[
    list[str],
    dict[str, int]
]:

    window = (

        recent_messages[
            -OPENER_WINDOW:
        ]
    )

    counter = (
        Counter()
    )

    for message in (
        window
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

    avoid = [

        opener

        for (
            opener,
            count
        ) in (
            counter.items()
        )

        if count >= 2
    ]

    avoid.sort(

        key=lambda opener:
            (
                -counter[
                    opener
                ],
                opener
            )
    )

    return (

        avoid,

        dict(
            counter
        )
    )


# =========================================================
# DETECT ASSISTANT PATTERNS
# =========================================================

def detect_assistant_patterns(
    text: str
) -> list[str]:

    normalized = (
        normalize_text(
            text
        )
    )

    found = []

    for pattern in (
        ASSISTANT_STYLE_PATTERNS
    ):

        if re.search(

            pattern,

            normalized,

            flags=re.IGNORECASE
        ):

            found.append(
                pattern
            )

    return found


# =========================================================
# COUNT ASSISTANT PATTERN MESSAGES
# =========================================================

def count_assistant_pattern_messages(
    messages: list[str]
) -> int:

    window = (

        messages[
            -PHRASE_WINDOW:
        ]
    )

    return sum(

        1

        for message
        in window

        if detect_assistant_patterns(
            message
        )
    )


# =========================================================
# DETECT FILLER PATTERNS
# =========================================================

def detect_filler_patterns(
    text: str
) -> list[str]:

    normalized = (
        normalize_text(
            text
        )
    )

    return [

        pattern

        for pattern
        in FILLER_PATTERNS

        if re.search(

            pattern,

            normalized,

            flags=re.IGNORECASE
        )
    ]


# =========================================================
# COUNT FILLER MESSAGES
# =========================================================

def count_filler_pattern_messages(
    messages: list[str]
) -> int:

    window = (

        messages[
            -PHRASE_WINDOW:
        ]
    )

    return sum(

        1

        for message
        in window

        if detect_filler_patterns(
            message
        )
    )


# =========================================================
# TOKEN JACCARD
#
# Teil der lokalen semantischen Ähnlichkeit.
# =========================================================

def token_jaccard(
    first: str,
    second: str
) -> float:

    left = set(
        extract_tokens(
            first
        )
    )

    right = set(
        extract_tokens(
            second
        )
    )

    if (
        not left
        or
        not right
    ):

        return 0.0

    union = (
        left
        |
        right
    )

    if not union:

        return 0.0

    return (

        len(
            left
            & right
        )

        /

        len(
            union
        )
    )


# =========================================================
# SEQUENCE SIMILARITY
# =========================================================

def sequence_similarity(
    first: str,
    second: str
) -> float:

    left = (
        normalize_for_similarity(
            first
        )
    )

    right = (
        normalize_for_similarity(
            second
        )
    )

    if (
        not left
        or
        not right
    ):

        return 0.0

    return (
        SequenceMatcher(

            None,

            left,

            right

        ).ratio()
    )


# =========================================================
# CONCEPT SIMILARITY
# =========================================================

def concept_similarity(
    first: str,
    second: str
) -> float:

    left = set(
        detect_concepts(
            first
        )
    )

    right = set(
        detect_concepts(
            second
        )
    )

    if (
        not left
        or
        not right
    ):

        return 0.0

    return (

        len(
            left
            & right
        )

        /

        len(
            left
            | right
        )
    )


# =========================================================
# MESSAGE SIMILARITY
#
# v1 nutzt bewusst KEINE API
# und KEINE Embeddings.
#
# Mischung aus:
#
# - Token overlap
# - Satzähnlichkeit
# - Concept overlap
#
# Später kann hier ein Embedding-Layer
# ergänzt werden.
# =========================================================

def message_similarity(
    first: str,
    second: str
) -> float:

    if (
        not first
        or
        not second
    ):

        return 0.0

    token_score = (
        token_jaccard(
            first,
            second
        )
    )

    sequence_score = (
        sequence_similarity(
            first,
            second
        )
    )

    concept_score = (
        concept_similarity(
            first,
            second
        )
    )

    score = (

        token_score
        * 0.50

        +

        sequence_score
        * 0.30

        +

        concept_score
        * 0.20
    )

    return max(

        0.0,

        min(
            1.0,
            score
        )
    )


# =========================================================
# FIND MOST SIMILAR MESSAGE
# =========================================================

def find_most_similar_message(
    candidate: str,
    recent_messages: list[str]
) -> SimilarityMatch:

    best = (
        SimilarityMatch()
    )

    window = (

        recent_messages[
            -SEMANTIC_WINDOW:
        ]
    )

    for (
        index,
        message
    ) in enumerate(
        window
    ):

        score = (
            message_similarity(
                candidate,
                message
            )
        )

        if score > (
            best.score
        ):

            best = (
                SimilarityMatch(

                    score=score,

                    message=message,

                    message_index=index
                )
            )

    return best


# =========================================================
# ANALYZE COHERENCE
#
# Hauptfunktion.
#
# recent_messages:
#
# Evilnaes eigene letzten Nachrichten
# CHANNELWEIT.
#
# candidate:
#
# optionale neue Antwort,
# die geprüft werden soll.
# =========================================================

def analyze_coherence(
    recent_messages: list[str],
    *,
    candidate: str = ""
) -> CoherenceAnalysis:

    recent = [

        str(
            message
        ).strip()

        for message
        in recent_messages[
            -CHANNEL_HISTORY_LIMIT:
        ]

        if (
            message is not None
            and
            str(
                message
            ).strip()
        )
    ]

    # =====================================================
    # CONCEPTS
    # =====================================================

    concept_stats = (
        analyze_concepts(
            recent
        )
    )

    avoid_concepts = [

        name

        for (
            name,
            stat
        ) in (
            concept_stats.items()
        )

        if stat.cooldown
    ]

    hard_avoid_concepts = [

        name

        for (
            name,
            stat
        ) in (
            concept_stats.items()
        )

        if stat.hard_cooldown
    ]

    # =====================================================
    # EMOJIS
    # =====================================================

    (
        avoid_emojis,
        emoji_counts
    ) = (
        get_emoji_cooldowns(
            recent
        )
    )

    # =====================================================
    # OPENERS
    # =====================================================

    (
        avoid_openers,
        opener_counts
    ) = (
        get_opener_cooldowns(
            recent
        )
    )

    # =====================================================
    # BOT STRUCTURE
    # =====================================================

    assistant_count = (
        count_assistant_pattern_messages(
            recent
        )
    )

    # =====================================================
    # FILLER
    # =====================================================

    filler_count = (
        count_filler_pattern_messages(
            recent
        )
    )

    # =====================================================
    # RESULT BASE
    # =====================================================

    analysis = (
        CoherenceAnalysis(

            recent_messages=recent,

            concept_stats=(
                concept_stats
            ),

            avoid_concepts=(
                avoid_concepts
            ),

            hard_avoid_concepts=(
                hard_avoid_concepts
            ),

            avoid_emojis=(
                avoid_emojis
            ),

            avoid_openers=(
                avoid_openers
            ),

            emoji_counts=(
                emoji_counts
            ),

            opener_counts=(
                opener_counts
            ),

            assistant_pattern_count=(
                assistant_count
            ),

            filler_pattern_count=(
                filler_count
            ),
        )
    )

    # =====================================================
    # KEIN CANDIDATE
    # =====================================================

    if not candidate:

        return analysis

    # =====================================================
    # CANDIDATE CONCEPTS
    # =====================================================

    candidate_concepts = (
        detect_concepts(
            candidate
        )
    )

    # =====================================================
    # SEMANTIC REPETITION
    # =====================================================

    similarity = (
        find_most_similar_message(

            candidate,

            recent
        )
    )

    violations = []

    # =====================================================
    # CONCEPT VIOLATIONS
    # =====================================================

    for concept in (
        candidate_concepts
    ):

        if concept in (
            hard_avoid_concepts
        ):

            violations.append(

                "hard_concept_cooldown:"
                f"{concept}"
            )

        elif concept in (
            avoid_concepts
        ):

            violations.append(

                "concept_cooldown:"
                f"{concept}"
            )

    # =====================================================
    # EMOJI VIOLATIONS
    # =====================================================

    for emoji in (
        avoid_emojis
    ):

        if emoji in (
            candidate
        ):

            violations.append(

                "emoji_cooldown:"
                f"{emoji}"
            )

    # =====================================================
    # OPENER VIOLATIONS
    # =====================================================

    opener = (
        detect_opener(
            candidate
        )
    )

    if (
        opener
        and
        opener
        in avoid_openers
    ):

        violations.append(

            "opener_cooldown:"
            f"{opener}"
        )

    # =====================================================
    # ASSISTANT STYLE
    # =====================================================

    assistant_patterns = (
        detect_assistant_patterns(
            candidate
        )
    )

    if assistant_patterns:

        violations.append(
            "assistant_structure"
        )

    # =====================================================
    # GENERIC FILLER
    # =====================================================

    filler_patterns = (
        detect_filler_patterns(
            candidate
        )
    )

    if filler_patterns:

        violations.append(
            "generic_filler"
        )

    # =====================================================
    # SEMANTIC REPETITION
    # =====================================================

    repeated = (

        similarity.score

        >=

        SEMANTIC_REPETITION_THRESHOLD
    )

    strong_repeated = (

        similarity.score

        >=

        STRONG_SEMANTIC_REPETITION_THRESHOLD
    )

    if strong_repeated:

        violations.append(
            "strong_semantic_repetition"
        )

    elif repeated:

        violations.append(
            "semantic_repetition"
        )

    # =====================================================
    # STORE CANDIDATE RESULTS
    # =====================================================

    analysis.candidate_similarity = (
        similarity.score
    )

    analysis.candidate_similarity_match = (
        similarity.message
    )

    analysis.candidate_repetition = (
        repeated
    )

    analysis.candidate_strong_repetition = (
        strong_repeated
    )

    analysis.candidate_concepts = (
        candidate_concepts
    )

    analysis.candidate_violations = list(

        dict.fromkeys(
            violations
        )
    )

    return analysis


# =========================================================
# ANALYZE CHANNEL SNAPSHOT
#
# Convenience Wrapper für bot.py.
# =========================================================

def analyze_channel_snapshot(
    channel_snapshot: Optional[
        Iterable[Any]
    ],
    *,
    candidate: str = "",
    limit: int = CHANNEL_HISTORY_LIMIT
) -> CoherenceAnalysis:

    messages = (
        extract_evilnae_messages(

            channel_snapshot,

            limit=limit
        )
    )

    return (
        analyze_coherence(

            messages,

            candidate=candidate
        )
    )


# =========================================================
# FINAL CANDIDATE CHECK
# =========================================================

def coherence_violation_reasons(
    candidate: str,
    recent_messages: list[str]
) -> list[str]:

    analysis = (
        analyze_coherence(

            recent_messages,

            candidate=candidate
        )
    )

    return (
        analysis.candidate_violations
    )


# =========================================================
# FORMAT EXAMPLES
# =========================================================

def _format_examples(
    values: list[str],
    *,
    limit: int = 3
) -> str:

    if not values:

        return "Keine."

    cleaned = []

    for value in (
        values[
            :limit
        ]
    ):

        compact = re.sub(

            r"\s+",

            " ",

            value
        ).strip()

        if len(
            compact
        ) > 180:

            compact = (

                compact[
                    :177
                ]

                + "..."
            )

        cleaned.append(

            f"- {compact}"
        )

    return (
        "\n".join(
            cleaned
        )
    )


# =========================================================
# FORMAT FOR WRITER
#
# Das kommt später in den Writer-Prompt.
# =========================================================

def format_coherence_for_writer(
    analysis: CoherenceAnalysis
) -> str:

    if analysis.avoid_concepts:

        concepts = (
            ", ".join(
                analysis.avoid_concepts
            )
        )

    else:

        concepts = (
            "Keine."
        )

    if analysis.hard_avoid_concepts:

        hard_concepts = (
            ", ".join(
                analysis.hard_avoid_concepts
            )
        )

    else:

        hard_concepts = (
            "Keine."
        )

    if analysis.avoid_emojis:

        emojis = (
            " ".join(
                analysis.avoid_emojis
            )
        )

    else:

        emojis = (
            "Keine."
        )

    if analysis.avoid_openers:

        openers = (
            ", ".join(
                analysis.avoid_openers
            )
        )

    else:

        openers = (
            "Keine."
        )

    recent_examples = (

        analysis.recent_messages[
            -6:
        ]
    )

    return f"""
CHANNEL-WIDE COHERENCE:

Die folgenden Hinweise beziehen sich auf
Evilnaes EIGENE letzten Nachrichten
im gesamten Channel,
nicht nur auf diesen User.

Temporär überbenutzte Konzepte:
{concepts}

Stark überbenutzte Konzepte:
{hard_concepts}

Temporär überbenutzte Emojis:
{emojis}

Temporär überbenutzte Satzanfänge:
{openers}

Assistant-/Support-Muster in letzter Zeit:
{analysis.assistant_pattern_count}

Generische Füllmuster in letzter Zeit:
{analysis.filler_pattern_count}

Letzte Evilnae-Nachrichten im Channel:
{_format_examples(recent_examples, limit=6)}

WICHTIG:

- Cooldowns sind temporär.

- Wiederhole ein überbenutztes Motiv
  nicht nur mit anderen Wörtern.

- Interne Zustände sind KEINE Wörter,
  die du aussprechen musst.

- "chaos_drive" bedeutet NICHT,
  dass das Wort "Chaos"
  benutzt werden soll.

- Wenn "Chaos" auf Cooldown ist,
  reagiere auf einen anderen Aspekt.

- Wenn ein Emoji auf Cooldown ist,
  benutze es nicht.

- Persönlichkeit soll aus dem Gedanken
  entstehen,
  nicht aus Persona-Schlagwörtern.
""".strip()


# =========================================================
# FORMAT FOR CRITIC / QWEN
#
# Kompakter als die Writer-Version.
# =========================================================

def format_coherence_for_critic(
    analysis: CoherenceAnalysis
) -> str:

    concept_counts = []

    for (
        name,
        stat
    ) in (
        analysis.concept_stats.items()
    ):

        if stat.count <= 0:

            continue

        concept_counts.append(

            f"{name}="
            f"{stat.count}"
        )

    concept_text = (

        ", ".join(
            concept_counts
        )

        if concept_counts

        else

        "keine"
    )

    emoji_text = (

        ", ".join(

            f"{emoji}:{count}"

            for (
                emoji,
                count
            ) in sorted(

                analysis
                .emoji_counts
                .items(),

                key=lambda item:
                    (
                        -item[1],
                        item[0]
                    )
            )
        )

        if analysis.emoji_counts

        else

        "keine"
    )

    avoid_concepts = (

        ", ".join(
            analysis.avoid_concepts
        )

        if analysis.avoid_concepts

        else

        "keine"
    )

    hard_avoid_concepts = (

        ", ".join(
            analysis.hard_avoid_concepts
        )

        if analysis.hard_avoid_concepts

        else

        "keine"
    )

    avoid_emojis = (

        " ".join(
            analysis.avoid_emojis
        )

        if analysis.avoid_emojis

        else

        "keine"
    )

    avoid_openers = (

        ", ".join(
            analysis.avoid_openers
        )

        if analysis.avoid_openers

        else

        "keine"
    )

    return f"""
CHANNEL REPETITION STATS:

Concept counts:
{concept_text}

Emoji counts:
{emoji_text}

Avoid concepts:
{avoid_concepts}

Hard avoid concepts:
{hard_avoid_concepts}

Avoid emojis:
{avoid_emojis}

Avoid openers:
{avoid_openers}

Recent assistant-like messages:
{analysis.assistant_pattern_count}

Recent filler-like messages:
{analysis.filler_pattern_count}
""".strip()


# =========================================================
# DEBUG FORMAT
# =========================================================

def format_coherence_debug(
    analysis: CoherenceAnalysis
) -> str:

    concept_parts = []

    for (
        name,
        stat
    ) in (
        analysis.concept_stats.items()
    ):

        if stat.count <= 0:

            continue

        suffix = ""

        if stat.hard_cooldown:

            suffix = "!!"

        elif stat.cooldown:

            suffix = "!"

        concept_parts.append(

            f"{name}:"
            f"{stat.count}"
            f"{suffix}"
        )

    concept_text = (

        ",".join(
            concept_parts
        )

        if concept_parts

        else

        "-"
    )

    if analysis.emoji_counts:

        sorted_emojis = sorted(

            analysis
            .emoji_counts
            .items(),

            key=lambda item:
                (
                    -item[1],
                    item[0]
                )
        )

        emoji_text = (

            ",".join(

                f"{emoji}:"
                f"{count}"

                for (
                    emoji,
                    count
                ) in (
                    sorted_emojis[
                        :6
                    ]
                )
            )
        )

    else:

        emoji_text = (
            "-"
        )

    violation_text = (

        ",".join(
            analysis.candidate_violations
        )

        if analysis.candidate_violations

        else

        "-"
    )

    return (

        "[COHERENCE] "

        f"v={COHERENCE_VERSION} "

        f"history="
        f"{len(analysis.recent_messages)} "

        f"concepts="
        f"{concept_text} "

        f"avoid_concepts="
        f"{analysis.avoid_concepts} "

        f"emojis="
        f"{emoji_text} "

        f"avoid_emojis="
        f"{analysis.avoid_emojis} "

        f"avoid_openers="
        f"{analysis.avoid_openers} "

        f"assistant="
        f"{analysis.assistant_pattern_count} "

        f"filler="
        f"{analysis.filler_pattern_count} "

        f"candidate_similarity="
        f"{analysis.candidate_similarity:.2f} "

        f"violations="
        f"{violation_text}"
    )


# =========================================================
# SELF TEST
#
# Kann direkt mit:
#
# python coherence.py
#
# getestet werden.
# =========================================================

def _self_test():

    recent = [

        (
            "bisschen Chaos "
            "muss sein 😈"
        ),

        (
            "ohne Chaos "
            "wird es langweilig 😂"
        ),

        (
            "das wird richtig "
            "wild 😏"
        ),

        (
            "Chaos pur, "
            "was soll schon passieren 😈"
        ),

        (
            "ja klar, "
            "wird bestimmt spannend 😂"
        ),

        (
            "die mods brauchen "
            "auch ein bisschen Chaos 😏"
        ),
    ]

    candidate = (

        "hahaha, "
        "ein bisschen Chaos "
        "muss sein 😂"
    )

    analysis = (

        analyze_coherence(

            recent,

            candidate=candidate
        )
    )

    print(
        format_coherence_debug(
            analysis
        )
    )

    print("")

    print(
        format_coherence_for_writer(
            analysis
        )
    )


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    _self_test()
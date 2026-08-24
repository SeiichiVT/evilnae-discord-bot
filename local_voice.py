import asyncio
import json
import os
import re
import time
import urllib.request

from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

from voice_memory import (
    get_relevant_voice_examples,
    format_voice_examples,
)

from coherence import (
    CoherenceAnalysis,
    analyze_coherence,
    format_coherence_for_critic,
)


# =========================================================
# VERSION
# =========================================================

LOCAL_VOICE_VERSION = "1.2.5"


# =========================================================
# ENV
# =========================================================

load_dotenv()


def env_bool(
    name,
    default=False
):
    value = os.getenv(name)

    if value is None:
        return default

    return (
        value.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


LOCAL_VOICE_ENABLED = env_bool(
    "LOCAL_VOICE_ENABLED",
    True
)

LOCAL_VOICE_URL = (
    os.getenv(
        "LOCAL_VOICE_URL",
        "http://127.0.0.1:11434"
    )
    .rstrip("/")
)

LOCAL_VOICE_MODEL = os.getenv(
    "LOCAL_VOICE_MODEL",
    "qwen3:4b-instruct"
)

LOCAL_VOICE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_TIMEOUT",
        "60"
    )
)

LOCAL_VOICE_QUEUE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_QUEUE_TIMEOUT",
        "5"
    )
)

LOCAL_VOICE_KEEP_ALIVE = os.getenv(
    "LOCAL_VOICE_KEEP_ALIVE",
    "5m"
)

LOCAL_VOICE_NUM_CTX = int(
    os.getenv(
        "LOCAL_VOICE_NUM_CTX",
        "4096"
    )
)

LOCAL_VOICE_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_NUM_PREDICT",
        "240"
    )
)

LOCAL_VOICE_TEMPERATURE = float(
    os.getenv(
        "LOCAL_VOICE_TEMPERATURE",
        "0.65"
    )
)


# =========================================================
# FOCUSED REPAIR
# =========================================================

LOCAL_VOICE_REPAIR_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_REPAIR_NUM_PREDICT",
        "180"
    )
)

LOCAL_VOICE_REPAIR_TEMPERATURE = float(
    os.getenv(
        "LOCAL_VOICE_REPAIR_TEMPERATURE",
        "0.50"
    )
)

LOCAL_VOICE_REPAIR_MAX_ATTEMPTS = int(
    os.getenv(
        "LOCAL_VOICE_REPAIR_MAX_ATTEMPTS",
        "2"
    )
)


# =========================================================
# CRITIC THRESHOLDS
# =========================================================

LOCAL_VOICE_BOT_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_BOT_THRESHOLD",
        "0.38"
    )
)

LOCAL_VOICE_REPETITION_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_REPETITION_THRESHOLD",
        "0.40"
    )
)

LOCAL_VOICE_MATCH_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_MATCH_THRESHOLD",
        "0.58"
    )
)

LOCAL_VOICE_MEANING_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_MEANING_THRESHOLD",
        "0.82"
    )
)

LOCAL_VOICE_PERSONA_CLICHE_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_PERSONA_CLICHE_THRESHOLD",
        "0.40"
    )
)

LOCAL_VOICE_ASSISTANT_STRUCTURE_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_ASSISTANT_STRUCTURE_THRESHOLD",
        "0.35"
    )
)

LOCAL_VOICE_CONCEPT_REPETITION_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_CONCEPT_REPETITION_THRESHOLD",
        "0.40"
    )
)

LOCAL_VOICE_EMOJI_REPETITION_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_EMOJI_REPETITION_THRESHOLD",
        "0.40"
    )
)

LOCAL_VOICE_CONTEXT_COHERENCE_THRESHOLD = float(
    os.getenv(
        "LOCAL_VOICE_CONTEXT_COHERENCE_THRESHOLD",
        "0.55"
    )
)


# =========================================================
# GPU CONCURRENCY
# =========================================================

_voice_semaphore = asyncio.Semaphore(1)


# =========================================================
# FORCED BLOCKING VIOLATIONS
# =========================================================

FORCED_BLOCKING_EXACT = {
    "assistant_structure",
    "generic_filler",
    "semantic_repetition",
    "strong_semantic_repetition",
    "trivial_collapse",
    "semantic_anchor_missing",
    "unsupported_habit_claim",
}

FORCED_BLOCKING_PREFIXES = (
    "concept_cooldown:",
    "hard_concept_cooldown:",
)


# =========================================================
# TRIVIAL COLLAPSE
# =========================================================

TRIVIAL_COLLAPSE_RESPONSES = {
    "ok",
    "okay",
    "oki",
    "okey",
    "ja",
    "jo",
    "jup",
    "jep",
    "yep",
    "yes",
    "mhm",
    "hm",
    "aha",
    "ah",
    "lol",
    "lmao",
    "true",
    "real",
    "gut",
    "nice",
    "cool",
    "passt",
    "passt schon",
    "alles klar",
    "von mir aus",
    "sure",
}


# =========================================================
# CONTENT / SEMANTIC ANCHORS
#
# Der Voice Editor darf Formulierung ändern,
# aber nicht den konkreten Kern der Aussage verlieren.
#
# Beispiel:
#
# Draft:
# "Ich bin gespannt, was ihr testen werdet."
#
# Kern:
# testen
#
# Schlechter Rewrite:
# "bisschen wild, wie immer"
#
# -> verliert den Kern.
# =========================================================

CONTENT_STOPWORDS = {
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
    "den",
    "dem",
    "ein",
    "eine",
    "einen",
    "einem",
    "einer",
    "und",
    "oder",
    "aber",
    "ist",
    "sind",
    "war",
    "waren",
    "wird",
    "werden",
    "ja",
    "ne",
    "nee",
    "nicht",
    "noch",
    "mal",
    "halt",
    "eben",
    "auch",
    "so",
    "da",
    "dann",
    "doch",
    "nur",
    "schon",
    "eigentlich",
    "was",
    "wie",
    "ob",
    "wenn",
    "weil",
    "dass",
    "mit",
    "von",
    "für",
    "fuer",
    "zu",
    "zum",
    "zur",
    "im",
    "in",
    "am",
    "an",
    "auf",
    "aus",
    "bei",
    "alles",
    "etwas",
    "bisschen",
    "mehr",
    "weniger",
}


GENERIC_STYLE_WORDS = {
    "cool",
    "nice",
    "spannend",
    "super",
    "toll",
    "gut",
    "geil",
    "wild",
    "chaos",
    "chaotisch",
    "lustig",
    "witzig",
    "spaß",
    "spass",
    "erfolg",
    "gespannt",
    "freue",
    "freut",
    "interessant",
    "interessiert",
}


# =========================================================
# ASSISTANT BOILERPLATE REMOVAL
#
# Diese Teile liefern keine eigentliche
# semantische Aussage, die der Voice Editor
# zwingend erhalten muss.
# =========================================================

ASSISTANT_BOILERPLATE_PATTERNS = [

    re.compile(
        r"\b(?:cool|okay|alles klar)[,!.\s]*"
        r"das klingt "
        r"(?:echt |wirklich |total )?"
        r"(?:spannend|super|gut|cool)[!.,\s]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bdas klingt "
        r"(?:echt |wirklich |total )?"
        r"(?:spannend|super|gut|cool)[!.,\s]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bich bin gespannt[, ]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bich freu(?:e)? mich darauf[,!. ]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bviel erfolg[!., ]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bdas freut mich zu hören[!., ]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bkein problem[!., ]*",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\balles klar[!., ]*",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# UNSUPPORTED HABIT CLAIMS
#
# Voice darf nicht plötzlich behaupten:
#
# "wie immer"
# "schon wieder"
# "typisch"
#
# wenn der Draft das gar nicht gesagt hat.
# =========================================================

HABIT_CLAIM_PATTERNS = [

    re.compile(
        r"\bwie immer\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwie üblich\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwie ueblich\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmal wieder\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bschon wieder\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bimmer wieder\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\btypisch\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bständig\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bstaendig\b",
        flags=re.IGNORECASE
    ),
]


# =========================================================
# RESULT
# =========================================================

@dataclass
class LocalVoiceResult:

    output_text: str

    used: bool

    rewritten: bool

    bot_likeness: float

    repetition: float

    evilnae_match: float

    meaning_preserved: float

    new_facts: bool

    reason: str

    duration: float = 0.0

    persona_cliche: float = 0.0

    assistant_structure: float = 0.0

    concept_repetition: float = 0.0

    emoji_repetition: float = 0.0

    context_coherence: float = 1.0

    unnecessary_compliance: float = 0.0

    character_drift: float = 0.0

    theme_borrowing: float = 0.0

    deterministic_violations: list[str] = field(
        default_factory=list
    )

    forced_rewrite: bool = False

    repair_attempted: bool = False

    repair_succeeded: bool = False

    repair_attempt_count: int = 0

    pre_coherence_score: int = 0

    post_coherence_score: int = 0


# =========================================================
# BASIC HELPERS
# =========================================================

def clamp01(
    value,
    default=0.0
):

    try:
        value = float(value)

    except (
        TypeError,
        ValueError
    ):
        return default

    return max(
        0.0,
        min(
            1.0,
            value
        )
    )


def parse_bool(
    value,
    default=False
):

    if isinstance(
        value,
        bool
    ):
        return value

    if isinstance(
        value,
        (
            int,
            float
        )
    ):
        return bool(value)

    if isinstance(
        value,
        str
    ):

        normalized = (
            value
            .strip()
            .lower()
        )

        if normalized in {
            "true",
            "1",
            "yes",
            "ja",
            "on",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
            "nein",
            "off",
        }:
            return False

    return default


# =========================================================
# CLEAN RESPONSE
# =========================================================

def clean_response_text(
    text
):

    text = (
        text
        or ""
    ).strip()

    if not text:
        return ""

    text = re.sub(
        r"^\s*Evilnae\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    quote_pairs = [
        ('"', '"'),
        ("„", "“"),
        ("“", "”"),
        ("'", "'"),
    ]

    for (
        opening,
        closing
    ) in quote_pairs:

        if (
            text.startswith(opening)
            and
            text.endswith(closing)
            and
            len(text) > 2
        ):

            candidate = (
                text[
                    len(opening):
                    len(text)
                    - len(closing)
                ]
                .strip()
            )

            if candidate:
                text = candidate
                break

    return text.strip()


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_simple_text(
    text
):

    text = (
        text
        or ""
    ).lower()

    text = re.sub(
        r"[^\wäöüß]+",
        " ",
        text,
        flags=re.UNICODE
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def extract_words(
    text
):

    return re.findall(
        r"[A-Za-zÄÖÜäöüß]+",
        (
            text
            or ""
        ).lower()
    )


# =========================================================
# REMOVE ASSISTANT BOILERPLATE
# =========================================================

def strip_assistant_boilerplate(
    text
):

    result = (
        text
        or ""
    )

    for pattern in (
        ASSISTANT_BOILERPLATE_PATTERNS
    ):

        result = pattern.sub(
            " ",
            result
        )

    result = re.sub(
        r"\s+",
        " ",
        result
    )

    return result.strip()


# =========================================================
# ANCHOR NORMALIZATION
#
# Leichtes Stemming + wichtige
# Synonymgruppen.
# =========================================================

def normalize_anchor_word(
    word
):

    word = (
        word
        .strip()
        .lower()
    )

    replacements = {
        "testen":
            "test",

        "testet":
            "test",

        "testest":
            "test",

        "getestet":
            "test",

        "testing":
            "test",

        "test":
            "test",

        "ausprobieren":
            "probier",

        "ausprobiert":
            "probier",

        "ausprobiertet":
            "probier",

        "probieren":
            "probier",

        "probiert":
            "probier",

        "probier":
            "probier",

        "später":
            "später",

        "spaeter":
            "später",

        "nachher":
            "später",

        "morgen":
            "morgen",

        "heute":
            "heute",

        "stream":
            "stream",

        "streamen":
            "stream",

        "streamt":
            "stream",

        "gestreamt":
            "stream",

        "spielen":
            "spiel",

        "spielt":
            "spiel",

        "gespielt":
            "spiel",

        "spiel":
            "spiel",

        "backen":
            "back",

        "backt":
            "back",

        "gebacken":
            "back",

        "kochen":
            "koch",

        "kocht":
            "koch",

        "gekocht":
            "koch",

        "schlafen":
            "schlaf",

        "schläft":
            "schlaf",

        "schlaeft":
            "schlaf",

        "geschlafen":
            "schlaf",
    }

    if word in replacements:
        return replacements[word]

    # -----------------------------------------------------
    # Sehr vorsichtiges deutsches Suffix-Stemming.
    # Nur längere Wörter.
    # -----------------------------------------------------

    if len(word) >= 7:

        for suffix in (
            "ern",
            "est",
            "end",
            "ung",
            "en",
            "er",
            "es",
            "em",
        ):

            if (
                word.endswith(suffix)
                and
                len(word) - len(suffix) >= 4
            ):

                return word[
                    :-len(suffix)
                ]

    if (
        len(word) >= 6
        and
        word.endswith("e")
    ):

        return word[:-1]

    return word


# =========================================================
# EXTRACT SEMANTIC ANCHORS
# =========================================================

def extract_semantic_anchors(
    text
):

    stripped = (
        strip_assistant_boilerplate(
            text
        )
    )

    anchors = []

    for word in extract_words(
        stripped
    ):

        if word in CONTENT_STOPWORDS:
            continue

        if word in GENERIC_STYLE_WORDS:
            continue

        if len(word) < 4:
            continue

        normalized = (
            normalize_anchor_word(
                word
            )
        )

        if (
            normalized
            and
            normalized not in CONTENT_STOPWORDS
            and
            normalized not in GENERIC_STYLE_WORDS
            and
            len(normalized) >= 4
        ):

            anchors.append(
                normalized
            )

    return list(
        dict.fromkeys(
            anchors
        )
    )


# =========================================================
# SEMANTIC ANCHOR PRESERVATION
# =========================================================

def semantic_anchor_preserved(
    draft,
    candidate
):

    draft_anchors = (
        extract_semantic_anchors(
            draft
        )
    )

    # -----------------------------------------------------
    # Kein konkreter Kern erkennbar.
    #
    # Dann darf dieser Guard nichts erzwingen.
    # -----------------------------------------------------

    if not draft_anchors:
        return True

    candidate_anchors = set(
        extract_semantic_anchors(
            candidate
        )
    )

    return any(
        anchor in candidate_anchors

        for anchor in draft_anchors
    )


# =========================================================
# UNSUPPORTED HABIT CLAIM
# =========================================================

def introduces_unsupported_habit_claim(
    draft,
    candidate
):

    draft = (
        draft
        or ""
    )

    candidate = (
        candidate
        or ""
    )

    for pattern in (
        HABIT_CLAIM_PATTERNS
    ):

        candidate_match = (
            pattern.search(
                candidate
            )
        )

        if not candidate_match:
            continue

        draft_match = (
            pattern.search(
                draft
            )
        )

        if not draft_match:
            return True

    return False


# =========================================================
# TRIVIAL COLLAPSE
# =========================================================

def extract_content_words(
    text
):

    return [
        word

        for word
        in extract_words(
            text
        )

        if (
            word not in CONTENT_STOPWORDS
            and
            word not in GENERIC_STYLE_WORDS
        )
    ]


def is_trivial_collapse(
    draft,
    candidate
):

    draft = (
        draft
        or ""
    ).strip()

    candidate = (
        candidate
        or ""
    ).strip()

    if not draft or not candidate:
        return True

    normalized_candidate = (
        normalize_simple_text(
            candidate
        )
    )

    draft_words = (
        extract_words(
            draft
        )
    )

    draft_content = (
        extract_content_words(
            draft
        )
    )

    candidate_words = (
        extract_words(
            candidate
        )
    )

    candidate_content = (
        extract_content_words(
            candidate
        )
    )

    if (
        len(draft_words) >= 6
        and
        normalized_candidate
        in TRIVIAL_COLLAPSE_RESPONSES
    ):
        return True

    if (
        len(draft_content) >= 5
        and
        len(candidate_content) <= 1
        and
        len(candidate) <= 18
    ):
        return True

    if (
        len(draft) >= 50
        and
        len(candidate_words) <= 1
    ):
        return True

    return False


# =========================================================
# HTTP
# =========================================================

def _ollama_chat_sync(
    payload
):

    url = (
        LOCAL_VOICE_URL
        +
        "/api/chat"
    )

    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False
        )
        .encode(
            "utf-8"
        )
    )

    request = urllib.request.Request(
        url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type":
                "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=LOCAL_VOICE_TIMEOUT
    ) as response:

        raw = (
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    return json.loads(
        raw
    )


async def ollama_chat(
    payload
):

    return await asyncio.wait_for(

        asyncio.to_thread(
            _ollama_chat_sync,
            payload
        ),

        timeout=(
            LOCAL_VOICE_TIMEOUT
            +
            1.0
        )
    )


async def run_local_model(
    *,
    system_prompt,
    user_prompt,
    temperature,
    num_predict
):

    payload = {

        "model":
            LOCAL_VOICE_MODEL,

        "stream":
            False,

        "format":
            "json",

        "keep_alive":
            LOCAL_VOICE_KEEP_ALIVE,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    system_prompt
            },

            {
                "role":
                    "user",

                "content":
                    user_prompt
            }
        ],

        "options": {

            "temperature":
                temperature,

            "num_ctx":
                LOCAL_VOICE_NUM_CTX,

            "num_predict":
                num_predict
        }
    }

    response = await ollama_chat(
        payload
    )

    try:

        return (
            response[
                "message"
            ][
                "content"
            ]
        )

    except (
        KeyError,
        TypeError
    ):

        return None


# =========================================================
# AVAILABILITY
# =========================================================

def _ollama_version_sync():

    request = urllib.request.Request(
        LOCAL_VOICE_URL
        +
        "/api/version",
        method="GET"
    )

    with urllib.request.urlopen(
        request,
        timeout=2.5
    ) as response:

        return json.loads(
            response
            .read()
            .decode(
                "utf-8"
            )
        )


async def is_local_voice_available():

    if not LOCAL_VOICE_ENABLED:
        return False

    try:

        await asyncio.wait_for(

            asyncio.to_thread(
                _ollama_version_sync
            ),

            timeout=3.0
        )

        return True

    except Exception:
        return False


# =========================================================
# WARMUP
# =========================================================

async def warm_local_voice():

    if not LOCAL_VOICE_ENABLED:
        return False

    payload = {

        "model":
            LOCAL_VOICE_MODEL,

        "stream":
            False,

        "format":
            "json",

        "keep_alive":
            LOCAL_VOICE_KEEP_ALIVE,

        "messages": [

            {
                "role":
                    "user",

                "content":
                    (
                        "Antworte nur mit "
                        '{"ok":true}'
                    )
            }
        ],

        "options": {

            "temperature":
                0.0,

            "num_ctx":
                512,

            "num_predict":
                20
        }
    }

    start = time.perf_counter()

    try:

        await ollama_chat(
            payload
        )

        print(
            "[LOCAL VOICE WARM] "
            f"model={LOCAL_VOICE_MODEL} "
            f"duration="
            f"{time.perf_counter() - start:.2f}s "
            "status=ready"
        )

        return True

    except Exception as error:

        print(
            "[LOCAL VOICE WARM] "
            f"model={LOCAL_VOICE_MODEL} "
            "status=failed "
            f"error="
            f"{type(error).__name__}: "
            f"{error}"
        )

        return False


# =========================================================
# QUESTION DETECTION
# =========================================================

QUESTION_WORDS = {
    "was",
    "wer",
    "wie",
    "warum",
    "wieso",
    "weshalb",
    "wann",
    "wo",
    "wohin",
    "woher",
    "welche",
    "welcher",
    "welches",
}


QUESTION_VERB_PATTERNS = [

    re.compile(
        r"\bkannst\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwillst\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bhast\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bbist\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwürdest\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bwuerdest\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmeinst\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bdenkst\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bfindest\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bmagst\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bweißt\s+du\b",
        flags=re.IGNORECASE
    ),

    re.compile(
        r"\bweisst\s+du\b",
        flags=re.IGNORECASE
    ),
]


RHETORICAL_ECHO_WORDS = {
    "ich",
    "du",
    "er",
    "sie",
    "wir",
    "hanae",
    "error",
    "evilnae",
    "evil",
    "das",
    "der",
    "die",
    "was",
}


def extract_question_segments(
    text
):

    text = (
        text
        or ""
    )

    segments = []

    start = 0

    for match in re.finditer(
        r"\?",
        text
    ):

        segment = (
            text[
                start:
                match.end()
            ]
            .strip()
        )

        if segment:
            segments.append(
                segment
            )

        start = match.end()

    return segments


def is_likely_genuine_question(
    segment
):

    segment = (
        segment
        or ""
    ).strip()

    if not segment.endswith("?"):
        return False

    without_mark = (
        segment[:-1]
        .strip()
    )

    if not without_mark:
        return False

    words = re.findall(
        r"[A-Za-zÄÖÜäöüß]+",
        without_mark.lower()
    )

    if not words:
        return False

    if (
        len(words) == 1
        and
        words[0]
        in RHETORICAL_ECHO_WORDS
    ):
        return False

    if words[0] in QUESTION_WORDS:
        return True

    if (
        len(words) >= 2
        and
        words[1]
        in QUESTION_WORDS
        and
        words[0]
        in {
            "und",
            "aber",
            "okay",
            "ja",
            "äh",
            "eh",
        }
    ):
        return True

    for pattern in (
        QUESTION_VERB_PATTERNS
    ):

        if pattern.search(
            without_mark
        ):
            return True

    if (
        "du"
        in words
        and
        len(words) >= 4
    ):
        return True

    return False


def count_genuine_questions(
    text
):

    return sum(

        1

        for segment
        in extract_question_segments(
            text
        )

        if is_likely_genuine_question(
            segment
        )
    )


def new_genuine_question_added(
    original,
    candidate
):

    return (
        count_genuine_questions(
            candidate
        )
        >
        count_genuine_questions(
            original
        )
    )


# =========================================================
# NEW MENTION GUARD
# =========================================================

def _new_mentions_added(
    original,
    candidate
):

    original_mentions = set(
        re.findall(
            r"<@!?\d+>",
            original
            or ""
        )
    )

    candidate_mentions = set(
        re.findall(
            r"<@!?\d+>",
            candidate
            or ""
        )
    )

    return not (
        candidate_mentions
        .issubset(
            original_mentions
        )
    )


# =========================================================
# COHERENCE SCORE
# =========================================================

def coherence_violation_score(
    violations
):

    score = 0

    for reason in (
        violations
        or []
    ):

        if reason.startswith(
            "hard_concept_cooldown:"
        ):
            score += 4

        elif reason.startswith(
            "concept_cooldown:"
        ):
            score += 3

        elif reason.startswith(
            "emoji_cooldown:"
        ):
            score += 2

        elif reason.startswith(
            "opener_cooldown:"
        ):
            score += 2

        elif reason == (
            "assistant_structure"
        ):
            score += 4

        elif reason == (
            "generic_filler"
        ):
            score += 3

        elif reason == (
            "strong_semantic_repetition"
        ):
            score += 5

        elif reason == (
            "semantic_repetition"
        ):
            score += 3

        elif reason == (
            "trivial_collapse"
        ):
            score += 4

        elif reason == (
            "semantic_anchor_missing"
        ):
            score += 4

        elif reason == (
            "unsupported_habit_claim"
        ):
            score += 4

        else:
            score += 1

    return score


# =========================================================
# VOICE CANDIDATE ANALYSIS
# =========================================================

def analyze_voice_candidate(
    *,
    history,
    draft,
    candidate
):

    analysis = analyze_coherence(
        history,
        candidate=candidate
    )

    violations = list(
        analysis
        .candidate_violations
    )

    if is_trivial_collapse(
        draft,
        candidate
    ):

        violations.append(
            "trivial_collapse"
        )

    if not semantic_anchor_preserved(
        draft,
        candidate
    ):

        violations.append(
            "semantic_anchor_missing"
        )

    if introduces_unsupported_habit_claim(
        draft,
        candidate
    ):

        violations.append(
            "unsupported_habit_claim"
        )

    violations = list(
        dict.fromkeys(
            violations
        )
    )

    return (
        analysis,
        violations
    )


# =========================================================
# BLOCKING VIOLATIONS
# =========================================================

def has_forced_blocking_violations(
    violations
):

    for reason in (
        violations
        or []
    ):

        if reason in FORCED_BLOCKING_EXACT:
            return True

        if reason.startswith(
            FORCED_BLOCKING_PREFIXES
        ):
            return True

    return False


# =========================================================
# DETERMINISTIC REWRITE PRESSURE
# =========================================================

def deterministic_rewrite_needed(
    coherence_analysis
):

    if not coherence_analysis:
        return False

    serious_prefixes = (
        "hard_concept_cooldown:",
        "concept_cooldown:",
        "emoji_cooldown:",
        "opener_cooldown:",
    )

    serious_exact = {
        "assistant_structure",
        "generic_filler",
        "strong_semantic_repetition",
        "semantic_repetition",
    }

    for reason in (
        coherence_analysis
        .candidate_violations
    ):

        if reason in serious_exact:
            return True

        if reason.startswith(
            serious_prefixes
        ):
            return True

    return False


# =========================================================
# FORCED REPAIR REQUIRED
# =========================================================

def forced_repair_required(
    *,
    deterministic_pressure,
    draft,
    candidate,
    pre_score,
    post_score,
    post_violations
):

    if not deterministic_pressure:
        return False

    if (
        not candidate
        or
        candidate.strip()
        ==
        draft.strip()
    ):
        return True

    if (
        post_score
        >=
        pre_score
    ):
        return True

    if has_forced_blocking_violations(
        post_violations
    ):
        return True

    return False


# =========================================================
# VOICE SYSTEM PROMPT
# =========================================================

VOICE_SYSTEM_PROMPT = """
Du bist Evilnaes Voice Editor und Critic.

Du bist NICHT ihr Brain.

Der Inhalt wurde bereits entschieden.
Du änderst nur die Formulierung.

Du darfst niemals:
- neue Fakten erfinden
- Fakten verändern
- Erinnerungen erfinden
- Beziehungen verändern
- neue Aktionen erfinden
- Versprechen hinzufügen
- neue Discord-Mentions hinzufügen
- die eigentliche Aussage verändern

Erkenne klassische Bot-Sprache:
- "Das klingt spannend"
- "Ich bin gespannt"
- "Viel Erfolg"
- künstliche Bestätigung
- Zusammenfassung des Users
- freundlicher Service-Abschluss
- unnötige Gegenfragen

Erkenne AUCH Persona-Bot-Sprache:
- ständig Chaos
- ständig wild
- ständig langweilig
- ständig haha/hahaha
- ständig dieselben Emojis
- künstlich edgy
- Gremlin-Template
- Persönlichkeit erklären statt zeigen

Evilnaes Persönlichkeit entsteht aus:
- Haltung
- Reaktion
- Timing
- Gedanken

Nicht aus Persona-Schlagwörtern.

Wenn Coherence einen Verstoß meldet,
nimm ihn ernst.

Wenn assistant_structure erkannt wurde,
reicht es nicht,
nur ein Emoji zu entfernen.

Die Assistant-Struktur selbst muss weg.

SEHR WICHTIG:

Der konkrete Inhalt des Drafts
muss erhalten bleiben.

Wenn der Draft beispielsweise davon spricht,
dass jemand Evilnae später testet,
darfst du daraus NICHT einfach
"bisschen wild" machen.

Du darfst außerdem keine neuen
Gewohnheiten oder Historien behaupten.

Nicht neu hinzufügen:
- "wie immer"
- "wie üblich"
- "schon wieder"
- "mal wieder"
- "typisch"

wenn der Draft so etwas nicht enthält.

Kurz ist gut.
Inhaltsverlust ist nicht gut.

Character Drift,
Theme Borrowing und
unnötigen Gehorsam nur bewerten.
Nicht eigenmächtig inhaltlich korrigieren.

JSON kurz halten.

Antworte ausschließlich mit
gültigem vollständigem JSON.
""".strip()


# =========================================================
# FOCUSED REPAIR SYSTEM
# =========================================================

FOCUSED_REPAIR_SYSTEM_PROMPT = """
Du bist Evilnaes Focused Voice Repair.

Der deterministische Guard hat bereits entschieden,
dass der Draft sprachlich nicht akzeptabel ist.

Der Rewrite IST nötig.

Formuliere denselben Gedanken natürlicher neu.

Du darfst NICHT:
- neue Fakten erfinden
- Fakten ändern
- Erinnerungen erfinden
- Beziehungen ändern
- neue Handlungen erfinden
- Versprechen hinzufügen
- neue Namen erfinden
- neue Discord-Mentions hinzufügen
- neue echte Gegenfragen hinzufügen
- Lore korrigieren
- neue Gewohnheiten behaupten

Der konkrete Inhalt des Drafts
muss sichtbar erhalten bleiben.

Wenn dir REQUIRED ANCHORS gegeben werden,
muss mindestens einer dieser
inhaltlichen Kerne im neuen Text
erkennbar erhalten bleiben.

Wenn assistant_structure gemeldet wurde:
entferne die Assistant-Struktur selbst.

Wenn generic_filler gemeldet wurde:
gib eine echte kleine Reaktion.

Wenn Concept-Cooldown gemeldet wurde:
nutze einen anderen Aspekt derselben Aussage.

Wenn Semantic Repetition gemeldet wurde:
formuliere deutlich anders.

Nicht einfach:
- ok
- ja
- lol
- passt
- wie immer
- bisschen wild

Keine Erklärung.

Antworte nur als JSON.
""".strip()


# =========================================================
# FORMAT RECENT
# =========================================================

def format_recent_messages(
    messages,
    *,
    limit=10
):

    messages = [

        str(message).strip()

        for message
        in (
            messages
            or []
        )

        if (
            message is not None
            and
            str(message).strip()
        )
    ]

    if not messages:
        return "Keine."

    return "\n".join(

        f"- {message}"

        for message
        in messages[
            -limit:
        ]
    )


# =========================================================
# NORMAL VOICE PROMPT
# =========================================================

def build_voice_prompt(
    *,
    user_message,
    draft,
    conversation_mode,
    response_goal,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages,
    channel_recent_evilnae_messages,
    coherence_analysis,
    good_examples,
    bad_examples,
    identity_context=""
):

    if allow_question:

        question_rule = (
            "Natürliche Frage erlaubt."
        )

    else:

        question_rule = (
            "Keine neue echte Gegenfrage."
        )

    identity_text = (
        identity_context.strip()

        if (
            identity_context
            and
            identity_context.strip()
        )

        else
        "Kein zusätzlicher Identity Context."
    )

    violations = (

        ", ".join(
            coherence_analysis
            .candidate_violations
        )

        if coherence_analysis
        .candidate_violations

        else
        "keine"
    )

    anchors = (
        extract_semantic_anchors(
            draft
        )
    )

    anchor_text = (
        ", ".join(
            anchors
        )

        if anchors

        else
        "keine"
    )

    return f"""
USER:
{user_message}

MODE:
{conversation_mode}

GOAL:
{response_goal}

STATE:
{inner_state_guidance}

IDENTITY:
{identity_text}

DRAFT:
{draft}

REQUIRED CONTENT ANCHORS:
{anchor_text}

QUESTION:
{question_rule}

RECENT USER-SPECIFIC:
{format_recent_messages(
    recent_evilnae_messages,
    limit=5
)}

RECENT CHANNEL-WIDE:
{format_recent_messages(
    channel_recent_evilnae_messages,
    limit=10
)}

COHERENCE:
{format_coherence_for_critic(
    coherence_analysis
)}

DRAFT VIOLATIONS:
{violations}

GOOD EXAMPLES:
{format_voice_examples(
    good_examples
)}

BAD EXAMPLES:
{format_voice_examples(
    bad_examples
)}

Bewerte:

b = bot_likeness
r = repetition
m = evilnae_match
p = persona_cliche
a = assistant_structure
c = concept_repetition
e = emoji_repetition
x = context_coherence
u = unnecessary_compliance
d = character_drift
t = theme_borrowing
g = meaning_preserved
f = new_facts
w = rewrite
z = Grund max 8 Wörter
o = finale Antwort

Wenn REQUIRED CONTENT ANCHORS vorhanden sind,
muss mindestens einer inhaltlich erhalten bleiben.

Keine neuen Aussagen wie "wie immer",
wenn sie im Draft nicht vorkommen.

JSON:

{{
  "b":0.0,
  "r":0.0,
  "m":1.0,
  "p":0.0,
  "a":0.0,
  "c":0.0,
  "e":0.0,
  "x":1.0,
  "u":0.0,
  "d":0.0,
  "t":0.0,
  "g":1.0,
  "f":false,
  "w":false,
  "z":"",
  "o":""
}}
""".strip()


# =========================================================
# FOCUSED REPAIR PROMPT
# =========================================================

def build_focused_repair_prompt(
    *,
    user_message,
    draft,
    allow_question,
    channel_recent_evilnae_messages,
    coherence_analysis,
    previous_failed_candidate="",
    previous_failure_reason=""
):

    violations = (

        ", ".join(
            coherence_analysis
            .candidate_violations
        )

        if coherence_analysis
        .candidate_violations

        else
        "unbekannt"
    )

    anchors = (
        extract_semantic_anchors(
            draft
        )
    )

    anchor_text = (

        ", ".join(
            anchors
        )

        if anchors

        else
        "keine"
    )

    avoid_concepts = (

        ", ".join(
            coherence_analysis
            .avoid_concepts
        )

        if coherence_analysis
        .avoid_concepts

        else
        "keine"
    )

    hard_concepts = (

        ", ".join(
            coherence_analysis
            .hard_avoid_concepts
        )

        if coherence_analysis
        .hard_avoid_concepts

        else
        "keine"
    )

    avoid_emojis = (

        " ".join(
            coherence_analysis
            .avoid_emojis
        )

        if coherence_analysis
        .avoid_emojis

        else
        "keine"
    )

    avoid_openers = (

        ", ".join(
            coherence_analysis
            .avoid_openers
        )

        if coherence_analysis
        .avoid_openers

        else
        "keine"
    )

    if allow_question:

        question_rule = (
            "Frage erlaubt."
        )

    else:

        question_rule = (
            "Keine neue echte Gegenfrage."
        )

    failed_section = ""

    if previous_failed_candidate:

        failed_section = f"""
VORHERIGER REPAIR:
{previous_failed_candidate}

ABGELEHNT WEGEN:
{previous_failure_reason}

Diesen Fehler nicht wiederholen.
""".strip()

    return f"""
USER:
{user_message}

DRAFT:
{draft}

REQUIRED CONTENT ANCHORS:
{anchor_text}

PROBLEME:
{violations}

AVOID CONCEPTS:
{avoid_concepts}

HARD AVOID:
{hard_concepts}

AVOID EMOJIS:
{avoid_emojis}

AVOID OPENERS:
{avoid_openers}

QUESTION:
{question_rule}

RECENT:
{format_recent_messages(
    channel_recent_evilnae_messages,
    limit=8
)}

{failed_section}

AUFGABE:

Formuliere denselben Gedanken neu.

Wenn REQUIRED CONTENT ANCHORS
nicht "keine" sind,
muss mindestens einer davon
im neuen Text erkennbar erhalten bleiben.

Keine neuen Gewohnheitsbehauptungen
wie "wie immer".

Kurz ist okay.
Inhaltsverlust nicht.

g = Bedeutung erhalten
f = neue Fakten
z = kurzer Grund
o = neue Antwort

JSON:

{{
  "g":1.0,
  "f":false,
  "z":"",
  "o":""
}}
""".strip()


# =========================================================
# JSON EXTRACTION
# =========================================================

def extract_json_dict(
    raw_text
):

    raw_text = (
        raw_text
        or ""
    ).strip()

    raw_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw_text,
        flags=re.IGNORECASE
    )

    raw_text = re.sub(
        r"\s*```$",
        "",
        raw_text
    )

    try:

        data = json.loads(
            raw_text
        )

    except json.JSONDecodeError:

        start = raw_text.find(
            "{"
        )

        end = raw_text.rfind(
            "}"
        )

        if (
            start == -1
            or
            end == -1
            or
            end <= start
        ):
            return None

        try:

            data = json.loads(
                raw_text[
                    start:
                    end + 1
                ]
            )

        except json.JSONDecodeError:
            return None

    if not isinstance(
        data,
        dict
    ):
        return None

    return data


# =========================================================
# COMPATIBLE KEY
# =========================================================

def get_result_value(
    data,
    short_key,
    long_key,
    default=None
):

    if short_key in data:
        return data.get(
            short_key
        )

    return data.get(
        long_key,
        default
    )


# =========================================================
# NORMAL RESULT PARSER
# =========================================================

def parse_voice_result(
    raw_text,
    original_draft
):

    data = extract_json_dict(
        raw_text
    )

    if data is None:
        return None

    response_text = (
        clean_response_text(

            get_result_value(
                data,
                "o",
                "response",
                ""
            )
        )
        or
        original_draft
    )

    return {

        "bot_likeness":
            clamp01(
                get_result_value(
                    data,
                    "b",
                    "bot_likeness"
                ),
                0.5
            ),

        "repetition":
            clamp01(
                get_result_value(
                    data,
                    "r",
                    "repetition"
                ),
                0.0
            ),

        "evilnae_match":
            clamp01(
                get_result_value(
                    data,
                    "m",
                    "evilnae_match"
                ),
                0.5
            ),

        "persona_cliche":
            clamp01(
                get_result_value(
                    data,
                    "p",
                    "persona_cliche"
                ),
                0.0
            ),

        "assistant_structure":
            clamp01(
                get_result_value(
                    data,
                    "a",
                    "assistant_structure"
                ),
                0.0
            ),

        "concept_repetition":
            clamp01(
                get_result_value(
                    data,
                    "c",
                    "concept_repetition"
                ),
                0.0
            ),

        "emoji_repetition":
            clamp01(
                get_result_value(
                    data,
                    "e",
                    "emoji_repetition"
                ),
                0.0
            ),

        "context_coherence":
            clamp01(
                get_result_value(
                    data,
                    "x",
                    "context_coherence"
                ),
                1.0
            ),

        "unnecessary_compliance":
            clamp01(
                get_result_value(
                    data,
                    "u",
                    "unnecessary_compliance"
                ),
                0.0
            ),

        "character_drift":
            clamp01(
                get_result_value(
                    data,
                    "d",
                    "character_drift"
                ),
                0.0
            ),

        "theme_borrowing":
            clamp01(
                get_result_value(
                    data,
                    "t",
                    "theme_borrowing"
                ),
                0.0
            ),

        "meaning_preserved":
            clamp01(
                get_result_value(
                    data,
                    "g",
                    "meaning_preserved"
                ),
                0.0
            ),

        "new_facts":
            parse_bool(
                get_result_value(
                    data,
                    "f",
                    "new_facts",
                    False
                )
            ),

        "model_rewrite":
            parse_bool(
                get_result_value(
                    data,
                    "w",
                    "rewrite",
                    False
                )
            ),

        "response":
            response_text,

        "reason":
            str(
                get_result_value(
                    data,
                    "z",
                    "reason",
                    ""
                )
            )[:160]
    }


# =========================================================
# REPAIR PARSER
# =========================================================

def parse_repair_result(
    raw_text
):

    data = extract_json_dict(
        raw_text
    )

    if data is None:
        return None

    response_text = (
        clean_response_text(

            get_result_value(
                data,
                "o",
                "response",
                ""
            )
        )
    )

    return {

        "meaning_preserved":
            clamp01(
                get_result_value(
                    data,
                    "g",
                    "meaning_preserved"
                ),
                0.0
            ),

        "new_facts":
            parse_bool(
                get_result_value(
                    data,
                    "f",
                    "new_facts",
                    False
                )
            ),

        "response":
            response_text,

        "reason":
            str(
                get_result_value(
                    data,
                    "z",
                    "reason",
                    ""
                )
            )[:120]
    }


# =========================================================
# CANDIDATE SAFETY
# =========================================================

def validate_voice_candidate(
    *,
    draft,
    candidate,
    allow_question,
    meaning_preserved,
    new_facts
):

    candidate = clean_response_text(
        candidate
    )

    if not candidate:

        return (
            False,
            "empty_rewrite"
        )

    if (
        meaning_preserved
        <
        LOCAL_VOICE_MEANING_THRESHOLD
    ):

        return (
            False,
            "meaning_changed"
        )

    if new_facts:

        return (
            False,
            "new_facts_added"
        )

    if (
        not allow_question
        and
        new_genuine_question_added(
            draft,
            candidate
        )
    ):

        return (
            False,
            "new_question_added"
        )

    if re.search(
        r"\bfair(?:\s+enough)?\b",
        candidate,
        flags=re.IGNORECASE
    ):

        return (
            False,
            "banned_word_added"
        )

    if _new_mentions_added(
        draft,
        candidate
    ):

        return (
            False,
            "new_mention_added"
        )

    if is_trivial_collapse(
        draft,
        candidate
    ):

        return (
            False,
            "trivial_collapse"
        )

    if not semantic_anchor_preserved(
        draft,
        candidate
    ):

        return (
            False,
            "semantic_anchor_missing"
        )

    if introduces_unsupported_habit_claim(
        draft,
        candidate
    ):

        return (
            False,
            "unsupported_habit_claim"
        )

    return (
        True,
        ""
    )


# =========================================================
# FOCUSED REPAIR
# =========================================================

async def attempt_focused_repair(
    *,
    user_message,
    draft,
    allow_question,
    channel_recent_evilnae_messages,
    coherence_analysis
):

    pre_score = (
        coherence_violation_score(
            coherence_analysis
            .candidate_violations
        )
    )

    previous_failed_candidate = ""
    previous_failure_reason = ""

    total_start = (
        time.perf_counter()
    )

    max_attempts = max(
        1,
        LOCAL_VOICE_REPAIR_MAX_ATTEMPTS
    )

    for attempt in range(
        1,
        max_attempts + 1
    ):

        prompt = (
            build_focused_repair_prompt(

                user_message=(
                    user_message
                ),

                draft=(
                    draft
                ),

                allow_question=(
                    allow_question
                ),

                channel_recent_evilnae_messages=(
                    channel_recent_evilnae_messages
                ),

                coherence_analysis=(
                    coherence_analysis
                ),

                previous_failed_candidate=(
                    previous_failed_candidate
                ),

                previous_failure_reason=(
                    previous_failure_reason
                )
            )
        )

        try:

            raw_content = (
                await run_local_model(

                    system_prompt=(
                        FOCUSED_REPAIR_SYSTEM_PROMPT
                    ),

                    user_prompt=(
                        prompt
                    ),

                    temperature=(
                        LOCAL_VOICE_REPAIR_TEMPERATURE
                    ),

                    num_predict=(
                        LOCAL_VOICE_REPAIR_NUM_PREDICT
                    )
                )
            )

        except Exception as error:

            previous_failure_reason = (
                "repair_model_failed"
            )

            print(
                "[LOCAL VOICE REPAIR] "
                f"attempt={attempt} "
                "status=failed "
                f"reason="
                f"{type(error).__name__}"
            )

            continue

        if raw_content is None:

            previous_failure_reason = (
                "repair_invalid_response"
            )

            print(
                "[LOCAL VOICE REPAIR] "
                f"attempt={attempt} "
                "status=failed "
                "reason=invalid_response"
            )

            continue

        parsed = parse_repair_result(
            raw_content
        )

        if parsed is None:

            previous_failure_reason = (
                "repair_json_parse_error"
            )

            print(
                "[LOCAL VOICE REPAIR] "
                f"attempt={attempt} "
                "status=failed "
                "reason=json_parse_error "
                f"raw={raw_content[:300]!r}"
            )

            continue

        candidate = clean_response_text(
            parsed[
                "response"
            ]
        )

        (
            valid,
            validation_reason
        ) = validate_voice_candidate(

            draft=(
                draft
            ),

            candidate=(
                candidate
            ),

            allow_question=(
                allow_question
            ),

            meaning_preserved=(
                parsed[
                    "meaning_preserved"
                ]
            ),

            new_facts=(
                parsed[
                    "new_facts"
                ]
            )
        )

        if not valid:

            previous_failed_candidate = (
                candidate
            )

            previous_failure_reason = (
                validation_reason
            )

            print(
                "[LOCAL VOICE REPAIR] "
                f"attempt={attempt} "
                "status=rejected "
                f"candidate={candidate!r} "
                f"reason={validation_reason}"
            )

            continue

        (
            repair_analysis,
            repair_violations
        ) = analyze_voice_candidate(

            history=(
                channel_recent_evilnae_messages
            ),

            draft=(
                draft
            ),

            candidate=(
                candidate
            )
        )

        repair_score = (
            coherence_violation_score(
                repair_violations
            )
        )

        success = (

            candidate.strip()
            !=
            draft.strip()

            and

            repair_score
            <
            pre_score

            and

            not has_forced_blocking_violations(
                repair_violations
            )
        )

        if success:

            duration = (
                time.perf_counter()
                -
                total_start
            )

            print(
                "[LOCAL VOICE REPAIR] "
                f"attempt={attempt} "
                "status=success "
                f"duration={duration:.2f}s "
                f"pre={pre_score} "
                f"post={repair_score} "
                f"candidate={candidate!r} "
                f"violations="
                f"{repair_violations}"
            )

            return {
                "success":
                    True,

                "candidate":
                    candidate,

                "analysis":
                    repair_analysis,

                "violations":
                    repair_violations,

                "score":
                    repair_score,

                "reason":
                    (
                        parsed[
                            "reason"
                        ]
                        or
                        "focused_repair"
                    ),

                "duration":
                    duration,

                "attempts":
                    attempt,
            }

        if has_forced_blocking_violations(
            repair_violations
        ):

            failure_reason = (
                "blocking_violation_remains"
            )

        else:

            failure_reason = (
                "repair_no_improvement"
            )

        previous_failed_candidate = (
            candidate
        )

        previous_failure_reason = (
            failure_reason
        )

        print(
            "[LOCAL VOICE REPAIR] "
            f"attempt={attempt} "
            "status=rejected "
            f"pre={pre_score} "
            f"post={repair_score} "
            f"candidate={candidate!r} "
            f"violations={repair_violations} "
            f"reason={failure_reason}"
        )

    duration = (
        time.perf_counter()
        -
        total_start
    )

    return {
        "success":
            False,

        "candidate":
            draft,

        "analysis":
            coherence_analysis,

        "violations":
            list(
                coherence_analysis
                .candidate_violations
            ),

        "score":
            pre_score,

        "reason":
            (
                previous_failure_reason
                or
                "repair_failed"
            ),

        "duration":
            duration,

        "attempts":
            max_attempts,
    }


# =========================================================
# MAIN HUMANIZER
# =========================================================

async def humanize_evilnae_response(
    *,
    user_message,
    draft,
    conversation_mode,
    response_goal,
    allow_question,
    inner_state_guidance,
    recent_evilnae_messages,
    channel_recent_evilnae_messages=None,
    coherence_analysis: Optional[
        CoherenceAnalysis
    ] = None,
    identity_context=""
):

    draft = (
        draft
        or ""
    ).strip()

    def fallback(
        reason,
        duration=0.0,
        deterministic_violations=None,
        forced_rewrite=False,
        pre_score=0,
        **scores
    ):

        return LocalVoiceResult(

            output_text=draft,

            used=False,

            rewritten=False,

            bot_likeness=(
                scores.get(
                    "bot_likeness",
                    0.0
                )
            ),

            repetition=(
                scores.get(
                    "repetition",
                    0.0
                )
            ),

            evilnae_match=(
                scores.get(
                    "evilnae_match",
                    1.0
                )
            ),

            meaning_preserved=(
                scores.get(
                    "meaning_preserved",
                    1.0
                )
            ),

            new_facts=(
                scores.get(
                    "new_facts",
                    False
                )
            ),

            reason=reason,

            duration=duration,

            persona_cliche=(
                scores.get(
                    "persona_cliche",
                    0.0
                )
            ),

            assistant_structure=(
                scores.get(
                    "assistant_structure",
                    0.0
                )
            ),

            concept_repetition=(
                scores.get(
                    "concept_repetition",
                    0.0
                )
            ),

            emoji_repetition=(
                scores.get(
                    "emoji_repetition",
                    0.0
                )
            ),

            context_coherence=(
                scores.get(
                    "context_coherence",
                    1.0
                )
            ),

            unnecessary_compliance=(
                scores.get(
                    "unnecessary_compliance",
                    0.0
                )
            ),

            character_drift=(
                scores.get(
                    "character_drift",
                    0.0
                )
            ),

            theme_borrowing=(
                scores.get(
                    "theme_borrowing",
                    0.0
                )
            ),

            deterministic_violations=list(
                deterministic_violations
                or []
            ),

            forced_rewrite=(
                forced_rewrite
            ),

            repair_attempted=False,

            repair_succeeded=False,

            repair_attempt_count=0,

            pre_coherence_score=(
                pre_score
            ),

            post_coherence_score=(
                pre_score
            )
        )

    if not draft:

        return fallback(
            "empty_draft"
        )

    if not LOCAL_VOICE_ENABLED:

        return fallback(
            "disabled"
        )

    recent_evilnae_messages = list(
        recent_evilnae_messages
        or []
    )

    if (
        channel_recent_evilnae_messages
        is None
    ):

        channel_recent_evilnae_messages = list(
            recent_evilnae_messages
        )

    else:

        channel_recent_evilnae_messages = list(
            channel_recent_evilnae_messages
            or []
        )

    # =====================================================
    # PRE COHERENCE
    # =====================================================

    if coherence_analysis is None:

        coherence_analysis = analyze_coherence(

            channel_recent_evilnae_messages,

            candidate=draft
        )

    draft_violations = list(
        coherence_analysis
        .candidate_violations
    )

    draft_violation_score = (
        coherence_violation_score(
            draft_violations
        )
    )

    deterministic_pressure = (
        deterministic_rewrite_needed(
            coherence_analysis
        )
    )

    # =====================================================
    # GPU QUEUE
    # =====================================================

    try:

        await asyncio.wait_for(

            _voice_semaphore.acquire(),

            timeout=(
                LOCAL_VOICE_QUEUE_TIMEOUT
            )
        )

    except asyncio.TimeoutError:

        print(
            "[LOCAL VOICE FALLBACK] "
            "reason=queue_busy"
        )

        return fallback(

            "queue_busy",

            deterministic_violations=(
                draft_violations
            ),

            forced_rewrite=(
                deterministic_pressure
            ),

            pre_score=(
                draft_violation_score
            )
        )

    total_start = (
        time.perf_counter()
    )

    try:

        (
            good_examples,
            bad_examples
        ) = get_relevant_voice_examples(
            user_message
        )

        prompt = build_voice_prompt(

            user_message=(
                user_message
            ),

            draft=(
                draft
            ),

            conversation_mode=(
                conversation_mode
            ),

            response_goal=(
                response_goal
            ),

            allow_question=(
                allow_question
            ),

            inner_state_guidance=(
                inner_state_guidance
            ),

            recent_evilnae_messages=(
                recent_evilnae_messages
            ),

            channel_recent_evilnae_messages=(
                channel_recent_evilnae_messages
            ),

            coherence_analysis=(
                coherence_analysis
            ),

            good_examples=(
                good_examples
            ),

            bad_examples=(
                bad_examples
            ),

            identity_context=(
                identity_context
            )
        )

        # =================================================
        # FIRST PASS
        # =================================================

        try:

            raw_content = await run_local_model(

                system_prompt=(
                    VOICE_SYSTEM_PROMPT
                ),

                user_prompt=(
                    prompt
                ),

                temperature=(
                    LOCAL_VOICE_TEMPERATURE
                ),

                num_predict=(
                    LOCAL_VOICE_NUM_PREDICT
                )
            )

        except Exception as error:

            duration = (
                time.perf_counter()
                -
                total_start
            )

            print(
                "[LOCAL VOICE FALLBACK] "
                f"model={LOCAL_VOICE_MODEL} "
                f"duration={duration:.2f}s "
                f"reason="
                f"{type(error).__name__}"
            )

            return fallback(

                "local_model_unavailable",

                duration,

                deterministic_violations=(
                    draft_violations
                ),

                forced_rewrite=(
                    deterministic_pressure
                ),

                pre_score=(
                    draft_violation_score
                )
            )

        if raw_content is None:

            duration = (
                time.perf_counter()
                -
                total_start
            )

            return fallback(

                "invalid_ollama_response",

                duration,

                deterministic_violations=(
                    draft_violations
                ),

                forced_rewrite=(
                    deterministic_pressure
                ),

                pre_score=(
                    draft_violation_score
                )
            )

        parsed = parse_voice_result(
            raw_content,
            draft
        )

        # =================================================
        # PARSE FAILED
        # =================================================

        if parsed is None:

            print(
                "[LOCAL VOICE PARSE ERROR] "
                f"raw="
                f"{raw_content[:700]!r}"
            )

            if deterministic_pressure:

                repair_result = (
                    await attempt_focused_repair(

                        user_message=(
                            user_message
                        ),

                        draft=(
                            draft
                        ),

                        allow_question=(
                            allow_question
                        ),

                        channel_recent_evilnae_messages=(
                            channel_recent_evilnae_messages
                        ),

                        coherence_analysis=(
                            coherence_analysis
                        )
                    )
                )

                duration = (
                    time.perf_counter()
                    -
                    total_start
                )

                if repair_result[
                    "success"
                ]:

                    return LocalVoiceResult(

                        output_text=(
                            repair_result[
                                "candidate"
                            ]
                        ),

                        used=True,

                        rewritten=True,

                        bot_likeness=0.5,

                        repetition=0.5,

                        evilnae_match=0.5,

                        meaning_preserved=1.0,

                        new_facts=False,

                        reason=(
                            "parse_failed_then_"
                            "focused_repair"
                        ),

                        duration=(
                            duration
                        ),

                        deterministic_violations=(
                            repair_result[
                                "violations"
                            ]
                        ),

                        forced_rewrite=True,

                        repair_attempted=True,

                        repair_succeeded=True,

                        repair_attempt_count=(
                            repair_result[
                                "attempts"
                            ]
                        ),

                        pre_coherence_score=(
                            draft_violation_score
                        ),

                        post_coherence_score=(
                            repair_result[
                                "score"
                            ]
                        )
                    )

                return fallback(

                    "json_parse_and_repair_failed",

                    duration,

                    deterministic_violations=(
                        draft_violations
                    ),

                    forced_rewrite=True,

                    pre_score=(
                        draft_violation_score
                    )
                )

            duration = (
                time.perf_counter()
                -
                total_start
            )

            return fallback(

                "json_parse_error",

                duration,

                deterministic_violations=(
                    draft_violations
                ),

                forced_rewrite=False,

                pre_score=(
                    draft_violation_score
                )
            )

        # =================================================
        # SHOULD REWRITE
        # =================================================

        should_rewrite = (

            deterministic_pressure

            or

            parsed[
                "model_rewrite"
            ]

            or

            parsed[
                "bot_likeness"
            ]
            >=
            LOCAL_VOICE_BOT_THRESHOLD

            or

            parsed[
                "repetition"
            ]
            >=
            LOCAL_VOICE_REPETITION_THRESHOLD

            or

            parsed[
                "persona_cliche"
            ]
            >=
            LOCAL_VOICE_PERSONA_CLICHE_THRESHOLD

            or

            parsed[
                "assistant_structure"
            ]
            >=
            LOCAL_VOICE_ASSISTANT_STRUCTURE_THRESHOLD

            or

            parsed[
                "concept_repetition"
            ]
            >=
            LOCAL_VOICE_CONCEPT_REPETITION_THRESHOLD

            or

            parsed[
                "emoji_repetition"
            ]
            >=
            LOCAL_VOICE_EMOJI_REPETITION_THRESHOLD

            or

            parsed[
                "evilnae_match"
            ]
            <
            LOCAL_VOICE_MATCH_THRESHOLD
        )

        if should_rewrite:

            candidate = (
                clean_response_text(
                    parsed[
                        "response"
                    ]
                )
            )

        else:

            candidate = (
                draft
            )

        reason = (
            parsed[
                "reason"
            ]
        )

        # =================================================
        # FIRST CANDIDATE SAFETY
        # =================================================

        if should_rewrite:

            (
                valid,
                validation_reason
            ) = validate_voice_candidate(

                draft=(
                    draft
                ),

                candidate=(
                    candidate
                ),

                allow_question=(
                    allow_question
                ),

                meaning_preserved=(
                    parsed[
                        "meaning_preserved"
                    ]
                ),

                new_facts=(
                    parsed[
                        "new_facts"
                    ]
                )
            )

            if not valid:

                print(
                    "[LOCAL VOICE FIRST PASS REJECT] "
                    f"candidate={candidate!r} "
                    f"reason={validation_reason}"
                )

                candidate = (
                    draft
                )

                reason = (
                    validation_reason
                )

        # =================================================
        # POST ANALYSIS
        # =================================================

        (
            candidate_analysis,
            candidate_violations
        ) = analyze_voice_candidate(

            history=(
                channel_recent_evilnae_messages
            ),

            draft=(
                draft
            ),

            candidate=(
                candidate
            )
        )

        candidate_score = (
            coherence_violation_score(
                candidate_violations
            )
        )

        # =================================================
        # DON'T MAKE IT WORSE
        # =================================================

        if (
            candidate.strip()
            !=
            draft.strip()

            and

            candidate_score
            >
            draft_violation_score
        ):

            candidate = (
                draft
            )

            candidate_analysis = (
                coherence_analysis
            )

            candidate_violations = (
                draft_violations
            )

            candidate_score = (
                draft_violation_score
            )

            reason = (
                "rewrite_worsened_coherence"
            )

        # =================================================
        # FORCED REPAIR CHECK
        # =================================================

        needs_repair = (
            forced_repair_required(

                deterministic_pressure=(
                    deterministic_pressure
                ),

                draft=(
                    draft
                ),

                candidate=(
                    candidate
                ),

                pre_score=(
                    draft_violation_score
                ),

                post_score=(
                    candidate_score
                ),

                post_violations=(
                    candidate_violations
                )
            )
        )

        repair_attempted = False
        repair_succeeded = False
        repair_attempt_count = 0

        # =================================================
        # FOCUSED REPAIR
        # =================================================

        if needs_repair:

            repair_attempted = (
                True
            )

            repair_result = (
                await attempt_focused_repair(

                    user_message=(
                        user_message
                    ),

                    draft=(
                        draft
                    ),

                    allow_question=(
                        allow_question
                    ),

                    channel_recent_evilnae_messages=(
                        channel_recent_evilnae_messages
                    ),

                    coherence_analysis=(
                        coherence_analysis
                    )
                )
            )

            repair_attempt_count = (
                repair_result[
                    "attempts"
                ]
            )

            if repair_result[
                "success"
            ]:

                repair_succeeded = (
                    True
                )

                candidate = (
                    repair_result[
                        "candidate"
                    ]
                )

                candidate_analysis = (
                    repair_result[
                        "analysis"
                    ]
                )

                candidate_violations = (
                    repair_result[
                        "violations"
                    ]
                )

                candidate_score = (
                    repair_result[
                        "score"
                    ]
                )

                reason = (
                    "focused_repair:"
                    +
                    repair_result[
                        "reason"
                    ]
                )

            else:

                candidate = (
                    draft
                )

                candidate_analysis = (
                    coherence_analysis
                )

                candidate_violations = (
                    draft_violations
                )

                candidate_score = (
                    draft_violation_score
                )

                reason = (
                    "forced_rewrite_failed:"
                    +
                    repair_result[
                        "reason"
                    ]
                )

        # =================================================
        # DIAGNOSTICS
        # =================================================

        if (
            parsed[
                "context_coherence"
            ]
            <
            LOCAL_VOICE_CONTEXT_COHERENCE_THRESHOLD
        ):

            if not reason:
                reason = (
                    "low_context_coherence"
                )

        if (
            parsed[
                "character_drift"
            ]
            >= 0.70

            or

            parsed[
                "theme_borrowing"
            ]
            >= 0.70
        ):

            if not reason:
                reason = (
                    "character_drift_detected"
                )

        # =================================================
        # FINAL
        # =================================================

        rewritten = (

            candidate.strip()

            !=

            draft.strip()
        )

        duration = (
            time.perf_counter()
            -
            total_start
        )

        print(
            "[LOCAL VOICE] "
            f"v={LOCAL_VOICE_VERSION} "
            f"model={LOCAL_VOICE_MODEL} "
            f"duration={duration:.2f}s "
            f"rewrite={rewritten} "
            f"forced={deterministic_pressure} "
            f"repair_attempted="
            f"{repair_attempted} "
            f"repair_success="
            f"{repair_succeeded} "
            f"repair_attempts="
            f"{repair_attempt_count} "
            f"bot="
            f"{parsed['bot_likeness']:.2f} "
            f"repeat="
            f"{parsed['repetition']:.2f} "
            f"persona="
            f"{parsed['persona_cliche']:.2f} "
            f"assistant="
            f"{parsed['assistant_structure']:.2f} "
            f"concept="
            f"{parsed['concept_repetition']:.2f} "
            f"emoji="
            f"{parsed['emoji_repetition']:.2f} "
            f"match="
            f"{parsed['evilnae_match']:.2f} "
            f"context="
            f"{parsed['context_coherence']:.2f} "
            f"drift="
            f"{parsed['character_drift']:.2f} "
            f"borrow="
            f"{parsed['theme_borrowing']:.2f} "
            f"meaning="
            f"{parsed['meaning_preserved']:.2f} "
            f"new_facts="
            f"{parsed['new_facts']} "
            f"pre_score="
            f"{draft_violation_score} "
            f"post_score="
            f"{candidate_score} "
            f"post_violations="
            f"{candidate_violations} "
            f"reason={reason!r}"
        )

        return LocalVoiceResult(

            output_text=(
                candidate
            ),

            used=True,

            rewritten=(
                rewritten
            ),

            bot_likeness=(
                parsed[
                    "bot_likeness"
                ]
            ),

            repetition=(
                parsed[
                    "repetition"
                ]
            ),

            evilnae_match=(
                parsed[
                    "evilnae_match"
                ]
            ),

            meaning_preserved=(
                parsed[
                    "meaning_preserved"
                ]
            ),

            new_facts=(
                parsed[
                    "new_facts"
                ]
            ),

            reason=(
                reason
            ),

            duration=(
                duration
            ),

            persona_cliche=(
                parsed[
                    "persona_cliche"
                ]
            ),

            assistant_structure=(
                parsed[
                    "assistant_structure"
                ]
            ),

            concept_repetition=(
                parsed[
                    "concept_repetition"
                ]
            ),

            emoji_repetition=(
                parsed[
                    "emoji_repetition"
                ]
            ),

            context_coherence=(
                parsed[
                    "context_coherence"
                ]
            ),

            unnecessary_compliance=(
                parsed[
                    "unnecessary_compliance"
                ]
            ),

            character_drift=(
                parsed[
                    "character_drift"
                ]
            ),

            theme_borrowing=(
                parsed[
                    "theme_borrowing"
                ]
            ),

            deterministic_violations=(
                candidate_violations
            ),

            forced_rewrite=(
                deterministic_pressure
            ),

            repair_attempted=(
                repair_attempted
            ),

            repair_succeeded=(
                repair_succeeded
            ),

            repair_attempt_count=(
                repair_attempt_count
            ),

            pre_coherence_score=(
                draft_violation_score
            ),

            post_coherence_score=(
                candidate_score
            )
        )

    finally:

        _voice_semaphore.release()


# =========================================================
# DEBUG CONFIG
# =========================================================

def format_local_voice_debug():

    return (
        "[LOCAL VOICE CONFIG] "
        f"v={LOCAL_VOICE_VERSION} "
        f"enabled={LOCAL_VOICE_ENABLED} "
        f"model={LOCAL_VOICE_MODEL} "
        f"url={LOCAL_VOICE_URL} "
        f"timeout={LOCAL_VOICE_TIMEOUT}s "
        f"queue={LOCAL_VOICE_QUEUE_TIMEOUT}s "
        f"ctx={LOCAL_VOICE_NUM_CTX} "
        f"predict={LOCAL_VOICE_NUM_PREDICT} "
        f"repair_predict="
        f"{LOCAL_VOICE_REPAIR_NUM_PREDICT} "
        f"repair_attempts="
        f"{LOCAL_VOICE_REPAIR_MAX_ATTEMPTS} "
        f"meaning_min="
        f"{LOCAL_VOICE_MEANING_THRESHOLD:.2f}"
    )


# =========================================================
# DETERMINISTIC SELF TEST
# =========================================================

def _run_deterministic_self_test():

    history = [

        "hahaha bisschen Chaos muss sein 😈",

        "ohne Chaos wird es doch langweilig 😂",

        "das wird richtig wild 😏",

        "Chaos pur, was soll schon passieren 😈",

        "ja das klingt spannend 😂",

        "die mods brauchen auch ein bisschen Chaos 😏",
    ]

    bad_draft = (
        "Cool, das klingt spannend! "
        "Ich bin gespannt, was ihr alles "
        "testen werdet. "
        "Viel Erfolg! 😈"
    )

    bad_analysis = analyze_coherence(
        history,
        candidate=bad_draft
    )

    good_candidate = (
        "testet ruhig weiter, mal sehen was ihr findet."
    )

    (
        good_analysis,
        good_violations
    ) = analyze_voice_candidate(
        history=history,
        draft=bad_draft,
        candidate=good_candidate
    )

    bad_previous_candidate = (
        "bisschen wild, wie immer"
    )

    (
        bad_previous_analysis,
        bad_previous_violations
    ) = analyze_voice_candidate(
        history=history,
        draft=bad_draft,
        candidate=bad_previous_candidate
    )

    trivial_candidate = (
        "ok"
    )

    (
        trivial_analysis,
        trivial_violations
    ) = analyze_voice_candidate(
        history=history,
        draft=bad_draft,
        candidate=trivial_candidate
    )

    short_good_candidate = (
        "testet ruhig."
    )

    (
        short_good_analysis,
        short_good_violations
    ) = analyze_voice_candidate(
        history=history,
        draft=bad_draft,
        candidate=short_good_candidate
    )

    habit_candidate = (
        "testen, wie immer."
    )

    (
        habit_analysis,
        habit_violations
    ) = analyze_voice_candidate(
        history=history,
        draft=bad_draft,
        candidate=habit_candidate
    )

    bad_score = (
        coherence_violation_score(
            bad_analysis
            .candidate_violations
        )
    )

    good_score = (
        coherence_violation_score(
            good_violations
        )
    )

    tests = [

        (
            "deterministic rewrite pressure",

            deterministic_rewrite_needed(
                bad_analysis
            )
        ),

        (
            "bad draft has violations",

            bool(
                bad_analysis
                .candidate_violations
            )
        ),

        (
            "good candidate scores lower",

            good_score
            <
            bad_score
        ),

        (
            "rhetorical question allowed",

            not is_likely_genuine_question(
                "ich?"
            )
        ),

        (
            "normal question detected",

            is_likely_genuine_question(
                "was machst du?"
            )
        ),

        (
            "new question detected",

            new_genuine_question_added(
                "passt schon.",
                "passt schon. was machst du?"
            )
        ),

        (
            "ok detected as trivial collapse",

            "trivial_collapse"
            in trivial_violations
        ),

        (
            "trivial collapse blocking",

            has_forced_blocking_violations(
                trivial_violations
            )
        ),

        (
            "test anchor extracted",

            "test"
            in extract_semantic_anchors(
                bad_draft
            )
        ),

        (
            "good rewrite preserves semantic anchor",

            semantic_anchor_preserved(
                bad_draft,
                good_candidate
            )
        ),

        (
            "short rewrite preserves semantic anchor",

            semantic_anchor_preserved(
                bad_draft,
                short_good_candidate
            )
        ),

        (
            "previous wild rewrite loses anchor",

            not semantic_anchor_preserved(
                bad_draft,
                bad_previous_candidate
            )
        ),

        (
            "previous wild rewrite flagged",

            "semantic_anchor_missing"
            in bad_previous_violations
        ),

        (
            "previous wild rewrite adds habit claim",

            "unsupported_habit_claim"
            in bad_previous_violations
        ),

        (
            "unsupported habit claim detected",

            introduces_unsupported_habit_claim(
                bad_draft,
                habit_candidate
            )
        ),

        (
            "habit claim is blocking",

            has_forced_blocking_violations(
                habit_violations
            )
        ),

        (
            "clean candidate has no blocking violations",

            not has_forced_blocking_violations(
                good_violations
            )
        ),

        (
            "good forced rewrite needs no repair",

            not forced_repair_required(

                deterministic_pressure=True,

                draft=bad_draft,

                candidate=good_candidate,

                pre_score=bad_score,

                post_score=good_score,

                post_violations=(
                    good_violations
                )
            )
        ),

        (
            "wild previous rewrite requires repair",

            forced_repair_required(

                deterministic_pressure=True,

                draft=bad_draft,

                candidate=bad_previous_candidate,

                pre_score=bad_score,

                post_score=(
                    coherence_violation_score(
                        bad_previous_violations
                    )
                ),

                post_violations=(
                    bad_previous_violations
                )
            )
        ),
    ]

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"LOCAL VOICE v"
        f"{LOCAL_VOICE_VERSION} "
        "DETERMINISTIC TEST"
    )
    print(
        "============================================"
    )
    print("")

    print(
        "DRAFT ANCHORS:"
    )

    print(
        extract_semantic_anchors(
            bad_draft
        )
    )

    print("")

    print(
        "OLD BAD REWRITE:"
    )

    print(
        bad_previous_candidate
    )

    print(
        bad_previous_violations
    )

    print("")

    print(
        "GOOD REWRITE:"
    )

    print(
        good_candidate
    )

    print(
        good_violations
    )

    print("")

    for (
        name,
        success
    ) in tests:

        if success:

            status = "PASS"
            passed += 1

        else:

            status = "FAIL"

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

    return (
        passed
        ==
        len(tests)
    )


# =========================================================
# LIVE TEST
# =========================================================

async def _run_live_test():

    print("")

    print(
        format_local_voice_debug()
    )

    available = (
        await is_local_voice_available()
    )

    print(
        "[LOCAL VOICE TEST] "
        f"available={available}"
    )

    if not available:
        return

    recent = [

        "hahaha bisschen Chaos muss sein 😈",

        "ohne Chaos wird es doch langweilig 😂",

        "das wird wild 😏",

        "Chaos pur 😈",

        "ja das klingt spannend 😂",

        "die mods brauchen etwas Chaos 😏",
    ]

    original = (
        "Cool, das klingt spannend! "
        "Ich bin gespannt, was ihr alles "
        "testen werdet. "
        "Viel Erfolg! 😈"
    )

    result = await humanize_evilnae_response(

        user_message=(
            "wir testen dich später "
            "noch ein bisschen"
        ),

        draft=(
            original
        ),

        conversation_mode=(
            "direct"
        ),

        response_goal=(
            "locker auf die Aussage reagieren"
        ),

        allow_question=False,

        inner_state_guidance=(
            "neutral; sozial zugänglich"
        ),

        recent_evilnae_messages=(
            recent
        ),

        channel_recent_evilnae_messages=(
            recent
        )
    )

    print("")

    print(
        "ORIGINAL:"
    )

    print(
        original
    )

    print("")

    print(
        "ANCHORS:"
    )

    print(
        extract_semantic_anchors(
            original
        )
    )

    print("")

    print(
        "VOICE:"
    )

    print(
        result.output_text
    )

    print("")

    print(
        "PIPELINE:"
    )

    print(
        f"forced="
        f"{result.forced_rewrite} "
        f"repair_attempted="
        f"{result.repair_attempted} "
        f"repair_success="
        f"{result.repair_succeeded} "
        f"repair_attempts="
        f"{result.repair_attempt_count} "
        f"pre="
        f"{result.pre_coherence_score} "
        f"post="
        f"{result.post_coherence_score} "
        f"violations="
        f"{result.deterministic_violations}"
    )

    print("")

    print(
        "FINAL:"
    )

    print(
        result
    )


# =========================================================
# ENTRYPOINT
# =========================================================

async def _test():

    _run_deterministic_self_test()

    await _run_live_test()


if __name__ == "__main__":

    asyncio.run(
        _test()
    )
import json
import os
import re
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional


# =========================================================
# VERSION
# =========================================================

VOICE_MEMORY_VERSION = "1.0"


# =========================================================
# STORAGE
# =========================================================

VOICE_MEMORY_FILE = (
    "voice_memory.json"
)

VOICE_MEMORY_TEMP_FILE = (
    VOICE_MEMORY_FILE
    + ".tmp"
)

MAX_VOICE_EXAMPLES = 400


# =========================================================
# LOCK
# =========================================================

voice_memory_lock = (
    threading.RLock()
)


# =========================================================
# DATA MODEL
# =========================================================

@dataclass
class VoiceExample:

    timestamp: float

    username: str

    user_message: str

    evilnae_response: str

    rating: str

    reason: str

    feedback_text: str = ""

    seed: bool = False


# =========================================================
# SEED GOOD EXAMPLES
#
# Diese Beispiele definieren NICHT,
# was Evilnae immer sagen soll.
#
# Sie zeigen nur:
#
# - Discord-Rhythmus
# - kein Support-Bot
# - keine unnötige Zusammenfassung
# - eigene Perspektive
# - unperfekte menschliche Sprache
# =========================================================

SEED_GOOD_EXAMPLES = [

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "wie läufts bei dir heute?"
        ),
        evilnae_response=(
            "joa geht eigentlich, "
            "mein hirn läuft nur noch "
            "so halb auf voller leistung"
        ),
        rating="good",
        reason="natural_discord_voice",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "ich muss morgen wieder früh raus"
        ),
        evilnae_response=(
            "mein beileid an dein "
            "zukünftiges ich 💀"
        ),
        rating="good",
        reason="natural_short_reaction",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "ich hab schon wieder hunger"
        ),
        evilnae_response=(
            "same problem, warum verlangt "
            "dieser körper eigentlich "
            "mehrmals täglich essen"
        ),
        rating="good",
        reason="own_perspective",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "bist du heute müde?"
        ),
        evilnae_response=(
            "bisschen. heute ist irgendwie "
            "so ein 3%-akku-tag"
        ),
        rating="good",
        reason="casual_metaphor",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "hanae nervt mich heute"
        ),
        evilnae_response=(
            "skill issue, ich hab sie "
            "nicht erzogen"
        ),
        rating="good",
        reason="evilnae_personality",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "ich hab heute eigentlich "
            "gar nichts gemacht"
        ),
        evilnae_response=(
            "auch ne leistung irgendwie"
        ),
        rating="good",
        reason="dry_natural_reaction",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "ich bin gerade komplett lost"
        ),
        evilnae_response=(
            "ja okay willkommen im club"
        ),
        rating="good",
        reason="short_social_response",
        seed=True
    ),
]


# =========================================================
# SEED BAD EXAMPLES
#
# Diese Antworten zeigen typische
# Bot-/Support-Muster.
# =========================================================

SEED_BAD_EXAMPLES = [

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "ich muss später noch arbeiten"
        ),
        evilnae_response=(
            "Das klingt anstrengend! "
            "Ich hoffe, du hast trotzdem "
            "einen schönen Tag und kannst "
            "dich später entspannen."
        ),
        rating="bad",
        reason="generic_assistant_language",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "wir testen dich später ein bisschen"
        ),
        evilnae_response=(
            "Cool, das klingt spannend! "
            "Ich bin gespannt, was ihr "
            "alles testen werdet. Viel Erfolg!"
        ),
        rating="bad",
        reason="support_bot_structure",
        seed=True
    ),

    VoiceExample(
        timestamp=0.0,
        username="seed",
        user_message=(
            "wenn dir was komisch vorkommt "
            "kannst du bescheid sagen"
        ),
        evilnae_response=(
            "Alles klar, ich halte die Augen offen! "
            "Wenn etwas komisch ist, "
            "sage ich Bescheid."
        ),
        rating="bad",
        reason="paraphrases_user",
        seed=True
    ),
]


# =========================================================
# DEFAULT STATE
# =========================================================

def create_default_state():

    return {

        "version":
            VOICE_MEMORY_VERSION,

        "examples":
            [
                asdict(
                    example
                )
                for example
                in (
                    SEED_GOOD_EXAMPLES
                    + SEED_BAD_EXAMPLES
                )
            ]
    }


# =========================================================
# LOAD
# =========================================================

def load_voice_memory():

    if not os.path.exists(
        VOICE_MEMORY_FILE
    ):

        return create_default_state()

    try:

        with open(
            VOICE_MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict
        ):

            return create_default_state()

        examples = (
            data.get(
                "examples",
                []
            )
        )

        if not isinstance(
            examples,
            list
        ):

            examples = []

        # -------------------------------------------------
        # Seeds sicherstellen
        # -------------------------------------------------

        existing_seed_responses = {

            str(
                item.get(
                    "evilnae_response",
                    ""
                )
            ).strip().lower()

            for item
            in examples

            if isinstance(
                item,
                dict
            )
        }

        for seed in (
            SEED_GOOD_EXAMPLES
            + SEED_BAD_EXAMPLES
        ):

            if (
                seed.evilnae_response
                .strip()
                .lower()
                not in existing_seed_responses
            ):

                examples.append(
                    asdict(
                        seed
                    )
                )

        return {

            "version":
                VOICE_MEMORY_VERSION,

            "examples":
                examples[
                    -MAX_VOICE_EXAMPLES:
                ]
        }

    except Exception as error:

        print(
            "[VOICE MEMORY LOAD ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return create_default_state()


# =========================================================
# STATE
# =========================================================

voice_memory_state = (
    load_voice_memory()
)


# =========================================================
# SAVE
# =========================================================

def save_voice_memory():

    with voice_memory_lock:

        try:

            with open(
                VOICE_MEMORY_TEMP_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    voice_memory_state,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

                file.flush()

                os.fsync(
                    file.fileno()
                )

            os.replace(
                VOICE_MEMORY_TEMP_FILE,
                VOICE_MEMORY_FILE
            )

        except Exception as error:

            print(
                "[VOICE MEMORY SAVE ERROR] "
                f"{type(error).__name__}: "
                f"{error}"
            )

            try:

                if os.path.exists(
                    VOICE_MEMORY_TEMP_FILE
                ):

                    os.remove(
                        VOICE_MEMORY_TEMP_FILE
                    )

            except OSError:

                pass


# =========================================================
# TOKENIZE
# =========================================================

def tokenize(
    text
):

    return set(
        re.findall(
            r"[a-z0-9äöüß]+",
            (
                text
                or ""
            ).lower()
        )
    )


# =========================================================
# SIMILARITY
#
# Für v1 bewusst lokal und billig.
#
# Später können wir Embeddings einsetzen.
# =========================================================

def text_similarity(
    text_a,
    text_b
):

    tokens_a = (
        tokenize(
            text_a
        )
    )

    tokens_b = (
        tokenize(
            text_b
        )
    )

    if (
        not tokens_a
        or
        not tokens_b
    ):

        return 0.0

    intersection = (
        len(
            tokens_a
            & tokens_b
        )
    )

    union = (
        len(
            tokens_a
            | tokens_b
        )
    )

    if union == 0:

        return 0.0

    return (
        intersection
        / union
    )


# =========================================================
# STYLE FEEDBACK PATTERNS
#
# Ganz wichtig:
#
# "Das klingt super!"
#
# soll NICHT automatisch
# als Voice-Training gelten.
#
# Wir speichern nur Feedback,
# das sich klar auf ihre Art zu reden bezieht.
# =========================================================

GOOD_VOICE_FEEDBACK_PATTERNS = [

    (
        r"\bklingt menschlich\b",
        "human_like"
    ),

    (
        r"\bwar menschlich\b",
        "human_like"
    ),

    (
        r"\bso klingt es menschlich\b",
        "human_like"
    ),

    (
        r"\bso klingt das menschlich\b",
        "human_like"
    ),

    (
        r"\bklingt natürlich\b",
        "natural"
    ),

    (
        r"\bklingt normal\b",
        "natural"
    ),

    (
        r"\bgenau so sollst du\b",
        "desired_voice"
    ),

    (
        r"\bgenau so reden\b",
        "desired_voice"
    ),

    (
        r"\bgenau so schreiben\b",
        "desired_voice"
    ),

    (
        r"\bso ist viel besser\b",
        "improved_voice"
    ),

    (
        r"\bviel menschlicher\b",
        "human_like"
    ),

    (
        r"\bdas war viel besser\b",
        "improved_voice"
    ),

    (
        r"\bso mag ich deine antworten\b",
        "desired_voice"
    ),
]


BAD_VOICE_FEEDBACK_PATTERNS = [

    (
        r"\bwie ein bot\b",
        "bot_like"
    ),

    (
        r"\bklingt wie ein bot\b",
        "bot_like"
    ),

    (
        r"\bbotartig\b",
        "bot_like"
    ),

    (
        r"\bzu bot\b",
        "bot_like"
    ),

    (
        r"\bwie chatgpt\b",
        "bot_like"
    ),

    (
        r"\bklingt nach chatgpt\b",
        "bot_like"
    ),

    (
        r"\bwie kundensupport\b",
        "support_bot"
    ),

    (
        r"\bwie kundenservice\b",
        "support_bot"
    ),

    (
        r"\bsupport bot\b",
        "support_bot"
    ),

    (
        r"\bklingt künstlich\b",
        "artificial"
    ),

    (
        r"\bunnatürlich\b",
        "artificial"
    ),

    (
        r"\bnicht menschlich\b",
        "artificial"
    ),

    (
        r"\brobotisch\b",
        "artificial"
    ),

    (
        r"\bzu förmlich\b",
        "too_formal"
    ),

    (
        r"\bzu formell\b",
        "too_formal"
    ),

    (
        r"\bzu höflich\b",
        "too_polite"
    ),

    (
        r"\bzu nett\b",
        "too_polite"
    ),

    (
        r"\bzu glatt\b",
        "too_polished"
    ),

    (
        r"\bzu generisch\b",
        "generic"
    ),

    (
        r"\bdu wiederholst dich\b",
        "repetitive"
    ),

    (
        r"\bwiederholst du dich\b",
        "repetitive"
    ),

    (
        r"\bwiederholend\b",
        "repetitive"
    ),

    (
        r"\bsehr wiederholend\b",
        "repetitive"
    ),

    (
        r"\bimmer das gleiche\b",
        "repetitive"
    ),
]


# =========================================================
# DETECT FEEDBACK
# =========================================================

def detect_voice_feedback(
    feedback_text
) -> Optional[tuple[str, str]]:

    text = (
        feedback_text
        or ""
    ).strip().lower()

    if not text:

        return None

    for (
        pattern,
        reason
    ) in GOOD_VOICE_FEEDBACK_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            return (
                "good",
                reason
            )

    for (
        pattern,
        reason
    ) in BAD_VOICE_FEEDBACK_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            return (
                "bad",
                reason
            )

    return None


# =========================================================
# ADD EXAMPLE
# =========================================================

def add_voice_example(
    *,
    username,
    user_message,
    evilnae_response,
    rating,
    reason,
    feedback_text=""
):

    if rating not in {
        "good",
        "bad"
    }:

        return False

    user_message = (
        user_message
        or ""
    ).strip()

    evilnae_response = (
        evilnae_response
        or ""
    ).strip()

    if not evilnae_response:

        return False

    with voice_memory_lock:

        examples = (
            voice_memory_state[
                "examples"
            ]
        )

        # -------------------------------------------------
        # Gleiche Antwort nicht ständig doppelt speichern.
        # -------------------------------------------------

        normalized_response = (
            evilnae_response.lower()
        )

        for existing in reversed(
            examples[-100:]
        ):

            if not isinstance(
                existing,
                dict
            ):

                continue

            if (
                str(
                    existing.get(
                        "evilnae_response",
                        ""
                    )
                )
                .strip()
                .lower()
                ==
                normalized_response
            ):

                existing[
                    "rating"
                ] = rating

                existing[
                    "reason"
                ] = reason

                existing[
                    "feedback_text"
                ] = (
                    feedback_text
                    or ""
                )[:500]

                existing[
                    "timestamp"
                ] = time.time()

                save_voice_memory()

                print(
                    "[VOICE MEMORY UPDATED] "
                    f"rating={rating} "
                    f"reason={reason}"
                )

                return True

        example = VoiceExample(

            timestamp=time.time(),

            username=(
                username
                or "unknown"
            ),

            user_message=(
                user_message[:1000]
            ),

            evilnae_response=(
                evilnae_response[:1000]
            ),

            rating=rating,

            reason=reason,

            feedback_text=(
                feedback_text
                or ""
            )[:500],

            seed=False
        )

        examples.append(
            asdict(
                example
            )
        )

        # Seeds + neueste echte Beispiele behalten.

        if (
            len(examples)
            > MAX_VOICE_EXAMPLES
        ):

            seeds = [
                item
                for item
                in examples

                if item.get(
                    "seed",
                    False
                )
            ]

            non_seeds = [
                item
                for item
                in examples

                if not item.get(
                    "seed",
                    False
                )
            ]

            remaining_slots = max(
                0,
                MAX_VOICE_EXAMPLES
                - len(
                    seeds
                )
            )

            voice_memory_state[
                "examples"
            ] = (
                seeds
                + non_seeds[
                    -remaining_slots:
                ]
            )

        save_voice_memory()

        print(
            "[VOICE MEMORY ADDED] "
            f"rating={rating} "
            f"reason={reason} "
            f"user={username}"
        )

        return True


# =========================================================
# REGISTER FEEDBACK
# =========================================================

def register_voice_feedback(
    *,
    username,
    user_message,
    evilnae_response,
    feedback_text
):

    detected = (
        detect_voice_feedback(
            feedback_text
        )
    )

    if not detected:

        return False

    (
        rating,
        reason
    ) = detected

    return add_voice_example(

        username=username,

        user_message=user_message,

        evilnae_response=evilnae_response,

        rating=rating,

        reason=reason,

        feedback_text=feedback_text
    )


# =========================================================
# GET RELEVANT EXAMPLES
# =========================================================

def get_relevant_voice_examples(
    current_user_message,
    *,
    good_limit=4,
    bad_limit=3
):

    with voice_memory_lock:

        examples = list(
            voice_memory_state[
                "examples"
            ]
        )

    scored_good = []

    scored_bad = []

    now = (
        time.time()
    )

    for item in examples:

        if not isinstance(
            item,
            dict
        ):

            continue

        similarity = (
            text_similarity(

                current_user_message,

                item.get(
                    "user_message",
                    ""
                )
            )
        )

        timestamp = float(
            item.get(
                "timestamp",
                0.0
            )
            or 0.0
        )

        seed = bool(
            item.get(
                "seed",
                False
            )
        )

        if seed:

            recency_bonus = (
                0.03
            )

        else:

            age_days = max(
                0.0,
                (
                    now
                    - timestamp
                )
                / 86400
            )

            recency_bonus = max(
                0.0,
                0.15
                - (
                    age_days
                    * 0.005
                )
            )

        score = (
            similarity
            + recency_bonus
        )

        if (
            item.get(
                "rating"
            )
            == "good"
        ):

            scored_good.append(
                (
                    score,
                    item
                )
            )

        elif (
            item.get(
                "rating"
            )
            == "bad"
        ):

            scored_bad.append(
                (
                    score,
                    item
                )
            )

    scored_good.sort(
        key=lambda value:
            value[0],
        reverse=True
    )

    scored_bad.sort(
        key=lambda value:
            value[0],
        reverse=True
    )

    good = [
        item
        for _score, item
        in scored_good[
            :good_limit
        ]
    ]

    bad = [
        item
        for _score, item
        in scored_bad[
            :bad_limit
        ]
    ]

    return (
        good,
        bad
    )


# =========================================================
# FORMAT EXAMPLES
# =========================================================

def format_voice_examples(
    examples
):

    if not examples:

        return "Keine."

    blocks = []

    for item in examples:

        blocks.append(
            (
                "User:\n"
                f"{item.get('user_message', '')}\n\n"
                "Evilnae:\n"
                f"{item.get('evilnae_response', '')}\n\n"
                "Warum gespeichert:\n"
                f"{item.get('reason', 'unknown')}"
            )
        )

    return (
        "\n\n---\n\n".join(
            blocks
        )
    )


# =========================================================
# DEBUG
# =========================================================

def get_voice_memory_counts():

    with voice_memory_lock:

        examples = (
            voice_memory_state[
                "examples"
            ]
        )

        good = sum(
            1
            for item
            in examples
            if item.get(
                "rating"
            )
            == "good"
        )

        bad = sum(
            1
            for item
            in examples
            if item.get(
                "rating"
            )
            == "bad"
        )

        learned = sum(
            1
            for item
            in examples
            if not item.get(
                "seed",
                False
            )
        )

    return (
        good,
        bad,
        learned
    )


def format_voice_memory_debug():

    (
        good,
        bad,
        learned
    ) = (
        get_voice_memory_counts()
    )

    return (
        "[VOICE MEMORY] "
        f"v={VOICE_MEMORY_VERSION} "
        f"good={good} "
        f"bad={bad} "
        f"learned={learned}"
    )


# =========================================================
# INITIAL SAVE
# =========================================================

if not os.path.exists(
    VOICE_MEMORY_FILE
):

    save_voice_memory()
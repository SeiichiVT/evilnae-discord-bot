import json
import os
import time
import random
from dataclasses import dataclass, asdict


# =========================================================
# VERSION
# =========================================================

INITIATIVE_VERSION = "1.0"


# =========================================================
# STORAGE
# =========================================================

STATE_FILE = "initiative_state.json"


# =========================================================
# CONFIG
# =========================================================

MIN_SECONDS_BETWEEN_INITIATIVES = (
    45 * 60
)

MAX_INITIATIVES_PER_DAY = 8

MIN_CHANNEL_SILENCE_SECONDS = (
    8 * 60
)

MAX_CHANNEL_SILENCE_SECONDS = (
    3 * 60 * 60
)

ACTIVE_HOUR_START = 10

ACTIVE_HOUR_END = 22


# =========================================================
# STATE
# =========================================================

@dataclass
class InitiativeState:

    date: str = ""

    daily_count: int = 0

    last_initiative_at: float = 0.0

    last_channel_message_at: float = 0.0

    last_user_message_at: float = 0.0


# =========================================================
# DEFAULT STATE
# =========================================================

def create_default_state():

    return InitiativeState()


# =========================================================
# LOAD
# =========================================================

def load_state():

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

        return InitiativeState(

            date=str(
                data.get(
                    "date",
                    ""
                )
            ),

            daily_count=int(
                data.get(
                    "daily_count",
                    0
                )
            ),

            last_initiative_at=float(
                data.get(
                    "last_initiative_at",
                    0.0
                )
            ),

            last_channel_message_at=float(
                data.get(
                    "last_channel_message_at",
                    0.0
                )
            ),

            last_user_message_at=float(
                data.get(
                    "last_user_message_at",
                    0.0
                )
            )
        )

    except Exception as error:

        print(
            "[INITIATIVE LOAD ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return create_default_state()


initiative_state = (
    load_state()
)


# =========================================================
# SAVE
# =========================================================

def save_state():

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                asdict(
                    initiative_state
                ),
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print(
            "[INITIATIVE SAVE ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )


# =========================================================
# DATE HELPERS
# =========================================================

def current_date_key():

    return (
        time.strftime(
            "%Y-%m-%d"
        )
    )


def refresh_daily_state():

    today = (
        current_date_key()
    )

    if (
        initiative_state.date
        == today
    ):

        return

    initiative_state.date = today

    initiative_state.daily_count = 0

    save_state()


# =========================================================
# CHANNEL ACTIVITY
# =========================================================

def register_channel_message(
    *,
    is_bot=False
):

    now = time.time()

    initiative_state.last_channel_message_at = now

    if not is_bot:

        initiative_state.last_user_message_at = now

    save_state()


# =========================================================
# TIME HELPERS
# =========================================================

def seconds_since_last_initiative():

    if (
        initiative_state.last_initiative_at
        <= 0
    ):

        return None

    return (
        time.time()
        - initiative_state.last_initiative_at
    )


def seconds_since_last_channel_message():

    if (
        initiative_state.last_channel_message_at
        <= 0
    ):

        return None

    return (
        time.time()
        - initiative_state.last_channel_message_at
    )


def seconds_since_last_user_message():

    if (
        initiative_state.last_user_message_at
        <= 0
    ):

        return None

    return (
        time.time()
        - initiative_state.last_user_message_at
    )


# =========================================================
# ACTIVE HOURS
# =========================================================

def is_inside_active_hours():

    current_hour = (
        time.localtime().tm_hour
    )

    return (
        ACTIVE_HOUR_START
        <= current_hour
        < ACTIVE_HOUR_END
    )


# =========================================================
# BASE ELIGIBILITY
# =========================================================

def can_initiate():

    refresh_daily_state()

    if not (
        is_inside_active_hours()
    ):

        return (
            False,
            "outside_active_hours"
        )

    if (
        initiative_state.daily_count
        >= MAX_INITIATIVES_PER_DAY
    ):

        return (
            False,
            "daily_limit"
        )

    since_last = (
        seconds_since_last_initiative()
    )

    if (
        since_last is not None
        and
        since_last
        <
        MIN_SECONDS_BETWEEN_INITIATIVES
    ):

        return (
            False,
            "cooldown"
        )

    return (
        True,
        "allowed"
    )


# =========================================================
# INNER STATE SCORE
# =========================================================

def calculate_initiative_score(
    inner_state
):

    score = 0.0

    # -----------------------------------------------------
    # CURIOSITY
    # -----------------------------------------------------

    score += (
        inner_state.curiosity
        * 0.30
    )

    # -----------------------------------------------------
    # BOREDOM
    # -----------------------------------------------------

    score += (
        inner_state.boredom
        * 0.30
    )

    # -----------------------------------------------------
    # SOCIAL ENERGY
    # -----------------------------------------------------

    score += (
        inner_state.social_energy
        * 0.20
    )

    # -----------------------------------------------------
    # CHAOS DRIVE
    # -----------------------------------------------------

    score += (
        inner_state.chaos_drive
        * 0.15
    )

    # -----------------------------------------------------
    # IRRITATION REDUCES INITIATIVE
    # -----------------------------------------------------

    score -= (
        inner_state.irritation
        * 0.20
    )

    # -----------------------------------------------------
    # LOW ENERGY REDUCES INITIATIVE
    # -----------------------------------------------------

    if (
        inner_state.energy
        < 0.35
    ):

        score -= 0.15

    return max(
        0.0,
        min(
            1.0,
            score
        )
    )


# =========================================================
# CHANNEL SILENCE ELIGIBILITY
# =========================================================

def channel_silence_is_suitable():

    since_user = (
        seconds_since_last_user_message()
    )

    if since_user is None:

        return (
            False,
            "no_user_activity"
        )

    if (
        since_user
        <
        MIN_CHANNEL_SILENCE_SECONDS
    ):

        return (
            False,
            "channel_too_active"
        )

    if (
        since_user
        >
        MAX_CHANNEL_SILENCE_SECONDS
    ):

        return (
            False,
            "channel_too_dead"
        )

    return (
        True,
        "suitable"
    )


# =========================================================
# SHOULD INITIATE?
# =========================================================

def should_initiate(
    inner_state
):

    allowed, reason = (
        can_initiate()
    )

    if not allowed:

        return (
            False,
            reason,
            0.0
        )

    silence_ok, silence_reason = (
        channel_silence_is_suitable()
    )

    if not silence_ok:

        return (
            False,
            silence_reason,
            0.0
        )

    score = (
        calculate_initiative_score(
            inner_state
        )
    )

    # -----------------------------------------------------
    # THRESHOLD
    # -----------------------------------------------------

    if score < 0.45:

        return (
            False,
            "score_too_low",
            score
        )

    # -----------------------------------------------------
    # STOCHASTIC GATE
    #
    # Selbst bei geeignetem Zustand
    # soll sie NICHT immer schreiben.
    # -----------------------------------------------------

    probability = (
        min(
            0.75,
            max(
                0.15,
                score
            )
        )
    )

    roll = (
        random.random()
    )

    if roll > probability:

        return (
            False,
            "random_gate",
            score
        )

    return (
        True,
        "allowed",
        score
    )


# =========================================================
# REGISTER INITIATIVE
# =========================================================

def register_initiative():

    refresh_daily_state()

    initiative_state.daily_count += 1

    initiative_state.last_initiative_at = (
        time.time()
    )

    save_state()


# =========================================================
# INITIATIVE TYPE
# =========================================================

def choose_initiative_type(
    inner_state
):

    candidates = []

    # -----------------------------------------------------
    # BORED
    # -----------------------------------------------------

    if (
        inner_state.boredom
        >= 0.55
    ):

        candidates.extend([
            "bored_comment",
            "poke_channel",
        ])

    # -----------------------------------------------------
    # CURIOUS
    # -----------------------------------------------------

    if (
        inner_state.curiosity
        >= 0.60
    ):

        candidates.extend([
            "curious_comment",
            "ask_channel",
        ])

    # -----------------------------------------------------
    # CHAOTIC
    # -----------------------------------------------------

    if (
        inner_state.chaos_drive
        >= 0.60
    ):

        candidates.append(
            "chaotic_comment"
        )

    # -----------------------------------------------------
    # SOCIAL
    # -----------------------------------------------------

    if (
        inner_state.social_energy
        >= 0.65
    ):

        candidates.append(
            "social_pingless_comment"
        )

    if not candidates:

        candidates = [
            "neutral_comment"
        ]

    return random.choice(
        candidates
    )


# =========================================================
# FORMAT PROMPT
# =========================================================

def build_initiative_prompt(
    *,
    initiative_type,
    inner_state_guidance,
    channel_context,
    recent_evilnae_messages,
):

    if recent_evilnae_messages:

        recent_text = (
            "\n".join(
                f"- {message}"
                for message
                in recent_evilnae_messages
            )
        )

    else:

        recent_text = "Keine."

    type_guidance = {

        "bored_comment":
            """
Evilnae langweilt sich etwas.

Sie darf etwas Kurzes sagen,
das wie ein spontaner Gedanke wirkt.

Keine künstliche Frage erzwingen.
""",

        "poke_channel":
            """
Evilnae möchte die Stille
ein bisschen brechen.

Sie darf den Channel leicht anstupsen.

Nicht needy wirken.
Nicht betteln, dass jemand antwortet.
""",

        "curious_comment":
            """
Evilnae hat einen spontanen
neugierigen Gedanken.

Sie darf etwas aufgreifen,
das im vorherigen Gespräch hängen geblieben ist.
""",

        "ask_channel":
            """
Evilnae ist genuinely neugierig
und darf ausnahmsweise
eine natürliche Frage in den Raum werfen.
""",

        "chaotic_comment":
            """
Evilnae hat gerade
etwas mehr Gremlin-Energy.

Kurzer spontaner Kommentar erlaubt.

Nicht random nonsense.
""",

        "social_pingless_comment":
            """
Evilnae hat Social Energy
und möchte einfach etwas sagen.

Keine Person pingen.
Keine künstliche Begrüßung.
""",

        "neutral_comment":
            """
Evilnae hat einen kleinen
spontanen Impuls.

Kurzer natürlicher Discord-Kommentar.
"""
    }

    selected_guidance = (
        type_guidance.get(
            initiative_type,
            type_guidance[
                "neutral_comment"
            ]
        )
    )

    return f"""
Du formulierst eine spontane,
selbst initiierte Discord-Nachricht
von Evilnae.

Niemand hat Evilnae gerade direkt gefragt.

Die Nachricht soll wirken,
als hätte Evilnae selbst entschieden,
etwas zu sagen.


==================================================
INITIATIVE TYPE
==================================================

{initiative_type}

{selected_guidance}


==================================================
INNER STATE
==================================================

{inner_state_guidance}


==================================================
RECENT CHANNEL CONTEXT
==================================================

{channel_context}


==================================================
EVILNAES LETZTE EIGENE NACHRICHTEN
==================================================

{recent_text}


==================================================
REGELN
==================================================

- maximal 1 bis 2 kurze Sätze
- keine Bot-Sprache
- keine Erklärung, warum sie schreibt
- nicht sagen "mir ist langweilig",
  außer es passt wirklich natürlich
- keine Person pingen
- keine @mentions
- keine künstliche Service-Frage
- nicht versuchen,
  unbedingt Aufmerksamkeit zu bekommen
- kein "fair"
- nicht dieselbe Phrase wiederholen
- darf einfach ein spontaner Gedanke sein
- darf leicht frech sein
- darf warm sein
- darf weird sein
- darf schweigen, indem du exakt
  NO_INITIATIVE schreibst,
  wenn nichts Natürliches passt

Schreibe NUR die Discord-Nachricht
oder exakt:

NO_INITIATIVE
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_initiative_debug(
    *,
    allowed,
    reason,
    score,
    initiative_type=None
):

    refresh_daily_state()

    return (
        "[INITIATIVE] "
        f"v={INITIATIVE_VERSION} "
        f"allowed={allowed} "
        f"reason={reason} "
        f"score={score:.2f} "
        f"type={initiative_type} "
        f"daily="
        f"{initiative_state.daily_count}/"
        f"{MAX_INITIATIVES_PER_DAY}"
    )
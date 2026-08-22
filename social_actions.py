import json
import os
import time
from datetime import datetime


# =========================================================
# VERSION
# =========================================================

SOCIAL_ACTIONS_VERSION = "1.1"


# =========================================================
# CONFIG
# =========================================================

MAX_AUTONOMOUS_PINGS_PER_DAY = 5

MIN_SECONDS_BETWEEN_AUTONOMOUS_PINGS = (
    2 * 60 * 60
)

STATE_FILE = (
    "social_actions_state.json"
)


# =========================================================
# DEFAULT STATE
# =========================================================

def default_state():

    return {
        "date": "",
        "daily_ping_count": 0,
        "last_global_ping": None,
        "last_target_pings": {}
    }


# =========================================================
# LOAD STATE
# =========================================================

def load_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return default_state()

    try:

        with open(
            STATE_FILE,
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

            return default_state()

        state = default_state()

        state.update(
            data
        )

        return state

    except Exception as error:

        print(
            "[SOCIAL STATE ERROR] "
            f"load="
            f"{type(error).__name__}: "
            f"{error}"
        )

        return default_state()


# =========================================================
# SAVE STATE
# =========================================================

def save_state():

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                social_state,
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print(
            "[SOCIAL STATE ERROR] "
            f"save="
            f"{type(error).__name__}: "
            f"{error}"
        )


# =========================================================
# RUNTIME STATE
# =========================================================

social_state = (
    load_state()
)


# =========================================================
# CURRENT DATE
# =========================================================

def current_date_key():

    return (
        datetime.now()
        .astimezone()
        .strftime(
            "%Y-%m-%d"
        )
    )


# =========================================================
# RESET DAILY COUNTER
# =========================================================

def refresh_daily_state():

    today = (
        current_date_key()
    )

    stored_date = (
        social_state.get(
            "date",
            ""
        )
    )

    if stored_date == today:

        return

    social_state[
        "date"
    ] = today

    social_state[
        "daily_ping_count"
    ] = 0

    # Letzte Ping-Zeit behalten wir.
    #
    # Dadurch kann ein Neustart / Tageswechsel
    # den 2h-Cooldown nicht umgehen.

    save_state()


# =========================================================
# DAILY COUNT
# =========================================================

def get_daily_ping_count():

    refresh_daily_state()

    return int(
        social_state.get(
            "daily_ping_count",
            0
        )
    )


# =========================================================
# GLOBAL LAST PING
# =========================================================

def seconds_since_last_global_ping():

    last_ping = (
        social_state.get(
            "last_global_ping"
        )
    )

    if last_ping is None:

        return None

    try:

        return (
            time.time()
            - float(
                last_ping
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return None


# =========================================================
# TARGET LAST PING
# =========================================================

def seconds_since_target_ping(
    target_user_id
):

    target_user_id = str(
        target_user_id
    )

    target_data = (
        social_state.get(
            "last_target_pings",
            {}
        )
    )

    last_ping = (
        target_data.get(
            target_user_id
        )
    )

    if last_ping is None:

        return None

    try:

        return (
            time.time()
            - float(
                last_ping
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return None


# =========================================================
# CAN AUTONOMOUSLY PING?
# =========================================================

def can_autonomously_ping(
    target_user_id
):

    refresh_daily_state()

    target_user_id = str(
        target_user_id
    )

    # -----------------------------------------------------
    # DAILY GLOBAL LIMIT
    # -----------------------------------------------------

    daily_count = (
        get_daily_ping_count()
    )

    if (
        daily_count
        >= MAX_AUTONOMOUS_PINGS_PER_DAY
    ):

        return (
            False,
            "daily_limit"
        )

    # -----------------------------------------------------
    # GLOBAL 2H COOLDOWN
    #
    # Evilnae darf insgesamt nur etwa
    # alle 2 Stunden jemanden autonom pingen.
    # -----------------------------------------------------

    since_global = (
        seconds_since_last_global_ping()
    )

    if (
        since_global is not None
        and
        since_global
        <
        MIN_SECONDS_BETWEEN_AUTONOMOUS_PINGS
    ):

        return (
            False,
            "global_cooldown"
        )

    return (
        True,
        "allowed"
    )


# =========================================================
# REGISTER AUTONOMOUS PING
# =========================================================

def register_autonomous_ping(
    target_user_id
):

    refresh_daily_state()

    target_user_id = str(
        target_user_id
    )

    now = time.time()

    social_state[
        "daily_ping_count"
    ] = (
        get_daily_ping_count()
        + 1
    )

    social_state[
        "last_global_ping"
    ] = now

    target_data = (
        social_state.setdefault(
            "last_target_pings",
            {}
        )
    )

    target_data[
        target_user_id
    ] = now

    save_state()


# =========================================================
# SOCIAL ACTION STATUS
# =========================================================

def get_social_action_status(
    target_user_id=None
):

    refresh_daily_state()

    daily_count = (
        get_daily_ping_count()
    )

    since_global = (
        seconds_since_last_global_ping()
    )

    if since_global is None:

        global_remaining = 0

    else:

        global_remaining = max(
            0,
            int(
                MIN_SECONDS_BETWEEN_AUTONOMOUS_PINGS
                - since_global
            )
        )

    target_remaining = 0

    if target_user_id:

        since_target = (
            seconds_since_target_ping(
                target_user_id
            )
        )

        if since_target is not None:

            target_remaining = max(
                0,
                int(
                    MIN_SECONDS_BETWEEN_AUTONOMOUS_PINGS
                    - since_target
                )
            )

    return {

        "daily_count":
            daily_count,

        "daily_limit":
            MAX_AUTONOMOUS_PINGS_PER_DAY,

        "global_cooldown_remaining":
            global_remaining,

        "target_cooldown_remaining":
            target_remaining
    }


# =========================================================
# DEBUG
# =========================================================

def format_social_action_debug(
    target_user_id=None
):

    status = (
        get_social_action_status(
            target_user_id
        )
    )

    return (
        "[SOCIAL ACTION] "
        f"daily="
        f"{status['daily_count']}/"
        f"{status['daily_limit']} "
        f"global_cd="
        f"{status['global_cooldown_remaining']}s "
        f"target="
        f"{target_user_id}"
    )
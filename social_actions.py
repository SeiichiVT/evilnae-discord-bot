import time
from datetime import datetime, timezone
from collections import defaultdict


# =========================================================
# VERSION
# =========================================================

SOCIAL_ACTIONS_VERSION = "1.0"


# =========================================================
# LIMITS
# =========================================================

MAX_AUTONOMOUS_PINGS_PER_DAY = 5

MIN_SECONDS_BETWEEN_PINGS = (
    2 * 60 * 60
)


# =========================================================
# RUNTIME STATE
# =========================================================

daily_ping_counts = defaultdict(
    int
)

last_ping_timestamp = {}


# =========================================================
# DATE KEY
# =========================================================

def get_day_key():

    now = datetime.now(
        timezone.utc
    )

    return now.strftime(
        "%Y-%m-%d"
    )


# =========================================================
# INTERNAL KEY
# =========================================================

def make_daily_key(
    target_user_id
):

    return (
        get_day_key(),
        str(target_user_id)
    )


# =========================================================
# GET COUNT
# =========================================================

def get_daily_ping_count(
    target_user_id
):

    key = (
        make_daily_key(
            target_user_id
        )
    )

    return daily_ping_counts[
        key
    ]


# =========================================================
# TIME SINCE LAST PING
# =========================================================

def seconds_since_last_ping(
    target_user_id
):

    target_user_id = str(
        target_user_id
    )

    last_ping = (
        last_ping_timestamp.get(
            target_user_id
        )
    )

    if last_ping is None:
        return None

    return (
        time.time()
        - last_ping
    )


# =========================================================
# CAN PING?
# =========================================================

def can_autonomously_ping(
    target_user_id
):

    count = (
        get_daily_ping_count(
            target_user_id
        )
    )

    if (
        count
        >= MAX_AUTONOMOUS_PINGS_PER_DAY
    ):

        return (
            False,
            "daily_limit"
        )

    seconds_since = (
        seconds_since_last_ping(
            target_user_id
        )
    )

    if (
        seconds_since is not None
        and
        seconds_since
        < MIN_SECONDS_BETWEEN_PINGS
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
# REGISTER PING
# =========================================================

def register_autonomous_ping(
    target_user_id
):

    target_user_id = str(
        target_user_id
    )

    key = (
        make_daily_key(
            target_user_id
        )
    )

    daily_ping_counts[
        key
    ] += 1

    last_ping_timestamp[
        target_user_id
    ] = time.time()


# =========================================================
# DEBUG
# =========================================================

def format_social_action_debug(
    target_user_id
):

    count = (
        get_daily_ping_count(
            target_user_id
        )
    )

    seconds_since = (
        seconds_since_last_ping(
            target_user_id
        )
    )

    if seconds_since is None:

        since_text = (
            "never"
        )

    else:

        since_text = (
            f"{seconds_since:.0f}s"
        )

    return (
        "[SOCIAL ACTION] "
        f"target={target_user_id} "
        f"daily={count}/"
        f"{MAX_AUTONOMOUS_PINGS_PER_DAY} "
        f"since_last={since_text}"
    )
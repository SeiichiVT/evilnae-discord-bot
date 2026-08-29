from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
from pathlib import Path
from typing import Any


SERVER_AWARENESS_VERSION = "1.0.1-sensitive-language"
SERVER_AWARENESS_PATH = Path(
    "evilnae_server_awareness.json"
)

_LOCK = threading.RLock()

MAX_EVENTS = 320
EVENT_TTL_SECONDS = 24 * 60 * 60

EVILNAE_NAME_PATTERN = re.compile(
    r"\b(?:evilnae|evil)\b",
    re.I,
)

HANAE_NAME_PATTERN = re.compile(
    r"\bhanae\b",
    re.I,
)

QUESTION_PATTERN = re.compile(
    r"\?|^\s*(?:was|wer|wie|warum|wieso|wann|wo|"
    r"welche|welcher|welches|kann|kannst|hast|bist|"
    r"magst|meinst|denkst|findest)\b",
    re.I,
)

LAUGHTER_PATTERN = re.compile(
    r"(?:\b(?:lol+|lmao|haha+|hehe+|xd+)\b|😂|🤣|💀)",
    re.I,
)

CARE_PATTERN = re.compile(
    r"(?:"
    r"\bkopfschmerz(?:en)?\b|"
    r"\b[A-Za-zÄÖÜäöüß-]*schmerzen\b|"
    r"\bmigräne\b|"
    r"\bmigraene\b|"
    r"\bkrank\b|"
    r"\bfieber\b|"
    r"\bnotaufnahme\b|"
    r"\bkrankenhaus\b|"
    r"\bmir\s+geht(?:'|’)?s\s+nicht\s+gut\b|"
    r"\bpanik\b|"
    r"\btraurig\b|"
    r"\bweine\b|"
    r"\bheule\b"
    r")",
    re.I,
)

CONFLICT_PATTERN = re.compile(
    r"\b(?:streit|angepisst|sauer|genervt|"
    r"halt\s+die\s+klappe|verpiss\s+dich|"
    r"fick\s+dich|ich\s+hasse\s+dich)\b",
    re.I,
)


def _hash(
    value: Any,
) -> str:
    raw = str(
        value
        or ""
    )

    return hashlib.sha1(
        raw.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


def _default_data() -> dict:
    return {
        "version": SERVER_AWARENESS_VERSION,
        "events": [],
        "channels": {},
    }


def _load() -> dict:
    if not SERVER_AWARENESS_PATH.exists():
        return _default_data()

    try:
        data = json.loads(
            SERVER_AWARENESS_PATH.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return _default_data()

    if not isinstance(
        data,
        dict,
    ):
        return _default_data()

    events = data.get(
        "events",
        [],
    )

    channels = data.get(
        "channels",
        {},
    )

    if not isinstance(
        events,
        list,
    ):
        events = []

    if not isinstance(
        channels,
        dict,
    ):
        channels = {}

    return {
        "version": SERVER_AWARENESS_VERSION,
        "events": [
            item
            for item in events
            if isinstance(
                item,
                dict,
            )
        ],
        "channels": channels,
    }


def _prune(
    data: dict,
    *,
    now: float,
) -> None:
    events = [
        item
        for item in (
            data.get(
                "events",
                [],
            )
            or []
        )
        if isinstance(
            item,
            dict,
        )
        and (
            now
            -
            float(
                item.get(
                    "timestamp",
                    0.0,
                )
                or 0.0
            )
            <=
            EVENT_TTL_SECONDS
        )
    ]

    data[
        "events"
    ] = events[
        -MAX_EVENTS:
    ]


def _save(
    data: dict,
) -> None:
    data[
        "version"
    ] = SERVER_AWARENESS_VERSION

    temp = Path(
        str(
            SERVER_AWARENESS_PATH
        )
        +
        ".tmp"
    )

    temp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp.replace(
        SERVER_AWARENESS_PATH
    )


def _flags_for_text(
    text: str,
    *,
    direct=False,
    replied_to_evilnae=False,
    emoji_only=False,
) -> list[str]:
    value = str(
        text
        or ""
    )

    flags = []

    if direct:
        flags.append(
            "direct"
        )

    if replied_to_evilnae:
        flags.append(
            "reply_to_evilnae"
        )

    if EVILNAE_NAME_PATTERN.search(
        value
    ):
        flags.append(
            "evilnae_reference"
        )

    if HANAE_NAME_PATTERN.search(
        value
    ):
        flags.append(
            "hanae_reference"
        )

    if QUESTION_PATTERN.search(
        value
    ):
        flags.append(
            "question"
        )

    if LAUGHTER_PATTERN.search(
        value
    ):
        flags.append(
            "laughter"
        )

    if CARE_PATTERN.search(
        value
    ):
        flags.append(
            "care_sensitive"
        )

    if CONFLICT_PATTERN.search(
        value
    ):
        flags.append(
            "conflict"
        )

    if emoji_only:
        flags.append(
            "emoji_only"
        )

    word_count = len(
        re.findall(
            r"[A-Za-zÄÖÜäöüß0-9]+",
            value,
        )
    )

    if word_count >= 20:
        flags.append(
            "substantial_message"
        )

    return list(
        dict.fromkeys(
            flags
        )
    )


def observe_message_metadata(
    *,
    guild_id="",
    channel_id="",
    channel_name="",
    user_id="",
    text="",
    message_id="",
    timestamp: float | None = None,
    direct=False,
    replied_to_evilnae=False,
    emoji_only=False,
) -> dict:
    """
    Persistent server awareness stores STRUCTURAL metadata only.

    It deliberately does NOT store raw Discord message text,
    usernames, attachments, URLs or message content.
    """

    channel_id = str(
        channel_id
        or ""
    ).strip()

    if not channel_id:
        return {
            "saved": False,
            "reason": "missing_channel",
        }

    now = float(
        timestamp
        if timestamp is not None
        else time.time()
    )

    event_key = (
        str(
            message_id
            or ""
        ).strip()
        or
        _hash(
            f"{channel_id}|{user_id}|{text}|{int(now)}"
        )
    )

    flags = _flags_for_text(
        text,
        direct=bool(
            direct
        ),
        replied_to_evilnae=bool(
            replied_to_evilnae
        ),
        emoji_only=bool(
            emoji_only
        ),
    )

    event = {
        "event_key": event_key,
        "timestamp": now,
        "kind": "user",
        "guild_id": str(
            guild_id
            or ""
        ),
        "channel_id": channel_id,
        "channel_name": str(
            channel_name
            or ""
        )[:80],
        "user_hash": _hash(
            user_id
        ),
        "flags": flags,
        "message_size": min(
            500,
            len(
                str(
                    text
                    or ""
                )
            ),
        ),
    }

    with _LOCK:
        data = _load()

        _prune(
            data,
            now=now,
        )

        for existing in reversed(
            data[
                "events"
            ][-40:]
        ):
            if (
                str(
                    existing.get(
                        "event_key",
                        "",
                    )
                )
                ==
                event_key
            ):
                return {
                    "saved": False,
                    "reason": "duplicate_event",
                    "event": existing,
                }

        data[
            "events"
        ].append(
            event
        )

        channel = dict(
            data[
                "channels"
            ].get(
                channel_id,
                {},
            )
            or {}
        )

        channel.update(
            {
                "guild_id": str(
                    guild_id
                    or channel.get(
                        "guild_id",
                        "",
                    )
                ),
                "channel_id": channel_id,
                "channel_name": str(
                    channel_name
                    or channel.get(
                        "channel_name",
                        "",
                    )
                )[:80],
                "last_user_message_at": now,
                "last_event_at": now,
            }
        )

        data[
            "channels"
        ][
            channel_id
        ] = channel

        _save(
            data
        )

    return {
        "saved": True,
        "reason": "observed",
        "event": event,
    }


def observe_discord_message(
    message,
    *,
    bot_user_id=None,
) -> dict:
    """
    Called before the bot's ALLOWED_CHANNEL_ID response gate.

    This gives Evilnae server-wide structural awareness without
    making her answer in channels where she is not allowed to answer.
    """

    if message is None:
        return {
            "saved": False,
            "reason": "missing_message",
        }

    author = getattr(
        message,
        "author",
        None,
    )

    channel = getattr(
        message,
        "channel",
        None,
    )

    guild = getattr(
        message,
        "guild",
        None,
    )

    if (
        author is None
        or channel is None
    ):
        return {
            "saved": False,
            "reason": "missing_metadata",
        }

    if bool(
        getattr(
            author,
            "bot",
            False,
        )
    ):
        return {
            "saved": False,
            "reason": "bot_message_ignored",
        }

    raw = str(
        getattr(
            message,
            "content",
            "",
        )
        or ""
    )

    bot_user_id = str(
        bot_user_id
        or ""
    )

    mentions = list(
        getattr(
            message,
            "mentions",
            [],
        )
        or []
    )

    directly_mentions_bot = any(
        str(
            getattr(
                member,
                "id",
                "",
            )
        )
        ==
        bot_user_id
        for member in mentions
        if bot_user_id
    )

    replied_to_evilnae = False

    reference = getattr(
        message,
        "reference",
        None,
    )

    resolved = getattr(
        reference,
        "resolved",
        None,
    )

    if (
        resolved is not None
        and bot_user_id
    ):
        replied_to_evilnae = (
            str(
                getattr(
                    getattr(
                        resolved,
                        "author",
                        None,
                    ),
                    "id",
                    "",
                )
            )
            ==
            bot_user_id
        )

    direct = bool(
        directly_mentions_bot
        or replied_to_evilnae
        or re.search(
            r"^\s*(?:hey|hi|hallo|yo|moin|na|okay|ok)?\s*"
            r"(?:evilnae|evil)\b",
            raw,
            flags=re.I,
        )
    )

    created_at = getattr(
        message,
        "created_at",
        None,
    )

    timestamp = (
        created_at.timestamp()
        if created_at is not None
        else time.time()
    )

    return observe_message_metadata(
        guild_id=str(
            getattr(
                guild,
                "id",
                "",
            )
            or ""
        ),
        channel_id=str(
            getattr(
                channel,
                "id",
                "",
            )
            or ""
        ),
        channel_name=str(
            getattr(
                channel,
                "name",
                "",
            )
            or ""
        ),
        user_id=str(
            getattr(
                author,
                "id",
                "",
            )
            or ""
        ),
        text=raw,
        message_id=str(
            getattr(
                message,
                "id",
                "",
            )
            or ""
        ),
        timestamp=timestamp,
        direct=direct,
        replied_to_evilnae=(
            replied_to_evilnae
        ),
        emoji_only=bool(
            raw.strip()
            and not re.search(
                r"[A-Za-zÄÖÜäöüß0-9]",
                re.sub(
                    r"<a?:[A-Za-z0-9_]+:\d+>",
                    "",
                    raw,
                ),
            )
        ),
    )


def register_bot_message(
    *,
    channel_id,
    kind="reply",
    timestamp: float | None = None,
) -> dict:
    channel_id = str(
        channel_id
        or ""
    ).strip()

    if not channel_id:
        return {
            "saved": False,
            "reason": "missing_channel",
        }

    now = float(
        timestamp
        if timestamp is not None
        else time.time()
    )

    with _LOCK:
        data = _load()

        _prune(
            data,
            now=now,
        )

        channel = dict(
            data[
                "channels"
            ].get(
                channel_id,
                {},
            )
            or {}
        )

        event = {
            "event_key": (
                "bot:"
                +
                _hash(
                    f"{channel_id}|{kind}|{time.time_ns()}"
                )
            ),
            "timestamp": now,
            "kind": "bot",
            "guild_id": str(
                channel.get(
                    "guild_id",
                    "",
                )
            ),
            "channel_id": channel_id,
            "channel_name": str(
                channel.get(
                    "channel_name",
                    "",
                )
            )[:80],
            "user_hash": "EVILNAE",
            "flags": [
                str(
                    kind
                    or "reply"
                )[:50]
            ],
            "message_size": 0,
        }

        data[
            "events"
        ].append(
            event
        )

        channel.update(
            {
                "channel_id": channel_id,
                "last_bot_message_at": now,
                "last_event_at": now,
            }
        )

        data[
            "channels"
        ][
            channel_id
        ] = channel

        _save(
            data
        )

    return {
        "saved": True,
        "reason": "bot_observed",
        "event": event,
    }


def _events_for_channel(
    channel_id: str,
    *,
    now: float,
) -> list[dict]:
    channel_id = str(
        channel_id
        or ""
    )

    with _LOCK:
        data = _load()

    return [
        item
        for item in (
            data.get(
                "events",
                [],
            )
            or []
        )
        if isinstance(
            item,
            dict,
        )
        and
        str(
            item.get(
                "channel_id",
                "",
            )
        )
        ==
        channel_id
        and
        now
        -
        float(
            item.get(
                "timestamp",
                0.0,
            )
            or 0.0
        )
        <=
        EVENT_TTL_SECONDS
    ]


def _window(
    events,
    *,
    now,
    seconds,
):
    return [
        item
        for item in events
        if now
        -
        float(
            item.get(
                "timestamp",
                0.0,
            )
            or 0.0
        )
        <= seconds
    ]


def _level(
    value: float,
) -> str:
    value = max(
        0.0,
        min(
            1.0,
            float(
                value
            ),
        ),
    )

    if value >= 0.72:
        return "high"

    if value >= 0.45:
        return "medium"

    if value >= 0.18:
        return "low"

    return "quiet"


def get_channel_signal(
    channel_id,
    *,
    now: float | None = None,
) -> dict:
    now = float(
        now
        if now is not None
        else time.time()
    )

    channel_id = str(
        channel_id
        or ""
    )

    events = _events_for_channel(
        channel_id,
        now=now,
    )

    last5 = _window(
        events,
        now=now,
        seconds=5 * 60,
    )

    last15 = _window(
        events,
        now=now,
        seconds=15 * 60,
    )

    last60 = _window(
        events,
        now=now,
        seconds=60 * 60,
    )

    users15 = {
        item.get(
            "user_hash"
        )
        for item in last15
        if item.get(
            "kind"
        )
        ==
        "user"
        and item.get(
            "user_hash"
        )
    }

    user_events15 = [
        item
        for item in last15
        if item.get(
            "kind"
        )
        ==
        "user"
    ]

    bot_events15 = [
        item
        for item in last15
        if item.get(
            "kind"
        )
        ==
        "bot"
    ]

    def count_flag(
        flag,
        items=last15,
    ):
        return sum(
            1
            for item in items
            if flag
            in (
                item.get(
                    "flags",
                    [],
                )
                or []
            )
        )

    evil_refs = (
        count_flag(
            "evilnae_reference"
        )
        +
        count_flag(
            "reply_to_evilnae"
        )
        +
        count_flag(
            "direct"
        )
    )

    questions = count_flag(
        "question"
    )

    care_count = count_flag(
        "care_sensitive",
        last60,
    )

    conflict_count = count_flag(
        "conflict",
        last60,
    )

    laughter = count_flag(
        "laughter"
    )

    total15 = (
        len(
            user_events15
        )
        +
        len(
            bot_events15
        )
    )

    bot_pressure = (
        len(
            bot_events15
        )
        /
        max(
            1,
            total15,
        )
    )

    if bot_events15:
        last_bot_age = now - max(
            float(
                item.get(
                    "timestamp",
                    0.0,
                )
                or 0.0
            )
            for item in bot_events15
        )
    else:
        last_bot_age = None

    user_events = [
        item
        for item in events
        if item.get(
            "kind"
        )
        ==
        "user"
    ]

    if user_events:
        last_user_age = now - max(
            float(
                item.get(
                    "timestamp",
                    0.0,
                )
                or 0.0
            )
            for item in user_events
        )
    else:
        last_user_age = None

    activity_score = min(
        1.0,
        (
            len(
                last5
            )
            /
            12.0
        )
        +
        (
            len(
                last15
            )
            /
            40.0
        ),
    )

    social_pull = min(
        1.0,
        evil_refs * 0.16
        +
        questions * 0.04
        +
        laughter * 0.025
        +
        min(
            0.18,
            len(
                users15
            )
            * 0.04,
        ),
    )

    if last_bot_age is not None:
        if last_bot_age < 90:
            bot_pressure = min(
                1.0,
                bot_pressure
                +
                0.25,
            )
        elif last_bot_age < 5 * 60:
            bot_pressure = min(
                1.0,
                bot_pressure
                +
                0.10,
            )

    sensitive_recent = bool(
        care_count
        or conflict_count
    )

    initiative_opportunity = 0.0

    if last_user_age is not None:
        if (
            8 * 60
            <= last_user_age
            <= 3 * 60 * 60
        ):
            silence_fit = 1.0 - min(
                1.0,
                abs(
                    last_user_age
                    -
                    35 * 60
                )
                /
                (
                    3 * 60 * 60
                ),
            )

            initiative_opportunity = (
                0.30
                +
                silence_fit * 0.28
                +
                social_pull * 0.22
                +
                min(
                    0.10,
                    len(
                        users15
                    )
                    * 0.02,
                )
                -
                bot_pressure * 0.34
            )

            if sensitive_recent:
                initiative_opportunity -= 0.25

    initiative_opportunity = max(
        0.0,
        min(
            1.0,
            initiative_opportunity,
        ),
    )

    if len(
        users15
    ) >= 6:
        crowd = "crowd"
    elif len(
        users15
    ) >= 3:
        crowd = "group"
    elif len(
        users15
    ) >= 2:
        crowd = "small_group"
    elif len(
        users15
    ) == 1:
        crowd = "solo"
    else:
        crowd = "quiet"

    if len(
        last5
    ) >= 12:
        activity = "busy"
    elif len(
        last5
    ) >= 5:
        activity = "active"
    elif len(
        last15
    ) >= 4:
        activity = "warm"
    else:
        activity = "quiet"

    return {
        "channel_id": channel_id,
        "activity": activity,
        "activity_score": round(
            activity_score,
            3,
        ),
        "crowd": crowd,
        "unique_users_15m": len(
            users15
        ),
        "user_messages_15m": len(
            user_events15
        ),
        "bot_messages_15m": len(
            bot_events15
        ),
        "evilnae_refs_15m": evil_refs,
        "questions_15m": questions,
        "social_pull": round(
            social_pull,
            3,
        ),
        "bot_pressure": round(
            max(
                0.0,
                min(
                    1.0,
                    bot_pressure,
                ),
            ),
            3,
        ),
        "sensitive_recent": (
            sensitive_recent
        ),
        "care_events_60m": care_count,
        "conflict_events_60m": (
            conflict_count
        ),
        "last_user_age": (
            round(
                last_user_age,
                1,
            )
            if last_user_age
            is not None
            else None
        ),
        "last_bot_age": (
            round(
                last_bot_age,
                1,
            )
            if last_bot_age
            is not None
            else None
        ),
        "initiative_opportunity": round(
            initiative_opportunity,
            3,
        ),
    }


def format_server_awareness_for_prompt(
    channel_id,
) -> str:
    signal = get_channel_signal(
        channel_id
    )

    return "\n".join(
        [
            (
                "[SERVER AWARENESS "
                f"v{SERVER_AWARENESS_VERSION}]"
            ),
            (
                "Strukturelle Discord-Situation; "
                "keine Fakten über konkrete Personen erfinden."
            ),
            (
                f"- channel activity: "
                f"{signal['activity']}"
            ),
            (
                f"- active crowd: "
                f"{signal['crowd']}"
            ),
            (
                f"- Evilnae social pull: "
                f"{_level(signal['social_pull'])}"
            ),
            (
                f"- Evilnae speaking pressure: "
                f"{_level(signal['bot_pressure'])}"
            ),
            (
                f"- initiative opportunity: "
                f"{_level(signal['initiative_opportunity'])}"
            ),
            (
                f"- sensitive atmosphere recently: "
                f"{'yes' if signal['sensitive_recent'] else 'no'}"
            ),
            (
                "HARD RULES: Server Awareness bestimmt nur "
                "Timing/Beteiligung. Es ist kein Conversation World "
                "und keine Faktenquelle über User."
            ),
        ]
    )


def server_awareness_stats() -> dict:
    now = time.time()

    with _LOCK:
        data = _load()

        _prune(
            data,
            now=now,
        )

    channels = data.get(
        "channels",
        {},
    )

    events = data.get(
        "events",
        [],
    )

    active_channels = {
        item.get(
            "channel_id"
        )
        for item in events
        if now
        -
        float(
            item.get(
                "timestamp",
                0.0,
            )
            or 0.0
        )
        <= 60 * 60
    }

    return {
        "version": SERVER_AWARENESS_VERSION,
        "channels": len(
            channels
        ),
        "active_channels_1h": len(
            {
                item
                for item
                in active_channels
                if item
            }
        ),
        "events_24h": len(
            events
        ),
    }


def format_server_awareness_debug(
    channel_id=None,
) -> str:
    if channel_id:
        signal = get_channel_signal(
            channel_id
        )

        return (
            "[SERVER AWARENESS] "
            f"v={SERVER_AWARENESS_VERSION} "
            f"channel={channel_id} "
            f"activity={signal['activity']} "
            f"crowd={signal['crowd']} "
            f"pull={signal['social_pull']:.2f} "
            f"bot_pressure={signal['bot_pressure']:.2f} "
            f"initiative={signal['initiative_opportunity']:.2f}"
        )

    stats = server_awareness_stats()

    return (
        "[SERVER AWARENESS] "
        f"v={SERVER_AWARENESS_VERSION} "
        f"channels={stats['channels']} "
        f"active_1h={stats['active_channels_1h']} "
        f"events_24h={stats['events_24h']}"
    )


def _self_test() -> int:
    global SERVER_AWARENESS_PATH

    import tempfile

    original = SERVER_AWARENESS_PATH
    tests = []

    try:
        with tempfile.TemporaryDirectory() as tmp:
            SERVER_AWARENESS_PATH = (
                Path(tmp)
                /
                "server.json"
            )

            now = time.time()

            result = observe_message_metadata(
                guild_id="g1",
                channel_id="c1",
                channel_name="general",
                user_id="u1",
                text=(
                    "Evil was denkst du über das? xD"
                ),
                message_id="m1",
                timestamp=now,
                direct=True,
            )

            tests.append(
                (
                    "message observed",
                    result[
                        "saved"
                    ],
                )
            )

            duplicate = observe_message_metadata(
                guild_id="g1",
                channel_id="c1",
                channel_name="general",
                user_id="u1",
                text="same raw text",
                message_id="m1",
                timestamp=now + 1,
                direct=True,
            )

            tests.append(
                (
                    "message dedupe",
                    duplicate[
                        "reason"
                    ]
                    ==
                    "duplicate_event",
                )
            )

            raw = (
                SERVER_AWARENESS_PATH.read_text(
                    encoding="utf-8"
                )
            )

            tests.append(
                (
                    "raw text not persisted",
                    "was denkst du"
                    not in raw
                    and
                    "same raw text"
                    not in raw,
                )
            )

            observe_message_metadata(
                guild_id="g1",
                channel_id="c2",
                channel_name="gaming",
                user_id="u2",
                text="hallo leute",
                message_id="m2",
                timestamp=now,
            )

            tests.append(
                (
                    "multiple channels known",
                    server_awareness_stats()[
                        "channels"
                    ]
                    ==
                    2,
                )
            )

            register_bot_message(
                channel_id="c1",
                kind="reply",
                timestamp=now + 2,
            )

            signal = get_channel_signal(
                "c1",
                now=now + 3,
            )

            tests.append(
                (
                    "Evilnae reference raises social pull",
                    signal[
                        "social_pull"
                    ]
                    >
                    0.0,
                )
            )

            tests.append(
                (
                    "recent bot raises bot pressure",
                    signal[
                        "bot_pressure"
                    ]
                    >
                    0.40,
                )
            )

            observe_message_metadata(
                guild_id="g1",
                channel_id="c3",
                channel_name="care",
                user_id="u3",
                text="ich hab Kopfschmerzen",
                message_id="m3",
                timestamp=now,
            )

            care_signal = get_channel_signal(
                "c3",
                now=now + 10,
            )

            tests.append(
                (
                    "sensitive atmosphere detected",
                    care_signal[
                        "sensitive_recent"
                    ],
                )
            )

            prompt = (
                format_server_awareness_for_prompt(
                    "c1"
                )
            )

            tests.append(
                (
                    "prompt has structural state",
                    "channel activity:"
                    in prompt
                    and
                    "speaking pressure:"
                    in prompt,
                )
            )

            tests.append(
                (
                    "prompt has no raw message",
                    "was denkst du"
                    not in prompt,
                )
            )

    finally:
        SERVER_AWARENESS_PATH = (
            original
        )

    passed = sum(
        1
        for _, success
        in tests
        if success
    )

    print()
    print("=" * 64)
    print(
        f"SERVER AWARENESS "
        f"v{SERVER_AWARENESS_VERSION} TEST"
    )
    print("=" * 64)

    for name, success in tests:
        print(
            f"[{'PASS' if success else 'FAIL'}] "
            f"{name}"
        )

    print(
        f"RESULT: "
        f"{passed}/{len(tests)} PASS"
    )

    return (
        0
        if passed == len(tests)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        _self_test()
    )

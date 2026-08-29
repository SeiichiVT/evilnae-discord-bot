from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
AGENCY_PATH = PROJECT_ROOT / "agency.py"
INITIATIVE_PATH = PROJECT_ROOT / "initiative.py"
SERVER_PATH = PROJECT_ROOT / "server_awareness.py"
AGENCY_V2_PATH = PROJECT_ROOT / "agency_initiative_v2.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

SERVER_SOURCE = 'from __future__ import annotations\n\nimport hashlib\nimport json\nimport math\nimport re\nimport threading\nimport time\nfrom pathlib import Path\nfrom typing import Any\n\n\nSERVER_AWARENESS_VERSION = "1.0"\nSERVER_AWARENESS_PATH = Path(\n    "evilnae_server_awareness.json"\n)\n\n_LOCK = threading.RLock()\n\nMAX_EVENTS = 320\nEVENT_TTL_SECONDS = 24 * 60 * 60\n\nEVILNAE_NAME_PATTERN = re.compile(\n    r"\\b(?:evilnae|evil)\\b",\n    re.I,\n)\n\nHANAE_NAME_PATTERN = re.compile(\n    r"\\bhanae\\b",\n    re.I,\n)\n\nQUESTION_PATTERN = re.compile(\n    r"\\?|^\\s*(?:was|wer|wie|warum|wieso|wann|wo|"\n    r"welche|welcher|welches|kann|kannst|hast|bist|"\n    r"magst|meinst|denkst|findest)\\b",\n    re.I,\n)\n\nLAUGHTER_PATTERN = re.compile(\n    r"(?:\\b(?:lol+|lmao|haha+|hehe+|xd+)\\b|😂|🤣|💀)",\n    re.I,\n)\n\nCARE_PATTERN = re.compile(\n    r"\\b(?:kopfschmerz|migräne|migraene|schmerzen|"\n    r"krank|fieber|notaufnahme|krankenhaus|"\n    r"mir\\s+geht(?:\'|’)?s\\s+nicht\\s+gut|"\n    r"panik|traurig|weine|heule)\\b",\n    re.I,\n)\n\nCONFLICT_PATTERN = re.compile(\n    r"\\b(?:streit|angepisst|sauer|genervt|"\n    r"halt\\s+die\\s+klappe|verpiss\\s+dich|"\n    r"fick\\s+dich|ich\\s+hasse\\s+dich)\\b",\n    re.I,\n)\n\n\ndef _hash(\n    value: Any,\n) -> str:\n    raw = str(\n        value\n        or ""\n    )\n\n    return hashlib.sha1(\n        raw.encode(\n            "utf-8",\n            errors="ignore",\n        )\n    ).hexdigest()\n\n\ndef _default_data() -> dict:\n    return {\n        "version": SERVER_AWARENESS_VERSION,\n        "events": [],\n        "channels": {},\n    }\n\n\ndef _load() -> dict:\n    if not SERVER_AWARENESS_PATH.exists():\n        return _default_data()\n\n    try:\n        data = json.loads(\n            SERVER_AWARENESS_PATH.read_text(\n                encoding="utf-8"\n            )\n        )\n    except Exception:\n        return _default_data()\n\n    if not isinstance(\n        data,\n        dict,\n    ):\n        return _default_data()\n\n    events = data.get(\n        "events",\n        [],\n    )\n\n    channels = data.get(\n        "channels",\n        {},\n    )\n\n    if not isinstance(\n        events,\n        list,\n    ):\n        events = []\n\n    if not isinstance(\n        channels,\n        dict,\n    ):\n        channels = {}\n\n    return {\n        "version": SERVER_AWARENESS_VERSION,\n        "events": [\n            item\n            for item in events\n            if isinstance(\n                item,\n                dict,\n            )\n        ],\n        "channels": channels,\n    }\n\n\ndef _prune(\n    data: dict,\n    *,\n    now: float,\n) -> None:\n    events = [\n        item\n        for item in (\n            data.get(\n                "events",\n                [],\n            )\n            or []\n        )\n        if isinstance(\n            item,\n            dict,\n        )\n        and (\n            now\n            -\n            float(\n                item.get(\n                    "timestamp",\n                    0.0,\n                )\n                or 0.0\n            )\n            <=\n            EVENT_TTL_SECONDS\n        )\n    ]\n\n    data[\n        "events"\n    ] = events[\n        -MAX_EVENTS:\n    ]\n\n\ndef _save(\n    data: dict,\n) -> None:\n    data[\n        "version"\n    ] = SERVER_AWARENESS_VERSION\n\n    temp = Path(\n        str(\n            SERVER_AWARENESS_PATH\n        )\n        +\n        ".tmp"\n    )\n\n    temp.write_text(\n        json.dumps(\n            data,\n            ensure_ascii=False,\n            indent=2,\n        ),\n        encoding="utf-8",\n    )\n\n    temp.replace(\n        SERVER_AWARENESS_PATH\n    )\n\n\ndef _flags_for_text(\n    text: str,\n    *,\n    direct=False,\n    replied_to_evilnae=False,\n    emoji_only=False,\n) -> list[str]:\n    value = str(\n        text\n        or ""\n    )\n\n    flags = []\n\n    if direct:\n        flags.append(\n            "direct"\n        )\n\n    if replied_to_evilnae:\n        flags.append(\n            "reply_to_evilnae"\n        )\n\n    if EVILNAE_NAME_PATTERN.search(\n        value\n    ):\n        flags.append(\n            "evilnae_reference"\n        )\n\n    if HANAE_NAME_PATTERN.search(\n        value\n    ):\n        flags.append(\n            "hanae_reference"\n        )\n\n    if QUESTION_PATTERN.search(\n        value\n    ):\n        flags.append(\n            "question"\n        )\n\n    if LAUGHTER_PATTERN.search(\n        value\n    ):\n        flags.append(\n            "laughter"\n        )\n\n    if CARE_PATTERN.search(\n        value\n    ):\n        flags.append(\n            "care_sensitive"\n        )\n\n    if CONFLICT_PATTERN.search(\n        value\n    ):\n        flags.append(\n            "conflict"\n        )\n\n    if emoji_only:\n        flags.append(\n            "emoji_only"\n        )\n\n    word_count = len(\n        re.findall(\n            r"[A-Za-zÄÖÜäöüß0-9]+",\n            value,\n        )\n    )\n\n    if word_count >= 20:\n        flags.append(\n            "substantial_message"\n        )\n\n    return list(\n        dict.fromkeys(\n            flags\n        )\n    )\n\n\ndef observe_message_metadata(\n    *,\n    guild_id="",\n    channel_id="",\n    channel_name="",\n    user_id="",\n    text="",\n    message_id="",\n    timestamp: float | None = None,\n    direct=False,\n    replied_to_evilnae=False,\n    emoji_only=False,\n) -> dict:\n    """\n    Persistent server awareness stores STRUCTURAL metadata only.\n\n    It deliberately does NOT store raw Discord message text,\n    usernames, attachments, URLs or message content.\n    """\n\n    channel_id = str(\n        channel_id\n        or ""\n    ).strip()\n\n    if not channel_id:\n        return {\n            "saved": False,\n            "reason": "missing_channel",\n        }\n\n    now = float(\n        timestamp\n        if timestamp is not None\n        else time.time()\n    )\n\n    event_key = (\n        str(\n            message_id\n            or ""\n        ).strip()\n        or\n        _hash(\n            f"{channel_id}|{user_id}|{text}|{int(now)}"\n        )\n    )\n\n    flags = _flags_for_text(\n        text,\n        direct=bool(\n            direct\n        ),\n        replied_to_evilnae=bool(\n            replied_to_evilnae\n        ),\n        emoji_only=bool(\n            emoji_only\n        ),\n    )\n\n    event = {\n        "event_key": event_key,\n        "timestamp": now,\n        "kind": "user",\n        "guild_id": str(\n            guild_id\n            or ""\n        ),\n        "channel_id": channel_id,\n        "channel_name": str(\n            channel_name\n            or ""\n        )[:80],\n        "user_hash": _hash(\n            user_id\n        ),\n        "flags": flags,\n        "message_size": min(\n            500,\n            len(\n                str(\n                    text\n                    or ""\n                )\n            ),\n        ),\n    }\n\n    with _LOCK:\n        data = _load()\n\n        _prune(\n            data,\n            now=now,\n        )\n\n        for existing in reversed(\n            data[\n                "events"\n            ][-40:]\n        ):\n            if (\n                str(\n                    existing.get(\n                        "event_key",\n                        "",\n                    )\n                )\n                ==\n                event_key\n            ):\n                return {\n                    "saved": False,\n                    "reason": "duplicate_event",\n                    "event": existing,\n                }\n\n        data[\n            "events"\n        ].append(\n            event\n        )\n\n        channel = dict(\n            data[\n                "channels"\n            ].get(\n                channel_id,\n                {},\n            )\n            or {}\n        )\n\n        channel.update(\n            {\n                "guild_id": str(\n                    guild_id\n                    or channel.get(\n                        "guild_id",\n                        "",\n                    )\n                ),\n                "channel_id": channel_id,\n                "channel_name": str(\n                    channel_name\n                    or channel.get(\n                        "channel_name",\n                        "",\n                    )\n                )[:80],\n                "last_user_message_at": now,\n                "last_event_at": now,\n            }\n        )\n\n        data[\n            "channels"\n        ][\n            channel_id\n        ] = channel\n\n        _save(\n            data\n        )\n\n    return {\n        "saved": True,\n        "reason": "observed",\n        "event": event,\n    }\n\n\ndef observe_discord_message(\n    message,\n    *,\n    bot_user_id=None,\n) -> dict:\n    """\n    Called before the bot\'s ALLOWED_CHANNEL_ID response gate.\n\n    This gives Evilnae server-wide structural awareness without\n    making her answer in channels where she is not allowed to answer.\n    """\n\n    if message is None:\n        return {\n            "saved": False,\n            "reason": "missing_message",\n        }\n\n    author = getattr(\n        message,\n        "author",\n        None,\n    )\n\n    channel = getattr(\n        message,\n        "channel",\n        None,\n    )\n\n    guild = getattr(\n        message,\n        "guild",\n        None,\n    )\n\n    if (\n        author is None\n        or channel is None\n    ):\n        return {\n            "saved": False,\n            "reason": "missing_metadata",\n        }\n\n    if bool(\n        getattr(\n            author,\n            "bot",\n            False,\n        )\n    ):\n        return {\n            "saved": False,\n            "reason": "bot_message_ignored",\n        }\n\n    raw = str(\n        getattr(\n            message,\n            "content",\n            "",\n        )\n        or ""\n    )\n\n    bot_user_id = str(\n        bot_user_id\n        or ""\n    )\n\n    mentions = list(\n        getattr(\n            message,\n            "mentions",\n            [],\n        )\n        or []\n    )\n\n    directly_mentions_bot = any(\n        str(\n            getattr(\n                member,\n                "id",\n                "",\n            )\n        )\n        ==\n        bot_user_id\n        for member in mentions\n        if bot_user_id\n    )\n\n    replied_to_evilnae = False\n\n    reference = getattr(\n        message,\n        "reference",\n        None,\n    )\n\n    resolved = getattr(\n        reference,\n        "resolved",\n        None,\n    )\n\n    if (\n        resolved is not None\n        and bot_user_id\n    ):\n        replied_to_evilnae = (\n            str(\n                getattr(\n                    getattr(\n                        resolved,\n                        "author",\n                        None,\n                    ),\n                    "id",\n                    "",\n                )\n            )\n            ==\n            bot_user_id\n        )\n\n    direct = bool(\n        directly_mentions_bot\n        or replied_to_evilnae\n        or re.search(\n            r"^\\s*(?:hey|hi|hallo|yo|moin|na|okay|ok)?\\s*"\n            r"(?:evilnae|evil)\\b",\n            raw,\n            flags=re.I,\n        )\n    )\n\n    created_at = getattr(\n        message,\n        "created_at",\n        None,\n    )\n\n    timestamp = (\n        created_at.timestamp()\n        if created_at is not None\n        else time.time()\n    )\n\n    return observe_message_metadata(\n        guild_id=str(\n            getattr(\n                guild,\n                "id",\n                "",\n            )\n            or ""\n        ),\n        channel_id=str(\n            getattr(\n                channel,\n                "id",\n                "",\n            )\n            or ""\n        ),\n        channel_name=str(\n            getattr(\n                channel,\n                "name",\n                "",\n            )\n            or ""\n        ),\n        user_id=str(\n            getattr(\n                author,\n                "id",\n                "",\n            )\n            or ""\n        ),\n        text=raw,\n        message_id=str(\n            getattr(\n                message,\n                "id",\n                "",\n            )\n            or ""\n        ),\n        timestamp=timestamp,\n        direct=direct,\n        replied_to_evilnae=(\n            replied_to_evilnae\n        ),\n        emoji_only=bool(\n            raw.strip()\n            and not re.search(\n                r"[A-Za-zÄÖÜäöüß0-9]",\n                re.sub(\n                    r"<a?:[A-Za-z0-9_]+:\\d+>",\n                    "",\n                    raw,\n                ),\n            )\n        ),\n    )\n\n\ndef register_bot_message(\n    *,\n    channel_id,\n    kind="reply",\n    timestamp: float | None = None,\n) -> dict:\n    channel_id = str(\n        channel_id\n        or ""\n    ).strip()\n\n    if not channel_id:\n        return {\n            "saved": False,\n            "reason": "missing_channel",\n        }\n\n    now = float(\n        timestamp\n        if timestamp is not None\n        else time.time()\n    )\n\n    with _LOCK:\n        data = _load()\n\n        _prune(\n            data,\n            now=now,\n        )\n\n        channel = dict(\n            data[\n                "channels"\n            ].get(\n                channel_id,\n                {},\n            )\n            or {}\n        )\n\n        event = {\n            "event_key": (\n                "bot:"\n                +\n                _hash(\n                    f"{channel_id}|{kind}|{time.time_ns()}"\n                )\n            ),\n            "timestamp": now,\n            "kind": "bot",\n            "guild_id": str(\n                channel.get(\n                    "guild_id",\n                    "",\n                )\n            ),\n            "channel_id": channel_id,\n            "channel_name": str(\n                channel.get(\n                    "channel_name",\n                    "",\n                )\n            )[:80],\n            "user_hash": "EVILNAE",\n            "flags": [\n                str(\n                    kind\n                    or "reply"\n                )[:50]\n            ],\n            "message_size": 0,\n        }\n\n        data[\n            "events"\n        ].append(\n            event\n        )\n\n        channel.update(\n            {\n                "channel_id": channel_id,\n                "last_bot_message_at": now,\n                "last_event_at": now,\n            }\n        )\n\n        data[\n            "channels"\n        ][\n            channel_id\n        ] = channel\n\n        _save(\n            data\n        )\n\n    return {\n        "saved": True,\n        "reason": "bot_observed",\n        "event": event,\n    }\n\n\ndef _events_for_channel(\n    channel_id: str,\n    *,\n    now: float,\n) -> list[dict]:\n    channel_id = str(\n        channel_id\n        or ""\n    )\n\n    with _LOCK:\n        data = _load()\n\n    return [\n        item\n        for item in (\n            data.get(\n                "events",\n                [],\n            )\n            or []\n        )\n        if isinstance(\n            item,\n            dict,\n        )\n        and\n        str(\n            item.get(\n                "channel_id",\n                "",\n            )\n        )\n        ==\n        channel_id\n        and\n        now\n        -\n        float(\n            item.get(\n                "timestamp",\n                0.0,\n            )\n            or 0.0\n        )\n        <=\n        EVENT_TTL_SECONDS\n    ]\n\n\ndef _window(\n    events,\n    *,\n    now,\n    seconds,\n):\n    return [\n        item\n        for item in events\n        if now\n        -\n        float(\n            item.get(\n                "timestamp",\n                0.0,\n            )\n            or 0.0\n        )\n        <= seconds\n    ]\n\n\ndef _level(\n    value: float,\n) -> str:\n    value = max(\n        0.0,\n        min(\n            1.0,\n            float(\n                value\n            ),\n        ),\n    )\n\n    if value >= 0.72:\n        return "high"\n\n    if value >= 0.45:\n        return "medium"\n\n    if value >= 0.18:\n        return "low"\n\n    return "quiet"\n\n\ndef get_channel_signal(\n    channel_id,\n    *,\n    now: float | None = None,\n) -> dict:\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    channel_id = str(\n        channel_id\n        or ""\n    )\n\n    events = _events_for_channel(\n        channel_id,\n        now=now,\n    )\n\n    last5 = _window(\n        events,\n        now=now,\n        seconds=5 * 60,\n    )\n\n    last15 = _window(\n        events,\n        now=now,\n        seconds=15 * 60,\n    )\n\n    last60 = _window(\n        events,\n        now=now,\n        seconds=60 * 60,\n    )\n\n    users15 = {\n        item.get(\n            "user_hash"\n        )\n        for item in last15\n        if item.get(\n            "kind"\n        )\n        ==\n        "user"\n        and item.get(\n            "user_hash"\n        )\n    }\n\n    user_events15 = [\n        item\n        for item in last15\n        if item.get(\n            "kind"\n        )\n        ==\n        "user"\n    ]\n\n    bot_events15 = [\n        item\n        for item in last15\n        if item.get(\n            "kind"\n        )\n        ==\n        "bot"\n    ]\n\n    def count_flag(\n        flag,\n        items=last15,\n    ):\n        return sum(\n            1\n            for item in items\n            if flag\n            in (\n                item.get(\n                    "flags",\n                    [],\n                )\n                or []\n            )\n        )\n\n    evil_refs = (\n        count_flag(\n            "evilnae_reference"\n        )\n        +\n        count_flag(\n            "reply_to_evilnae"\n        )\n        +\n        count_flag(\n            "direct"\n        )\n    )\n\n    questions = count_flag(\n        "question"\n    )\n\n    care_count = count_flag(\n        "care_sensitive",\n        last60,\n    )\n\n    conflict_count = count_flag(\n        "conflict",\n        last60,\n    )\n\n    laughter = count_flag(\n        "laughter"\n    )\n\n    total15 = (\n        len(\n            user_events15\n        )\n        +\n        len(\n            bot_events15\n        )\n    )\n\n    bot_pressure = (\n        len(\n            bot_events15\n        )\n        /\n        max(\n            1,\n            total15,\n        )\n    )\n\n    if bot_events15:\n        last_bot_age = now - max(\n            float(\n                item.get(\n                    "timestamp",\n                    0.0,\n                )\n                or 0.0\n            )\n            for item in bot_events15\n        )\n    else:\n        last_bot_age = None\n\n    user_events = [\n        item\n        for item in events\n        if item.get(\n            "kind"\n        )\n        ==\n        "user"\n    ]\n\n    if user_events:\n        last_user_age = now - max(\n            float(\n                item.get(\n                    "timestamp",\n                    0.0,\n                )\n                or 0.0\n            )\n            for item in user_events\n        )\n    else:\n        last_user_age = None\n\n    activity_score = min(\n        1.0,\n        (\n            len(\n                last5\n            )\n            /\n            12.0\n        )\n        +\n        (\n            len(\n                last15\n            )\n            /\n            40.0\n        ),\n    )\n\n    social_pull = min(\n        1.0,\n        evil_refs * 0.16\n        +\n        questions * 0.04\n        +\n        laughter * 0.025\n        +\n        min(\n            0.18,\n            len(\n                users15\n            )\n            * 0.04,\n        ),\n    )\n\n    if last_bot_age is not None:\n        if last_bot_age < 90:\n            bot_pressure = min(\n                1.0,\n                bot_pressure\n                +\n                0.25,\n            )\n        elif last_bot_age < 5 * 60:\n            bot_pressure = min(\n                1.0,\n                bot_pressure\n                +\n                0.10,\n            )\n\n    sensitive_recent = bool(\n        care_count\n        or conflict_count\n    )\n\n    initiative_opportunity = 0.0\n\n    if last_user_age is not None:\n        if (\n            8 * 60\n            <= last_user_age\n            <= 3 * 60 * 60\n        ):\n            silence_fit = 1.0 - min(\n                1.0,\n                abs(\n                    last_user_age\n                    -\n                    35 * 60\n                )\n                /\n                (\n                    3 * 60 * 60\n                ),\n            )\n\n            initiative_opportunity = (\n                0.30\n                +\n                silence_fit * 0.28\n                +\n                social_pull * 0.22\n                +\n                min(\n                    0.10,\n                    len(\n                        users15\n                    )\n                    * 0.02,\n                )\n                -\n                bot_pressure * 0.34\n            )\n\n            if sensitive_recent:\n                initiative_opportunity -= 0.25\n\n    initiative_opportunity = max(\n        0.0,\n        min(\n            1.0,\n            initiative_opportunity,\n        ),\n    )\n\n    if len(\n        users15\n    ) >= 6:\n        crowd = "crowd"\n    elif len(\n        users15\n    ) >= 3:\n        crowd = "group"\n    elif len(\n        users15\n    ) >= 2:\n        crowd = "small_group"\n    elif len(\n        users15\n    ) == 1:\n        crowd = "solo"\n    else:\n        crowd = "quiet"\n\n    if len(\n        last5\n    ) >= 12:\n        activity = "busy"\n    elif len(\n        last5\n    ) >= 5:\n        activity = "active"\n    elif len(\n        last15\n    ) >= 4:\n        activity = "warm"\n    else:\n        activity = "quiet"\n\n    return {\n        "channel_id": channel_id,\n        "activity": activity,\n        "activity_score": round(\n            activity_score,\n            3,\n        ),\n        "crowd": crowd,\n        "unique_users_15m": len(\n            users15\n        ),\n        "user_messages_15m": len(\n            user_events15\n        ),\n        "bot_messages_15m": len(\n            bot_events15\n        ),\n        "evilnae_refs_15m": evil_refs,\n        "questions_15m": questions,\n        "social_pull": round(\n            social_pull,\n            3,\n        ),\n        "bot_pressure": round(\n            max(\n                0.0,\n                min(\n                    1.0,\n                    bot_pressure,\n                ),\n            ),\n            3,\n        ),\n        "sensitive_recent": (\n            sensitive_recent\n        ),\n        "care_events_60m": care_count,\n        "conflict_events_60m": (\n            conflict_count\n        ),\n        "last_user_age": (\n            round(\n                last_user_age,\n                1,\n            )\n            if last_user_age\n            is not None\n            else None\n        ),\n        "last_bot_age": (\n            round(\n                last_bot_age,\n                1,\n            )\n            if last_bot_age\n            is not None\n            else None\n        ),\n        "initiative_opportunity": round(\n            initiative_opportunity,\n            3,\n        ),\n    }\n\n\ndef format_server_awareness_for_prompt(\n    channel_id,\n) -> str:\n    signal = get_channel_signal(\n        channel_id\n    )\n\n    return "\\n".join(\n        [\n            (\n                "[SERVER AWARENESS "\n                f"v{SERVER_AWARENESS_VERSION}]"\n            ),\n            (\n                "Strukturelle Discord-Situation; "\n                "keine Fakten über konkrete Personen erfinden."\n            ),\n            (\n                f"- channel activity: "\n                f"{signal[\'activity\']}"\n            ),\n            (\n                f"- active crowd: "\n                f"{signal[\'crowd\']}"\n            ),\n            (\n                f"- Evilnae social pull: "\n                f"{_level(signal[\'social_pull\'])}"\n            ),\n            (\n                f"- Evilnae speaking pressure: "\n                f"{_level(signal[\'bot_pressure\'])}"\n            ),\n            (\n                f"- initiative opportunity: "\n                f"{_level(signal[\'initiative_opportunity\'])}"\n            ),\n            (\n                f"- sensitive atmosphere recently: "\n                f"{\'yes\' if signal[\'sensitive_recent\'] else \'no\'}"\n            ),\n            (\n                "HARD RULES: Server Awareness bestimmt nur "\n                "Timing/Beteiligung. Es ist kein Conversation World "\n                "und keine Faktenquelle über User."\n            ),\n        ]\n    )\n\n\ndef server_awareness_stats() -> dict:\n    now = time.time()\n\n    with _LOCK:\n        data = _load()\n\n        _prune(\n            data,\n            now=now,\n        )\n\n    channels = data.get(\n        "channels",\n        {},\n    )\n\n    events = data.get(\n        "events",\n        [],\n    )\n\n    active_channels = {\n        item.get(\n            "channel_id"\n        )\n        for item in events\n        if now\n        -\n        float(\n            item.get(\n                "timestamp",\n                0.0,\n            )\n            or 0.0\n        )\n        <= 60 * 60\n    }\n\n    return {\n        "version": SERVER_AWARENESS_VERSION,\n        "channels": len(\n            channels\n        ),\n        "active_channels_1h": len(\n            {\n                item\n                for item\n                in active_channels\n                if item\n            }\n        ),\n        "events_24h": len(\n            events\n        ),\n    }\n\n\ndef format_server_awareness_debug(\n    channel_id=None,\n) -> str:\n    if channel_id:\n        signal = get_channel_signal(\n            channel_id\n        )\n\n        return (\n            "[SERVER AWARENESS] "\n            f"v={SERVER_AWARENESS_VERSION} "\n            f"channel={channel_id} "\n            f"activity={signal[\'activity\']} "\n            f"crowd={signal[\'crowd\']} "\n            f"pull={signal[\'social_pull\']:.2f} "\n            f"bot_pressure={signal[\'bot_pressure\']:.2f} "\n            f"initiative={signal[\'initiative_opportunity\']:.2f}"\n        )\n\n    stats = server_awareness_stats()\n\n    return (\n        "[SERVER AWARENESS] "\n        f"v={SERVER_AWARENESS_VERSION} "\n        f"channels={stats[\'channels\']} "\n        f"active_1h={stats[\'active_channels_1h\']} "\n        f"events_24h={stats[\'events_24h\']}"\n    )\n\n\ndef _self_test() -> int:\n    global SERVER_AWARENESS_PATH\n\n    import tempfile\n\n    original = SERVER_AWARENESS_PATH\n    tests = []\n\n    try:\n        with tempfile.TemporaryDirectory() as tmp:\n            SERVER_AWARENESS_PATH = (\n                Path(tmp)\n                /\n                "server.json"\n            )\n\n            now = time.time()\n\n            result = observe_message_metadata(\n                guild_id="g1",\n                channel_id="c1",\n                channel_name="general",\n                user_id="u1",\n                text=(\n                    "Evil was denkst du über das? xD"\n                ),\n                message_id="m1",\n                timestamp=now,\n                direct=True,\n            )\n\n            tests.append(\n                (\n                    "message observed",\n                    result[\n                        "saved"\n                    ],\n                )\n            )\n\n            duplicate = observe_message_metadata(\n                guild_id="g1",\n                channel_id="c1",\n                channel_name="general",\n                user_id="u1",\n                text="same raw text",\n                message_id="m1",\n                timestamp=now + 1,\n                direct=True,\n            )\n\n            tests.append(\n                (\n                    "message dedupe",\n                    duplicate[\n                        "reason"\n                    ]\n                    ==\n                    "duplicate_event",\n                )\n            )\n\n            raw = (\n                SERVER_AWARENESS_PATH.read_text(\n                    encoding="utf-8"\n                )\n            )\n\n            tests.append(\n                (\n                    "raw text not persisted",\n                    "was denkst du"\n                    not in raw\n                    and\n                    "same raw text"\n                    not in raw,\n                )\n            )\n\n            observe_message_metadata(\n                guild_id="g1",\n                channel_id="c2",\n                channel_name="gaming",\n                user_id="u2",\n                text="hallo leute",\n                message_id="m2",\n                timestamp=now,\n            )\n\n            tests.append(\n                (\n                    "multiple channels known",\n                    server_awareness_stats()[\n                        "channels"\n                    ]\n                    ==\n                    2,\n                )\n            )\n\n            register_bot_message(\n                channel_id="c1",\n                kind="reply",\n                timestamp=now + 2,\n            )\n\n            signal = get_channel_signal(\n                "c1",\n                now=now + 3,\n            )\n\n            tests.append(\n                (\n                    "Evilnae reference raises social pull",\n                    signal[\n                        "social_pull"\n                    ]\n                    >\n                    0.0,\n                )\n            )\n\n            tests.append(\n                (\n                    "recent bot raises bot pressure",\n                    signal[\n                        "bot_pressure"\n                    ]\n                    >\n                    0.40,\n                )\n            )\n\n            observe_message_metadata(\n                guild_id="g1",\n                channel_id="c3",\n                channel_name="care",\n                user_id="u3",\n                text="ich hab Kopfschmerzen",\n                message_id="m3",\n                timestamp=now,\n            )\n\n            care_signal = get_channel_signal(\n                "c3",\n                now=now + 10,\n            )\n\n            tests.append(\n                (\n                    "sensitive atmosphere detected",\n                    care_signal[\n                        "sensitive_recent"\n                    ],\n                )\n            )\n\n            prompt = (\n                format_server_awareness_for_prompt(\n                    "c1"\n                )\n            )\n\n            tests.append(\n                (\n                    "prompt has structural state",\n                    "channel activity:"\n                    in prompt\n                    and\n                    "speaking pressure:"\n                    in prompt,\n                )\n            )\n\n            tests.append(\n                (\n                    "prompt has no raw message",\n                    "was denkst du"\n                    not in prompt,\n                )\n            )\n\n    finally:\n        SERVER_AWARENESS_PATH = (\n            original\n        )\n\n    passed = sum(\n        1\n        for _, success\n        in tests\n        if success\n    )\n\n    print()\n    print("=" * 64)\n    print(\n        f"SERVER AWARENESS "\n        f"v{SERVER_AWARENESS_VERSION} TEST"\n    )\n    print("=" * 64)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
AGENCY_V2_SOURCE = 'from __future__ import annotations\n\nimport contextvars\nimport functools\nimport random\nimport re\n\nimport initiative as initiative_module\n\nfrom agency import (\n    AgencyResult,\n    ACTION_REPLY,\n    ACTION_STAY_SILENT,\n    MODE_DIRECT,\n    MODE_CONTINUATION,\n    MODE_PARTICIPATION,\n)\n\nfrom participation import (\n    ParticipationDecision,\n)\n\nfrom server_awareness import (\n    get_channel_signal,\n    format_server_awareness_for_prompt,\n)\n\n\nAGENCY_INITIATIVE_V2_VERSION = "2.0"\n\n_CURRENT_MESSAGE_CHANNEL = (\n    contextvars.ContextVar(\n        "evilnae_agency_message_channel",\n        default="",\n    )\n)\n\n_CURRENT_INITIATIVE_CHANNEL = (\n    contextvars.ContextVar(\n        "evilnae_agency_initiative_channel",\n        default="",\n    )\n)\n\n\ndef set_message_channel_context(\n    channel_id,\n) -> None:\n    _CURRENT_MESSAGE_CHANNEL.set(\n        str(\n            channel_id\n            or ""\n        )\n    )\n\n\ndef set_initiative_channel_context(\n    channel_id,\n) -> None:\n    _CURRENT_INITIATIVE_CHANNEL.set(\n        str(\n            channel_id\n            or ""\n        )\n    )\n\n\ndef _is_question(\n    text: str,\n) -> bool:\n    value = str(\n        text\n        or ""\n    )\n\n    return bool(\n        "?"\n        in value\n        or re.search(\n            r"^\\s*(?:was|wer|wie|warum|wieso|wann|wo|"\n            r"welche|welcher|welches|kann|kannst|hast|bist|"\n            r"magst|meinst|denkst|findest)\\b",\n            value,\n            flags=re.I,\n        )\n    )\n\n\ndef _evilnae_relevant(\n    text: str,\n) -> bool:\n    return bool(\n        re.search(\n            r"\\b(?:evilnae|evil)\\b",\n            str(\n                text\n                or ""\n            ),\n            flags=re.I,\n        )\n    )\n\n\ndef adjust_agency_result_v2(\n    result,\n    *,\n    conversation_mode,\n    user_text,\n    signal,\n):\n    """\n    Agency 2.0 does not make Evilnae disappear from direct address.\n\n    It mainly prevents her from compulsively extending low-value\n    continuations when she has already dominated the channel.\n    """\n\n    mode = str(\n        conversation_mode\n        or ""\n    ).lower()\n\n    if mode in {\n        MODE_DIRECT,\n        MODE_PARTICIPATION,\n    }:\n        return result\n\n    if (\n        mode\n        ==\n        MODE_CONTINUATION\n        and\n        getattr(\n            result,\n            "action",\n            ACTION_REPLY,\n        )\n        ==\n        ACTION_REPLY\n    ):\n        word_count = len(\n            re.findall(\n                r"[A-Za-zÄÖÜäöüß0-9]+",\n                str(\n                    user_text\n                    or ""\n                ),\n            )\n        )\n\n        if (\n            float(\n                signal.get(\n                    "bot_pressure",\n                    0.0,\n                )\n                or 0.0\n            )\n            >=\n            0.72\n            and\n            word_count <= 5\n            and\n            not _is_question(\n                user_text\n            )\n            and\n            not _evilnae_relevant(\n                user_text\n            )\n        ):\n            return AgencyResult(\n                action=(\n                    ACTION_STAY_SILENT\n                ),\n                reaction=None,\n                overridden=True,\n                reason=(\n                    "agency_v2_bot_pressure"\n                ),\n                conversation_mode=mode,\n            )\n\n    return result\n\n\ndef wrap_agency_guard_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        result = original(\n            *args,\n            **kwargs,\n        )\n\n        channel_id = (\n            _CURRENT_MESSAGE_CHANNEL.get()\n        )\n\n        if not channel_id:\n            return result\n\n        signal = get_channel_signal(\n            channel_id\n        )\n\n        return adjust_agency_result_v2(\n            result,\n            conversation_mode=str(\n                kwargs.get(\n                    "conversation_mode",\n                    "",\n                )\n                or ""\n            ),\n            user_text=str(\n                kwargs.get(\n                    "user_text",\n                    "",\n                )\n                or ""\n            ),\n            signal=signal,\n        )\n\n    return wrapped\n\n\ndef _participation_should_hard_silence(\n    *,\n    signal,\n    current_message,\n) -> bool:\n    if _evilnae_relevant(\n        current_message\n    ):\n        return False\n\n    if _is_question(\n        current_message\n    ):\n        # A question to somebody else still goes through the normal\n        # Participation Brain; we do not assume it is for Evilnae.\n        return False\n\n    bot_pressure = float(\n        signal.get(\n            "bot_pressure",\n            0.0,\n        )\n        or 0.0\n    )\n\n    social_pull = float(\n        signal.get(\n            "social_pull",\n            0.0,\n        )\n        or 0.0\n    )\n\n    if (\n        bot_pressure >= 0.68\n        and\n        social_pull < 0.28\n    ):\n        return True\n\n    return False\n\n\ndef wrap_participation_brain_server_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    async def wrapped(\n        *args,\n        **kwargs,\n    ):\n        channel_id = (\n            _CURRENT_MESSAGE_CHANNEL.get()\n        )\n\n        current_message = str(\n            kwargs.get(\n                "current_message",\n                "",\n            )\n            or ""\n        )\n\n        if not channel_id:\n            return await original(\n                *args,\n                **kwargs,\n            )\n\n        signal = get_channel_signal(\n            channel_id\n        )\n\n        if _participation_should_hard_silence(\n            signal=signal,\n            current_message=(\n                current_message\n            ),\n        ):\n            print(\n                "[AGENCY V2] "\n                "participation suppressed "\n                "reason=bot_pressure"\n            )\n\n            return ParticipationDecision(\n                action="stay_silent",\n                confidence="high",\n                relevance=0.10,\n                social_value=0.05,\n                conversation_involvement=0.10,\n                reason=(\n                    "agency_v2_bot_pressure"\n                ),\n                response_goal="",\n                notes=[\n                    "server_awareness",\n                ],\n            )\n\n        kwargs = dict(\n            kwargs\n        )\n\n        base_context = str(\n            kwargs.get(\n                "channel_context",\n                "",\n            )\n            or ""\n        ).strip()\n\n        server_context = (\n            format_server_awareness_for_prompt(\n                channel_id\n            )\n        )\n\n        kwargs[\n            "channel_context"\n        ] = (\n            (\n                base_context\n                +\n                "\\n\\n"\n                +\n                server_context\n            )\n            if base_context\n            else server_context\n        )\n\n        return await original(\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n\ndef compute_initiative_score_v2(\n    inner_state,\n    signal,\n) -> float:\n    base = (\n        initiative_module\n        .calculate_initiative_score(\n            inner_state\n        )\n    )\n\n    opportunity = float(\n        signal.get(\n            "initiative_opportunity",\n            0.0,\n        )\n        or 0.0\n    )\n\n    social_pull = float(\n        signal.get(\n            "social_pull",\n            0.0,\n        )\n        or 0.0\n    )\n\n    bot_pressure = float(\n        signal.get(\n            "bot_pressure",\n            0.0,\n        )\n        or 0.0\n    )\n\n    score = (\n        base\n        +\n        opportunity * 0.24\n        +\n        social_pull * 0.08\n        -\n        bot_pressure * 0.32\n    )\n\n    if bool(\n        signal.get(\n            "sensitive_recent",\n            False,\n        )\n    ):\n        score -= 0.22\n\n    return max(\n        0.0,\n        min(\n            1.0,\n            score,\n        ),\n    )\n\n\ndef wrap_should_initiate_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        inner_state,\n    ):\n        channel_id = (\n            _CURRENT_INITIATIVE_CHANNEL.get()\n        )\n\n        if not channel_id:\n            return original(\n                inner_state\n            )\n\n        allowed, reason = (\n            initiative_module\n            .can_initiate()\n        )\n\n        if not allowed:\n            return (\n                False,\n                reason,\n                0.0,\n            )\n\n        silence_ok, silence_reason = (\n            initiative_module\n            .channel_silence_is_suitable()\n        )\n\n        if not silence_ok:\n            return (\n                False,\n                silence_reason,\n                0.0,\n            )\n\n        signal = get_channel_signal(\n            channel_id\n        )\n\n        if (\n            float(\n                signal.get(\n                    "bot_pressure",\n                    0.0,\n                )\n                or 0.0\n            )\n            >=\n            0.70\n        ):\n            return (\n                False,\n                "agency_v2_bot_pressure",\n                0.0,\n            )\n\n        if bool(\n            signal.get(\n                "sensitive_recent",\n                False,\n            )\n        ):\n            return (\n                False,\n                "agency_v2_sensitive_atmosphere",\n                0.0,\n            )\n\n        score = compute_initiative_score_v2(\n            inner_state,\n            signal,\n        )\n\n        if score < 0.43:\n            return (\n                False,\n                "agency_v2_score_too_low",\n                score,\n            )\n\n        probability = min(\n            0.72,\n            max(\n                0.12,\n                score\n                +\n                float(\n                    signal.get(\n                        "initiative_opportunity",\n                        0.0,\n                    )\n                    or 0.0\n                )\n                *\n                0.10,\n            ),\n        )\n\n        if random.random() > probability:\n            return (\n                False,\n                "agency_v2_random_gate",\n                score,\n            )\n\n        return (\n            True,\n            "agency_v2_allowed",\n            score,\n        )\n\n    return wrapped\n\n\ndef wrap_choose_initiative_type_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        inner_state,\n    ):\n        channel_id = (\n            _CURRENT_INITIATIVE_CHANNEL.get()\n        )\n\n        if not channel_id:\n            return original(\n                inner_state\n            )\n\n        signal = get_channel_signal(\n            channel_id\n        )\n\n        refs = int(\n            signal.get(\n                "evilnae_refs_15m",\n                0,\n            )\n            or 0\n        )\n\n        social_pull = float(\n            signal.get(\n                "social_pull",\n                0.0,\n            )\n            or 0.0\n        )\n\n        crowd = str(\n            signal.get(\n                "crowd",\n                "quiet",\n            )\n        )\n\n        if refs >= 2:\n            return "callback_thought"\n\n        if (\n            crowd\n            in {\n                "group",\n                "crowd",\n            }\n            and\n            social_pull >= 0.20\n        ):\n            return "community_comment"\n\n        if social_pull >= 0.30:\n            return "ongoing_topic"\n\n        return original(\n            inner_state\n        )\n\n    return wrapped\n\n\ndef wrap_initiative_prompt_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        requested_type = str(\n            kwargs.get(\n                "initiative_type",\n                "",\n            )\n            or ""\n        )\n\n        base_type = (\n            requested_type\n        )\n\n        special = ""\n\n        if requested_type == "callback_thought":\n            base_type = "curious_comment"\n            special = (\n                "Der Channel hat Evilnae kürzlich mehrfach sozial "\n                "einbezogen. Sie darf einen natürlichen Callback "\n                "auf den laufenden Vibe machen, aber keine alte "\n                "Antwort kopieren und niemanden zwanghaft pingen."\n            )\n\n        elif requested_type == "community_comment":\n            base_type = "social_pingless_comment"\n            special = (\n                "Mehrere Personen waren zuletzt aktiv. Die Nachricht "\n                "soll wie ein eigener Community-Kommentar wirken, "\n                "nicht wie Moderation und nicht wie eine Rundfrage."\n            )\n\n        elif requested_type == "ongoing_topic":\n            base_type = "curious_comment"\n            special = (\n                "Es gibt noch sozialen Pull aus dem jüngeren Gespräch. "\n                "Nur einen tatsächlich vorhandenen Hook aus dem "\n                "Channel-Kontext aufgreifen; nichts erfinden."\n            )\n\n        kwargs = dict(\n            kwargs\n        )\n\n        kwargs[\n            "initiative_type"\n        ] = base_type\n\n        prompt = original(\n            *args,\n            **kwargs,\n        )\n\n        channel_id = (\n            _CURRENT_INITIATIVE_CHANNEL.get()\n        )\n\n        server_context = (\n            format_server_awareness_for_prompt(\n                channel_id\n            )\n            if channel_id\n            else (\n                "[SERVER AWARENESS]\\n"\n                "Kein Channel-Signal verfügbar."\n            )\n        )\n\n        return (\n            str(\n                prompt\n                or ""\n            )\n            +\n            "\\n\\n"\n            +\n            "==================================================\\n"\n            "AGENCY / INITIATIVE 2.0\\n"\n            "==================================================\\n\\n"\n            +\n            server_context\n            +\n            "\\n\\n"\n            +\n            (\n                "Spezifischer Initiative-Impuls:\\n"\n                +\n                special\n                +\n                "\\n\\n"\n                if special\n                else ""\n            )\n            +\n            "Die Initiative soll einen echten Grund haben. "\n            "Wenn Server Awareness sagt, dass Evilnae schon viel "\n            "geredet hat oder die Stimmung sensibel ist, lieber "\n            "NO_INITIATIVE. Keine künstliche Aktivität nur weil "\n            "der Timer ausgelöst hat."\n        )\n\n    return wrapped\n\n\ndef _self_test() -> int:\n    tests = []\n\n    direct = AgencyResult(\n        action=ACTION_REPLY,\n        reason="direct_reply",\n        conversation_mode=(\n            MODE_DIRECT\n        ),\n    )\n\n    adjusted = adjust_agency_result_v2(\n        direct,\n        conversation_mode=(\n            MODE_DIRECT\n        ),\n        user_text="Evil?",\n        signal={\n            "bot_pressure": 1.0,\n        },\n    )\n\n    tests.append(\n        (\n            "direct address never suppressed",\n            adjusted.action\n            ==\n            ACTION_REPLY,\n        )\n    )\n\n    continuation = AgencyResult(\n        action=ACTION_REPLY,\n        reason="brain_reply",\n        conversation_mode=(\n            MODE_CONTINUATION\n        ),\n    )\n\n    adjusted = adjust_agency_result_v2(\n        continuation,\n        conversation_mode=(\n            MODE_CONTINUATION\n        ),\n        user_text="ja genau",\n        signal={\n            "bot_pressure": 0.90,\n        },\n    )\n\n    tests.append(\n        (\n            "high bot pressure suppresses low-value continuation",\n            adjusted.action\n            ==\n            ACTION_STAY_SILENT,\n        )\n    )\n\n    adjusted_question = (\n        adjust_agency_result_v2(\n            continuation,\n            conversation_mode=(\n                MODE_CONTINUATION\n            ),\n            user_text=(\n                "wie meinst du das?"\n            ),\n            signal={\n                "bot_pressure": 0.90,\n            },\n        )\n    )\n\n    tests.append(\n        (\n            "question survives bot-pressure guard",\n            adjusted_question.action\n            ==\n            ACTION_REPLY,\n        )\n    )\n\n    tests.append(\n        (\n            "participation hard silence for overtalking",\n            _participation_should_hard_silence(\n                signal={\n                    "bot_pressure": 0.80,\n                    "social_pull": 0.10,\n                },\n                current_message=(\n                    "ja das ist schon wild"\n                ),\n            ),\n        )\n    )\n\n    tests.append(\n        (\n            "Evilnae reference bypasses participation silence",\n            not _participation_should_hard_silence(\n                signal={\n                    "bot_pressure": 0.80,\n                    "social_pull": 0.10,\n                },\n                current_message=(\n                    "Evil ist heute echt wild"\n                ),\n            ),\n        )\n    )\n\n    class State:\n        curiosity = 0.65\n        boredom = 0.55\n        social_energy = 0.65\n        chaos_drive = 0.50\n        irritation = 0.05\n        energy = 0.70\n\n    base = (\n        initiative_module\n        .calculate_initiative_score(\n            State()\n        )\n    )\n\n    boosted = compute_initiative_score_v2(\n        State(),\n        {\n            "initiative_opportunity": 0.80,\n            "social_pull": 0.50,\n            "bot_pressure": 0.05,\n            "sensitive_recent": False,\n        },\n    )\n\n    tests.append(\n        (\n            "server opportunity can raise initiative score",\n            boosted\n            >\n            base,\n        )\n    )\n\n    suppressed = compute_initiative_score_v2(\n        State(),\n        {\n            "initiative_opportunity": 0.20,\n            "social_pull": 0.10,\n            "bot_pressure": 0.90,\n            "sensitive_recent": True,\n        },\n    )\n\n    tests.append(\n        (\n            "bot pressure and sensitivity lower initiative score",\n            suppressed\n            <\n            base,\n        )\n    )\n\n    passed = sum(\n        1\n        for _, success\n        in tests\n        if success\n    )\n\n    print()\n    print("=" * 64)\n    print(\n        f"AGENCY / INITIATIVE "\n        f"v{AGENCY_INITIATIVE_V2_VERSION} TEST"\n    )\n    print("=" * 64)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
BOT_VERSION_OLD = 'BOT_VERSION = "3.9.0-self-development-arcs"'
BOT_VERSION_NEW = 'BOT_VERSION = "4.0.0-agency-server-awareness"'
LIVE_VERSION_OLD = 'LIVE_STABILITY_VERSION = "1.3-self-development"'
LIVE_VERSION_NEW = 'LIVE_STABILITY_VERSION = "1.4-agency-server-awareness"'
AGENCY_VERSION_OLD = 'AGENCY_VERSION = "1.0"'
AGENCY_VERSION_NEW = 'AGENCY_VERSION = "2.0-server-aware"'
INIT_VERSION_OLD = 'INITIATIVE_VERSION = "1.0"'
INIT_VERSION_NEW = 'INITIATIVE_VERSION = "2.0-server-aware"'
SERVER_IMPORT = '\nfrom server_awareness import (\n    SERVER_AWARENESS_VERSION,\n    observe_discord_message,\n    register_bot_message as register_server_bot_message,\n    server_awareness_stats,\n    format_server_awareness_debug,\n)\n\nfrom agency_initiative_v2 import (\n    AGENCY_INITIATIVE_V2_VERSION,\n    set_message_channel_context,\n    set_initiative_channel_context,\n    wrap_agency_guard_v2,\n    wrap_participation_brain_server_v2,\n    wrap_should_initiate_v2,\n    wrap_choose_initiative_type_v2,\n    wrap_initiative_prompt_v2,\n)\n\n'
AGENCY_IMPORT_MARKER = 'from agency import (\n    AGENCY_VERSION,\n    ACTION_REPLY,\n    ACTION_REACT,\n    ACTION_STAY_SILENT,\n    apply_agency_guard,\n    format_agency_debug,\n)\n\n'
WRAP_ASSIGNMENTS = '\n# =========================================================\n# 4.0.0 AGENCY / INITIATIVE 2.0 WRAPPERS\n# =========================================================\n\napply_agency_guard = wrap_agency_guard_v2(\n    apply_agency_guard\n)\n\nrun_participation_brain = (\n    wrap_participation_brain_server_v2(\n        run_participation_brain\n    )\n)\n\nshould_initiate = wrap_should_initiate_v2(\n    should_initiate\n)\n\nchoose_initiative_type = (\n    wrap_choose_initiative_type_v2(\n        choose_initiative_type\n    )\n)\n\nbuild_initiative_prompt = (\n    wrap_initiative_prompt_v2(\n        build_initiative_prompt\n    )\n)\n\n\n'
BOT_ASSIGN_MARKER = 'build_initiative_prompt = (\n    wrap_initiative_prompt_v3(\n        build_initiative_prompt\n    )\n)\n\n\n'
RAW_OBSERVE_MARKER = '    # -----------------------------------------------------\n    # CHANNEL LIMIT\n    # -----------------------------------------------------\n\n'
RAW_OBSERVE_BLOCK = '    # =====================================================\n    # 4.0 SERVER AWARENESS — METADATA ONLY\n    # =====================================================\n    #\n    # Runs BEFORE the response-channel limit so Evilnae can know\n    # whether the wider server is quiet/active/crowded without\n    # replying outside ALLOWED_CHANNEL_ID.\n    #\n    # Persistent state stores no raw Discord message text.\n    # =====================================================\n\n    try:\n        observe_discord_message(\n            message,\n            bot_user_id=(\n                str(bot.user.id)\n                if bot.user\n                else None\n            ),\n        )\n    except Exception as error:\n        print(\n            "[SERVER AWARENESS ERROR] "\n            f"{type(error).__name__}: {error}"\n        )\n\n'
PERCEPTION_CONTEXT_MARKER = '    print(\n        format_perception_debug(\n            perception\n        )\n    )\n\n    channel_id = (\n        perception.channel_id\n    )\n'
PERCEPTION_CONTEXT_NEW = '    print(\n        format_perception_debug(\n            perception\n        )\n    )\n\n    set_message_channel_context(\n        perception.channel_id\n    )\n\n    channel_id = (\n        perception.channel_id\n    )\n'
INIT_CONTEXT_MARKER = 'async def generate_initiative_message(\n    *,\n    channel_id\n):\n\n    apply_time_decay()\n'
INIT_CONTEXT_NEW = 'async def generate_initiative_message(\n    *,\n    channel_id\n):\n\n    set_initiative_channel_context(\n        channel_id\n    )\n\n    apply_time_decay()\n'
BOT_CONTEXT_PATCHES = [('def add_channel_bot_message(\n    channel_id,\n    user_id,\n    username,\n    answer\n):\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'def add_channel_bot_message(\n    channel_id,\n    user_id,\n    username,\n    answer\n):\n\n    register_server_bot_message(\n        channel_id=channel_id,\n        kind="reply",\n    )\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'Normal replies update Server Awareness'), ('def add_channel_continuation_message(\n    channel_id,\n    user_id,\n    username,\n    answer\n):\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'def add_channel_continuation_message(\n    channel_id,\n    user_id,\n    username,\n    answer\n):\n\n    register_server_bot_message(\n        channel_id=channel_id,\n        kind="continuation",\n    )\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'Continuation replies update Server Awareness'), ('def add_channel_participation_message(\n    channel_id,\n    answer\n):\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'def add_channel_participation_message(\n    channel_id,\n    answer\n):\n\n    register_server_bot_message(\n        channel_id=channel_id,\n        kind="participation",\n    )\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'Participation replies update Server Awareness'), ('def add_channel_initiative_message(\n    channel_id,\n    answer\n):\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'def add_channel_initiative_message(\n    channel_id,\n    answer\n):\n\n    register_server_bot_message(\n        channel_id=channel_id,\n        kind="initiative",\n    )\n\n    context = (\n        get_channel_context(\n            channel_id\n        )\n    )\n', 'Initiatives update Server Awareness')]
STARTUP_AGENCY_OLD = '    print(\n        f"Response Agency v"\n        f"{AGENCY_VERSION}: ACTIVE"\n    )\n'
STARTUP_AGENCY_NEW = '    print(\n        f"Response Agency v"\n        f"{AGENCY_VERSION}: ACTIVE"\n    )\n\n    awareness_state = (\n        server_awareness_stats()\n    )\n\n    print(\n        f"Server Awareness v"\n        f"{SERVER_AWARENESS_VERSION}: ACTIVE "\n        f"channels={awareness_state.get(\'channels\', 0)} "\n        f"active_1h={awareness_state.get(\'active_channels_1h\', 0)}"\n    )\n\n    print(\n        f"Agency / Initiative v"\n        f"{AGENCY_INITIATIVE_V2_VERSION}: ACTIVE"\n    )\n'
AUTONOMY_LABEL_OLD = '    print(\n        "Autonomy / Initiative v1: ACTIVE"\n    )\n'
AUTONOMY_LABEL_NEW = '    print(\n        "Autonomy / Initiative v2: ACTIVE"\n    )\n'
LIVE_COMPACT_OLD = '            "Self Development v",\n            "Qwen Surface Writer v",\n'
LIVE_COMPACT_NEW = '            "Self Development v",\n            "Server Awareness v",\n            "Agency / Initiative v",\n            "Response Agency v",\n            "Qwen Surface Writer v",\n'


def ok(text):
    print(
        f"[OK] {text}"
    )


def fail(text):
    print()
    print(
        f"[INSTALL ERROR] {text}"
    )
    print(
        "Nothing was overwritten by this installer."
    )
    raise SystemExit(
        1
    )


def replace_once(
    text,
    old,
    new,
    label,
):
    count = text.count(
        old
    )

    if count != 1:
        fail(
            f"{label}: expected exactly 1 match, "
            f"found {count}"
        )

    ok(label)

    return text.replace(
        old,
        new,
        1,
    )


def insert_before_once(
    text,
    marker,
    block,
    label,
):
    count = text.count(
        marker
    )

    if count != 1:
        fail(
            f"{label}: expected exactly 1 marker, "
            f"found {count}"
        )

    ok(label)

    return text.replace(
        marker,
        block
        +
        marker,
        1,
    )


def insert_after_once(
    text,
    marker,
    block,
    label,
):
    count = text.count(
        marker
    )

    if count != 1:
        fail(
            f"{label}: expected exactly 1 marker, "
            f"found {count}"
        )

    ok(label)

    return text.replace(
        marker,
        marker
        +
        block,
        1,
    )


def syntax_check(
    text,
    filename,
):
    try:
        ast.parse(
            text,
            filename=filename,
        )

    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch "
            f"line {error.lineno}: {error.msg}"
        )

    ok(
        f"{filename} syntax check"
    )


print("=" * 78)
print(
    "EVILNAE 4.0.0 — AGENCY / INITIATIVE 2.0 + SERVER AWARENESS"
)
print("=" * 78)
print(
    f"Project: {PROJECT_ROOT}"
)
print()
print(
    "WICHTIG: bot.py muss vollständig AUS sein."
)
print()


for path in (
    BOT_PATH,
    LIVE_PATH,
    AGENCY_PATH,
    INITIATIVE_PATH,
):
    if not path.exists():
        fail(
            f"Missing required file: {path.name}"
        )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)

live = LIVE_PATH.read_text(
    encoding="utf-8"
)

agency = AGENCY_PATH.read_text(
    encoding="utf-8"
)

initiative = INITIATIVE_PATH.read_text(
    encoding="utf-8"
)


if (
    BOT_VERSION_NEW in bot
    and
    SERVER_PATH.exists()
    and
    AGENCY_V2_PATH.exists()
):
    print(
        "4.0.0 is already installed."
    )
    raise SystemExit(
        0
    )


if BOT_VERSION_OLD not in bot:
    fail(
        "Expected Bot 3.9.0-self-development-arcs"
    )


if LIVE_VERSION_OLD not in live:
    fail(
        "Expected Live Stability 1.3-self-development"
    )


if (
    'SELF_DEVELOPMENT_VERSION = "1.0"'
    not in
    (
        PROJECT_ROOT
        /
        "self_development.py"
    ).read_text(
        encoding="utf-8"
    )
):
    fail(
        "Expected Self Development v1.0"
    )


if (
    'EXPERIENCE_LEARNING_VERSION = "2.0.1-evidence-fix"'
    not in
    (
        PROJECT_ROOT
        /
        "experience_learning.py"
    ).read_text(
        encoding="utf-8"
    )
):
    fail(
        "Expected Experience Learning 2.0.1-evidence-fix"
    )


if AGENCY_VERSION_OLD not in agency:
    fail(
        "Expected Agency v1.0"
    )


if INIT_VERSION_OLD not in initiative:
    fail(
        "Expected Initiative v1.0"
    )


if (
    SERVER_PATH.exists()
    or
    AGENCY_V2_PATH.exists()
):
    fail(
        "4.0 runtime module already exists unexpectedly."
    )


ok(
    "3.9.0 architecture base detected"
)


# =========================================================
# PATCH VERSIONS
# =========================================================

agency = replace_once(
    agency,
    AGENCY_VERSION_OLD,
    AGENCY_VERSION_NEW,
    "Agency -> 2.0-server-aware",
)


initiative = replace_once(
    initiative,
    INIT_VERSION_OLD,
    INIT_VERSION_NEW,
    "Initiative -> 2.0-server-aware",
)


live = replace_once(
    live,
    LIVE_VERSION_OLD,
    LIVE_VERSION_NEW,
    "Live Stability -> 1.4-agency-server-awareness",
)


live = replace_once(
    live,
    LIVE_COMPACT_OLD,
    LIVE_COMPACT_NEW,
    "Compact Console allows Phase-E startup",
)


# =========================================================
# PATCH BOT IMPORTS / WRAPPERS
# =========================================================

bot = replace_once(
    bot,
    BOT_VERSION_OLD,
    BOT_VERSION_NEW,
    "Bot version -> 4.0.0-agency-server-awareness",
)


bot = insert_after_once(
    bot,
    AGENCY_IMPORT_MARKER,
    SERVER_IMPORT,
    "Bot imports Server Awareness + Agency 2.0",
)


bot = insert_after_once(
    bot,
    BOT_ASSIGN_MARKER,
    WRAP_ASSIGNMENTS,
    "Bot installs Agency / Initiative 2.0 wrappers",
)


bot = insert_before_once(
    bot,
    RAW_OBSERVE_MARKER,
    RAW_OBSERVE_BLOCK,
    "Server-wide metadata observation before channel response gate",
)


bot = replace_once(
    bot,
    PERCEPTION_CONTEXT_MARKER,
    PERCEPTION_CONTEXT_NEW,
    "Current response channel feeds Agency 2.0 context",
)


bot = replace_once(
    bot,
    INIT_CONTEXT_MARKER,
    INIT_CONTEXT_NEW,
    "Initiative target channel feeds Initiative 2.0 context",
)


for old, new, label in BOT_CONTEXT_PATCHES:
    bot = replace_once(
        bot,
        old,
        new,
        label,
    )


bot = replace_once(
    bot,
    STARTUP_AGENCY_OLD,
    STARTUP_AGENCY_NEW,
    "Startup Server Awareness + Agency / Initiative 2.0 banner",
)


bot = replace_once(
    bot,
    AUTONOMY_LABEL_OLD,
    AUTONOMY_LABEL_NEW,
    "Startup Autonomy label -> v2",
)


# =========================================================
# PRE-WRITE INVARIANTS
# =========================================================

for marker in (
    'SERVER_AWARENESS_VERSION = "1.0"',
    "evilnae_server_awareness.json",
    "observe_discord_message",
    "get_channel_signal",
    "initiative_opportunity",
    "raw Discord message text",
):
    if marker not in SERVER_SOURCE:
        fail(
            f"server_awareness.py missing invariant: {marker}"
        )


for marker in (
    'AGENCY_INITIATIVE_V2_VERSION = "2.0"',
    "adjust_agency_result_v2",
    "wrap_participation_brain_server_v2",
    "compute_initiative_score_v2",
    "wrap_should_initiate_v2",
    "wrap_choose_initiative_type_v2",
    "wrap_initiative_prompt_v2",
):
    if marker not in AGENCY_V2_SOURCE:
        fail(
            f"agency_initiative_v2.py missing invariant: {marker}"
        )


for marker in (
    BOT_VERSION_NEW,
    "observe_discord_message",
    "wrap_agency_guard_v2",
    "wrap_should_initiate_v2",
    "set_initiative_channel_context",
    "register_server_bot_message",
    "Server Awareness v",
    "Agency / Initiative v",
):
    if marker not in bot:
        fail(
            f"Patched bot.py missing invariant: {marker}"
        )


for marker in (
    LIVE_VERSION_NEW,
    '"Server Awareness v"',
    '"Agency / Initiative v"',
):
    if marker not in live:
        fail(
            f"Patched live_stability.py missing invariant: {marker}"
        )


syntax_check(
    SERVER_SOURCE,
    "server_awareness.py",
)

syntax_check(
    AGENCY_V2_SOURCE,
    "agency_initiative_v2.py",
)

syntax_check(
    agency,
    "agency.py",
)

syntax_check(
    initiative,
    "initiative.py",
)

syntax_check(
    live,
    "live_stability.py",
)

syntax_check(
    bot,
    "bot.py",
)


# =========================================================
# CONTRACT TESTS
# =========================================================

contract_tests = {
    "no new OpenAI call":
        (
            "AsyncOpenAI"
            not in SERVER_SOURCE
            and
            "AsyncOpenAI"
            not in AGENCY_V2_SOURCE
            and
            "openai_client"
            not in SERVER_SOURCE
            and
            "openai_client"
            not in AGENCY_V2_SOURCE
        ),

    "no new Qwen call":
        (
            "run_local_model"
            not in SERVER_SOURCE
            and
            "run_local_model"
            not in AGENCY_V2_SOURCE
        ),

    "server-wide observation before allowed channel gate":
        (
            bot.index(
                "observe_discord_message("
            )
            <
            bot.index(
                "# CHANNEL LIMIT"
            )
        ),

    "no response permission widening":
        (
            "if ALLOWED_CHANNEL_ID:"
            in bot
        ),

    "no raw chat state":
        (
            '"text": text'
            not in SERVER_SOURCE
            and
            '"raw_content"'
            not in SERVER_SOURCE
        ),

    "bot pressure":
        (
            "bot_pressure"
            in SERVER_SOURCE
            and
            "agency_v2_bot_pressure"
            in AGENCY_V2_SOURCE
        ),

    "sensitive initiative suppression":
        (
            "agency_v2_sensitive_atmosphere"
            in AGENCY_V2_SOURCE
        ),

    "direct reply protected":
        (
            "direct address never suppressed"
            in AGENCY_V2_SOURCE
        ),

    "participation pressure":
        (
            "wrap_participation_brain_server_v2"
            in AGENCY_V2_SOURCE
        ),

    "initiative opportunity":
        (
            "initiative_opportunity"
            in AGENCY_V2_SOURCE
        ),

    "server prompt":
        (
            "format_server_awareness_for_prompt"
            in AGENCY_V2_SOURCE
        ),

    "all bot outputs counted":
        all(
            kind in bot
            for kind in (
                'kind="reply"',
                'kind="continuation"',
                'kind="participation"',
                'kind="initiative"',
            )
        ),

    "compact startup":
        (
            "Server Awareness v"
            in live
            and
            "Agency / Initiative v"
            in live
        ),
}


failed = [
    name
    for name, success
    in contract_tests.items()
    if not success
]


if failed:
    fail(
        "Contract self-test failed: "
        +
        ", ".join(
            failed
        )
    )


ok(
    f"Contract self-test: "
    f"{len(contract_tests)}/"
    f"{len(contract_tests)} PASS"
)


# =========================================================
# BACKUP
# =========================================================

timestamp = (
    datetime.now()
    .astimezone()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)


backup_dir = (
    BACKUP_ROOT
    /
    timestamp
)


suffix = 1

while backup_dir.exists():
    backup_dir = (
        BACKUP_ROOT
        /
        f"{timestamp}_{suffix:02d}"
    )
    suffix += 1


backup_dir.mkdir(
    parents=True,
    exist_ok=False,
)


for path in (
    BOT_PATH,
    LIVE_PATH,
    AGENCY_PATH,
    INITIATIVE_PATH,
):
    shutil.copy2(
        path,
        backup_dir
        /
        path.name,
    )

    ok(
        f"Backup: {path.name}"
    )


# =========================================================
# ATOMIC WRITE
# =========================================================

def atomic_write(
    path,
    text,
):
    temp = Path(
        str(path)
        +
        ".tmp"
    )

    temp.write_text(
        text,
        encoding="utf-8",
    )

    temp.replace(
        path
    )


atomic_write(
    SERVER_PATH,
    SERVER_SOURCE,
)

ok(
    "Created: server_awareness.py"
)


atomic_write(
    AGENCY_V2_PATH,
    AGENCY_V2_SOURCE,
)

ok(
    "Created: agency_initiative_v2.py"
)


atomic_write(
    AGENCY_PATH,
    agency,
)

ok(
    "Updated: agency.py"
)


atomic_write(
    INITIATIVE_PATH,
    initiative,
)

ok(
    "Updated: initiative.py"
)


atomic_write(
    LIVE_PATH,
    live,
)

ok(
    "Updated: live_stability.py"
)


atomic_write(
    BOT_PATH,
    bot,
)

ok(
    "Updated: bot.py"
)


# =========================================================
# COMPILE COMPLETE PHASE-E CORE
# =========================================================

compile_targets = [
    SERVER_PATH,
    AGENCY_V2_PATH,
    AGENCY_PATH,
    INITIATIVE_PATH,
    LIVE_PATH,
    BOT_PATH,
    PROJECT_ROOT
    /
    "participation.py",
    PROJECT_ROOT
    /
    "self_development.py",
]


result = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        *[
            str(path)
            for path in compile_targets
        ],
    ],
    cwd=str(
        PROJECT_ROOT
    ),
    check=False,
)


if result.returncode != 0:
    print()
    print(
        "[POST-INSTALL WARNING] py_compile failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    "Post-install py_compile: 8/8"
)


# =========================================================
# REAL FILE SELF TESTS
# =========================================================

for test_path, label in (
    (
        SERVER_PATH,
        "Server Awareness",
    ),
    (
        AGENCY_V2_PATH,
        "Agency / Initiative 2.0",
    ),
    (
        AGENCY_PATH,
        "Agency",
    ),
):
    result = subprocess.run(
        [
            sys.executable,
            str(
                test_path
            ),
        ],
        cwd=str(
            PROJECT_ROOT
        ),
        check=False,
    )

    if result.returncode != 0:
        print()
        print(
            "[POST-INSTALL WARNING] "
            f"{label} self-test failed."
        )
        print(
            f"Backup: {backup_dir}"
        )
        raise SystemExit(
            result.returncode
        )

    ok(
        f"Post-install {label} self-test: PASS"
    )


print()
print("=" * 78)
print(
    "EVILNAE 4.0.0 AGENCY / INITIATIVE 2.0 + SERVER AWARENESS INSTALLED"
)
print("=" * 78)

print()
print("Server Awareness:")
print(
    "  [✓] observes structural activity across visible server channels"
)
print(
    "  [✓] still replies ONLY where existing ALLOWED_CHANNEL_ID permits"
)
print(
    "  [✓] no raw Discord chat text stored in Awareness state"
)
print(
    "  [✓] tracks activity / crowd / Evilnae social pull"
)
print(
    "  [✓] tracks Evilnae speaking pressure"
)
print(
    "  [✓] detects recent sensitive/conflict atmosphere"
)
print(
    "  [✓] 24h rolling structural event window"
)

print()
print("Agency 2.0:")
print(
    "  [✓] direct address can never be suppressed by server pressure"
)
print(
    "  [✓] low-value continuation can end naturally if Evilnae talked too much"
)
print(
    "  [✓] Participation Brain gets Server Awareness context"
)
print(
    "  [✓] high bot-pressure can skip obviously unnecessary Participation calls"
)

print()
print("Initiative 2.0:")
print(
    "  [✓] Inner State is still the personality drive"
)
print(
    "  [✓] Server opportunity can raise/lower initiative score"
)
print(
    "  [✓] high Evilnae speaking pressure blocks initiative"
)
print(
    "  [✓] sensitive recent atmosphere blocks casual initiative"
)
print(
    "  [✓] callback_thought / community_comment / ongoing_topic initiative shapes"
)
print(
    "  [✓] existing silence window + daily limit remain intact"
)
print(
    "  [✓] existing stochastic gate remains, now server-aware"
)

print()
print("Runtime file:")
print(
    "  evilnae_server_awareness.json"
)

print()
print("Versions:")
print(
    "  Bot: 4.0.0-agency-server-awareness"
)
print(
    "  Live Stability: 1.4-agency-server-awareness"
)
print(
    "  Response Agency: 2.0-server-aware"
)
print(
    "  Initiative: 2.0-server-aware"
)
print(
    "  Server Awareness: 1.0"
)
print(
    "  Agency / Initiative Engine: 2.0"
)

print()
print("No new model call:")
print(
    "  [✓] no extra OpenAI request"
)
print(
    "  [✓] no extra Qwen/Ollama request"
)

print()
print("Unchanged:")
print(
    "  [✓] Character Foundation / Canon"
)
print(
    "  [✓] Character Learning"
)
print(
    "  [✓] Experience Learning"
)
print(
    "  [✓] Self Development / Arcs"
)
print(
    "  [✓] Social Emotional State"
)
print(
    "  [✓] Episodes / Emotional Salience"
)
print(
    "  [✓] Inner State"
)
print(
    "  [✓] Emotes"
)

print()
print(
    f"Backup: {backup_dir}"
)

print()
print(
    "NO MEMORY RESET REQUIRED."
)

print()
print("NEXT:")
print(
    "  If this succeeds, the big Discord brain architecture "
    "is ready for a broader live test before Phase F "
    "(Voice / Twitch / VTS / Vision / Games)."
)

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

CONVERSATION_EPISODES_VERSION = "1.1-authority-safe"

EPISODE_GAP_SECONDS = int(
    os.getenv("EVILNAE_EPISODE_GAP_SECONDS", str(20 * 60))
)
EPISODE_HARD_MAX_SECONDS = int(
    os.getenv("EVILNAE_EPISODE_HARD_MAX_SECONDS", str(90 * 60))
)
EPISODE_MAX_EVENTS = int(
    os.getenv("EVILNAE_EPISODE_MAX_EVENTS", "80")
)
EPISODE_MAX_CLOSED = int(
    os.getenv("EVILNAE_EPISODE_MAX_CLOSED", "120")
)
EPISODE_PROMPT_EVENTS = int(
    os.getenv("EVILNAE_EPISODE_PROMPT_EVENTS", "12")
)
EPISODE_STATE_PATH = Path(
    os.getenv("EVILNAE_EPISODE_STATE_PATH", "evilnae_episodes.json")
)

_LOCK = threading.RLock()


@dataclass
class EpisodeObservation:
    episode_id: str = ""
    started_new: bool = False
    closed_previous: bool = False
    close_reason: str = ""
    event_added: bool = False
    active_event_count: int = 0
    participant_count: int = 0


def _default_data():
    return {
        "version": CONVERSATION_EPISODES_VERSION,
        "channels": {},
        "closed": [],
    }


def _load():
    if not EPISODE_STATE_PATH.exists():
        return _default_data()

    try:
        data = json.loads(
            EPISODE_STATE_PATH.read_text(encoding="utf-8")
        )
    except Exception:
        return _default_data()

    if not isinstance(data, dict):
        return _default_data()

    data.setdefault("version", CONVERSATION_EPISODES_VERSION)
    data.setdefault("channels", {})
    data.setdefault("closed", [])
    return data


def _save(data):
    data["version"] = CONVERSATION_EPISODES_VERSION

    temp = Path(str(EPISODE_STATE_PATH) + ".tmp")
    temp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temp.replace(EPISODE_STATE_PATH)


def _clean(value, limit=800):
    text = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()
    return text[:limit]


def _new_episode(channel_id, timestamp):
    return {
        "episode_id":
            f"ep_{str(channel_id)}_{int(timestamp * 1000)}",
        "channel_id": str(channel_id),
        "status": "active",
        "started_at": float(timestamp),
        "updated_at": float(timestamp),
        "ended_at": 0.0,
        "close_reason": "",
        "participants": {},
        "events": [],
        "seen_event_keys": [],
        "digest": "",
    }


def _event_key(
    *,
    role,
    user_id,
    username,
    content,
    message_id="",
):
    if message_id:
        return "msg:" + str(message_id)

    raw = (
        f"{role}|{user_id}|"
        f"{username}|{content}"
    )

    return (
        "hash:"
        +
        hashlib.sha1(
            raw.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()
    )


def _participant_names(episode):
    result = []

    for item in (
        episode.get("participants", {})
        or {}
    ).values():

        if not isinstance(item, dict):
            continue

        name = _clean(
            item.get("username", ""),
            80,
        )

        if name:
            result.append(name)

    return result


def _build_digest(episode):
    names = _participant_names(episode)

    participant_text = (
        ", ".join(names[:6])
        if names
        else "unbekannte Teilnehmer"
    )

    meaningful = []

    for event in episode.get("events", []) or []:
        if not isinstance(event, dict):
            continue

        content = _clean(
            event.get("content", ""),
            180,
        )

        if not content:
            continue

        if content.startswith("[nonverbale"):
            continue

        if len(
            re.findall(
                r"[A-Za-zÄÖÜäöüß0-9]+",
                content,
            )
        ) < 2:
            continue

        meaningful.append(content)

    if not meaningful:
        return f"Gespräch mit {participant_text}"

    snippets = []

    for text in meaningful[:2] + meaningful[-2:]:
        if text not in snippets:
            snippets.append(text)

    return (
        f"Teilnehmer: {participant_text}. "
        f"Verlauf: {' | '.join(snippets)}"
    )[:900]


def _boundary_reason(episode, timestamp):
    updated_at = float(
        episode.get("updated_at", 0.0)
        or 0.0
    )

    started_at = float(
        episode.get("started_at", 0.0)
        or 0.0
    )

    if (
        updated_at
        and
        timestamp - updated_at
        >=
        EPISODE_GAP_SECONDS
    ):
        return "conversation_gap"

    if (
        started_at
        and
        timestamp - started_at
        >=
        EPISODE_HARD_MAX_SECONDS
    ):
        return "hard_duration_limit"

    if len(
        episode.get("events", [])
        or []
    ) >= EPISODE_MAX_EVENTS:
        return "event_limit"

    return ""


def _close_locked(
    data,
    channel_key,
    *,
    timestamp,
    reason,
):
    episode = (
        data.get("channels", {})
        .get(channel_key)
    )

    if not isinstance(episode, dict):
        return None

    episode["status"] = "closed"
    episode["ended_at"] = float(timestamp)
    episode["updated_at"] = float(timestamp)
    episode["close_reason"] = reason or "closed"
    episode["digest"] = _build_digest(episode)
    episode.pop("seen_event_keys", None)

    closed = list(
        data.get("closed", [])
        or []
    )

    closed.append(episode)

    data["closed"] = closed[
        -EPISODE_MAX_CLOSED:
    ]

    data["channels"].pop(
        channel_key,
        None,
    )

    return episode


def observe_episode_message(
    *,
    channel_id: Any,
    role: str,
    content: str,
    user_id: Any = "",
    username: str = "",
    message_id: Any = "",
    timestamp: Optional[float] = None,
):
    timestamp = float(
        timestamp
        if timestamp is not None
        else time.time()
    )

    channel_key = str(channel_id)
    role = _clean(role, 40).lower() or "user"
    content = _clean(content, 900)
    user_id = str(user_id or "")
    username = _clean(username, 100)
    message_id = str(message_id or "")

    if not content:
        return EpisodeObservation()

    with _LOCK:
        data = _load()
        episode = (
            data["channels"]
            .get(channel_key)
        )

        started_new = False
        closed_previous = False
        close_reason = ""

        if isinstance(episode, dict):
            close_reason = _boundary_reason(
                episode,
                timestamp,
            )

            if close_reason:
                _close_locked(
                    data,
                    channel_key,
                    timestamp=timestamp,
                    reason=close_reason,
                )
                episode = None
                closed_previous = True

        if not isinstance(episode, dict):
            episode = _new_episode(
                channel_id,
                timestamp,
            )
            data["channels"][
                channel_key
            ] = episode
            started_new = True

        key = _event_key(
            role=role,
            user_id=user_id,
            username=username,
            content=content,
            message_id=message_id,
        )

        seen = list(
            episode.get("seen_event_keys", [])
            or []
        )

        if key in seen:
            return EpisodeObservation(
                episode_id=episode.get(
                    "episode_id",
                    "",
                ),
                started_new=started_new,
                closed_previous=closed_previous,
                close_reason=close_reason,
                event_added=False,
                active_event_count=len(
                    episode.get("events", [])
                    or []
                ),
                participant_count=len(
                    episode.get("participants", {})
                    or {}
                ),
            )

        events = list(
            episode.get("events", [])
            or []
        )

        events.append(
            {
                "role": role,
                "user_id": user_id,
                "username": username,
                "content": content,
                "message_id": message_id,
                "timestamp": timestamp,
            }
        )

        episode["events"] = events[
            -EPISODE_MAX_EVENTS:
        ]

        seen.append(key)

        episode["seen_event_keys"] = seen[
            -(EPISODE_MAX_EVENTS * 2):
        ]

        if role not in {
            "evilnae",
            "assistant",
            "bot",
        }:
            pkey = (
                user_id
                or username
                or "unknown"
            )

            participants = (
                episode.get("participants", {})
                or {}
            )

            item = dict(
                participants.get(pkey, {})
                or {}
            )

            item["user_id"] = user_id
            item["username"] = (
                username
                or item.get(
                    "username",
                    "unknown",
                )
            )
            item["message_count"] = (
                int(
                    item.get(
                        "message_count",
                        0,
                    )
                    or 0
                )
                +
                1
            )
            item["last_seen"] = timestamp

            participants[pkey] = item
            episode["participants"] = participants

        episode["updated_at"] = timestamp

        _save(data)

        return EpisodeObservation(
            episode_id=episode.get(
                "episode_id",
                "",
            ),
            started_new=started_new,
            closed_previous=closed_previous,
            close_reason=close_reason,
            event_added=True,
            active_event_count=len(
                episode.get("events", [])
                or []
            ),
            participant_count=len(
                episode.get("participants", {})
                or {}
            ),
        )


def sync_evilnae_from_snapshot(
    channel_id,
    snapshot,
):
    added = 0

    for item in snapshot or []:
        if not isinstance(item, dict):
            continue

        role = _clean(
            item.get(
                "role",
                item.get("type", ""),
            ),
            40,
        ).lower()

        username = _clean(
            item.get(
                "username",
                item.get("author_name", ""),
            ),
            100,
        )

        if not (
            role in {
                "assistant",
                "evilnae",
                "bot",
            }
            or
            username.lower()
            ==
            "evilnae"
        ):
            continue

        content = _clean(
            item.get(
                "content",
                item.get("text", ""),
            ),
            900,
        )

        if not content:
            continue

        raw_timestamp = item.get(
            "timestamp",
            None,
        )

        try:
            event_timestamp = (
                float(raw_timestamp)
                if raw_timestamp is not None
                else None
            )
        except Exception:
            event_timestamp = None

        result = observe_episode_message(
            channel_id=channel_id,
            role="evilnae",
            content=content,
            user_id=item.get(
                "user_id",
                item.get(
                    "author_id",
                    "evilnae",
                ),
            ),
            username=username or "Evilnae",
            message_id=item.get(
                "message_id",
                item.get("id", ""),
            ),
            timestamp=event_timestamp,
        )

        if result.event_added:
            added += 1

    return added


def close_stale_episodes(
    now=None,
):
    now = float(
        now
        if now is not None
        else time.time()
    )

    closed_count = 0

    with _LOCK:
        data = _load()

        for channel_key in list(
            data.get("channels", {})
            or {}
        ):
            episode = (
                data["channels"]
                .get(channel_key)
            )

            if not isinstance(episode, dict):
                continue

            reason = _boundary_reason(
                episode,
                now,
            )

            if not reason:
                continue

            _close_locked(
                data,
                channel_key,
                timestamp=now,
                reason=(
                    "startup_stale"
                    if reason == "conversation_gap"
                    else reason
                ),
            )

            closed_count += 1

        if closed_count:
            _save(data)

    return closed_count


def get_active_episode(channel_id):
    with _LOCK:
        data = _load()

        episode = (
            data.get("channels", {})
            .get(str(channel_id))
        )

        if not isinstance(episode, dict):
            return None

        return json.loads(
            json.dumps(
                episode,
                ensure_ascii=False,
            )
        )


def get_recent_closed_episodes(
    channel_id,
    *,
    limit=3,
):
    channel_key = str(channel_id)

    with _LOCK:
        data = _load()

        result = [
            item

            for item
            in data.get("closed", [])
            or []

            if (
                isinstance(item, dict)
                and
                str(
                    item.get(
                        "channel_id",
                        "",
                    )
                )
                ==
                channel_key
            )
        ]

    return result[
        -max(1, int(limit)):
    ]


def format_episode_context(
    channel_id,
):
    active = get_active_episode(
        channel_id
    )

    recent = get_recent_closed_episodes(
        channel_id,
        limit=2,
    )

    lines = [
        "[PERSISTENT CONVERSATION EPISODES]",
        (
            "Episode = zusammenhängendes Gesprächserlebnis, "
            "nicht automatisch langfristige Erinnerung."
        ),
        (
            "Abgeschlossene Episoden geben Kontext, "
            "verändern aber noch nicht Evilnaes Charakter."
        ),
        (
            "WICHTIG: Frühere von Evilnae GENERIERTE Antworten sind "
            "historischer Dialog, KEINE Autorität für ihre aktuelle Stimmung "
            "oder für Fakten über andere Personen. Inner State, Character State "
            "und aktuelle User-Korrekturen haben Vorrang."
        ),
        (
            "Nicht aus einer früheren trockenen/negativen Formulierung "
            "automatisch dieselbe Stimmung in die nächste Antwort fortschreiben."
        ),
        "",
    ]

    if active:
        names = _participant_names(active)

        lines.extend(
            [
                "ACTIVE EPISODE:",
                f"id={active.get('episode_id', '')}",
                (
                    "participants="
                    +
                    (
                        ", ".join(names[:8])
                        if names
                        else
                        "keine"
                    )
                ),
                "recent events:",
            ]
        )

        for event in (
            active.get("events", [])
            or []
        )[-EPISODE_PROMPT_EVENTS:]:

            if not isinstance(event, dict):
                continue

            role = _clean(
                event.get("role", "user"),
                40,
            )

            name = _clean(
                event.get("username", ""),
                80,
            )

            content = _clean(
                event.get("content", ""),
                260,
            )

            if not content:
                continue

            speaker = (
                "Evilnae"
                if role in {
                    "evilnae",
                    "assistant",
                    "bot",
                }
                else
                (name or "User")
            )

            lines.append(
                f"- {speaker}: {content}"
            )

    else:
        lines.append(
            "ACTIVE EPISODE: keine"
        )

    if recent:
        lines.extend(
            [
                "",
                "RECENT CLOSED EPISODES:",
            ]
        )

        for item in recent:
            lines.append(
                f"- {item.get('episode_id', '')}: "
                f"{_clean(item.get('digest', ''), 600)}"
            )

    return "\n".join(lines).strip()


def format_episode_observation_debug(
    result,
):
    return (
        "[CONVERSATION EPISODE] "
        f"v={CONVERSATION_EPISODES_VERSION} "
        f"id={result.episode_id!r} "
        f"new={result.started_new} "
        f"closed_previous={result.closed_previous} "
        f"close_reason={result.close_reason!r} "
        f"event_added={result.event_added} "
        f"events={result.active_event_count} "
        f"participants={result.participant_count}"
    )


def format_episode_stats_debug():
    with _LOCK:
        data = _load()

    return (
        "[CONVERSATION EPISODES] "
        f"v={CONVERSATION_EPISODES_VERSION} "
        f"active={len(data.get('channels', {}) or {})} "
        f"closed={len(data.get('closed', []) or [])} "
        f"gap={EPISODE_GAP_SECONDS}s "
        f"max_events={EPISODE_MAX_EVENTS}"
    )


def _self_test():
    global EPISODE_STATE_PATH

    original = EPISODE_STATE_PATH
    test_path = Path(
        "_evilnae_episode_selftest.json"
    )

    EPISODE_STATE_PATH = test_path

    try:
        if test_path.exists():
            test_path.unlink()

        tests = []

        first = observe_episode_message(
            channel_id="1",
            role="user",
            user_id="10",
            username="Alice",
            content="ich hab heute den boss gelegt",
            message_id="100",
            timestamp=1000.0,
        )

        tests.append(
            (
                "new episode starts",
                first.started_new
                and
                first.event_added,
            )
        )

        second = observe_episode_message(
            channel_id="1",
            role="user",
            user_id="10",
            username="Alice",
            content="war komplett cursed",
            message_id="101",
            timestamp=1050.0,
        )

        tests.append(
            (
                "same episode continues",
                (
                    not second.started_new
                    and
                    second.active_event_count == 2
                ),
            )
        )

        duplicate = observe_episode_message(
            channel_id="1",
            role="user",
            user_id="10",
            username="Alice",
            content="war komplett cursed",
            message_id="101",
            timestamp=1051.0,
        )

        tests.append(
            (
                "message id dedupe",
                (
                    not duplicate.event_added
                    and
                    duplicate.active_event_count == 2
                ),
            )
        )

        rotated = observe_episode_message(
            channel_id="1",
            role="user",
            user_id="11",
            username="Bob",
            content="neues thema",
            message_id="102",
            timestamp=(
                1050.0
                +
                EPISODE_GAP_SECONDS
                +
                5
            ),
        )

        tests.append(
            (
                "20m gap rotates",
                (
                    rotated.started_new
                    and
                    rotated.closed_previous
                    and
                    rotated.close_reason
                    ==
                    "conversation_gap"
                ),
            )
        )

        context = format_episode_context("1")

        tests.append(
            (
                "prompt context",
                (
                    "ACTIVE EPISODE"
                    in context
                    and
                    "Bob"
                    in context
                ),
            )
        )

        closed = get_recent_closed_episodes(
            "1",
            limit=3,
        )

        tests.append(
            (
                "closed archive digest",
                (
                    len(closed) == 1
                    and
                    bool(
                        closed[0].get(
                            "digest"
                        )
                    )
                ),
            )
        )

        passed = sum(
            1
            for _, success
            in tests
            if success
        )

        print("")
        print("=" * 58)
        print(
            f"CONVERSATION EPISODES v"
            f"{CONVERSATION_EPISODES_VERSION} TEST"
        )
        print("=" * 58)

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

    finally:
        EPISODE_STATE_PATH = original

        try:
            if test_path.exists():
                test_path.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(
        _self_test()
    )

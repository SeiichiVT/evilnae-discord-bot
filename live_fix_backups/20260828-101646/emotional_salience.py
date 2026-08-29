import hashlib
import json
import os
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conversation_episodes import (
    EPISODE_STATE_PATH,
)


EMOTIONAL_SALIENCE_VERSION = "1.0"

SALIENCE_STATE_PATH = Path(
    os.getenv(
        "EVILNAE_SALIENCE_STATE_PATH",
        "evilnae_salience.json",
    )
)

SALIENCE_MAX_EPISODES = int(
    os.getenv(
        "EVILNAE_SALIENCE_MAX_EPISODES",
        "240",
    )
)

RETENTION_CANDIDATE_THRESHOLD = float(
    os.getenv(
        "EVILNAE_SALIENCE_RETENTION_THRESHOLD",
        "0.50",
    )
)

_LOCK = threading.RLock()


@dataclass
class SalienceResult:
    episode_id: str = ""
    event_score: float = 0.0
    event_level: str = "mundane"
    valence: str = "neutral"
    signals: list[str] = field(
        default_factory=list
    )
    episode_score: float = 0.0
    retention_candidate: bool = False
    duplicate: bool = False


def _default_data():
    return {
        "version": EMOTIONAL_SALIENCE_VERSION,
        "episodes": {},
    }


def _load():
    if not SALIENCE_STATE_PATH.exists():
        return _default_data()

    try:
        data = json.loads(
            SALIENCE_STATE_PATH.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return _default_data()

    if not isinstance(data, dict):
        return _default_data()

    data.setdefault(
        "version",
        EMOTIONAL_SALIENCE_VERSION,
    )
    data.setdefault(
        "episodes",
        {},
    )

    return data


def _save(data):
    data[
        "version"
    ] = EMOTIONAL_SALIENCE_VERSION

    temp = Path(
        str(SALIENCE_STATE_PATH)
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
        SALIENCE_STATE_PATH
    )


def _clean(value: Any, limit=500):
    text = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    return text[:limit]


def _clamp01(value):
    try:
        number = float(value)
    except Exception:
        number = 0.0

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def _level(score):
    score = _clamp01(score)

    if score >= 0.70:
        return "significant"

    if score >= 0.45:
        return "important"

    if score >= 0.20:
        return "notable"

    return "mundane"


def _event_key(
    *,
    message_id,
    user_id,
    text,
):
    if message_id:
        return (
            "msg:"
            +
            str(message_id)
        )

    raw = (
        f"{user_id}|"
        f"{text}"
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


MUNDANE_ONLY_PATTERNS = [
    re.compile(
        r"^\s*(?:hi|hey|huhu|moin|morgen|guten morgen|"
        r"gute nacht|nacht|bye|tschüss|tschuess|bis morgen)"
        r"[!.? ]*$",
        re.I,
    ),
    re.compile(
        r"^\s*(?:lol|lmao|xd|xD|haha+|hehe+|jo|jup|jap|"
        r"okay|ok|true|real|same)[!.? ]*$",
        re.I,
    ),
]

POSITIVE_RELATION_PATTERNS = [
    re.compile(
        r"\b(?:ich\s+mag\s+dich|hab\s+dich\s+lieb|"
        r"ich\s+liebe\s+dich|du\s+bist\s+mir\s+wichtig|"
        r"du\s+bist\s+die\s+beste|du\s+bist\s+süß|"
        r"du\s+bist\s+suess)\b",
        re.I,
    ),
]

NEGATIVE_RELATION_PATTERNS = [
    re.compile(
        r"\b(?:ich\s+hasse\s+dich|ich\s+mag\s+dich\s+nicht|"
        r"du\s+nervst|du\s+bist\s+gemein|"
        r"bin\s+enttäuscht\s+von\s+dir|"
        r"bin\s+enttaeuscht\s+von\s+dir)\b",
        re.I,
    ),
]

APOLOGY_PATTERNS = [
    re.compile(
        r"\b(?:sorry|tut\s+mir\s+leid|verzeih(?:\s+mir)?|"
        r"entschuldige|entschuldigung)\b",
        re.I,
    ),
]

VULNERABILITY_PATTERNS = [
    re.compile(
        r"\b(?:mir\s+geht'?s\s+(?:nicht\s+gut|schlecht)|"
        r"ich\s+bin\s+traurig|ich\s+hab(?:e)?\s+angst|"
        r"ich\s+fühl(?:e)?\s+mich\s+einsam|"
        r"ich\s+fuehl(?:e)?\s+mich\s+einsam|"
        r"ich\s+bin\s+überfordert|ich\s+bin\s+ueberfordert|"
        r"ich\s+weine|ich\s+heule|panik|"
        r"macht\s+mich\s+fertig)\b",
        re.I,
    ),
]

EXPLICIT_FEEDBACK_PATTERNS = [
    re.compile(
        r"\b(?:deine\s+antwort|deine\s+reaktion|"
        r"du\s+hast\s+(?:gerade\s+)?(?:so|voll|echt)\s+"
        r"(?:süß|suess|gemein|kalt|lieb)\s+reagiert|"
        r"mehr\s+nicht\?|"
        r"das\s+war\s+(?:süß|suess|gemein|kalt|lieb)|"
        r"hätte\s+.*\s+süßer\s+reagiert|"
        r"haette\s+.*\s+suesser\s+reagiert)\b",
        re.I,
    ),
]

CORRECTION_PATTERNS = [
    re.compile(
        r"\b(?:das\s+stimmt\s+nicht|das\s+ist\s+falsch|"
        r"nein[, ]+evil|du\s+hast\s+.*\s+verwechselt|"
        r"ich\s+meinte\s+doch|das\s+hab\s+ich\s+nicht\s+gesagt|"
        r"das\s+habe\s+ich\s+nicht\s+gesagt)\b",
        re.I,
    ),
]

CALLBACK_PATTERNS = [
    re.compile(
        r"\b(?:weißt\s+du\s+noch|weisst\s+du\s+noch|"
        r"erinnerst\s+du\s+dich|wie\s+gestern|"
        r"wie\s+letztens|unser\s+running\s+gag)\b",
        re.I,
    ),
]

MILESTONE_PATTERNS = [
    re.compile(
        r"\b(?:endlich\s+geschafft|ich\s+hab(?:e)?\s+es\s+geschafft|"
        r"bestanden|gewonnen|job\s+bekommen|"
        r"beförderung|befoerderung|geburtstag|"
        r"jubiläum|jubilaeum)\b",
        re.I,
    ),
]

PERSONAL_PREFERENCE_PATTERNS = [
    re.compile(
        r"\b(?:mein(?:e|er)?\s+lieblings\w+|"
        r"ich\s+liebe\s+(?!dich\b)|"
        r"ich\s+hasse\s+(?!dich\b)|"
        r"ich\s+spiele\s+am\s+liebsten|"
        r"ich\s+schaue\s+am\s+liebsten)\b",
        re.I,
    ),
]


def analyze_event_salience(
    text,
    *,
    direct=False,
    is_hanae=False,
):
    value = _clean(
        text,
        1200,
    )

    lower = value.lower()

    if not value:
        return (
            0.0,
            "mundane",
            "neutral",
            [],
        )

    if any(
        pattern.search(value)
        for pattern
        in MUNDANE_ONLY_PATTERNS
    ):
        return (
            0.05,
            "mundane",
            "neutral",
            ["routine_smalltalk"],
        )

    score = 0.08
    signals = []
    positive = 0
    negative = 0

    if direct:
        score += 0.04
        signals.append(
            "direct_interaction"
        )

    if is_hanae:
        score += 0.03
        signals.append(
            "hanae_relationship_context"
        )

    if any(
        pattern.search(value)
        for pattern
        in POSITIVE_RELATION_PATTERNS
    ):
        score += 0.46
        positive += 2
        signals.append(
            "positive_relationship_signal"
        )

    if any(
        pattern.search(value)
        for pattern
        in NEGATIVE_RELATION_PATTERNS
    ):
        score += 0.46
        negative += 2
        signals.append(
            "negative_relationship_signal"
        )

    if any(
        pattern.search(value)
        for pattern
        in APOLOGY_PATTERNS
    ):
        score += 0.34
        signals.append(
            "relationship_repair"
        )

    if any(
        pattern.search(value)
        for pattern
        in VULNERABILITY_PATTERNS
    ):
        score += 0.48
        negative += 2
        signals.append(
            "vulnerability"
        )

    if any(
        pattern.search(value)
        for pattern
        in EXPLICIT_FEEDBACK_PATTERNS
    ):
        score += 0.44
        signals.append(
            "explicit_feedback"
        )

        if (
            "süß" in lower
            or
            "suess" in lower
            or
            "lieb" in lower
        ):
            positive += 1

        if (
            "gemein" in lower
            or
            "kalt" in lower
            or
            "mehr nicht" in lower
        ):
            negative += 1

    if any(
        pattern.search(value)
        for pattern
        in CORRECTION_PATTERNS
    ):
        score += 0.36
        signals.append(
            "explicit_correction"
        )

    if any(
        pattern.search(value)
        for pattern
        in CALLBACK_PATTERNS
    ):
        score += 0.28
        signals.append(
            "shared_callback"
        )

    if any(
        pattern.search(value)
        for pattern
        in MILESTONE_PATTERNS
    ):
        score += 0.30
        positive += 1
        signals.append(
            "personal_milestone"
        )

    if any(
        pattern.search(value)
        for pattern
        in PERSONAL_PREFERENCE_PATTERNS
    ):
        score += 0.18
        signals.append(
            "personal_preference"
        )

    word_count = len(
        re.findall(
            r"[A-Za-zÄÖÜäöüß0-9]+",
            value,
        )
    )

    if word_count >= 24:
        score += 0.05
        signals.append(
            "substantial_disclosure"
        )

    if not signals:
        signals.append(
            "ordinary_interaction"
        )

    score = _clamp01(
        score
    )

    if positive > negative:
        valence = "positive"
    elif negative > positive:
        valence = "negative"
    elif positive and negative:
        valence = "mixed"
    else:
        valence = "neutral"

    return (
        score,
        _level(score),
        valence,
        signals,
    )


def _episode_score(record):
    max_score = _clamp01(
        record.get(
            "max_event_score",
            0.0,
        )
    )

    important_count = int(
        record.get(
            "important_event_count",
            0,
        )
        or 0
    )

    signal_count = len(
        record.get(
            "signal_counts",
            {}
        )
        or {}
    )

    return _clamp01(
        max_score
        +
        min(
            0.16,
            important_count
            *
            0.035,
        )
        +
        min(
            0.08,
            signal_count
            *
            0.01,
        )
    )


def observe_salience_event(
    *,
    episode_id,
    channel_id,
    user_id,
    username,
    text,
    message_id="",
    direct=False,
    is_hanae=False,
):
    episode_id = str(
        episode_id
        or ""
    )

    if not episode_id:
        return SalienceResult()

    text = _clean(
        text,
        1200,
    )

    (
        event_score,
        event_level,
        valence,
        signals,
    ) = analyze_event_salience(
        text,
        direct=direct,
        is_hanae=is_hanae,
    )

    key = _event_key(
        message_id=message_id,
        user_id=user_id,
        text=text,
    )

    with _LOCK:
        data = _load()
        episodes = data[
            "episodes"
        ]

        record = dict(
            episodes.get(
                episode_id,
                {}
            )
            or {}
        )

        if not record:
            record = {
                "episode_id":
                    episode_id,
                "channel_id":
                    str(channel_id),
                "status":
                    "active",
                "created_at":
                    time.time(),
                "updated_at":
                    time.time(),
                "event_count":
                    0,
                "important_event_count":
                    0,
                "max_event_score":
                    0.0,
                "episode_score":
                    0.0,
                "signal_counts":
                    {},
                "valence_counts":
                    {},
                "strongest_signal":
                    "",
                "strongest_excerpt":
                    "",
                "seen_event_keys":
                    [],
                "retention_candidate":
                    False,
                "close_reason":
                    "",
                "closed_at":
                    0.0,
            }

        seen = list(
            record.get(
                "seen_event_keys",
                []
            )
            or []
        )

        if key in seen:
            return SalienceResult(
                episode_id=episode_id,
                event_score=event_score,
                event_level=event_level,
                valence=valence,
                signals=signals,
                episode_score=float(
                    record.get(
                        "episode_score",
                        0.0,
                    )
                    or 0.0
                ),
                retention_candidate=bool(
                    record.get(
                        "retention_candidate",
                        False,
                    )
                ),
                duplicate=True,
            )

        seen.append(
            key
        )

        record[
            "seen_event_keys"
        ] = seen[-180:]

        record[
            "event_count"
        ] = (
            int(
                record.get(
                    "event_count",
                    0,
                )
                or 0
            )
            +
            1
        )

        if event_score >= 0.45:
            record[
                "important_event_count"
            ] = (
                int(
                    record.get(
                        "important_event_count",
                        0,
                    )
                    or 0
                )
                +
                1
            )

        previous_max = float(
            record.get(
                "max_event_score",
                0.0,
            )
            or 0.0
        )

        if event_score > previous_max:
            record[
                "max_event_score"
            ] = event_score

            record[
                "strongest_signal"
            ] = (
                signals[0]
                if signals
                else
                "ordinary_interaction"
            )

            record[
                "strongest_excerpt"
            ] = _clean(
                text,
                220,
            )

            record[
                "strongest_user_id"
            ] = str(
                user_id
                or ""
            )

            record[
                "strongest_username"
            ] = _clean(
                username,
                100,
            )

        signal_counts = Counter(
            record.get(
                "signal_counts",
                {}
            )
            or {}
        )

        for signal in signals:
            signal_counts[
                signal
            ] += 1

        record[
            "signal_counts"
        ] = dict(
            signal_counts
        )

        valence_counts = Counter(
            record.get(
                "valence_counts",
                {}
            )
            or {}
        )

        valence_counts[
            valence
        ] += 1

        record[
            "valence_counts"
        ] = dict(
            valence_counts
        )

        record[
            "updated_at"
        ] = time.time()

        record[
            "episode_score"
        ] = _episode_score(
            record
        )

        record[
            "retention_candidate"
        ] = (
            record[
                "episode_score"
            ]
            >=
            RETENTION_CANDIDATE_THRESHOLD
        )

        episodes[
            episode_id
        ] = record

        # Keep the newest records only.
        if len(
            episodes
        ) > SALIENCE_MAX_EPISODES:

            ordered = sorted(
                episodes.items(),
                key=lambda item:
                    float(
                        item[1].get(
                            "updated_at",
                            0.0,
                        )
                        or 0.0
                    ),
            )

            for old_id, _ in ordered[
                :max(
                    0,
                    len(episodes)
                    -
                    SALIENCE_MAX_EPISODES
                )
            ]:
                episodes.pop(
                    old_id,
                    None,
                )

        _save(
            data
        )

        return SalienceResult(
            episode_id=episode_id,
            event_score=event_score,
            event_level=event_level,
            valence=valence,
            signals=signals,
            episode_score=float(
                record[
                    "episode_score"
                ]
            ),
            retention_candidate=bool(
                record[
                    "retention_candidate"
                ]
            ),
            duplicate=False,
        )


def sync_closed_episode_salience():
    if not EPISODE_STATE_PATH.exists():
        return 0

    try:
        episode_data = json.loads(
            EPISODE_STATE_PATH.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return 0

    closed = (
        episode_data.get(
            "closed",
            [],
        )
        if isinstance(
            episode_data,
            dict,
        )
        else []
    )

    if not isinstance(
        closed,
        list,
    ):
        return 0

    updated = 0

    with _LOCK:
        data = _load()
        records = data[
            "episodes"
        ]

        for episode in closed:
            if not isinstance(
                episode,
                dict,
            ):
                continue

            episode_id = str(
                episode.get(
                    "episode_id",
                    "",
                )
            )

            if not episode_id:
                continue

            record = records.get(
                episode_id
            )

            if not isinstance(
                record,
                dict,
            ):
                continue

            if record.get(
                "status"
            ) == "closed":
                continue

            record[
                "status"
            ] = "closed"

            record[
                "closed_at"
            ] = float(
                episode.get(
                    "ended_at",
                    time.time(),
                )
                or time.time()
            )

            record[
                "close_reason"
            ] = str(
                episode.get(
                    "close_reason",
                    "closed",
                )
                or "closed"
            )

            record[
                "episode_digest"
            ] = _clean(
                episode.get(
                    "digest",
                    "",
                ),
                700,
            )

            record[
                "episode_score"
            ] = _episode_score(
                record
            )

            record[
                "retention_candidate"
            ] = (
                record[
                    "episode_score"
                ]
                >=
                RETENTION_CANDIDATE_THRESHOLD
            )

            record[
                "updated_at"
            ] = time.time()

            updated += 1

        if updated:
            _save(
                data
            )

    return updated


def get_episode_salience(
    episode_id,
):
    with _LOCK:
        data = _load()

        record = (
            data.get(
                "episodes",
                {}
            )
            .get(
                str(
                    episode_id
                    or ""
                )
            )
        )

        if not isinstance(
            record,
            dict,
        ):
            return None

        return json.loads(
            json.dumps(
                record,
                ensure_ascii=False,
            )
        )


def format_salience_context(
    result,
):
    if result is None:
        return (
            "[EMOTIONAL SALIENCE]\n"
            "current=unknown\n"
            "Kein Learning aus diesem Block."
        )

    if result.event_level == "significant":
        guidance = (
            "Der Moment kann emotional stark relevant sein. "
            "Nicht mit Template-Smalltalk wegwischen. "
            "Ton und Beziehungskontext ernst nehmen."
        )
    elif result.event_level == "important":
        guidance = (
            "Der Moment ist wichtig genug für bewusste Kontinuität. "
            "Nicht unnötig trivialisieren."
        )
    elif result.event_level == "notable":
        guidance = (
            "Bemerkenswerter Moment, aber kein Drama erzwingen."
        )
    else:
        guidance = (
            "Gewöhnlicher Moment. Keine künstliche Bedeutung aufblasen."
        )

    return (
        "[EMOTIONAL SALIENCE]\n"
        f"current_event_score="
        f"{result.event_score:.2f}\n"
        f"current_level="
        f"{result.event_level}\n"
        f"valence="
        f"{result.valence}\n"
        f"signals="
        f"{', '.join(result.signals) if result.signals else 'none'}\n"
        f"episode_score="
        f"{result.episode_score:.2f}\n"
        f"retention_candidate="
        f"{result.retention_candidate}\n"
        f"guidance="
        f"{guidance}\n"
        "HARD: Salience ist keine Faktenquelle und schreibt "
        "noch KEIN Character Learning / Memory."
    )


def format_salience_debug(
    result,
):
    return (
        "[EMOTIONAL SALIENCE] "
        f"v={EMOTIONAL_SALIENCE_VERSION} "
        f"episode={result.episode_id!r} "
        f"event={result.event_score:.2f} "
        f"level={result.event_level} "
        f"valence={result.valence} "
        f"signals={result.signals} "
        f"episode_score={result.episode_score:.2f} "
        f"retention={result.retention_candidate} "
        f"duplicate={result.duplicate}"
    )


def format_salience_stats_debug():
    with _LOCK:
        data = _load()

    records = list(
        (
            data.get(
                "episodes",
                {}
            )
            or {}
        ).values()
    )

    active = sum(
        1
        for item in records
        if isinstance(item, dict)
        and item.get("status") != "closed"
    )

    closed = sum(
        1
        for item in records
        if isinstance(item, dict)
        and item.get("status") == "closed"
    )

    candidates = sum(
        1
        for item in records
        if isinstance(item, dict)
        and bool(
            item.get(
                "retention_candidate",
                False,
            )
        )
    )

    return (
        "[EMOTIONAL SALIENCE STATE] "
        f"v={EMOTIONAL_SALIENCE_VERSION} "
        f"active={active} "
        f"closed={closed} "
        f"retention_candidates={candidates} "
        f"threshold={RETENTION_CANDIDATE_THRESHOLD:.2f}"
    )


def _self_test():
    tests = []

    mundane = analyze_event_salience(
        "Guten Morgen!"
    )

    tests.append(
        (
            "routine greeting stays mundane",
            mundane[1] == "mundane",
        )
    )

    vulnerable = analyze_event_salience(
        "Mir gehts heute echt schlecht und ich bin traurig",
        direct=True,
    )

    tests.append(
        (
            "vulnerability is important",
            vulnerable[0] >= 0.45
            and
            "vulnerability"
            in vulnerable[3],
        )
    )

    feedback = analyze_event_salience(
        "Wow Evil, das war gerade echt gemein",
        direct=True,
    )

    tests.append(
        (
            "explicit feedback matters",
            feedback[0] >= 0.45
            and
            "explicit_feedback"
            in feedback[3],
        )
    )

    correction = analyze_event_salience(
        "Das stimmt nicht, du hast Hanae und mich verwechselt",
        direct=True,
    )

    tests.append(
        (
            "correction is retained as signal",
            "explicit_correction"
            in correction[3],
        )
    )

    callback = analyze_event_salience(
        "Weißt du noch wie wir gestern über den Boss geredet haben?"
    )

    tests.append(
        (
            "shared callback is notable",
            callback[0] >= 0.20
            and
            "shared_callback"
            in callback[3],
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
        f"EMOTIONAL SALIENCE v"
        f"{EMOTIONAL_SALIENCE_VERSION} TEST"
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


if __name__ == "__main__":
    raise SystemExit(
        _self_test()
    )

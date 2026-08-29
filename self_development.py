from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from character_foundation import (
    foundation_blocks_learning,
)
from character_learning import (
    CHARACTER_LEARNING_PATH,
)
from experience_learning import (
    EXPERIENCE_STATE_PATH,
)


SELF_DEVELOPMENT_VERSION = "1.0"
SELF_DEVELOPMENT_PATH = Path(
    "evilnae_self_development.json"
)

REFLECTION_STATE_PATH = Path(
    "reflection_state.json"
)

_LOCK = threading.RLock()

_REFRESH_INTERVAL_SECONDS = 30.0
_LAST_REFRESH_AT = 0.0

ARC_DORMANT_AFTER = (
    30 * 24 * 60 * 60
)

ARC_ARCHIVE_AFTER = (
    180 * 24 * 60 * 60
)

ARC_GENERIC_COOLDOWN = (
    6 * 60 * 60
)

MAX_ARCS = 120

STYLE_BASELINES = {
    "brevity_preference": 0.50,
    "teasing_preference": 0.50,
    "warmth_preference": 0.50,
    "slang_preference": 0.45,
    "emoji_preference": 0.35,
    "question_preference": 0.25,
    "initiative_preference": 0.35,
}

STYLE_LABELS = {
    "brevity_preference": "brevity",
    "teasing_preference": "teasing",
    "warmth_preference": "warmth",
    "slang_preference": "slang",
    "emoji_preference": "emoji",
    "question_preference": "questions",
    "initiative_preference": "initiative",
}


def _normalize(
    value: Any,
) -> str:
    text = str(
        value
        or ""
    ).lower()

    text = re.sub(
        r"[^a-z0-9äöüß]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def _tokens(
    value: Any,
) -> set[str]:
    return {
        token
        for token
        in _normalize(
            value
        ).split()
        if len(token) >= 3
    }


def _arc_id(
    topic_key: str,
    sentiment: str,
) -> str:
    raw = (
        f"{_normalize(topic_key)}|"
        f"{str(sentiment or '').lower()}"
    )

    return (
        "arc_"
        +
        hashlib.sha1(
            raw.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()[:18]
    )


def _default_data() -> dict:
    return {
        "version": SELF_DEVELOPMENT_VERSION,
        "arcs": {},
        "style_tracks": {},
        "last_refresh_at": 0.0,
    }


def _load_json(
    path: Path,
    default,
):
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return default


def _load() -> dict:
    data = _load_json(
        SELF_DEVELOPMENT_PATH,
        _default_data(),
    )

    if not isinstance(
        data,
        dict,
    ):
        data = _default_data()

    if not isinstance(
        data.get(
            "arcs"
        ),
        dict,
    ):
        data[
            "arcs"
        ] = {}

    if not isinstance(
        data.get(
            "style_tracks"
        ),
        dict,
    ):
        data[
            "style_tracks"
        ] = {}

    data[
        "version"
    ] = SELF_DEVELOPMENT_VERSION

    return data


def _save(
    data: dict,
) -> None:
    data[
        "version"
    ] = SELF_DEVELOPMENT_VERSION

    arcs = data.get(
        "arcs",
        {},
    )

    if isinstance(
        arcs,
        dict,
    ):
        ranked = sorted(
            arcs.items(),
            key=lambda item:
            float(
                item[1].get(
                    "last_supported_at",
                    0.0,
                )
                or 0.0
            ),
            reverse=True,
        )

        data[
            "arcs"
        ] = dict(
            ranked[
                :MAX_ARCS
            ]
        )

    temp = Path(
        str(
            SELF_DEVELOPMENT_PATH
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
        SELF_DEVELOPMENT_PATH
    )


def _safe_float(
    value,
    default=0.0,
) -> float:
    try:
        return float(
            value
        )
    except Exception:
        return float(
            default
        )


def _learning_entries() -> dict:
    data = _load_json(
        CHARACTER_LEARNING_PATH,
        {
            "entries": {},
        },
    )

    entries = (
        data.get(
            "entries",
            {},
        )
        if isinstance(
            data,
            dict,
        )
        else {}
    )

    return (
        entries
        if isinstance(
            entries,
            dict,
        )
        else {}
    )


def _experience_items() -> list[dict]:
    data = _load_json(
        EXPERIENCE_STATE_PATH,
        {
            "experiences": [],
        },
    )

    experiences = (
        data.get(
            "experiences",
            [],
        )
        if isinstance(
            data,
            dict,
        )
        else []
    )

    return [
        item
        for item
        in experiences
        if isinstance(
            item,
            dict,
        )
    ]


def _reflection_state() -> dict:
    data = _load_json(
        REFLECTION_STATE_PATH,
        {},
    )

    return (
        data
        if isinstance(
            data,
            dict,
        )
        else {}
    )


def _aggregate_experience_candidates() -> dict:
    aggregates = {}

    for item in _experience_items():
        candidate = item.get(
            "candidate_preference"
        )

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        topic = str(
            candidate.get(
                "topic",
                "",
            )
            or ""
        ).strip()

        topic_key = _normalize(
            candidate.get(
                "topic_key",
                topic,
            )
        )

        sentiment = str(
            candidate.get(
                "sentiment",
                "",
            )
            or ""
        ).strip().lower()

        context_hash = str(
            item.get(
                "context_hash",
                "",
            )
            or ""
        )

        experience_id = str(
            item.get(
                "experience_id",
                "",
            )
            or ""
        )

        created_at = _safe_float(
            item.get(
                "created_at",
                0.0,
            )
        )

        if (
            not topic
            or not topic_key
            or not sentiment
            or not context_hash
        ):
            continue

        key = (
            topic_key,
            sentiment,
        )

        record = aggregates.setdefault(
            key,
            {
                "topic": topic,
                "topic_key": topic_key,
                "sentiment": sentiment,
                "contexts": set(),
                "experience_ids": set(),
                "last_supported_at": 0.0,
                "promoted_seen": False,
            },
        )

        record[
            "contexts"
        ].add(
            context_hash
        )

        if experience_id:
            record[
                "experience_ids"
            ].add(
                experience_id
            )

        record[
            "last_supported_at"
        ] = max(
            _safe_float(
                record.get(
                    "last_supported_at",
                    0.0,
                )
            ),
            created_at,
        )

        if (
            item.get(
                "promoted"
            )
            or str(
                item.get(
                    "status",
                    "",
                )
            )
            ==
            "promoted"
        ):
            record[
                "promoted_seen"
            ] = True

    return aggregates


def _learning_match(
    topic_key: str,
) -> dict | None:
    entries = (
        _learning_entries()
    )

    direct = entries.get(
        topic_key
    )

    if isinstance(
        direct,
        dict,
    ):
        return direct

    for key, entry in (
        entries.items()
    ):
        if not isinstance(
            entry,
            dict,
        ):
            continue

        if (
            _normalize(
                key
            )
            ==
            topic_key
            or
            _normalize(
                entry.get(
                    "topic",
                    "",
                )
            )
            ==
            topic_key
        ):
            return entry

    return None


def _stage_for(
    *,
    evidence_count: int,
    learning_entry: dict | None,
    promoted_seen: bool,
) -> tuple[str | None, float, bool]:
    source = ""

    status = ""

    learning_evidence = []

    if isinstance(
        learning_entry,
        dict,
    ):
        source = str(
            learning_entry.get(
                "source",
                "",
            )
            or ""
        )

        status = str(
            learning_entry.get(
                "status",
                "",
            )
            or ""
        )

        learning_evidence = [
            str(item)
            for item in (
                learning_entry.get(
                    "evidence_ids",
                    [],
                )
                or []
            )
            if str(item).strip()
        ]

    reflection_validated = bool(
        promoted_seen
        or (
            source
            ==
            "experience_reflection_v2"
            and
            len(
                learning_evidence
            )
            >= 3
        )
    )

    if (
        reflection_validated
        and (
            status
            ==
            "favorite_candidate"
            or
            evidence_count
            >= 5
            or
            len(
                learning_evidence
            )
            >= 5
        )
    ):
        return (
            "signature",
            0.86,
            True,
        )

    if reflection_validated:
        return (
            "established",
            0.68,
            True,
        )

    if evidence_count >= 3:
        return (
            "developing",
            0.46,
            False,
        )

    if evidence_count >= 2:
        return (
            "spark",
            0.26,
            False,
        )

    # One isolated interaction is deliberately NOT an arc.
    return (
        None,
        0.0,
        False,
    )


def _blocked_by_foundation(
    topic: str,
) -> bool:
    try:
        blocked, _ = (
            foundation_blocks_learning(
                topic
            )
        )

        return bool(
            blocked
        )

    except Exception:
        return False


def _refresh_arcs(
    data: dict,
    *,
    now: float,
) -> int:
    arcs = data[
        "arcs"
    ]

    aggregates = (
        _aggregate_experience_candidates()
    )

    changed = 0
    seen_ids = set()

    for (
        topic_key,
        sentiment,
    ), record in aggregates.items():

        topic = str(
            record[
                "topic"
            ]
        )

        if _blocked_by_foundation(
            topic
        ):
            continue

        evidence_count = len(
            record[
                "contexts"
            ]
        )

        learning_entry = (
            _learning_match(
                topic_key
            )
        )

        (
            computed_stage,
            strength,
            reflection_validated,
        ) = _stage_for(
            evidence_count=(
                evidence_count
            ),
            learning_entry=(
                learning_entry
            ),
            promoted_seen=bool(
                record.get(
                    "promoted_seen"
                )
            ),
        )

        if computed_stage is None:
            continue

        arc_id = _arc_id(
            topic_key,
            sentiment,
        )

        seen_ids.add(
            arc_id
        )

        old = dict(
            arcs.get(
                arc_id,
                {},
            )
            or {}
        )

        created_at = _safe_float(
            old.get(
                "created_at",
                0.0,
            )
        )

        if not created_at:
            created_at = now

        last_supported_at = (
            _safe_float(
                record.get(
                    "last_supported_at",
                    0.0,
                )
            )
            or now
        )

        age = max(
            0.0,
            now
            -
            last_supported_at,
        )

        stage = (
            computed_stage
        )

        if age >= ARC_ARCHIVE_AFTER:
            stage = "archived"

        elif age >= ARC_DORMANT_AFTER:
            stage = "dormant"

        updated = {
            "arc_id": arc_id,
            "kind": "interest",
            "topic": topic,
            "topic_key": topic_key,
            "sentiment": sentiment,
            "stage": stage,
            "underlying_stage": (
                computed_stage
            ),
            "strength": round(
                strength,
                3,
            ),
            "evidence_count": (
                evidence_count
            ),
            "reflection_validated": (
                reflection_validated
            ),
            "created_at": created_at,
            "updated_at": now,
            "last_supported_at": (
                last_supported_at
            ),
            "last_used_at": _safe_float(
                old.get(
                    "last_used_at",
                    0.0,
                )
            ),
            "use_count": int(
                old.get(
                    "use_count",
                    0,
                )
                or 0
            ),
        }

        if updated != old:
            changed += 1

        arcs[
            arc_id
        ] = updated

    for (
        arc_id,
        old,
    ) in list(
        arcs.items()
    ):
        if arc_id in seen_ids:
            continue

        updated = dict(
            old
        )

        last_supported_at = _safe_float(
            updated.get(
                "last_supported_at",
                0.0,
            )
        )

        age = (
            max(
                0.0,
                now
                -
                last_supported_at,
            )
            if last_supported_at
            else ARC_ARCHIVE_AFTER
        )

        new_stage = str(
            updated.get(
                "stage",
                "dormant",
            )
        )

        if age >= ARC_ARCHIVE_AFTER:
            new_stage = "archived"

        elif age >= ARC_DORMANT_AFTER:
            new_stage = "dormant"

        if (
            new_stage
            !=
            updated.get(
                "stage"
            )
        ):
            updated[
                "stage"
            ] = new_stage

            updated[
                "updated_at"
            ] = now

            arcs[
                arc_id
            ] = updated

            changed += 1

    return changed


def _refresh_style_tracks(
    data: dict,
    *,
    now: float,
) -> int:
    reflection = (
        _reflection_state()
    )

    recent = reflection.get(
        "recent_reflections",
        [],
    )

    if not isinstance(
        recent,
        list,
    ):
        recent = []

    reflection_count = len(
        recent
    )

    last_updated = _safe_float(
        reflection.get(
            "last_updated",
            0.0,
        )
    )

    tracks = data[
        "style_tracks"
    ]

    changed = 0

    for (
        field,
        baseline,
    ) in STYLE_BASELINES.items():

        value = _safe_float(
            reflection.get(
                field,
                baseline,
            ),
            baseline,
        )

        delta = (
            value
            -
            baseline
        )

        key = STYLE_LABELS[
            field
        ]

        old = dict(
            tracks.get(
                key,
                {},
            )
            or {}
        )

        # Needs repeated reflection, not one chat.
        if (
            reflection_count < 4
            or abs(
                delta
            )
            < 0.08
        ):
            if old:
                new = dict(
                    old
                )

                new[
                    "stage"
                ] = "dormant"

                new[
                    "updated_at"
                ] = now

                if new != old:
                    tracks[
                        key
                    ] = new

                    changed += 1

            continue

        age = (
            max(
                0.0,
                now
                -
                last_updated,
            )
            if last_updated
            else ARC_ARCHIVE_AFTER
        )

        if age >= ARC_ARCHIVE_AFTER:
            stage = "archived"

        elif age >= ARC_DORMANT_AFTER:
            stage = "dormant"

        elif (
            reflection_count >= 8
            and
            abs(
                delta
            )
            >= 0.12
        ):
            stage = "established"

        else:
            stage = "developing"

        direction = (
            "more"
            if delta > 0
            else "less"
        )

        updated = {
            "track": key,
            "direction": direction,
            "stage": stage,
            "strength": round(
                min(
                    1.0,
                    abs(
                        delta
                    )
                    *
                    3.0,
                ),
                3,
            ),
            "reflection_count": (
                reflection_count
            ),
            "last_reflection_at": (
                last_updated
            ),
            "updated_at": now,
        }

        if updated != old:
            changed += 1

        tracks[
            key
        ] = updated

    return changed


def refresh_self_development(
    *,
    now: float | None = None,
    force=False,
) -> dict:
    global _LAST_REFRESH_AT

    now = float(
        now
        if now is not None
        else time.time()
    )

    with _LOCK:
        if (
            not force
            and
            _LAST_REFRESH_AT
            and
            now
            -
            _LAST_REFRESH_AT
            <
            _REFRESH_INTERVAL_SECONDS
        ):
            data = _load()

            return {
                "changed": 0,
                "reason": "refresh_cooldown",
                "data": data,
            }

        data = _load()

        arc_changes = (
            _refresh_arcs(
                data,
                now=now,
            )
        )

        style_changes = (
            _refresh_style_tracks(
                data,
                now=now,
            )
        )

        data[
            "last_refresh_at"
        ] = now

        _save(
            data
        )

        _LAST_REFRESH_AT = now

    return {
        "changed": (
            arc_changes
            +
            style_changes
        ),
        "arc_changes": arc_changes,
        "style_changes": style_changes,
        "reason": "refreshed",
        "data": data,
    }


def observe_development_from_experience(
    result,
) -> dict:
    if not isinstance(
        result,
        dict,
    ):
        return {
            "changed": 0,
            "reason": "invalid_experience_result",
        }

    candidate = result.get(
        "candidate"
    )

    cluster_count = int(
        result.get(
            "cluster_count",
            0,
        )
        or 0
    )

    # One interaction is not enough to create an Arc.
    if (
        not isinstance(
            candidate,
            dict,
        )
        or cluster_count < 2
    ):
        return {
            "changed": 0,
            "reason": "not_enough_arc_evidence",
        }

    return refresh_self_development(
        force=True
    )


def observe_development_from_reflection(
    metadata,
) -> dict:
    if not isinstance(
        metadata,
        dict,
    ):
        return {
            "changed": 0,
            "reason": "invalid_reflection_metadata",
        }

    preference = metadata.get(
        "preference_result"
    )

    if not isinstance(
        preference,
        dict,
    ):
        return {
            "changed": 0,
            "reason": "no_preference_reflection",
        }

    reason = str(
        preference.get(
            "reason",
            "",
        )
        or ""
    )

    if (
        preference.get(
            "promoted"
        )
        or reason
        in {
            "needs_more_independent_experiences",
            "reflected_preference_promoted",
        }
    ):
        return refresh_self_development(
            force=True
        )

    return {
        "changed": 0,
        "reason": "reflection_not_arc_relevant",
    }


def _topic_is_relevant(
    topic: str,
    user_text: str,
) -> bool:
    topic_tokens = _tokens(
        topic
    )

    query_tokens = _tokens(
        user_text
    )

    if not topic_tokens:
        return False

    return bool(
        topic_tokens
        &
        query_tokens
    )


def _arc_visible(
    arc: dict,
    *,
    user_text: str,
    now: float,
) -> bool:
    stage = str(
        arc.get(
            "stage",
            "",
        )
    )

    if stage in {
        "archived",
        "dormant",
    }:
        return False

    relevant = _topic_is_relevant(
        str(
            arc.get(
                "topic",
                "",
            )
        ),
        user_text,
    )

    if stage in {
        "spark",
        "developing",
    }:
        return relevant

    if relevant:
        return True

    last_used_at = _safe_float(
        arc.get(
            "last_used_at",
            0.0,
        )
    )

    if (
        last_used_at
        and
        now
        -
        last_used_at
        <
        ARC_GENERIC_COOLDOWN
    ):
        return False

    return True


def _arc_rank(
    arc: dict,
    *,
    user_text: str,
) -> tuple:
    relevant = _topic_is_relevant(
        str(
            arc.get(
                "topic",
                "",
            )
        ),
        user_text,
    )

    stage_score = {
        "signature": 4,
        "established": 3,
        "developing": 2,
        "spark": 1,
    }.get(
        str(
            arc.get(
                "stage",
                "",
            )
        ),
        0,
    )

    return (
        1 if relevant else 0,
        stage_score,
        _safe_float(
            arc.get(
                "strength",
                0.0,
            )
        ),
        _safe_float(
            arc.get(
                "last_supported_at",
                0.0,
            )
        ),
    )


def format_self_development_for_prompt(
    user_text: str = "",
    *,
    limit=3,
) -> str:
    refresh_self_development()

    now = time.time()

    with _LOCK:
        data = _load()

    arcs = [
        dict(
            arc
        )
        for arc in (
            data.get(
                "arcs",
                {}
            )
            or {}
        ).values()
        if isinstance(
            arc,
            dict,
        )
        and
        _arc_visible(
            arc,
            user_text=user_text,
            now=now,
        )
    ]

    arcs.sort(
        key=lambda arc:
        _arc_rank(
            arc,
            user_text=user_text,
        ),
        reverse=True,
    )

    selected = arcs[
        :max(
            1,
            int(
                limit
            ),
        )
    ]

    tracks = [
        dict(
            track
        )
        for track in (
            data.get(
                "style_tracks",
                {}
            )
            or {}
        ).values()
        if isinstance(
            track,
            dict,
        )
        and
        str(
            track.get(
                "stage",
                "",
            )
        )
        in {
            "developing",
            "established",
        }
    ]

    tracks.sort(
        key=lambda track: (
            1
            if track.get(
                "stage"
            )
            ==
            "established"
            else 0,
            _safe_float(
                track.get(
                    "strength",
                    0.0,
                )
            ),
        ),
        reverse=True,
    )

    lines = [
        (
            "[SELF DEVELOPMENT / LONG-RUNNING ARCS "
            f"v{SELF_DEVELOPMENT_VERSION}]"
        ),
        (
            "Dieser Layer liegt UNTER der Character Foundation "
            "und UNTER bestätigten Fakten."
        ),
        (
            "Arcs sind langfristige Entwicklungstendenzen, "
            "keine neuen Ereignisse und keine Lore."
        ),
    ]

    if selected:
        lines.append(
            "Aktive Interest-Arcs:"
        )

        for arc in selected:
            stage = str(
                arc.get(
                    "stage",
                    ""
                )
            )

            topic = str(
                arc.get(
                    "topic",
                    ""
                )
            )

            sentiment = str(
                arc.get(
                    "sentiment",
                    ""
                )
            )

            evidence = int(
                arc.get(
                    "evidence_count",
                    0,
                )
                or 0
            )

            validated = bool(
                arc.get(
                    "reflection_validated",
                    False,
                )
            )

            lines.append(
                (
                    f"- {topic}: "
                    f"stage={stage}, "
                    f"sentiment={sentiment}, "
                    f"independent_evidence={evidence}, "
                    f"reflection_validated={validated}"
                )
            )

    else:
        lines.append(
            "Keine aktuell relevante Arc für diesen Turn."
        )

    if tracks:
        lines.append(
            "Langsame Style-Entwicklung:"
        )

        for track in tracks[:2]:
            lines.append(
                (
                    f"- {track.get('track')}: "
                    f"{track.get('direction')} "
                    f"({track.get('stage')})"
                )
            )

    lines.extend(
        [
            "HARD RULES:",
            (
                "- spark/developing ist KEIN stabiler Self-Fact; "
                "nur aufgreifen, wenn der User das Thema selbst berührt."
            ),
            (
                "- established/signature darf subtil Verhalten färben, "
                "aber NICHT in jeder Antwort erwähnt werden."
            ),
            (
                "- Niemals ein Erlebnis erfinden, um einen Arc zu erklären."
            ),
            (
                "- Keine Arc darf Foundation/Canon überschreiben."
            ),
            (
                "- Keine aktuelle Aktivität aus einem Long-running Arc ableiten."
            ),
            (
                "- Arc-Cooldown beachten: nicht dasselbe Thema "
                "immer wieder ungefragt hineinziehen."
            ),
        ]
    )

    return "\n".join(
        lines
    )


def register_arc_surface_use(
    answer: str,
    *,
    now: float | None = None,
) -> int:
    text = _normalize(
        answer
    )

    if not text:
        return 0

    now = float(
        now
        if now is not None
        else time.time()
    )

    refresh_self_development(
        now=now,
    )

    changed = 0

    with _LOCK:
        data = _load()

        arcs = data.get(
            "arcs",
            {},
        )

        for (
            arc_id,
            arc,
        ) in arcs.items():

            if not isinstance(
                arc,
                dict,
            ):
                continue

            stage = str(
                arc.get(
                    "stage",
                    "",
                )
            )

            if stage not in {
                "established",
                "signature",
            }:
                continue

            topic = _normalize(
                arc.get(
                    "topic",
                    "",
                )
            )

            if (
                len(
                    topic
                )
                < 3
                or topic not in text
            ):
                continue

            updated = dict(
                arc
            )

            updated[
                "last_used_at"
            ] = now

            updated[
                "use_count"
            ] = int(
                updated.get(
                    "use_count",
                    0,
                )
                or 0
            ) + 1

            updated[
                "updated_at"
            ] = now

            arcs[
                arc_id
            ] = updated

            changed += 1

        if changed:
            _save(
                data
            )

    return changed


def self_development_stats() -> dict:
    refresh_self_development()

    with _LOCK:
        data = _load()

    arcs = [
        arc
        for arc in (
            data.get(
                "arcs",
                {}
            )
            or {}
        ).values()
        if isinstance(
            arc,
            dict,
        )
    ]

    stages = {}

    for arc in arcs:
        stage = str(
            arc.get(
                "stage",
                "unknown",
            )
        )

        stages[
            stage
        ] = stages.get(
            stage,
            0,
        ) + 1

    tracks = [
        track
        for track in (
            data.get(
                "style_tracks",
                {}
            )
            or {}
        ).values()
        if isinstance(
            track,
            dict,
        )
        and
        str(
            track.get(
                "stage",
                "",
            )
        )
        in {
            "developing",
            "established",
        }
    ]

    return {
        "version": SELF_DEVELOPMENT_VERSION,
        "arcs": len(
            arcs
        ),
        "active_arcs": sum(
            count
            for stage, count
            in stages.items()
            if stage
            in {
                "spark",
                "developing",
                "established",
                "signature",
            }
        ),
        "stages": stages,
        "style_tracks": len(
            tracks
        ),
    }


def format_self_development_debug(
    result=None,
) -> str:
    stats = (
        self_development_stats()
    )

    if not result:
        return (
            "[SELF DEVELOPMENT] "
            f"v={SELF_DEVELOPMENT_VERSION} "
            f"arcs={stats['arcs']} "
            f"active={stats['active_arcs']} "
            f"tracks={stats['style_tracks']}"
        )

    return (
        "[SELF DEVELOPMENT] "
        f"v={SELF_DEVELOPMENT_VERSION} "
        f"changed={result.get('changed', 0)} "
        f"reason={result.get('reason', '')} "
        f"arcs={stats['arcs']} "
        f"active={stats['active_arcs']}"
    )


def _self_test() -> int:
    global SELF_DEVELOPMENT_PATH
    global REFLECTION_STATE_PATH
    global _LAST_REFRESH_AT

    import tempfile

    original_dev = (
        SELF_DEVELOPMENT_PATH
    )

    original_reflection = (
        REFLECTION_STATE_PATH
    )

    original_experience = (
        EXPERIENCE_STATE_PATH
    )

    original_learning = (
        CHARACTER_LEARNING_PATH
    )

    tests = []

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(
                tmp
            )

            SELF_DEVELOPMENT_PATH = (
                tmp
                /
                "development.json"
            )

            REFLECTION_STATE_PATH = (
                tmp
                /
                "reflection.json"
            )

            # Imported Path constants are module globals; replace them
            # locally for this deterministic self-test.
            globals()[
                "EXPERIENCE_STATE_PATH"
            ] = (
                tmp
                /
                "experiences.json"
            )

            globals()[
                "CHARACTER_LEARNING_PATH"
            ] = (
                tmp
                /
                "character_learning.json"
            )

            base_now = time.time()

            def write_experiences(
                count,
                *,
                last_offset=0.0,
            ):
                items = []

                for index in range(
                    count
                ):
                    created = (
                        base_now
                        +
                        last_offset
                        +
                        index
                    )

                    items.append(
                        {
                            "experience_id":
                                f"exp{index}",
                            "created_at":
                                created,
                            "context_hash":
                                f"ctx{index}",
                            "candidate_preference":
                                {
                                    "topic":
                                        "Hades",
                                    "topic_key":
                                        "hades",
                                    "sentiment":
                                        "like",
                                },
                            "status":
                                "candidate",
                            "promoted":
                                False,
                        }
                    )

                globals()[
                    "EXPERIENCE_STATE_PATH"
                ].write_text(
                    json.dumps(
                        {
                            "experiences":
                                items
                        }
                    ),
                    encoding="utf-8",
                )

            globals()[
                "CHARACTER_LEARNING_PATH"
            ].write_text(
                json.dumps(
                    {
                        "entries": {}
                    }
                ),
                encoding="utf-8",
            )

            REFLECTION_STATE_PATH.write_text(
                json.dumps(
                    {
                        "recent_reflections":
                            [],
                    }
                ),
                encoding="utf-8",
            )

            write_experiences(
                1
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 10,
                force=True,
            )

            tests.append(
                (
                    "one interaction creates no arc",
                    self_development_stats()[
                        "arcs"
                    ]
                    ==
                    0,
                )
            )

            write_experiences(
                2
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 20,
                force=True,
            )

            data = _load()

            arc = next(
                iter(
                    data[
                        "arcs"
                    ].values()
                )
            )

            tests.append(
                (
                    "two contexts create spark",
                    arc[
                        "stage"
                    ]
                    ==
                    "spark"
                    and
                    arc[
                        "evidence_count"
                    ]
                    ==
                    2,
                )
            )

            # Duplicate context does not count independently.
            duplicate_data = {
                "experiences": [
                    {
                        "experience_id":
                            "a",
                        "created_at":
                            base_now,
                        "context_hash":
                            "same",
                        "candidate_preference":
                            {
                                "topic":
                                    "Hades",
                                "topic_key":
                                    "hades",
                                "sentiment":
                                    "like",
                            },
                    },
                    {
                        "experience_id":
                            "b",
                        "created_at":
                            base_now + 1,
                        "context_hash":
                            "same",
                        "candidate_preference":
                            {
                                "topic":
                                    "Hades",
                                "topic_key":
                                    "hades",
                                "sentiment":
                                    "like",
                            },
                    },
                ]
            }

            globals()[
                "EXPERIENCE_STATE_PATH"
            ].write_text(
                json.dumps(
                    duplicate_data
                ),
                encoding="utf-8",
            )

            SELF_DEVELOPMENT_PATH.unlink(
                missing_ok=True
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 30,
                force=True,
            )

            tests.append(
                (
                    "duplicate context is not arc evidence",
                    self_development_stats()[
                        "arcs"
                    ]
                    ==
                    0,
                )
            )

            write_experiences(
                3
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 40,
                force=True,
            )

            data = _load()

            arc = next(
                iter(
                    data[
                        "arcs"
                    ].values()
                )
            )

            tests.append(
                (
                    "three contexts create developing arc",
                    arc[
                        "stage"
                    ]
                    ==
                    "developing",
                )
            )

            globals()[
                "CHARACTER_LEARNING_PATH"
            ].write_text(
                json.dumps(
                    {
                        "entries":
                            {
                                "hades":
                                    {
                                        "topic":
                                            "Hades",
                                        "sentiment":
                                            "like",
                                        "status":
                                            "stable",
                                        "source":
                                            "experience_reflection_v2",
                                        "evidence_ids":
                                            [
                                                "exp0",
                                                "exp1",
                                                "exp2",
                                            ],
                                    }
                            }
                    }
                ),
                encoding="utf-8",
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 50,
                force=True,
            )

            arc = next(
                iter(
                    _load()[
                        "arcs"
                    ].values()
                )
            )

            tests.append(
                (
                    "reflection promotion establishes arc",
                    arc[
                        "stage"
                    ]
                    ==
                    "established"
                    and
                    arc[
                        "reflection_validated"
                    ],
                )
            )

            write_experiences(
                5
            )

            globals()[
                "CHARACTER_LEARNING_PATH"
            ].write_text(
                json.dumps(
                    {
                        "entries":
                            {
                                "hades":
                                    {
                                        "topic":
                                            "Hades",
                                        "sentiment":
                                            "like",
                                        "status":
                                            "favorite_candidate",
                                        "source":
                                            "experience_reflection_v2",
                                        "evidence_ids":
                                            [
                                                "exp0",
                                                "exp1",
                                                "exp2",
                                                "exp3",
                                                "exp4",
                                            ],
                                    }
                            }
                    }
                ),
                encoding="utf-8",
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 60,
                force=True,
            )

            arc = next(
                iter(
                    _load()[
                        "arcs"
                    ].values()
                )
            )

            tests.append(
                (
                    "five reflected contexts create signature arc",
                    arc[
                        "stage"
                    ]
                    ==
                    "signature",
                )
            )

            before = (
                format_self_development_for_prompt(
                    "Was zockst du gern?"
                )
            )

            tests.append(
                (
                    "signature arc enters prompt",
                    "Hades"
                    in before,
                )
            )

            register_arc_surface_use(
                "Hades ist schon ziemlich stark.",
                now=base_now + 70,
            )

            cooldown_generic = (
                format_self_development_for_prompt(
                    "Wie geht es dir heute?"
                )
            )

            direct_topic = (
                format_self_development_for_prompt(
                    "Was hältst du von Hades?"
                )
            )

            tests.append(
                (
                    "generic cooldown hides recently used arc",
                    "Hades"
                    not in cooldown_generic,
                )
            )

            tests.append(
                (
                    "direct topic bypasses arc cooldown",
                    "Hades"
                    in direct_topic,
                )
            )

            REFLECTION_STATE_PATH.write_text(
                json.dumps(
                    {
                        "brevity_preference":
                            0.63,
                        "teasing_preference":
                            0.50,
                        "warmth_preference":
                            0.50,
                        "slang_preference":
                            0.45,
                        "emoji_preference":
                            0.35,
                        "question_preference":
                            0.25,
                        "initiative_preference":
                            0.35,
                        "recent_reflections":
                            [
                                {},
                                {},
                                {},
                                {},
                                {},
                            ],
                        "last_updated":
                            base_now + 80,
                    }
                ),
                encoding="utf-8",
            )

            _LAST_REFRESH_AT = 0.0

            refresh_self_development(
                now=base_now + 90,
                force=True,
            )

            tracks = (
                _load()[
                    "style_tracks"
                ]
            )

            tests.append(
                (
                    "style track needs repeated reflection",
                    tracks[
                        "brevity"
                    ][
                        "stage"
                    ]
                    ==
                    "developing"
                    and
                    tracks[
                        "brevity"
                    ][
                        "direction"
                    ]
                    ==
                    "more",
                )
            )

            serialized = (
                SELF_DEVELOPMENT_PATH.read_text(
                    encoding="utf-8"
                )
            )

            tests.append(
                (
                    "no raw chat content stored",
                    "Was hältst du"
                    not in serialized
                    and
                    "Wie geht es dir"
                    not in serialized,
                )
            )

    finally:
        SELF_DEVELOPMENT_PATH = (
            original_dev
        )

        REFLECTION_STATE_PATH = (
            original_reflection
        )

        globals()[
            "EXPERIENCE_STATE_PATH"
        ] = (
            original_experience
        )

        globals()[
            "CHARACTER_LEARNING_PATH"
        ] = (
            original_learning
        )

        _LAST_REFRESH_AT = 0.0

    passed = sum(
        1
        for _, success
        in tests
        if success
    )

    print()
    print("=" * 68)
    print(
        f"SELF DEVELOPMENT / LONG-RUNNING ARCS "
        f"v{SELF_DEVELOPMENT_VERSION} TEST"
    )
    print("=" * 68)

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

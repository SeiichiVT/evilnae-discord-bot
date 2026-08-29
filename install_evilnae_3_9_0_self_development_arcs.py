from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
EXPERIENCE_PATH = PROJECT_ROOT / "experience_learning.py"
CHARACTER_LEARNING_PATH = PROJECT_ROOT / "character_learning.py"
SELF_DEV_PATH = PROJECT_ROOT / "self_development.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

SELF_DEV_SOURCE = 'from __future__ import annotations\n\nimport hashlib\nimport json\nimport re\nimport threading\nimport time\nfrom pathlib import Path\nfrom typing import Any\n\nfrom character_foundation import (\n    foundation_blocks_learning,\n)\nfrom character_learning import (\n    CHARACTER_LEARNING_PATH,\n)\nfrom experience_learning import (\n    EXPERIENCE_STATE_PATH,\n)\n\n\nSELF_DEVELOPMENT_VERSION = "1.0"\nSELF_DEVELOPMENT_PATH = Path(\n    "evilnae_self_development.json"\n)\n\nREFLECTION_STATE_PATH = Path(\n    "reflection_state.json"\n)\n\n_LOCK = threading.RLock()\n\n_REFRESH_INTERVAL_SECONDS = 30.0\n_LAST_REFRESH_AT = 0.0\n\nARC_DORMANT_AFTER = (\n    30 * 24 * 60 * 60\n)\n\nARC_ARCHIVE_AFTER = (\n    180 * 24 * 60 * 60\n)\n\nARC_GENERIC_COOLDOWN = (\n    6 * 60 * 60\n)\n\nMAX_ARCS = 120\n\nSTYLE_BASELINES = {\n    "brevity_preference": 0.50,\n    "teasing_preference": 0.50,\n    "warmth_preference": 0.50,\n    "slang_preference": 0.45,\n    "emoji_preference": 0.35,\n    "question_preference": 0.25,\n    "initiative_preference": 0.35,\n}\n\nSTYLE_LABELS = {\n    "brevity_preference": "brevity",\n    "teasing_preference": "teasing",\n    "warmth_preference": "warmth",\n    "slang_preference": "slang",\n    "emoji_preference": "emoji",\n    "question_preference": "questions",\n    "initiative_preference": "initiative",\n}\n\n\ndef _normalize(\n    value: Any,\n) -> str:\n    text = str(\n        value\n        or ""\n    ).lower()\n\n    text = re.sub(\n        r"[^a-z0-9äöüß]+",\n        " ",\n        text,\n    )\n\n    return re.sub(\n        r"\\s+",\n        " ",\n        text,\n    ).strip()\n\n\ndef _tokens(\n    value: Any,\n) -> set[str]:\n    return {\n        token\n        for token\n        in _normalize(\n            value\n        ).split()\n        if len(token) >= 3\n    }\n\n\ndef _arc_id(\n    topic_key: str,\n    sentiment: str,\n) -> str:\n    raw = (\n        f"{_normalize(topic_key)}|"\n        f"{str(sentiment or \'\').lower()}"\n    )\n\n    return (\n        "arc_"\n        +\n        hashlib.sha1(\n            raw.encode(\n                "utf-8",\n                errors="ignore",\n            )\n        ).hexdigest()[:18]\n    )\n\n\ndef _default_data() -> dict:\n    return {\n        "version": SELF_DEVELOPMENT_VERSION,\n        "arcs": {},\n        "style_tracks": {},\n        "last_refresh_at": 0.0,\n    }\n\n\ndef _load_json(\n    path: Path,\n    default,\n):\n    if not path.exists():\n        return default\n\n    try:\n        return json.loads(\n            path.read_text(\n                encoding="utf-8"\n            )\n        )\n    except Exception:\n        return default\n\n\ndef _load() -> dict:\n    data = _load_json(\n        SELF_DEVELOPMENT_PATH,\n        _default_data(),\n    )\n\n    if not isinstance(\n        data,\n        dict,\n    ):\n        data = _default_data()\n\n    if not isinstance(\n        data.get(\n            "arcs"\n        ),\n        dict,\n    ):\n        data[\n            "arcs"\n        ] = {}\n\n    if not isinstance(\n        data.get(\n            "style_tracks"\n        ),\n        dict,\n    ):\n        data[\n            "style_tracks"\n        ] = {}\n\n    data[\n        "version"\n    ] = SELF_DEVELOPMENT_VERSION\n\n    return data\n\n\ndef _save(\n    data: dict,\n) -> None:\n    data[\n        "version"\n    ] = SELF_DEVELOPMENT_VERSION\n\n    arcs = data.get(\n        "arcs",\n        {},\n    )\n\n    if isinstance(\n        arcs,\n        dict,\n    ):\n        ranked = sorted(\n            arcs.items(),\n            key=lambda item:\n            float(\n                item[1].get(\n                    "last_supported_at",\n                    0.0,\n                )\n                or 0.0\n            ),\n            reverse=True,\n        )\n\n        data[\n            "arcs"\n        ] = dict(\n            ranked[\n                :MAX_ARCS\n            ]\n        )\n\n    temp = Path(\n        str(\n            SELF_DEVELOPMENT_PATH\n        )\n        +\n        ".tmp"\n    )\n\n    temp.write_text(\n        json.dumps(\n            data,\n            ensure_ascii=False,\n            indent=2,\n        ),\n        encoding="utf-8",\n    )\n\n    temp.replace(\n        SELF_DEVELOPMENT_PATH\n    )\n\n\ndef _safe_float(\n    value,\n    default=0.0,\n) -> float:\n    try:\n        return float(\n            value\n        )\n    except Exception:\n        return float(\n            default\n        )\n\n\ndef _learning_entries() -> dict:\n    data = _load_json(\n        CHARACTER_LEARNING_PATH,\n        {\n            "entries": {},\n        },\n    )\n\n    entries = (\n        data.get(\n            "entries",\n            {},\n        )\n        if isinstance(\n            data,\n            dict,\n        )\n        else {}\n    )\n\n    return (\n        entries\n        if isinstance(\n            entries,\n            dict,\n        )\n        else {}\n    )\n\n\ndef _experience_items() -> list[dict]:\n    data = _load_json(\n        EXPERIENCE_STATE_PATH,\n        {\n            "experiences": [],\n        },\n    )\n\n    experiences = (\n        data.get(\n            "experiences",\n            [],\n        )\n        if isinstance(\n            data,\n            dict,\n        )\n        else []\n    )\n\n    return [\n        item\n        for item\n        in experiences\n        if isinstance(\n            item,\n            dict,\n        )\n    ]\n\n\ndef _reflection_state() -> dict:\n    data = _load_json(\n        REFLECTION_STATE_PATH,\n        {},\n    )\n\n    return (\n        data\n        if isinstance(\n            data,\n            dict,\n        )\n        else {}\n    )\n\n\ndef _aggregate_experience_candidates() -> dict:\n    aggregates = {}\n\n    for item in _experience_items():\n        candidate = item.get(\n            "candidate_preference"\n        )\n\n        if not isinstance(\n            candidate,\n            dict,\n        ):\n            continue\n\n        topic = str(\n            candidate.get(\n                "topic",\n                "",\n            )\n            or ""\n        ).strip()\n\n        topic_key = _normalize(\n            candidate.get(\n                "topic_key",\n                topic,\n            )\n        )\n\n        sentiment = str(\n            candidate.get(\n                "sentiment",\n                "",\n            )\n            or ""\n        ).strip().lower()\n\n        context_hash = str(\n            item.get(\n                "context_hash",\n                "",\n            )\n            or ""\n        )\n\n        experience_id = str(\n            item.get(\n                "experience_id",\n                "",\n            )\n            or ""\n        )\n\n        created_at = _safe_float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n        )\n\n        if (\n            not topic\n            or not topic_key\n            or not sentiment\n            or not context_hash\n        ):\n            continue\n\n        key = (\n            topic_key,\n            sentiment,\n        )\n\n        record = aggregates.setdefault(\n            key,\n            {\n                "topic": topic,\n                "topic_key": topic_key,\n                "sentiment": sentiment,\n                "contexts": set(),\n                "experience_ids": set(),\n                "last_supported_at": 0.0,\n                "promoted_seen": False,\n            },\n        )\n\n        record[\n            "contexts"\n        ].add(\n            context_hash\n        )\n\n        if experience_id:\n            record[\n                "experience_ids"\n            ].add(\n                experience_id\n            )\n\n        record[\n            "last_supported_at"\n        ] = max(\n            _safe_float(\n                record.get(\n                    "last_supported_at",\n                    0.0,\n                )\n            ),\n            created_at,\n        )\n\n        if (\n            item.get(\n                "promoted"\n            )\n            or str(\n                item.get(\n                    "status",\n                    "",\n                )\n            )\n            ==\n            "promoted"\n        ):\n            record[\n                "promoted_seen"\n            ] = True\n\n    return aggregates\n\n\ndef _learning_match(\n    topic_key: str,\n) -> dict | None:\n    entries = (\n        _learning_entries()\n    )\n\n    direct = entries.get(\n        topic_key\n    )\n\n    if isinstance(\n        direct,\n        dict,\n    ):\n        return direct\n\n    for key, entry in (\n        entries.items()\n    ):\n        if not isinstance(\n            entry,\n            dict,\n        ):\n            continue\n\n        if (\n            _normalize(\n                key\n            )\n            ==\n            topic_key\n            or\n            _normalize(\n                entry.get(\n                    "topic",\n                    "",\n                )\n            )\n            ==\n            topic_key\n        ):\n            return entry\n\n    return None\n\n\ndef _stage_for(\n    *,\n    evidence_count: int,\n    learning_entry: dict | None,\n    promoted_seen: bool,\n) -> tuple[str | None, float, bool]:\n    source = ""\n\n    status = ""\n\n    learning_evidence = []\n\n    if isinstance(\n        learning_entry,\n        dict,\n    ):\n        source = str(\n            learning_entry.get(\n                "source",\n                "",\n            )\n            or ""\n        )\n\n        status = str(\n            learning_entry.get(\n                "status",\n                "",\n            )\n            or ""\n        )\n\n        learning_evidence = [\n            str(item)\n            for item in (\n                learning_entry.get(\n                    "evidence_ids",\n                    [],\n                )\n                or []\n            )\n            if str(item).strip()\n        ]\n\n    reflection_validated = bool(\n        promoted_seen\n        or (\n            source\n            ==\n            "experience_reflection_v2"\n            and\n            len(\n                learning_evidence\n            )\n            >= 3\n        )\n    )\n\n    if (\n        reflection_validated\n        and (\n            status\n            ==\n            "favorite_candidate"\n            or\n            evidence_count\n            >= 5\n            or\n            len(\n                learning_evidence\n            )\n            >= 5\n        )\n    ):\n        return (\n            "signature",\n            0.86,\n            True,\n        )\n\n    if reflection_validated:\n        return (\n            "established",\n            0.68,\n            True,\n        )\n\n    if evidence_count >= 3:\n        return (\n            "developing",\n            0.46,\n            False,\n        )\n\n    if evidence_count >= 2:\n        return (\n            "spark",\n            0.26,\n            False,\n        )\n\n    # One isolated interaction is deliberately NOT an arc.\n    return (\n        None,\n        0.0,\n        False,\n    )\n\n\ndef _blocked_by_foundation(\n    topic: str,\n) -> bool:\n    try:\n        blocked, _ = (\n            foundation_blocks_learning(\n                topic\n            )\n        )\n\n        return bool(\n            blocked\n        )\n\n    except Exception:\n        return False\n\n\ndef _refresh_arcs(\n    data: dict,\n    *,\n    now: float,\n) -> int:\n    arcs = data[\n        "arcs"\n    ]\n\n    aggregates = (\n        _aggregate_experience_candidates()\n    )\n\n    changed = 0\n    seen_ids = set()\n\n    for (\n        topic_key,\n        sentiment,\n    ), record in aggregates.items():\n\n        topic = str(\n            record[\n                "topic"\n            ]\n        )\n\n        if _blocked_by_foundation(\n            topic\n        ):\n            continue\n\n        evidence_count = len(\n            record[\n                "contexts"\n            ]\n        )\n\n        learning_entry = (\n            _learning_match(\n                topic_key\n            )\n        )\n\n        (\n            computed_stage,\n            strength,\n            reflection_validated,\n        ) = _stage_for(\n            evidence_count=(\n                evidence_count\n            ),\n            learning_entry=(\n                learning_entry\n            ),\n            promoted_seen=bool(\n                record.get(\n                    "promoted_seen"\n                )\n            ),\n        )\n\n        if computed_stage is None:\n            continue\n\n        arc_id = _arc_id(\n            topic_key,\n            sentiment,\n        )\n\n        seen_ids.add(\n            arc_id\n        )\n\n        old = dict(\n            arcs.get(\n                arc_id,\n                {},\n            )\n            or {}\n        )\n\n        created_at = _safe_float(\n            old.get(\n                "created_at",\n                0.0,\n            )\n        )\n\n        if not created_at:\n            created_at = now\n\n        last_supported_at = (\n            _safe_float(\n                record.get(\n                    "last_supported_at",\n                    0.0,\n                )\n            )\n            or now\n        )\n\n        age = max(\n            0.0,\n            now\n            -\n            last_supported_at,\n        )\n\n        stage = (\n            computed_stage\n        )\n\n        if age >= ARC_ARCHIVE_AFTER:\n            stage = "archived"\n\n        elif age >= ARC_DORMANT_AFTER:\n            stage = "dormant"\n\n        updated = {\n            "arc_id": arc_id,\n            "kind": "interest",\n            "topic": topic,\n            "topic_key": topic_key,\n            "sentiment": sentiment,\n            "stage": stage,\n            "underlying_stage": (\n                computed_stage\n            ),\n            "strength": round(\n                strength,\n                3,\n            ),\n            "evidence_count": (\n                evidence_count\n            ),\n            "reflection_validated": (\n                reflection_validated\n            ),\n            "created_at": created_at,\n            "updated_at": now,\n            "last_supported_at": (\n                last_supported_at\n            ),\n            "last_used_at": _safe_float(\n                old.get(\n                    "last_used_at",\n                    0.0,\n                )\n            ),\n            "use_count": int(\n                old.get(\n                    "use_count",\n                    0,\n                )\n                or 0\n            ),\n        }\n\n        if updated != old:\n            changed += 1\n\n        arcs[\n            arc_id\n        ] = updated\n\n    for (\n        arc_id,\n        old,\n    ) in list(\n        arcs.items()\n    ):\n        if arc_id in seen_ids:\n            continue\n\n        updated = dict(\n            old\n        )\n\n        last_supported_at = _safe_float(\n            updated.get(\n                "last_supported_at",\n                0.0,\n            )\n        )\n\n        age = (\n            max(\n                0.0,\n                now\n                -\n                last_supported_at,\n            )\n            if last_supported_at\n            else ARC_ARCHIVE_AFTER\n        )\n\n        new_stage = str(\n            updated.get(\n                "stage",\n                "dormant",\n            )\n        )\n\n        if age >= ARC_ARCHIVE_AFTER:\n            new_stage = "archived"\n\n        elif age >= ARC_DORMANT_AFTER:\n            new_stage = "dormant"\n\n        if (\n            new_stage\n            !=\n            updated.get(\n                "stage"\n            )\n        ):\n            updated[\n                "stage"\n            ] = new_stage\n\n            updated[\n                "updated_at"\n            ] = now\n\n            arcs[\n                arc_id\n            ] = updated\n\n            changed += 1\n\n    return changed\n\n\ndef _refresh_style_tracks(\n    data: dict,\n    *,\n    now: float,\n) -> int:\n    reflection = (\n        _reflection_state()\n    )\n\n    recent = reflection.get(\n        "recent_reflections",\n        [],\n    )\n\n    if not isinstance(\n        recent,\n        list,\n    ):\n        recent = []\n\n    reflection_count = len(\n        recent\n    )\n\n    last_updated = _safe_float(\n        reflection.get(\n            "last_updated",\n            0.0,\n        )\n    )\n\n    tracks = data[\n        "style_tracks"\n    ]\n\n    changed = 0\n\n    for (\n        field,\n        baseline,\n    ) in STYLE_BASELINES.items():\n\n        value = _safe_float(\n            reflection.get(\n                field,\n                baseline,\n            ),\n            baseline,\n        )\n\n        delta = (\n            value\n            -\n            baseline\n        )\n\n        key = STYLE_LABELS[\n            field\n        ]\n\n        old = dict(\n            tracks.get(\n                key,\n                {},\n            )\n            or {}\n        )\n\n        # Needs repeated reflection, not one chat.\n        if (\n            reflection_count < 4\n            or abs(\n                delta\n            )\n            < 0.08\n        ):\n            if old:\n                new = dict(\n                    old\n                )\n\n                new[\n                    "stage"\n                ] = "dormant"\n\n                new[\n                    "updated_at"\n                ] = now\n\n                if new != old:\n                    tracks[\n                        key\n                    ] = new\n\n                    changed += 1\n\n            continue\n\n        age = (\n            max(\n                0.0,\n                now\n                -\n                last_updated,\n            )\n            if last_updated\n            else ARC_ARCHIVE_AFTER\n        )\n\n        if age >= ARC_ARCHIVE_AFTER:\n            stage = "archived"\n\n        elif age >= ARC_DORMANT_AFTER:\n            stage = "dormant"\n\n        elif (\n            reflection_count >= 8\n            and\n            abs(\n                delta\n            )\n            >= 0.12\n        ):\n            stage = "established"\n\n        else:\n            stage = "developing"\n\n        direction = (\n            "more"\n            if delta > 0\n            else "less"\n        )\n\n        updated = {\n            "track": key,\n            "direction": direction,\n            "stage": stage,\n            "strength": round(\n                min(\n                    1.0,\n                    abs(\n                        delta\n                    )\n                    *\n                    3.0,\n                ),\n                3,\n            ),\n            "reflection_count": (\n                reflection_count\n            ),\n            "last_reflection_at": (\n                last_updated\n            ),\n            "updated_at": now,\n        }\n\n        if updated != old:\n            changed += 1\n\n        tracks[\n            key\n        ] = updated\n\n    return changed\n\n\ndef refresh_self_development(\n    *,\n    now: float | None = None,\n    force=False,\n) -> dict:\n    global _LAST_REFRESH_AT\n\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    with _LOCK:\n        if (\n            not force\n            and\n            _LAST_REFRESH_AT\n            and\n            now\n            -\n            _LAST_REFRESH_AT\n            <\n            _REFRESH_INTERVAL_SECONDS\n        ):\n            data = _load()\n\n            return {\n                "changed": 0,\n                "reason": "refresh_cooldown",\n                "data": data,\n            }\n\n        data = _load()\n\n        arc_changes = (\n            _refresh_arcs(\n                data,\n                now=now,\n            )\n        )\n\n        style_changes = (\n            _refresh_style_tracks(\n                data,\n                now=now,\n            )\n        )\n\n        data[\n            "last_refresh_at"\n        ] = now\n\n        _save(\n            data\n        )\n\n        _LAST_REFRESH_AT = now\n\n    return {\n        "changed": (\n            arc_changes\n            +\n            style_changes\n        ),\n        "arc_changes": arc_changes,\n        "style_changes": style_changes,\n        "reason": "refreshed",\n        "data": data,\n    }\n\n\ndef observe_development_from_experience(\n    result,\n) -> dict:\n    if not isinstance(\n        result,\n        dict,\n    ):\n        return {\n            "changed": 0,\n            "reason": "invalid_experience_result",\n        }\n\n    candidate = result.get(\n        "candidate"\n    )\n\n    cluster_count = int(\n        result.get(\n            "cluster_count",\n            0,\n        )\n        or 0\n    )\n\n    # One interaction is not enough to create an Arc.\n    if (\n        not isinstance(\n            candidate,\n            dict,\n        )\n        or cluster_count < 2\n    ):\n        return {\n            "changed": 0,\n            "reason": "not_enough_arc_evidence",\n        }\n\n    return refresh_self_development(\n        force=True\n    )\n\n\ndef observe_development_from_reflection(\n    metadata,\n) -> dict:\n    if not isinstance(\n        metadata,\n        dict,\n    ):\n        return {\n            "changed": 0,\n            "reason": "invalid_reflection_metadata",\n        }\n\n    preference = metadata.get(\n        "preference_result"\n    )\n\n    if not isinstance(\n        preference,\n        dict,\n    ):\n        return {\n            "changed": 0,\n            "reason": "no_preference_reflection",\n        }\n\n    reason = str(\n        preference.get(\n            "reason",\n            "",\n        )\n        or ""\n    )\n\n    if (\n        preference.get(\n            "promoted"\n        )\n        or reason\n        in {\n            "needs_more_independent_experiences",\n            "reflected_preference_promoted",\n        }\n    ):\n        return refresh_self_development(\n            force=True\n        )\n\n    return {\n        "changed": 0,\n        "reason": "reflection_not_arc_relevant",\n    }\n\n\ndef _topic_is_relevant(\n    topic: str,\n    user_text: str,\n) -> bool:\n    topic_tokens = _tokens(\n        topic\n    )\n\n    query_tokens = _tokens(\n        user_text\n    )\n\n    if not topic_tokens:\n        return False\n\n    return bool(\n        topic_tokens\n        &\n        query_tokens\n    )\n\n\ndef _arc_visible(\n    arc: dict,\n    *,\n    user_text: str,\n    now: float,\n) -> bool:\n    stage = str(\n        arc.get(\n            "stage",\n            "",\n        )\n    )\n\n    if stage in {\n        "archived",\n        "dormant",\n    }:\n        return False\n\n    relevant = _topic_is_relevant(\n        str(\n            arc.get(\n                "topic",\n                "",\n            )\n        ),\n        user_text,\n    )\n\n    if stage in {\n        "spark",\n        "developing",\n    }:\n        return relevant\n\n    if relevant:\n        return True\n\n    last_used_at = _safe_float(\n        arc.get(\n            "last_used_at",\n            0.0,\n        )\n    )\n\n    if (\n        last_used_at\n        and\n        now\n        -\n        last_used_at\n        <\n        ARC_GENERIC_COOLDOWN\n    ):\n        return False\n\n    return True\n\n\ndef _arc_rank(\n    arc: dict,\n    *,\n    user_text: str,\n) -> tuple:\n    relevant = _topic_is_relevant(\n        str(\n            arc.get(\n                "topic",\n                "",\n            )\n        ),\n        user_text,\n    )\n\n    stage_score = {\n        "signature": 4,\n        "established": 3,\n        "developing": 2,\n        "spark": 1,\n    }.get(\n        str(\n            arc.get(\n                "stage",\n                "",\n            )\n        ),\n        0,\n    )\n\n    return (\n        1 if relevant else 0,\n        stage_score,\n        _safe_float(\n            arc.get(\n                "strength",\n                0.0,\n            )\n        ),\n        _safe_float(\n            arc.get(\n                "last_supported_at",\n                0.0,\n            )\n        ),\n    )\n\n\ndef format_self_development_for_prompt(\n    user_text: str = "",\n    *,\n    limit=3,\n) -> str:\n    refresh_self_development()\n\n    now = time.time()\n\n    with _LOCK:\n        data = _load()\n\n    arcs = [\n        dict(\n            arc\n        )\n        for arc in (\n            data.get(\n                "arcs",\n                {}\n            )\n            or {}\n        ).values()\n        if isinstance(\n            arc,\n            dict,\n        )\n        and\n        _arc_visible(\n            arc,\n            user_text=user_text,\n            now=now,\n        )\n    ]\n\n    arcs.sort(\n        key=lambda arc:\n        _arc_rank(\n            arc,\n            user_text=user_text,\n        ),\n        reverse=True,\n    )\n\n    selected = arcs[\n        :max(\n            1,\n            int(\n                limit\n            ),\n        )\n    ]\n\n    tracks = [\n        dict(\n            track\n        )\n        for track in (\n            data.get(\n                "style_tracks",\n                {}\n            )\n            or {}\n        ).values()\n        if isinstance(\n            track,\n            dict,\n        )\n        and\n        str(\n            track.get(\n                "stage",\n                "",\n            )\n        )\n        in {\n            "developing",\n            "established",\n        }\n    ]\n\n    tracks.sort(\n        key=lambda track: (\n            1\n            if track.get(\n                "stage"\n            )\n            ==\n            "established"\n            else 0,\n            _safe_float(\n                track.get(\n                    "strength",\n                    0.0,\n                )\n            ),\n        ),\n        reverse=True,\n    )\n\n    lines = [\n        (\n            "[SELF DEVELOPMENT / LONG-RUNNING ARCS "\n            f"v{SELF_DEVELOPMENT_VERSION}]"\n        ),\n        (\n            "Dieser Layer liegt UNTER der Character Foundation "\n            "und UNTER bestätigten Fakten."\n        ),\n        (\n            "Arcs sind langfristige Entwicklungstendenzen, "\n            "keine neuen Ereignisse und keine Lore."\n        ),\n    ]\n\n    if selected:\n        lines.append(\n            "Aktive Interest-Arcs:"\n        )\n\n        for arc in selected:\n            stage = str(\n                arc.get(\n                    "stage",\n                    ""\n                )\n            )\n\n            topic = str(\n                arc.get(\n                    "topic",\n                    ""\n                )\n            )\n\n            sentiment = str(\n                arc.get(\n                    "sentiment",\n                    ""\n                )\n            )\n\n            evidence = int(\n                arc.get(\n                    "evidence_count",\n                    0,\n                )\n                or 0\n            )\n\n            validated = bool(\n                arc.get(\n                    "reflection_validated",\n                    False,\n                )\n            )\n\n            lines.append(\n                (\n                    f"- {topic}: "\n                    f"stage={stage}, "\n                    f"sentiment={sentiment}, "\n                    f"independent_evidence={evidence}, "\n                    f"reflection_validated={validated}"\n                )\n            )\n\n    else:\n        lines.append(\n            "Keine aktuell relevante Arc für diesen Turn."\n        )\n\n    if tracks:\n        lines.append(\n            "Langsame Style-Entwicklung:"\n        )\n\n        for track in tracks[:2]:\n            lines.append(\n                (\n                    f"- {track.get(\'track\')}: "\n                    f"{track.get(\'direction\')} "\n                    f"({track.get(\'stage\')})"\n                )\n            )\n\n    lines.extend(\n        [\n            "HARD RULES:",\n            (\n                "- spark/developing ist KEIN stabiler Self-Fact; "\n                "nur aufgreifen, wenn der User das Thema selbst berührt."\n            ),\n            (\n                "- established/signature darf subtil Verhalten färben, "\n                "aber NICHT in jeder Antwort erwähnt werden."\n            ),\n            (\n                "- Niemals ein Erlebnis erfinden, um einen Arc zu erklären."\n            ),\n            (\n                "- Keine Arc darf Foundation/Canon überschreiben."\n            ),\n            (\n                "- Keine aktuelle Aktivität aus einem Long-running Arc ableiten."\n            ),\n            (\n                "- Arc-Cooldown beachten: nicht dasselbe Thema "\n                "immer wieder ungefragt hineinziehen."\n            ),\n        ]\n    )\n\n    return "\\n".join(\n        lines\n    )\n\n\ndef register_arc_surface_use(\n    answer: str,\n    *,\n    now: float | None = None,\n) -> int:\n    text = _normalize(\n        answer\n    )\n\n    if not text:\n        return 0\n\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    refresh_self_development(\n        now=now,\n    )\n\n    changed = 0\n\n    with _LOCK:\n        data = _load()\n\n        arcs = data.get(\n            "arcs",\n            {},\n        )\n\n        for (\n            arc_id,\n            arc,\n        ) in arcs.items():\n\n            if not isinstance(\n                arc,\n                dict,\n            ):\n                continue\n\n            stage = str(\n                arc.get(\n                    "stage",\n                    "",\n                )\n            )\n\n            if stage not in {\n                "established",\n                "signature",\n            }:\n                continue\n\n            topic = _normalize(\n                arc.get(\n                    "topic",\n                    "",\n                )\n            )\n\n            if (\n                len(\n                    topic\n                )\n                < 3\n                or topic not in text\n            ):\n                continue\n\n            updated = dict(\n                arc\n            )\n\n            updated[\n                "last_used_at"\n            ] = now\n\n            updated[\n                "use_count"\n            ] = int(\n                updated.get(\n                    "use_count",\n                    0,\n                )\n                or 0\n            ) + 1\n\n            updated[\n                "updated_at"\n            ] = now\n\n            arcs[\n                arc_id\n            ] = updated\n\n            changed += 1\n\n        if changed:\n            _save(\n                data\n            )\n\n    return changed\n\n\ndef self_development_stats() -> dict:\n    refresh_self_development()\n\n    with _LOCK:\n        data = _load()\n\n    arcs = [\n        arc\n        for arc in (\n            data.get(\n                "arcs",\n                {}\n            )\n            or {}\n        ).values()\n        if isinstance(\n            arc,\n            dict,\n        )\n    ]\n\n    stages = {}\n\n    for arc in arcs:\n        stage = str(\n            arc.get(\n                "stage",\n                "unknown",\n            )\n        )\n\n        stages[\n            stage\n        ] = stages.get(\n            stage,\n            0,\n        ) + 1\n\n    tracks = [\n        track\n        for track in (\n            data.get(\n                "style_tracks",\n                {}\n            )\n            or {}\n        ).values()\n        if isinstance(\n            track,\n            dict,\n        )\n        and\n        str(\n            track.get(\n                "stage",\n                "",\n            )\n        )\n        in {\n            "developing",\n            "established",\n        }\n    ]\n\n    return {\n        "version": SELF_DEVELOPMENT_VERSION,\n        "arcs": len(\n            arcs\n        ),\n        "active_arcs": sum(\n            count\n            for stage, count\n            in stages.items()\n            if stage\n            in {\n                "spark",\n                "developing",\n                "established",\n                "signature",\n            }\n        ),\n        "stages": stages,\n        "style_tracks": len(\n            tracks\n        ),\n    }\n\n\ndef format_self_development_debug(\n    result=None,\n) -> str:\n    stats = (\n        self_development_stats()\n    )\n\n    if not result:\n        return (\n            "[SELF DEVELOPMENT] "\n            f"v={SELF_DEVELOPMENT_VERSION} "\n            f"arcs={stats[\'arcs\']} "\n            f"active={stats[\'active_arcs\']} "\n            f"tracks={stats[\'style_tracks\']}"\n        )\n\n    return (\n        "[SELF DEVELOPMENT] "\n        f"v={SELF_DEVELOPMENT_VERSION} "\n        f"changed={result.get(\'changed\', 0)} "\n        f"reason={result.get(\'reason\', \'\')} "\n        f"arcs={stats[\'arcs\']} "\n        f"active={stats[\'active_arcs\']}"\n    )\n\n\ndef _self_test() -> int:\n    global SELF_DEVELOPMENT_PATH\n    global REFLECTION_STATE_PATH\n    global _LAST_REFRESH_AT\n\n    import tempfile\n\n    original_dev = (\n        SELF_DEVELOPMENT_PATH\n    )\n\n    original_reflection = (\n        REFLECTION_STATE_PATH\n    )\n\n    original_experience = (\n        EXPERIENCE_STATE_PATH\n    )\n\n    original_learning = (\n        CHARACTER_LEARNING_PATH\n    )\n\n    tests = []\n\n    try:\n        with tempfile.TemporaryDirectory() as tmp:\n            tmp = Path(\n                tmp\n            )\n\n            SELF_DEVELOPMENT_PATH = (\n                tmp\n                /\n                "development.json"\n            )\n\n            REFLECTION_STATE_PATH = (\n                tmp\n                /\n                "reflection.json"\n            )\n\n            # Imported Path constants are module globals; replace them\n            # locally for this deterministic self-test.\n            globals()[\n                "EXPERIENCE_STATE_PATH"\n            ] = (\n                tmp\n                /\n                "experiences.json"\n            )\n\n            globals()[\n                "CHARACTER_LEARNING_PATH"\n            ] = (\n                tmp\n                /\n                "character_learning.json"\n            )\n\n            base_now = time.time()\n\n            def write_experiences(\n                count,\n                *,\n                last_offset=0.0,\n            ):\n                items = []\n\n                for index in range(\n                    count\n                ):\n                    created = (\n                        base_now\n                        +\n                        last_offset\n                        +\n                        index\n                    )\n\n                    items.append(\n                        {\n                            "experience_id":\n                                f"exp{index}",\n                            "created_at":\n                                created,\n                            "context_hash":\n                                f"ctx{index}",\n                            "candidate_preference":\n                                {\n                                    "topic":\n                                        "Hades",\n                                    "topic_key":\n                                        "hades",\n                                    "sentiment":\n                                        "like",\n                                },\n                            "status":\n                                "candidate",\n                            "promoted":\n                                False,\n                        }\n                    )\n\n                globals()[\n                    "EXPERIENCE_STATE_PATH"\n                ].write_text(\n                    json.dumps(\n                        {\n                            "experiences":\n                                items\n                        }\n                    ),\n                    encoding="utf-8",\n                )\n\n            globals()[\n                "CHARACTER_LEARNING_PATH"\n            ].write_text(\n                json.dumps(\n                    {\n                        "entries": {}\n                    }\n                ),\n                encoding="utf-8",\n            )\n\n            REFLECTION_STATE_PATH.write_text(\n                json.dumps(\n                    {\n                        "recent_reflections":\n                            [],\n                    }\n                ),\n                encoding="utf-8",\n            )\n\n            write_experiences(\n                1\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 10,\n                force=True,\n            )\n\n            tests.append(\n                (\n                    "one interaction creates no arc",\n                    self_development_stats()[\n                        "arcs"\n                    ]\n                    ==\n                    0,\n                )\n            )\n\n            write_experiences(\n                2\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 20,\n                force=True,\n            )\n\n            data = _load()\n\n            arc = next(\n                iter(\n                    data[\n                        "arcs"\n                    ].values()\n                )\n            )\n\n            tests.append(\n                (\n                    "two contexts create spark",\n                    arc[\n                        "stage"\n                    ]\n                    ==\n                    "spark"\n                    and\n                    arc[\n                        "evidence_count"\n                    ]\n                    ==\n                    2,\n                )\n            )\n\n            # Duplicate context does not count independently.\n            duplicate_data = {\n                "experiences": [\n                    {\n                        "experience_id":\n                            "a",\n                        "created_at":\n                            base_now,\n                        "context_hash":\n                            "same",\n                        "candidate_preference":\n                            {\n                                "topic":\n                                    "Hades",\n                                "topic_key":\n                                    "hades",\n                                "sentiment":\n                                    "like",\n                            },\n                    },\n                    {\n                        "experience_id":\n                            "b",\n                        "created_at":\n                            base_now + 1,\n                        "context_hash":\n                            "same",\n                        "candidate_preference":\n                            {\n                                "topic":\n                                    "Hades",\n                                "topic_key":\n                                    "hades",\n                                "sentiment":\n                                    "like",\n                            },\n                    },\n                ]\n            }\n\n            globals()[\n                "EXPERIENCE_STATE_PATH"\n            ].write_text(\n                json.dumps(\n                    duplicate_data\n                ),\n                encoding="utf-8",\n            )\n\n            SELF_DEVELOPMENT_PATH.unlink(\n                missing_ok=True\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 30,\n                force=True,\n            )\n\n            tests.append(\n                (\n                    "duplicate context is not arc evidence",\n                    self_development_stats()[\n                        "arcs"\n                    ]\n                    ==\n                    0,\n                )\n            )\n\n            write_experiences(\n                3\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 40,\n                force=True,\n            )\n\n            data = _load()\n\n            arc = next(\n                iter(\n                    data[\n                        "arcs"\n                    ].values()\n                )\n            )\n\n            tests.append(\n                (\n                    "three contexts create developing arc",\n                    arc[\n                        "stage"\n                    ]\n                    ==\n                    "developing",\n                )\n            )\n\n            globals()[\n                "CHARACTER_LEARNING_PATH"\n            ].write_text(\n                json.dumps(\n                    {\n                        "entries":\n                            {\n                                "hades":\n                                    {\n                                        "topic":\n                                            "Hades",\n                                        "sentiment":\n                                            "like",\n                                        "status":\n                                            "stable",\n                                        "source":\n                                            "experience_reflection_v2",\n                                        "evidence_ids":\n                                            [\n                                                "exp0",\n                                                "exp1",\n                                                "exp2",\n                                            ],\n                                    }\n                            }\n                    }\n                ),\n                encoding="utf-8",\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 50,\n                force=True,\n            )\n\n            arc = next(\n                iter(\n                    _load()[\n                        "arcs"\n                    ].values()\n                )\n            )\n\n            tests.append(\n                (\n                    "reflection promotion establishes arc",\n                    arc[\n                        "stage"\n                    ]\n                    ==\n                    "established"\n                    and\n                    arc[\n                        "reflection_validated"\n                    ],\n                )\n            )\n\n            write_experiences(\n                5\n            )\n\n            globals()[\n                "CHARACTER_LEARNING_PATH"\n            ].write_text(\n                json.dumps(\n                    {\n                        "entries":\n                            {\n                                "hades":\n                                    {\n                                        "topic":\n                                            "Hades",\n                                        "sentiment":\n                                            "like",\n                                        "status":\n                                            "favorite_candidate",\n                                        "source":\n                                            "experience_reflection_v2",\n                                        "evidence_ids":\n                                            [\n                                                "exp0",\n                                                "exp1",\n                                                "exp2",\n                                                "exp3",\n                                                "exp4",\n                                            ],\n                                    }\n                            }\n                    }\n                ),\n                encoding="utf-8",\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 60,\n                force=True,\n            )\n\n            arc = next(\n                iter(\n                    _load()[\n                        "arcs"\n                    ].values()\n                )\n            )\n\n            tests.append(\n                (\n                    "five reflected contexts create signature arc",\n                    arc[\n                        "stage"\n                    ]\n                    ==\n                    "signature",\n                )\n            )\n\n            before = (\n                format_self_development_for_prompt(\n                    "Was zockst du gern?"\n                )\n            )\n\n            tests.append(\n                (\n                    "signature arc enters prompt",\n                    "Hades"\n                    in before,\n                )\n            )\n\n            register_arc_surface_use(\n                "Hades ist schon ziemlich stark.",\n                now=base_now + 70,\n            )\n\n            cooldown_generic = (\n                format_self_development_for_prompt(\n                    "Wie geht es dir heute?"\n                )\n            )\n\n            direct_topic = (\n                format_self_development_for_prompt(\n                    "Was hältst du von Hades?"\n                )\n            )\n\n            tests.append(\n                (\n                    "generic cooldown hides recently used arc",\n                    "Hades"\n                    not in cooldown_generic,\n                )\n            )\n\n            tests.append(\n                (\n                    "direct topic bypasses arc cooldown",\n                    "Hades"\n                    in direct_topic,\n                )\n            )\n\n            REFLECTION_STATE_PATH.write_text(\n                json.dumps(\n                    {\n                        "brevity_preference":\n                            0.63,\n                        "teasing_preference":\n                            0.50,\n                        "warmth_preference":\n                            0.50,\n                        "slang_preference":\n                            0.45,\n                        "emoji_preference":\n                            0.35,\n                        "question_preference":\n                            0.25,\n                        "initiative_preference":\n                            0.35,\n                        "recent_reflections":\n                            [\n                                {},\n                                {},\n                                {},\n                                {},\n                                {},\n                            ],\n                        "last_updated":\n                            base_now + 80,\n                    }\n                ),\n                encoding="utf-8",\n            )\n\n            _LAST_REFRESH_AT = 0.0\n\n            refresh_self_development(\n                now=base_now + 90,\n                force=True,\n            )\n\n            tracks = (\n                _load()[\n                    "style_tracks"\n                ]\n            )\n\n            tests.append(\n                (\n                    "style track needs repeated reflection",\n                    tracks[\n                        "brevity"\n                    ][\n                        "stage"\n                    ]\n                    ==\n                    "developing"\n                    and\n                    tracks[\n                        "brevity"\n                    ][\n                        "direction"\n                    ]\n                    ==\n                    "more",\n                )\n            )\n\n            serialized = (\n                SELF_DEVELOPMENT_PATH.read_text(\n                    encoding="utf-8"\n                )\n            )\n\n            tests.append(\n                (\n                    "no raw chat content stored",\n                    "Was hältst du"\n                    not in serialized\n                    and\n                    "Wie geht es dir"\n                    not in serialized,\n                )\n            )\n\n    finally:\n        SELF_DEVELOPMENT_PATH = (\n            original_dev\n        )\n\n        REFLECTION_STATE_PATH = (\n            original_reflection\n        )\n\n        globals()[\n            "EXPERIENCE_STATE_PATH"\n        ] = (\n            original_experience\n        )\n\n        globals()[\n            "CHARACTER_LEARNING_PATH"\n        ] = (\n            original_learning\n        )\n\n        _LAST_REFRESH_AT = 0.0\n\n    passed = sum(\n        1\n        for _, success\n        in tests\n        if success\n    )\n\n    print()\n    print("=" * 68)\n    print(\n        f"SELF DEVELOPMENT / LONG-RUNNING ARCS "\n        f"v{SELF_DEVELOPMENT_VERSION} TEST"\n    )\n    print("=" * 68)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
SELF_DEV_IMPORT = '\nfrom self_development import (\n    SELF_DEVELOPMENT_VERSION,\n    observe_development_from_experience,\n    observe_development_from_reflection,\n    format_self_development_for_prompt,\n    register_arc_surface_use,\n    self_development_stats,\n    format_self_development_debug,\n)\n\n'
NEW_LIVE_WRAPPERS = '\n\n# =========================================================\n# 3.9.0 SELF DEVELOPMENT / LONG-RUNNING ARC WRAPPERS\n# =========================================================\n\ndef wrap_character_learning_prompt_v3(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        user_text="",\n        *args,\n        **kwargs,\n    ):\n        base = original(\n            user_text,\n            *args,\n            **kwargs,\n        )\n\n        development = (\n            format_self_development_for_prompt(\n                user_text\n            )\n        )\n\n        return (\n            str(\n                base\n                or ""\n            ).strip()\n            +\n            "\\n\\n"\n            +\n            development\n        ).strip()\n\n    return wrapped\n\n\ndef wrap_initiative_prompt_v3(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        kwargs = dict(\n            kwargs\n        )\n\n        channel_context = str(\n            kwargs.get(\n                "channel_context",\n                "",\n            )\n            or ""\n        ).strip()\n\n        development = (\n            format_self_development_for_prompt(\n                ""\n            )\n        )\n\n        kwargs[\n            "channel_context"\n        ] = (\n            (\n                channel_context\n                +\n                "\\n\\n"\n                +\n                development\n            )\n            if channel_context\n            else development\n        )\n\n        return original(\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n'
EXPERIENCE_CAPTURE_OLD = '        result = (\n            capture_experience(\n                user_id=(\n                    _CURRENT_USER_ID.get()\n                ),\n                username=(\n                    _CURRENT_USERNAME.get()\n                ),\n                user_text=user_text,\n                evilnae_answer=(\n                    evilnae_answer\n                ),\n            )\n        )\n\n        print(\n            format_experience_debug(\n                result\n            )\n        )\n'
EXPERIENCE_CAPTURE_NEW = '        result = (\n            capture_experience(\n                user_id=(\n                    _CURRENT_USER_ID.get()\n                ),\n                username=(\n                    _CURRENT_USERNAME.get()\n                ),\n                user_text=user_text,\n                evilnae_answer=(\n                    evilnae_answer\n                ),\n            )\n        )\n\n        development_result = (\n            observe_development_from_experience(\n                result\n            )\n        )\n\n        if int(\n            development_result.get(\n                "changed",\n                0,\n            )\n            or 0\n        ) > 0:\n            print(\n                format_self_development_debug(\n                    development_result\n                )\n            )\n\n        print(\n            format_experience_debug(\n                result\n            )\n        )\n'
REFLECTION_GATE_OLD = '        gated, metadata = (\n            gate_reflection_learning(\n                data\n            )\n        )\n\n        print(\n            "[EXPERIENCE REFLECTION GATE] "\n'
REFLECTION_GATE_NEW = '        gated, metadata = (\n            gate_reflection_learning(\n                data\n            )\n        )\n\n        development_result = (\n            observe_development_from_reflection(\n                metadata\n            )\n        )\n\n        if int(\n            development_result.get(\n                "changed",\n                0,\n            )\n            or 0\n        ) > 0:\n            print(\n                format_self_development_debug(\n                    development_result\n                )\n            )\n\n        print(\n            "[EXPERIENCE REFLECTION GATE] "\n'
SURFACE_USE_OLD = '        print(\n            "[LIVE OUT] "\n            f"{_CURRENT_USERNAME.get()} <- "\n            f"{_short(answer)}"\n        )\n'
SURFACE_USE_NEW = '        register_arc_surface_use(\n            answer\n        )\n\n        print(\n            "[LIVE OUT] "\n            f"{_CURRENT_USERNAME.get()} <- "\n            f"{_short(answer)}"\n        )\n'
BOT_VERSION_OLD = 'BOT_VERSION = "3.8.0-experience-reflection-learning"'
BOT_VERSION_NEW = 'BOT_VERSION = "3.9.0-self-development-arcs"'
LIVE_VERSION_OLD = 'LIVE_STABILITY_VERSION = "1.2-experience-learning"'
LIVE_VERSION_NEW = 'LIVE_STABILITY_VERSION = "1.3-self-development"'
BOT_IMPORT_NAMES_OLD = '    EXPERIENCE_LEARNING_VERSION,\n    experience_stats,\n    ConsoleOutputFilter,\n'
BOT_IMPORT_NAMES_NEW = '    EXPERIENCE_LEARNING_VERSION,\n    experience_stats,\n    SELF_DEVELOPMENT_VERSION,\n    self_development_stats,\n    ConsoleOutputFilter,\n'
BOT_WRAPPER_IMPORT_OLD = '    wrap_apply_learning_signals_v2,\n    wrap_store_reflection_v2,\n)\n'
BOT_WRAPPER_IMPORT_NEW = '    wrap_apply_learning_signals_v2,\n    wrap_store_reflection_v2,\n    wrap_character_learning_prompt_v3,\n    wrap_initiative_prompt_v3,\n)\n'
BOT_ASSIGN_MARKER = 'store_reflection = wrap_store_reflection_v2(\n    store_reflection\n)\n\n\n'
BOT_ASSIGN_ADDITION = 'format_character_learning_for_prompt = (\n    wrap_character_learning_prompt_v3(\n        format_character_learning_for_prompt\n    )\n)\n\nbuild_initiative_prompt = (\n    wrap_initiative_prompt_v3(\n        build_initiative_prompt\n    )\n)\n\n\n'
BOT_STARTUP_EXPERIENCE = '    print(\n        f"Experience Learning v"\n        f"{EXPERIENCE_LEARNING_VERSION}: ACTIVE "\n        f"total={experience_learning_stats.get(\'total\', 0)} "\n        f"candidates={experience_learning_stats.get(\'candidates\', 0)}"\n    )\n\n'
BOT_STARTUP_SELF_DEV = '    self_development_state = (\n        self_development_stats()\n    )\n\n    print(\n        f"Self Development v"\n        f"{SELF_DEVELOPMENT_VERSION}: ACTIVE "\n        f"arcs={self_development_state.get(\'arcs\', 0)} "\n        f"active={self_development_state.get(\'active_arcs\', 0)} "\n        f"tracks={self_development_state.get(\'style_tracks\', 0)}"\n    )\n\n'


EXPECTED_EXPERIENCE = (
    'EXPERIENCE_LEARNING_VERSION = '
    '"2.0.1-evidence-fix"'
)

EXPECTED_CHARACTER = (
    'CHARACTER_LEARNING_VERSION = '
    '"1.2-reflection-gated"'
)


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
    "EVILNAE 3.9.0 — SELF DEVELOPMENT + LONG-RUNNING ARCS"
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
    EXPERIENCE_PATH,
    CHARACTER_LEARNING_PATH,
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

experience = EXPERIENCE_PATH.read_text(
    encoding="utf-8"
)

character = (
    CHARACTER_LEARNING_PATH.read_text(
        encoding="utf-8"
    )
)


if (
    BOT_VERSION_NEW in bot
    and SELF_DEV_PATH.exists()
):
    print(
        "3.9.0 is already installed."
    )
    raise SystemExit(
        0
    )


if BOT_VERSION_OLD not in bot:
    fail(
        "Expected Bot 3.8.0-experience-reflection-learning"
    )


if LIVE_VERSION_OLD not in live:
    fail(
        "Expected Live Stability 1.2-experience-learning"
    )


if EXPECTED_EXPERIENCE not in experience:
    fail(
        "Expected Experience Learning 2.0.1-evidence-fix"
    )


if EXPECTED_CHARACTER not in character:
    fail(
        "Expected Character Learning 1.2-reflection-gated"
    )


if SELF_DEV_PATH.exists():
    fail(
        "self_development.py already exists unexpectedly."
    )


ok(
    "3.8.0 architecture base detected"
)


# =========================================================
# PATCH LIVE STABILITY
# =========================================================

live = replace_once(
    live,
    LIVE_VERSION_OLD,
    LIVE_VERSION_NEW,
    "Live Stability -> 1.3-self-development",
)


experience_import_marker = (
    "from experience_learning import (\n"
    "    EXPERIENCE_LEARNING_VERSION,\n"
    "    register_salience_result,\n"
    "    capture_experience,\n"
    "    format_experience_for_reflection,\n"
    "    gate_reflection_learning,\n"
    "    annotate_reflection_record,\n"
    "    experience_stats,\n"
    "    format_experience_debug,\n"
    ")\n\n"
)


live = insert_after_once(
    live,
    experience_import_marker,
    SELF_DEV_IMPORT,
    "Live Stability imports Self Development",
)


live = replace_once(
    live,
    '            "Experience Learning v",\n'
    '            "Qwen Surface Writer v",\n',
    '            "Experience Learning v",\n'
    '            "Self Development v",\n'
    '            "Qwen Surface Writer v",\n',
    "Compact console allows Self Development startup",
)


live = replace_once(
    live,
    EXPERIENCE_CAPTURE_OLD,
    EXPERIENCE_CAPTURE_NEW,
    "Experience observations refresh long-running arcs",
)


live = replace_once(
    live,
    REFLECTION_GATE_OLD,
    REFLECTION_GATE_NEW,
    "Reflection promotion refreshes long-running arcs",
)


live = replace_once(
    live,
    SURFACE_USE_OLD,
    SURFACE_USE_NEW,
    "Arc surface-use cooldown tracking",
)


live = insert_before_once(
    live,
    "# =========================================================\n"
    "# SELF TEST\n"
    "# =========================================================\n",
    NEW_LIVE_WRAPPERS,
    "Live Stability Self Development prompt wrappers",
)


# =========================================================
# PATCH BOT
# =========================================================

bot = replace_once(
    bot,
    BOT_VERSION_OLD,
    BOT_VERSION_NEW,
    "Bot version -> 3.9.0-self-development-arcs",
)


bot = replace_once(
    bot,
    BOT_IMPORT_NAMES_OLD,
    BOT_IMPORT_NAMES_NEW,
    "Bot imports Self Development version/stats",
)


bot = replace_once(
    bot,
    BOT_WRAPPER_IMPORT_OLD,
    BOT_WRAPPER_IMPORT_NEW,
    "Bot imports Self Development wrappers",
)


bot = insert_after_once(
    bot,
    BOT_ASSIGN_MARKER,
    BOT_ASSIGN_ADDITION,
    "Bot installs Character/Initiative arc-context wrappers",
)


bot = insert_after_once(
    bot,
    BOT_STARTUP_EXPERIENCE,
    BOT_STARTUP_SELF_DEV,
    "Startup Self Development banner",
)


# =========================================================
# PRE-WRITE INVARIANTS
# =========================================================

for marker in (
    'SELF_DEVELOPMENT_VERSION = "1.0"',
    "evilnae_self_development.json",
    "ARC_DORMANT_AFTER",
    "ARC_ARCHIVE_AFTER",
    "ARC_GENERIC_COOLDOWN",
    "one interaction creates no arc",
    "two contexts create spark",
    "reflection promotion establishes arc",
    "five reflected contexts create signature arc",
    "style track needs repeated reflection",
):
    if marker not in SELF_DEV_SOURCE:
        fail(
            "self_development.py missing invariant: "
            f"{marker}"
        )


for marker in (
    LIVE_VERSION_NEW,
    "observe_development_from_experience",
    "observe_development_from_reflection",
    "register_arc_surface_use",
    "wrap_character_learning_prompt_v3",
    "wrap_initiative_prompt_v3",
    '"Self Development v"',
):
    if marker not in live:
        fail(
            f"Patched live_stability.py missing invariant: {marker}"
        )


for marker in (
    BOT_VERSION_NEW,
    "SELF_DEVELOPMENT_VERSION",
    "self_development_stats",
    "wrap_character_learning_prompt_v3",
    "wrap_initiative_prompt_v3",
    "Self Development v",
):
    if marker not in bot:
        fail(
            f"Patched bot.py missing invariant: {marker}"
        )


syntax_check(
    SELF_DEV_SOURCE,
    "self_development.py",
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
    "no extra OpenAI call":
        (
            "AsyncOpenAI"
            not in SELF_DEV_SOURCE
            and
            "openai_client"
            not in SELF_DEV_SOURCE
        ),

    "no extra Qwen call":
        (
            "run_local_model"
            not in SELF_DEV_SOURCE
            and
            "urllib.request"
            not in SELF_DEV_SOURCE
        ),

    "single interaction cannot create arc":
        (
            "evidence_count >= 2"
            in SELF_DEV_SOURCE
            and
            "One isolated interaction is deliberately NOT an arc"
            in SELF_DEV_SOURCE
        ),

    "independent context evidence":
        (
            '"contexts": set()'
            in SELF_DEV_SOURCE
            and
            "context_hash"
            in SELF_DEV_SOURCE
        ),

    "reflection validation":
        (
            "experience_reflection_v2"
            in SELF_DEV_SOURCE
            and
            "reflection_validated"
            in SELF_DEV_SOURCE
        ),

    "foundation authority":
        (
            "foundation_blocks_learning"
            in SELF_DEV_SOURCE
        ),

    "current state separation":
        (
            "Keine aktuelle Aktivität aus einem Long-running Arc ableiten."
            in SELF_DEV_SOURCE
        ),

    "arc cooldown":
        (
            "ARC_GENERIC_COOLDOWN"
            in SELF_DEV_SOURCE
            and
            "register_arc_surface_use"
            in live
        ),

    "style development requires reflection":
        (
            "reflection_count < 4"
            in SELF_DEV_SOURCE
        ),

    "initiative integration":
        (
            "wrap_initiative_prompt_v3"
            in bot
        ),

    "normal reply integration":
        (
            "wrap_character_learning_prompt_v3"
            in bot
        ),

    "compact startup":
        (
            "Self Development v"
            in bot
            and
            "Self Development v"
            in live
        ),

    "no raw chat persistence API":
        (
            "user_message"
            not in SELF_DEV_SOURCE
            and
            "evilnae_answer"
            not in SELF_DEV_SOURCE
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
# PRE-WRITE BEHAVIOR TEST
# =========================================================

namespace = {
    "__name__": "_evilnae_390_preflight_",
}


try:
    exec(
        compile(
            SELF_DEV_SOURCE,
            "self_development.py",
            "exec",
        ),
        namespace,
    )

except Exception as error:
    fail(
        "Could not load Self Development preflight: "
        f"{type(error).__name__}: {error}"
    )


self_test = namespace.get(
    "_self_test"
)


if not callable(
    self_test
):
    fail(
        "Self Development self-test unavailable."
    )


if self_test() != 0:
    fail(
        "Self Development behavior self-test failed."
    )


ok(
    "Self Development behavior self-test: PASS"
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
    SELF_DEV_PATH,
    SELF_DEV_SOURCE,
)

ok(
    "Created: self_development.py"
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
# COMPILE
# =========================================================

compile_targets = [
    SELF_DEV_PATH,
    LIVE_PATH,
    BOT_PATH,
    EXPERIENCE_PATH,
    CHARACTER_LEARNING_PATH,
]


result = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        *[
            str(path)
            for path
            in compile_targets
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
    "Post-install py_compile: 5/5"
)


# =========================================================
# REAL FILE SELF TEST
# =========================================================

result = subprocess.run(
    [
        sys.executable,
        str(
            SELF_DEV_PATH
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
        "Self Development real-file self-test failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    "Post-install Self Development self-test: PASS"
)


print()
print("=" * 78)
print(
    "EVILNAE 3.9.0 SELF DEVELOPMENT + LONG-RUNNING ARCS INSTALLED"
)
print("=" * 78)

print()
print("Long-running Interest Arcs:")
print(
    "  1 independent context  -> no arc"
)
print(
    "  2 independent contexts -> spark"
)
print(
    "  3 independent contexts -> developing"
)
print(
    "  reflected/promotion     -> established"
)
print(
    "  strong 5+ evidence      -> signature"
)

print()
print("Safety / authority:")
print(
    "  [✓] Foundation remains highest authority"
)
print(
    "  [✓] no automatic writes into fixed Self Model"
)
print(
    "  [✓] Current Character State stays separate"
)
print(
    "  [✓] no raw Discord message stored"
)
print(
    "  [✓] no single chat can create a long-running arc"
)
print(
    "  [✓] dormant after 30 days without support"
)
print(
    "  [✓] archived after 180 days without support"
)

print()
print("Naturalness:")
print(
    "  [✓] spark/developing only surface when current topic is relevant"
)
print(
    "  [✓] established/signature can subtly influence normal replies"
)
print(
    "  [✓] 6h generic reuse cooldown after an arc is mentioned"
)
print(
    "  [✓] direct user topic bypasses cooldown"
)
print(
    "  [✓] Initiative can see mature arcs without forcing them"
)

print()
print("Self Development:")
print(
    "  [✓] repeated Reflection can create slow style-development tracks"
)
print(
    "  [✓] brevity / teasing / warmth / slang / emoji / questions / initiative"
)
print(
    "  [✓] style track needs at least 4 reflections"
)
print(
    "  [✓] strong stable movement needs repeated evidence"
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
print("Runtime file:")
print(
    "  evilnae_self_development.json"
)

print()
print("Versions:")
print(
    "  Bot: 3.9.0-self-development-arcs"
)
print(
    "  Live Stability: 1.3-self-development"
)
print(
    "  Self Development: 1.0"
)
print(
    "  Experience Learning: 2.0.1-evidence-fix"
)
print(
    "  Character Learning: 1.2-reflection-gated"
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
    "  After this succeeds, next major block is "
    "Agency / Initiative 2.0 + Server Awareness."
)

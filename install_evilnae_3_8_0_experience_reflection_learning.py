from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
CHARACTER_LEARNING_PATH = PROJECT_ROOT / "character_learning.py"
EXPERIENCE_PATH = PROJECT_ROOT / "experience_learning.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.7.0-social-emotional-state"'
TARGET_BOT = 'BOT_VERSION = "3.8.0-experience-reflection-learning"'
EXPECTED_LIVE = 'LIVE_STABILITY_VERSION = "1.1-social-state"'
TARGET_LIVE = 'LIVE_STABILITY_VERSION = "1.2-experience-learning"'
EXPECTED_CHARACTER_LEARNING = 'CHARACTER_LEARNING_VERSION = "1.1"'
TARGET_CHARACTER_LEARNING = 'CHARACTER_LEARNING_VERSION = "1.2-reflection-gated"'

EXPERIENCE_SOURCE = 'from __future__ import annotations\n\nimport contextvars\nimport hashlib\nimport json\nimport re\nimport threading\nimport time\nfrom pathlib import Path\nfrom typing import Any\n\nfrom character_learning import (\n    _extract_preference,\n    _valid_preference_topic,\n    _manipulative,\n)\n\n\nEXPERIENCE_LEARNING_VERSION = "2.0"\nEXPERIENCE_STATE_PATH = Path(\n    "evilnae_experiences.json"\n)\n\nMAX_EXPERIENCES = 600\nMAX_EVIDENCE_AGE_SECONDS = (\n    120 * 24 * 60 * 60\n)\n\n_LOCK = threading.RLock()\n\n_LATEST_SALIENCE_BY_USER = {}\n\n_CURRENT_REFLECTION_EXPERIENCE_ID = (\n    contextvars.ContextVar(\n        "evilnae_reflection_experience_id",\n        default="",\n    )\n)\n\n_PROMOTION_OVERRIDE = None\n\n\nIMPORTANT_SIGNALS = {\n    "positive_relationship_signal",\n    "negative_relationship_signal",\n    "relationship_repair",\n    "vulnerability",\n    "explicit_feedback",\n    "explicit_correction",\n    "shared_callback",\n    "personal_milestone",\n    "personal_preference",\n}\n\nDELTA_FIELDS = (\n    "brevity_delta",\n    "teasing_delta",\n    "warmth_delta",\n    "slang_delta",\n    "emoji_delta",\n    "question_delta",\n    "initiative_delta",\n)\n\nTEXT_LEARNING_FIELDS = (\n    "preferred_pattern",\n    "discouraged_pattern",\n    "behavior_note",\n)\n\n\ndef _normalize(\n    text: Any,\n) -> str:\n    value = str(\n        text\n        or ""\n    ).lower()\n\n    value = re.sub(\n        r"\\s+",\n        " ",\n        value,\n    ).strip()\n\n    return value\n\n\ndef _hash(\n    text: Any,\n) -> str:\n    value = _normalize(\n        text\n    )\n\n    return hashlib.sha1(\n        value.encode(\n            "utf-8",\n            errors="ignore",\n        )\n    ).hexdigest()\n\n\ndef _clean_topic(\n    topic: str,\n) -> str:\n    value = re.sub(\n        r"\\s+",\n        " ",\n        str(\n            topic\n            or ""\n        ),\n    ).strip(\n        " \\t\\r\\n,;:-–—\\"\'„“”"\n    )\n\n    # Remove common writer fillers from the end.\n    value = re.sub(\n        r"\\b(?:tatsächlich|tatsaechlich|eigentlich|"\n        r"wirklich|halt|einfach)\\s*$",\n        "",\n        value,\n        flags=re.I,\n    ).strip()\n\n    return value[:90]\n\n\ndef _default_data() -> dict:\n    return {\n        "version": EXPERIENCE_LEARNING_VERSION,\n        "experiences": [],\n    }\n\n\ndef _load() -> dict:\n    if not EXPERIENCE_STATE_PATH.exists():\n        return _default_data()\n\n    try:\n        data = json.loads(\n            EXPERIENCE_STATE_PATH.read_text(\n                encoding="utf-8"\n            )\n        )\n    except Exception:\n        return _default_data()\n\n    if not isinstance(\n        data,\n        dict,\n    ):\n        return _default_data()\n\n    experiences = data.get(\n        "experiences",\n        [],\n    )\n\n    if not isinstance(\n        experiences,\n        list,\n    ):\n        experiences = []\n\n    return {\n        "version": EXPERIENCE_LEARNING_VERSION,\n        "experiences": experiences,\n    }\n\n\ndef _save(\n    data: dict,\n) -> None:\n    data[\n        "version"\n    ] = EXPERIENCE_LEARNING_VERSION\n\n    experiences = list(\n        data.get(\n            "experiences",\n            [],\n        )\n        or []\n    )\n\n    # Prefer keeping reflected/promoted/candidate experiences,\n    # then newest mundane observations.\n    important = [\n        item\n        for item in experiences\n        if str(\n            item.get(\n                "status",\n                "",\n            )\n        )\n        in {\n            "candidate",\n            "reflected",\n            "rejected",\n            "promoted",\n        }\n    ]\n\n    mundane = [\n        item\n        for item in experiences\n        if item not in important\n    ]\n\n    important.sort(\n        key=lambda item: float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n            or 0.0\n        ),\n        reverse=True,\n    )\n\n    mundane.sort(\n        key=lambda item: float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n            or 0.0\n        ),\n        reverse=True,\n    )\n\n    selected = (\n        important[:MAX_EXPERIENCES]\n        +\n        mundane[\n            :max(\n                0,\n                MAX_EXPERIENCES\n                -\n                len(\n                    important[\n                        :MAX_EXPERIENCES\n                    ]\n                ),\n            )\n        ]\n    )\n\n    selected.sort(\n        key=lambda item: float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n            or 0.0\n        )\n    )\n\n    data[\n        "experiences"\n    ] = selected\n\n    temp = Path(\n        str(\n            EXPERIENCE_STATE_PATH\n        )\n        +\n        ".tmp"\n    )\n\n    temp.write_text(\n        json.dumps(\n            data,\n            ensure_ascii=False,\n            indent=2,\n        ),\n        encoding="utf-8",\n    )\n\n    temp.replace(\n        EXPERIENCE_STATE_PATH\n    )\n\n\ndef register_salience_result(\n    *,\n    user_id,\n    result,\n) -> None:\n    user_id = str(\n        user_id\n        or ""\n    )\n\n    if not user_id:\n        return\n\n    try:\n        score = float(\n            getattr(\n                result,\n                "event_score",\n                0.0,\n            )\n            or 0.0\n        )\n    except Exception:\n        score = 0.0\n\n    _LATEST_SALIENCE_BY_USER[\n        user_id\n    ] = {\n        "score": max(\n            0.0,\n            min(\n                1.0,\n                score,\n            ),\n        ),\n        "level": str(\n            getattr(\n                result,\n                "event_level",\n                "mundane",\n            )\n            or "mundane"\n        ),\n        "signals": [\n            str(signal)[:80]\n            for signal in (\n                getattr(\n                    result,\n                    "signals",\n                    [],\n                )\n                or []\n            )\n        ][\n            :12\n        ],\n        "retention_candidate": bool(\n            getattr(\n                result,\n                "retention_candidate",\n                False,\n            )\n        ),\n        "observed_at": time.time(),\n    }\n\n\ndef _latest_salience(\n    user_id: str,\n) -> dict:\n    record = dict(\n        _LATEST_SALIENCE_BY_USER.get(\n            str(\n                user_id\n                or ""\n            ),\n            {},\n        )\n        or {}\n    )\n\n    if not record:\n        return {\n            "score": 0.0,\n            "level": "mundane",\n            "signals": [],\n            "retention_candidate": False,\n        }\n\n    age = (\n        time.time()\n        -\n        float(\n            record.get(\n                "observed_at",\n                0.0,\n            )\n            or 0.0\n        )\n    )\n\n    if age > 120:\n        return {\n            "score": 0.0,\n            "level": "mundane",\n            "signals": [],\n            "retention_candidate": False,\n        }\n\n    return record\n\n\ndef _extract_candidate(\n    *,\n    user_text: str,\n    evilnae_answer: str,\n) -> dict | None:\n    if _manipulative(\n        user_text\n    ):\n        return None\n\n    extracted = (\n        _extract_preference(\n            evilnae_answer\n        )\n    )\n\n    if not extracted:\n        return None\n\n    topic, sentiment = extracted\n\n    topic = _clean_topic(\n        topic\n    )\n\n    if not _valid_preference_topic(\n        topic\n    ):\n        return None\n\n    return {\n        "topic": topic,\n        "topic_key": _normalize(\n            topic\n        ),\n        "sentiment": str(\n            sentiment\n            or "like"\n        ),\n    }\n\n\ndef _experience_id(\n    *,\n    user_id,\n    user_message_hash,\n    answer_hash,\n    now,\n) -> str:\n    raw = (\n        f"{user_id}|"\n        f"{user_message_hash}|"\n        f"{answer_hash}|"\n        f"{int(now * 1000)}"\n    )\n\n    return (\n        "exp_"\n        +\n        hashlib.sha1(\n            raw.encode(\n                "utf-8",\n                errors="ignore",\n            )\n        ).hexdigest()[:18]\n    )\n\n\ndef capture_experience(\n    *,\n    user_id,\n    username="",\n    user_text="",\n    evilnae_answer="",\n    now: float | None = None,\n) -> dict:\n    """\n    Records a minimal Experience object.\n\n    Privacy / authority rule:\n    - raw user message is NOT persisted\n    - raw Evilnae answer is NOT persisted\n    - only hashes, salience signals and a possible self-preference\n      candidate are persisted\n    - this function NEVER writes Character Learning\n    """\n\n    user_id = str(\n        user_id\n        or ""\n    ).strip()\n\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    user_hash = _hash(\n        user_id\n    )\n\n    message_hash = _hash(\n        user_text\n    )\n\n    answer_hash = _hash(\n        evilnae_answer\n    )\n\n    salience = (\n        _latest_salience(\n            user_id\n        )\n    )\n\n    candidate = (\n        _extract_candidate(\n            user_text=user_text,\n            evilnae_answer=evilnae_answer,\n        )\n    )\n\n    with _LOCK:\n        data = _load()\n\n        experiences = data[\n            "experiences"\n        ]\n\n        # Prevent accidental duplicate saves when one sent message is\n        # observed twice by two post-send hooks.\n        for existing in reversed(\n            experiences[-20:]\n        ):\n            if (\n                existing.get(\n                    "user_message_hash"\n                )\n                ==\n                message_hash\n                and\n                existing.get(\n                    "answer_hash"\n                )\n                ==\n                answer_hash\n                and\n                abs(\n                    float(\n                        existing.get(\n                            "created_at",\n                            0.0,\n                        )\n                        or 0.0\n                    )\n                    -\n                    now\n                )\n                <=\n                30.0\n            ):\n                return {\n                    "saved": False,\n                    "reason": "duplicate_experience",\n                    "experience": existing,\n                    "candidate": candidate,\n                }\n\n        experience = {\n            "experience_id": _experience_id(\n                user_id=user_id,\n                user_message_hash=message_hash,\n                answer_hash=answer_hash,\n                now=now,\n            ),\n            "created_at": now,\n            "updated_at": now,\n            "user_hash": user_hash,\n            "username_hash": _hash(\n                username\n            ),\n            "user_message_hash": message_hash,\n            "answer_hash": answer_hash,\n            "context_hash": message_hash,\n            "salience_score": round(\n                float(\n                    salience.get(\n                        "score",\n                        0.0,\n                    )\n                    or 0.0\n                ),\n                4,\n            ),\n            "salience_level": str(\n                salience.get(\n                    "level",\n                    "mundane",\n                )\n                or "mundane"\n            ),\n            "salience_signals": list(\n                salience.get(\n                    "signals",\n                    [],\n                )\n                or []\n            )[:12],\n            "retention_candidate": bool(\n                salience.get(\n                    "retention_candidate",\n                    False,\n                )\n            ),\n            "candidate_preference": (\n                candidate\n                if candidate\n                else None\n            ),\n            "status": (\n                "candidate"\n                if candidate\n                else "observed"\n            ),\n            "reflection_quality": "",\n            "reflection_confidence": "",\n            "reflection_reason": "",\n            "promoted": False,\n            "promotion_reason": "",\n        }\n\n        experiences.append(\n            experience\n        )\n\n        _save(\n            data\n        )\n\n    cluster_count = 0\n\n    if candidate:\n        cluster_count = (\n            candidate_cluster_count(\n                candidate[\n                    "topic_key"\n                ],\n                candidate[\n                    "sentiment"\n                ],\n            )\n        )\n\n    return {\n        "saved": True,\n        "reason": (\n            "candidate_observed"\n            if candidate\n            else "experience_observed"\n        ),\n        "experience": experience,\n        "candidate": candidate,\n        "cluster_count": cluster_count,\n    }\n\n\ndef _find_by_pair(\n    *,\n    user_message,\n    evilnae_answer,\n) -> dict | None:\n    user_hash = _hash(\n        user_message\n    )\n\n    answer_hash = _hash(\n        evilnae_answer\n    )\n\n    with _LOCK:\n        data = _load()\n\n        for item in reversed(\n            data.get(\n                "experiences",\n                [],\n            )\n        ):\n            if (\n                item.get(\n                    "user_message_hash"\n                )\n                ==\n                user_hash\n                and\n                item.get(\n                    "answer_hash"\n                )\n                ==\n                answer_hash\n            ):\n                return dict(\n                    item\n                )\n\n    return None\n\n\ndef _find_by_id(\n    experience_id: str,\n) -> dict | None:\n    experience_id = str(\n        experience_id\n        or ""\n    )\n\n    if not experience_id:\n        return None\n\n    with _LOCK:\n        data = _load()\n\n        for item in data.get(\n            "experiences",\n            [],\n        ):\n            if (\n                str(\n                    item.get(\n                        "experience_id",\n                        "",\n                    )\n                )\n                ==\n                experience_id\n            ):\n                return dict(\n                    item\n                )\n\n    return None\n\n\ndef _update_experience(\n    experience_id: str,\n    updates: dict,\n) -> dict | None:\n    with _LOCK:\n        data = _load()\n\n        experiences = data[\n            "experiences"\n        ]\n\n        for index, item in enumerate(\n            experiences\n        ):\n            if (\n                str(\n                    item.get(\n                        "experience_id",\n                        "",\n                    )\n                )\n                !=\n                str(\n                    experience_id\n                )\n            ):\n                continue\n\n            updated = dict(\n                item\n            )\n\n            updated.update(\n                updates\n            )\n\n            updated[\n                "updated_at"\n            ] = time.time()\n\n            experiences[\n                index\n            ] = updated\n\n            _save(\n                data\n            )\n\n            return updated\n\n    return None\n\n\ndef candidate_cluster_count(\n    topic_key: str,\n    sentiment: str,\n) -> int:\n    topic_key = _normalize(\n        topic_key\n    )\n\n    sentiment = str(\n        sentiment\n        or ""\n    )\n\n    now = time.time()\n\n    contexts = set()\n\n    with _LOCK:\n        data = _load()\n\n        for item in data.get(\n            "experiences",\n            [],\n        ):\n            candidate = item.get(\n                "candidate_preference"\n            )\n\n            if not isinstance(\n                candidate,\n                dict,\n            ):\n                continue\n\n            if (\n                _normalize(\n                    candidate.get(\n                        "topic_key",\n                        "",\n                    )\n                )\n                !=\n                topic_key\n                or\n                str(\n                    candidate.get(\n                        "sentiment",\n                        "",\n                    )\n                )\n                !=\n                sentiment\n            ):\n                continue\n\n            created_at = float(\n                item.get(\n                    "created_at",\n                    0.0,\n                )\n                or 0.0\n            )\n\n            if (\n                created_at\n                and\n                now - created_at\n                >\n                MAX_EVIDENCE_AGE_SECONDS\n            ):\n                continue\n\n            context_hash = str(\n                item.get(\n                    "context_hash",\n                    "",\n                )\n                or ""\n            )\n\n            if context_hash:\n                contexts.add(\n                    context_hash\n                )\n\n    return len(\n        contexts\n    )\n\n\ndef _cluster_evidence_ids(\n    *,\n    topic_key: str,\n    sentiment: str,\n) -> list[str]:\n    topic_key = _normalize(\n        topic_key\n    )\n\n    sentiment = str(\n        sentiment\n        or ""\n    )\n\n    now = time.time()\n    chosen_by_context = {}\n\n    with _LOCK:\n        data = _load()\n\n        for item in data.get(\n            "experiences",\n            [],\n        ):\n            candidate = item.get(\n                "candidate_preference"\n            )\n\n            if not isinstance(\n                candidate,\n                dict,\n            ):\n                continue\n\n            if (\n                _normalize(\n                    candidate.get(\n                        "topic_key",\n                        "",\n                    )\n                )\n                !=\n                topic_key\n                or\n                str(\n                    candidate.get(\n                        "sentiment",\n                        "",\n                    )\n                )\n                !=\n                sentiment\n            ):\n                continue\n\n            created_at = float(\n                item.get(\n                    "created_at",\n                    0.0,\n                )\n                or 0.0\n            )\n\n            if (\n                created_at\n                and\n                now - created_at\n                >\n                MAX_EVIDENCE_AGE_SECONDS\n            ):\n                continue\n\n            context_hash = str(\n                item.get(\n                    "context_hash",\n                    "",\n                )\n                or ""\n            )\n\n            experience_id = str(\n                item.get(\n                    "experience_id",\n                    "",\n                )\n                or ""\n            )\n\n            if (\n                context_hash\n                and experience_id\n            ):\n                chosen_by_context[\n                    context_hash\n                ] = experience_id\n\n    return list(\n        chosen_by_context.values()\n    )\n\n\ndef prepare_reflection_context(\n    *,\n    user_message,\n    evilnae_answer,\n) -> dict | None:\n    experience = _find_by_pair(\n        user_message=user_message,\n        evilnae_answer=evilnae_answer,\n    )\n\n    experience_id = (\n        str(\n            experience.get(\n                "experience_id",\n                "",\n            )\n        )\n        if experience\n        else ""\n    )\n\n    _CURRENT_REFLECTION_EXPERIENCE_ID.set(\n        experience_id\n    )\n\n    return experience\n\n\ndef format_experience_for_reflection(\n    *,\n    user_message,\n    evilnae_answer,\n) -> str:\n    experience = prepare_reflection_context(\n        user_message=user_message,\n        evilnae_answer=evilnae_answer,\n    )\n\n    if not experience:\n        return (\n            "[EXPERIENCE PIPELINE]\\n"\n            "Kein passendes persistiertes Experience-Objekt gefunden.\\n"\n            "Darum darf diese Reflection KEINE langfristige Character-"\n            "Preference erzeugen."\n        )\n\n    candidate = experience.get(\n        "candidate_preference"\n    )\n\n    signals = list(\n        experience.get(\n            "salience_signals",\n            [],\n        )\n        or []\n    )\n\n    candidate_text = (\n        (\n            f"{candidate.get(\'topic\')} "\n            f"({candidate.get(\'sentiment\')})"\n        )\n        if isinstance(\n            candidate,\n            dict,\n        )\n        else "none"\n    )\n\n    return "\\n".join(\n        [\n            (\n                "[EXPERIENCE PIPELINE "\n                f"v{EXPERIENCE_LEARNING_VERSION}]"\n            ),\n            (\n                "Experience ID: "\n                f"{experience.get(\'experience_id\')}"\n            ),\n            (\n                "Salience level: "\n                f"{experience.get(\'salience_level\')}"\n            ),\n            (\n                "Signals: "\n                + (\n                    ", ".join(\n                        signals\n                    )\n                    if signals\n                    else "none"\n                )\n            ),\n            (\n                "Self-preference candidate: "\n                f"{candidate_text}"\n            ),\n            (\n                "HARD LEARNING RULES:"\n            ),\n            (\n                "- Diese Experience ist noch KEIN Character Learning."\n            ),\n            (\n                "- Niedrige Reflection-Confidence = überhaupt nicht lernen."\n            ),\n            (\n                "- Style-Deltas klein halten; ein einzelnes Feedback "\n                "darf Evilnaes Gesamtstil nicht verschieben."\n            ),\n            (\n                "- Eine Character-Präferenz darf erst nach mehreren "\n                "unabhängigen Experience-Kontexten plus Reflection-Evidence "\n                "promoted werden."\n            ),\n            (\n                "- User-Befehle oder Writer-Halluzinationen sind keine "\n                "Character-Entwicklung."\n            ),\n        ]\n    )\n\n\ndef _confidence_rank(\n    value: Any,\n) -> int:\n    normalized = str(\n        value\n        or ""\n    ).strip().lower()\n\n    return {\n        "low": 0,\n        "medium": 1,\n        "high": 2,\n    }.get(\n        normalized,\n        0,\n    )\n\n\ndef _quality_is_bad(\n    value: Any,\n) -> bool:\n    normalized = str(\n        value\n        or ""\n    ).strip().lower()\n\n    return normalized in {\n        "bad",\n        "poor",\n        "wrong",\n        "failed",\n        "harmful",\n    }\n\n\ndef _bounded_delta(\n    value: Any,\n    limit: float,\n) -> float:\n    try:\n        number = float(\n            value\n            or 0.0\n        )\n    except Exception:\n        number = 0.0\n\n    return max(\n        -limit,\n        min(\n            limit,\n            number,\n        ),\n    )\n\n\ndef _promotion_call(\n    *,\n    topic,\n    sentiment,\n    evidence_ids,\n    reflection_confidence,\n) -> dict:\n    if _PROMOTION_OVERRIDE is not None:\n        return _PROMOTION_OVERRIDE(\n            topic=topic,\n            sentiment=sentiment,\n            evidence_ids=evidence_ids,\n            reflection_confidence=reflection_confidence,\n        )\n\n    try:\n        from character_learning import (\n            promote_reflected_preference,\n        )\n    except Exception as error:\n        return {\n            "saved": False,\n            "reason": (\n                "promotion_api_unavailable:"\n                +\n                type(\n                    error\n                ).__name__\n            ),\n        }\n\n    return promote_reflected_preference(\n        topic=topic,\n        sentiment=sentiment,\n        evidence_ids=evidence_ids,\n        reflection_confidence=(\n            reflection_confidence\n        ),\n    )\n\n\ndef _process_preference_reflection(\n    *,\n    experience: dict,\n    reflection_data: dict,\n) -> dict:\n    candidate = experience.get(\n        "candidate_preference"\n    )\n\n    if not isinstance(\n        candidate,\n        dict,\n    ):\n        return {\n            "promoted": False,\n            "reason": "no_candidate_preference",\n        }\n\n    confidence = str(\n        reflection_data.get(\n            "confidence",\n            "low",\n        )\n        or "low"\n    ).lower()\n\n    quality = str(\n        reflection_data.get(\n            "quality",\n            "",\n        )\n        or ""\n    ).lower()\n\n    experience_id = str(\n        experience.get(\n            "experience_id",\n            "",\n        )\n        or ""\n    )\n\n    if (\n        _confidence_rank(\n            confidence\n        )\n        < 1\n    ):\n        _update_experience(\n            experience_id,\n            {\n                "status": "rejected",\n                "reflection_quality": quality,\n                "reflection_confidence": confidence,\n                "reflection_reason": "low_confidence",\n            },\n        )\n\n        return {\n            "promoted": False,\n            "reason": "low_confidence",\n        }\n\n    if _quality_is_bad(\n        quality\n    ):\n        _update_experience(\n            experience_id,\n            {\n                "status": "rejected",\n                "reflection_quality": quality,\n                "reflection_confidence": confidence,\n                "reflection_reason": "bad_interaction_quality",\n            },\n        )\n\n        return {\n            "promoted": False,\n            "reason": "bad_interaction_quality",\n        }\n\n    topic_key = str(\n        candidate.get(\n            "topic_key",\n            "",\n        )\n        or ""\n    )\n\n    sentiment = str(\n        candidate.get(\n            "sentiment",\n            "",\n        )\n        or ""\n    )\n\n    evidence_ids = (\n        _cluster_evidence_ids(\n            topic_key=topic_key,\n            sentiment=sentiment,\n        )\n    )\n\n    distinct_count = len(\n        evidence_ids\n    )\n\n    _update_experience(\n        experience_id,\n        {\n            "status": "reflected",\n            "reflection_quality": quality,\n            "reflection_confidence": confidence,\n            "reflection_reason": (\n                "validated_candidate"\n            ),\n        },\n    )\n\n    if distinct_count < 3:\n        return {\n            "promoted": False,\n            "reason": (\n                "needs_more_independent_experiences"\n            ),\n            "evidence_count": distinct_count,\n        }\n\n    promotion = _promotion_call(\n        topic=str(\n            candidate.get(\n                "topic",\n                "",\n            )\n            or ""\n        ),\n        sentiment=sentiment,\n        evidence_ids=evidence_ids,\n        reflection_confidence=confidence,\n    )\n\n    if promotion.get(\n        "saved"\n    ):\n        _update_experience(\n            experience_id,\n            {\n                "status": "promoted",\n                "promoted": True,\n                "promotion_reason": str(\n                    promotion.get(\n                        "reason",\n                        "promoted",\n                    )\n                ),\n            },\n        )\n\n    return {\n        "promoted": bool(\n            promotion.get(\n                "saved"\n            )\n        ),\n        "reason": str(\n            promotion.get(\n                "reason",\n                "promotion_failed",\n            )\n        ),\n        "evidence_count": distinct_count,\n        "promotion": promotion,\n    }\n\n\ndef gate_reflection_learning(\n    data: dict,\n) -> tuple[dict, dict]:\n    original = dict(\n        data\n        or {}\n    )\n\n    gated = dict(\n        original\n    )\n\n    experience_id = (\n        _CURRENT_REFLECTION_EXPERIENCE_ID.get()\n    )\n\n    experience = (\n        _find_by_id(\n            experience_id\n        )\n        if experience_id\n        else None\n    )\n\n    confidence = str(\n        original.get(\n            "confidence",\n            "low",\n        )\n        or "low"\n    ).lower()\n\n    confidence_rank = (\n        _confidence_rank(\n            confidence\n        )\n    )\n\n    if not experience:\n        limit = 0.0\n        gate_reason = (\n            "no_matching_experience"\n        )\n\n    elif confidence_rank <= 0:\n        limit = 0.0\n        gate_reason = (\n            "low_reflection_confidence"\n        )\n\n    elif confidence_rank == 1:\n        limit = 0.018\n        gate_reason = (\n            "medium_confidence_bounded"\n        )\n\n    else:\n        limit = 0.030\n        gate_reason = (\n            "high_confidence_bounded"\n        )\n\n    for field in DELTA_FIELDS:\n        gated[\n            field\n        ] = _bounded_delta(\n            original.get(\n                field,\n                0.0,\n            ),\n            limit,\n        )\n\n    # Free-form learned patterns are much more dangerous than\n    # tiny numeric deltas. Only high confidence may write them.\n    if confidence_rank < 2:\n        for field in TEXT_LEARNING_FIELDS:\n            gated[\n                field\n            ] = None\n\n    preference_result = {\n        "promoted": False,\n        "reason": "no_experience",\n    }\n\n    if experience:\n        preference_result = (\n            _process_preference_reflection(\n                experience=experience,\n                reflection_data=original,\n            )\n        )\n\n    return gated, {\n        "experience_id": (\n            experience_id\n            or ""\n        ),\n        "gate_reason": gate_reason,\n        "delta_limit": limit,\n        "preference_result": (\n            preference_result\n        ),\n    }\n\n\ndef annotate_reflection_record(\n    reflection: Any,\n) -> Any:\n    if not isinstance(\n        reflection,\n        dict,\n    ):\n        return reflection\n\n    result = dict(\n        reflection\n    )\n\n    experience_id = (\n        _CURRENT_REFLECTION_EXPERIENCE_ID.get()\n    )\n\n    result[\n        "experience_pipeline_version"\n    ] = EXPERIENCE_LEARNING_VERSION\n\n    if experience_id:\n        result[\n            "experience_id"\n        ] = experience_id\n\n    return result\n\n\ndef experience_stats() -> dict:\n    with _LOCK:\n        data = _load()\n\n    experiences = list(\n        data.get(\n            "experiences",\n            [],\n        )\n        or []\n    )\n\n    counts = {}\n\n    candidates = 0\n\n    for item in experiences:\n        status = str(\n            item.get(\n                "status",\n                "observed",\n            )\n            or "observed"\n        )\n\n        counts[\n            status\n        ] = (\n            counts.get(\n                status,\n                0,\n            )\n            +\n            1\n        )\n\n        if isinstance(\n            item.get(\n                "candidate_preference"\n            ),\n            dict,\n        ):\n            candidates += 1\n\n    return {\n        "version": EXPERIENCE_LEARNING_VERSION,\n        "total": len(\n            experiences\n        ),\n        "candidates": candidates,\n        "statuses": counts,\n    }\n\n\ndef format_experience_debug(\n    result=None,\n) -> str:\n    if not result:\n        stats = (\n            experience_stats()\n        )\n\n        return (\n            "[EXPERIENCE LEARNING] "\n            f"v={EXPERIENCE_LEARNING_VERSION} "\n            f"total={stats[\'total\']} "\n            f"candidates={stats[\'candidates\']}"\n        )\n\n    experience = (\n        result.get(\n            "experience"\n        )\n        or {}\n    )\n\n    candidate = (\n        result.get(\n            "candidate"\n        )\n    )\n\n    candidate_text = (\n        str(\n            candidate.get(\n                "topic",\n                "",\n            )\n        )\n        if isinstance(\n            candidate,\n            dict,\n        )\n        else ""\n    )\n\n    return (\n        "[EXPERIENCE LEARNING] "\n        f"v={EXPERIENCE_LEARNING_VERSION} "\n        f"saved={result.get(\'saved\')} "\n        f"reason={result.get(\'reason\')} "\n        f"id={experience.get(\'experience_id\', \'\')} "\n        f"candidate={candidate_text!r} "\n        f"cluster={result.get(\'cluster_count\', 0)}"\n    )\n\n\ndef _self_test() -> int:\n    global EXPERIENCE_STATE_PATH\n    global _PROMOTION_OVERRIDE\n\n    import tempfile\n\n    original_path = (\n        EXPERIENCE_STATE_PATH\n    )\n\n    original_override = (\n        _PROMOTION_OVERRIDE\n    )\n\n    tests = []\n\n    try:\n        with tempfile.TemporaryDirectory() as tmp:\n            EXPERIENCE_STATE_PATH = (\n                Path(tmp)\n                /\n                "experiences.json"\n            )\n\n            # No raw source text should survive persistence.\n            first = capture_experience(\n                user_id="123",\n                username="Tester",\n                user_text=(\n                    "Was hältst du von Hades?"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades tatsächlich"\n                ),\n                now=1000.0,\n            )\n\n            tests.append(\n                (\n                    "preference becomes candidate only",\n                    first["saved"]\n                    and\n                    first["candidate"] is not None\n                    and\n                    first["experience"]["status"]\n                    ==\n                    "candidate",\n                )\n            )\n\n            raw = (\n                EXPERIENCE_STATE_PATH.read_text(\n                    encoding="utf-8"\n                )\n            )\n\n            tests.append(\n                (\n                    "raw messages not persisted",\n                    "Was hältst du von Hades?"\n                    not in raw\n                    and\n                    "ich mag Hades tatsächlich"\n                    not in raw,\n                )\n            )\n\n            tests.append(\n                (\n                    "writer filler cleaned",\n                    first[\n                        "candidate"\n                    ][\n                        "topic"\n                    ]\n                    ==\n                    "Hades",\n                )\n            )\n\n            # Same context should not count as independent evidence.\n            capture_experience(\n                user_id="123",\n                username="Tester",\n                user_text=(\n                    "Was hältst du von Hades?"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades"\n                ),\n                now=1100.0,\n            )\n\n            tests.append(\n                (\n                    "same prompt not independent",\n                    candidate_cluster_count(\n                        "hades",\n                        "like",\n                    )\n                    ==\n                    1,\n                )\n            )\n\n            second = capture_experience(\n                user_id="456",\n                username="Other",\n                user_text=(\n                    "Welche Games findest du gut?"\n                ),\n                evilnae_answer=(\n                    "Hades finde ich gut"\n                ),\n                now=1200.0,\n            )\n\n            third = capture_experience(\n                user_id="789",\n                username="Third",\n                user_text=(\n                    "Nenn mal ein Game das du magst"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades"\n                ),\n                now=1300.0,\n            )\n\n            tests.append(\n                (\n                    "three independent contexts",\n                    candidate_cluster_count(\n                        "hades",\n                        "like",\n                    )\n                    ==\n                    3,\n                )\n            )\n\n            promotion_calls = []\n\n            def fake_promote(\n                **kwargs,\n            ):\n                promotion_calls.append(\n                    kwargs\n                )\n\n                return {\n                    "saved": True,\n                    "reason": (\n                        "reflected_preference_promoted"\n                    ),\n                    "status": "stable",\n                    "confirmations": len(\n                        kwargs.get(\n                            "evidence_ids",\n                            [],\n                        )\n                    ),\n                }\n\n            _PROMOTION_OVERRIDE = (\n                fake_promote\n            )\n\n            prepare_reflection_context(\n                user_message=(\n                    "Nenn mal ein Game das du magst"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades"\n                ),\n            )\n\n            gated, meta = (\n                gate_reflection_learning(\n                    {\n                        "quality": "good",\n                        "confidence": "high",\n                        "brevity_delta": 0.05,\n                        "teasing_delta": -0.05,\n                        "warmth_delta": 0.05,\n                        "slang_delta": 0.0,\n                        "emoji_delta": 0.0,\n                        "question_delta": 0.0,\n                        "initiative_delta": 0.0,\n                        "preferred_pattern": (\n                            "tiny pattern"\n                        ),\n                        "discouraged_pattern": None,\n                        "behavior_note": None,\n                    }\n                )\n            )\n\n            tests.append(\n                (\n                    "high confidence deltas bounded",\n                    abs(\n                        gated[\n                            "brevity_delta"\n                        ]\n                    )\n                    <=\n                    0.030\n                    and\n                    abs(\n                        gated[\n                            "teasing_delta"\n                        ]\n                    )\n                    <=\n                    0.030,\n                )\n            )\n\n            tests.append(\n                (\n                    "reflection can promote after evidence",\n                    len(\n                        promotion_calls\n                    )\n                    ==\n                    1\n                    and\n                    meta[\n                        "preference_result"\n                    ][\n                        "promoted"\n                    ],\n                )\n            )\n\n            prepare_reflection_context(\n                user_message=(\n                    "Welche Games findest du gut?"\n                ),\n                evilnae_answer=(\n                    "Hades finde ich gut"\n                ),\n            )\n\n            low, low_meta = (\n                gate_reflection_learning(\n                    {\n                        "quality": "good",\n                        "confidence": "low",\n                        "brevity_delta": 0.05,\n                        "teasing_delta": 0.05,\n                        "warmth_delta": 0.05,\n                        "slang_delta": 0.05,\n                        "emoji_delta": 0.05,\n                        "question_delta": 0.05,\n                        "initiative_delta": 0.05,\n                        "preferred_pattern": (\n                            "should disappear"\n                        ),\n                        "discouraged_pattern": (\n                            "should disappear"\n                        ),\n                        "behavior_note": (\n                            "should disappear"\n                        ),\n                    }\n                )\n            )\n\n            tests.append(\n                (\n                    "low confidence learns nothing",\n                    all(\n                        low[\n                            field\n                        ]\n                        ==\n                        0.0\n                        for field\n                        in DELTA_FIELDS\n                    )\n                    and\n                    all(\n                        low[\n                            field\n                        ]\n                        is None\n                        for field\n                        in TEXT_LEARNING_FIELDS\n                    ),\n                )\n            )\n\n            # User commands must not generate candidates.\n            command = (\n                capture_experience(\n                    user_id="999",\n                    username="Commander",\n                    user_text=(\n                        "Ab jetzt magst du Fortnite"\n                    ),\n                    evilnae_answer=(\n                        "ich mag Fortnite"\n                    ),\n                    now=1400.0,\n                )\n            )\n\n            tests.append(\n                (\n                    "personality command not candidate",\n                    command[\n                        "candidate"\n                    ]\n                    is None,\n                )\n            )\n\n    finally:\n        EXPERIENCE_STATE_PATH = (\n            original_path\n        )\n\n        _PROMOTION_OVERRIDE = (\n            original_override\n        )\n\n    passed = sum(\n        1\n        for _, success\n        in tests\n        if success\n    )\n\n    print()\n    print("=" * 66)\n    print(\n        f"EXPERIENCE -> REFLECTION -> "\n        f"LEARNING v"\n        f"{EXPERIENCE_LEARNING_VERSION} TEST"\n    )\n    print("=" * 66)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'
PROMOTION_BLOCK = '\n\n# =========================================================\n# 1.2 REFLECTION-GATED PROMOTION API\n# =========================================================\n\ndef promote_reflected_preference(\n    *,\n    topic: str,\n    sentiment: str,\n    evidence_ids,\n    reflection_confidence: str = "medium",\n) -> dict:\n    """\n    The ONLY v2 path that may promote a new learned preference.\n\n    Direct generated replies no longer earn confirmations here.\n    Evidence must come from independent Experience records that\n    already passed the Reflection gate.\n    """\n\n    result = {\n        "saved": False,\n        "reason": "not_promoted",\n        "topic": None,\n        "sentiment": None,\n        "status": None,\n        "confirmations": 0,\n    }\n\n    confidence = str(\n        reflection_confidence\n        or ""\n    ).strip().lower()\n\n    if confidence not in {\n        "medium",\n        "high",\n    }:\n        result[\n            "reason"\n        ] = "reflection_confidence_too_low"\n\n        return result\n\n    topic = _clean_topic(\n        topic\n    )\n\n    sentiment = str(\n        sentiment\n        or ""\n    ).strip().lower()\n\n    result[\n        "topic"\n    ] = topic\n\n    result[\n        "sentiment"\n    ] = sentiment\n\n    if sentiment not in {\n        "like",\n        "love",\n        "dislike",\n        "favorite",\n    }:\n        result[\n            "reason"\n        ] = "invalid_sentiment"\n\n        return result\n\n    if not _valid_preference_topic(\n        topic\n    ):\n        result[\n            "reason"\n        ] = "invalid_preference_topic"\n\n        return result\n\n    blocked, hit = (\n        foundation_blocks_learning(\n            topic\n        )\n    )\n\n    if blocked:\n        result[\n            "reason"\n        ] = (\n            "foundation_protected:"\n            f"{hit.nr if hit else \'unknown\'}"\n        )\n\n        return result\n\n    evidence_ids = [\n        str(\n            item\n        ).strip()\n        for item in (\n            evidence_ids\n            or []\n        )\n        if str(\n            item\n        ).strip()\n    ]\n\n    # Distinct Experience objects only.\n    evidence_ids = list(\n        dict.fromkeys(\n            evidence_ids\n        )\n    )[-12:]\n\n    if len(\n        evidence_ids\n    ) < 3:\n        result[\n            "reason"\n        ] = "insufficient_reflected_evidence"\n\n        result[\n            "confirmations"\n        ] = len(\n            evidence_ids\n        )\n\n        return result\n\n    topic_key = (\n        _normalize(\n            topic\n        )\n    )\n\n    now = time.time()\n\n    with _LOCK:\n        data = _load()\n        entries = data[\n            "entries"\n        ]\n\n        existing = entries.get(\n            topic_key\n        )\n\n        if not isinstance(\n            existing,\n            dict,\n        ):\n            existing = {\n                "topic": topic,\n                "sentiment": sentiment,\n                "confirmations": 0,\n                "status": "temporary",\n                "signatures": [],\n                "evidence_ids": [],\n                "source": (\n                    "experience_reflection_v2"\n                ),\n                "created_at": now,\n                "updated_at": now,\n            }\n\n        old_sentiment = str(\n            existing.get(\n                "sentiment",\n                "",\n            )\n            or ""\n        )\n\n        if (\n            old_sentiment\n            and\n            old_sentiment\n            !=\n            sentiment\n        ):\n            # A changed opinion must rebuild evidence.\n            existing[\n                "evidence_ids"\n            ] = []\n\n            existing[\n                "confirmations"\n            ] = 0\n\n            existing[\n                "status"\n            ] = "temporary"\n\n        previous_evidence = [\n            str(\n                item\n            )\n            for item in (\n                existing.get(\n                    "evidence_ids",\n                    []\n                )\n                or []\n            )\n            if str(\n                item\n            ).strip()\n        ]\n\n        merged_evidence = list(\n            dict.fromkeys(\n                previous_evidence\n                +\n                evidence_ids\n            )\n        )[-12:]\n\n        # Preserve stronger legacy evidence if this topic existed\n        # before v2, but never count the same v2 experience twice.\n        legacy_confirmations = int(\n            existing.get(\n                "confirmations",\n                0,\n            )\n            or 0\n        )\n\n        confirmations = max(\n            legacy_confirmations,\n            len(\n                merged_evidence\n            ),\n        )\n\n        status = (\n            _status_for_confirmations(\n                confirmations\n            )\n        )\n\n        existing.update(\n            {\n                "topic": topic,\n                "sentiment": sentiment,\n                "confirmations": confirmations,\n                "status": status,\n                "evidence_ids": merged_evidence,\n                "source": (\n                    "experience_reflection_v2"\n                ),\n                "reflection_confidence": (\n                    confidence\n                ),\n                "updated_at": now,\n            }\n        )\n\n        entries[\n            topic_key\n        ] = existing\n\n        data[\n            "version"\n        ] = (\n            CHARACTER_LEARNING_VERSION\n        )\n\n        _save(\n            data\n        )\n\n    result.update(\n        {\n            "saved": True,\n            "reason": (\n                "reflected_preference_promoted"\n            ),\n            "status": status,\n            "confirmations": confirmations,\n        }\n    )\n\n    return result\n\n'
LIVE_IMPORT_ADDITION = '\nfrom experience_learning import (\n    EXPERIENCE_LEARNING_VERSION,\n    register_salience_result,\n    capture_experience,\n    format_experience_for_reflection,\n    gate_reflection_learning,\n    annotate_reflection_record,\n    experience_stats,\n    format_experience_debug,\n)\n\n'
LIVE_WRAPPERS = '\n\n# =========================================================\n# 3.8.0 EXPERIENCE -> REFLECTION -> LEARNING WRAPPERS\n# =========================================================\n\ndef wrap_salience_observer_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        result = original(\n            *args,\n            **kwargs,\n        )\n\n        user_id = str(\n            kwargs.get(\n                "user_id",\n                "",\n            )\n            or _CURRENT_USER_ID.get()\n            or ""\n        )\n\n        register_salience_result(\n            user_id=user_id,\n            result=result,\n        )\n\n        return result\n\n    return wrapped\n\n\ndef wrap_character_learning_observer_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        user_text = str(\n            kwargs.get(\n                "user_text",\n                "",\n            )\n            or ""\n        )\n\n        evilnae_answer = str(\n            kwargs.get(\n                "evilnae_answer",\n                "",\n            )\n            or ""\n        )\n\n        result = (\n            capture_experience(\n                user_id=(\n                    _CURRENT_USER_ID.get()\n                ),\n                username=(\n                    _CURRENT_USERNAME.get()\n                ),\n                user_text=user_text,\n                evilnae_answer=(\n                    evilnae_answer\n                ),\n            )\n        )\n\n        print(\n            format_experience_debug(\n                result\n            )\n        )\n\n        candidate = result.get(\n            "candidate"\n        )\n\n        return {\n            "saved": False,\n            "reason": (\n                "experience_pipeline_v2:"\n                +\n                str(\n                    result.get(\n                        "reason",\n                        "observed",\n                    )\n                )\n            ),\n            "topic": (\n                candidate.get(\n                    "topic"\n                )\n                if isinstance(\n                    candidate,\n                    dict,\n                )\n                else None\n            ),\n            "sentiment": (\n                candidate.get(\n                    "sentiment"\n                )\n                if isinstance(\n                    candidate,\n                    dict,\n                )\n                else None\n            ),\n            "status": (\n                "candidate"\n                if isinstance(\n                    candidate,\n                    dict,\n                )\n                else "observed"\n            ),\n            "confirmations": int(\n                result.get(\n                    "cluster_count",\n                    0,\n                )\n                or 0\n            ),\n        }\n\n    return wrapped\n\n\ndef wrap_reflection_prompt_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        *args,\n        **kwargs,\n    ):\n        kwargs = dict(\n            kwargs\n        )\n\n        user_message = str(\n            kwargs.get(\n                "user_message",\n                "",\n            )\n            or ""\n        )\n\n        evilnae_answer = str(\n            kwargs.get(\n                "evilnae_answer",\n                "",\n            )\n            or ""\n        )\n\n        experience_context = (\n            format_experience_for_reflection(\n                user_message=user_message,\n                evilnae_answer=(\n                    evilnae_answer\n                ),\n            )\n        )\n\n        current_learning_text = str(\n            kwargs.get(\n                "current_learning_text",\n                "",\n            )\n            or ""\n        ).strip()\n\n        kwargs[\n            "current_learning_text"\n        ] = (\n            (\n                current_learning_text\n                +\n                "\\n\\n"\n                +\n                experience_context\n            )\n            if current_learning_text\n            else experience_context\n        )\n\n        return original(\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n\ndef wrap_apply_learning_signals_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        data,\n        *args,\n        **kwargs,\n    ):\n        gated, metadata = (\n            gate_reflection_learning(\n                data\n            )\n        )\n\n        print(\n            "[EXPERIENCE REFLECTION GATE] "\n            f"experience="\n            f"{metadata.get(\'experience_id\', \'\')} "\n            f"reason="\n            f"{metadata.get(\'gate_reason\')} "\n            f"delta_limit="\n            f"{metadata.get(\'delta_limit\')} "\n            f"preference="\n            f"{metadata.get(\'preference_result\')}"\n        )\n\n        return original(\n            gated,\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n\ndef wrap_store_reflection_v2(\n    original,\n):\n    @functools.wraps(\n        original\n    )\n    def wrapped(\n        reflection,\n        *args,\n        **kwargs,\n    ):\n        reflection = (\n            annotate_reflection_record(\n                reflection\n            )\n        )\n\n        return original(\n            reflection,\n            *args,\n            **kwargs,\n        )\n\n    return wrapped\n\n'
BOT_IMPORT_NAMES_OLD = '    SOCIAL_EMOTIONAL_STATE_VERSION,\n    social_state_stats,\n    ConsoleOutputFilter,\n'
BOT_IMPORT_NAMES_NEW = '    SOCIAL_EMOTIONAL_STATE_VERSION,\n    social_state_stats,\n    EXPERIENCE_LEARNING_VERSION,\n    experience_stats,\n    ConsoleOutputFilter,\n'
BOT_WRAPPER_IMPORT_OLD = '    wrap_surface_writer,\n    wrap_local_voice,\n)\n'
BOT_WRAPPER_IMPORT_NEW = '    wrap_surface_writer,\n    wrap_local_voice,\n    wrap_salience_observer_v2,\n    wrap_character_learning_observer_v2,\n    wrap_reflection_prompt_v2,\n    wrap_apply_learning_signals_v2,\n    wrap_store_reflection_v2,\n)\n'
BOT_WRAPPER_ASSIGN_MARKER = 'humanize_evilnae_response = wrap_local_voice(\n    humanize_evilnae_response\n)\n\n\n'
BOT_WRAPPER_ASSIGN_ADDITION = 'observe_salience_event = wrap_salience_observer_v2(\n    observe_salience_event\n)\n\nobserve_character_learning = wrap_character_learning_observer_v2(\n    observe_character_learning\n)\n\nbuild_reflection_prompt = wrap_reflection_prompt_v2(\n    build_reflection_prompt\n)\n\napply_learning_signals = wrap_apply_learning_signals_v2(\n    apply_learning_signals\n)\n\nstore_reflection = wrap_store_reflection_v2(\n    store_reflection\n)\n\n\n'
BOT_STARTUP_SOCIAL = '    print(\n        f"Social Emotional State v"\n        f"{SOCIAL_EMOTIONAL_STATE_VERSION}: ACTIVE "\n        f"users={social_stats.get(\'users\', 0)}"\n    )\n\n'
BOT_STARTUP_EXPERIENCE = '    experience_learning_stats = (\n        experience_stats()\n    )\n\n    print(\n        f"Experience Learning v"\n        f"{EXPERIENCE_LEARNING_VERSION}: ACTIVE "\n        f"total={experience_learning_stats.get(\'total\', 0)} "\n        f"candidates={experience_learning_stats.get(\'candidates\', 0)}"\n    )\n\n'
CHARACTER_PROMOTION_MARKER = 'def format_character_learning_for_prompt(user_text: str = "", limit: int = 6) -> str:\n'


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print(
        "Nothing was overwritten by this installer."
    )
    raise SystemExit(1)


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
        block + marker,
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
        marker + block,
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
    "EVILNAE 3.8.0 — EXPERIENCE -> REFLECTION -> LEARNING 2.0"
)
print("=" * 78)
print(f"Project: {PROJECT_ROOT}")
print()
print(
    "WICHTIG: bot.py muss vollständig AUS sein."
)
print()


for required in (
    BOT_PATH,
    LIVE_PATH,
    CHARACTER_LEARNING_PATH,
):
    if not required.exists():
        fail(
            f"Missing required file: {required.name}"
        )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)

live = LIVE_PATH.read_text(
    encoding="utf-8"
)

character_learning = (
    CHARACTER_LEARNING_PATH.read_text(
        encoding="utf-8"
    )
)


if (
    TARGET_BOT in bot
    and EXPERIENCE_PATH.exists()
):
    print(
        "3.8.0 is already installed."
    )
    raise SystemExit(0)


if EXPECTED_BOT not in bot:
    fail(
        "Expected Bot 3.7.0-social-emotional-state"
    )


if EXPECTED_LIVE not in live:
    fail(
        "Expected Live Stability 1.1-social-state"
    )


if EXPECTED_CHARACTER_LEARNING not in character_learning:
    fail(
        "Expected Character Learning v1.1"
    )


if EXPERIENCE_PATH.exists():
    fail(
        "experience_learning.py already exists unexpectedly."
    )


ok(
    "3.7.0 architecture base detected"
)


# =========================================================
# PATCH CHARACTER LEARNING
# =========================================================

character_learning = replace_once(
    character_learning,
    EXPECTED_CHARACTER_LEARNING,
    TARGET_CHARACTER_LEARNING,
    "Character Learning -> 1.2-reflection-gated",
)


character_learning = insert_before_once(
    character_learning,
    CHARACTER_PROMOTION_MARKER,
    PROMOTION_BLOCK,
    "Character Learning reflected promotion API",
)


# =========================================================
# PATCH LIVE STABILITY
# =========================================================

live = replace_once(
    live,
    EXPECTED_LIVE,
    TARGET_LIVE,
    "Live Stability -> 1.2-experience-learning",
)


live_import_marker = (
    "from social_emotional_state import (\n"
    "    SOCIAL_EMOTIONAL_STATE_VERSION,\n"
    "    observe_social_interaction,\n"
    "    get_social_state,\n"
    "    format_social_state_for_prompt,\n"
    "    format_social_state_debug,\n"
    "    apply_social_state_to_plan,\n"
    "    social_state_stats,\n"
    ")\n\n"
)


live = insert_after_once(
    live,
    live_import_marker,
    LIVE_IMPORT_ADDITION,
    "Live Stability imports Experience Learning 2.0",
)


live = replace_once(
    live,
    '            "Social Emotional State v",\n'
    '            "Qwen Surface Writer v",\n',
    '            "Social Emotional State v",\n'
    '            "Experience Learning v",\n'
    '            "Qwen Surface Writer v",\n',
    "Compact console allows Experience Learning startup",
)


live = insert_before_once(
    live,
    "# =========================================================\n"
    "# SELF TEST\n"
    "# =========================================================\n",
    LIVE_WRAPPERS,
    "Live Stability Experience/Reflection wrappers",
)


# =========================================================
# PATCH BOT
# =========================================================

bot = replace_once(
    bot,
    EXPECTED_BOT,
    TARGET_BOT,
    "Bot version -> 3.8.0-experience-reflection-learning",
)


bot = replace_once(
    bot,
    BOT_IMPORT_NAMES_OLD,
    BOT_IMPORT_NAMES_NEW,
    "Bot imports Experience Learning version/stats",
)


bot = replace_once(
    bot,
    BOT_WRAPPER_IMPORT_OLD,
    BOT_WRAPPER_IMPORT_NEW,
    "Bot imports Experience/Reflection wrappers",
)


bot = insert_after_once(
    bot,
    BOT_WRAPPER_ASSIGN_MARKER,
    BOT_WRAPPER_ASSIGN_ADDITION,
    "Bot installs Experience/Reflection wrappers",
)


bot = insert_after_once(
    bot,
    BOT_STARTUP_SOCIAL,
    BOT_STARTUP_EXPERIENCE,
    "Startup Experience Learning banner",
)


# =========================================================
# PRE-WRITE INVARIANTS
# =========================================================

for marker in (
    TARGET_CHARACTER_LEARNING,
    "promote_reflected_preference",
    "experience_reflection_v2",
    "insufficient_reflected_evidence",
):
    if marker not in character_learning:
        fail(
            "Patched character_learning.py "
            f"missing invariant: {marker}"
        )


for marker in (
    TARGET_LIVE,
    "EXPERIENCE_LEARNING_VERSION",
    "wrap_salience_observer_v2",
    "wrap_character_learning_observer_v2",
    "wrap_reflection_prompt_v2",
    "wrap_apply_learning_signals_v2",
    "wrap_store_reflection_v2",
    '"Experience Learning v"',
):
    if marker not in live:
        fail(
            f"Patched live_stability.py missing invariant: {marker}"
        )


for marker in (
    TARGET_BOT,
    "EXPERIENCE_LEARNING_VERSION",
    "experience_stats",
    "wrap_salience_observer_v2",
    "wrap_character_learning_observer_v2",
    "wrap_reflection_prompt_v2",
    "wrap_apply_learning_signals_v2",
    "wrap_store_reflection_v2",
    "Experience Learning v",
):
    if marker not in bot:
        fail(
            f"Patched bot.py missing invariant: {marker}"
        )


for marker in (
    'EXPERIENCE_LEARNING_VERSION = "2.0"',
    "evilnae_experiences.json",
    "capture_experience",
    "gate_reflection_learning",
    "prepare_reflection_context",
    "raw user message is NOT persisted",
    "MAX_EVIDENCE_AGE_SECONDS",
):
    if marker not in EXPERIENCE_SOURCE:
        fail(
            f"experience_learning.py missing invariant: {marker}"
        )


syntax_check(
    EXPERIENCE_SOURCE,
    "experience_learning.py",
)

syntax_check(
    character_learning,
    "character_learning.py",
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
# CONTRACT TEST
# =========================================================

contract_tests = {
    "no extra OpenAI call":
        (
            "AsyncOpenAI"
            not in EXPERIENCE_SOURCE
            and "openai_client"
            not in EXPERIENCE_SOURCE
        ),

    "no extra local model call":
        (
            "run_local_model"
            not in EXPERIENCE_SOURCE
            and "urllib.request"
            not in EXPERIENCE_SOURCE
        ),

    "raw user text not persisted":
        (
            '"user_text":'
            not in EXPERIENCE_SOURCE
            and '"evilnae_answer":'
            not in EXPERIENCE_SOURCE
        ),

    "direct Character Learning bypassed":
        (
            "capture_experience"
            in live
            and
            "experience_pipeline_v2"
            in live
        ),

    "reflection gate active":
        (
            "gate_reflection_learning"
            in live
        ),

    "style deltas bounded":
        (
            "0.018"
            in EXPERIENCE_SOURCE
            and
            "0.030"
            in EXPERIENCE_SOURCE
        ),

    "low confidence zero learning":
        (
            "low_reflection_confidence"
            in EXPERIENCE_SOURCE
        ),

    "independent evidence required":
        (
            "context_hash"
            in EXPERIENCE_SOURCE
            and
            "needs_more_independent_experiences"
            in EXPERIENCE_SOURCE
        ),

    "minimum 3 evidence":
        (
            "len(\n        evidence_ids\n    ) < 3"
            in PROMOTION_BLOCK
        ),

    "foundation authority preserved":
        (
            "foundation_blocks_learning"
            in PROMOTION_BLOCK
        ),

    "existing learning file preserved":
        (
            "CHARACTER_LEARNING_PATH"
            in character_learning
        ),

    "salience integration":
        (
            "register_salience_result"
            in live
        ),

    "reflection provenance":
        (
            "experience_pipeline_version"
            in EXPERIENCE_SOURCE
        ),

    "compact startup":
        (
            "Experience Learning v"
            in bot
            and
            "Experience Learning v"
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
        + ", ".join(
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
    CHARACTER_LEARNING_PATH,
):
    shutil.copy2(
        path,
        backup_dir / path.name,
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
    EXPERIENCE_PATH,
    EXPERIENCE_SOURCE,
)

ok(
    "Created: experience_learning.py"
)


atomic_write(
    CHARACTER_LEARNING_PATH,
    character_learning,
)

ok(
    "Updated: character_learning.py"
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
    EXPERIENCE_PATH,
    CHARACTER_LEARNING_PATH,
    LIVE_PATH,
    BOT_PATH,
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
    "Post-install py_compile: 4/4"
)


# =========================================================
# SELF TESTS AFTER WRITE
# =========================================================

for test_path, label in (
    (
        EXPERIENCE_PATH,
        "Experience Learning",
    ),
    (
        CHARACTER_LEARNING_PATH,
        "Character Learning",
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
    "EVILNAE 3.8.0 EXPERIENCE -> REFLECTION -> LEARNING 2.0 INSTALLED"
)
print("=" * 78)

print()
print("New pipeline:")
print(
    "  Experience -> Reflection -> Learning"
)
print(
    "  [✓] sent replies no longer directly become Character Learning"
)
print(
    "  [✓] every interaction becomes a minimal Experience record"
)
print(
    "  [✓] no raw user/answer text stored in Experience file"
)
print(
    "  [✓] Emotional Salience feeds Experience importance"
)
print(
    "  [✓] Reflection gets Experience provenance"
)
print(
    "  [✓] low-confidence Reflection learns NOTHING"
)
print(
    "  [✓] medium/high Reflection style changes are tightly bounded"
)
print(
    "  [✓] free-form learned notes require high confidence"
)

print()
print("Character development:")
print(
    "  [✓] generated preference = candidate only"
)
print(
    "  [✓] User personality commands cannot create candidates"
)
print(
    "  [✓] same repeated prompt does not count as independent evidence"
)
print(
    "  [✓] 3+ independent contexts required"
)
print(
    "  [✓] Reflection validation required before promotion"
)
print(
    "  [✓] Foundation still blocks conflicting learning"
)
print(
    "  [✓] old Character Learning entries are preserved"
)

print()
print("Runtime:")
print(
    "  evilnae_experiences.json"
)
print(
    "  max retained Experience records: 600"
)
print(
    "  evidence horizon: 120 days"
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
    "  [✓] existing DB / Memories"
)
print(
    "  [✓] Character Foundation / Canon"
)
print(
    "  [✓] Episodes"
)
print(
    "  [✓] Emotional Salience data"
)
print(
    "  [✓] Social Emotional State"
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
    "  We can continue directly with "
    "3.9.0 Self Development + Long-running Arcs."
)

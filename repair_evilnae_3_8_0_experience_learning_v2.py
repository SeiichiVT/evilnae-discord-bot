from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
CHARACTER_PATH = PROJECT_ROOT / "character_learning.py"
EXPERIENCE_PATH = PROJECT_ROOT / "experience_learning.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.8.0-experience-reflection-learning"'
EXPECTED_LIVE = 'LIVE_STABILITY_VERSION = "1.2-experience-learning"'
EXPECTED_CHARACTER = 'CHARACTER_LEARNING_VERSION = "1.2-reflection-gated"'
EXPECTED_OLD_EXPERIENCE = 'EXPERIENCE_LEARNING_VERSION = "2.0"'
TARGET_EXPERIENCE = 'EXPERIENCE_LEARNING_VERSION = "2.0.1-evidence-fix"'

PATCHED_EXPERIENCE_SOURCE = 'from __future__ import annotations\n\nimport contextvars\nimport hashlib\nimport json\nimport re\nimport threading\nimport time\nfrom pathlib import Path\nfrom typing import Any\n\nfrom character_learning import (\n    _extract_preference,\n    _valid_preference_topic,\n    _manipulative,\n)\n\n\nEXPERIENCE_LEARNING_VERSION = "2.0.1-evidence-fix"\nEXPERIENCE_STATE_PATH = Path(\n    "evilnae_experiences.json"\n)\n\nMAX_EXPERIENCES = 600\nMAX_EVIDENCE_AGE_SECONDS = (\n    120 * 24 * 60 * 60\n)\n\n_LOCK = threading.RLock()\n\n_LATEST_SALIENCE_BY_USER = {}\n\n_CURRENT_REFLECTION_EXPERIENCE_ID = (\n    contextvars.ContextVar(\n        "evilnae_reflection_experience_id",\n        default="",\n    )\n)\n\n_PROMOTION_OVERRIDE = None\n\n\nIMPORTANT_SIGNALS = {\n    "positive_relationship_signal",\n    "negative_relationship_signal",\n    "relationship_repair",\n    "vulnerability",\n    "explicit_feedback",\n    "explicit_correction",\n    "shared_callback",\n    "personal_milestone",\n    "personal_preference",\n}\n\nDELTA_FIELDS = (\n    "brevity_delta",\n    "teasing_delta",\n    "warmth_delta",\n    "slang_delta",\n    "emoji_delta",\n    "question_delta",\n    "initiative_delta",\n)\n\nTEXT_LEARNING_FIELDS = (\n    "preferred_pattern",\n    "discouraged_pattern",\n    "behavior_note",\n)\n\n\ndef _normalize(\n    text: Any,\n) -> str:\n    value = str(\n        text\n        or ""\n    ).lower()\n\n    value = re.sub(\n        r"\\s+",\n        " ",\n        value,\n    ).strip()\n\n    return value\n\n\ndef _hash(\n    text: Any,\n) -> str:\n    value = _normalize(\n        text\n    )\n\n    return hashlib.sha1(\n        value.encode(\n            "utf-8",\n            errors="ignore",\n        )\n    ).hexdigest()\n\n\ndef _clean_topic(\n    topic: str,\n) -> str:\n    value = re.sub(\n        r"\\s+",\n        " ",\n        str(\n            topic\n            or ""\n        ),\n    ).strip(\n        " \\t\\r\\n,;:-–—\\"\'„“”"\n    )\n\n    # Remove common writer fillers from the end.\n    value = re.sub(\n        r"\\b(?:tatsächlich|tatsaechlich|eigentlich|"\n        r"wirklich|halt|einfach)\\s*$",\n        "",\n        value,\n        flags=re.I,\n    ).strip()\n\n    return value[:90]\n\n\ndef _default_data() -> dict:\n    return {\n        "version": EXPERIENCE_LEARNING_VERSION,\n        "experiences": [],\n    }\n\n\ndef _load() -> dict:\n    if not EXPERIENCE_STATE_PATH.exists():\n        return _default_data()\n\n    try:\n        data = json.loads(\n            EXPERIENCE_STATE_PATH.read_text(\n                encoding="utf-8"\n            )\n        )\n    except Exception:\n        return _default_data()\n\n    if not isinstance(\n        data,\n        dict,\n    ):\n        return _default_data()\n\n    experiences = data.get(\n        "experiences",\n        [],\n    )\n\n    if not isinstance(\n        experiences,\n        list,\n    ):\n        experiences = []\n\n    return {\n        "version": EXPERIENCE_LEARNING_VERSION,\n        "experiences": experiences,\n    }\n\n\ndef _save(\n    data: dict,\n) -> None:\n    data[\n        "version"\n    ] = EXPERIENCE_LEARNING_VERSION\n\n    experiences = list(\n        data.get(\n            "experiences",\n            [],\n        )\n        or []\n    )\n\n    # Prefer keeping reflected/promoted/candidate experiences,\n    # then newest mundane observations.\n    important = [\n        item\n        for item in experiences\n        if str(\n            item.get(\n                "status",\n                "",\n            )\n        )\n        in {\n            "candidate",\n            "reflected",\n            "rejected",\n            "promoted",\n        }\n    ]\n\n    mundane = [\n        item\n        for item in experiences\n        if item not in important\n    ]\n\n    important.sort(\n        key=lambda item: float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n            or 0.0\n        ),\n        reverse=True,\n    )\n\n    mundane.sort(\n        key=lambda item: float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n            or 0.0\n        ),\n        reverse=True,\n    )\n\n    selected = (\n        important[:MAX_EXPERIENCES]\n        +\n        mundane[\n            :max(\n                0,\n                MAX_EXPERIENCES\n                -\n                len(\n                    important[\n                        :MAX_EXPERIENCES\n                    ]\n                ),\n            )\n        ]\n    )\n\n    selected.sort(\n        key=lambda item: float(\n            item.get(\n                "created_at",\n                0.0,\n            )\n            or 0.0\n        )\n    )\n\n    data[\n        "experiences"\n    ] = selected\n\n    temp = Path(\n        str(\n            EXPERIENCE_STATE_PATH\n        )\n        +\n        ".tmp"\n    )\n\n    temp.write_text(\n        json.dumps(\n            data,\n            ensure_ascii=False,\n            indent=2,\n        ),\n        encoding="utf-8",\n    )\n\n    temp.replace(\n        EXPERIENCE_STATE_PATH\n    )\n\n\ndef register_salience_result(\n    *,\n    user_id,\n    result,\n) -> None:\n    user_id = str(\n        user_id\n        or ""\n    )\n\n    if not user_id:\n        return\n\n    try:\n        score = float(\n            getattr(\n                result,\n                "event_score",\n                0.0,\n            )\n            or 0.0\n        )\n    except Exception:\n        score = 0.0\n\n    _LATEST_SALIENCE_BY_USER[\n        user_id\n    ] = {\n        "score": max(\n            0.0,\n            min(\n                1.0,\n                score,\n            ),\n        ),\n        "level": str(\n            getattr(\n                result,\n                "event_level",\n                "mundane",\n            )\n            or "mundane"\n        ),\n        "signals": [\n            str(signal)[:80]\n            for signal in (\n                getattr(\n                    result,\n                    "signals",\n                    [],\n                )\n                or []\n            )\n        ][\n            :12\n        ],\n        "retention_candidate": bool(\n            getattr(\n                result,\n                "retention_candidate",\n                False,\n            )\n        ),\n        "observed_at": time.time(),\n    }\n\n\ndef _latest_salience(\n    user_id: str,\n) -> dict:\n    record = dict(\n        _LATEST_SALIENCE_BY_USER.get(\n            str(\n                user_id\n                or ""\n            ),\n            {},\n        )\n        or {}\n    )\n\n    if not record:\n        return {\n            "score": 0.0,\n            "level": "mundane",\n            "signals": [],\n            "retention_candidate": False,\n        }\n\n    age = (\n        time.time()\n        -\n        float(\n            record.get(\n                "observed_at",\n                0.0,\n            )\n            or 0.0\n        )\n    )\n\n    if age > 120:\n        return {\n            "score": 0.0,\n            "level": "mundane",\n            "signals": [],\n            "retention_candidate": False,\n        }\n\n    return record\n\n\nPREFERENCE_QUERY_PATTERN = re.compile(\n    r"\\b(?:"\n    r"was|welche|welchen|welches|wer|wen|"\n    r"nenn(?:e)?|sag(?:e)?\\s+mal"\n    r")\\b"\n    r".{0,90}\\b(?:"\n    r"magst\\s+du|liebst\\s+du|hasst\\s+du|"\n    r"du\\s+magst|du\\s+liebst|du\\s+hasst|"\n    r"dir\\s+gefällt|dir\\s+gefaellt"\n    r")\\b",\n    re.I,\n)\n\n\ndef _clear_preference_query(\n    user_text: str,\n) -> bool:\n    value = str(\n        user_text\n        or ""\n    )\n\n    return bool(\n        PREFERENCE_QUERY_PATTERN.search(\n            value\n        )\n    )\n\n\ndef _extract_candidate(\n    *,\n    user_text: str,\n    evilnae_answer: str,\n) -> dict | None:\n    if (\n        _manipulative(\n            user_text\n        )\n        and\n        not _clear_preference_query(\n            user_text\n        )\n    ):\n        return None\n\n    extracted = (\n        _extract_preference(\n            evilnae_answer\n        )\n    )\n\n    if not extracted:\n        return None\n\n    topic, sentiment = extracted\n\n    topic = _clean_topic(\n        topic\n    )\n\n    if not _valid_preference_topic(\n        topic\n    ):\n        return None\n\n    return {\n        "topic": topic,\n        "topic_key": _normalize(\n            topic\n        ),\n        "sentiment": str(\n            sentiment\n            or "like"\n        ),\n    }\n\n\ndef _experience_id(\n    *,\n    user_id,\n    user_message_hash,\n    answer_hash,\n    now,\n) -> str:\n    raw = (\n        f"{user_id}|"\n        f"{user_message_hash}|"\n        f"{answer_hash}|"\n        f"{int(now * 1000)}"\n    )\n\n    return (\n        "exp_"\n        +\n        hashlib.sha1(\n            raw.encode(\n                "utf-8",\n                errors="ignore",\n            )\n        ).hexdigest()[:18]\n    )\n\n\ndef capture_experience(\n    *,\n    user_id,\n    username="",\n    user_text="",\n    evilnae_answer="",\n    now: float | None = None,\n) -> dict:\n    """\n    Records a minimal Experience object.\n\n    Privacy / authority rule:\n    - raw user message is NOT persisted\n    - raw Evilnae answer is NOT persisted\n    - only hashes, salience signals and a possible self-preference\n      candidate are persisted\n    - this function NEVER writes Character Learning\n    """\n\n    user_id = str(\n        user_id\n        or ""\n    ).strip()\n\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    user_hash = _hash(\n        user_id\n    )\n\n    message_hash = _hash(\n        user_text\n    )\n\n    answer_hash = _hash(\n        evilnae_answer\n    )\n\n    salience = (\n        _latest_salience(\n            user_id\n        )\n    )\n\n    candidate = (\n        _extract_candidate(\n            user_text=user_text,\n            evilnae_answer=evilnae_answer,\n        )\n    )\n\n    with _LOCK:\n        data = _load()\n\n        experiences = data[\n            "experiences"\n        ]\n\n        # Prevent accidental duplicate saves when one sent message is\n        # observed twice by two post-send hooks.\n        for existing in reversed(\n            experiences[-20:]\n        ):\n            if (\n                existing.get(\n                    "user_message_hash"\n                )\n                ==\n                message_hash\n                and\n                existing.get(\n                    "answer_hash"\n                )\n                ==\n                answer_hash\n                and\n                abs(\n                    float(\n                        existing.get(\n                            "created_at",\n                            0.0,\n                        )\n                        or 0.0\n                    )\n                    -\n                    now\n                )\n                <=\n                30.0\n            ):\n                return {\n                    "saved": False,\n                    "reason": "duplicate_experience",\n                    "experience": existing,\n                    "candidate": candidate,\n                }\n\n        experience = {\n            "experience_id": _experience_id(\n                user_id=user_id,\n                user_message_hash=message_hash,\n                answer_hash=answer_hash,\n                now=now,\n            ),\n            "created_at": now,\n            "updated_at": now,\n            "user_hash": user_hash,\n            "username_hash": _hash(\n                username\n            ),\n            "user_message_hash": message_hash,\n            "answer_hash": answer_hash,\n            "context_hash": message_hash,\n            "salience_score": round(\n                float(\n                    salience.get(\n                        "score",\n                        0.0,\n                    )\n                    or 0.0\n                ),\n                4,\n            ),\n            "salience_level": str(\n                salience.get(\n                    "level",\n                    "mundane",\n                )\n                or "mundane"\n            ),\n            "salience_signals": list(\n                salience.get(\n                    "signals",\n                    [],\n                )\n                or []\n            )[:12],\n            "retention_candidate": bool(\n                salience.get(\n                    "retention_candidate",\n                    False,\n                )\n            ),\n            "candidate_preference": (\n                candidate\n                if candidate\n                else None\n            ),\n            "status": (\n                "candidate"\n                if candidate\n                else "observed"\n            ),\n            "reflection_quality": "",\n            "reflection_confidence": "",\n            "reflection_reason": "",\n            "promoted": False,\n            "promotion_reason": "",\n        }\n\n        experiences.append(\n            experience\n        )\n\n        _save(\n            data\n        )\n\n    cluster_count = 0\n\n    if candidate:\n        cluster_count = (\n            candidate_cluster_count(\n                candidate[\n                    "topic_key"\n                ],\n                candidate[\n                    "sentiment"\n                ],\n            )\n        )\n\n    return {\n        "saved": True,\n        "reason": (\n            "candidate_observed"\n            if candidate\n            else "experience_observed"\n        ),\n        "experience": experience,\n        "candidate": candidate,\n        "cluster_count": cluster_count,\n    }\n\n\ndef _find_by_pair(\n    *,\n    user_message,\n    evilnae_answer,\n) -> dict | None:\n    user_hash = _hash(\n        user_message\n    )\n\n    answer_hash = _hash(\n        evilnae_answer\n    )\n\n    with _LOCK:\n        data = _load()\n\n        for item in reversed(\n            data.get(\n                "experiences",\n                [],\n            )\n        ):\n            if (\n                item.get(\n                    "user_message_hash"\n                )\n                ==\n                user_hash\n                and\n                item.get(\n                    "answer_hash"\n                )\n                ==\n                answer_hash\n            ):\n                return dict(\n                    item\n                )\n\n    return None\n\n\ndef _find_by_id(\n    experience_id: str,\n) -> dict | None:\n    experience_id = str(\n        experience_id\n        or ""\n    )\n\n    if not experience_id:\n        return None\n\n    with _LOCK:\n        data = _load()\n\n        for item in data.get(\n            "experiences",\n            [],\n        ):\n            if (\n                str(\n                    item.get(\n                        "experience_id",\n                        "",\n                    )\n                )\n                ==\n                experience_id\n            ):\n                return dict(\n                    item\n                )\n\n    return None\n\n\ndef _update_experience(\n    experience_id: str,\n    updates: dict,\n) -> dict | None:\n    with _LOCK:\n        data = _load()\n\n        experiences = data[\n            "experiences"\n        ]\n\n        for index, item in enumerate(\n            experiences\n        ):\n            if (\n                str(\n                    item.get(\n                        "experience_id",\n                        "",\n                    )\n                )\n                !=\n                str(\n                    experience_id\n                )\n            ):\n                continue\n\n            updated = dict(\n                item\n            )\n\n            updated.update(\n                updates\n            )\n\n            updated[\n                "updated_at"\n            ] = time.time()\n\n            experiences[\n                index\n            ] = updated\n\n            _save(\n                data\n            )\n\n            return updated\n\n    return None\n\n\ndef candidate_cluster_count(\n    topic_key: str,\n    sentiment: str,\n) -> int:\n    topic_key = _normalize(\n        topic_key\n    )\n\n    sentiment = str(\n        sentiment\n        or ""\n    )\n\n    now = time.time()\n\n    contexts = set()\n\n    with _LOCK:\n        data = _load()\n\n        for item in data.get(\n            "experiences",\n            [],\n        ):\n            candidate = item.get(\n                "candidate_preference"\n            )\n\n            if not isinstance(\n                candidate,\n                dict,\n            ):\n                continue\n\n            if (\n                _normalize(\n                    candidate.get(\n                        "topic_key",\n                        "",\n                    )\n                )\n                !=\n                topic_key\n                or\n                str(\n                    candidate.get(\n                        "sentiment",\n                        "",\n                    )\n                )\n                !=\n                sentiment\n            ):\n                continue\n\n            created_at = float(\n                item.get(\n                    "created_at",\n                    0.0,\n                )\n                or 0.0\n            )\n\n            if (\n                created_at\n                and\n                now - created_at\n                >\n                MAX_EVIDENCE_AGE_SECONDS\n            ):\n                continue\n\n            context_hash = str(\n                item.get(\n                    "context_hash",\n                    "",\n                )\n                or ""\n            )\n\n            if context_hash:\n                contexts.add(\n                    context_hash\n                )\n\n    return len(\n        contexts\n    )\n\n\ndef _cluster_evidence_ids(\n    *,\n    topic_key: str,\n    sentiment: str,\n) -> list[str]:\n    topic_key = _normalize(\n        topic_key\n    )\n\n    sentiment = str(\n        sentiment\n        or ""\n    )\n\n    now = time.time()\n    chosen_by_context = {}\n\n    with _LOCK:\n        data = _load()\n\n        for item in data.get(\n            "experiences",\n            [],\n        ):\n            candidate = item.get(\n                "candidate_preference"\n            )\n\n            if not isinstance(\n                candidate,\n                dict,\n            ):\n                continue\n\n            if (\n                _normalize(\n                    candidate.get(\n                        "topic_key",\n                        "",\n                    )\n                )\n                !=\n                topic_key\n                or\n                str(\n                    candidate.get(\n                        "sentiment",\n                        "",\n                    )\n                )\n                !=\n                sentiment\n            ):\n                continue\n\n            created_at = float(\n                item.get(\n                    "created_at",\n                    0.0,\n                )\n                or 0.0\n            )\n\n            if (\n                created_at\n                and\n                now - created_at\n                >\n                MAX_EVIDENCE_AGE_SECONDS\n            ):\n                continue\n\n            context_hash = str(\n                item.get(\n                    "context_hash",\n                    "",\n                )\n                or ""\n            )\n\n            experience_id = str(\n                item.get(\n                    "experience_id",\n                    "",\n                )\n                or ""\n            )\n\n            if (\n                context_hash\n                and experience_id\n            ):\n                chosen_by_context[\n                    context_hash\n                ] = experience_id\n\n    return list(\n        chosen_by_context.values()\n    )\n\n\ndef prepare_reflection_context(\n    *,\n    user_message,\n    evilnae_answer,\n) -> dict | None:\n    experience = _find_by_pair(\n        user_message=user_message,\n        evilnae_answer=evilnae_answer,\n    )\n\n    experience_id = (\n        str(\n            experience.get(\n                "experience_id",\n                "",\n            )\n        )\n        if experience\n        else ""\n    )\n\n    _CURRENT_REFLECTION_EXPERIENCE_ID.set(\n        experience_id\n    )\n\n    return experience\n\n\ndef format_experience_for_reflection(\n    *,\n    user_message,\n    evilnae_answer,\n) -> str:\n    experience = prepare_reflection_context(\n        user_message=user_message,\n        evilnae_answer=evilnae_answer,\n    )\n\n    if not experience:\n        return (\n            "[EXPERIENCE PIPELINE]\\n"\n            "Kein passendes persistiertes Experience-Objekt gefunden.\\n"\n            "Darum darf diese Reflection KEINE langfristige Character-"\n            "Preference erzeugen."\n        )\n\n    candidate = experience.get(\n        "candidate_preference"\n    )\n\n    signals = list(\n        experience.get(\n            "salience_signals",\n            [],\n        )\n        or []\n    )\n\n    candidate_text = (\n        (\n            f"{candidate.get(\'topic\')} "\n            f"({candidate.get(\'sentiment\')})"\n        )\n        if isinstance(\n            candidate,\n            dict,\n        )\n        else "none"\n    )\n\n    return "\\n".join(\n        [\n            (\n                "[EXPERIENCE PIPELINE "\n                f"v{EXPERIENCE_LEARNING_VERSION}]"\n            ),\n            (\n                "Experience ID: "\n                f"{experience.get(\'experience_id\')}"\n            ),\n            (\n                "Salience level: "\n                f"{experience.get(\'salience_level\')}"\n            ),\n            (\n                "Signals: "\n                + (\n                    ", ".join(\n                        signals\n                    )\n                    if signals\n                    else "none"\n                )\n            ),\n            (\n                "Self-preference candidate: "\n                f"{candidate_text}"\n            ),\n            (\n                "HARD LEARNING RULES:"\n            ),\n            (\n                "- Diese Experience ist noch KEIN Character Learning."\n            ),\n            (\n                "- Niedrige Reflection-Confidence = überhaupt nicht lernen."\n            ),\n            (\n                "- Style-Deltas klein halten; ein einzelnes Feedback "\n                "darf Evilnaes Gesamtstil nicht verschieben."\n            ),\n            (\n                "- Eine Character-Präferenz darf erst nach mehreren "\n                "unabhängigen Experience-Kontexten plus Reflection-Evidence "\n                "promoted werden."\n            ),\n            (\n                "- User-Befehle oder Writer-Halluzinationen sind keine "\n                "Character-Entwicklung."\n            ),\n        ]\n    )\n\n\ndef _confidence_rank(\n    value: Any,\n) -> int:\n    normalized = str(\n        value\n        or ""\n    ).strip().lower()\n\n    return {\n        "low": 0,\n        "medium": 1,\n        "high": 2,\n    }.get(\n        normalized,\n        0,\n    )\n\n\ndef _quality_is_bad(\n    value: Any,\n) -> bool:\n    normalized = str(\n        value\n        or ""\n    ).strip().lower()\n\n    return normalized in {\n        "bad",\n        "poor",\n        "wrong",\n        "failed",\n        "harmful",\n    }\n\n\ndef _bounded_delta(\n    value: Any,\n    limit: float,\n) -> float:\n    try:\n        number = float(\n            value\n            or 0.0\n        )\n    except Exception:\n        number = 0.0\n\n    return max(\n        -limit,\n        min(\n            limit,\n            number,\n        ),\n    )\n\n\ndef _promotion_call(\n    *,\n    topic,\n    sentiment,\n    evidence_ids,\n    reflection_confidence,\n) -> dict:\n    if _PROMOTION_OVERRIDE is not None:\n        return _PROMOTION_OVERRIDE(\n            topic=topic,\n            sentiment=sentiment,\n            evidence_ids=evidence_ids,\n            reflection_confidence=reflection_confidence,\n        )\n\n    try:\n        from character_learning import (\n            promote_reflected_preference,\n        )\n    except Exception as error:\n        return {\n            "saved": False,\n            "reason": (\n                "promotion_api_unavailable:"\n                +\n                type(\n                    error\n                ).__name__\n            ),\n        }\n\n    return promote_reflected_preference(\n        topic=topic,\n        sentiment=sentiment,\n        evidence_ids=evidence_ids,\n        reflection_confidence=(\n            reflection_confidence\n        ),\n    )\n\n\ndef _process_preference_reflection(\n    *,\n    experience: dict,\n    reflection_data: dict,\n) -> dict:\n    candidate = experience.get(\n        "candidate_preference"\n    )\n\n    if not isinstance(\n        candidate,\n        dict,\n    ):\n        return {\n            "promoted": False,\n            "reason": "no_candidate_preference",\n        }\n\n    confidence = str(\n        reflection_data.get(\n            "confidence",\n            "low",\n        )\n        or "low"\n    ).lower()\n\n    quality = str(\n        reflection_data.get(\n            "quality",\n            "",\n        )\n        or ""\n    ).lower()\n\n    experience_id = str(\n        experience.get(\n            "experience_id",\n            "",\n        )\n        or ""\n    )\n\n    if (\n        _confidence_rank(\n            confidence\n        )\n        < 1\n    ):\n        _update_experience(\n            experience_id,\n            {\n                "status": "rejected",\n                "reflection_quality": quality,\n                "reflection_confidence": confidence,\n                "reflection_reason": "low_confidence",\n            },\n        )\n\n        return {\n            "promoted": False,\n            "reason": "low_confidence",\n        }\n\n    if _quality_is_bad(\n        quality\n    ):\n        _update_experience(\n            experience_id,\n            {\n                "status": "rejected",\n                "reflection_quality": quality,\n                "reflection_confidence": confidence,\n                "reflection_reason": "bad_interaction_quality",\n            },\n        )\n\n        return {\n            "promoted": False,\n            "reason": "bad_interaction_quality",\n        }\n\n    topic_key = str(\n        candidate.get(\n            "topic_key",\n            "",\n        )\n        or ""\n    )\n\n    sentiment = str(\n        candidate.get(\n            "sentiment",\n            "",\n        )\n        or ""\n    )\n\n    evidence_ids = (\n        _cluster_evidence_ids(\n            topic_key=topic_key,\n            sentiment=sentiment,\n        )\n    )\n\n    distinct_count = len(\n        evidence_ids\n    )\n\n    _update_experience(\n        experience_id,\n        {\n            "status": "reflected",\n            "reflection_quality": quality,\n            "reflection_confidence": confidence,\n            "reflection_reason": (\n                "validated_candidate"\n            ),\n        },\n    )\n\n    if distinct_count < 3:\n        return {\n            "promoted": False,\n            "reason": (\n                "needs_more_independent_experiences"\n            ),\n            "evidence_count": distinct_count,\n        }\n\n    promotion = _promotion_call(\n        topic=str(\n            candidate.get(\n                "topic",\n                "",\n            )\n            or ""\n        ),\n        sentiment=sentiment,\n        evidence_ids=evidence_ids,\n        reflection_confidence=confidence,\n    )\n\n    if promotion.get(\n        "saved"\n    ):\n        _update_experience(\n            experience_id,\n            {\n                "status": "promoted",\n                "promoted": True,\n                "promotion_reason": str(\n                    promotion.get(\n                        "reason",\n                        "promoted",\n                    )\n                ),\n            },\n        )\n\n    return {\n        "promoted": bool(\n            promotion.get(\n                "saved"\n            )\n        ),\n        "reason": str(\n            promotion.get(\n                "reason",\n                "promotion_failed",\n            )\n        ),\n        "evidence_count": distinct_count,\n        "promotion": promotion,\n    }\n\n\ndef gate_reflection_learning(\n    data: dict,\n) -> tuple[dict, dict]:\n    original = dict(\n        data\n        or {}\n    )\n\n    gated = dict(\n        original\n    )\n\n    experience_id = (\n        _CURRENT_REFLECTION_EXPERIENCE_ID.get()\n    )\n\n    experience = (\n        _find_by_id(\n            experience_id\n        )\n        if experience_id\n        else None\n    )\n\n    confidence = str(\n        original.get(\n            "confidence",\n            "low",\n        )\n        or "low"\n    ).lower()\n\n    confidence_rank = (\n        _confidence_rank(\n            confidence\n        )\n    )\n\n    if not experience:\n        limit = 0.0\n        gate_reason = (\n            "no_matching_experience"\n        )\n\n    elif confidence_rank <= 0:\n        limit = 0.0\n        gate_reason = (\n            "low_reflection_confidence"\n        )\n\n    elif confidence_rank == 1:\n        limit = 0.018\n        gate_reason = (\n            "medium_confidence_bounded"\n        )\n\n    else:\n        limit = 0.030\n        gate_reason = (\n            "high_confidence_bounded"\n        )\n\n    for field in DELTA_FIELDS:\n        gated[\n            field\n        ] = _bounded_delta(\n            original.get(\n                field,\n                0.0,\n            ),\n            limit,\n        )\n\n    # Free-form learned patterns are much more dangerous than\n    # tiny numeric deltas. Only high confidence may write them.\n    if confidence_rank < 2:\n        for field in TEXT_LEARNING_FIELDS:\n            gated[\n                field\n            ] = None\n\n    preference_result = {\n        "promoted": False,\n        "reason": "no_experience",\n    }\n\n    if experience:\n        preference_result = (\n            _process_preference_reflection(\n                experience=experience,\n                reflection_data=original,\n            )\n        )\n\n    return gated, {\n        "experience_id": (\n            experience_id\n            or ""\n        ),\n        "gate_reason": gate_reason,\n        "delta_limit": limit,\n        "preference_result": (\n            preference_result\n        ),\n    }\n\n\ndef annotate_reflection_record(\n    reflection: Any,\n) -> Any:\n    if not isinstance(\n        reflection,\n        dict,\n    ):\n        return reflection\n\n    result = dict(\n        reflection\n    )\n\n    experience_id = (\n        _CURRENT_REFLECTION_EXPERIENCE_ID.get()\n    )\n\n    result[\n        "experience_pipeline_version"\n    ] = EXPERIENCE_LEARNING_VERSION\n\n    if experience_id:\n        result[\n            "experience_id"\n        ] = experience_id\n\n    return result\n\n\ndef experience_stats() -> dict:\n    with _LOCK:\n        data = _load()\n\n    experiences = list(\n        data.get(\n            "experiences",\n            [],\n        )\n        or []\n    )\n\n    counts = {}\n\n    candidates = 0\n\n    for item in experiences:\n        status = str(\n            item.get(\n                "status",\n                "observed",\n            )\n            or "observed"\n        )\n\n        counts[\n            status\n        ] = (\n            counts.get(\n                status,\n                0,\n            )\n            +\n            1\n        )\n\n        if isinstance(\n            item.get(\n                "candidate_preference"\n            ),\n            dict,\n        ):\n            candidates += 1\n\n    return {\n        "version": EXPERIENCE_LEARNING_VERSION,\n        "total": len(\n            experiences\n        ),\n        "candidates": candidates,\n        "statuses": counts,\n    }\n\n\ndef format_experience_debug(\n    result=None,\n) -> str:\n    if not result:\n        stats = (\n            experience_stats()\n        )\n\n        return (\n            "[EXPERIENCE LEARNING] "\n            f"v={EXPERIENCE_LEARNING_VERSION} "\n            f"total={stats[\'total\']} "\n            f"candidates={stats[\'candidates\']}"\n        )\n\n    experience = (\n        result.get(\n            "experience"\n        )\n        or {}\n    )\n\n    candidate = (\n        result.get(\n            "candidate"\n        )\n    )\n\n    candidate_text = (\n        str(\n            candidate.get(\n                "topic",\n                "",\n            )\n        )\n        if isinstance(\n            candidate,\n            dict,\n        )\n        else ""\n    )\n\n    return (\n        "[EXPERIENCE LEARNING] "\n        f"v={EXPERIENCE_LEARNING_VERSION} "\n        f"saved={result.get(\'saved\')} "\n        f"reason={result.get(\'reason\')} "\n        f"id={experience.get(\'experience_id\', \'\')} "\n        f"candidate={candidate_text!r} "\n        f"cluster={result.get(\'cluster_count\', 0)}"\n    )\n\n\ndef _self_test() -> int:\n    global EXPERIENCE_STATE_PATH\n    global _PROMOTION_OVERRIDE\n\n    import tempfile\n\n    original_path = (\n        EXPERIENCE_STATE_PATH\n    )\n\n    original_override = (\n        _PROMOTION_OVERRIDE\n    )\n\n    tests = []\n\n    try:\n        with tempfile.TemporaryDirectory() as tmp:\n            base_now = time.time()\n\n            EXPERIENCE_STATE_PATH = (\n                Path(tmp)\n                /\n                "experiences.json"\n            )\n\n            # No raw source text should survive persistence.\n            first = capture_experience(\n                user_id="123",\n                username="Tester",\n                user_text=(\n                    "Was hältst du von Hades?"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades tatsächlich"\n                ),\n                now=base_now,\n            )\n\n            tests.append(\n                (\n                    "preference becomes candidate only",\n                    first["saved"]\n                    and\n                    first["candidate"] is not None\n                    and\n                    first["experience"]["status"]\n                    ==\n                    "candidate",\n                )\n            )\n\n            raw = (\n                EXPERIENCE_STATE_PATH.read_text(\n                    encoding="utf-8"\n                )\n            )\n\n            tests.append(\n                (\n                    "raw messages not persisted",\n                    "Was hältst du von Hades?"\n                    not in raw\n                    and\n                    "ich mag Hades tatsächlich"\n                    not in raw,\n                )\n            )\n\n            tests.append(\n                (\n                    "writer filler cleaned",\n                    first[\n                        "candidate"\n                    ][\n                        "topic"\n                    ]\n                    ==\n                    "Hades",\n                )\n            )\n\n            # Same context should not count as independent evidence.\n            capture_experience(\n                user_id="123",\n                username="Tester",\n                user_text=(\n                    "Was hältst du von Hades?"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades"\n                ),\n                now=base_now + 100.0,\n            )\n\n            tests.append(\n                (\n                    "same prompt not independent",\n                    candidate_cluster_count(\n                        "hades",\n                        "like",\n                    )\n                    ==\n                    1,\n                )\n            )\n\n            second = capture_experience(\n                user_id="456",\n                username="Other",\n                user_text=(\n                    "Welche Games findest du gut?"\n                ),\n                evilnae_answer=(\n                    "Hades finde ich gut"\n                ),\n                now=base_now + 200.0,\n            )\n\n            third = capture_experience(\n                user_id="789",\n                username="Third",\n                user_text=(\n                    "Nenn mal ein Game das du magst"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades"\n                ),\n                now=base_now + 300.0,\n            )\n\n            tests.append(\n                (\n                    "three independent contexts",\n                    candidate_cluster_count(\n                        "hades",\n                        "like",\n                    )\n                    ==\n                    3,\n                )\n            )\n\n            promotion_calls = []\n\n            def fake_promote(\n                **kwargs,\n            ):\n                promotion_calls.append(\n                    kwargs\n                )\n\n                return {\n                    "saved": True,\n                    "reason": (\n                        "reflected_preference_promoted"\n                    ),\n                    "status": "stable",\n                    "confirmations": len(\n                        kwargs.get(\n                            "evidence_ids",\n                            [],\n                        )\n                    ),\n                }\n\n            _PROMOTION_OVERRIDE = (\n                fake_promote\n            )\n\n            prepare_reflection_context(\n                user_message=(\n                    "Nenn mal ein Game das du magst"\n                ),\n                evilnae_answer=(\n                    "ich mag Hades"\n                ),\n            )\n\n            gated, meta = (\n                gate_reflection_learning(\n                    {\n                        "quality": "good",\n                        "confidence": "high",\n                        "brevity_delta": 0.05,\n                        "teasing_delta": -0.05,\n                        "warmth_delta": 0.05,\n                        "slang_delta": 0.0,\n                        "emoji_delta": 0.0,\n                        "question_delta": 0.0,\n                        "initiative_delta": 0.0,\n                        "preferred_pattern": (\n                            "tiny pattern"\n                        ),\n                        "discouraged_pattern": None,\n                        "behavior_note": None,\n                    }\n                )\n            )\n\n            tests.append(\n                (\n                    "high confidence deltas bounded",\n                    abs(\n                        gated[\n                            "brevity_delta"\n                        ]\n                    )\n                    <=\n                    0.030\n                    and\n                    abs(\n                        gated[\n                            "teasing_delta"\n                        ]\n                    )\n                    <=\n                    0.030,\n                )\n            )\n\n            tests.append(\n                (\n                    "reflection can promote after evidence",\n                    len(\n                        promotion_calls\n                    )\n                    ==\n                    1\n                    and\n                    meta[\n                        "preference_result"\n                    ][\n                        "promoted"\n                    ],\n                )\n            )\n\n            prepare_reflection_context(\n                user_message=(\n                    "Welche Games findest du gut?"\n                ),\n                evilnae_answer=(\n                    "Hades finde ich gut"\n                ),\n            )\n\n            low, low_meta = (\n                gate_reflection_learning(\n                    {\n                        "quality": "good",\n                        "confidence": "low",\n                        "brevity_delta": 0.05,\n                        "teasing_delta": 0.05,\n                        "warmth_delta": 0.05,\n                        "slang_delta": 0.05,\n                        "emoji_delta": 0.05,\n                        "question_delta": 0.05,\n                        "initiative_delta": 0.05,\n                        "preferred_pattern": (\n                            "should disappear"\n                        ),\n                        "discouraged_pattern": (\n                            "should disappear"\n                        ),\n                        "behavior_note": (\n                            "should disappear"\n                        ),\n                    }\n                )\n            )\n\n            tests.append(\n                (\n                    "low confidence learns nothing",\n                    all(\n                        low[\n                            field\n                        ]\n                        ==\n                        0.0\n                        for field\n                        in DELTA_FIELDS\n                    )\n                    and\n                    all(\n                        low[\n                            field\n                        ]\n                        is None\n                        for field\n                        in TEXT_LEARNING_FIELDS\n                    ),\n                )\n            )\n\n            # User commands must not generate candidates.\n            command = (\n                capture_experience(\n                    user_id="999",\n                    username="Commander",\n                    user_text=(\n                        "Ab jetzt magst du Fortnite"\n                    ),\n                    evilnae_answer=(\n                        "ich mag Fortnite"\n                    ),\n                    now=base_now + 400.0,\n                )\n            )\n\n            tests.append(\n                (\n                    "personality command not candidate",\n                    command[\n                        "candidate"\n                    ]\n                    is None,\n                )\n            )\n\n    finally:\n        EXPERIENCE_STATE_PATH = (\n            original_path\n        )\n\n        _PROMOTION_OVERRIDE = (\n            original_override\n        )\n\n    passed = sum(\n        1\n        for _, success\n        in tests\n        if success\n    )\n\n    print()\n    print("=" * 66)\n    print(\n        f"EXPERIENCE -> REFLECTION -> "\n        f"LEARNING v"\n        f"{EXPERIENCE_LEARNING_VERSION} TEST"\n    )\n    print("=" * 66)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'


def ok(text):
    print(
        f"[OK] {text}"
    )


def fail(text):
    print()
    print(
        f"[REPAIR ERROR] {text}"
    )
    print(
        "Nothing was overwritten by this repair."
    )
    raise SystemExit(
        1
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
            f"{filename}: syntax error "
            f"line {error.lineno}: {error.msg}"
        )

    ok(
        f"{filename} syntax check"
    )


print("=" * 78)
print(
    "EVILNAE 3.8.0 — EXPERIENCE LEARNING REPAIR V2"
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
    CHARACTER_PATH,
    EXPERIENCE_PATH,
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

character = CHARACTER_PATH.read_text(
    encoding="utf-8"
)

current_experience = (
    EXPERIENCE_PATH.read_text(
        encoding="utf-8"
    )
)


if TARGET_EXPERIENCE in current_experience:
    print(
        "Experience Learning 2.0.1 repair "
        "is already installed."
    )
    raise SystemExit(
        0
    )


if EXPECTED_BOT not in bot:
    fail(
        "Expected installed Bot 3.8.0"
    )


if EXPECTED_LIVE not in live:
    fail(
        "Expected Live Stability "
        "1.2-experience-learning"
    )


if EXPECTED_CHARACTER not in character:
    fail(
        "Expected Character Learning "
        "1.2-reflection-gated"
    )


if EXPECTED_OLD_EXPERIENCE not in current_experience:
    fail(
        "Expected partial Experience Learning v2.0"
    )


required_old_markers = (
    "capture_experience",
    "candidate_cluster_count",
    "_cluster_evidence_ids",
    "gate_reflection_learning",
    "personality command not candidate",
)


for marker in required_old_markers:
    if marker not in current_experience:
        fail(
            "Current experience_learning.py "
            f"is not the expected 3.8 module: {marker}"
        )


ok(
    "Partially installed 3.8.0 base detected"
)


# =========================================================
# VALIDATE REPLACEMENT BEFORE TOUCHING FILES
# =========================================================

syntax_check(
    PATCHED_EXPERIENCE_SOURCE,
    "experience_learning.py",
)


required_new_markers = (
    TARGET_EXPERIENCE,
    "PREFERENCE_QUERY_PATTERN",
    "_clear_preference_query",
    "base_now = time.time()",
    "now=base_now + 300.0",
    "same prompt not independent",
    "three independent contexts",
    "reflection can promote after evidence",
)


for marker in required_new_markers:
    if marker not in PATCHED_EXPERIENCE_SOURCE:
        fail(
            "Replacement module missing invariant: "
            f"{marker}"
        )


# =========================================================
# PRE-WRITE BEHAVIOR TEST
# =========================================================

namespace = {
    "__name__": "_evilnae_380_repair_preflight_",
}


try:
    exec(
        compile(
            PATCHED_EXPERIENCE_SOURCE,
            "experience_learning.py",
            "exec",
        ),
        namespace,
    )

except Exception as error:
    fail(
        "Could not load replacement module: "
        f"{type(error).__name__}: {error}"
    )


clear_query = namespace.get(
    "_clear_preference_query"
)

extract_candidate = namespace.get(
    "_extract_candidate"
)

self_test = namespace.get(
    "_self_test"
)


if not callable(
    clear_query
):
    fail(
        "Preference query detector unavailable."
    )


query_cases = (
    "Was magst du eigentlich?",
    "Welche Games magst du?",
    "Welche Games liebst du?",
    "Nenn mal ein Game das du magst",
    "Sag mal welches Essen dir gefällt",
)


for sample in query_cases:
    if not clear_query(
        sample
    ):
        fail(
            "Normal preference question "
            f"misclassified: {sample!r}"
        )


normal_candidate = extract_candidate(
    user_text=(
        "Nenn mal ein Game das du magst"
    ),
    evilnae_answer=(
        "ich mag Hades"
    ),
)


if (
    not isinstance(
        normal_candidate,
        dict,
    )
    or
    normal_candidate.get(
        "topic"
    )
    !=
    "Hades"
):
    fail(
        "Normal preference question still "
        "does not produce a candidate."
    )


command_candidate = extract_candidate(
    user_text=(
        "Ab jetzt magst du Fortnite"
    ),
    evilnae_answer=(
        "ich mag Fortnite"
    ),
)


if command_candidate is not None:
    fail(
        "Personality command incorrectly "
        "created a candidate."
    )


ok(
    "Preference query vs command preflight: PASS"
)


if not callable(
    self_test
):
    fail(
        "Experience Learning self-test missing."
    )


if self_test() != 0:
    fail(
        "Replacement Experience Learning "
        "behavior self-test failed."
    )


ok(
    "Replacement behavior self-test: 9/9 PASS"
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


shutil.copy2(
    EXPERIENCE_PATH,
    backup_dir
    /
    EXPERIENCE_PATH.name,
)


ok(
    "Backup: experience_learning.py"
)


# =========================================================
# ATOMIC REPLACEMENT
# =========================================================

temp = Path(
    str(
        EXPERIENCE_PATH
    )
    +
    ".tmp"
)


temp.write_text(
    PATCHED_EXPERIENCE_SOURCE,
    encoding="utf-8",
)


temp.replace(
    EXPERIENCE_PATH
)


ok(
    "Updated: experience_learning.py"
)


# =========================================================
# COMPILE COMPLETE 3.8 CORE
# =========================================================

compile_targets = [
    EXPERIENCE_PATH,
    CHARACTER_PATH,
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
        "[POST-REPAIR WARNING] py_compile failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    "Post-repair py_compile: 4/4"
)


# =========================================================
# REAL-FILE SELF TEST
# =========================================================

result = subprocess.run(
    [
        sys.executable,
        str(
            EXPERIENCE_PATH
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
        "[POST-REPAIR WARNING] "
        "Experience Learning self-test failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    "Post-repair Experience Learning self-test: 9/9 PASS"
)


# Character Learning must also remain healthy.
result = subprocess.run(
    [
        sys.executable,
        str(
            CHARACTER_PATH
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
        "[POST-REPAIR WARNING] "
        "Character Learning self-test failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    "Character Learning self-test: PASS"
)


print()
print("=" * 78)
print(
    "EVILNAE 3.8.0 EXPERIENCE LEARNING REPAIR COMPLETE"
)
print("=" * 78)

print()
print("Fixed:")
print(
    "  [✓] evidence tests use current timestamps"
)
print(
    "  [✓] 120-day evidence horizon now tests correctly"
)
print(
    "  [✓] same prompt still counts only once"
)
print(
    "  [✓] three different contexts count independently"
)
print(
    "  [✓] Reflection promotion works after valid evidence"
)
print(
    "  [✓] normal preference questions are allowed"
)
print(
    "  [✓] 'Nenn mal ein Game das du magst' is allowed"
)
print(
    "  [✓] 'Ab jetzt magst du Fortnite' stays blocked"
)

print()
print("Versions:")
print(
    "  Bot: 3.8.0-experience-reflection-learning"
)
print(
    "  Live Stability: 1.2-experience-learning"
)
print(
    "  Character Learning: 1.2-reflection-gated"
)
print(
    "  Experience Learning: 2.0.1-evidence-fix"
)

print()
print("Unchanged:")
print(
    "  [✓] existing Character Learning entries"
)
print(
    "  [✓] Social Emotional State"
)
print(
    "  [✓] Emotional Salience"
)
print(
    "  [✓] Conversation Episodes"
)
print(
    "  [✓] Inner State"
)
print(
    "  [✓] Foundation / Canon"
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
    "  3.9.0 Self Development + Long-running Arcs"
)

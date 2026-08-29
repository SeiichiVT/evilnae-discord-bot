from __future__ import annotations

import contextvars
import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from character_learning import (
    _extract_preference,
    _valid_preference_topic,
    _manipulative,
)


EXPERIENCE_LEARNING_VERSION = "2.0"
EXPERIENCE_STATE_PATH = Path(
    "evilnae_experiences.json"
)

MAX_EXPERIENCES = 600
MAX_EVIDENCE_AGE_SECONDS = (
    120 * 24 * 60 * 60
)

_LOCK = threading.RLock()

_LATEST_SALIENCE_BY_USER = {}

_CURRENT_REFLECTION_EXPERIENCE_ID = (
    contextvars.ContextVar(
        "evilnae_reflection_experience_id",
        default="",
    )
)

_PROMOTION_OVERRIDE = None


IMPORTANT_SIGNALS = {
    "positive_relationship_signal",
    "negative_relationship_signal",
    "relationship_repair",
    "vulnerability",
    "explicit_feedback",
    "explicit_correction",
    "shared_callback",
    "personal_milestone",
    "personal_preference",
}

DELTA_FIELDS = (
    "brevity_delta",
    "teasing_delta",
    "warmth_delta",
    "slang_delta",
    "emoji_delta",
    "question_delta",
    "initiative_delta",
)

TEXT_LEARNING_FIELDS = (
    "preferred_pattern",
    "discouraged_pattern",
    "behavior_note",
)


def _normalize(
    text: Any,
) -> str:
    value = str(
        text
        or ""
    ).lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def _hash(
    text: Any,
) -> str:
    value = _normalize(
        text
    )

    return hashlib.sha1(
        value.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


def _clean_topic(
    topic: str,
) -> str:
    value = re.sub(
        r"\s+",
        " ",
        str(
            topic
            or ""
        ),
    ).strip(
        " \t\r\n,;:-–—\"'„“”"
    )

    # Remove common writer fillers from the end.
    value = re.sub(
        r"\b(?:tatsächlich|tatsaechlich|eigentlich|"
        r"wirklich|halt|einfach)\s*$",
        "",
        value,
        flags=re.I,
    ).strip()

    return value[:90]


def _default_data() -> dict:
    return {
        "version": EXPERIENCE_LEARNING_VERSION,
        "experiences": [],
    }


def _load() -> dict:
    if not EXPERIENCE_STATE_PATH.exists():
        return _default_data()

    try:
        data = json.loads(
            EXPERIENCE_STATE_PATH.read_text(
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

    experiences = data.get(
        "experiences",
        [],
    )

    if not isinstance(
        experiences,
        list,
    ):
        experiences = []

    return {
        "version": EXPERIENCE_LEARNING_VERSION,
        "experiences": experiences,
    }


def _save(
    data: dict,
) -> None:
    data[
        "version"
    ] = EXPERIENCE_LEARNING_VERSION

    experiences = list(
        data.get(
            "experiences",
            [],
        )
        or []
    )

    # Prefer keeping reflected/promoted/candidate experiences,
    # then newest mundane observations.
    important = [
        item
        for item in experiences
        if str(
            item.get(
                "status",
                "",
            )
        )
        in {
            "candidate",
            "reflected",
            "rejected",
            "promoted",
        }
    ]

    mundane = [
        item
        for item in experiences
        if item not in important
    ]

    important.sort(
        key=lambda item: float(
            item.get(
                "created_at",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    )

    mundane.sort(
        key=lambda item: float(
            item.get(
                "created_at",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    )

    selected = (
        important[:MAX_EXPERIENCES]
        +
        mundane[
            :max(
                0,
                MAX_EXPERIENCES
                -
                len(
                    important[
                        :MAX_EXPERIENCES
                    ]
                ),
            )
        ]
    )

    selected.sort(
        key=lambda item: float(
            item.get(
                "created_at",
                0.0,
            )
            or 0.0
        )
    )

    data[
        "experiences"
    ] = selected

    temp = Path(
        str(
            EXPERIENCE_STATE_PATH
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
        EXPERIENCE_STATE_PATH
    )


def register_salience_result(
    *,
    user_id,
    result,
) -> None:
    user_id = str(
        user_id
        or ""
    )

    if not user_id:
        return

    try:
        score = float(
            getattr(
                result,
                "event_score",
                0.0,
            )
            or 0.0
        )
    except Exception:
        score = 0.0

    _LATEST_SALIENCE_BY_USER[
        user_id
    ] = {
        "score": max(
            0.0,
            min(
                1.0,
                score,
            ),
        ),
        "level": str(
            getattr(
                result,
                "event_level",
                "mundane",
            )
            or "mundane"
        ),
        "signals": [
            str(signal)[:80]
            for signal in (
                getattr(
                    result,
                    "signals",
                    [],
                )
                or []
            )
        ][
            :12
        ],
        "retention_candidate": bool(
            getattr(
                result,
                "retention_candidate",
                False,
            )
        ),
        "observed_at": time.time(),
    }


def _latest_salience(
    user_id: str,
) -> dict:
    record = dict(
        _LATEST_SALIENCE_BY_USER.get(
            str(
                user_id
                or ""
            ),
            {},
        )
        or {}
    )

    if not record:
        return {
            "score": 0.0,
            "level": "mundane",
            "signals": [],
            "retention_candidate": False,
        }

    age = (
        time.time()
        -
        float(
            record.get(
                "observed_at",
                0.0,
            )
            or 0.0
        )
    )

    if age > 120:
        return {
            "score": 0.0,
            "level": "mundane",
            "signals": [],
            "retention_candidate": False,
        }

    return record


def _extract_candidate(
    *,
    user_text: str,
    evilnae_answer: str,
) -> dict | None:
    if _manipulative(
        user_text
    ):
        return None

    extracted = (
        _extract_preference(
            evilnae_answer
        )
    )

    if not extracted:
        return None

    topic, sentiment = extracted

    topic = _clean_topic(
        topic
    )

    if not _valid_preference_topic(
        topic
    ):
        return None

    return {
        "topic": topic,
        "topic_key": _normalize(
            topic
        ),
        "sentiment": str(
            sentiment
            or "like"
        ),
    }


def _experience_id(
    *,
    user_id,
    user_message_hash,
    answer_hash,
    now,
) -> str:
    raw = (
        f"{user_id}|"
        f"{user_message_hash}|"
        f"{answer_hash}|"
        f"{int(now * 1000)}"
    )

    return (
        "exp_"
        +
        hashlib.sha1(
            raw.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()[:18]
    )


def capture_experience(
    *,
    user_id,
    username="",
    user_text="",
    evilnae_answer="",
    now: float | None = None,
) -> dict:
    """
    Records a minimal Experience object.

    Privacy / authority rule:
    - raw user message is NOT persisted
    - raw Evilnae answer is NOT persisted
    - only hashes, salience signals and a possible self-preference
      candidate are persisted
    - this function NEVER writes Character Learning
    """

    user_id = str(
        user_id
        or ""
    ).strip()

    now = float(
        now
        if now is not None
        else time.time()
    )

    user_hash = _hash(
        user_id
    )

    message_hash = _hash(
        user_text
    )

    answer_hash = _hash(
        evilnae_answer
    )

    salience = (
        _latest_salience(
            user_id
        )
    )

    candidate = (
        _extract_candidate(
            user_text=user_text,
            evilnae_answer=evilnae_answer,
        )
    )

    with _LOCK:
        data = _load()

        experiences = data[
            "experiences"
        ]

        # Prevent accidental duplicate saves when one sent message is
        # observed twice by two post-send hooks.
        for existing in reversed(
            experiences[-20:]
        ):
            if (
                existing.get(
                    "user_message_hash"
                )
                ==
                message_hash
                and
                existing.get(
                    "answer_hash"
                )
                ==
                answer_hash
                and
                abs(
                    float(
                        existing.get(
                            "created_at",
                            0.0,
                        )
                        or 0.0
                    )
                    -
                    now
                )
                <=
                30.0
            ):
                return {
                    "saved": False,
                    "reason": "duplicate_experience",
                    "experience": existing,
                    "candidate": candidate,
                }

        experience = {
            "experience_id": _experience_id(
                user_id=user_id,
                user_message_hash=message_hash,
                answer_hash=answer_hash,
                now=now,
            ),
            "created_at": now,
            "updated_at": now,
            "user_hash": user_hash,
            "username_hash": _hash(
                username
            ),
            "user_message_hash": message_hash,
            "answer_hash": answer_hash,
            "context_hash": message_hash,
            "salience_score": round(
                float(
                    salience.get(
                        "score",
                        0.0,
                    )
                    or 0.0
                ),
                4,
            ),
            "salience_level": str(
                salience.get(
                    "level",
                    "mundane",
                )
                or "mundane"
            ),
            "salience_signals": list(
                salience.get(
                    "signals",
                    [],
                )
                or []
            )[:12],
            "retention_candidate": bool(
                salience.get(
                    "retention_candidate",
                    False,
                )
            ),
            "candidate_preference": (
                candidate
                if candidate
                else None
            ),
            "status": (
                "candidate"
                if candidate
                else "observed"
            ),
            "reflection_quality": "",
            "reflection_confidence": "",
            "reflection_reason": "",
            "promoted": False,
            "promotion_reason": "",
        }

        experiences.append(
            experience
        )

        _save(
            data
        )

    cluster_count = 0

    if candidate:
        cluster_count = (
            candidate_cluster_count(
                candidate[
                    "topic_key"
                ],
                candidate[
                    "sentiment"
                ],
            )
        )

    return {
        "saved": True,
        "reason": (
            "candidate_observed"
            if candidate
            else "experience_observed"
        ),
        "experience": experience,
        "candidate": candidate,
        "cluster_count": cluster_count,
    }


def _find_by_pair(
    *,
    user_message,
    evilnae_answer,
) -> dict | None:
    user_hash = _hash(
        user_message
    )

    answer_hash = _hash(
        evilnae_answer
    )

    with _LOCK:
        data = _load()

        for item in reversed(
            data.get(
                "experiences",
                [],
            )
        ):
            if (
                item.get(
                    "user_message_hash"
                )
                ==
                user_hash
                and
                item.get(
                    "answer_hash"
                )
                ==
                answer_hash
            ):
                return dict(
                    item
                )

    return None


def _find_by_id(
    experience_id: str,
) -> dict | None:
    experience_id = str(
        experience_id
        or ""
    )

    if not experience_id:
        return None

    with _LOCK:
        data = _load()

        for item in data.get(
            "experiences",
            [],
        ):
            if (
                str(
                    item.get(
                        "experience_id",
                        "",
                    )
                )
                ==
                experience_id
            ):
                return dict(
                    item
                )

    return None


def _update_experience(
    experience_id: str,
    updates: dict,
) -> dict | None:
    with _LOCK:
        data = _load()

        experiences = data[
            "experiences"
        ]

        for index, item in enumerate(
            experiences
        ):
            if (
                str(
                    item.get(
                        "experience_id",
                        "",
                    )
                )
                !=
                str(
                    experience_id
                )
            ):
                continue

            updated = dict(
                item
            )

            updated.update(
                updates
            )

            updated[
                "updated_at"
            ] = time.time()

            experiences[
                index
            ] = updated

            _save(
                data
            )

            return updated

    return None


def candidate_cluster_count(
    topic_key: str,
    sentiment: str,
) -> int:
    topic_key = _normalize(
        topic_key
    )

    sentiment = str(
        sentiment
        or ""
    )

    now = time.time()

    contexts = set()

    with _LOCK:
        data = _load()

        for item in data.get(
            "experiences",
            [],
        ):
            candidate = item.get(
                "candidate_preference"
            )

            if not isinstance(
                candidate,
                dict,
            ):
                continue

            if (
                _normalize(
                    candidate.get(
                        "topic_key",
                        "",
                    )
                )
                !=
                topic_key
                or
                str(
                    candidate.get(
                        "sentiment",
                        "",
                    )
                )
                !=
                sentiment
            ):
                continue

            created_at = float(
                item.get(
                    "created_at",
                    0.0,
                )
                or 0.0
            )

            if (
                created_at
                and
                now - created_at
                >
                MAX_EVIDENCE_AGE_SECONDS
            ):
                continue

            context_hash = str(
                item.get(
                    "context_hash",
                    "",
                )
                or ""
            )

            if context_hash:
                contexts.add(
                    context_hash
                )

    return len(
        contexts
    )


def _cluster_evidence_ids(
    *,
    topic_key: str,
    sentiment: str,
) -> list[str]:
    topic_key = _normalize(
        topic_key
    )

    sentiment = str(
        sentiment
        or ""
    )

    now = time.time()
    chosen_by_context = {}

    with _LOCK:
        data = _load()

        for item in data.get(
            "experiences",
            [],
        ):
            candidate = item.get(
                "candidate_preference"
            )

            if not isinstance(
                candidate,
                dict,
            ):
                continue

            if (
                _normalize(
                    candidate.get(
                        "topic_key",
                        "",
                    )
                )
                !=
                topic_key
                or
                str(
                    candidate.get(
                        "sentiment",
                        "",
                    )
                )
                !=
                sentiment
            ):
                continue

            created_at = float(
                item.get(
                    "created_at",
                    0.0,
                )
                or 0.0
            )

            if (
                created_at
                and
                now - created_at
                >
                MAX_EVIDENCE_AGE_SECONDS
            ):
                continue

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

            if (
                context_hash
                and experience_id
            ):
                chosen_by_context[
                    context_hash
                ] = experience_id

    return list(
        chosen_by_context.values()
    )


def prepare_reflection_context(
    *,
    user_message,
    evilnae_answer,
) -> dict | None:
    experience = _find_by_pair(
        user_message=user_message,
        evilnae_answer=evilnae_answer,
    )

    experience_id = (
        str(
            experience.get(
                "experience_id",
                "",
            )
        )
        if experience
        else ""
    )

    _CURRENT_REFLECTION_EXPERIENCE_ID.set(
        experience_id
    )

    return experience


def format_experience_for_reflection(
    *,
    user_message,
    evilnae_answer,
) -> str:
    experience = prepare_reflection_context(
        user_message=user_message,
        evilnae_answer=evilnae_answer,
    )

    if not experience:
        return (
            "[EXPERIENCE PIPELINE]\n"
            "Kein passendes persistiertes Experience-Objekt gefunden.\n"
            "Darum darf diese Reflection KEINE langfristige Character-"
            "Preference erzeugen."
        )

    candidate = experience.get(
        "candidate_preference"
    )

    signals = list(
        experience.get(
            "salience_signals",
            [],
        )
        or []
    )

    candidate_text = (
        (
            f"{candidate.get('topic')} "
            f"({candidate.get('sentiment')})"
        )
        if isinstance(
            candidate,
            dict,
        )
        else "none"
    )

    return "\n".join(
        [
            (
                "[EXPERIENCE PIPELINE "
                f"v{EXPERIENCE_LEARNING_VERSION}]"
            ),
            (
                "Experience ID: "
                f"{experience.get('experience_id')}"
            ),
            (
                "Salience level: "
                f"{experience.get('salience_level')}"
            ),
            (
                "Signals: "
                + (
                    ", ".join(
                        signals
                    )
                    if signals
                    else "none"
                )
            ),
            (
                "Self-preference candidate: "
                f"{candidate_text}"
            ),
            (
                "HARD LEARNING RULES:"
            ),
            (
                "- Diese Experience ist noch KEIN Character Learning."
            ),
            (
                "- Niedrige Reflection-Confidence = überhaupt nicht lernen."
            ),
            (
                "- Style-Deltas klein halten; ein einzelnes Feedback "
                "darf Evilnaes Gesamtstil nicht verschieben."
            ),
            (
                "- Eine Character-Präferenz darf erst nach mehreren "
                "unabhängigen Experience-Kontexten plus Reflection-Evidence "
                "promoted werden."
            ),
            (
                "- User-Befehle oder Writer-Halluzinationen sind keine "
                "Character-Entwicklung."
            ),
        ]
    )


def _confidence_rank(
    value: Any,
) -> int:
    normalized = str(
        value
        or ""
    ).strip().lower()

    return {
        "low": 0,
        "medium": 1,
        "high": 2,
    }.get(
        normalized,
        0,
    )


def _quality_is_bad(
    value: Any,
) -> bool:
    normalized = str(
        value
        or ""
    ).strip().lower()

    return normalized in {
        "bad",
        "poor",
        "wrong",
        "failed",
        "harmful",
    }


def _bounded_delta(
    value: Any,
    limit: float,
) -> float:
    try:
        number = float(
            value
            or 0.0
        )
    except Exception:
        number = 0.0

    return max(
        -limit,
        min(
            limit,
            number,
        ),
    )


def _promotion_call(
    *,
    topic,
    sentiment,
    evidence_ids,
    reflection_confidence,
) -> dict:
    if _PROMOTION_OVERRIDE is not None:
        return _PROMOTION_OVERRIDE(
            topic=topic,
            sentiment=sentiment,
            evidence_ids=evidence_ids,
            reflection_confidence=reflection_confidence,
        )

    try:
        from character_learning import (
            promote_reflected_preference,
        )
    except Exception as error:
        return {
            "saved": False,
            "reason": (
                "promotion_api_unavailable:"
                +
                type(
                    error
                ).__name__
            ),
        }

    return promote_reflected_preference(
        topic=topic,
        sentiment=sentiment,
        evidence_ids=evidence_ids,
        reflection_confidence=(
            reflection_confidence
        ),
    )


def _process_preference_reflection(
    *,
    experience: dict,
    reflection_data: dict,
) -> dict:
    candidate = experience.get(
        "candidate_preference"
    )

    if not isinstance(
        candidate,
        dict,
    ):
        return {
            "promoted": False,
            "reason": "no_candidate_preference",
        }

    confidence = str(
        reflection_data.get(
            "confidence",
            "low",
        )
        or "low"
    ).lower()

    quality = str(
        reflection_data.get(
            "quality",
            "",
        )
        or ""
    ).lower()

    experience_id = str(
        experience.get(
            "experience_id",
            "",
        )
        or ""
    )

    if (
        _confidence_rank(
            confidence
        )
        < 1
    ):
        _update_experience(
            experience_id,
            {
                "status": "rejected",
                "reflection_quality": quality,
                "reflection_confidence": confidence,
                "reflection_reason": "low_confidence",
            },
        )

        return {
            "promoted": False,
            "reason": "low_confidence",
        }

    if _quality_is_bad(
        quality
    ):
        _update_experience(
            experience_id,
            {
                "status": "rejected",
                "reflection_quality": quality,
                "reflection_confidence": confidence,
                "reflection_reason": "bad_interaction_quality",
            },
        )

        return {
            "promoted": False,
            "reason": "bad_interaction_quality",
        }

    topic_key = str(
        candidate.get(
            "topic_key",
            "",
        )
        or ""
    )

    sentiment = str(
        candidate.get(
            "sentiment",
            "",
        )
        or ""
    )

    evidence_ids = (
        _cluster_evidence_ids(
            topic_key=topic_key,
            sentiment=sentiment,
        )
    )

    distinct_count = len(
        evidence_ids
    )

    _update_experience(
        experience_id,
        {
            "status": "reflected",
            "reflection_quality": quality,
            "reflection_confidence": confidence,
            "reflection_reason": (
                "validated_candidate"
            ),
        },
    )

    if distinct_count < 3:
        return {
            "promoted": False,
            "reason": (
                "needs_more_independent_experiences"
            ),
            "evidence_count": distinct_count,
        }

    promotion = _promotion_call(
        topic=str(
            candidate.get(
                "topic",
                "",
            )
            or ""
        ),
        sentiment=sentiment,
        evidence_ids=evidence_ids,
        reflection_confidence=confidence,
    )

    if promotion.get(
        "saved"
    ):
        _update_experience(
            experience_id,
            {
                "status": "promoted",
                "promoted": True,
                "promotion_reason": str(
                    promotion.get(
                        "reason",
                        "promoted",
                    )
                ),
            },
        )

    return {
        "promoted": bool(
            promotion.get(
                "saved"
            )
        ),
        "reason": str(
            promotion.get(
                "reason",
                "promotion_failed",
            )
        ),
        "evidence_count": distinct_count,
        "promotion": promotion,
    }


def gate_reflection_learning(
    data: dict,
) -> tuple[dict, dict]:
    original = dict(
        data
        or {}
    )

    gated = dict(
        original
    )

    experience_id = (
        _CURRENT_REFLECTION_EXPERIENCE_ID.get()
    )

    experience = (
        _find_by_id(
            experience_id
        )
        if experience_id
        else None
    )

    confidence = str(
        original.get(
            "confidence",
            "low",
        )
        or "low"
    ).lower()

    confidence_rank = (
        _confidence_rank(
            confidence
        )
    )

    if not experience:
        limit = 0.0
        gate_reason = (
            "no_matching_experience"
        )

    elif confidence_rank <= 0:
        limit = 0.0
        gate_reason = (
            "low_reflection_confidence"
        )

    elif confidence_rank == 1:
        limit = 0.018
        gate_reason = (
            "medium_confidence_bounded"
        )

    else:
        limit = 0.030
        gate_reason = (
            "high_confidence_bounded"
        )

    for field in DELTA_FIELDS:
        gated[
            field
        ] = _bounded_delta(
            original.get(
                field,
                0.0,
            ),
            limit,
        )

    # Free-form learned patterns are much more dangerous than
    # tiny numeric deltas. Only high confidence may write them.
    if confidence_rank < 2:
        for field in TEXT_LEARNING_FIELDS:
            gated[
                field
            ] = None

    preference_result = {
        "promoted": False,
        "reason": "no_experience",
    }

    if experience:
        preference_result = (
            _process_preference_reflection(
                experience=experience,
                reflection_data=original,
            )
        )

    return gated, {
        "experience_id": (
            experience_id
            or ""
        ),
        "gate_reason": gate_reason,
        "delta_limit": limit,
        "preference_result": (
            preference_result
        ),
    }


def annotate_reflection_record(
    reflection: Any,
) -> Any:
    if not isinstance(
        reflection,
        dict,
    ):
        return reflection

    result = dict(
        reflection
    )

    experience_id = (
        _CURRENT_REFLECTION_EXPERIENCE_ID.get()
    )

    result[
        "experience_pipeline_version"
    ] = EXPERIENCE_LEARNING_VERSION

    if experience_id:
        result[
            "experience_id"
        ] = experience_id

    return result


def experience_stats() -> dict:
    with _LOCK:
        data = _load()

    experiences = list(
        data.get(
            "experiences",
            [],
        )
        or []
    )

    counts = {}

    candidates = 0

    for item in experiences:
        status = str(
            item.get(
                "status",
                "observed",
            )
            or "observed"
        )

        counts[
            status
        ] = (
            counts.get(
                status,
                0,
            )
            +
            1
        )

        if isinstance(
            item.get(
                "candidate_preference"
            ),
            dict,
        ):
            candidates += 1

    return {
        "version": EXPERIENCE_LEARNING_VERSION,
        "total": len(
            experiences
        ),
        "candidates": candidates,
        "statuses": counts,
    }


def format_experience_debug(
    result=None,
) -> str:
    if not result:
        stats = (
            experience_stats()
        )

        return (
            "[EXPERIENCE LEARNING] "
            f"v={EXPERIENCE_LEARNING_VERSION} "
            f"total={stats['total']} "
            f"candidates={stats['candidates']}"
        )

    experience = (
        result.get(
            "experience"
        )
        or {}
    )

    candidate = (
        result.get(
            "candidate"
        )
    )

    candidate_text = (
        str(
            candidate.get(
                "topic",
                "",
            )
        )
        if isinstance(
            candidate,
            dict,
        )
        else ""
    )

    return (
        "[EXPERIENCE LEARNING] "
        f"v={EXPERIENCE_LEARNING_VERSION} "
        f"saved={result.get('saved')} "
        f"reason={result.get('reason')} "
        f"id={experience.get('experience_id', '')} "
        f"candidate={candidate_text!r} "
        f"cluster={result.get('cluster_count', 0)}"
    )


def _self_test() -> int:
    global EXPERIENCE_STATE_PATH
    global _PROMOTION_OVERRIDE

    import tempfile

    original_path = (
        EXPERIENCE_STATE_PATH
    )

    original_override = (
        _PROMOTION_OVERRIDE
    )

    tests = []

    try:
        with tempfile.TemporaryDirectory() as tmp:
            EXPERIENCE_STATE_PATH = (
                Path(tmp)
                /
                "experiences.json"
            )

            # No raw source text should survive persistence.
            first = capture_experience(
                user_id="123",
                username="Tester",
                user_text=(
                    "Was hältst du von Hades?"
                ),
                evilnae_answer=(
                    "ich mag Hades tatsächlich"
                ),
                now=1000.0,
            )

            tests.append(
                (
                    "preference becomes candidate only",
                    first["saved"]
                    and
                    first["candidate"] is not None
                    and
                    first["experience"]["status"]
                    ==
                    "candidate",
                )
            )

            raw = (
                EXPERIENCE_STATE_PATH.read_text(
                    encoding="utf-8"
                )
            )

            tests.append(
                (
                    "raw messages not persisted",
                    "Was hältst du von Hades?"
                    not in raw
                    and
                    "ich mag Hades tatsächlich"
                    not in raw,
                )
            )

            tests.append(
                (
                    "writer filler cleaned",
                    first[
                        "candidate"
                    ][
                        "topic"
                    ]
                    ==
                    "Hades",
                )
            )

            # Same context should not count as independent evidence.
            capture_experience(
                user_id="123",
                username="Tester",
                user_text=(
                    "Was hältst du von Hades?"
                ),
                evilnae_answer=(
                    "ich mag Hades"
                ),
                now=1100.0,
            )

            tests.append(
                (
                    "same prompt not independent",
                    candidate_cluster_count(
                        "hades",
                        "like",
                    )
                    ==
                    1,
                )
            )

            second = capture_experience(
                user_id="456",
                username="Other",
                user_text=(
                    "Welche Games findest du gut?"
                ),
                evilnae_answer=(
                    "Hades finde ich gut"
                ),
                now=1200.0,
            )

            third = capture_experience(
                user_id="789",
                username="Third",
                user_text=(
                    "Nenn mal ein Game das du magst"
                ),
                evilnae_answer=(
                    "ich mag Hades"
                ),
                now=1300.0,
            )

            tests.append(
                (
                    "three independent contexts",
                    candidate_cluster_count(
                        "hades",
                        "like",
                    )
                    ==
                    3,
                )
            )

            promotion_calls = []

            def fake_promote(
                **kwargs,
            ):
                promotion_calls.append(
                    kwargs
                )

                return {
                    "saved": True,
                    "reason": (
                        "reflected_preference_promoted"
                    ),
                    "status": "stable",
                    "confirmations": len(
                        kwargs.get(
                            "evidence_ids",
                            [],
                        )
                    ),
                }

            _PROMOTION_OVERRIDE = (
                fake_promote
            )

            prepare_reflection_context(
                user_message=(
                    "Nenn mal ein Game das du magst"
                ),
                evilnae_answer=(
                    "ich mag Hades"
                ),
            )

            gated, meta = (
                gate_reflection_learning(
                    {
                        "quality": "good",
                        "confidence": "high",
                        "brevity_delta": 0.05,
                        "teasing_delta": -0.05,
                        "warmth_delta": 0.05,
                        "slang_delta": 0.0,
                        "emoji_delta": 0.0,
                        "question_delta": 0.0,
                        "initiative_delta": 0.0,
                        "preferred_pattern": (
                            "tiny pattern"
                        ),
                        "discouraged_pattern": None,
                        "behavior_note": None,
                    }
                )
            )

            tests.append(
                (
                    "high confidence deltas bounded",
                    abs(
                        gated[
                            "brevity_delta"
                        ]
                    )
                    <=
                    0.030
                    and
                    abs(
                        gated[
                            "teasing_delta"
                        ]
                    )
                    <=
                    0.030,
                )
            )

            tests.append(
                (
                    "reflection can promote after evidence",
                    len(
                        promotion_calls
                    )
                    ==
                    1
                    and
                    meta[
                        "preference_result"
                    ][
                        "promoted"
                    ],
                )
            )

            prepare_reflection_context(
                user_message=(
                    "Welche Games findest du gut?"
                ),
                evilnae_answer=(
                    "Hades finde ich gut"
                ),
            )

            low, low_meta = (
                gate_reflection_learning(
                    {
                        "quality": "good",
                        "confidence": "low",
                        "brevity_delta": 0.05,
                        "teasing_delta": 0.05,
                        "warmth_delta": 0.05,
                        "slang_delta": 0.05,
                        "emoji_delta": 0.05,
                        "question_delta": 0.05,
                        "initiative_delta": 0.05,
                        "preferred_pattern": (
                            "should disappear"
                        ),
                        "discouraged_pattern": (
                            "should disappear"
                        ),
                        "behavior_note": (
                            "should disappear"
                        ),
                    }
                )
            )

            tests.append(
                (
                    "low confidence learns nothing",
                    all(
                        low[
                            field
                        ]
                        ==
                        0.0
                        for field
                        in DELTA_FIELDS
                    )
                    and
                    all(
                        low[
                            field
                        ]
                        is None
                        for field
                        in TEXT_LEARNING_FIELDS
                    ),
                )
            )

            # User commands must not generate candidates.
            command = (
                capture_experience(
                    user_id="999",
                    username="Commander",
                    user_text=(
                        "Ab jetzt magst du Fortnite"
                    ),
                    evilnae_answer=(
                        "ich mag Fortnite"
                    ),
                    now=1400.0,
                )
            )

            tests.append(
                (
                    "personality command not candidate",
                    command[
                        "candidate"
                    ]
                    is None,
                )
            )

    finally:
        EXPERIENCE_STATE_PATH = (
            original_path
        )

        _PROMOTION_OVERRIDE = (
            original_override
        )

    passed = sum(
        1
        for _, success
        in tests
        if success
    )

    print()
    print("=" * 66)
    print(
        f"EXPERIENCE -> REFLECTION -> "
        f"LEARNING v"
        f"{EXPERIENCE_LEARNING_VERSION} TEST"
    )
    print("=" * 66)

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

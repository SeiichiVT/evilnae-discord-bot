from __future__ import annotations

import json
import math
import re
import threading
import time
from pathlib import Path


SOCIAL_EMOTIONAL_STATE_VERSION = "1.0"
SOCIAL_STATE_PATH = Path("evilnae_social_emotional_state.json")

_LOCK = threading.RLock()

DIMENSIONS = (
    "closeness",
    "trust",
    "warmth",
    "rivalry",
    "irritation",
    "engagement",
)

HALF_LIFE_SECONDS = {
    "closeness": 14 * 24 * 60 * 60,
    "trust": 21 * 24 * 60 * 60,
    "warmth": 12 * 60 * 60,
    "rivalry": 36 * 60 * 60,
    "irritation": 6 * 60 * 60,
    "engagement": 3 * 60 * 60,
}

MAX_EVENT_HISTORY = 16

POSITIVE_PATTERN = re.compile(
    r"\b(?:danke|dankeschön|dankeschoen|lieb\s+von\s+dir|"
    r"gut\s+gemacht|stolz\s+auf\s+dich|supporte\s+dich|"
    r"du\s+bist\s+(?:cool|lustig|witzig|süß|suess|lieb))\b",
    re.I,
)

AFFECTION_PATTERN = re.compile(
    r"\b(?:hab\s+dich\s+lieb|ich\s+mag\s+dich|"
    r"liebe\s+dich|love\s+you|luv\s+u|"
    r"meine\s+sis|sis\b)\b",
    re.I,
)

APOLOGY_PATTERN = re.compile(
    r"\b(?:sorry|tut\s+mir\s+leid|entschuldige|"
    r"war\s+nicht\s+so\s+gemeint)\b",
    re.I,
)

TRUST_PATTERN = re.compile(
    r"\b(?:ich\s+vertrau(?:e)?\s+dir|"
    r"kann\s+ich\s+dir\s+was\s+sagen|"
    r"ich\s+muss\s+dir\s+was\s+erzählen|"
    r"ich\s+muss\s+dir\s+was\s+erzaehlen)\b",
    re.I,
)

VULNERABLE_PATTERN = re.compile(
    r"\b(?:ich\s+hab(?:e)?\s+angst|"
    r"ich\s+bin\s+traurig|"
    r"mir\s+geht(?:'|’)?s\s+nicht\s+gut|"
    r"ich\s+bin\s+überfordert|ich\s+bin\s+ueberfordert|"
    r"ich\s+fühl(?:e)?\s+mich|ich\s+fuehl(?:e)?\s+mich)\b",
    re.I,
)

PLAYFUL_RIVALRY_PATTERN = re.compile(
    r"\b(?:skill\s+issue|ich\s+bin\s+besser|"
    r"du\s+verlierst|du\s+packst\s+das\s+nicht|"
    r"1v1|fight\s+me|komm\s+doch|"
    r"nö+|noe+|cope|seethe|l\s+take|"
    r"verrat|verräter|verraeter)\b",
    re.I,
)

HOSTILITY_PATTERN = re.compile(
    r"\b(?:halt\s+die\s+klappe|"
    r"du\s+bist\s+(?:dumm|scheiße|scheisse|nervig|"
    r"bescheuert|idiotisch)|"
    r"ich\s+hasse\s+dich|"
    r"verpiss\s+dich|fick\s+dich)\b",
    re.I,
)

LAUGHTER_PATTERN = re.compile(
    r"(?:\b(?:xd+|lol+|lmao|haha+|hehe+)\b|😂|🤣)",
    re.I,
)

CARE_SENSITIVE_PATTERN = re.compile(
    r"\b(?:kopfschmerz|migräne|migraene|schmerzen|"
    r"krank|fieber|mir\s+geht(?:'|’)?s\s+nicht\s+gut|"
    r"bitte\s+leiser|kümmer(?:e)?\s+dich|kuemmer(?:e)?\s+dich)\b",
    re.I,
)


def _clamp(value: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def _empty_state(
    user_id: str,
    username: str = "",
    now: float | None = None,
) -> dict:
    now = float(
        now
        if now is not None
        else time.time()
    )

    return {
        "user_id": str(user_id),
        "username": str(username or ""),
        "closeness": 0.0,
        "trust": 0.0,
        "warmth": 0.0,
        "rivalry": 0.0,
        "irritation": 0.0,
        "engagement": 0.0,
        "updated_at": now,
        "last_interaction_at": 0.0,
        "last_event_id": "",
        "events": [],
    }


def _normalize_state(
    state: dict,
    *,
    user_id: str,
    username: str = "",
    now: float | None = None,
) -> dict:
    if not isinstance(
        state,
        dict,
    ):
        state = {}

    result = _empty_state(
        user_id,
        username,
        now,
    )

    result.update(
        {
            key: state.get(
                key,
                result[key],
            )
            for key in result
        }
    )

    result["user_id"] = str(user_id)

    if username:
        result["username"] = str(
            username
        )

    for name in DIMENSIONS:
        try:
            result[name] = _clamp(
                float(
                    result.get(
                        name,
                        0.0,
                    )
                    or 0.0
                )
            )
        except Exception:
            result[name] = 0.0

    try:
        result["updated_at"] = float(
            result.get(
                "updated_at",
                0.0,
            )
            or 0.0
        )
    except Exception:
        result["updated_at"] = 0.0

    try:
        result["last_interaction_at"] = float(
            result.get(
                "last_interaction_at",
                0.0,
            )
            or 0.0
        )
    except Exception:
        result["last_interaction_at"] = 0.0

    result["last_event_id"] = str(
        result.get(
            "last_event_id",
            "",
        )
        or ""
    )

    events = result.get(
        "events",
        [],
    )

    if not isinstance(
        events,
        list,
    ):
        events = []

    result["events"] = [
        str(event)[:80]
        for event in events[-MAX_EVENT_HISTORY:]
        if str(event).strip()
    ]

    return result


def _load() -> dict:
    if not SOCIAL_STATE_PATH.exists():
        return {
            "version": SOCIAL_EMOTIONAL_STATE_VERSION,
            "users": {},
        }

    try:
        data = json.loads(
            SOCIAL_STATE_PATH.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {
            "version": SOCIAL_EMOTIONAL_STATE_VERSION,
            "users": {},
        }

    if not isinstance(
        data,
        dict,
    ):
        data = {}

    users = data.get(
        "users",
        {},
    )

    if not isinstance(
        users,
        dict,
    ):
        users = {}

    return {
        "version": SOCIAL_EMOTIONAL_STATE_VERSION,
        "users": users,
    }


def _save(data: dict) -> None:
    temp = Path(
        str(SOCIAL_STATE_PATH)
        + ".tmp"
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
        SOCIAL_STATE_PATH
    )


def _decay_factor(
    elapsed: float,
    half_life: float,
) -> float:
    if elapsed <= 0:
        return 1.0

    if half_life <= 0:
        return 0.0

    return math.pow(
        0.5,
        elapsed / half_life,
    )


def decay_state(
    state: dict,
    *,
    now: float | None = None,
) -> dict:
    now = float(
        now
        if now is not None
        else time.time()
    )

    result = dict(
        state
    )

    try:
        updated_at = float(
            result.get(
                "updated_at",
                now,
            )
            or now
        )
    except Exception:
        updated_at = now

    elapsed = max(
        0.0,
        now - updated_at,
    )

    for name in DIMENSIONS:
        current = _clamp(
            float(
                result.get(
                    name,
                    0.0,
                )
                or 0.0
            )
        )

        factor = _decay_factor(
            elapsed,
            HALF_LIFE_SECONDS[
                name
            ],
        )

        result[name] = round(
            _clamp(
                current
                * factor
            ),
            4,
        )

    result["updated_at"] = now

    return result


def _apply_delta(
    state: dict,
    name: str,
    amount: float,
) -> None:
    state[name] = round(
        _clamp(
            float(
                state.get(
                    name,
                    0.0,
                )
                or 0.0
            )
            +
            float(amount)
        ),
        4,
    )


def _signal_deltas(
    *,
    user_text: str,
    direct: bool,
    replied_to_bot: bool,
    name_mentioned: bool,
) -> tuple[dict, list[str]]:
    text = str(
        user_text
        or ""
    )

    deltas = {
        name: 0.0
        for name in DIMENSIONS
    }

    signals = []

    if direct:
        deltas["engagement"] += 0.09
        signals.append(
            "direct_engagement"
        )

    elif replied_to_bot:
        deltas["engagement"] += 0.08
        signals.append(
            "reply_engagement"
        )

    elif name_mentioned:
        deltas["engagement"] += 0.04
        signals.append(
            "mention_engagement"
        )

    if POSITIVE_PATTERN.search(
        text
    ):
        deltas["warmth"] += 0.10
        deltas["closeness"] += 0.025
        deltas["trust"] += 0.015
        signals.append(
            "positive"
        )

    if AFFECTION_PATTERN.search(
        text
    ):
        deltas["warmth"] += 0.16
        deltas["closeness"] += 0.055
        deltas["trust"] += 0.025
        signals.append(
            "affection"
        )

    if APOLOGY_PATTERN.search(
        text
    ):
        deltas["warmth"] += 0.08
        deltas["trust"] += 0.035
        deltas["irritation"] -= 0.12
        signals.append(
            "apology"
        )

    if TRUST_PATTERN.search(
        text
    ):
        deltas["trust"] += 0.075
        deltas["closeness"] += 0.025
        deltas["warmth"] += 0.035
        signals.append(
            "trust"
        )

    if VULNERABLE_PATTERN.search(
        text
    ):
        # Only the signal label is stored.
        # The sensitive message itself is never persisted here.
        deltas["trust"] += 0.045
        deltas["closeness"] += 0.015
        deltas["warmth"] += 0.035
        signals.append(
            "vulnerability"
        )

    playful = bool(
        PLAYFUL_RIVALRY_PATTERN.search(
            text
        )
    )

    laughter = bool(
        LAUGHTER_PATTERN.search(
            text
        )
    )

    hostile = bool(
        HOSTILITY_PATTERN.search(
            text
        )
    )

    if playful:
        deltas["rivalry"] += 0.11
        deltas["engagement"] += 0.04
        signals.append(
            "playful_rivalry"
        )

    if hostile:
        if laughter:
            deltas["rivalry"] += 0.08
            deltas["irritation"] += 0.015
            signals.append(
                "teasing_hostility"
            )

        else:
            deltas["irritation"] += 0.10
            deltas["warmth"] -= 0.04
            signals.append(
                "hostility"
            )

    if CARE_SENSITIVE_PATTERN.search(
        text
    ):
        # Serious/boundary messages must not make Evilnae annoyed
        # simply because someone asks for consideration.
        deltas["irritation"] = min(
            deltas["irritation"],
            0.0,
        )
        signals.append(
            "care_context"
        )

    caps = {
        "closeness": 0.07,
        "trust": 0.09,
        "warmth": 0.20,
        "rivalry": 0.15,
        "irritation": 0.12,
        "engagement": 0.14,
    }

    for name in DIMENSIONS:
        cap = caps[
            name
        ]

        deltas[name] = max(
            -cap,
            min(
                cap,
                deltas[name],
            ),
        )

    return deltas, signals


def observe_social_interaction(
    *,
    user_id,
    username="",
    user_text="",
    direct=False,
    replied_to_bot=False,
    name_mentioned=False,
    event_id="",
    now: float | None = None,
) -> dict:
    user_id = str(
        user_id
        or ""
    ).strip()

    if not user_id:
        return {
            "saved": False,
            "reason": "missing_user_id",
            "user_id": "",
            "signals": [],
            "state": None,
        }

    now = float(
        now
        if now is not None
        else time.time()
    )

    event_id = str(
        event_id
        or ""
    )

    with _LOCK:
        data = _load()
        users = data[
            "users"
        ]

        current = _normalize_state(
            users.get(
                user_id,
                {},
            ),
            user_id=user_id,
            username=username,
            now=now,
        )

        current = decay_state(
            current,
            now=now,
        )

        if (
            event_id
            and current.get(
                "last_event_id"
            )
            ==
            event_id
        ):
            return {
                "saved": False,
                "reason": "duplicate_event",
                "user_id": user_id,
                "signals": [],
                "state": current,
            }

        deltas, signals = _signal_deltas(
            user_text=user_text,
            direct=bool(direct),
            replied_to_bot=bool(
                replied_to_bot
            ),
            name_mentioned=bool(
                name_mentioned
            ),
        )

        for name in DIMENSIONS:
            _apply_delta(
                current,
                name,
                deltas[
                    name
                ],
            )

        current["username"] = str(
            username
            or current.get(
                "username",
                "",
            )
        )

        current[
            "last_interaction_at"
        ] = now

        current[
            "updated_at"
        ] = now

        if event_id:
            current[
                "last_event_id"
            ] = event_id

        if signals:
            current[
                "events"
            ] = (
                list(
                    current.get(
                        "events",
                        [],
                    )
                )
                +
                signals
            )[-MAX_EVENT_HISTORY:]

        users[
            user_id
        ] = current

        data[
            "version"
        ] = (
            SOCIAL_EMOTIONAL_STATE_VERSION
        )

        _save(
            data
        )

    return {
        "saved": True,
        "reason": "observed",
        "user_id": user_id,
        "signals": signals,
        "deltas": deltas,
        "state": current,
    }


def get_social_state(
    user_id,
    *,
    username="",
    now: float | None = None,
    persist_decay=True,
) -> dict:
    user_id = str(
        user_id
        or ""
    ).strip()

    if not user_id:
        return _empty_state(
            "",
            username,
            now,
        )

    now = float(
        now
        if now is not None
        else time.time()
    )

    with _LOCK:
        data = _load()
        users = data[
            "users"
        ]

        current = _normalize_state(
            users.get(
                user_id,
                {},
            ),
            user_id=user_id,
            username=username,
            now=now,
        )

        decayed = decay_state(
            current,
            now=now,
        )

        if persist_decay:
            users[
                user_id
            ] = decayed
            data[
                "version"
            ] = (
                SOCIAL_EMOTIONAL_STATE_VERSION
            )
            _save(
                data
            )

    return decayed


def _band(
    value: float,
) -> str:
    value = float(
        value
    )

    if value >= 0.72:
        return "high"

    if value >= 0.42:
        return "medium"

    if value >= 0.16:
        return "low"

    return "neutral"


def format_social_state_for_prompt(
    user_id,
    *,
    username="",
) -> str:
    state = get_social_state(
        user_id,
        username=username,
    )

    return "\n".join(
        [
            (
                "[SOCIAL EMOTIONAL STATE "
                f"v{SOCIAL_EMOTIONAL_STATE_VERSION}]"
            ),
            (
                "Temporärer, abklingender sozialer Zustand "
                "gegenüber genau diesem User."
            ),
            (
                "Er beeinflusst Ton/Nähe/Banter, ist aber KEIN "
                "Faktenbeweis und KEINE dauerhafte Beziehung."
            ),
            (
                f"- closeness: "
                f"{_band(state['closeness'])}"
            ),
            (
                f"- trust: "
                f"{_band(state['trust'])}"
            ),
            (
                f"- warmth: "
                f"{_band(state['warmth'])}"
            ),
            (
                f"- rivalry: "
                f"{_band(state['rivalry'])}"
            ),
            (
                f"- irritation: "
                f"{_band(state['irritation'])}"
            ),
            (
                f"- engagement: "
                f"{_band(state['engagement'])}"
            ),
            (
                "HARD RULES: keine Scores erwähnen; keine "
                "Beziehungsfakten daraus erfinden; Serious/Care "
                "Context schlägt Rivalry/Irritation; hohe Irritation "
                "allein darf Evilnae nicht plötzlich dauerhaft "
                "schlecht gelaunt machen."
            ),
        ]
    )


def apply_social_state_to_plan(
    plan,
    *,
    user_id,
    user_text="",
    is_hanae=False,
):
    state = get_social_state(
        user_id
    )

    sensitive = bool(
        CARE_SENSITIVE_PATTERN.search(
            str(
                user_text
                or ""
            )
        )
    )

    warmth = float(
        state.get(
            "warmth",
            0.0,
        )
        or 0.0
    )

    closeness = float(
        state.get(
            "closeness",
            0.0,
        )
        or 0.0
    )

    trust = float(
        state.get(
            "trust",
            0.0,
        )
        or 0.0
    )

    rivalry = float(
        state.get(
            "rivalry",
            0.0,
        )
        or 0.0
    )

    irritation = float(
        state.get(
            "irritation",
            0.0,
        )
        or 0.0
    )

    engagement = float(
        state.get(
            "engagement",
            0.0,
        )
        or 0.0
    )

    social_warmth_floor = min(
        0.62,
        0.18
        + warmth * 0.42
        + closeness * 0.22
        + trust * 0.12,
    )

    if not sensitive:
        plan.warmth_intensity = max(
            float(
                getattr(
                    plan,
                    "warmth_intensity",
                    0.0,
                )
                or 0.0
            ),
            social_warmth_floor,
        )

    rivalry_effect = rivalry

    if is_hanae:
        rivalry_effect = max(
            rivalry_effect,
            0.22,
        )

    if (
        not sensitive
        and rivalry_effect >= 0.34
        and irritation < 0.65
    ):
        plan.banter_intensity = max(
            float(
                getattr(
                    plan,
                    "banter_intensity",
                    0.0,
                )
                or 0.0
            ),
            min(
                0.72,
                0.32
                + rivalry_effect * 0.48,
            ),
        )

        if getattr(
            plan,
            "stance",
            "",
        ) in {
            "neutral",
            "dry",
        }:
            plan.stance = (
                "smug"
                if rivalry_effect >= 0.58
                else "playful"
            )

    # Important: relational irritation is NOT global mood authority.
    if (
        not sensitive
        and irritation >= 0.48
    ):
        plan.warmth_intensity = max(
            0.16,
            min(
                float(
                    getattr(
                        plan,
                        "warmth_intensity",
                        0.3,
                    )
                    or 0.3
                ),
                0.42,
            ),
        )

        existing = list(
            getattr(
                plan,
                "must_avoid",
                [],
            )
            or []
        )

        for item in (
            "Irritation als globale schlechte Laune darstellen",
            "User wegen alter Irritation grundlos anfahren",
            "grausam/beleidigend statt spielerisch-firm reagieren",
        ):
            if item not in existing:
                existing.append(
                    item
                )

        plan.must_avoid = existing[
            :16
        ]

    social_angle = (
        "Temporärer Social State: "
        f"closeness={_band(closeness)}, "
        f"trust={_band(trust)}, "
        f"warmth={_band(warmth)}, "
        f"rivalry={_band(rivalry_effect)}, "
        f"irritation={_band(irritation)}, "
        f"engagement={_band(engagement)}. "
        "Nur als Ton-/Nähe-Druck verwenden, nicht als Fakt."
    )

    current_angle = str(
        getattr(
            plan,
            "emotional_angle",
            "",
        )
        or ""
    ).strip()

    if social_angle not in current_angle:
        plan.emotional_angle = (
            (
                current_angle
                + " | "
                + social_angle
            )
            if current_angle
            else social_angle
        )

    return state


def social_state_stats() -> dict:
    with _LOCK:
        data = _load()

    users = data.get(
        "users",
        {},
    )

    return {
        "version": SOCIAL_EMOTIONAL_STATE_VERSION,
        "users": len(
            users
        ),
        "path": str(
            SOCIAL_STATE_PATH
        ),
    }


def format_social_state_debug(
    result=None,
) -> str:
    if not result:
        stats = social_state_stats()

        return (
            "[SOCIAL EMOTIONAL STATE] "
            f"v={SOCIAL_EMOTIONAL_STATE_VERSION} "
            f"users={stats['users']}"
        )

    state = (
        result.get(
            "state"
        )
        or {}
    )

    return (
        "[SOCIAL EMOTIONAL STATE] "
        f"v={SOCIAL_EMOTIONAL_STATE_VERSION} "
        f"user={result.get('user_id')} "
        f"saved={result.get('saved')} "
        f"signals={result.get('signals', [])} "
        f"warmth={float(state.get('warmth', 0.0) or 0.0):.2f} "
        f"rivalry={float(state.get('rivalry', 0.0) or 0.0):.2f} "
        f"irritation={float(state.get('irritation', 0.0) or 0.0):.2f} "
        f"engagement={float(state.get('engagement', 0.0) or 0.0):.2f}"
    )


def _self_test() -> int:
    global SOCIAL_STATE_PATH

    import tempfile

    original_path = SOCIAL_STATE_PATH
    tests = []

    try:
        with tempfile.TemporaryDirectory() as tmp:
            SOCIAL_STATE_PATH = (
                Path(tmp)
                /
                "social.json"
            )

            first = observe_social_interaction(
                user_id="1",
                username="Test",
                user_text="evil ich hab dich lieb sis",
                direct=True,
                event_id="m1",
                now=1000.0,
            )

            state = first[
                "state"
            ]

            tests.append(
                (
                    "affection builds warmth",
                    state["warmth"] > 0.10,
                )
            )

            tests.append(
                (
                    "affection builds closeness slowly",
                    0.0
                    <
                    state["closeness"]
                    <= 0.07,
                )
            )

            duplicate = observe_social_interaction(
                user_id="1",
                username="Test",
                user_text="evil ich hab dich lieb sis",
                direct=True,
                event_id="m1",
                now=1001.0,
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

            rivalry = observe_social_interaction(
                user_id="2",
                username="Rival",
                user_text="skill issue xd, ich bin besser",
                direct=True,
                event_id="m2",
                now=1000.0,
            )["state"]

            tests.append(
                (
                    "playful rivalry",
                    rivalry["rivalry"]
                    >
                    rivalry["irritation"],
                )
            )

            hostile = observe_social_interaction(
                user_id="3",
                username="Hostile",
                user_text="du bist nervig",
                direct=True,
                event_id="m3",
                now=1000.0,
            )["state"]

            tests.append(
                (
                    "hostility bounded",
                    0.0
                    <
                    hostile["irritation"]
                    <= 0.12,
                )
            )

            care = observe_social_interaction(
                user_id="4",
                username="Care",
                user_text="ich hab Kopfschmerzen, sei bitte leiser",
                direct=True,
                event_id="m4",
                now=1000.0,
            )["state"]

            tests.append(
                (
                    "care does not create irritation",
                    care["irritation"]
                    ==
                    0.0,
                )
            )

            old = dict(
                state
            )

            decayed = decay_state(
                old,
                now=(
                    1000.0
                    +
                    24 * 60 * 60
                ),
            )

            tests.append(
                (
                    "warmth decays",
                    decayed["warmth"]
                    <
                    old["warmth"],
                )
            )

            tests.append(
                (
                    "closeness decays slower",
                    (
                        decayed["closeness"]
                        /
                        max(
                            old["closeness"],
                            0.0001,
                        )
                    )
                    >
                    (
                        decayed["warmth"]
                        /
                        max(
                            old["warmth"],
                            0.0001,
                        )
                    ),
                )
            )

            raw = json.loads(
                SOCIAL_STATE_PATH.read_text(
                    encoding="utf-8"
                )
            )

            serialized = json.dumps(
                raw,
                ensure_ascii=False,
            )

            tests.append(
                (
                    "no raw sensitive text persisted",
                    "Kopfschmerzen"
                    not in serialized
                    and "skill issue"
                    not in serialized,
                )
            )

            prompt = format_social_state_for_prompt(
                "1"
            )

            tests.append(
                (
                    "prompt has no numeric scores",
                    not re.search(
                        r"\b0\.\d+\b",
                        prompt,
                    ),
                )
            )

    finally:
        SOCIAL_STATE_PATH = original_path

    passed = sum(
        1
        for _, success in tests
        if success
    )

    print()
    print("=" * 62)
    print(
        f"SOCIAL EMOTIONAL STATE "
        f"v{SOCIAL_EMOTIONAL_STATE_VERSION} TEST"
    )
    print("=" * 62)

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

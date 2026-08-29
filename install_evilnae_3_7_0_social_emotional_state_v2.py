from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent

BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
SOCIAL_PATH = PROJECT_ROOT / "social_emotional_state.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.6.2-context-semantic"'
TARGET_BOT = 'BOT_VERSION = "3.7.0-social-emotional-state"'

EXPECTED_LIVE = 'LIVE_STABILITY_VERSION = "1.0"'
TARGET_LIVE = 'LIVE_STABILITY_VERSION = "1.1-social-state"'

SOCIAL_SOURCE = 'from __future__ import annotations\n\nimport json\nimport math\nimport re\nimport threading\nimport time\nfrom pathlib import Path\n\n\nSOCIAL_EMOTIONAL_STATE_VERSION = "1.0"\nSOCIAL_STATE_PATH = Path("evilnae_social_emotional_state.json")\n\n_LOCK = threading.RLock()\n\nDIMENSIONS = (\n    "closeness",\n    "trust",\n    "warmth",\n    "rivalry",\n    "irritation",\n    "engagement",\n)\n\nHALF_LIFE_SECONDS = {\n    "closeness": 14 * 24 * 60 * 60,\n    "trust": 21 * 24 * 60 * 60,\n    "warmth": 12 * 60 * 60,\n    "rivalry": 36 * 60 * 60,\n    "irritation": 6 * 60 * 60,\n    "engagement": 3 * 60 * 60,\n}\n\nMAX_EVENT_HISTORY = 16\n\nPOSITIVE_PATTERN = re.compile(\n    r"\\b(?:danke|dankeschön|dankeschoen|lieb\\s+von\\s+dir|"\n    r"gut\\s+gemacht|stolz\\s+auf\\s+dich|supporte\\s+dich|"\n    r"du\\s+bist\\s+(?:cool|lustig|witzig|süß|suess|lieb))\\b",\n    re.I,\n)\n\nAFFECTION_PATTERN = re.compile(\n    r"\\b(?:hab\\s+dich\\s+lieb|ich\\s+mag\\s+dich|"\n    r"liebe\\s+dich|love\\s+you|luv\\s+u|"\n    r"meine\\s+sis|sis\\b)\\b",\n    re.I,\n)\n\nAPOLOGY_PATTERN = re.compile(\n    r"\\b(?:sorry|tut\\s+mir\\s+leid|entschuldige|"\n    r"war\\s+nicht\\s+so\\s+gemeint)\\b",\n    re.I,\n)\n\nTRUST_PATTERN = re.compile(\n    r"\\b(?:ich\\s+vertrau(?:e)?\\s+dir|"\n    r"kann\\s+ich\\s+dir\\s+was\\s+sagen|"\n    r"ich\\s+muss\\s+dir\\s+was\\s+erzählen|"\n    r"ich\\s+muss\\s+dir\\s+was\\s+erzaehlen)\\b",\n    re.I,\n)\n\nVULNERABLE_PATTERN = re.compile(\n    r"\\b(?:ich\\s+hab(?:e)?\\s+angst|"\n    r"ich\\s+bin\\s+traurig|"\n    r"mir\\s+geht(?:\'|’)?s\\s+nicht\\s+gut|"\n    r"ich\\s+bin\\s+überfordert|ich\\s+bin\\s+ueberfordert|"\n    r"ich\\s+fühl(?:e)?\\s+mich|ich\\s+fuehl(?:e)?\\s+mich)\\b",\n    re.I,\n)\n\nPLAYFUL_RIVALRY_PATTERN = re.compile(\n    r"\\b(?:skill\\s+issue|ich\\s+bin\\s+besser|"\n    r"du\\s+verlierst|du\\s+packst\\s+das\\s+nicht|"\n    r"1v1|fight\\s+me|komm\\s+doch|"\n    r"nö+|noe+|cope|seethe|l\\s+take|"\n    r"verrat|verräter|verraeter)\\b",\n    re.I,\n)\n\nHOSTILITY_PATTERN = re.compile(\n    r"\\b(?:halt\\s+die\\s+klappe|"\n    r"du\\s+bist\\s+(?:dumm|scheiße|scheisse|nervig|"\n    r"bescheuert|idiotisch)|"\n    r"ich\\s+hasse\\s+dich|"\n    r"verpiss\\s+dich|fick\\s+dich)\\b",\n    re.I,\n)\n\nLAUGHTER_PATTERN = re.compile(\n    r"(?:\\b(?:xd+|lol+|lmao|haha+|hehe+)\\b|😂|🤣)",\n    re.I,\n)\n\nCARE_SENSITIVE_PATTERN = re.compile(\n    r"\\b(?:kopfschmerz|migräne|migraene|schmerzen|"\n    r"krank|fieber|mir\\s+geht(?:\'|’)?s\\s+nicht\\s+gut|"\n    r"bitte\\s+leiser|kümmer(?:e)?\\s+dich|kuemmer(?:e)?\\s+dich)\\b",\n    re.I,\n)\n\n\ndef _clamp(value: float) -> float:\n    return max(\n        0.0,\n        min(\n            1.0,\n            float(value),\n        ),\n    )\n\n\ndef _empty_state(\n    user_id: str,\n    username: str = "",\n    now: float | None = None,\n) -> dict:\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    return {\n        "user_id": str(user_id),\n        "username": str(username or ""),\n        "closeness": 0.0,\n        "trust": 0.0,\n        "warmth": 0.0,\n        "rivalry": 0.0,\n        "irritation": 0.0,\n        "engagement": 0.0,\n        "updated_at": now,\n        "last_interaction_at": 0.0,\n        "last_event_id": "",\n        "events": [],\n    }\n\n\ndef _normalize_state(\n    state: dict,\n    *,\n    user_id: str,\n    username: str = "",\n    now: float | None = None,\n) -> dict:\n    if not isinstance(\n        state,\n        dict,\n    ):\n        state = {}\n\n    result = _empty_state(\n        user_id,\n        username,\n        now,\n    )\n\n    result.update(\n        {\n            key: state.get(\n                key,\n                result[key],\n            )\n            for key in result\n        }\n    )\n\n    result["user_id"] = str(user_id)\n\n    if username:\n        result["username"] = str(\n            username\n        )\n\n    for name in DIMENSIONS:\n        try:\n            result[name] = _clamp(\n                float(\n                    result.get(\n                        name,\n                        0.0,\n                    )\n                    or 0.0\n                )\n            )\n        except Exception:\n            result[name] = 0.0\n\n    try:\n        result["updated_at"] = float(\n            result.get(\n                "updated_at",\n                0.0,\n            )\n            or 0.0\n        )\n    except Exception:\n        result["updated_at"] = 0.0\n\n    try:\n        result["last_interaction_at"] = float(\n            result.get(\n                "last_interaction_at",\n                0.0,\n            )\n            or 0.0\n        )\n    except Exception:\n        result["last_interaction_at"] = 0.0\n\n    result["last_event_id"] = str(\n        result.get(\n            "last_event_id",\n            "",\n        )\n        or ""\n    )\n\n    events = result.get(\n        "events",\n        [],\n    )\n\n    if not isinstance(\n        events,\n        list,\n    ):\n        events = []\n\n    result["events"] = [\n        str(event)[:80]\n        for event in events[-MAX_EVENT_HISTORY:]\n        if str(event).strip()\n    ]\n\n    return result\n\n\ndef _load() -> dict:\n    if not SOCIAL_STATE_PATH.exists():\n        return {\n            "version": SOCIAL_EMOTIONAL_STATE_VERSION,\n            "users": {},\n        }\n\n    try:\n        data = json.loads(\n            SOCIAL_STATE_PATH.read_text(\n                encoding="utf-8"\n            )\n        )\n    except Exception:\n        return {\n            "version": SOCIAL_EMOTIONAL_STATE_VERSION,\n            "users": {},\n        }\n\n    if not isinstance(\n        data,\n        dict,\n    ):\n        data = {}\n\n    users = data.get(\n        "users",\n        {},\n    )\n\n    if not isinstance(\n        users,\n        dict,\n    ):\n        users = {}\n\n    return {\n        "version": SOCIAL_EMOTIONAL_STATE_VERSION,\n        "users": users,\n    }\n\n\ndef _save(data: dict) -> None:\n    temp = Path(\n        str(SOCIAL_STATE_PATH)\n        + ".tmp"\n    )\n\n    temp.write_text(\n        json.dumps(\n            data,\n            ensure_ascii=False,\n            indent=2,\n        ),\n        encoding="utf-8",\n    )\n\n    temp.replace(\n        SOCIAL_STATE_PATH\n    )\n\n\ndef _decay_factor(\n    elapsed: float,\n    half_life: float,\n) -> float:\n    if elapsed <= 0:\n        return 1.0\n\n    if half_life <= 0:\n        return 0.0\n\n    return math.pow(\n        0.5,\n        elapsed / half_life,\n    )\n\n\ndef decay_state(\n    state: dict,\n    *,\n    now: float | None = None,\n) -> dict:\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    result = dict(\n        state\n    )\n\n    try:\n        updated_at = float(\n            result.get(\n                "updated_at",\n                now,\n            )\n            or now\n        )\n    except Exception:\n        updated_at = now\n\n    elapsed = max(\n        0.0,\n        now - updated_at,\n    )\n\n    for name in DIMENSIONS:\n        current = _clamp(\n            float(\n                result.get(\n                    name,\n                    0.0,\n                )\n                or 0.0\n            )\n        )\n\n        factor = _decay_factor(\n            elapsed,\n            HALF_LIFE_SECONDS[\n                name\n            ],\n        )\n\n        result[name] = round(\n            _clamp(\n                current\n                * factor\n            ),\n            4,\n        )\n\n    result["updated_at"] = now\n\n    return result\n\n\ndef _apply_delta(\n    state: dict,\n    name: str,\n    amount: float,\n) -> None:\n    state[name] = round(\n        _clamp(\n            float(\n                state.get(\n                    name,\n                    0.0,\n                )\n                or 0.0\n            )\n            +\n            float(amount)\n        ),\n        4,\n    )\n\n\ndef _signal_deltas(\n    *,\n    user_text: str,\n    direct: bool,\n    replied_to_bot: bool,\n    name_mentioned: bool,\n) -> tuple[dict, list[str]]:\n    text = str(\n        user_text\n        or ""\n    )\n\n    deltas = {\n        name: 0.0\n        for name in DIMENSIONS\n    }\n\n    signals = []\n\n    if direct:\n        deltas["engagement"] += 0.09\n        signals.append(\n            "direct_engagement"\n        )\n\n    elif replied_to_bot:\n        deltas["engagement"] += 0.08\n        signals.append(\n            "reply_engagement"\n        )\n\n    elif name_mentioned:\n        deltas["engagement"] += 0.04\n        signals.append(\n            "mention_engagement"\n        )\n\n    if POSITIVE_PATTERN.search(\n        text\n    ):\n        deltas["warmth"] += 0.10\n        deltas["closeness"] += 0.025\n        deltas["trust"] += 0.015\n        signals.append(\n            "positive"\n        )\n\n    if AFFECTION_PATTERN.search(\n        text\n    ):\n        deltas["warmth"] += 0.16\n        deltas["closeness"] += 0.055\n        deltas["trust"] += 0.025\n        signals.append(\n            "affection"\n        )\n\n    if APOLOGY_PATTERN.search(\n        text\n    ):\n        deltas["warmth"] += 0.08\n        deltas["trust"] += 0.035\n        deltas["irritation"] -= 0.12\n        signals.append(\n            "apology"\n        )\n\n    if TRUST_PATTERN.search(\n        text\n    ):\n        deltas["trust"] += 0.075\n        deltas["closeness"] += 0.025\n        deltas["warmth"] += 0.035\n        signals.append(\n            "trust"\n        )\n\n    if VULNERABLE_PATTERN.search(\n        text\n    ):\n        # Only the signal label is stored.\n        # The sensitive message itself is never persisted here.\n        deltas["trust"] += 0.045\n        deltas["closeness"] += 0.015\n        deltas["warmth"] += 0.035\n        signals.append(\n            "vulnerability"\n        )\n\n    playful = bool(\n        PLAYFUL_RIVALRY_PATTERN.search(\n            text\n        )\n    )\n\n    laughter = bool(\n        LAUGHTER_PATTERN.search(\n            text\n        )\n    )\n\n    hostile = bool(\n        HOSTILITY_PATTERN.search(\n            text\n        )\n    )\n\n    if playful:\n        deltas["rivalry"] += 0.11\n        deltas["engagement"] += 0.04\n        signals.append(\n            "playful_rivalry"\n        )\n\n    if hostile:\n        if laughter:\n            deltas["rivalry"] += 0.08\n            deltas["irritation"] += 0.015\n            signals.append(\n                "teasing_hostility"\n            )\n\n        else:\n            deltas["irritation"] += 0.10\n            deltas["warmth"] -= 0.04\n            signals.append(\n                "hostility"\n            )\n\n    if CARE_SENSITIVE_PATTERN.search(\n        text\n    ):\n        # Serious/boundary messages must not make Evilnae annoyed\n        # simply because someone asks for consideration.\n        deltas["irritation"] = min(\n            deltas["irritation"],\n            0.0,\n        )\n        signals.append(\n            "care_context"\n        )\n\n    caps = {\n        "closeness": 0.07,\n        "trust": 0.09,\n        "warmth": 0.20,\n        "rivalry": 0.15,\n        "irritation": 0.12,\n        "engagement": 0.14,\n    }\n\n    for name in DIMENSIONS:\n        cap = caps[\n            name\n        ]\n\n        deltas[name] = max(\n            -cap,\n            min(\n                cap,\n                deltas[name],\n            ),\n        )\n\n    return deltas, signals\n\n\ndef observe_social_interaction(\n    *,\n    user_id,\n    username="",\n    user_text="",\n    direct=False,\n    replied_to_bot=False,\n    name_mentioned=False,\n    event_id="",\n    now: float | None = None,\n) -> dict:\n    user_id = str(\n        user_id\n        or ""\n    ).strip()\n\n    if not user_id:\n        return {\n            "saved": False,\n            "reason": "missing_user_id",\n            "user_id": "",\n            "signals": [],\n            "state": None,\n        }\n\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    event_id = str(\n        event_id\n        or ""\n    )\n\n    with _LOCK:\n        data = _load()\n        users = data[\n            "users"\n        ]\n\n        current = _normalize_state(\n            users.get(\n                user_id,\n                {},\n            ),\n            user_id=user_id,\n            username=username,\n            now=now,\n        )\n\n        current = decay_state(\n            current,\n            now=now,\n        )\n\n        if (\n            event_id\n            and current.get(\n                "last_event_id"\n            )\n            ==\n            event_id\n        ):\n            return {\n                "saved": False,\n                "reason": "duplicate_event",\n                "user_id": user_id,\n                "signals": [],\n                "state": current,\n            }\n\n        deltas, signals = _signal_deltas(\n            user_text=user_text,\n            direct=bool(direct),\n            replied_to_bot=bool(\n                replied_to_bot\n            ),\n            name_mentioned=bool(\n                name_mentioned\n            ),\n        )\n\n        for name in DIMENSIONS:\n            _apply_delta(\n                current,\n                name,\n                deltas[\n                    name\n                ],\n            )\n\n        current["username"] = str(\n            username\n            or current.get(\n                "username",\n                "",\n            )\n        )\n\n        current[\n            "last_interaction_at"\n        ] = now\n\n        current[\n            "updated_at"\n        ] = now\n\n        if event_id:\n            current[\n                "last_event_id"\n            ] = event_id\n\n        if signals:\n            current[\n                "events"\n            ] = (\n                list(\n                    current.get(\n                        "events",\n                        [],\n                    )\n                )\n                +\n                signals\n            )[-MAX_EVENT_HISTORY:]\n\n        users[\n            user_id\n        ] = current\n\n        data[\n            "version"\n        ] = (\n            SOCIAL_EMOTIONAL_STATE_VERSION\n        )\n\n        _save(\n            data\n        )\n\n    return {\n        "saved": True,\n        "reason": "observed",\n        "user_id": user_id,\n        "signals": signals,\n        "deltas": deltas,\n        "state": current,\n    }\n\n\ndef get_social_state(\n    user_id,\n    *,\n    username="",\n    now: float | None = None,\n    persist_decay=True,\n) -> dict:\n    user_id = str(\n        user_id\n        or ""\n    ).strip()\n\n    if not user_id:\n        return _empty_state(\n            "",\n            username,\n            now,\n        )\n\n    now = float(\n        now\n        if now is not None\n        else time.time()\n    )\n\n    with _LOCK:\n        data = _load()\n        users = data[\n            "users"\n        ]\n\n        current = _normalize_state(\n            users.get(\n                user_id,\n                {},\n            ),\n            user_id=user_id,\n            username=username,\n            now=now,\n        )\n\n        decayed = decay_state(\n            current,\n            now=now,\n        )\n\n        if persist_decay:\n            users[\n                user_id\n            ] = decayed\n            data[\n                "version"\n            ] = (\n                SOCIAL_EMOTIONAL_STATE_VERSION\n            )\n            _save(\n                data\n            )\n\n    return decayed\n\n\ndef _band(\n    value: float,\n) -> str:\n    value = float(\n        value\n    )\n\n    if value >= 0.72:\n        return "high"\n\n    if value >= 0.42:\n        return "medium"\n\n    if value >= 0.16:\n        return "low"\n\n    return "neutral"\n\n\ndef format_social_state_for_prompt(\n    user_id,\n    *,\n    username="",\n) -> str:\n    state = get_social_state(\n        user_id,\n        username=username,\n    )\n\n    return "\\n".join(\n        [\n            (\n                "[SOCIAL EMOTIONAL STATE "\n                f"v{SOCIAL_EMOTIONAL_STATE_VERSION}]"\n            ),\n            (\n                "Temporärer, abklingender sozialer Zustand "\n                "gegenüber genau diesem User."\n            ),\n            (\n                "Er beeinflusst Ton/Nähe/Banter, ist aber KEIN "\n                "Faktenbeweis und KEINE dauerhafte Beziehung."\n            ),\n            (\n                f"- closeness: "\n                f"{_band(state[\'closeness\'])}"\n            ),\n            (\n                f"- trust: "\n                f"{_band(state[\'trust\'])}"\n            ),\n            (\n                f"- warmth: "\n                f"{_band(state[\'warmth\'])}"\n            ),\n            (\n                f"- rivalry: "\n                f"{_band(state[\'rivalry\'])}"\n            ),\n            (\n                f"- irritation: "\n                f"{_band(state[\'irritation\'])}"\n            ),\n            (\n                f"- engagement: "\n                f"{_band(state[\'engagement\'])}"\n            ),\n            (\n                "HARD RULES: keine Scores erwähnen; keine "\n                "Beziehungsfakten daraus erfinden; Serious/Care "\n                "Context schlägt Rivalry/Irritation; hohe Irritation "\n                "allein darf Evilnae nicht plötzlich dauerhaft "\n                "schlecht gelaunt machen."\n            ),\n        ]\n    )\n\n\ndef apply_social_state_to_plan(\n    plan,\n    *,\n    user_id,\n    user_text="",\n    is_hanae=False,\n):\n    state = get_social_state(\n        user_id\n    )\n\n    sensitive = bool(\n        CARE_SENSITIVE_PATTERN.search(\n            str(\n                user_text\n                or ""\n            )\n        )\n    )\n\n    warmth = float(\n        state.get(\n            "warmth",\n            0.0,\n        )\n        or 0.0\n    )\n\n    closeness = float(\n        state.get(\n            "closeness",\n            0.0,\n        )\n        or 0.0\n    )\n\n    trust = float(\n        state.get(\n            "trust",\n            0.0,\n        )\n        or 0.0\n    )\n\n    rivalry = float(\n        state.get(\n            "rivalry",\n            0.0,\n        )\n        or 0.0\n    )\n\n    irritation = float(\n        state.get(\n            "irritation",\n            0.0,\n        )\n        or 0.0\n    )\n\n    engagement = float(\n        state.get(\n            "engagement",\n            0.0,\n        )\n        or 0.0\n    )\n\n    social_warmth_floor = min(\n        0.62,\n        0.18\n        + warmth * 0.42\n        + closeness * 0.22\n        + trust * 0.12,\n    )\n\n    if not sensitive:\n        plan.warmth_intensity = max(\n            float(\n                getattr(\n                    plan,\n                    "warmth_intensity",\n                    0.0,\n                )\n                or 0.0\n            ),\n            social_warmth_floor,\n        )\n\n    rivalry_effect = rivalry\n\n    if is_hanae:\n        rivalry_effect = max(\n            rivalry_effect,\n            0.22,\n        )\n\n    if (\n        not sensitive\n        and rivalry_effect >= 0.34\n        and irritation < 0.65\n    ):\n        plan.banter_intensity = max(\n            float(\n                getattr(\n                    plan,\n                    "banter_intensity",\n                    0.0,\n                )\n                or 0.0\n            ),\n            min(\n                0.72,\n                0.32\n                + rivalry_effect * 0.48,\n            ),\n        )\n\n        if getattr(\n            plan,\n            "stance",\n            "",\n        ) in {\n            "neutral",\n            "dry",\n        }:\n            plan.stance = (\n                "smug"\n                if rivalry_effect >= 0.58\n                else "playful"\n            )\n\n    # Important: relational irritation is NOT global mood authority.\n    if (\n        not sensitive\n        and irritation >= 0.48\n    ):\n        plan.warmth_intensity = max(\n            0.16,\n            min(\n                float(\n                    getattr(\n                        plan,\n                        "warmth_intensity",\n                        0.3,\n                    )\n                    or 0.3\n                ),\n                0.42,\n            ),\n        )\n\n        existing = list(\n            getattr(\n                plan,\n                "must_avoid",\n                [],\n            )\n            or []\n        )\n\n        for item in (\n            "Irritation als globale schlechte Laune darstellen",\n            "User wegen alter Irritation grundlos anfahren",\n            "grausam/beleidigend statt spielerisch-firm reagieren",\n        ):\n            if item not in existing:\n                existing.append(\n                    item\n                )\n\n        plan.must_avoid = existing[\n            :16\n        ]\n\n    social_angle = (\n        "Temporärer Social State: "\n        f"closeness={_band(closeness)}, "\n        f"trust={_band(trust)}, "\n        f"warmth={_band(warmth)}, "\n        f"rivalry={_band(rivalry_effect)}, "\n        f"irritation={_band(irritation)}, "\n        f"engagement={_band(engagement)}. "\n        "Nur als Ton-/Nähe-Druck verwenden, nicht als Fakt."\n    )\n\n    current_angle = str(\n        getattr(\n            plan,\n            "emotional_angle",\n            "",\n        )\n        or ""\n    ).strip()\n\n    if social_angle not in current_angle:\n        plan.emotional_angle = (\n            (\n                current_angle\n                + " | "\n                + social_angle\n            )\n            if current_angle\n            else social_angle\n        )\n\n    return state\n\n\ndef social_state_stats() -> dict:\n    with _LOCK:\n        data = _load()\n\n    users = data.get(\n        "users",\n        {},\n    )\n\n    return {\n        "version": SOCIAL_EMOTIONAL_STATE_VERSION,\n        "users": len(\n            users\n        ),\n        "path": str(\n            SOCIAL_STATE_PATH\n        ),\n    }\n\n\ndef format_social_state_debug(\n    result=None,\n) -> str:\n    if not result:\n        stats = social_state_stats()\n\n        return (\n            "[SOCIAL EMOTIONAL STATE] "\n            f"v={SOCIAL_EMOTIONAL_STATE_VERSION} "\n            f"users={stats[\'users\']}"\n        )\n\n    state = (\n        result.get(\n            "state"\n        )\n        or {}\n    )\n\n    return (\n        "[SOCIAL EMOTIONAL STATE] "\n        f"v={SOCIAL_EMOTIONAL_STATE_VERSION} "\n        f"user={result.get(\'user_id\')} "\n        f"saved={result.get(\'saved\')} "\n        f"signals={result.get(\'signals\', [])} "\n        f"warmth={float(state.get(\'warmth\', 0.0) or 0.0):.2f} "\n        f"rivalry={float(state.get(\'rivalry\', 0.0) or 0.0):.2f} "\n        f"irritation={float(state.get(\'irritation\', 0.0) or 0.0):.2f} "\n        f"engagement={float(state.get(\'engagement\', 0.0) or 0.0):.2f}"\n    )\n\n\ndef _self_test() -> int:\n    global SOCIAL_STATE_PATH\n\n    import tempfile\n\n    original_path = SOCIAL_STATE_PATH\n    tests = []\n\n    try:\n        with tempfile.TemporaryDirectory() as tmp:\n            SOCIAL_STATE_PATH = (\n                Path(tmp)\n                /\n                "social.json"\n            )\n\n            first = observe_social_interaction(\n                user_id="1",\n                username="Test",\n                user_text="evil ich hab dich lieb sis",\n                direct=True,\n                event_id="m1",\n                now=1000.0,\n            )\n\n            state = first[\n                "state"\n            ]\n\n            tests.append(\n                (\n                    "affection builds warmth",\n                    state["warmth"] > 0.10,\n                )\n            )\n\n            tests.append(\n                (\n                    "affection builds closeness slowly",\n                    0.0\n                    <\n                    state["closeness"]\n                    <= 0.07,\n                )\n            )\n\n            duplicate = observe_social_interaction(\n                user_id="1",\n                username="Test",\n                user_text="evil ich hab dich lieb sis",\n                direct=True,\n                event_id="m1",\n                now=1001.0,\n            )\n\n            tests.append(\n                (\n                    "message dedupe",\n                    duplicate[\n                        "reason"\n                    ]\n                    ==\n                    "duplicate_event",\n                )\n            )\n\n            rivalry = observe_social_interaction(\n                user_id="2",\n                username="Rival",\n                user_text="skill issue xd, ich bin besser",\n                direct=True,\n                event_id="m2",\n                now=1000.0,\n            )["state"]\n\n            tests.append(\n                (\n                    "playful rivalry",\n                    rivalry["rivalry"]\n                    >\n                    rivalry["irritation"],\n                )\n            )\n\n            hostile = observe_social_interaction(\n                user_id="3",\n                username="Hostile",\n                user_text="du bist nervig",\n                direct=True,\n                event_id="m3",\n                now=1000.0,\n            )["state"]\n\n            tests.append(\n                (\n                    "hostility bounded",\n                    0.0\n                    <\n                    hostile["irritation"]\n                    <= 0.12,\n                )\n            )\n\n            care = observe_social_interaction(\n                user_id="4",\n                username="Care",\n                user_text="ich hab Kopfschmerzen, sei bitte leiser",\n                direct=True,\n                event_id="m4",\n                now=1000.0,\n            )["state"]\n\n            tests.append(\n                (\n                    "care does not create irritation",\n                    care["irritation"]\n                    ==\n                    0.0,\n                )\n            )\n\n            old = dict(\n                state\n            )\n\n            decayed = decay_state(\n                old,\n                now=(\n                    1000.0\n                    +\n                    24 * 60 * 60\n                ),\n            )\n\n            tests.append(\n                (\n                    "warmth decays",\n                    decayed["warmth"]\n                    <\n                    old["warmth"],\n                )\n            )\n\n            tests.append(\n                (\n                    "closeness decays slower",\n                    (\n                        decayed["closeness"]\n                        /\n                        max(\n                            old["closeness"],\n                            0.0001,\n                        )\n                    )\n                    >\n                    (\n                        decayed["warmth"]\n                        /\n                        max(\n                            old["warmth"],\n                            0.0001,\n                        )\n                    ),\n                )\n            )\n\n            raw = json.loads(\n                SOCIAL_STATE_PATH.read_text(\n                    encoding="utf-8"\n                )\n            )\n\n            serialized = json.dumps(\n                raw,\n                ensure_ascii=False,\n            )\n\n            tests.append(\n                (\n                    "no raw sensitive text persisted",\n                    "Kopfschmerzen"\n                    not in serialized\n                    and "skill issue"\n                    not in serialized,\n                )\n            )\n\n            prompt = format_social_state_for_prompt(\n                "1"\n            )\n\n            tests.append(\n                (\n                    "prompt has no numeric scores",\n                    not re.search(\n                        r"\\b0\\.\\d+\\b",\n                        prompt,\n                    ),\n                )\n            )\n\n    finally:\n        SOCIAL_STATE_PATH = original_path\n\n    passed = sum(\n        1\n        for _, success in tests\n        if success\n    )\n\n    print()\n    print("=" * 62)\n    print(\n        f"SOCIAL EMOTIONAL STATE "\n        f"v{SOCIAL_EMOTIONAL_STATE_VERSION} TEST"\n    )\n    print("=" * 62)\n\n    for name, success in tests:\n        print(\n            f"[{\'PASS\' if success else \'FAIL\'}] "\n            f"{name}"\n        )\n\n    print(\n        f"RESULT: "\n        f"{passed}/{len(tests)} PASS"\n    )\n\n    return (\n        0\n        if passed == len(tests)\n        else 1\n    )\n\n\nif __name__ == "__main__":\n    raise SystemExit(\n        _self_test()\n    )\n'


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print("Nothing was overwritten by this installer.")
    raise SystemExit(1)


def replace_once(text, old, new, label):
    count = text.count(old)

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


def syntax_check(text, filename):
    try:
        ast.parse(
            text,
            filename=filename,
        )
    except SyntaxError as error:
        fail(
            f"{filename} syntax error after patch: "
            f"line {error.lineno}: {error.msg}"
        )

    ok(
        f"{filename} syntax check"
    )


print("=" * 78)
print(
    "EVILNAE 3.7.0 — SOCIAL EMOTIONAL STATE V2"
)
print("=" * 78)
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()


for required in (
    BOT_PATH,
    LIVE_PATH,
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


if (
    TARGET_BOT in bot
    and SOCIAL_PATH.exists()
):
    print(
        "3.7.0 is already installed."
    )
    raise SystemExit(0)


if EXPECTED_BOT not in bot:
    fail(
        "Expected Bot 3.6.2-context-semantic"
    )


if EXPECTED_LIVE not in live:
    fail(
        "Expected Live Stability v1.0"
    )


if SOCIAL_PATH.exists():
    fail(
        "social_emotional_state.py already exists unexpectedly."
    )


ok(
    "3.6.2 live base detected"
)


# =========================================================
# BOT PATCH
# =========================================================

bot = replace_once(
    bot,
    EXPECTED_BOT,
    TARGET_BOT,
    "Bot version -> 3.7.0-social-emotional-state",
)


bot = replace_once(
    bot,
    """    CONSOLE_OUTPUT_VERSION,
    ConsoleOutputFilter,
""",
    """    CONSOLE_OUTPUT_VERSION,
    SOCIAL_EMOTIONAL_STATE_VERSION,
    social_state_stats,
    ConsoleOutputFilter,
""",
    "Bot imports Social Emotional State version/stats",
)


startup_old = """    print(
        f"Live Stability v"
        f"{LIVE_STABILITY_VERSION}: ACTIVE"
    )

    print(
        f"Compact Console v"
"""

startup_new = """    print(
        f"Live Stability v"
        f"{LIVE_STABILITY_VERSION}: ACTIVE"
    )

    social_stats = (
        social_state_stats()
    )

    print(
        f"Social Emotional State v"
        f"{SOCIAL_EMOTIONAL_STATE_VERSION}: ACTIVE "
        f"users={social_stats.get('users', 0)}"
    )

    print(
        f"Compact Console v"
"""

bot = replace_once(
    bot,
    startup_old,
    startup_new,
    "Startup Social Emotional State banner",
)


# =========================================================
# LIVE STABILITY PATCH
# =========================================================

live = replace_once(
    live,
    """from local_voice import LocalVoiceResult


LIVE_STABILITY_VERSION = "1.0"
""",
    """from local_voice import LocalVoiceResult

from social_emotional_state import (
    SOCIAL_EMOTIONAL_STATE_VERSION,
    observe_social_interaction,
    get_social_state,
    format_social_state_for_prompt,
    format_social_state_debug,
    apply_social_state_to_plan,
    social_state_stats,
)


LIVE_STABILITY_VERSION = "1.1-social-state"
""",
    "Live Stability imports Social Emotional State",
)


live = replace_once(
    live,
    """_CURRENT_USERNAME = contextvars.ContextVar(
    "evilnae_live_username",
    default="unknown",
)

_SURFACE_FAILED = contextvars.ContextVar(
""",
    """_CURRENT_USERNAME = contextvars.ContextVar(
    "evilnae_live_username",
    default="unknown",
)

_CURRENT_USER_ID = contextvars.ContextVar(
    "evilnae_live_user_id",
    default="",
)

_SURFACE_FAILED = contextvars.ContextVar(
""",
    "Per-response user-id context",
)


live = replace_once(
    live,
    """            "Emotional Salience v",
            "Qwen Surface Writer v",
""",
    """            "Emotional Salience v",
            "Social Emotional State v",
            "Qwen Surface Writer v",
""",
    "Compact console allows Social Emotional State startup",
)


live = replace_once(
    live,
    """        text = str(
            getattr(
                result,
                "text",
                "",
            )
""",
    """        user_id = str(
            getattr(
                result,
                "user_id",
                "",
            )
            or ""
        )

        text = str(
            getattr(
                result,
                "text",
                "",
            )
""",
    "Perception extracts user id",
)


live = replace_once(
    live,
    """        _CURRENT_USERNAME.set(
            username
        )

        _CURRENT_USER_TEXT.set(
            text
        )

        _SURFACE_FAILED.set(
            False
        )

        if text:
""",
    """        _CURRENT_USERNAME.set(
            username
        )

        _CURRENT_USER_ID.set(
            user_id
        )

        _CURRENT_USER_TEXT.set(
            text
        )

        _SURFACE_FAILED.set(
            False
        )

        event_id = ""

        if args:
            try:
                event_id = str(
                    getattr(
                        args[0],
                        "id",
                        "",
                    )
                    or ""
                )
            except Exception:
                event_id = ""

        social_result = (
            observe_social_interaction(
                user_id=user_id,
                username=username,
                user_text=text,
                direct=bool(
                    getattr(
                        result,
                        "direct_address",
                        False,
                    )
                ),
                replied_to_bot=bool(
                    getattr(
                        result,
                        "replied_to_bot",
                        False,
                    )
                ),
                name_mentioned=bool(
                    getattr(
                        result,
                        "name_mentioned",
                        False,
                    )
                ),
                event_id=event_id,
            )
        )

        print(
            format_social_state_debug(
                social_result
            )
        )

        if text:
""",
    "Perception observes per-user social state",
)


live = replace_once(
    live,
    """        plan.must_avoid = _merge_unique(
            getattr(
                plan,
                "must_avoid",
                [],
            ),
            additions,
        )

        return plan
""",
    """        plan.must_avoid = _merge_unique(
            getattr(
                plan,
                "must_avoid",
                [],
            ),
            additions,
        )

        social_state = (
            apply_social_state_to_plan(
                plan,
                user_id=(
                    _CURRENT_USER_ID.get()
                ),
                user_text=user_text,
                is_hanae=bool(
                    kwargs.get(
                        "is_hanae",
                        False,
                    )
                ),
            )
        )

        print(
            "[SOCIAL PLAN] "
            f"user={_CURRENT_USER_ID.get()} "
            f"warmth={float(social_state.get('warmth', 0.0) or 0.0):.2f} "
            f"rivalry={float(social_state.get('rivalry', 0.0) or 0.0):.2f} "
            f"irritation={float(social_state.get('irritation', 0.0) or 0.0):.2f}"
        )

        return plan
""",
    "Response Planner receives temporary social state",
)


live = replace_once(
    live,
    """        return await original(
            *args,
            **kwargs,
        )

    return wrapped


def wrap_reference_context(
""",
    """        user_id = str(
            kwargs.get(
                "user_id",
                "",
            )
            or _CURRENT_USER_ID.get()
            or ""
        )

        if user_id:
            kwargs = dict(
                kwargs
            )

            relationship_text = str(
                kwargs.get(
                    "relationship_text",
                    "",
                )
                or ""
            ).strip()

            social_context = (
                format_social_state_for_prompt(
                    user_id,
                    username=(
                        _CURRENT_USERNAME.get()
                    ),
                )
            )

            kwargs[
                "relationship_text"
            ] = (
                relationship_text
                + "\\n\\n"
                + social_context
            ).strip()

        return await original(
            *args,
            **kwargs,
        )

    return wrapped


def wrap_reference_context(
""",
    "Participation receives temporary social context",
)


# =========================================================
# CONTRACT / SYNTAX
# =========================================================

for marker in (
    TARGET_BOT,
    "SOCIAL_EMOTIONAL_STATE_VERSION",
    "social_state_stats",
    "Social Emotional State v",
):
    if marker not in bot:
        fail(
            f"Patched bot.py missing invariant: {marker}"
        )


for marker in (
    TARGET_LIVE,
    "observe_social_interaction",
    "apply_social_state_to_plan",
    "format_social_state_for_prompt",
    "_CURRENT_USER_ID",
    "Social Emotional State v",
):
    if marker not in live:
        fail(
            f"Patched live_stability.py missing invariant: {marker}"
        )


for marker in (
    'SOCIAL_EMOTIONAL_STATE_VERSION = "1.0"',
    "HALF_LIFE_SECONDS",
    "observe_social_interaction",
    "apply_social_state_to_plan",
    "no raw sensitive text persisted",
):
    if marker not in SOCIAL_SOURCE:
        fail(
            f"social_emotional_state.py missing invariant: {marker}"
        )


syntax_check(
    SOCIAL_SOURCE,
    "social_emotional_state.py",
)

syntax_check(
    live,
    "live_stability.py",
)

syntax_check(
    bot,
    "bot.py",
)


contract_tests = {
    "no OpenAI call":
        "OpenAI" not in SOCIAL_SOURCE,

    "no Ollama call":
        "run_local_model" not in SOCIAL_SOURCE,

    "separate state file":
        "evilnae_social_emotional_state.json"
        in SOCIAL_SOURCE,

    "six social dimensions":
        all(
            name in SOCIAL_SOURCE
            for name in (
                "closeness",
                "trust",
                "warmth",
                "rivalry",
                "irritation",
                "engagement",
            )
        ),

    "decay enabled":
        "HALF_LIFE_SECONDS"
        in SOCIAL_SOURCE
        and "decay_state"
        in SOCIAL_SOURCE,

    "message dedupe":
        "duplicate_event"
        in SOCIAL_SOURCE,

    "sensitive text not persisted":
        "Only the signal label is stored"
        in SOCIAL_SOURCE,

    "care overrides irritation":
        "care_context"
        in SOCIAL_SOURCE,

    "old pissed-loop protected":
        "relational irritation is NOT global mood authority"
        in SOCIAL_SOURCE,

    "planner integration":
        "apply_social_state_to_plan"
        in live,

    "participation integration":
        "format_social_state_for_prompt"
        in live,

    "compact startup integration":
        "Social Emotional State v"
        in bot
        and "Social Emotional State v"
        in live,
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
        + ", ".join(failed)
    )


ok(
    f"Contract self-test: "
    f"{len(contract_tests)}/"
    f"{len(contract_tests)} PASS"
)


# =========================================================
# PRE-WRITE SOCIAL BEHAVIOR TEST
# =========================================================

namespace = {
    "__name__": "_evilnae_social_preflight_",
}


exec(
    compile(
        SOCIAL_SOURCE,
        "social_emotional_state.py",
        "exec",
    ),
    namespace,
)


if namespace[
    "_self_test"
]() != 0:
    fail(
        "Social Emotional State behavior self-test failed"
    )


ok(
    "Social Emotional State behavior self-test: PASS"
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
        + ".tmp"
    )

    temp.write_text(
        text,
        encoding="utf-8",
    )

    temp.replace(
        path
    )


atomic_write(
    SOCIAL_PATH,
    SOCIAL_SOURCE,
)

ok(
    "Created: social_emotional_state.py"
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
# COMPILE + MODULE SELF TEST
# =========================================================

compile_targets = [
    SOCIAL_PATH,
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
            for path in compile_targets
        ],
    ],
    cwd=str(PROJECT_ROOT),
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
    "Post-install py_compile: 3/3"
)


result = subprocess.run(
    [
        sys.executable,
        str(
            SOCIAL_PATH
        ),
    ],
    cwd=str(PROJECT_ROOT),
    check=False,
)


if result.returncode != 0:
    print()
    print(
        "[POST-INSTALL WARNING] "
        "social_emotional_state.py self-test failed."
    )
    print(
        f"Backup: {backup_dir}"
    )
    raise SystemExit(
        result.returncode
    )


ok(
    "Post-install Social Emotional State self-test: PASS"
)


print()
print("=" * 78)
print(
    "EVILNAE 3.7.0 SOCIAL EMOTIONAL STATE INSTALLED"
)
print("=" * 78)

print()
print("Architecture:")
print(
    "  [✓] per-user temporary social state"
)
print(
    "  [✓] closeness"
)
print(
    "  [✓] trust"
)
print(
    "  [✓] warmth"
)
print(
    "  [✓] playful rivalry"
)
print(
    "  [✓] relational irritation"
)
print(
    "  [✓] engagement"
)
print(
    "  [✓] independent decay per dimension"
)
print(
    "  [✓] per-message bounded changes"
)
print(
    "  [✓] Discord-message dedupe"
)
print(
    "  [✓] no raw sensitive message stored"
)

print()
print("Integration:")
print(
    "  [✓] Response Planner uses social tone pressure"
)
print(
    "  [✓] Participation Brain sees temporary social context"
)
print(
    "  [✓] Care/Serious Context overrides rivalry"
)
print(
    "  [✓] Irritation cannot become global bad mood authority"
)
print(
    "  [✓] Hanae sibling rivalry may have a small tonal floor"
)

print()
print("Important separation:")
print(
    "  [✓] existing DB relationship is NOT overwritten"
)
print(
    "  [✓] Character Learning is NOT written by this layer"
)
print(
    "  [✓] Social state is NOT Canon"
)
print(
    "  [✓] Social state is NOT a factual memory"
)

print()
print(
    "Runtime file: "
    "evilnae_social_emotional_state.json"
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
    "  python bot.py"
)

print()
print("Expected compact startup:")
print(
    "  Bot Version: 3.7.0-social-emotional-state"
)
print(
    "  Live Stability v1.1-social-state: ACTIVE"
)
print(
    "  Social Emotional State v1.0: ACTIVE users=..."
)

print()
print(
    "After this succeeds we can go straight to "
    "3.8.0 Experience -> Reflection -> Learning 2.0 "
    "without doing a community test first."
)

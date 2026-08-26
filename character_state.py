import json
import re
import threading
import time
from pathlib import Path

CHARACTER_STATE_VERSION = "1.0"
CHARACTER_STATE_PATH = Path("evilnae_character_state.json")

_LOCK = threading.RLock()

TTL_SECONDS = {
    "location": 4 * 60 * 60,
    "activity": 2 * 60 * 60,
    "game": 3 * 60 * 60,
    "food": 90 * 60,
    "drink": 2 * 60 * 60,
    "music": 60 * 60,
    "outfit": 12 * 60 * 60,
    "weather": 2 * 60 * 60,
}

DANGEROUS_HEALTH_PATTERNS = [
    r"\b(?:starke|heftige)?\s*schmerzen\b",
    r"\batemnot\b",
    r"\bblut(?:e|ung|et)?\b",
    r"\bverletzt\b",
    r"\bkrank\b",
    r"\bfieber\b",
    r"\bohnmacht\b",
]

PATTERNS = [
    (
        "game",
        re.compile(r"\bich\s+(?:zocke|zock|spiele|spiel)\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})", re.IGNORECASE),
    ),
    (
        "food",
        re.compile(r"\bich\s+(?:esse|ess|futtere|snacke)\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})", re.IGNORECASE),
    ),
    (
        "drink",
        re.compile(r"\bich\s+(?:trinke|trink)\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})", re.IGNORECASE),
    ),
    (
        "music",
        re.compile(r"\bich\s+(?:höre|hoere|hör|hoer)\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})", re.IGNORECASE),
    ),
    (
        "outfit",
        re.compile(r"\bich\s+(?:trage|trag)\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})", re.IGNORECASE),
    ),
    (
        "outfit",
        re.compile(r"\bich\s+hab(?:e)?\s+(?:gerade\s+)?(?P<value>[^.!?\n]{2,90})\s+an\b", re.IGNORECASE),
    ),
    (
        "location",
        re.compile(r"\bich\s+(?:bin|sitze|sitz|liege|lieg)\s+(?:gerade\s+)?(?P<value>(?:im|in|am|auf|bei)\s+[^.!?\n]{2,90})", re.IGNORECASE),
    ),
    (
        "activity",
        re.compile(r"\bich\s+bin\s+(?:gerade\s+)?(?:am|beim)\s+(?P<value>[^.!?\n]{2,90})", re.IGNORECASE),
    ),
]


def _load() -> dict:
    if not CHARACTER_STATE_PATH.exists():
        return {"version": CHARACTER_STATE_VERSION, "states": {}}
    try:
        data = json.loads(CHARACTER_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": CHARACTER_STATE_VERSION, "states": {}}
    if not isinstance(data, dict):
        return {"version": CHARACTER_STATE_VERSION, "states": {}}
    if not isinstance(data.get("states"), dict):
        data["states"] = {}
    return data


def _save(data: dict) -> None:
    temp = Path(str(CHARACTER_STATE_PATH) + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(CHARACTER_STATE_PATH)


def _clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip(" \t\r\n,;:-–—\"'„“”")
    return value[:120]


def _has_dangerous_health_claim(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in DANGEROUS_HEALTH_PATTERNS)


def extract_character_states(answer: str) -> list[tuple[str, str]]:
    text = str(answer or "").strip()
    if not text or _has_dangerous_health_claim(text):
        return []

    found = []
    seen = set()
    for category, pattern in PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = _clean_value(match.group("value"))
        if not value or len(value) < 2:
            continue
        key = (category, value.lower())
        if key in seen:
            continue
        seen.add(key)
        found.append((category, value))
    return found


def observe_character_state(*, evilnae_answer: str) -> dict:
    observations = extract_character_states(evilnae_answer)
    result = {"saved": 0, "observations": observations}
    if not observations:
        return result

    now = time.time()
    with _LOCK:
        data = _load()
        states = data["states"]
        for category, value in observations:
            ttl = TTL_SECONDS.get(category, 60 * 60)
            states[category] = {
                "value": value,
                "source": "evilnae_sent_message",
                "created_at": now,
                "updated_at": now,
                "expires_at": now + ttl,
            }
        data["version"] = CHARACTER_STATE_VERSION
        _save(data)
    result["saved"] = len(observations)
    return result


def _active_states() -> dict:
    now = time.time()
    changed = False
    with _LOCK:
        data = _load()
        states = data.get("states", {})
        for key in list(states):
            try:
                expires_at = float(states[key].get("expires_at") or 0.0)
            except Exception:
                expires_at = 0.0
            if expires_at and expires_at < now:
                states.pop(key, None)
                changed = True
        if changed:
            _save(data)
        return dict(states)


def format_character_state_for_prompt() -> str:
    states = _active_states()
    if not states:
        return (
            "[CURRENT CHARACTER STATE]\n"
            "Kein persistenter aktueller Alltagszustand gesetzt. "
            "Erfinde keinen konkreten Ort, Essen, Drink, Game, Outfit oder Aktivität nur um eine Antwort lebendiger zu machen."
        )

    lines = [
        "[CURRENT CHARACTER STATE]",
        "Diese Zustände stammen aus Evilnaes eigenen tatsächlich gesendeten Nachrichten und gelten nur temporär.",
    ]
    for category, state in states.items():
        lines.append(f"- {category}: {state.get('value')}")
    lines.append("Wenn neuer Gesprächskontext einen Zustand ausdrücklich ändert, darf er aktualisiert werden.")
    return "\n".join(lines)


def format_character_state_debug(result: dict | None = None) -> str:
    active = _active_states()
    if result is None:
        return f"[CHARACTER STATE] v={CHARACTER_STATE_VERSION} active={list(active.keys())}"
    return (
        f"[CHARACTER STATE] v={CHARACTER_STATE_VERSION} active={list(active.keys())} "
        f"saved={result.get('saved')} observations={result.get('observations')}"
    )


def _self_test() -> int:
    tests = [
        ("game", ("game", "Elden Ring") in extract_character_states("ich zocke gerade Elden Ring")),
        ("drink", ("drink", "Cola") in extract_character_states("ich trinke Cola")),
        ("location", bool(extract_character_states("ich liege gerade im Bett"))),
        ("health blocked", extract_character_states("ich hab starke Schmerzen und liege im Bett") == []),
        ("random no state", extract_character_states("das ist komplett wild") == []),
    ]
    failed = 0
    for name, passed in tests:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        failed += 0 if passed else 1
    print(f"Character State self-test: {len(tests) - failed}/{len(tests)} PASS")
    return failed


if __name__ == "__main__":
    raise SystemExit(1 if _self_test() else 0)

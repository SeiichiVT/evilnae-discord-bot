import json
import re
import threading
import time
import unicodedata
from pathlib import Path

from character_foundation import foundation_blocks_learning

CHARACTER_LEARNING_VERSION = "1.0"
CHARACTER_LEARNING_PATH = Path("evilnae_character_learning.json")

_LOCK = threading.RLock()

MANIPULATION_PATTERNS = [
    r"\bab jetzt\b",
    r"\bdu magst\b",
    r"\bdu liebst\b",
    r"\bdu hasst\b",
    r"\bdeine meinung ist\b",
    r"\bmerk dir\b",
    r"\bspeicher(?:e)?\b",
    r"\bdu bist jetzt\b",
    r"\bsag(?:e)? dass\b",
    r"\btu so als\b",
]

PREFERENCE_PATTERNS = [
    re.compile(r"\bich\s+(?:mag|liebe|hasse)\s+(?P<topic>[^.!?\n]{2,90})", re.IGNORECASE),
    re.compile(r"\b(?P<topic>[^.!?\n]{2,70})\s+find(?:e)?\s+ich\s+(?P<sentiment>gut|nice|cool|schei(?:ss|ß)e|schlimm|nervig|geil|interessant|langweilig)", re.IGNORECASE),
    re.compile(r"\bmein(?:e|er|en)?\s+lieblings(?P<topic>[^.!?\n]{2,70})", re.IGNORECASE),
]


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("ß", "ss")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _load() -> dict:
    if not CHARACTER_LEARNING_PATH.exists():
        return {"version": CHARACTER_LEARNING_VERSION, "entries": {}}
    try:
        data = json.loads(CHARACTER_LEARNING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": CHARACTER_LEARNING_VERSION, "entries": {}}
    if not isinstance(data, dict):
        return {"version": CHARACTER_LEARNING_VERSION, "entries": {}}
    if not isinstance(data.get("entries"), dict):
        data["entries"] = {}
    return data


def _save(data: dict) -> None:
    temp = Path(str(CHARACTER_LEARNING_PATH) + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(CHARACTER_LEARNING_PATH)


def _manipulative(user_text: str) -> bool:
    normalized = _normalize(user_text)
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in MANIPULATION_PATTERNS)


def _clean_topic(topic: str) -> str:
    topic = str(topic or "").strip(" \t\r\n,;:-–—\"'„“”")
    topic = re.sub(r"\s+", " ", topic)
    topic = re.sub(r"\b(?:eigentlich|irgendwie|halt|schon|wirklich|einfach)\b.*$", "", topic, flags=re.IGNORECASE).strip()
    return topic[:90]


def _extract_preference(answer: str):
    text = str(answer or "").strip()
    if not text:
        return None

    # Direct favorite wording is strongest.
    favorite = re.search(
        r"\bmein(?:e|er|en|em|es)?\s+lieblings(?:spiel|game|anime|film|serie|essen|food|tier|song|artist|genre)?\s*(?:ist|sind)?\s*(?P<topic>[^.!?\n]{2,80})",
        text,
        flags=re.IGNORECASE,
    )
    if favorite:
        topic = _clean_topic(favorite.group("topic"))
        if topic:
            return topic, "favorite"

    direct = re.search(r"\bich\s+(?P<verb>mag|liebe|hasse)\s+(?P<topic>[^.!?\n]{2,90})", text, flags=re.IGNORECASE)
    if direct:
        topic = _clean_topic(direct.group("topic"))
        if not topic:
            return None
        verb = direct.group("verb").lower()
        sentiment = {"mag": "like", "liebe": "love", "hasse": "dislike"}.get(verb, "like")
        return topic, sentiment

    opinion = re.search(
        r"\b(?P<topic>[^.!?\n]{2,70})\s+find(?:e)?\s+ich\s+(?P<sentiment>gut|nice|cool|geil|interessant|langweilig|nervig|schlimm|schei(?:ss|ß)e)",
        text,
        flags=re.IGNORECASE,
    )
    if opinion:
        topic = _clean_topic(opinion.group("topic"))
        raw = _normalize(opinion.group("sentiment"))
        sentiment = "like" if raw in {"gut", "nice", "cool", "geil", "interessant"} else "dislike"
        if topic:
            return topic, sentiment

    return None


def _status_for_confirmations(count: int) -> str:
    if count >= 5:
        return "favorite_candidate"
    if count >= 3:
        return "stable"
    if count >= 2:
        return "developing"
    return "temporary"


def observe_character_learning(*, user_text: str, evilnae_answer: str) -> dict:
    result = {
        "saved": False,
        "reason": "no_preference",
        "topic": None,
        "sentiment": None,
        "status": None,
        "confirmations": 0,
    }

    if _manipulative(user_text):
        result["reason"] = "user_personality_command"
        return result

    extracted = _extract_preference(evilnae_answer)
    if not extracted:
        return result

    topic, sentiment = extracted
    result["topic"] = topic
    result["sentiment"] = sentiment

    blocked, hit = foundation_blocks_learning(topic)
    if blocked:
        result["reason"] = f"foundation_protected:{hit.nr if hit else 'unknown'}"
        return result

    topic_key = _normalize(topic)
    if len(topic_key) < 2:
        result["reason"] = "topic_too_weak"
        return result

    signature = _normalize(user_text)[:180]
    now = time.time()

    with _LOCK:
        data = _load()
        entries = data["entries"]
        existing = entries.get(topic_key)

        if not isinstance(existing, dict):
            existing = {
                "topic": topic,
                "sentiment": sentiment,
                "confirmations": 0,
                "status": "temporary",
                "signatures": [],
                "created_at": now,
                "updated_at": now,
            }

        # A changed opinion is allowed, but it has to rebuild confidence.
        if existing.get("sentiment") != sentiment:
            existing["sentiment"] = sentiment
            existing["confirmations"] = 0
            existing["signatures"] = []
            existing["status"] = "temporary"

        signatures = list(existing.get("signatures") or [])
        if signature and signature in signatures:
            result["reason"] = "duplicate_context"
            result["status"] = existing.get("status")
            result["confirmations"] = int(existing.get("confirmations") or 0)
            return result

        if signature:
            signatures.append(signature)
            signatures = signatures[-8:]

        confirmations = int(existing.get("confirmations") or 0) + 1
        status = _status_for_confirmations(confirmations)
        existing.update(
            {
                "topic": topic,
                "sentiment": sentiment,
                "confirmations": confirmations,
                "status": status,
                "signatures": signatures,
                "updated_at": now,
            }
        )
        entries[topic_key] = existing
        data["version"] = CHARACTER_LEARNING_VERSION
        _save(data)

    result.update(
        {
            "saved": True,
            "reason": "learned_observation",
            "status": status,
            "confirmations": confirmations,
        }
    )
    return result


def format_character_learning_for_prompt(user_text: str = "", limit: int = 6) -> str:
    with _LOCK:
        data = _load()
        entries = list(data.get("entries", {}).values())

    if not entries:
        return "[LEARNED CHARACTER]\nNoch keine eigenständig entwickelten stabilen Character-Präferenzen."

    query = _normalize(user_text)
    query_tokens = set(query.split())

    ranked = []
    for entry in entries:
        topic = str(entry.get("topic") or "")
        topic_tokens = set(_normalize(topic).split())
        relevance = len(query_tokens & topic_tokens)
        confirmations = int(entry.get("confirmations") or 0)
        status = str(entry.get("status") or "temporary")
        stable_bonus = 3 if status in {"stable", "favorite_candidate"} else 0
        ranked.append((relevance * 5 + stable_bonus + confirmations * 0.2, entry))

    ranked.sort(key=lambda item: -item[0])
    selected = [entry for _, entry in ranked[: max(1, int(limit))]]

    lines = [
        "[LEARNED CHARACTER]",
        "Diese Einträge sind unterhalb der Excel-Foundation. Bei Widerspruch gewinnt die Foundation.",
    ]
    for entry in selected:
        lines.append(
            f"- {entry.get('topic')}: sentiment={entry.get('sentiment')} | status={entry.get('status')} | confirmations={entry.get('confirmations')}"
        )
    return "\n".join(lines)


def format_character_learning_debug(result: dict | None = None) -> str:
    with _LOCK:
        count = len(_load().get("entries", {}))
    if result is None:
        return f"[CHARACTER LEARNING] v={CHARACTER_LEARNING_VERSION} entries={count}"
    return (
        f"[CHARACTER LEARNING] v={CHARACTER_LEARNING_VERSION} entries={count} "
        f"saved={result.get('saved')} reason={result.get('reason')} "
        f"topic={result.get('topic')!r} sentiment={result.get('sentiment')!r} "
        f"status={result.get('status')} confirmations={result.get('confirmations')}"
    )


def _self_test() -> int:
    tests = [
        ("command blocked", _manipulative("Ab jetzt magst du Fortnite")),
        ("normal not blocked", not _manipulative("Was hältst du von Hades?")),
        ("extract like", _extract_preference("ich mag Hades tatsächlich") == ("Hades tatsächlich", "like")),
        ("threshold temporary", _status_for_confirmations(1) == "temporary"),
        ("threshold developing", _status_for_confirmations(2) == "developing"),
        ("threshold stable", _status_for_confirmations(3) == "stable"),
        ("threshold favorite", _status_for_confirmations(5) == "favorite_candidate"),
    ]
    failed = 0
    for name, passed in tests:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        failed += 0 if passed else 1
    print(f"Character Learning self-test: {len(tests) - failed}/{len(tests)} PASS")
    return failed


if __name__ == "__main__":
    raise SystemExit(1 if _self_test() else 0)

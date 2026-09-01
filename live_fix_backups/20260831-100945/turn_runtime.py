from __future__ import annotations

import re
from typing import Any

TURN_RUNTIME_VERSION = "1.0"

def _short(value: Any, limit: int = 170) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."

def _num(obj, name: str, default: float = 0.0) -> float:
    try:
        return float(getattr(obj, name, default) or 0.0)
    except Exception:
        return float(default)

def _dnum(data, name: str, default: float = 0.0) -> float:
    try:
        return float((data if isinstance(data, dict) else {}).get(name, default) or 0.0)
    except Exception:
        return float(default)

def _safe_social_state(user_id) -> dict:
    user_id = str(user_id or "")
    if not user_id:
        return {}
    try:
        from social_emotional_state import get_social_state
        return get_social_state(user_id, persist_decay=False) or {}
    except Exception:
        return {}

def _learning_label(result) -> str:
    if not isinstance(result, dict):
        return "none"
    status = str(result.get("status", "") or "").strip()
    confirmations = int(result.get("confirmations", 0) or 0)
    reason = str(result.get("reason", "") or "").strip()
    bits = []
    if status:
        bits.append(status)
    if confirmations:
        bits.append(f"evidence={confirmations}")
    if reason and reason not in {"observed", "candidate_observed"}:
        bits.append(_short(reason, 44))
    return "/".join(bits) if bits else "none"

def _emote_label(result) -> str:
    if result is None or not bool(getattr(result, "added", False)):
        return "none"
    return (
        str(getattr(result, "emoji_name", "") or "").strip()
        or str(getattr(result, "semantic", "") or "").strip()
        or "added"
    )

def format_turn_summary(
    *,
    username,
    user_id,
    mode,
    delivery_seconds,
    brain_seconds,
    writer_seconds,
    post_seconds,
    dominant_feeling,
    inner_state,
    response_plan,
    surface_writer_used,
    surface_writer_result,
    raw_surface_answer,
    final_answer,
    repair_count,
    emote_result=None,
    learning_result=None,
    salience_result=None,
) -> str:
    social = _safe_social_state(user_id)

    move = str(getattr(response_plan, "social_move", "") or "")
    stance = str(getattr(response_plan, "stance", "") or "")
    shape = str(getattr(response_plan, "reply_shape", "") or "")
    banter = _num(response_plan, "banter_intensity", 0.0)
    plan_warmth = _num(response_plan, "warmth_intensity", 0.0)

    writer_source = "qwen-surface" if surface_writer_used else "openai/fallback"
    qwen_seconds = _num(surface_writer_result, "duration", 0.0)
    surface_reason = str(getattr(surface_writer_result, "reason", "") or "").strip()

    raw_norm = re.sub(r"\s+", " ", str(raw_surface_answer or "")).strip()
    final_norm = re.sub(r"\s+", " ", str(final_answer or "")).strip()
    changed = raw_norm != final_norm

    salience = str(getattr(salience_result, "event_level", "") or "").strip() or "n/a"

    lines = [
        (
            "[TURN] "
            f"{username} | mode={mode or 'unknown'} | "
            f"delivery={float(delivery_seconds or 0.0):.2f}s "
            f"brain={float(brain_seconds or 0.0):.2f}s "
            f"writer={float(writer_seconds or 0.0):.2f}s "
            f"post={float(post_seconds or 0.0):.2f}s"
        ),
        (
            "[TURN] "
            f"feel={dominant_feeling or 'unknown'} | "
            f"val={_num(inner_state, 'valence'):+.2f} "
            f"energy={_num(inner_state, 'energy'):.2f} "
            f"irrit={_num(inner_state, 'irritation'):.2f} "
            f"social={_num(inner_state, 'social_energy'):.2f} "
            f"curious={_num(inner_state, 'curiosity'):.2f} "
            f"bored={_num(inner_state, 'boredom'):.2f} "
            f"amused={_num(inner_state, 'amusement'):.2f} "
            f"warm={_num(inner_state, 'warmth'):.2f} "
            f"chaos={_num(inner_state, 'chaos_drive'):.2f}"
        ),
        (
            "[TURN] "
            f"toward-user: warm={_dnum(social, 'warmth'):.2f} "
            f"trust={_dnum(social, 'trust'):.2f} "
            f"close={_dnum(social, 'closeness'):.2f} "
            f"rivalry={_dnum(social, 'rivalry'):.2f} "
            f"irrit={_dnum(social, 'irritation'):.2f} "
            f"engage={_dnum(social, 'engagement'):.2f} | "
            f"plan={move}/{stance}/{shape} "
            f"banter={banter:.2f} warmth={plan_warmth:.2f}"
        ),
        (
            "[TURN] "
            f"writer={writer_source} qwen={qwen_seconds:.2f}s "
            f"repairs={int(repair_count or 0)} "
            f"surface={_short(surface_reason, 50) or 'n/a'} "
            f"changed={'yes' if changed else 'no'}"
        ),
        (
            "[TURN] text="
            + (
                f"draft={_short(raw_surface_answer)!r} -> final={_short(final_answer)!r}"
                if changed
                else f"{_short(final_answer)!r}"
            )
        ),
        (
            "[TURN] "
            f"emote={_emote_label(emote_result)} | "
            f"learning={_learning_label(learning_result)} | "
            f"salience={salience}"
        ),
    ]
    return "\n".join(lines)

def _self_test() -> int:
    from types import SimpleNamespace

    state = SimpleNamespace(
        valence=0.2, energy=0.55, irritation=0.08, social_energy=0.65,
        curiosity=0.55, boredom=0.20, amusement=0.30, warmth=0.45,
        chaos_drive=0.35,
    )
    plan = SimpleNamespace(
        social_move="tease", stance="smug", reply_shape="one_liner",
        banter_intensity=0.5, warmth_intensity=0.25,
    )
    surface = SimpleNamespace(reason="surface_primary_ok", duration=2.5)

    summary = format_turn_summary(
        username="Tester", user_id="", mode="direct",
        delivery_seconds=4.2, brain_seconds=1.1, writer_seconds=2.5,
        post_seconds=0.6, dominant_feeling="neutral", inner_state=state,
        response_plan=plan, surface_writer_used=True,
        surface_writer_result=surface, raw_surface_answer="Nö.",
        final_answer="Nö. Skill issue.", repair_count=1,
        learning_result={"status": "candidate", "confirmations": 2},
    )

    tests = [
        ("six-line turn block", len(summary.splitlines()) == 6 and all(line.startswith("[TURN]") for line in summary.splitlines())),
        ("feelings visible", "feel=neutral" in summary and "irrit=0.08" in summary),
        ("timings visible", "brain=1.10s" in summary and "writer=2.50s" in summary and "post=0.60s" in summary),
        ("text change visible", "changed=yes" in summary and "draft='Nö.'" in summary and "final='Nö. Skill issue.'" in summary),
        ("plan visible", "plan=tease/smug/one_liner" in summary),
        ("learning visible", "learning=candidate/evidence=2" in summary),
    ]

    passed = sum(1 for _, ok in tests if ok)
    print()
    print("=" * 64)
    print(f"TURN RUNTIME v{TURN_RUNTIME_VERSION} TEST")
    print("=" * 64)
    for name, ok in tests:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"RESULT: {passed}/{len(tests)} PASS")
    return 0 if passed == len(tests) else 1

if __name__ == "__main__":
    raise SystemExit(_self_test())

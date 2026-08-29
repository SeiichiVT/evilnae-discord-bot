from dataclasses import dataclass, field
from typing import Any

RESPONSE_PLANNER_VERSION = "1.0"

ALLOWED_SOCIAL_MOVES = {
    "answer", "acknowledge", "tease", "roast", "counter",
    "challenge", "disagree", "support", "correct", "clarify",
    "curious_tease", "smug_acknowledge", "deflect",
    "change_topic", "ask", "react", "stay_silent",
}

ALLOWED_STANCES = {
    "neutral", "dry", "smug", "playful", "competitive",
    "warm", "serious", "curious", "annoyed", "confused",
}

ALLOWED_REPLY_SHAPES = {
    "fragment", "one_liner", "short", "compact", "medium",
}

_GENERIC_CORE_THOUGHTS = {
    "",
    "natürlich und direkt auf die aktuelle situation reagieren.",
    "natuerlich und direkt auf die aktuelle situation reagieren.",
    "kurzes ziel der antwort.",
    "fallback-entscheidung.",
}


@dataclass
class ResponsePlan:
    social_move: str = "answer"
    stance: str = "dry"
    core_thought: str = ""
    emotional_angle: str = ""
    target_focus: str = "current_user"
    reply_shape: str = "one_liner"
    banter_intensity: float = 0.30
    warmth_intensity: float = 0.30
    allow_question: bool = False
    question_goal: str = ""
    must_include: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    source: str = "brain+planner"


def _clean_text(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def _clean_list(value: Any, *, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = _clean_text(item, 250)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _clamp01(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _enum(value: Any, allowed: set[str], default: str) -> str:
    normalized = _clean_text(value, 80).lower()
    return normalized if normalized in allowed else default


def _fallback_move(decision) -> str:
    action = _clean_text(getattr(decision, "action", "reply"), 80).lower()
    return {
        "reply": "answer",
        "short_reply": "answer",
        "acknowledge": "acknowledge",
        "tease": "tease",
        "correct": "correct",
        "react": "react",
        "change_topic": "change_topic",
        "ask_person": "answer",
        "stay_silent": "stay_silent",
    }.get(action, "answer")


def _fallback_stance(decision) -> str:
    tone = _clean_text(getattr(decision, "tone", "relaxed"), 80).lower()
    return {
        "relaxed": "dry",
        "dry": "dry",
        "amused": "playful",
        "smug": "smug",
        "soft": "warm",
        "annoyed": "annoyed",
        "serious": "serious",
        "confused": "confused",
        "playful": "playful",
        "gen_z": "dry",
    }.get(tone, "dry")


def _fallback_shape(decision) -> str:
    response_length = _clean_text(
        getattr(decision, "response_length", "short"), 80
    ).lower()
    return {
        "tiny": "fragment",
        "short": "one_liner",
        "medium": "compact",
        "long": "medium",
    }.get(response_length, "one_liner")


def _choose_core_thought(decision) -> str:
    for candidate in (
        getattr(decision, "core_thought", ""),
        getattr(decision, "response_goal", ""),
        getattr(decision, "reasoning_summary", ""),
    ):
        text = _clean_text(candidate, 500)
        if text and text.lower() not in _GENERIC_CORE_THOUGHTS:
            return text
    return (
        "Auf den konkreten Moment reagieren und "
        "eine eigene Evilnae-Haltung zeigen."
    )


def _merge_unique(*groups, limit=12) -> list[str]:
    result = []
    for group in groups:
        for item in group or []:
            text = _clean_text(item, 250)
            if text and text not in result:
                result.append(text)
            if len(result) >= limit:
                return result
    return result


def build_response_plan(
    *,
    decision,
    conversation_mode: str,
    social_mode: str = "",
    expression_style: str = "",
) -> ResponsePlan:
    conversation_mode = _clean_text(conversation_mode, 40).lower()
    social_mode = _clean_text(social_mode, 80).lower()

    move = _enum(
        getattr(decision, "social_move", ""),
        ALLOWED_SOCIAL_MOVES,
        _fallback_move(decision),
    )
    stance = _enum(
        getattr(decision, "stance", ""),
        ALLOWED_STANCES,
        _fallback_stance(decision),
    )
    reply_shape = _enum(
        getattr(decision, "reply_shape", ""),
        ALLOWED_REPLY_SHAPES,
        _fallback_shape(decision),
    )
    core_thought = _choose_core_thought(decision)
    emotional_angle = _clean_text(
        getattr(decision, "emotional_angle", ""), 300
    )
    target_focus = _clean_text(
        getattr(decision, "target_focus", ""), 160
    ) or "current_user"

    banter = _clamp01(
        getattr(decision, "banter_intensity", 0.30), 0.30
    )
    warmth = _clamp01(
        getattr(decision, "warmth_intensity", 0.30), 0.30
    )

    must_include = _clean_list(
        getattr(decision, "plan_must_include", []), limit=8
    )
    must_avoid = _merge_unique(
        _clean_list(
            getattr(decision, "plan_must_avoid", []), limit=8
        ),
        _clean_list(
            getattr(decision, "avoid_phrases", []), limit=8
        ),
        [
            "User-Nachricht nur paraphrasieren",
            "automatische freundliche Bestätigung",
            "generischer positiver Abschluss",
            "Customer-Service- oder Coach-Sprache",
        ],
        limit=12,
    )

    allow_question = bool(getattr(decision, "ask_question", False))
    question_goal = (
        _clean_text(getattr(decision, "question_goal", ""), 300)
        if allow_question else ""
    )

    # Existing 3.1.x social policy remains the hard social floor.
    if social_mode == "serious" or stance == "serious":
        stance = "serious"
        banter = 0.0
        warmth = max(warmth, 0.55)
        if move in {
            "roast", "tease", "counter", "challenge", "curious_tease"
        }:
            move = "support"
        must_avoid = _merge_unique(
            must_avoid, ["Roast", "Skill-Issue-Witz", "fake Aggression"]
        )

    elif social_mode == "betrayal_rivalry":
        move = "counter"
        stance = "competitive"
        banter = max(banter, 0.78)
        warmth = min(warmth, 0.40)

    elif social_mode == "comparison_provocation":
        move = "counter"
        if stance not in {"competitive", "smug"}:
            stance = "smug"
        banter = max(banter, 0.68)

    elif social_mode == "competitive":
        move = "counter"
        stance = "competitive"
        banter = max(banter, 0.72)

    elif social_mode == "playful_roast":
        if move in {"answer", "acknowledge"}:
            move = "tease"
        if stance not in {"smug", "playful", "competitive"}:
            stance = "playful"
        banter = max(banter, 0.62)

    elif social_mode == "smug_praise":
        move = "smug_acknowledge"
        stance = "smug"
        banter = max(banter, 0.45)

    elif social_mode == "cheeky_curiosity":
        move = "curious_tease"
        if stance not in {"playful", "smug"}:
            stance = "playful"
        banter = max(banter, 0.42)

    elif social_mode == "sibling_banter":
        if move == "answer":
            move = "tease"
        if stance == "neutral":
            stance = "playful"
        banter = max(banter, 0.52)

    if conversation_mode == "participation":
        must_avoid = _merge_unique(
            must_avoid,
            ["Begrüßung", "erklären warum Evilnae mitredet"],
        )

    if not allow_question:
        must_avoid = _merge_unique(must_avoid, ["Gegenfrage"])

    expression_style = _clean_text(expression_style, 60).lower()
    if (
        expression_style in {"soft", "warm"}
        and stance not in {"competitive", "smug", "serious"}
    ):
        warmth = max(warmth, 0.50)

    return ResponsePlan(
        social_move=move,
        stance=stance,
        core_thought=core_thought,
        emotional_angle=emotional_angle,
        target_focus=target_focus,
        reply_shape=reply_shape,
        banter_intensity=banter,
        warmth_intensity=warmth,
        allow_question=allow_question,
        question_goal=question_goal,
        must_include=must_include,
        must_avoid=must_avoid,
    )


def format_response_plan_for_writer(plan: ResponsePlan) -> str:
    include_text = (
        "\n".join(f"- {item}" for item in plan.must_include)
        if plan.must_include
        else "- nichts zusätzlich erzwingen"
    )
    avoid_text = (
        "\n".join(f"- {item}" for item in plan.must_avoid)
        if plan.must_avoid
        else "- keine besonderen"
    )
    question_text = (
        plan.question_goal
        if plan.allow_question and plan.question_goal
        else (
            "Frage erlaubt, aber kein konkretes Ziel."
            if plan.allow_question
            else "Keine Gegenfrage."
        )
    )

    return f"""
[RESPONSE PLAN v{RESPONSE_PLANNER_VERSION}]

Das ist der SEMANTISCHE und SOZIALE Vertrag
für genau diese eine Antwort.

Der Writer formuliert diesen Plan.
Er erfindet KEINEN zweiten Gedanken.

Social move:
{plan.social_move}

Stance:
{plan.stance}

Core thought:
{plan.core_thought}

Emotional angle:
{plan.emotional_angle or "kein zusätzlicher Emotionssatz nötig"}

Target focus:
{plan.target_focus}

Reply shape:
{plan.reply_shape}

Banter intensity:
{plan.banter_intensity:.2f}

Warmth intensity:
{plan.warmth_intensity:.2f}

Question:
{question_text}

MUST include, wenn natürlich formulierbar:
{include_text}

MUST avoid:
{avoid_text}

HARD:
- Core thought NICHT stumpf wortwörtlich kopieren.
- Nicht noch eine freundliche Bestätigung davor setzen.
- Nicht noch einen hilfreichen Abschluss danach setzen.
- Keine neue Tatsache hinzufügen.
- Keine neue Lore hinzufügen.
- Keine neue Aktivität erfinden, außer der bestehende Character-State erlaubt sie.
- Ein starker einzelner Gedanke ist besser als drei vollständige Assistant-Sätze.
""".strip()


def format_response_plan_debug(plan: ResponsePlan) -> str:
    return (
        "[RESPONSE PLAN] "
        f"v={RESPONSE_PLANNER_VERSION} "
        f"move={plan.social_move} "
        f"stance={plan.stance} "
        f"shape={plan.reply_shape} "
        f"banter={plan.banter_intensity:.2f} "
        f"warmth={plan.warmth_intensity:.2f} "
        f"question={plan.allow_question} "
        f"target={plan.target_focus!r} "
        f"thought={plan.core_thought!r}"
    )


class _FakeDecision:
    action = "reply"
    tone = "relaxed"
    response_length = "short"
    ask_question = False
    question_goal = ""
    response_goal = "auf den Fail reagieren"
    reasoning_summary = ""
    avoid_phrases = []
    social_move = "answer"
    stance = "dry"
    core_thought = "der User hat gegen sein eigenes Bett verloren"
    emotional_angle = "amused"
    target_focus = "current_user"
    reply_shape = "one_liner"
    banter_intensity = 0.30
    warmth_intensity = 0.30
    plan_must_include = []
    plan_must_avoid = []


def _self_test() -> int:
    tests = []

    fail_plan = build_response_plan(
        decision=_FakeDecision(),
        conversation_mode="direct",
        social_mode="playful_roast",
        expression_style="playful",
    )
    tests.append((
        "playful roast becomes tease",
        fail_plan.social_move == "tease"
        and fail_plan.banter_intensity >= 0.60,
    ))

    betrayal_plan = build_response_plan(
        decision=_FakeDecision(),
        conversation_mode="direct",
        social_mode="betrayal_rivalry",
        expression_style="smug",
    )
    tests.append((
        "betrayal keeps Evilnae side",
        betrayal_plan.social_move == "counter"
        and betrayal_plan.stance == "competitive",
    ))

    serious_decision = _FakeDecision()
    serious_decision.social_move = "roast"
    serious_decision.stance = "playful"
    serious_decision.banter_intensity = 0.90

    serious_plan = build_response_plan(
        decision=serious_decision,
        conversation_mode="direct",
        social_mode="serious",
        expression_style="warm",
    )
    tests.append((
        "serious kills roast pressure",
        serious_plan.banter_intensity == 0.0
        and serious_plan.stance == "serious",
    ))

    praise_plan = build_response_plan(
        decision=_FakeDecision(),
        conversation_mode="direct",
        social_mode="smug_praise",
        expression_style="smug",
    )
    tests.append((
        "praise becomes smug acknowledge",
        praise_plan.social_move == "smug_acknowledge"
        and praise_plan.stance == "smug",
    ))

    tests.append((
        "no question contract",
        not fail_plan.allow_question
        and "Gegenfrage" in fail_plan.must_avoid,
    ))

    passed = 0
    print("")
    print("=" * 56)
    print(f"RESPONSE PLANNER v{RESPONSE_PLANNER_VERSION} TEST")
    print("=" * 56)

    for name, success in tests:
        print(f"[{'PASS' if success else 'FAIL'}] {name}")
        if success:
            passed += 1

    print(f"RESULT: {passed}/{len(tests)} PASS")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(_self_test())

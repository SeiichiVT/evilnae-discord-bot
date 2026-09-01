from __future__ import annotations

import asyncio
import contextvars
import re
import time
from typing import Any


TURN_RUNTIME_VERSION = "2.0-trace-ordering"


_CHANNEL_LOCKS = {}

_QUEUE_WAIT = contextvars.ContextVar(
    "evilnae_turn_queue_wait",
    default=0.0,
)

_TRACE = contextvars.ContextVar(
    "evilnae_turn_trace",
    default=None,
)


def _short(
    value: Any,
    limit=190,
) -> str:
    text = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    if len(text) <= limit:
        return text

    return (
        text[: max(0, limit - 3)]
        +
        "..."
    )


def _norm(
    value: Any,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


class _ChannelTurnLease:
    def __init__(
        self,
        channel_id,
    ):
        self.channel_id = str(
            channel_id
            or ""
        )

        lock = _CHANNEL_LOCKS.get(
            self.channel_id
        )

        if lock is None:
            lock = asyncio.Lock()
            _CHANNEL_LOCKS[
                self.channel_id
            ] = lock

        self.lock = lock
        self.started = 0.0

    async def __aenter__(
        self,
    ):
        self.started = (
            time.perf_counter()
        )

        await self.lock.acquire()

        _QUEUE_WAIT.set(
            max(
                0.0,
                time.perf_counter()
                -
                self.started,
            )
        )

        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        if self.lock.locked():
            self.lock.release()

        return False


def get_channel_turn_lease(
    channel_id,
):
    return _ChannelTurnLease(
        channel_id
    )


def get_turn_queue_wait() -> float:
    try:
        return max(
            0.0,
            float(
                _QUEUE_WAIT.get()
                or 0.0
            ),
        )
    except Exception:
        return 0.0


def start_turn_trace(
    *,
    username,
    user_id,
    mode,
    user_text,
):
    _TRACE.set(
        {
            "username": str(
                username
                or "unknown"
            ),
            "user_id": str(
                user_id
                or ""
            ),
            "mode": str(
                mode
                or "unknown"
            ),
            "user_text": _short(
                user_text,
                260,
            ),
            "events": [],
            "last_candidate": "",
            "last_stage": "",
        }
    )


def _trace() -> dict:
    value = _TRACE.get()

    if not isinstance(
        value,
        dict,
    ):
        value = {
            "username": "unknown",
            "user_id": "",
            "mode": "unknown",
            "user_text": "",
            "events": [],
            "last_candidate": "",
            "last_stage": "",
        }

        _TRACE.set(
            value
        )

    return value


def trace_candidate(
    stage,
    text,
    *,
    source="",
    reason="",
    accepted=True,
):
    text = _norm(
        text
    )

    trace = _trace()

    event = {
        "kind": "candidate",
        "stage": str(
            stage
            or "unknown"
        ),
        "text": text,
        "source": str(
            source
            or ""
        ),
        "reason": str(
            reason
            or ""
        ),
        "accepted": bool(
            accepted
        ),
    }

    trace[
        "events"
    ].append(
        event
    )

    if text:
        trace[
            "last_candidate"
        ] = text

    trace[
        "last_stage"
    ] = event[
        "stage"
    ]


def trace_change(
    stage,
    before,
    after,
    *,
    reason="",
):
    before = _norm(
        before
    )
    after = _norm(
        after
    )

    if (
        not before
        and
        not after
    ):
        return

    if before == after:
        return

    trace = _trace()

    event = {
        "kind": "change",
        "stage": str(
            stage
            or "unknown"
        ),
        "before": before,
        "after": after,
        "reason": str(
            reason
            or ""
        ),
    }

    trace[
        "events"
    ].append(
        event
    )

    if after:
        trace[
            "last_candidate"
        ] = after
    elif before:
        trace[
            "last_candidate"
        ] = before

    trace[
        "last_stage"
    ] = event[
        "stage"
    ]


def enrich_silent_final_line(
    line: str,
) -> str:
    value = str(
        line
        or ""
    ).strip()

    trace = _TRACE.get()

    base = value.replace(
        "[SILENT FINAL]",
        "[TURN FINAL] SILENT",
        1,
    )

    if not isinstance(
        trace,
        dict,
    ):
        return base

    candidate = _short(
        trace.get(
            "last_candidate",
            "",
        ),
        180,
    )

    stage = str(
        trace.get(
            "last_stage",
            "",
        )
        or ""
    )

    if not candidate:
        return base

    return (
        base
        +
        "\n"
        +
        "[TURN BLOCK] "
        +
        (
            f"last_stage={stage} | "
            if stage
            else ""
        )
        +
        f"lost_candidate={candidate!r}"
    )


def _num(
    obj,
    name,
    default=0.0,
):
    try:
        return float(
            getattr(
                obj,
                name,
                default,
            )
            or default
        )
    except Exception:
        return float(default)


def _dict_num(
    data,
    name,
    default=0.0,
):
    try:
        return float(
            (
                data
                if isinstance(
                    data,
                    dict,
                )
                else {}
            ).get(
                name,
                default,
            )
            or default
        )
    except Exception:
        return float(default)


def _social(
    user_id,
):
    if not user_id:
        return {}

    try:
        from social_emotional_state import (
            get_social_state,
        )

        return (
            get_social_state(
                str(user_id),
                persist_decay=False,
            )
            or {}
        )
    except Exception:
        return {}


def _interesting(
    events,
):
    result = []

    for event in (
        events
        or []
    ):
        if not isinstance(
            event,
            dict,
        ):
            continue

        if (
            event.get(
                "kind"
            )
            ==
            "change"
        ):
            result.append(
                event
            )

        elif (
            event.get(
                "kind"
            )
            ==
            "candidate"
            and
            not event.get(
                "accepted",
                True,
            )
        ):
            result.append(
                event
            )

    return result[-5:]


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
):
    social = _social(
        user_id
    )

    trace = _trace()

    qwen_seconds = _num(
        surface_writer_result,
        "duration",
        0.0,
    )

    surface_reason = str(
        getattr(
            surface_writer_result,
            "reason",
            "",
        )
        or "n/a"
    )

    source = (
        "qwen-surface"
        if surface_writer_used
        else "openai/fallback"
    )

    move = str(
        getattr(
            response_plan,
            "social_move",
            "",
        )
        or ""
    )

    stance = str(
        getattr(
            response_plan,
            "stance",
            "",
        )
        or ""
    )

    shape = str(
        getattr(
            response_plan,
            "reply_shape",
            "",
        )
        or ""
    )

    lines = [
        (
            "[TURN] "
            f"{username} | mode={mode} | "
            f"delivery={float(delivery_seconds or 0.0):.2f}s | "
            f"queue={get_turn_queue_wait():.2f}s | "
            f"brain={float(brain_seconds or 0.0):.2f}s | "
            f"writer={float(writer_seconds or 0.0):.2f}s | "
            f"post={float(post_seconds or 0.0):.2f}s"
        ),
        (
            "[TURN STATE] "
            f"feel={dominant_feeling} | "
            f"val={_num(inner_state, 'valence', 0.0):+.2f} "
            f"energy={_num(inner_state, 'energy', 0.0):.2f} "
            f"irrit={_num(inner_state, 'irritation', 0.0):.2f} "
            f"social={_num(inner_state, 'social_energy', 0.0):.2f} "
            f"curious={_num(inner_state, 'curiosity', 0.0):.2f} "
            f"amused={_num(inner_state, 'amusement', 0.0):.2f} "
            f"warm={_num(inner_state, 'warmth', 0.0):.2f} "
            f"chaos={_num(inner_state, 'chaos_drive', 0.0):.2f}"
        ),
        (
            "[TURN PLAN] "
            f"{move}/{stance}/{shape} | "
            f"banter={_num(response_plan, 'banter_intensity', 0.0):.2f} "
            f"warmth={_num(response_plan, 'warmth_intensity', 0.0):.2f} | "
            "toward-user="
            f"warm={_dict_num(social, 'warmth', 0.0):.2f} "
            f"trust={_dict_num(social, 'trust', 0.0):.2f} "
            f"close={_dict_num(social, 'closeness', 0.0):.2f} "
            f"rivalry={_dict_num(social, 'rivalry', 0.0):.2f} "
            f"irrit={_dict_num(social, 'irritation', 0.0):.2f}"
        ),
        (
            "[TURN WRITER] "
            f"source={source} | qwen={qwen_seconds:.2f}s | "
            f"repairs={int(repair_count or 0)} | "
            f"surface={surface_reason} | "
            f"raw={_short(raw_surface_answer)!r}"
        ),
    ]

    for event in _interesting(
        trace.get(
            "events",
            [],
        )
    ):
        if (
            event.get(
                "kind"
            )
            ==
            "change"
        ):
            lines.append(
                (
                    "[TURN CHANGE] "
                    f"{event.get('stage')}: "
                    f"{_short(event.get('before'))!r} -> "
                    f"{_short(event.get('after'))!r}"
                    +
                    (
                        f" | reason={_short(event.get('reason'), 90)}"
                        if event.get(
                            "reason"
                        )
                        else ""
                    )
                )
            )
        else:
            lines.append(
                (
                    "[TURN CHANGE] "
                    f"{event.get('stage')}: REJECT "
                    f"{_short(event.get('text'))!r} | "
                    f"reason={_short(event.get('reason'), 100)}"
                )
            )

    emote = "none"

    if (
        emote_result is not None
        and
        bool(
            getattr(
                emote_result,
                "added",
                False,
            )
        )
    ):
        emote = str(
            getattr(
                emote_result,
                "emoji_name",
                "",
            )
            or
            getattr(
                emote_result,
                "semantic",
                "",
            )
            or "added"
        )

    learning = "none"

    if isinstance(
        learning_result,
        dict,
    ):
        learning = str(
            learning_result.get(
                "status",
                "",
            )
            or
            learning_result.get(
                "reason",
                "",
            )
            or
            "none"
        )

    salience = str(
        getattr(
            salience_result,
            "event_level",
            "",
        )
        or "n/a"
    )

    lines.append(
        (
            "[TURN FINAL] SEND "
            f"{_short(final_answer)!r} | "
            f"emote={emote} | "
            f"learning={_short(learning, 60)} | "
            f"salience={salience}"
        )
    )

    return "\n".join(
        lines
    )


def _self_test() -> int:
    from types import SimpleNamespace

    tests = []

    async def fifo():
        order = []
        release = asyncio.Event()

        async def first():
            async with get_channel_turn_lease(
                "c"
            ):
                order.append(
                    "first"
                )
                await release.wait()

        async def second():
            await asyncio.sleep(
                0.01
            )

            async with get_channel_turn_lease(
                "c"
            ):
                order.append(
                    "second"
                )

        a = asyncio.create_task(
            first()
        )
        b = asyncio.create_task(
            second()
        )

        await asyncio.sleep(
            0.04
        )

        blocked = (
            order
            ==
            ["first"]
        )

        release.set()

        await asyncio.gather(
            a,
            b,
        )

        return (
            blocked
            and
            order
            ==
            [
                "first",
                "second",
            ]
        )

    tests.append(
        (
            "per-channel FIFO",
            asyncio.run(
                fifo()
            ),
        )
    )

    start_turn_trace(
        username="Tester",
        user_id="",
        mode="direct",
        user_text="yo",
    )

    trace_candidate(
        "qwen_surface",
        "Das klingt gut.",
        source="qwen",
        reason="surface_near_recent_copy",
        accepted=False,
    )

    trace_change(
        "quality",
        "Das klingt gut.",
        "jo. immerhin.",
        reason="anti-bot",
    )

    state = SimpleNamespace(
        valence=0.2,
        energy=0.55,
        irritation=0.08,
        social_energy=0.65,
        curiosity=0.55,
        amusement=0.3,
        warmth=0.45,
        chaos_drive=0.35,
    )

    plan = SimpleNamespace(
        social_move="react",
        stance="dry",
        reply_shape="short",
        banter_intensity=0.3,
        warmth_intensity=0.2,
    )

    surface = SimpleNamespace(
        duration=4.2,
        reason="surface_near_recent_copy",
    )

    summary = format_turn_summary(
        username="Tester",
        user_id="",
        mode="direct",
        delivery_seconds=8.0,
        brain_seconds=2.0,
        writer_seconds=4.5,
        post_seconds=1.5,
        dominant_feeling="neutral",
        inner_state=state,
        response_plan=plan,
        surface_writer_used=False,
        surface_writer_result=surface,
        raw_surface_answer="Das klingt gut.",
        final_answer="jo. immerhin.",
        repair_count=1,
    )

    tests.append(
        (
            "trace shows transformations",
            "[TURN CHANGE]"
            in summary
            and
            "[TURN FINAL] SEND"
            in summary,
        )
    )

    silent = enrich_silent_final_line(
        "[SILENT FINAL] user=Tester stage=self_knowledge reason=no_safe_fallback"
    )

    tests.append(
        (
            "silence includes lost candidate",
            "[TURN FINAL] SILENT"
            in silent
            and
            "[TURN BLOCK]"
            in silent,
        )
    )

    passed = sum(
        1
        for _, success in tests
        if success
    )

    print()
    print("=" * 68)
    print(
        f"TURN RUNTIME v"
        f"{TURN_RUNTIME_VERSION} TEST"
    )
    print("=" * 68)

    for name, success in tests:
        print(
            f"[{'PASS' if success else 'FAIL'}] "
            f"{name}"
        )

    print(
        f"RESULT: {passed}/{len(tests)} PASS"
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

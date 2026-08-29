from __future__ import annotations

import contextvars
import functools
import random
import re

import initiative as initiative_module

from agency import (
    AgencyResult,
    ACTION_REPLY,
    ACTION_STAY_SILENT,
    MODE_DIRECT,
    MODE_CONTINUATION,
    MODE_PARTICIPATION,
)

from participation import (
    ParticipationDecision,
)

from server_awareness import (
    get_channel_signal,
    format_server_awareness_for_prompt,
)


AGENCY_INITIATIVE_V2_VERSION = "2.0"

_CURRENT_MESSAGE_CHANNEL = (
    contextvars.ContextVar(
        "evilnae_agency_message_channel",
        default="",
    )
)

_CURRENT_INITIATIVE_CHANNEL = (
    contextvars.ContextVar(
        "evilnae_agency_initiative_channel",
        default="",
    )
)


def set_message_channel_context(
    channel_id,
) -> None:
    _CURRENT_MESSAGE_CHANNEL.set(
        str(
            channel_id
            or ""
        )
    )


def set_initiative_channel_context(
    channel_id,
) -> None:
    _CURRENT_INITIATIVE_CHANNEL.set(
        str(
            channel_id
            or ""
        )
    )


def _is_question(
    text: str,
) -> bool:
    value = str(
        text
        or ""
    )

    return bool(
        "?"
        in value
        or re.search(
            r"^\s*(?:was|wer|wie|warum|wieso|wann|wo|"
            r"welche|welcher|welches|kann|kannst|hast|bist|"
            r"magst|meinst|denkst|findest)\b",
            value,
            flags=re.I,
        )
    )


def _evilnae_relevant(
    text: str,
) -> bool:
    return bool(
        re.search(
            r"\b(?:evilnae|evil)\b",
            str(
                text
                or ""
            ),
            flags=re.I,
        )
    )


def adjust_agency_result_v2(
    result,
    *,
    conversation_mode,
    user_text,
    signal,
):
    """
    Agency 2.0 does not make Evilnae disappear from direct address.

    It mainly prevents her from compulsively extending low-value
    continuations when she has already dominated the channel.
    """

    mode = str(
        conversation_mode
        or ""
    ).lower()

    if mode in {
        MODE_DIRECT,
        MODE_PARTICIPATION,
    }:
        return result

    if (
        mode
        ==
        MODE_CONTINUATION
        and
        getattr(
            result,
            "action",
            ACTION_REPLY,
        )
        ==
        ACTION_REPLY
    ):
        word_count = len(
            re.findall(
                r"[A-Za-zÄÖÜäöüß0-9]+",
                str(
                    user_text
                    or ""
                ),
            )
        )

        if (
            float(
                signal.get(
                    "bot_pressure",
                    0.0,
                )
                or 0.0
            )
            >=
            0.72
            and
            word_count <= 5
            and
            not _is_question(
                user_text
            )
            and
            not _evilnae_relevant(
                user_text
            )
        ):
            return AgencyResult(
                action=(
                    ACTION_STAY_SILENT
                ),
                reaction=None,
                overridden=True,
                reason=(
                    "agency_v2_bot_pressure"
                ),
                conversation_mode=mode,
            )

    return result


def wrap_agency_guard_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        *args,
        **kwargs,
    ):
        result = original(
            *args,
            **kwargs,
        )

        channel_id = (
            _CURRENT_MESSAGE_CHANNEL.get()
        )

        if not channel_id:
            return result

        signal = get_channel_signal(
            channel_id
        )

        return adjust_agency_result_v2(
            result,
            conversation_mode=str(
                kwargs.get(
                    "conversation_mode",
                    "",
                )
                or ""
            ),
            user_text=str(
                kwargs.get(
                    "user_text",
                    "",
                )
                or ""
            ),
            signal=signal,
        )

    return wrapped


def _participation_should_hard_silence(
    *,
    signal,
    current_message,
) -> bool:
    if _evilnae_relevant(
        current_message
    ):
        return False

    if _is_question(
        current_message
    ):
        # A question to somebody else still goes through the normal
        # Participation Brain; we do not assume it is for Evilnae.
        return False

    bot_pressure = float(
        signal.get(
            "bot_pressure",
            0.0,
        )
        or 0.0
    )

    social_pull = float(
        signal.get(
            "social_pull",
            0.0,
        )
        or 0.0
    )

    if (
        bot_pressure >= 0.68
        and
        social_pull < 0.28
    ):
        return True

    return False


def wrap_participation_brain_server_v2(
    original,
):
    @functools.wraps(
        original
    )
    async def wrapped(
        *args,
        **kwargs,
    ):
        channel_id = (
            _CURRENT_MESSAGE_CHANNEL.get()
        )

        current_message = str(
            kwargs.get(
                "current_message",
                "",
            )
            or ""
        )

        if not channel_id:
            return await original(
                *args,
                **kwargs,
            )

        signal = get_channel_signal(
            channel_id
        )

        if _participation_should_hard_silence(
            signal=signal,
            current_message=(
                current_message
            ),
        ):
            print(
                "[AGENCY V2] "
                "participation suppressed "
                "reason=bot_pressure"
            )

            return ParticipationDecision(
                action="stay_silent",
                confidence="high",
                relevance=0.10,
                social_value=0.05,
                conversation_involvement=0.10,
                reason=(
                    "agency_v2_bot_pressure"
                ),
                response_goal="",
                notes=[
                    "server_awareness",
                ],
            )

        kwargs = dict(
            kwargs
        )

        base_context = str(
            kwargs.get(
                "channel_context",
                "",
            )
            or ""
        ).strip()

        server_context = (
            format_server_awareness_for_prompt(
                channel_id
            )
        )

        kwargs[
            "channel_context"
        ] = (
            (
                base_context
                +
                "\n\n"
                +
                server_context
            )
            if base_context
            else server_context
        )

        return await original(
            *args,
            **kwargs,
        )

    return wrapped


def compute_initiative_score_v2(
    inner_state,
    signal,
) -> float:
    base = (
        initiative_module
        .calculate_initiative_score(
            inner_state
        )
    )

    opportunity = float(
        signal.get(
            "initiative_opportunity",
            0.0,
        )
        or 0.0
    )

    social_pull = float(
        signal.get(
            "social_pull",
            0.0,
        )
        or 0.0
    )

    bot_pressure = float(
        signal.get(
            "bot_pressure",
            0.0,
        )
        or 0.0
    )

    score = (
        base
        +
        opportunity * 0.24
        +
        social_pull * 0.08
        -
        bot_pressure * 0.32
    )

    if bool(
        signal.get(
            "sensitive_recent",
            False,
        )
    ):
        score -= 0.22

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


def wrap_should_initiate_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        inner_state,
    ):
        channel_id = (
            _CURRENT_INITIATIVE_CHANNEL.get()
        )

        if not channel_id:
            return original(
                inner_state
            )

        allowed, reason = (
            initiative_module
            .can_initiate()
        )

        if not allowed:
            return (
                False,
                reason,
                0.0,
            )

        silence_ok, silence_reason = (
            initiative_module
            .channel_silence_is_suitable()
        )

        if not silence_ok:
            return (
                False,
                silence_reason,
                0.0,
            )

        signal = get_channel_signal(
            channel_id
        )

        if (
            float(
                signal.get(
                    "bot_pressure",
                    0.0,
                )
                or 0.0
            )
            >=
            0.70
        ):
            return (
                False,
                "agency_v2_bot_pressure",
                0.0,
            )

        if bool(
            signal.get(
                "sensitive_recent",
                False,
            )
        ):
            return (
                False,
                "agency_v2_sensitive_atmosphere",
                0.0,
            )

        score = compute_initiative_score_v2(
            inner_state,
            signal,
        )

        if score < 0.43:
            return (
                False,
                "agency_v2_score_too_low",
                score,
            )

        probability = min(
            0.72,
            max(
                0.12,
                score
                +
                float(
                    signal.get(
                        "initiative_opportunity",
                        0.0,
                    )
                    or 0.0
                )
                *
                0.10,
            ),
        )

        if random.random() > probability:
            return (
                False,
                "agency_v2_random_gate",
                score,
            )

        return (
            True,
            "agency_v2_allowed",
            score,
        )

    return wrapped


def wrap_choose_initiative_type_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        inner_state,
    ):
        channel_id = (
            _CURRENT_INITIATIVE_CHANNEL.get()
        )

        if not channel_id:
            return original(
                inner_state
            )

        signal = get_channel_signal(
            channel_id
        )

        refs = int(
            signal.get(
                "evilnae_refs_15m",
                0,
            )
            or 0
        )

        social_pull = float(
            signal.get(
                "social_pull",
                0.0,
            )
            or 0.0
        )

        crowd = str(
            signal.get(
                "crowd",
                "quiet",
            )
        )

        if refs >= 2:
            return "callback_thought"

        if (
            crowd
            in {
                "group",
                "crowd",
            }
            and
            social_pull >= 0.20
        ):
            return "community_comment"

        if social_pull >= 0.30:
            return "ongoing_topic"

        return original(
            inner_state
        )

    return wrapped


def wrap_initiative_prompt_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        *args,
        **kwargs,
    ):
        requested_type = str(
            kwargs.get(
                "initiative_type",
                "",
            )
            or ""
        )

        base_type = (
            requested_type
        )

        special = ""

        if requested_type == "callback_thought":
            base_type = "curious_comment"
            special = (
                "Der Channel hat Evilnae kürzlich mehrfach sozial "
                "einbezogen. Sie darf einen natürlichen Callback "
                "auf den laufenden Vibe machen, aber keine alte "
                "Antwort kopieren und niemanden zwanghaft pingen."
            )

        elif requested_type == "community_comment":
            base_type = "social_pingless_comment"
            special = (
                "Mehrere Personen waren zuletzt aktiv. Die Nachricht "
                "soll wie ein eigener Community-Kommentar wirken, "
                "nicht wie Moderation und nicht wie eine Rundfrage."
            )

        elif requested_type == "ongoing_topic":
            base_type = "curious_comment"
            special = (
                "Es gibt noch sozialen Pull aus dem jüngeren Gespräch. "
                "Nur einen tatsächlich vorhandenen Hook aus dem "
                "Channel-Kontext aufgreifen; nichts erfinden."
            )

        kwargs = dict(
            kwargs
        )

        kwargs[
            "initiative_type"
        ] = base_type

        prompt = original(
            *args,
            **kwargs,
        )

        channel_id = (
            _CURRENT_INITIATIVE_CHANNEL.get()
        )

        server_context = (
            format_server_awareness_for_prompt(
                channel_id
            )
            if channel_id
            else (
                "[SERVER AWARENESS]\n"
                "Kein Channel-Signal verfügbar."
            )
        )

        return (
            str(
                prompt
                or ""
            )
            +
            "\n\n"
            +
            "==================================================\n"
            "AGENCY / INITIATIVE 2.0\n"
            "==================================================\n\n"
            +
            server_context
            +
            "\n\n"
            +
            (
                "Spezifischer Initiative-Impuls:\n"
                +
                special
                +
                "\n\n"
                if special
                else ""
            )
            +
            "Die Initiative soll einen echten Grund haben. "
            "Wenn Server Awareness sagt, dass Evilnae schon viel "
            "geredet hat oder die Stimmung sensibel ist, lieber "
            "NO_INITIATIVE. Keine künstliche Aktivität nur weil "
            "der Timer ausgelöst hat."
        )

    return wrapped


def _self_test() -> int:
    tests = []

    direct = AgencyResult(
        action=ACTION_REPLY,
        reason="direct_reply",
        conversation_mode=(
            MODE_DIRECT
        ),
    )

    adjusted = adjust_agency_result_v2(
        direct,
        conversation_mode=(
            MODE_DIRECT
        ),
        user_text="Evil?",
        signal={
            "bot_pressure": 1.0,
        },
    )

    tests.append(
        (
            "direct address never suppressed",
            adjusted.action
            ==
            ACTION_REPLY,
        )
    )

    continuation = AgencyResult(
        action=ACTION_REPLY,
        reason="brain_reply",
        conversation_mode=(
            MODE_CONTINUATION
        ),
    )

    adjusted = adjust_agency_result_v2(
        continuation,
        conversation_mode=(
            MODE_CONTINUATION
        ),
        user_text="ja genau",
        signal={
            "bot_pressure": 0.90,
        },
    )

    tests.append(
        (
            "high bot pressure suppresses low-value continuation",
            adjusted.action
            ==
            ACTION_STAY_SILENT,
        )
    )

    adjusted_question = (
        adjust_agency_result_v2(
            continuation,
            conversation_mode=(
                MODE_CONTINUATION
            ),
            user_text=(
                "wie meinst du das?"
            ),
            signal={
                "bot_pressure": 0.90,
            },
        )
    )

    tests.append(
        (
            "question survives bot-pressure guard",
            adjusted_question.action
            ==
            ACTION_REPLY,
        )
    )

    tests.append(
        (
            "participation hard silence for overtalking",
            _participation_should_hard_silence(
                signal={
                    "bot_pressure": 0.80,
                    "social_pull": 0.10,
                },
                current_message=(
                    "ja das ist schon wild"
                ),
            ),
        )
    )

    tests.append(
        (
            "Evilnae reference bypasses participation silence",
            not _participation_should_hard_silence(
                signal={
                    "bot_pressure": 0.80,
                    "social_pull": 0.10,
                },
                current_message=(
                    "Evil ist heute echt wild"
                ),
            ),
        )
    )

    class State:
        curiosity = 0.65
        boredom = 0.55
        social_energy = 0.65
        chaos_drive = 0.50
        irritation = 0.05
        energy = 0.70

    base = (
        initiative_module
        .calculate_initiative_score(
            State()
        )
    )

    boosted = compute_initiative_score_v2(
        State(),
        {
            "initiative_opportunity": 0.80,
            "social_pull": 0.50,
            "bot_pressure": 0.05,
            "sensitive_recent": False,
        },
    )

    tests.append(
        (
            "server opportunity can raise initiative score",
            boosted
            >
            base,
        )
    )

    suppressed = compute_initiative_score_v2(
        State(),
        {
            "initiative_opportunity": 0.20,
            "social_pull": 0.10,
            "bot_pressure": 0.90,
            "sensitive_recent": True,
        },
    )

    tests.append(
        (
            "bot pressure and sensitivity lower initiative score",
            suppressed
            <
            base,
        )
    )

    passed = sum(
        1
        for _, success
        in tests
        if success
    )

    print()
    print("=" * 64)
    print(
        f"AGENCY / INITIATIVE "
        f"v{AGENCY_INITIATIVE_V2_VERSION} TEST"
    )
    print("=" * 64)

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

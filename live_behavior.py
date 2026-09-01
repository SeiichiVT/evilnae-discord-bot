from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any


LIVE_BEHAVIOR_VERSION = "1.0"


_SECOND_PERSON = re.compile(
    r"\b(?:du|dir|dich|dein|deine|deiner|deinem|deinen|"
    r"ihr|euch|euer|eure|eurem|euren)\b",
    re.IGNORECASE,
)

_QUESTION_LEAD = re.compile(
    r"^\s*(?:warum|wieso|weshalb|was|wer|wie|wann|wo|"
    r"welche|welcher|welches|kann|können|koennen|"
    r"ist|sind|hat|haben|macht|machen)\b",
    re.IGNORECASE,
)

_CURRENT_ACTIVITY = re.compile(
    r"\b(?:was\s+machst\s+du|was\s+treibst\s+du|"
    r"was\s+zockst\s+du|was\s+spielst\s+du|"
    r"was\s+schaust\s+du|was\s+guckst\s+du|"
    r"was\s+hörst\s+du|was\s+hoerst\s+du)\b",
    re.IGNORECASE,
)

_GREETING = re.compile(
    r"^\s*(?:guten\s+morgen|morgen|moin|hallo|hey|hi|yo)\b",
    re.IGNORECASE,
)

_BOTLIKE_RECENT = re.compile(
    r"\b(?:"
    r"(?:das\s+)?klingt\s+(?:ja\s+|echt\s+|wirklich\s+)?"
    r"(?:nach|wie|spannend|interessant|gut|cool|frustrierend|nervig)|"
    r"das\s+freut\s+mich|"
    r"schön\s+zu\s+hören|schoen\s+zu\s+hoeren|"
    r"gut\s+zu\s+hören|gut\s+zu\s+hoeren|"
    r"hoffentlich|danke\s+(?:für|fuer)\s+die\s+frage"
    r")\b",
    re.IGNORECASE,
)


BOTLIKE_QUALITY_ISSUES = {
    "sounds_like_wrapper",
    "overpolite_smalltalk",
    "assistant_empathy",
    "imagined_empathy",
    "support_closure",
    "service_success",
    "generic_excited",
    "generic_validation",
    "motivational_coach",
    "bot_happy_mirror",
    "automatic_plan_agreement",
    "assistant_deserved_validation",
    "cozy_service_phrase",
    "soft_fail_wrapper",
}


def _clean(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


def _normalize(value: Any) -> str:
    text = _clean(value).lower()
    text = re.sub(
        r"<a?:[A-Za-z0-9_]+:\d+>",
        " ",
        text,
    )
    text = re.sub(
        r"[^a-z0-9äöüß]+",
        " ",
        text,
    )
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def _words(value: Any) -> list[str]:
    return re.findall(
        r"[A-Za-zÄÖÜäöüß0-9]+",
        str(value or ""),
    )


def is_nonconversational_self_answered_question(
    text: str,
) -> bool:
    value = _clean(text)

    if value.count("?") != 1:
        return False

    before, after = value.split(
        "?",
        1,
    )

    before = before.strip()
    after = after.strip()

    if (
        not before
        or not after
        or len(_words(after)) < 2
    ):
        return False

    if not _QUESTION_LEAD.search(
        before
    ):
        return False

    if _SECOND_PERSON.search(
        before
    ):
        return False

    return "?" not in after


def has_forbidden_conversational_question(
    text: str,
    *,
    allow_question: bool,
) -> bool:
    value = _clean(text)
    marks = value.count("?")

    if marks <= 0:
        return False

    if allow_question:
        return marks > 1

    if (
        marks == 1
        and
        is_nonconversational_self_answered_question(
            value
        )
    ):
        return False

    return True


def _pick_variant(
    variants,
    *,
    user_text,
    recent_evilnae_messages=None,
) -> str:
    recent = [
        _normalize(item)
        for item
        in (
            recent_evilnae_messages
            or []
        )[-10:]
        if _normalize(item)
    ]

    digest = hashlib.sha1(
        _normalize(user_text).encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()

    offset = (
        int(
            digest[:8],
            16,
        )
        %
        max(
            1,
            len(variants),
        )
    )

    ordered = (
        variants[offset:]
        +
        variants[:offset]
    )

    for candidate in ordered:
        norm = _normalize(
            candidate
        )

        if all(
            SequenceMatcher(
                None,
                norm,
                old,
            ).ratio()
            <
            0.78
            for old in recent
        ):
            return candidate

    return ordered[0]


def build_grounded_epistemic_fallback(
    user_text: str,
    *,
    is_hanae=False,
    recent_evilnae_messages=None,
) -> str:
    user = str(
        user_text
        or ""
    )

    if _CURRENT_ACTIVITY.search(
        user
    ):
        variants = [
            "gerade? ich häng hier im Discord rum.",
            "aktuell nichts Spektakuläres, ich bin einfach hier.",
            "im Moment? eher hier rumhängen als irgendwas Großes.",
            "gerade bin ich einfach hier bei euch, mehr Drama gibt's nicht.",
            "nichts, was ich gerade groß ankündigen müsste. ich bin hier.",
        ]

        if is_hanae:
            variants.extend(
                [
                    "gerade? offensichtlich mit dir hier rumhängen, sis.",
                    "im Moment bin ich einfach hier, sis. sehr exklusiv.",
                ]
            )

        return _pick_variant(
            variants,
            user_text=user,
            recent_evilnae_messages=(
                recent_evilnae_messages
            ),
        )

    if _GREETING.search(
        user
    ):
        variants = [
            "moin.",
            "morgen.",
            "yo, morgen.",
            "bin da. morgen.",
            "guten morgen, ich existiere schon.",
        ]

        if is_hanae:
            variants.append(
                "morgen, sis."
            )

        return _pick_variant(
            variants,
            user_text=user,
            recent_evilnae_messages=(
                recent_evilnae_messages
            ),
        )

    return ""


def surface_failure_directive(
    reason: str,
    rejected_candidate: str = "",
) -> str:
    reason = str(
        reason
        or ""
    ).strip()

    rejected = _clean(
        rejected_candidate
    )

    lines = [
        "[SURFACE FALLBACK RECOVERY]",
        (
            "Der lokale Surface-Entwurf wurde verworfen. "
            "Der OpenAI-Fallback darf NICHT einfach denselben Gedanken "
            "mit Synonymen nachbauen."
        ),
    ]

    if (
        "repeat" in reason
        or "recent_copy" in reason
    ):
        lines.append(
            (
                "REPETITION ESCAPE: Wechsle den sozialen/reagierenden "
                "Winkel. Nicht dieselbe Pointe, Stimmung oder Kernaussage "
                "nur neu formulieren."
            )
        )

    if any(
        marker in reason.lower()
        for marker in (
            "assistant",
            "generic",
            "wrapper",
            "bot",
        )
    ):
        lines.append(
            (
                "ANTI-BOT: Keine Service-Bestätigung, kein 'klingt nach', "
                "kein Motivations-/Support-Abschluss. Eigene Haltung zuerst."
            )
        )

    if rejected:
        lines.append(
            "NICHT NACHFORMULIEREN:\n"
            +
            rejected[:500]
        )

    return "\n\n".join(
        lines
    )


def quality_requires_personality_repair(
    analysis,
) -> bool:
    issues = set(
        str(item)
        for item
        in (
            getattr(
                analysis,
                "issues",
                [],
            )
            or []
        )
    )

    if (
        issues
        &
        BOTLIKE_QUALITY_ISSUES
    ):
        return True

    return bool(
        int(
            getattr(
                analysis,
                "generic_score",
                0,
            )
            or 0
        )
        >= 3
        or
        int(
            getattr(
                analysis,
                "repetition_score",
                0,
            )
            or 0
        )
        >= 2
        or
        int(
            getattr(
                analysis,
                "grammar_score",
                0,
            )
            or 0
        )
        >= 3
        or
        int(
            getattr(
                analysis,
                "total_penalty",
                0,
            )
            or 0
        )
        >= 5
    )


def apply_surface_variety_to_plan(
    plan,
    *,
    recent_evilnae_messages,
    user_text: str,
):
    recent = [
        _clean(item)
        for item
        in (
            recent_evilnae_messages
            or []
        )[-8:]
        if _clean(item)
    ]

    if not recent:
        return plan

    must_avoid = list(
        getattr(
            plan,
            "must_avoid",
            [],
        )
        or []
    )

    opener_counts = {}

    for item in recent[-5:]:
        match = re.match(
            r"^\s*(ich|bin|das|ja|mhm|morgen|okay|ok|also)\b",
            item,
            re.IGNORECASE,
        )

        if match:
            opener = (
                match.group(1)
                .lower()
            )

            opener_counts[
                opener
            ] = opener_counts.get(
                opener,
                0,
            ) + 1

    for opener, count in opener_counts.items():
        if count >= 2:
            must_avoid.append(
                (
                    "Rhythmus wechseln: nicht schon wieder "
                    f"mit '{opener}' eröffnen"
                )
            )

    if any(
        _BOTLIKE_RECENT.search(
            item
        )
        for item in recent[-6:]
    ):
        must_avoid.append(
            (
                "keine 'klingt nach'/Support-/Service-Verpackung; "
                "eigene Reaktion oder Haltung statt Bestätigung"
            )
        )

    short_declaratives = sum(
        1
        for item in recent[-4:]
        if (
            len(_words(item)) <= 10
            and
            "?" not in item
        )
    )

    if short_declaratives >= 3:
        must_avoid.append(
            (
                "nicht wieder denselben kurzen Aussagesatz-Rhythmus; "
                "Satzbau/Opener natürlich variieren, ohne Stimmung zu erfinden"
            )
        )

    unique = []

    for item in must_avoid:
        item = str(
            item
            or ""
        ).strip()

        if (
            item
            and
            item not in unique
        ):
            unique.append(
                item
            )

    try:
        plan.must_avoid = unique[:18]
    except Exception:
        pass

    return plan


def _self_test() -> int:
    from types import SimpleNamespace

    tests = []

    joke = (
        "Warum können Skelette keine Lügen erzählen? "
        "Weil ihnen das Rückgrat fehlt."
    )

    tests.append(
        (
            "self-answered joke allowed",
            is_nonconversational_self_answered_question(
                joke
            )
            and
            not has_forbidden_conversational_question(
                joke,
                allow_question=False,
            ),
        )
    )

    tests.append(
        (
            "real counterquestion blocked",
            has_forbidden_conversational_question(
                "Und wie geht es dir?",
                allow_question=False,
            ),
        )
    )

    tests.append(
        (
            "second-person question not rhetorical escape",
            not is_nonconversational_self_answered_question(
                "Was machst du? Ich chille."
            ),
        )
    )

    activity = build_grounded_epistemic_fallback(
        "Was machst du gerade?",
    )

    tests.append(
        (
            "grounded activity fallback",
            bool(activity)
            and
            not re.search(
                r"\b(?:elden|valorant|warzone|chainsaw|minecraft)\b",
                activity,
                re.IGNORECASE,
            ),
        )
    )

    tests.append(
        (
            "unrelated knowledge has no canned fallback",
            build_grounded_epistemic_fallback(
                "Kennst du Person X?"
            )
            ==
            "",
        )
    )

    directive = surface_failure_directive(
        "surface_near_recent_copy",
        "Morgen, läuft.",
    )

    tests.append(
        (
            "repetition fallback changes angle",
            "Wechsle den sozialen/reagierenden Winkel"
            in directive
            and
            "NICHT NACHFORMULIEREN"
            in directive,
        )
    )

    analysis = SimpleNamespace(
        issues=[
            "sounds_like_wrapper",
        ],
        generic_score=2,
        repetition_score=0,
        grammar_score=0,
        total_penalty=2,
    )

    tests.append(
        (
            "botlike low penalty still repairs",
            quality_requires_personality_repair(
                analysis
            ),
        )
    )

    plan = SimpleNamespace(
        must_avoid=[],
    )

    apply_surface_variety_to_plan(
        plan,
        recent_evilnae_messages=[
            "Ich bin da.",
            "Ich bin wach.",
            "Ich bin halt hier.",
        ],
        user_text="yo",
    )

    tests.append(
        (
            "repeated opener creates variety pressure",
            any(
                "nicht schon wieder"
                in item
                for item in plan.must_avoid
            ),
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
        f"LIVE BEHAVIOR v"
        f"{LIVE_BEHAVIOR_VERSION} TEST"
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

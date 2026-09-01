from __future__ import annotations

import contextvars
import functools
import os
import re
from typing import Any

from participation import ParticipationDecision
from character_state import extract_character_states
from local_voice import LocalVoiceResult

from social_emotional_state import (
    SOCIAL_EMOTIONAL_STATE_VERSION,
    observe_social_interaction,
    get_social_state,
    format_social_state_for_prompt,
    format_social_state_debug,
    apply_social_state_to_plan,
    social_state_stats,
)


from experience_learning import (
    EXPERIENCE_LEARNING_VERSION,
    register_salience_result,
    capture_experience,
    format_experience_for_reflection,
    gate_reflection_learning,
    annotate_reflection_record,
    experience_stats,
    format_experience_debug,
)


from self_development import (
    SELF_DEVELOPMENT_VERSION,
    observe_development_from_experience,
    observe_development_from_reflection,
    format_self_development_for_prompt,
    register_arc_surface_use,
    self_development_stats,
    format_self_development_debug,
)


LIVE_STABILITY_VERSION = "1.5-turn-console-latency"
CONSOLE_OUTPUT_VERSION = "1.1-turn-summary"

_CURRENT_USER_TEXT = contextvars.ContextVar(
    "evilnae_live_user_text",
    default="",
)

_CURRENT_USERNAME = contextvars.ContextVar(
    "evilnae_live_username",
    default="unknown",
)

_CURRENT_USER_ID = contextvars.ContextVar(
    "evilnae_live_user_id",
    default="",
)

_SURFACE_FAILED = contextvars.ContextVar(
    "evilnae_surface_failed",
    default=False,
)


# =========================================================
# COMPACT TERMINAL
# =========================================================

def get_console_mode() -> str:
    mode = str(
        os.getenv(
            "EVILNAE_CONSOLE_MODE",
            "compact",
        )
        or "compact"
    ).strip().lower()

    if mode not in {
        "compact",
        "quiet",
        "debug",
    }:
        mode = "compact"

    return mode


class ConsoleOutputFilter:
    """Filter only terminal output; file logging remains untouched."""

    def __init__(self):
        self._buffer = ""
        self._traceback_budget = 0

    def _errorish(self, line: str) -> bool:
        value = line.lower()

        return bool(
            "[error" in value
            or "[warn" in value
            or " error " in value
            or " warning " in value
            or value.startswith("error:")
            or value.startswith("warning:")
        )

    def _show_compact(self, line: str) -> bool:
        stripped = line.strip()

        if not stripped:
            return False

        if stripped.startswith(
            (
                "[LIVE IN]",
                "[TURN]",
                "[SILENT FINAL]",
                "[AGENCY APPLICATION REACTION]",
                "[LIVE GUARD]",
                "[LIVE WARN]",
                "[AUTO FILE LOGGING]",
                "[LOCAL VOICE WARM]",
            )
        ):
            return True

        if self._errorish(stripped):
            return True

        startup_prefixes = (
            "Evilnae ist online als ",
            "Bot Version:",
            "Live Stability v",
            "Compact Console v",
            "Response Planner v",
            "Conversation Episodes v",
            "Emotional Salience v",
            "Social Emotional State v",
            "Experience Learning v",
            "Self Development v",
            "Server Awareness v",
            "Agency / Initiative v",
            "Response Agency v",
            "Turn Runtime v",
            "Qwen Surface Writer v",
            "Output Quality v",
            "Routing Hardening v",
            "Character Foundation v",
            "Foundation Entries:",
            "Character Learning v",
            "Character Current State v",
            "Local Voice v",
            "Voice Memory v",
        )

        if stripped.startswith(
            startup_prefixes
        ):
            return True

        if stripped.startswith(
            "Traceback (most recent call last):"
        ):
            self._traceback_budget = 24
            return True

        if self._traceback_budget > 0:
            self._traceback_budget -= 1
            return True

        return False

    def _show_quiet(self, line: str) -> bool:
        stripped = line.strip()

        if not stripped:
            return False

        if stripped.startswith(
            (
                "[LIVE OUT]",
                "[LIVE WARN]",
                "[AUTO FILE LOGGING]",
                "Evilnae ist online als ",
                "Bot Version:",
            )
        ):
            return True

        if self._errorish(stripped):
            return True

        if stripped.startswith(
            "Traceback (most recent call last):"
        ):
            self._traceback_budget = 24
            return True

        if self._traceback_budget > 0:
            self._traceback_budget -= 1
            return True

        return False

    def _show_line(self, line: str) -> bool:
        mode = get_console_mode()

        if mode == "debug":
            return True

        if mode == "quiet":
            return self._show_quiet(line)

        return self._show_compact(line)

    def filter_chunk(self, chunk: str) -> str:
        value = str(
            chunk
            if chunk is not None
            else ""
        )

        if get_console_mode() == "debug":
            return value

        self._buffer += value
        output = []

        while "\n" in self._buffer:
            line, self._buffer = (
                self._buffer.split(
                    "\n",
                    1,
                )
            )

            if self._show_line(line):
                output.append(
                    line + "\n"
                )

        return "".join(output)

    def flush_pending(self) -> str:
        if not self._buffer:
            return ""

        pending = self._buffer
        self._buffer = ""

        return (
            pending
            if self._show_line(pending)
            else ""
        )


# =========================================================
# TEXT HELPERS
# =========================================================

STOPWORDS = {
    "aber", "also", "auch", "auf", "aus", "bei", "bin", "bist",
    "das", "dass", "dein", "deine", "dem", "den", "der", "die",
    "dir", "dich", "du", "ein", "eine", "einen", "er", "es",
    "für", "fuer", "hab", "habe", "hat", "ich", "im", "in",
    "ist", "ja", "mal", "mein", "meine", "mit", "nach", "nicht",
    "noch", "nur", "oder", "schon", "sie", "so", "und", "uns",
    "von", "war", "was", "wie", "wir", "zu", "zum", "zur",
    "gerade", "grad", "jetzt", "heute", "eigentlich", "denn",
    "dann", "wenn", "weil", "mir", "mich", "ihr", "ihre",
}


def _normalize(text: Any) -> str:
    value = str(
        text
        or ""
    ).lower()

    value = re.sub(
        r"<a?:[A-Za-z0-9_]+:\d+>",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9äöüß]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _words(text: Any) -> list[str]:
    return re.findall(
        r"[A-Za-zÄÖÜäöüß0-9]+",
        str(text or "").lower(),
    )


def _tokens(text: Any) -> set[str]:
    return {
        token
        for token in _words(text)
        if (
            len(token) >= 3
            and token not in STOPWORDS
        )
    }


def _short(text: Any, limit: int = 180) -> str:
    value = re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()

    if len(value) <= limit:
        return value

    return value[: limit - 3] + "..."


def _merge_unique(
    original,
    additions,
    *,
    limit=16,
):
    result = []

    for group in (
        original or [],
        additions or [],
    ):
        for item in group:
            value = str(
                item
                or ""
            ).strip()

            if (
                value
                and value not in result
            ):
                result.append(value)

            if len(result) >= limit:
                return result

    return result


# =========================================================
# SELF-STATE AUTHORITY 2.0
# =========================================================

SELF_STATE_WORDS = (
    "müde",
    "muede",
    "verschlafen",
    "verwirrt",
    "durcheinander",
    "planlos",
    "beschäftigt",
    "beschaeftigt",
    "krank",
    "kopfschmerzen",
    "hungrig",
    "traurig",
    "sauer",
    "genervt",
)

SELF_STATE_USER_PATTERN = re.compile(
    r"\b(?:"
    r"du\s+(?:bist|wirkst)\s+"
    r"|bist\s+du\s+"
    r"|wirkst\s+du\s+"
    r")"
    r"(?:(?:heute|gerade|grad|irgendwie|echt|wirklich|"
    r"voll|total|ziemlich|so)\s+){0,4}"
    r"(?P<state>"
    + "|".join(SELF_STATE_WORDS)
    + r")\b",
    re.IGNORECASE,
)

FIRST_PERSON_STATE_PATTERNS = {
    "müde": re.compile(
        r"\bich\s+bin\s+.*\bmüde\b",
        re.I,
    ),
    "muede": re.compile(
        r"\bich\s+bin\s+.*\bmuede\b",
        re.I,
    ),
    "verschlafen": re.compile(
        r"\bich\s+.*\bverschlafen\b",
        re.I,
    ),
    "verwirrt": re.compile(
        r"\bich\s+bin\s+.*\bverwirrt\b",
        re.I,
    ),
    "durcheinander": re.compile(
        r"\bich\s+bin\s+.*\bdurcheinander\b",
        re.I,
    ),
    "planlos": re.compile(
        r"\bich\s+.*\bplanlos\b",
        re.I,
    ),
    "beschäftigt": re.compile(
        r"\bich\s+bin\s+.*\bbeschäftigt\b",
        re.I,
    ),
    "beschaeftigt": re.compile(
        r"\bich\s+bin\s+.*\bbeschaeftigt\b",
        re.I,
    ),
    "krank": re.compile(
        r"\bich\s+bin\s+.*\bkrank\b",
        re.I,
    ),
    "kopfschmerzen": re.compile(
        r"\bich\s+hab(?:e)?\s+.*\bkopfschmerzen\b",
        re.I,
    ),
    "hungrig": re.compile(
        r"\bich\s+bin\s+.*\bhungrig\b",
        re.I,
    ),
    "traurig": re.compile(
        r"\bich\s+bin\s+.*\btraurig\b",
        re.I,
    ),
    "sauer": re.compile(
        r"\bich\s+bin\s+.*\bsauer\b",
        re.I,
    ),
    "genervt": re.compile(
        r"\bich\s+bin\s+.*\bgenervt\b",
        re.I,
    ),
}


def _grounded(
    state_word: str,
    *,
    inner_state_guidance: str = "",
    evidence_context: str = "",
    response_plan_text: str = "",
) -> bool:
    needle = _normalize(
        state_word
    )

    # Only actual state/evidence may ground a current self-state.
    # The Response Plan can mention a state merely to FORBID adopting it.
    authority = _normalize(
        " ".join(
            (
                inner_state_guidance or "",
                evidence_context or "",
            )
        )
    )

    return bool(
        needle
        and needle in authority
    )


def adopts_ungrounded_user_state(
    *,
    user_text: str,
    candidate: str,
    inner_state_guidance: str = "",
    evidence_context: str = "",
    response_plan_text: str = "",
) -> bool:
    match = SELF_STATE_USER_PATTERN.search(
        str(user_text or "")
    )

    if not match:
        return False

    state_word = (
        match.group("state")
        .lower()
    )

    pattern = (
        FIRST_PERSON_STATE_PATTERNS.get(
            state_word
        )
    )

    if not pattern:
        return False

    if not pattern.search(
        str(candidate or "")
    ):
        return False

    return not _grounded(
        state_word,
        inner_state_guidance=(
            inner_state_guidance
        ),
        evidence_context=(
            evidence_context
        ),
        response_plan_text=(
            response_plan_text
        ),
    )


# =========================================================
# CARE / SENSITIVE CONTEXT
# =========================================================

CARE_CONTEXT_PATTERN = re.compile(
    r"\b(?:"
    r"kopfschmerz(?:en)?|migräne|migraene|"
    r"schmerzen|krank|fieber|"
    r"mir\s+geht(?:'|’)?s\s+nicht\s+gut|"
    r"geht\s+es\s+(?:ihr|ihm)\s+nicht\s+gut|"
    r"bitte\s+leiser|sei\s+bitte\s+leiser|"
    r"kümmer(?:e)?\s+dich|kuemmer(?:e)?\s+dich|"
    r"ruh\s+dich\s+aus|ausruhen"
    r")\b",
    re.IGNORECASE,
)

PRACTICAL_HELP_PATTERN = re.compile(
    r"\b(?:"
    r"tee\s+(?:machen|mach|bringen)|"
    r"mach(?:st)?\s+.*\btee\b|"
    r"bring(?:st)?\s+.*\b(?:tee|trinken|wasser)\b|"
    r"kümmer(?:e)?\s+dich|kuemmer(?:e)?\s+dich|"
    r"bitte\s+leiser|sei\s+bitte\s+leiser"
    r")\b",
    re.IGNORECASE,
)


# =========================================================
# INTENT FULFILLMENT
# =========================================================

HOW_ARE_YOU_PATTERN = re.compile(
    r"\b(?:wie\s+geht(?:'|’)?s\s+dir|"
    r"wie\s+geht\s+es\s+dir|"
    r"wie\s+gehts\s+dir)\b",
    re.IGNORECASE,
)

FOOD_HISTORY_PATTERN = re.compile(
    r"\b(?:was\s+hast\s+du(?:\s+heute)?\s+(?:alles\s+)?gegessen|"
    r"was\s+du\s+alles\s+heute\s+gegessen)\b",
    re.IGNORECASE,
)

CURRENT_ACTIVITY_PATTERN = re.compile(
    r"\b(?:was\s+machst\s+du|was\s+treibst\s+du|"
    r"was\s+zockst\s+du|was\s+spielst\s+du|"
    r"was\s+schaust\s+du|was\s+guckst\s+du)\b",
    re.IGNORECASE,
)

MUSIC_PREFERENCE_PATTERN = re.compile(
    r"\b(?:welche\s+musik|was\s+für\s+musik|"
    r"was\s+fuer\s+musik|musikart\s+hörst\s+du|"
    r"musikart\s+hoerst\s+du)\b",
    re.IGNORECASE,
)

DIRECT_REQUEST_PATTERN = re.compile(
    r"\b(?:kannst\s+du|könntest\s+du|koenntest\s+du|"
    r"mach\s+mir|mach\s+ihr|bring\s+mir|bring\s+ihr|"
    r"kümmer(?:e)?\s+dich|kuemmer(?:e)?\s+dich|"
    r"sei\s+bitte)\b",
    re.IGNORECASE,
)

SELF_INTENTION_QUERY_PATTERN = re.compile(
    r"\b(?:trollst\s+du|willst\s+du|"
    r"möchtest\s+du|moechtest\s+du|"
    r"hast\s+du\s+vor|"
    r"bist\s+du\s+beschäftigt|"
    r"bist\s+du\s+beschaeftigt)\b",
    re.IGNORECASE,
)

NONANSWER_UNCERTAINTY_PATTERN = re.compile(
    r"\b(?:weiß\s+ich\s+(?:grad|gerade)?\s*nicht\s+sicher|"
    r"weiss\s+ich\s+(?:grad|gerade)?\s*nicht\s+sicher|"
    r"bin\s+mir\s+(?:grad|gerade)?\s*nicht\s+sicher|"
    r"keine\s+ahnung,?\s+das\s+(?:ändert|aendert)\s+sich|"
    r"ka,?\s+ob\s+ich)\b",
    re.IGNORECASE,
)


def intent_violation_reason(
    user_text: str,
    candidate: str,
) -> str:
    user = str(
        user_text
        or ""
    )

    answer = str(
        candidate
        or ""
    )

    if not _normalize(answer):
        return "empty_answer"

    if HOW_ARE_YOU_PATTERN.search(user):
        if not re.search(
            r"\b(?:mir\s+geht|geht\s+so|"
            r"geht\s+(?:mir\s+)?(?:gut|okay|schlecht)|"
            r"ich\s+bin|bin\s+(?:gut|okay|fit|wach|"
            r"müde|muede|entspannt|genervt)|"
            r"alles\s+(?:gut|okay)|ganz\s+(?:gut|okay))\b",
            answer,
            re.IGNORECASE,
        ):
            return "intent_how_are_you_not_answered"

    if FOOD_HISTORY_PATTERN.search(user):
        if not re.search(
            r"\b(?:gegessen|esse|essen|frühstück|fruehstueck|"
            r"mittag|abendessen|snack|nudel|pizza|brot|toast|"
            r"müsli|muesli|reis|pasta|burger|döner|doener|"
            r"nugget|suppe|salat|noch\s+nichts|"
            r"nichts\s+gegessen|weiß\s+ich\s+nicht|"
            r"weiss\s+ich\s+nicht)\b",
            answer,
            re.IGNORECASE,
        ):
            return "intent_food_history_not_answered"

    if CURRENT_ACTIVITY_PATTERN.search(user):
        if not re.search(
            r"\b(?:ich\s+(?:zock|zocke|spiel|spiele|schau|"
            r"schaue|guck|gucke|scroll|scrolle|hör|höre|"
            r"hoer|hoere|les|lese|koch|koche|ess|esse|"
            r"trink|trinke|arbeite|chill|hänge|haenge|"
            r"mach|mache)|"
            r"bin\s+(?:gerade|grad)\s+(?:am|beim|auf|in))\b",
            answer,
            re.IGNORECASE,
        ):
            return "intent_current_activity_not_answered"

    if DIRECT_REQUEST_PATTERN.search(user):
        if NONANSWER_UNCERTAINTY_PATTERN.search(
            answer
        ):
            return "intent_request_uncertainty"

        if not re.search(
            r"\b(?:klar|ja|jap|jo|okay|ok|mach|mache|"
            r"komm|komme|bring|bringe|kann\s+ich|"
            r"versuch|versuche|leiser|kümmere|kuemmere|"
            r"nein|nee|nö|noe|geht\s+(?:grad|gerade)\s+nicht|"
            r"später|spaeter)\b",
            answer,
            re.IGNORECASE,
        ):
            return "intent_request_not_answered"

    if SELF_INTENTION_QUERY_PATTERN.search(user):
        if NONANSWER_UNCERTAINTY_PATTERN.search(
            answer
        ):
            return "intent_self_intention_uncertainty"

    if MUSIC_PREFERENCE_PATTERN.search(user):
        if re.search(
            r"\b(?:gehört|gehoert)\s+mir\s+eher\s+zu\b",
            answer,
            re.IGNORECASE,
        ):
            return "intent_music_malformed"

    return ""


# =========================================================
# SEMANTIC SANITY
# =========================================================

MALFORMED_PATTERNS = (
    (
        "semantic_bruederin",
        re.compile(
            r"\bbrüderin\b|\bbruederin\b",
            re.IGNORECASE,
        ),
    ),
    (
        "semantic_die_gps",
        re.compile(
            r"\bdie\s+gps\b",
            re.IGNORECASE,
        ),
    ),
    (
        "semantic_gehoert_mir_zu",
        re.compile(
            r"\b(?:gehört|gehoert)\s+mir\s+eher\s+zu\b",
            re.IGNORECASE,
        ),
    ),
    (
        "semantic_busy_tea_logic",
        re.compile(
            r"\bich\s+mach(?:e|'|’)?\s+.{0,35}\btee\b"
            r".{0,35}\bwenn\s+ich\s+beschäftigt\s+bin\b",
            re.IGNORECASE,
        ),
    ),
)


def semantic_violation_reason(
    candidate: str,
    *,
    user_text: str = "",
    inner_state_guidance: str = "",
    evidence_context: str = "",
    response_plan_text: str = "",
) -> str:
    answer = str(
        candidate
        or ""
    )

    for name, pattern in MALFORMED_PATTERNS:
        if pattern.search(answer):
            return name

    if adopts_ungrounded_user_state(
        user_text=user_text,
        candidate=answer,
        inner_state_guidance=(
            inner_state_guidance
        ),
        evidence_context=(
            evidence_context
        ),
        response_plan_text=(
            response_plan_text
        ),
    ):
        return "semantic_ungrounded_self_state"

    return intent_violation_reason(
        user_text,
        answer,
    )


# =========================================================
# CONCEPT REPETITION
# =========================================================

CONCEPT_PATTERNS = {
    "confusion_loop": re.compile(
        r"\b(?:verwirrt|durcheinander|planlos|"
        r"in\s+gedanken\s+abdrift|im\s+nebel|"
        r"verschlafen|schlecht\s+eingeschlafen)\b",
        re.IGNORECASE,
    ),
    "uncertainty_loop": re.compile(
        r"\b(?:nicht\s+sicher|"
        r"weiß\s+ich\s+(?:grad|gerade)?\s*nicht|"
        r"weiss\s+ich\s+(?:grad|gerade)?\s*nicht|"
        r"keine\s+ahnung|ka,?\s+ob)\b",
        re.IGNORECASE,
    ),
    "food_boss_loop": re.compile(
        r"\b(?:boss.{0,24}fressen|"
        r"fressen.{0,24}boss|"
        r"keine\s+halben\s+sachen.{0,20}fressen)\b",
        re.IGNORECASE,
    ),
    "morning_flat_loop": re.compile(
        r"\b(?:aufgestanden.{0,20}chill|"
        r"morgen,?\s+(?:läuft|laeuft))\b",
        re.IGNORECASE,
    ),
}


def repeated_concepts(
    candidate: str,
    recent_messages,
) -> list[str]:
    result = []

    for name, pattern in (
        CONCEPT_PATTERNS.items()
    ):
        if not pattern.search(
            str(candidate or "")
        ):
            continue

        if any(
            pattern.search(
                str(message or "")
            )
            for message
            in list(
                recent_messages
                or []
            )[-12:]
        ):
            result.append(name)

    return result


def _user_echo_ratio(
    user_text: str,
    candidate: str,
) -> float:
    user_tokens = _tokens(
        user_text
    )

    candidate_tokens = _tokens(
        candidate
    )

    if (
        len(user_tokens) < 3
        or len(candidate_tokens) < 3
    ):
        return 0.0

    return len(
        user_tokens
        &
        candidate_tokens
    ) / max(
        1,
        len(candidate_tokens),
    )


# =========================================================
# EPISODE / THREAD RELEVANCE
# =========================================================

SHORT_CONTINUATION_PATTERN = re.compile(
    r"^\s*(?:ich\s+glaube\s+beides|beides|richtig|genau|"
    r"stimmt|true|same|hä+|hae+|was\??|wieso\??|warum\??|"
    r"wie\s+meinst\s+du(?:\s+das)?\??|"
    r"was\s+meinst\s+du\??|"
    r"brüderin\s+was\??|bruederin\s+was\??|"
    r"nö|noe|nee|nein|aber\s+.*|deshalb\s+.*)"
    r"\s*[!.?]*\s*$",
    re.IGNORECASE,
)

BOT_REFERENCE_PATTERN = re.compile(
    r"\b(?:der\s+bot|die\s+bot|bott)\b",
    re.IGNORECASE,
)

PRONOUN_REPLY_PATTERN = re.compile(
    r"^\s*(?:ich\s+glaube\s+(?:sie|beides)|"
    r"sie\s+(?:ist|war|braucht|hat|kann)|"
    r"ihr\s+(?:geht|ist))\b",
    re.IGNORECASE,
)


def _item_content(item) -> str:
    if not isinstance(item, dict):
        return ""

    return str(
        item.get(
            "content",
            "",
        )
        or ""
    )


def filter_episode_snapshot(
    channel_snapshot,
    *,
    limit=12,
):
    items = list(
        channel_snapshot
        or []
    )

    if len(items) <= 5:
        return items[-limit:]

    current = items[-1]
    current_text = _item_content(
        current
    )

    if (
        len(_words(current_text)) <= 5
        or SHORT_CONTINUATION_PATTERN.search(
            current_text
        )
    ):
        return items[-5:]

    current_tokens = _tokens(
        current_text
    )

    keep_indices = set(
        range(
            max(
                0,
                len(items) - 3,
            ),
            len(items),
        )
    )

    current_user = str(
        current.get(
            "user_id",
            "",
        )
        or ""
    )

    for index in range(
        len(items) - 4,
        -1,
        -1,
    ):
        if len(keep_indices) >= min(
            limit,
            7,
        ):
            break

        item = items[index]
        overlap = (
            current_tokens
            &
            _tokens(
                _item_content(item)
            )
        )

        same_user = (
            current_user
            and str(
                item.get(
                    "user_id",
                    "",
                )
                or ""
            )
            ==
            current_user
        )

        is_bot = (
            str(
                item.get(
                    "type",
                    "",
                )
            )
            ==
            "bot"
        )

        if (
            overlap
            or (
                same_user
                and len(keep_indices) < 5
            )
            or (
                is_bot
                and len(keep_indices) < 4
            )
        ):
            keep_indices.add(
                index
            )

    return [
        items[index]
        for index in sorted(
            keep_indices
        )
    ][-limit:]


def _recent_context_mentions_evilnae(
    channel_context: str,
) -> bool:
    return bool(
        re.search(
            r"\bEvilnae\b",
            str(
                channel_context
                or ""
            )[-1200:],
            re.IGNORECASE,
        )
    )


def implicit_evilnae_continuation(
    *,
    current_message: str,
    channel_context: str,
    recent_evilnae_messages,
) -> bool:
    text = str(
        current_message
        or ""
    ).strip()

    if (
        not text
        or not recent_evilnae_messages
        or not _recent_context_mentions_evilnae(
            channel_context
        )
    ):
        return False

    word_count = len(
        _words(text)
    )

    if (
        word_count <= 14
        and SHORT_CONTINUATION_PATTERN.search(
            text
        )
    ):
        return True

    if (
        word_count <= 16
        and (
            BOT_REFERENCE_PATTERN.search(
                text
            )
            or PRONOUN_REPLY_PATTERN.search(
                text
            )
        )
    ):
        return True

    return False


# =========================================================
# CHARACTER STATE WRITE GUARD
# =========================================================

SUSPICIOUS_STATE_ANSWER_PATTERN = re.compile(
    r"\b(?:ich\s+(?:schau|schaue|guck|gucke)\s+mal,?\s+ob|"
    r"warte,?\s+ich\s+(?:schau|schaue|guck|gucke)\s+mal|"
    r"was\s+brauchbares\s+finden|"
    r"bin\s+mir\s+(?:grad|gerade)?\s*nicht\s+sicher|"
    r"weiß\s+ich\s+(?:grad|gerade)?\s*nicht\s+sicher|"
    r"weiss\s+ich\s+(?:grad|gerade)?\s*nicht\s+sicher|"
    r"in\s+gedanken\s+abdrift|planlos\s+rumeier|"
    r"ich\s+(?:überlege|ueberlege)\s+mal)\b",
    re.IGNORECASE,
)

SUSPICIOUS_ACTIVITY_VALUE_PATTERN = re.compile(
    r"^(?:mal,?\s+ob|ob\s+ich|"
    r"was\s+brauchbares|mir\s+.*|nach\s+.*)",
    re.IGNORECASE,
)


def state_write_block_reason(
    answer: str,
) -> str:
    text = str(
        answer
        or ""
    )

    if SUSPICIOUS_STATE_ANSWER_PATTERN.search(
        text
    ):
        return "low_confidence_meta_activity"

    for category, value in (
        extract_character_states(
            text
        )
    ):
        if (
            category == "activity"
            and SUSPICIOUS_ACTIVITY_VALUE_PATTERN.search(
                str(value or "")
            )
        ):
            return "ambiguous_activity_capture"

    return ""


# =========================================================
# WRAPPERS
# =========================================================

def wrap_perceive_message(
    original,
):
    @functools.wraps(original)
    async def wrapped(
        *args,
        **kwargs,
    ):
        result = await original(
            *args,
            **kwargs,
        )

        username = str(
            getattr(
                result,
                "username",
                "unknown",
            )
            or "unknown"
        )

        user_id = str(
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
            or getattr(
                result,
                "raw_content",
                "",
            )
            or ""
        ).strip()

        _CURRENT_USERNAME.set(
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
            print(
                "[LIVE IN] "
                f"{username}: "
                f"{_short(text)}"
            )

        return result

    return wrapped


def wrap_response_planner(
    original,
):
    @functools.wraps(original)
    def wrapped(
        *args,
        **kwargs,
    ):
        plan = original(
            *args,
            **kwargs,
        )

        user_text = str(
            kwargs.get(
                "user_text",
                "",
            )
            or _CURRENT_USER_TEXT.get()
            or ""
        )

        _CURRENT_USER_TEXT.set(
            user_text
        )

        additions = []

        direct_intent = bool(
            HOW_ARE_YOU_PATTERN.search(
                user_text
            )
            or FOOD_HISTORY_PATTERN.search(
                user_text
            )
            or CURRENT_ACTIVITY_PATTERN.search(
                user_text
            )
            or MUSIC_PREFERENCE_PATTERN.search(
                user_text
            )
            or DIRECT_REQUEST_PATTERN.search(
                user_text
            )
            or SELF_INTENTION_QUERY_PATTERN.search(
                user_text
            )
        )

        if direct_intent:
            additions.extend(
                [
                    "aktuelle direkte Frage/Bitte zuerst konkret beantworten",
                    "nicht auf einen älteren Episode-Nebengedanken ausweichen",
                    "bei eigenem Verhalten/Zustand keine vage 'weiß ich nicht sicher'-Antwort",
                ]
            )

        state_match = (
            SELF_STATE_USER_PATTERN.search(
                user_text
            )
        )

        if state_match:
            state_word = (
                state_match.group(
                    "state"
                )
            )

            plan.core_thought = (
                "Auf die Beobachtung des Users reagieren, "
                f"ohne '{state_word}' als bestätigten Selbstzustand "
                "zu übernehmen. Der echte Inner/Current State hat Vorrang. "
                "Wenn der Zustand nicht belegt ist, locker widersprechen "
                "oder neutral bleiben."
            )

            additions.extend(
                [
                    "User-Spekulation über Evilnaes Zustand nicht als Fakt übernehmen",
                    "Müdigkeit/Verwirrung/Beschäftigung/Krankheit nur aus echtem Inner/Current State behaupten",
                ]
            )

            if getattr(
                plan,
                "stance",
                "",
            ) in {
                "confused",
                "annoyed",
            }:
                plan.stance = "playful"

        if CARE_CONTEXT_PATTERN.search(
            user_text
        ):
            plan.banter_intensity = min(
                float(
                    getattr(
                        plan,
                        "banter_intensity",
                        0.0,
                    )
                    or 0.0
                ),
                0.12,
            )

            plan.warmth_intensity = max(
                float(
                    getattr(
                        plan,
                        "warmth_intensity",
                        0.0,
                    )
                    or 0.0
                ),
                0.66,
            )

            if getattr(
                plan,
                "social_move",
                "",
            ) in {
                "roast",
                "tease",
                "counter",
                "challenge",
                "curious_tease",
            }:
                plan.social_move = "support"

            if getattr(
                plan,
                "stance",
                "",
            ) in {
                "smug",
                "competitive",
                "annoyed",
            }:
                plan.stance = "warm"

            additions.extend(
                [
                    "bei Schmerzen/Unwohlsein nicht gegen eine einfache Hilfe-Bitte argumentieren",
                    "Rücksicht/Hilfe zuerst; Humor darf die Hilfe nicht untergraben",
                ]
            )

            if PRACTICAL_HELP_PATTERN.search(
                user_text
            ):
                plan.core_thought = (
                    "Die praktische Bitte direkt beantworten "
                    "und Rücksicht zeigen. Keine Gaming-/Chaos-Ausrede "
                    "gegen Schmerzen oder Unwohlsein stellen."
                )

        recent = list(
            kwargs.get(
                "recent_evilnae_messages",
                None,
            )
            or []
        )

        repeated = []

        for name, pattern in (
            CONCEPT_PATTERNS.items()
        ):
            count = sum(
                1
                for message in recent[-12:]
                if pattern.search(
                    str(message or "")
                )
            )

            if count >= 2:
                repeated.append(
                    name
                )

        if repeated:
            additions.append(
                "bereits wiederholte Antwortidee komplett verlassen; nicht nur Synonyme austauschen"
            )

            additions.extend(
                f"Konzept nicht erneut benutzen: {name}"
                for name in repeated
            )

        plan.must_avoid = _merge_unique(
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

    return wrapped


def wrap_participation_brain(
    original,
):
    @functools.wraps(original)
    async def wrapped(
        *args,
        **kwargs,
    ):
        current_message = str(
            kwargs.get(
                "current_message",
                "",
            )
            or ""
        )

        channel_context = str(
            kwargs.get(
                "channel_context",
                "",
            )
            or ""
        )

        recent = list(
            kwargs.get(
                "recent_evilnae_messages",
                None,
            )
            or []
        )

        if implicit_evilnae_continuation(
            current_message=(
                current_message
            ),
            channel_context=(
                channel_context
            ),
            recent_evilnae_messages=(
                recent
            ),
        ):
            print(
                "[LIVE GUARD] "
                "implicit reply ownership -> Evilnae"
            )

            return ParticipationDecision(
                action="join",
                confidence="high",
                relevance=0.90,
                social_value=0.58,
                conversation_involvement=0.96,
                reason=(
                    "implicit_recent_evilnae_continuation"
                ),
                response_goal=(
                    "Auf die unmittelbare Fortsetzung "
                    "des vorherigen Evilnae-Turns reagieren."
                ),
                notes=[
                    "implicit_thread_ownership",
                ],
            )

        user_id = str(
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
                + "\n\n"
                + social_context
            ).strip()

        return await original(
            *args,
            **kwargs,
        )

    return wrapped


def wrap_reference_context(
    original,
):
    @functools.wraps(original)
    def wrapped(
        user_text,
        channel_snapshot,
        *args,
        **kwargs,
    ):
        result = original(
            user_text,
            channel_snapshot,
            *args,
            **kwargs,
        )

        if (
            SHORT_CONTINUATION_PATTERN.search(
                str(user_text or "")
            )
            and channel_snapshot
        ):
            result = (
                str(result)
                +
                "\n\n"
                "[IMMEDIATE REPLY OWNERSHIP]\n"
                "- Kurze Reaktionen wie 'beides', 'richtig', 'hä?' "
                "oder 'was meinst du?' gehören wahrscheinlich zum "
                "unmittelbar vorherigen Turn.\n"
                "- Wenn dieser Turn von Evilnae stammt, ist Evilnae "
                "weiterhin die Gesprächspartnerin, auch ohne Namen."
            )

        return result

    return wrapped


def wrap_episode_focus(
    original,
):
    @functools.wraps(original)
    def wrapped(
        channel_snapshot,
        *args,
        **kwargs,
    ):
        limit = int(
            kwargs.get(
                "limit",
                12,
            )
            or 12
        )

        filtered = (
            filter_episode_snapshot(
                channel_snapshot,
                limit=limit,
            )
        )

        result = original(
            filtered,
            *args,
            **kwargs,
        )

        return (
            str(result)
            +
            "\n"
            "- RELEVANCE GATE: Der aktuelle User-Turn hat Vorrang. "
            "Alte Episode-Themen nicht ohne aktuellen Bezug zur "
            "neuen Antwortidee machen.\n"
            "- Frühere Evilnae-Sätze sind Dialoghistorie und kein "
            "Beweis für ihren aktuellen Zustand."
        )

    return wrapped


def _add_issue(
    analysis,
    *,
    issue,
    penalty=5,
    repetition=0,
    grammar=0,
    echo=0,
):
    issues = list(
        getattr(
            analysis,
            "issues",
            [],
        )
        or []
    )

    if issue in issues:
        analysis.severe = True
        return

    issues.append(issue)
    analysis.issues = issues

    analysis.total_penalty = (
        int(
            getattr(
                analysis,
                "total_penalty",
                0,
            )
            or 0
        )
        +
        int(penalty)
    )

    analysis.repetition_score = (
        int(
            getattr(
                analysis,
                "repetition_score",
                0,
            )
            or 0
        )
        +
        int(repetition)
    )

    analysis.grammar_score = (
        int(
            getattr(
                analysis,
                "grammar_score",
                0,
            )
            or 0
        )
        +
        int(grammar)
    )

    analysis.echo_score = (
        int(
            getattr(
                analysis,
                "echo_score",
                0,
            )
            or 0
        )
        +
        int(echo)
    )

    analysis.severe = True


def wrap_response_quality_analyzer(
    original,
):
    @functools.wraps(original)
    def wrapped(
        text,
        *args,
        **kwargs,
    ):
        analysis = original(
            text,
            *args,
            **kwargs,
        )

        user_text = str(
            kwargs.get(
                "user_text",
                "",
            )
            or _CURRENT_USER_TEXT.get()
            or ""
        )

        recent = list(
            kwargs.get(
                "recent_evilnae_messages",
                None,
            )
            or []
        )

        reason = (
            semantic_violation_reason(
                str(text or ""),
                user_text=(
                    user_text
                ),
            )
        )

        if reason:
            _add_issue(
                analysis,
                issue=reason,
                penalty=6,
                grammar=(
                    4
                    if reason.startswith(
                        "semantic_"
                    )
                    else 0
                ),
            )

        for name in repeated_concepts(
            str(text or ""),
            recent,
        ):
            _add_issue(
                analysis,
                issue=(
                    "repeated_concept:"
                    +
                    name
                ),
                penalty=5,
                repetition=5,
            )

        if (
            _user_echo_ratio(
                user_text,
                str(text or ""),
            )
            >= 0.78
        ):
            _add_issue(
                analysis,
                issue=(
                    "user_idea_echo_takeover_v2"
                ),
                penalty=5,
                echo=5,
            )

        return analysis

    return wrapped


def wrap_character_state_observer(
    original,
):
    @functools.wraps(original)
    def wrapped(
        *args,
        **kwargs,
    ):
        answer = str(
            kwargs.get(
                "evilnae_answer",
                "",
            )
            or (
                args[0]
                if args
                else ""
            )
            or ""
        )

        reason = (
            state_write_block_reason(
                answer
            )
        )

        if reason:
            print(
                "[LIVE GUARD] "
                "character-state write blocked: "
                f"{reason}"
            )

            result = {
                "saved": 0,
                "observations": [],
                "blocked": reason,
            }

        else:
            result = original(
                *args,
                **kwargs,
            )

        register_arc_surface_use(
            answer
        )

        print(
            "[LIVE OUT] "
            f"{_CURRENT_USERNAME.get()} <- "
            f"{_short(answer)}"
        )

        return result

    return wrapped


def wrap_surface_writer(
    original,
):
    @functools.wraps(original)
    async def wrapped(
        *args,
        **kwargs,
    ):
        _SURFACE_FAILED.set(
            False
        )

        try:
            result = await original(
                *args,
                **kwargs,
            )

        except Exception as error:
            _SURFACE_FAILED.set(
                True
            )

            print(
                "[LIVE WARN] "
                "Qwen Surface exception -> "
                f"{type(error).__name__}"
            )

            raise

        candidate = str(
            getattr(
                result,
                "output_text",
                "",
            )
            or ""
        )

        reason = (
            semantic_violation_reason(
                candidate,
                user_text=str(
                    kwargs.get(
                        "user_message",
                        "",
                    )
                    or ""
                ),
                inner_state_guidance=str(
                    kwargs.get(
                        "inner_state_guidance",
                        "",
                    )
                    or ""
                ),
                evidence_context=str(
                    kwargs.get(
                        "evidence_context",
                        "",
                    )
                    or ""
                ),
                response_plan_text=str(
                    kwargs.get(
                        "response_plan_text",
                        "",
                    )
                    or ""
                ),
            )
        )

        if (
            candidate
            and reason
        ):
            try:
                result.success = False
                result.reason = (
                    "stability:"
                    +
                    reason
                )
            except Exception:
                pass

            _SURFACE_FAILED.set(
                True
            )

            print(
                "[LIVE GUARD] "
                "Qwen Surface rejected: "
                f"{reason}"
            )

            return result

        if (
            bool(
                getattr(
                    result,
                    "used",
                    False,
                )
            )
            and not bool(
                getattr(
                    result,
                    "success",
                    False,
                )
            )
        ):
            _SURFACE_FAILED.set(
                True
            )

            print(
                "[LIVE WARN] "
                "Qwen Surface fallback: "
                f"{getattr(result, 'reason', 'unknown')}"
            )

        return result

    return wrapped


def _local_passthrough(
    draft: str,
) -> LocalVoiceResult:
    return LocalVoiceResult(
        output_text=str(
            draft
            or ""
        ),
        used=False,
        rewritten=False,
        bot_likeness=0.0,
        repetition=0.0,
        evilnae_match=1.0,
        meaning_preserved=1.0,
        new_facts=False,
        reason=(
            "surface_failed_fast_fallback"
        ),
        duration=0.0,
        context_coherence=1.0,
    )


def wrap_local_voice(
    original,
):
    @functools.wraps(original)
    async def wrapped(
        *args,
        **kwargs,
    ):
        if _SURFACE_FAILED.get():
            print(
                "[LIVE WARN] "
                "second local Qwen pass skipped "
                "after Surface failure"
            )

            return _local_passthrough(
                str(
                    kwargs.get(
                        "draft",
                        "",
                    )
                    or ""
                )
            )

        return await original(
            *args,
            **kwargs,
        )

    return wrapped




# =========================================================
# 3.8.0 EXPERIENCE -> REFLECTION -> LEARNING WRAPPERS
# =========================================================

def wrap_salience_observer_v2(
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

        user_id = str(
            kwargs.get(
                "user_id",
                "",
            )
            or _CURRENT_USER_ID.get()
            or ""
        )

        register_salience_result(
            user_id=user_id,
            result=result,
        )

        return result

    return wrapped


def wrap_character_learning_observer_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        *args,
        **kwargs,
    ):
        user_text = str(
            kwargs.get(
                "user_text",
                "",
            )
            or ""
        )

        evilnae_answer = str(
            kwargs.get(
                "evilnae_answer",
                "",
            )
            or ""
        )

        result = (
            capture_experience(
                user_id=(
                    _CURRENT_USER_ID.get()
                ),
                username=(
                    _CURRENT_USERNAME.get()
                ),
                user_text=user_text,
                evilnae_answer=(
                    evilnae_answer
                ),
            )
        )

        development_result = (
            observe_development_from_experience(
                result
            )
        )

        if int(
            development_result.get(
                "changed",
                0,
            )
            or 0
        ) > 0:
            print(
                format_self_development_debug(
                    development_result
                )
            )

        print(
            format_experience_debug(
                result
            )
        )

        candidate = result.get(
            "candidate"
        )

        return {
            "saved": False,
            "reason": (
                "experience_pipeline_v2:"
                +
                str(
                    result.get(
                        "reason",
                        "observed",
                    )
                )
            ),
            "topic": (
                candidate.get(
                    "topic"
                )
                if isinstance(
                    candidate,
                    dict,
                )
                else None
            ),
            "sentiment": (
                candidate.get(
                    "sentiment"
                )
                if isinstance(
                    candidate,
                    dict,
                )
                else None
            ),
            "status": (
                "candidate"
                if isinstance(
                    candidate,
                    dict,
                )
                else "observed"
            ),
            "confirmations": int(
                result.get(
                    "cluster_count",
                    0,
                )
                or 0
            ),
        }

    return wrapped


def wrap_reflection_prompt_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        *args,
        **kwargs,
    ):
        kwargs = dict(
            kwargs
        )

        user_message = str(
            kwargs.get(
                "user_message",
                "",
            )
            or ""
        )

        evilnae_answer = str(
            kwargs.get(
                "evilnae_answer",
                "",
            )
            or ""
        )

        experience_context = (
            format_experience_for_reflection(
                user_message=user_message,
                evilnae_answer=(
                    evilnae_answer
                ),
            )
        )

        current_learning_text = str(
            kwargs.get(
                "current_learning_text",
                "",
            )
            or ""
        ).strip()

        kwargs[
            "current_learning_text"
        ] = (
            (
                current_learning_text
                +
                "\n\n"
                +
                experience_context
            )
            if current_learning_text
            else experience_context
        )

        return original(
            *args,
            **kwargs,
        )

    return wrapped


def wrap_apply_learning_signals_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        data,
        *args,
        **kwargs,
    ):
        gated, metadata = (
            gate_reflection_learning(
                data
            )
        )

        development_result = (
            observe_development_from_reflection(
                metadata
            )
        )

        if int(
            development_result.get(
                "changed",
                0,
            )
            or 0
        ) > 0:
            print(
                format_self_development_debug(
                    development_result
                )
            )

        print(
            "[EXPERIENCE REFLECTION GATE] "
            f"experience="
            f"{metadata.get('experience_id', '')} "
            f"reason="
            f"{metadata.get('gate_reason')} "
            f"delta_limit="
            f"{metadata.get('delta_limit')} "
            f"preference="
            f"{metadata.get('preference_result')}"
        )

        return original(
            gated,
            *args,
            **kwargs,
        )

    return wrapped


def wrap_store_reflection_v2(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        reflection,
        *args,
        **kwargs,
    ):
        reflection = (
            annotate_reflection_record(
                reflection
            )
        )

        return original(
            reflection,
            *args,
            **kwargs,
        )

    return wrapped



# =========================================================
# 3.9.0 SELF DEVELOPMENT / LONG-RUNNING ARC WRAPPERS
# =========================================================

def wrap_character_learning_prompt_v3(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        user_text="",
        *args,
        **kwargs,
    ):
        base = original(
            user_text,
            *args,
            **kwargs,
        )

        development = (
            format_self_development_for_prompt(
                user_text
            )
        )

        return (
            str(
                base
                or ""
            ).strip()
            +
            "\n\n"
            +
            development
        ).strip()

    return wrapped


def wrap_initiative_prompt_v3(
    original,
):
    @functools.wraps(
        original
    )
    def wrapped(
        *args,
        **kwargs,
    ):
        kwargs = dict(
            kwargs
        )

        channel_context = str(
            kwargs.get(
                "channel_context",
                "",
            )
            or ""
        ).strip()

        development = (
            format_self_development_for_prompt(
                ""
            )
        )

        kwargs[
            "channel_context"
        ] = (
            (
                channel_context
                +
                "\n\n"
                +
                development
            )
            if channel_context
            else development
        )

        return original(
            *args,
            **kwargs,
        )

    return wrapped

# =========================================================
# SELF TEST
# =========================================================

def _self_test() -> int:
    tests = [
        (
            "how-are-you non-answer",
            intent_violation_reason(
                "Evil, wie geht es dir?",
                "Hab schon fast nicht mehr dran geglaubt, dass du noch da bist.",
            )
            ==
            "intent_how_are_you_not_answered",
        ),
        (
            "how-are-you valid",
            intent_violation_reason(
                "Evil, wie geht es dir?",
                "Mir geht's gut, nur bisschen langsam heute.",
            )
            ==
            "",
        ),
        (
            "food boss non-answer",
            intent_violation_reason(
                "Was hast du heute alles gegessen?",
                "Ich bin halt der Boss im Fressen, Deal with it.",
            )
            ==
            "intent_food_history_not_answered",
        ),
        (
            "tea uncertainty",
            intent_violation_reason(
                "Evil kannst du mir einen Tee machen?",
                "weiß ich grad nicht sicher.",
            )
            ==
            "intent_request_uncertainty",
        ),
        (
            "Bruederin",
            semantic_violation_reason(
                "Ich dachte, du wärst meine eigene Brüderin.",
                user_text="Evil du bist so ein Morgenmuffel",
            )
            ==
            "semantic_bruederin",
        ),
        (
            "ungrounded confused state with modifiers",
            semantic_violation_reason(
                "Ja, ich bin verwirrt.",
                user_text="Evil du bist heute irgendwie echt verwirrt",
                inner_state_guidance=(
                    "feeling=neutral irritation=0.08"
                ),
                evidence_context="",
                response_plan_text=(
                    "User sagt verwirrt, aber nicht als Fakt übernehmen"
                ),
            )
            ==
            "semantic_ungrounded_self_state",
        ),
        (
            "ungrounded confused state",
            semantic_violation_reason(
                "Ja, ich bin verwirrt.",
                user_text="Evil du bist heute verwirrt",
                inner_state_guidance=(
                    "feeling=neutral irritation=0.08"
                ),
                evidence_context="",
                response_plan_text=(
                    "neutral reagieren"
                ),
            )
            ==
            "semantic_ungrounded_self_state",
        ),
        (
            "confusion repeat",
            "confusion_loop"
            in repeated_concepts(
                "Bin noch komplett im Nebel.",
                [
                    "Hab verschlafen und bin etwas verwirrt."
                ],
            ),
        ),
        (
            "food boss repeat",
            "food_boss_loop"
            in repeated_concepts(
                "Der Boss im Fressen macht keine halben Sachen.",
                [
                    "Ich bin halt der Boss im Fressen."
                ],
            ),
        ),
        (
            "implicit beides",
            implicit_evilnae_continuation(
                current_message=(
                    "Ich glaube beides"
                ),
                channel_context=(
                    "Hanae: du bist verwirrt\n"
                    "Evilnae: bin ich verwirrt oder schlecht eingeschlafen"
                ),
                recent_evilnae_messages=[
                    "bin ich verwirrt oder schlecht eingeschlafen"
                ],
            ),
        ),
        (
            "state pollution",
            state_write_block_reason(
                "Warte, ich schaue mal, ob ich was Brauchbares finden kann."
            )
            ==
            "low_confidence_meta_activity",
        ),
    ]

    sample_episode = [
        {
            "type": "user",
            "content": "Kopfschmerzen und Gaming",
            "user_id": "1",
        },
        {
            "type": "bot",
            "content": "Ich bin leiser.",
            "user_id": "",
        },
        {
            "type": "user",
            "content": "Einkaufen später",
            "user_id": "2",
        },
        {
            "type": "bot",
            "content": "Klar.",
            "user_id": "",
        },
        {
            "type": "user",
            "content": "Richtig",
            "user_id": "2",
        },
        {
            "type": "bot",
            "content": "Genau.",
            "user_id": "",
        },
        {
            "type": "user",
            "content": "Wie geht es dir?",
            "user_id": "3",
        },
    ]

    tests.append(
        (
            "episode relevance",
            len(
                filter_episode_snapshot(
                    sample_episode,
                    limit=12,
                )
            )
            <= 5,
        )
    )

    console = ConsoleOutputFilter()

    tests.append(
        (
            "compact hides debug",
            console.filter_chunk(
                "[BRAIN DEBUG] huge thing\n"
            )
            ==
            "",
        )
    )

    tests.append(
        (
            "compact shows live",
            "[LIVE OUT]"
            in console.filter_chunk(
                "[LIVE OUT] Hanae <- passt\n"
            ),
        )
    )

    passed = sum(
        1
        for _, success in tests
        if success
    )

    print()
    print("=" * 62)
    print(
        f"LIVE STABILITY v"
        f"{LIVE_STABILITY_VERSION} TEST"
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

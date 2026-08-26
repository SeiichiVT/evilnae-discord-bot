import re
import time

from dataclasses import dataclass
from typing import Optional

import evilnae_emotes


# =========================================================
# VERSION
# =========================================================

DISCORD_ACTIONS_VERSION = "1.0"


# =========================================================
# COOLDOWNS
# =========================================================

REACTION_GLOBAL_COOLDOWN = 12.0
REACTION_SEMANTIC_COOLDOWN = 60.0

TEXT_EMOTE_GLOBAL_COOLDOWN = 20.0
TEXT_EMOTE_SEMANTIC_COOLDOWN = 90.0


SPECIAL_TEXT_COOLDOWNS = {
    "wave": 150.0,
    "love": 90.0,
    "fire": 90.0,
    "party": 90.0,
    "laugh": 60.0,
}


# =========================================================
# RUNTIME STATE
# =========================================================

_reaction_last_any = {}
_reaction_last_semantic = {}

_text_last_any = {}
_text_last_semantic = {}


# =========================================================
# RESULT
# =========================================================

@dataclass
class ApplicationReactionDecision:

    semantic: Optional[str] = None

    rendered: Optional[str] = None

    confidence: float = 0.0

    allowed: bool = False

    reason: str = "none"

    cooldown_remaining: float = 0.0


@dataclass
class TextEmoteCooldownResult:

    semantic: Optional[str] = None

    allowed: bool = True

    suppressed: bool = False

    reason: str = "none"

    cooldown_remaining: float = 0.0


# =========================================================
# PATTERNS
# =========================================================

SERIOUS_PATTERNS = [

    re.compile(
        r"\b(?:gestorben|verstorben|tod|trauer|"
        r"beerdigung|selbstmord|suizid|"
        r"selbstverletz|umbringen|krebs|"
        r"schwer krank|krankenhaus|notaufnahme|"
        r"missbrauch|vergewaltig|trauma)\w*\b",
        re.IGNORECASE,
    ),
]


LAUGH_PATTERNS = [

    re.compile(
        r"\b(?:lol|lmao|lmfao|haha+|hehe+|"
        r"kekw|xd)\b",
        re.IGNORECASE,
    ),
]


SHOCK_PATTERNS = [

    re.compile(
        r"\b(?:wtf|what|no way|oha|ernsthaft|"
        r"wirklich\?|was zur hölle|was zum fick)\b",
        re.IGNORECASE,
    ),
]


LOVE_PATTERNS = [

    re.compile(
        r"\b(?:danke|lieb von dir|süß|suess|"
        r"hab dich lieb|love you|liebe dich)\b",
        re.IGNORECASE,
    ),
]


RAGE_PATTERNS = [

    re.compile(
        r"\b(?:ich raste|ich hasse das|"
        r"rage|ich schwöre|ich schwoere)\b",
        re.IGNORECASE,
    ),
]


ANGRY_PATTERNS = [

    re.compile(
        r"\b(?:nervt|nervig|sauer|wütend|wuetend|"
        r"abfuck|scheiße|scheisse|scheiß|scheiss|"
        r"ätzend|aetzend|frustrierend)\b",
        re.IGNORECASE,
    ),
]


THINK_PATTERNS = [

    re.compile(
        r"\b(?:hmm+|hm+|sus|interessant|warte mal|"
        r"moment mal|wait)\b",
        re.IGNORECASE,
    ),
]


PARTY_PATTERNS = [

    re.compile(
        r"\b(?:gewonnen|geschafft|glückwunsch|"
        r"glueckwunsch|geburtstag|party|feiern)\b",
        re.IGNORECASE,
    ),
]


FIRE_PATTERNS = [

    re.compile(
        r"\b(?:clean|based|stark|rasiert|zerlegt|"
        r"heftig|krass)\b",
        re.IGNORECASE,
    ),
]


BONK_PATTERNS = [

    re.compile(
        r"\b(?:frech|hör auf|hoer auf|"
        r"benimm dich|du dieb|diebin)\b",
        re.IGNORECASE,
    ),
]


WAVE_PATTERNS = [

    re.compile(
        r"\b(?:bye|tschüss|tschuess|bis später|"
        r"bis spaeter|gute nacht|schlaf gut)\b",
        re.IGNORECASE,
    ),
]


NEGATIVE_PATTERNS = [

    re.compile(
        r"\b(?:nervt|nervig|scheiße|scheisse|"
        r"scheiß|scheiss|frust|verloren|"
        r"kaputt|schlecht|ätzend|aetzend|"
        r"abfuck)\w*\b",
        re.IGNORECASE,
    ),
]


# =========================================================
# HELPERS
# =========================================================

def _now(
    value=None
):

    if value is None:

        return (
            time.monotonic()
        )

    return float(
        value
    )


def _matches(
    text,
    patterns
):

    return any(
        pattern.search(
            text
            or ""
        )

        for pattern
        in patterns
    )


def _channel_key(
    channel_id
):

    return str(
        channel_id
    )


def _semantic_key(
    channel_id,
    semantic
):

    return (
        str(
            channel_id
        ),
        str(
            semantic
        ),
    )


def _is_serious(
    text
):

    return (
        _matches(
            text,
            SERIOUS_PATTERNS
        )
    )


# =========================================================
# REACTION SEMANTIC
# =========================================================

def choose_reaction_semantic(
    user_text: str,
    *,
    suggested_reaction: Optional[str] = None
):

    text = str(
        user_text
        or ""
    )

    suggested = str(
        suggested_reaction
        or ""
    )

    if _is_serious(
        text
    ):

        return (
            None,
            1.0,
            "serious_context"
        )

    negative = (
        _matches(
            text,
            NEGATIVE_PATTERNS
        )
    )

    # -----------------------------------------------------
    # EXPLICIT CONTENT SIGNALS
    # -----------------------------------------------------

    if (
        _matches(
            text,
            LAUGH_PATTERNS
        )
        or
        suggested
        in {
            "😂",
            "🤣",
            "💀",
        }
    ):

        return (
            "laugh",
            0.95,
            "laughter_signal"
        )

    if _matches(
        text,
        SHOCK_PATTERNS
    ):

        return (
            "shocked",
            0.90,
            "shock_signal"
        )

    if _matches(
        text,
        LOVE_PATTERNS
    ):

        return (
            "love",
            0.90,
            "love_signal"
        )

    if _matches(
        text,
        RAGE_PATTERNS
    ):

        return (
            "rage",
            0.90,
            "rage_signal"
        )

    if _matches(
        text,
        ANGRY_PATTERNS
    ):

        return (
            "angry",
            0.86,
            "negative_signal"
        )

    if (
        _matches(
            text,
            THINK_PATTERNS
        )
        or
        suggested
        ==
        "👀"
    ):

        return (
            "think",
            0.82,
            "thinking_signal"
        )

    if (
        not negative
        and
        _matches(
            text,
            PARTY_PATTERNS
        )
    ):

        return (
            "party",
            0.85,
            "celebration_signal"
        )

    if (
        not negative
        and
        _matches(
            text,
            FIRE_PATTERNS
        )
    ):

        return (
            "fire",
            0.80,
            "positive_signal"
        )

    if _matches(
        text,
        BONK_PATTERNS
    ):

        return (
            "bonk",
            0.78,
            "playful_bonk_signal"
        )

    if _matches(
        text,
        WAVE_PATTERNS
    ):

        return (
            "wave",
            0.76,
            "farewell_signal"
        )

    # -----------------------------------------------------
    # IMPORTANT
    #
    # 👍 ist KEINE Default-Reaction mehr.
    #
    # Wenn Agency lediglich "react" sagt,
    # aber kein echter semantischer Grund
    # für eines von Evilnaes Emotes existiert,
    # reagieren wir lieber gar nicht.
    # -----------------------------------------------------

    return (
        None,
        0.0,
        "no_application_reaction_signal"
    )


# =========================================================
# REACTION COOLDOWN
# =========================================================

def _reaction_cooldown_remaining(
    *,
    channel_id,
    semantic,
    now=None,
):

    now = _now(
        now
    )

    channel_key = (
        _channel_key(
            channel_id
        )
    )

    semantic_key = (
        _semantic_key(
            channel_id,
            semantic
        )
    )

    global_last = (
        _reaction_last_any.get(
            channel_key
        )
    )

    semantic_last = (
        _reaction_last_semantic.get(
            semantic_key
        )
    )

    global_remaining = (
        0.0
    )

    semantic_remaining = (
        0.0
    )

    if global_last is not None:

        global_remaining = max(
            0.0,
            REACTION_GLOBAL_COOLDOWN
            -
            (
                now
                -
                global_last
            )
        )

    if semantic_last is not None:

        semantic_remaining = max(
            0.0,
            REACTION_SEMANTIC_COOLDOWN
            -
            (
                now
                -
                semantic_last
            )
        )

    return max(
        global_remaining,
        semantic_remaining
    )


# =========================================================
# PREPARE APPLICATION REACTION
# =========================================================

def prepare_application_reaction(
    *,
    user_text,
    suggested_reaction=None,
    channel_id,
    now=None,
):

    (
        semantic,
        confidence,
        reason
    ) = (
        choose_reaction_semantic(
            user_text,
            suggested_reaction=(
                suggested_reaction
            )
        )
    )

    if not semantic:

        return (
            ApplicationReactionDecision(
                semantic=None,
                rendered=None,
                confidence=confidence,
                allowed=False,
                reason=reason,
            )
        )

    rendered = (
        evilnae_emotes.get_emote(
            semantic
        )
    )

    if not rendered:

        return (
            ApplicationReactionDecision(
                semantic=semantic,
                rendered=None,
                confidence=confidence,
                allowed=False,
                reason="application_emoji_not_loaded",
            )
        )

    remaining = (
        _reaction_cooldown_remaining(
            channel_id=channel_id,
            semantic=semantic,
            now=now,
        )
    )

    if remaining > 0:

        return (
            ApplicationReactionDecision(
                semantic=semantic,
                rendered=rendered,
                confidence=confidence,
                allowed=False,
                reason="reaction_cooldown",
                cooldown_remaining=remaining,
            )
        )

    return (
        ApplicationReactionDecision(
            semantic=semantic,
            rendered=rendered,
            confidence=confidence,
            allowed=True,
            reason=reason,
            cooldown_remaining=0.0,
        )
    )


# =========================================================
# REGISTER REACTION
# =========================================================

def register_application_reaction(
    *,
    channel_id,
    semantic,
    now=None,
):

    if not semantic:

        return

    now = _now(
        now
    )

    _reaction_last_any[
        _channel_key(
            channel_id
        )
    ] = now

    _reaction_last_semantic[
        _semantic_key(
            channel_id,
            semantic
        )
    ] = now


# =========================================================
# TEXT EMOTE COOLDOWN
# =========================================================

def _text_emote_cooldown_remaining(
    *,
    channel_id,
    semantic,
    now=None,
):

    now = _now(
        now
    )

    channel_key = (
        _channel_key(
            channel_id
        )
    )

    semantic_key = (
        _semantic_key(
            channel_id,
            semantic
        )
    )

    global_last = (
        _text_last_any.get(
            channel_key
        )
    )

    semantic_last = (
        _text_last_semantic.get(
            semantic_key
        )
    )

    global_remaining = (
        0.0
    )

    semantic_remaining = (
        0.0
    )

    semantic_cooldown = (
        SPECIAL_TEXT_COOLDOWNS.get(
            semantic,
            TEXT_EMOTE_SEMANTIC_COOLDOWN
        )
    )

    if global_last is not None:

        global_remaining = max(
            0.0,
            TEXT_EMOTE_GLOBAL_COOLDOWN
            -
            (
                now
                -
                global_last
            )
        )

    if semantic_last is not None:

        semantic_remaining = max(
            0.0,
            semantic_cooldown
            -
            (
                now
                -
                semantic_last
            )
        )

    return max(
        global_remaining,
        semantic_remaining
    )


def apply_text_emote_cooldown(
    answer,
    emote_result,
    *,
    channel_id,
    now=None,
):

    if (
        emote_result is None
        or
        not bool(
            getattr(
                emote_result,
                "added",
                False
            )
        )
    ):

        return (
            str(
                answer
                or ""
            ),
            TextEmoteCooldownResult(
                allowed=True,
                suppressed=False,
                reason="no_emote_added",
            )
        )

    semantic = (
        getattr(
            emote_result,
            "semantic",
            None
        )
    )

    rendered = (
        getattr(
            emote_result,
            "rendered",
            None
        )
    )

    if (
        not semantic
        or
        not rendered
    ):

        return (
            str(
                answer
                or ""
            ),
            TextEmoteCooldownResult(
                semantic=semantic,
                allowed=True,
                suppressed=False,
                reason="missing_semantic_or_rendered",
            )
        )

    remaining = (
        _text_emote_cooldown_remaining(
            channel_id=channel_id,
            semantic=semantic,
            now=now,
        )
    )

    if remaining > 0:

        cleaned = (
            str(
                answer
                or ""
            )
            .replace(
                rendered,
                ""
            )
            .strip()
        )

        cleaned = re.sub(
            r"[ \t]+",
            " ",
            cleaned
        )

        try:

            emote_result.added = (
                False
            )

            emote_result.reason = (
                "text_emote_cooldown"
            )

        except Exception:

            pass

        return (
            cleaned,
            TextEmoteCooldownResult(
                semantic=semantic,
                allowed=False,
                suppressed=True,
                reason="text_emote_cooldown",
                cooldown_remaining=remaining,
            )
        )

    now_value = _now(
        now
    )

    _text_last_any[
        _channel_key(
            channel_id
        )
    ] = now_value

    _text_last_semantic[
        _semantic_key(
            channel_id,
            semantic
        )
    ] = now_value

    return (
        str(
            answer
            or ""
        ),
        TextEmoteCooldownResult(
            semantic=semantic,
            allowed=True,
            suppressed=False,
            reason="allowed",
            cooldown_remaining=0.0,
        )
    )


# =========================================================
# DEBUG
# =========================================================

def format_application_reaction_debug(
    result
):

    return (
        "[APPLICATION REACTION] "
        f"v={DISCORD_ACTIONS_VERSION} "
        f"semantic={result.semantic!r} "
        f"confidence={result.confidence:.2f} "
        f"allowed={result.allowed} "
        f"reason={result.reason} "
        f"cooldown={result.cooldown_remaining:.1f}s"
    )


def format_text_emote_cooldown_debug(
    result
):

    return (
        "[TEXT EMOTE COOLDOWN] "
        f"v={DISCORD_ACTIONS_VERSION} "
        f"semantic={result.semantic!r} "
        f"allowed={result.allowed} "
        f"suppressed={result.suppressed} "
        f"reason={result.reason} "
        f"cooldown={result.cooldown_remaining:.1f}s"
    )


# =========================================================
# SELF TEST
# =========================================================

def _reset_test_state():

    _reaction_last_any.clear()
    _reaction_last_semantic.clear()

    _text_last_any.clear()
    _text_last_semantic.clear()


def _self_test():

    _reset_test_state()

    old_cache = dict(
        evilnae_emotes._application_emojis
    )

    evilnae_emotes._application_emojis = {

        name:
            f"<:{name}:123>"

        for name
        in evilnae_emotes.EMOTE_NAMES.values()
    }

    tests = []

    try:

        semantic, _, _ = (
            choose_reaction_semantic(
                "LMAO was war das"
            )
        )

        tests.append(
            (
                "laugh semantic",
                semantic == "laugh"
            )
        )

        semantic, _, _ = (
            choose_reaction_semantic(
                "hmm das ist sus",
                suggested_reaction="👀",
            )
        )

        tests.append(
            (
                "think semantic",
                semantic == "think"
            )
        )

        semantic, _, _ = (
            choose_reaction_semantic(
                "okay",
                suggested_reaction="👍",
            )
        )

        tests.append(
            (
                "no thumbs-up fallback",
                semantic is None
            )
        )

        semantic, _, _ = (
            choose_reaction_semantic(
                "mein hund ist gestorben"
            )
        )

        tests.append(
            (
                "serious context no reaction",
                semantic is None
            )
        )

        semantic, _, _ = (
            choose_reaction_semantic(
                "endlich den boss geschafft"
            )
        )

        tests.append(
            (
                "celebration semantic",
                semantic == "party"
            )
        )

        semantic, _, _ = (
            choose_reaction_semantic(
                "der boss nervt krass"
            )
        )

        tests.append(
            (
                "negative krass not fire",
                semantic != "fire"
            )
        )

        reaction = (
            prepare_application_reaction(
                user_text="lmao",
                suggested_reaction="😂",
                channel_id="1",
                now=100.0,
            )
        )

        tests.append(
            (
                "application emoji prepared",
                (
                    reaction.allowed
                    and
                    reaction.semantic == "laugh"
                    and
                    "evilnae_laugh"
                    in (
                        reaction.rendered
                        or ""
                    )
                )
            )
        )

        register_application_reaction(
            channel_id="1",
            semantic="laugh",
            now=100.0,
        )

        cooldown_reaction = (
            prepare_application_reaction(
                user_text="haha",
                suggested_reaction="😂",
                channel_id="1",
                now=105.0,
            )
        )

        tests.append(
            (
                "reaction cooldown blocks repeat",
                (
                    not cooldown_reaction.allowed
                    and
                    cooldown_reaction.reason
                    ==
                    "reaction_cooldown"
                )
            )
        )

        class FakeEmoteResult:

            added = True
            semantic = "wave"
            rendered = "<:evilnae_wave:123>"
            reason = "greeting"

        answer, result = (
            apply_text_emote_cooldown(
                "bye <:evilnae_wave:123>",
                FakeEmoteResult(),
                channel_id="2",
                now=200.0,
            )
        )

        tests.append(
            (
                "first text emote allowed",
                (
                    result.allowed
                    and
                    "evilnae_wave"
                    in answer
                )
            )
        )

        second_fake = (
            FakeEmoteResult()
        )

        answer, result = (
            apply_text_emote_cooldown(
                "bis später <:evilnae_wave:123>",
                second_fake,
                channel_id="2",
                now=210.0,
            )
        )

        tests.append(
            (
                "repeated wave suppressed",
                (
                    result.suppressed
                    and
                    "evilnae_wave"
                    not in answer
                )
            )
        )

        different_channel = (
            prepare_application_reaction(
                user_text="haha",
                suggested_reaction="😂",
                channel_id="999",
                now=105.0,
            )
        )

        tests.append(
            (
                "reaction cooldown channel scoped",
                different_channel.allowed
            )
        )

    finally:

        evilnae_emotes._application_emojis = (
            old_cache
        )

        _reset_test_state()

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"DISCORD ACTIONS "
        f"v{DISCORD_ACTIONS_VERSION} TEST"
    )
    print(
        "============================================"
    )
    print("")

    for (
        name,
        success
    ) in tests:

        if success:

            status = "PASS"
            passed += 1

        else:

            status = "FAIL"

        print(
            f"[{status}] {name}"
        )

    print("")
    print(
        "============================================"
    )
    print(
        f"RESULT: "
        f"{passed}/{len(tests)} passed"
    )
    print(
        "============================================"
    )

    return (
        passed
        ==
        len(tests)
    )


if __name__ == "__main__":

    _self_test()
import re

from dataclasses import dataclass
from typing import Optional


# =========================================================
# VERSION
# =========================================================

AGENCY_VERSION = "1.0"


# =========================================================
# ACTIONS
# =========================================================

ACTION_REPLY = "reply"

ACTION_REACT = "react"

ACTION_STAY_SILENT = "stay_silent"


# =========================================================
# CONVERSATION MODES
# =========================================================

MODE_DIRECT = "direct"

MODE_CONTINUATION = "continuation"

MODE_PARTICIPATION = "participation"


# =========================================================
# LOW-VALUE ACKNOWLEDGEMENTS
#
# In einem laufenden Gespräch brauchen diese Nachrichten
# normalerweise KEINE sprachliche Antwort.
# =========================================================

LOW_VALUE_ACKS = {

    "check",

    "ok",

    "okay",

    "oki",

    "alles klar",

    "nice",

    "true",

    "mhm",

    "hm",

    "jo",

    "jap",

    "jup",

    "passt",

    "verstehe",

    "achso",

    "ach so",

    "same",

    "rip",

    "lol",

    "lmao",

    "haha",

    "hehe",

    "bruh",

    "ja",

    "jap genau",

    "genau",

    "stimmt",

    "korrekt",
}


# =========================================================
# LAUGHTER SIGNALS
# =========================================================

LAUGHTER_SIGNALS = {

    "lol",

    "lmao",

    "haha",

    "hahaha",

    "hehe",

    "xd",

    "xD",
}


# =========================================================
# EYE / INTEREST SIGNALS
# =========================================================

EYE_SIGNALS = {

    "sus",

    "hmm",

    "interessant",

    "oha",

    "warte",

    "moment",
}


# =========================================================
# RESULT
# =========================================================

@dataclass
class AgencyResult:

    action: str = ACTION_REPLY

    reaction: Optional[str] = None

    overridden: bool = False

    reason: str = "brain_reply"

    conversation_mode: str = MODE_DIRECT


# =========================================================
# NORMALIZE
# =========================================================

def normalize_message(
    text: str
) -> str:

    text = str(
        text
        or ""
    ).strip().lower()

    text = re.sub(
        r"<a?:[a-zA-Z0-9_]+:\d+>",
        "",
        text
    )

    text = re.sub(
        r"[^\wäöüß]+",
        " ",
        text,
        flags=re.UNICODE
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# QUESTION-LIKE
# =========================================================

QUESTION_STARTERS = {

    "was",

    "wer",

    "wie",

    "warum",

    "wieso",

    "wann",

    "wo",

    "welche",

    "welcher",

    "welches",

    "kann",

    "kannst",

    "willst",

    "würdest",

    "wuerdest",

    "hast",

    "bist",

    "magst",

    "meinst",

    "denkst",

    "findest",

    "weißt",

    "weisst",
}


def looks_like_question(
    text: str
) -> bool:

    text = str(
        text
        or ""
    ).strip()

    if "?" in text:

        return True

    normalized = normalize_message(
        text
    )

    if not normalized:

        return False

    first_word = (
        normalized
        .split(
            " ",
            1
        )[0]
    )

    return (
        first_word
        in QUESTION_STARTERS
    )


# =========================================================
# WORD COUNT
# =========================================================

def message_word_count(
    text: str
) -> int:

    normalized = normalize_message(
        text
    )

    if not normalized:

        return 0

    return len(
        normalized.split()
    )


# =========================================================
# REACTION CHOICE
#
# Noch Standard-Unicode.
# Custom Discord Emotes kommen später separat.
# =========================================================

def choose_reaction(
    text: str
) -> str:

    normalized = normalize_message(
        text
    )

    words = set(
        normalized.split()
    )

    if (
        words
        &
        {
            item.lower()
            for item
            in LAUGHTER_SIGNALS
        }
    ):

        return "😂"

    if (
        words
        &
        EYE_SIGNALS
    ):

        return "👀"

    if any(
        marker in str(
            text
            or ""
        )

        for marker
        in (
            "😂",
            "🤣",
            "💀",
        )
    ):

        return "😂"

    return "👍"


# =========================================================
# APPLY AGENCY GUARD
# =========================================================

def apply_agency_guard(
    *,
    decision,
    conversation_mode: str,
    user_text: str,
    is_emoji_only: bool = False
) -> AgencyResult:

    conversation_mode = str(
        conversation_mode
        or
        MODE_DIRECT
    ).lower()

    brain_action = str(
        getattr(
            decision,
            "action",
            ACTION_REPLY
        )
        or
        ACTION_REPLY
    ).lower()

    # =====================================================
    # DIRECT ADDRESS
    #
    # Wenn der User Evilnae direkt anspricht,
    # verschwinden wir nicht einfach.
    #
    # Das Brain darf hier weiterhin bestimmen,
    # WIE sie reagiert, aber nicht kommentarlos schweigen.
    # =====================================================

    if (
        conversation_mode
        ==
        MODE_DIRECT
    ):

        if brain_action in {
            ACTION_STAY_SILENT,
            ACTION_REACT,
        }:

            decision.action = (
                ACTION_REPLY
            )

            return AgencyResult(

                action=(
                    ACTION_REPLY
                ),

                reaction=None,

                overridden=True,

                reason=(
                    "direct_address_requires_reply"
                ),

                conversation_mode=(
                    conversation_mode
                )
            )

        return AgencyResult(

            action=(
                ACTION_REPLY
            ),

            reaction=None,

            overridden=False,

            reason="direct_reply",

            conversation_mode=(
                conversation_mode
            )
        )

    # =====================================================
    # PARTICIPATION
    #
    # Participation Brain hat bereits entschieden:
    #
    # "Ich mische mich ein."
    #
    # Danach soll das Main Brain nicht direkt
    # wieder zurückrudern.
    # =====================================================

    if (
        conversation_mode
        ==
        MODE_PARTICIPATION
    ):

        if brain_action in {
            ACTION_STAY_SILENT,
            ACTION_REACT,
        }:

            decision.action = (
                ACTION_REPLY
            )

            return AgencyResult(

                action=(
                    ACTION_REPLY
                ),

                overridden=True,

                reason=(
                    "participation_already_committed"
                ),

                conversation_mode=(
                    conversation_mode
                )
            )

        return AgencyResult(

            action=(
                ACTION_REPLY
            ),

            reason=(
                "participation_reply"
            ),

            conversation_mode=(
                conversation_mode
            )
        )

    # =====================================================
    # CONTINUATION
    #
    # Hier darf Evilnae wirklich entscheiden,
    # dass gar keine Textantwort nötig ist.
    # =====================================================

    normalized = normalize_message(
        user_text
    )

    # -----------------------------------------------------
    # Echte Frage:
    #
    # Niemals wegen eines Silence-Heuristics verschlucken.
    # -----------------------------------------------------

    if looks_like_question(
        user_text
    ):

        if brain_action == (
            ACTION_STAY_SILENT
        ):

            decision.action = (
                ACTION_REPLY
            )

            return AgencyResult(

                action=(
                    ACTION_REPLY
                ),

                overridden=True,

                reason=(
                    "question_requires_reply"
                ),

                conversation_mode=(
                    conversation_mode
                )
            )

        if brain_action == (
            ACTION_REACT
        ):

            decision.action = (
                ACTION_REPLY
            )

            return AgencyResult(

                action=(
                    ACTION_REPLY
                ),

                overridden=True,

                reason=(
                    "question_not_reaction_only"
                ),

                conversation_mode=(
                    conversation_mode
                )
            )

        return AgencyResult(

            action=(
                ACTION_REPLY
            ),

            reason="continuation_question",

            conversation_mode=(
                conversation_mode
            )
        )

    # -----------------------------------------------------
    # Reines Emoji / Custom Emote
    #
    # Nicht automatisch noch eine Textantwort draufsetzen.
    # -----------------------------------------------------

    if is_emoji_only:

        decision.action = (
            ACTION_STAY_SILENT
        )

        return AgencyResult(

            action=(
                ACTION_STAY_SILENT
            ),

            overridden=(
                brain_action
                !=
                ACTION_STAY_SILENT
            ),

            reason=(
                "emoji_only_no_text_needed"
            ),

            conversation_mode=(
                conversation_mode
            )
        )

    # -----------------------------------------------------
    # "Check"
    # "nice"
    # "true"
    # "mhm"
    #
    # Genau diese Fälle haben bisher unnötige
    # Bot-Antworten erzeugt.
    # -----------------------------------------------------

    if (
        normalized
        in
        LOW_VALUE_ACKS
    ):

        decision.action = (
            ACTION_STAY_SILENT
        )

        return AgencyResult(

            action=(
                ACTION_STAY_SILENT
            ),

            overridden=(
                brain_action
                !=
                ACTION_STAY_SILENT
            ),

            reason=(
                "low_value_acknowledgement"
            ),

            conversation_mode=(
                conversation_mode
            )
        )

    # -----------------------------------------------------
    # Brain selbst sagt:
    # stay_silent
    # -----------------------------------------------------

    if brain_action == (
        ACTION_STAY_SILENT
    ):

        return AgencyResult(

            action=(
                ACTION_STAY_SILENT
            ),

            overridden=False,

            reason=(
                "brain_chose_silence"
            ),

            conversation_mode=(
                conversation_mode
            )
        )

    # -----------------------------------------------------
    # Brain selbst sagt:
    # react
    # -----------------------------------------------------

    if brain_action == (
        ACTION_REACT
    ):

        reaction = (
            choose_reaction(
                user_text
            )
        )

        return AgencyResult(

            action=(
                ACTION_REACT
            ),

            reaction=(
                reaction
            ),

            overridden=False,

            reason=(
                "brain_chose_reaction"
            ),

            conversation_mode=(
                conversation_mode
            )
        )

    # -----------------------------------------------------
    # Topic exhausted + sehr kurze Nachricht.
    #
    # Zusätzliche Absicherung gegen:
    #
    # "jo"
    # "passt"
    # "same"
    # -----------------------------------------------------

    if (
        bool(
            getattr(
                decision,
                "topic_exhausted",
                False
            )
        )
        and
        message_word_count(
            user_text
        )
        <= 4
    ):

        decision.action = (
            ACTION_STAY_SILENT
        )

        return AgencyResult(

            action=(
                ACTION_STAY_SILENT
            ),

            overridden=True,

            reason=(
                "topic_exhausted_short_message"
            ),

            conversation_mode=(
                conversation_mode
            )
        )

    # -----------------------------------------------------
    # Normal reply.
    # -----------------------------------------------------

    decision.action = (
        brain_action
    )

    return AgencyResult(

        action=(
            ACTION_REPLY
        ),

        overridden=False,

        reason=(
            "brain_reply"
        ),

        conversation_mode=(
            conversation_mode
        )
    )


# =========================================================
# DEBUG
# =========================================================

def format_agency_debug(
    result: AgencyResult
) -> str:

    return (

        "[AGENCY] "
        f"v={AGENCY_VERSION} "
        f"mode={result.conversation_mode} "
        f"action={result.action} "
        f"reaction={result.reaction!r} "
        f"overridden={result.overridden} "
        f"reason={result.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _Decision:

    def __init__(
        self,
        *,
        action="reply",
        topic_exhausted=False
    ):

        self.action = (
            action
        )

        self.topic_exhausted = (
            topic_exhausted
        )


def _self_test():

    tests = []

    # -----------------------------------------------------
    # 1. Direct silence forbidden
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="stay_silent"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_DIRECT
            ),

            user_text=(
                "Evil?"
            )
        )
    )

    tests.append(
        (
            "direct cannot silently disappear",

            (
                result.action
                ==
                ACTION_REPLY

                and

                decision.action
                ==
                ACTION_REPLY
            )
        )
    )

    # -----------------------------------------------------
    # 2. Check in continuation -> silence
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="reply"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text="Check"
        )
    )

    tests.append(
        (
            "check becomes silent",

            result.action
            ==
            ACTION_STAY_SILENT
        )
    )

    # -----------------------------------------------------
    # 3. Nice -> silence
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="reply"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text="Nice"
        )
    )

    tests.append(
        (
            "nice becomes silent",

            result.action
            ==
            ACTION_STAY_SILENT
        )
    )

    # -----------------------------------------------------
    # 4. Question always reply
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="stay_silent"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text=(
                "Und meine?"
            )
        )
    )

    tests.append(
        (
            "question overrides silence",

            result.action
            ==
            ACTION_REPLY
        )
    )

    # -----------------------------------------------------
    # 5. Brain reaction
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="react"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text=(
                "lmao das war dumm"
            )
        )
    )

    tests.append(
        (
            "brain reaction works",

            (
                result.action
                ==
                ACTION_REACT

                and

                result.reaction
                ==
                "😂"
            )
        )
    )

    # -----------------------------------------------------
    # 6. Emoji only -> silence
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="reply"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text="",

            is_emoji_only=True
        )
    )

    tests.append(
        (
            "emoji only silent",

            result.action
            ==
            ACTION_STAY_SILENT
        )
    )

    # -----------------------------------------------------
    # 7. Normal continuation remains reply
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="reply"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text=(
                "Ich hab heute Pizza bestellt"
            )
        )
    )

    tests.append(
        (
            "normal continuation replies",

            result.action
            ==
            ACTION_REPLY
        )
    )

    # -----------------------------------------------------
    # 8. Participation already committed
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="stay_silent"
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_PARTICIPATION
            ),

            user_text=(
                "irgendwas passiert"
            )
        )
    )

    tests.append(
        (
            "participation does not double-abort",

            result.action
            ==
            ACTION_REPLY
        )
    )

    # -----------------------------------------------------
    # 9. Exhausted short topic
    # -----------------------------------------------------

    decision = (
        _Decision(
            action="reply",
            topic_exhausted=True
        )
    )

    result = (
        apply_agency_guard(

            decision=decision,

            conversation_mode=(
                MODE_CONTINUATION
            ),

            user_text=(
                "jo dann passt"
            )
        )
    )

    tests.append(
        (
            "exhausted short topic silent",

            result.action
            ==
            ACTION_STAY_SILENT
        )
    )

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"AGENCY v{AGENCY_VERSION} TEST"
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

            status = (
                "PASS"
            )

            passed += 1

        else:

            status = (
                "FAIL"
            )

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
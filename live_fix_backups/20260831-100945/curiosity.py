from dataclasses import dataclass


# =========================================================
# VERSION
# =========================================================

CURIOSITY_VERSION = "1.1"


# =========================================================
# QUESTION TYPES
# =========================================================

QUESTION_NONE = "none"

QUESTION_CURIOSITY = "curiosity"

QUESTION_CLARIFICATION = "clarification"

QUESTION_SOCIAL = "social"


VALID_QUESTION_TYPES = {
    QUESTION_NONE,
    QUESTION_CURIOSITY,
    QUESTION_CLARIFICATION,
    QUESTION_SOCIAL,
}


# =========================================================
# LEVELS
# =========================================================

VALID_INFORMATION_GAPS = {
    "none",
    "low",
    "medium",
    "high",
}


VALID_TOPIC_INTEREST = {
    "low",
    "medium",
    "high",
}


# =========================================================
# RESULT
# =========================================================

@dataclass
class CuriosityResult:

    requested: bool = False

    allowed: bool = False

    question_type: str = QUESTION_NONE

    question_goal: str = ""

    curiosity_strength: float = 0.0

    information_gap: str = "none"

    topic_interest: str = "medium"

    question_pressure: float = 0.0

    recent_question_count: int = 0

    recent_two_questions: int = 0

    reason: str = "no_question_requested"


# =========================================================
# HELPERS
# =========================================================

def clamp(
    value,
    minimum=0.0,
    maximum=1.0
):

    try:

        value = float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        value = 0.0

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def normalize_level(
    value,
    allowed,
    default
):

    value = str(
        value
        or
        default
    ).strip().lower()

    if value not in allowed:

        return default

    return value


def normalize_question_type(
    value
):

    value = str(
        value
        or
        QUESTION_NONE
    ).strip().lower()

    if (
        value
        not in VALID_QUESTION_TYPES
    ):

        return QUESTION_NONE

    return value


def normalize_goal(
    value
):

    return " ".join(
        str(
            value
            or ""
        )
        .strip()
        .split()
    )[:300]


# =========================================================
# GENERIC QUESTION GOALS
# =========================================================

GENERIC_GOALS = {

    "",

    "gespräch weiterführen",

    "gespraech weiterfuehren",

    "gespräch am laufen halten",

    "gespraech am laufen halten",

    "conversation weiterführen",

    "conversation am laufen halten",

    "mehr erfahren",

    "mehr wissen",

    "interesse zeigen",

    "smalltalk",

    "gegenfrage stellen",

    "user einbeziehen",

    "gespräch fördern",

    "gespraech foerdern",
}


def goal_is_specific(
    goal
):

    goal = normalize_goal(
        goal
    )

    lowered = (
        goal.lower()
    )

    if not goal:

        return False

    if (
        lowered
        in GENERIC_GOALS
    ):

        return False

    if len(
        goal
    ) < 5:

        return False

    return True


# =========================================================
# QUESTION PRESSURE v1.1
#
# WICHTIG:
#
# Alte Version:
#
# 1 Antwort
# 1 Frage
# =
# pressure 1.00
#
# Das war falsch.
#
# Neue Idee:
#
# Wir betrachten ein Fenster von 4 Antworten.
#
# Eine einzelne Frage erzeugt nur leichten Druck.
#
# Erst mehrere Fragen hintereinander
# erzeugen echten Interview-Druck.
# =========================================================

def calculate_question_pressure(
    recent_messages,
    window=4
):

    recent_messages = [

        str(
            message
        ).strip()

        for message
        in (
            recent_messages
            or []
        )

        if str(
            message
        ).strip()
    ]

    recent_messages = (
        recent_messages[
            -window:
        ]
    )

    if not recent_messages:

        return (
            0.0,
            0,
            0
        )

    question_flags = [

        "?" in message

        for message
        in recent_messages
    ]

    question_count = sum(
        question_flags
    )

    recent_two = (
        question_flags[
            -2:
        ]
    )

    recent_two_questions = sum(
        recent_two
    )

    # -----------------------------------------------------
    # Grunddruck basiert IMMER auf dem vollen
    # Beobachtungsfenster.
    #
    # Deshalb:
    #
    # 1 Frage = 0.25
    # 2 Fragen = 0.50
    # 3 Fragen = 0.75
    # 4 Fragen = 1.00
    #
    # Nicht mehr:
    #
    # 1/1 = 1.00
    # -----------------------------------------------------

    pressure = (
        question_count
        /
        float(
            window
        )
    )

    # -----------------------------------------------------
    # Streak Pressure
    #
    # Zwei direkt aufeinanderfolgende Fragen
    # sind ein stärkeres Interview-Signal.
    # -----------------------------------------------------

    if (
        len(
            recent_two
        )
        >= 2
        and
        recent_two_questions
        ==
        2
    ):

        pressure += (
            0.25
        )

    elif (
        recent_two
        and
        recent_two[-1]
    ):

        # Eine einzelne direkt letzte Frage
        # erhöht den Druck nur leicht.
        pressure += (
            0.05
        )

    pressure = clamp(
        pressure
    )

    return (
        pressure,
        question_count,
        recent_two_questions
    )


# =========================================================
# MUTATORS
# =========================================================

def _disable_question(
    decision
):

    decision.ask_question = (
        False
    )

    return decision


def _allow_question(
    decision
):

    decision.ask_question = (
        True
    )

    return decision


# =========================================================
# COMMON RESULT
# =========================================================

def _result(
    *,
    requested,
    allowed,
    question_type,
    question_goal,
    curiosity_strength,
    information_gap,
    topic_interest,
    question_pressure,
    recent_question_count,
    recent_two_questions,
    reason
):

    return CuriosityResult(

        requested=requested,

        allowed=allowed,

        question_type=(
            question_type
        ),

        question_goal=(
            question_goal
        ),

        curiosity_strength=(
            curiosity_strength
        ),

        information_gap=(
            information_gap
        ),

        topic_interest=(
            topic_interest
        ),

        question_pressure=(
            question_pressure
        ),

        recent_question_count=(
            recent_question_count
        ),

        recent_two_questions=(
            recent_two_questions
        ),

        reason=(
            reason
        )
    )


# =========================================================
# APPLY CURIOSITY POLICY
# =========================================================

def apply_curiosity_policy(
    *,
    decision,
    recent_evilnae_messages,
    conversation_mode="direct"
) -> CuriosityResult:

    requested = bool(
        getattr(
            decision,
            "ask_question",
            False
        )
    )

    question_type = (
        normalize_question_type(
            getattr(
                decision,
                "question_type",
                QUESTION_NONE
            )
        )
    )

    question_goal = (
        normalize_goal(
            getattr(
                decision,
                "question_goal",
                ""
            )
        )
    )

    curiosity_strength = (
        clamp(
            getattr(
                decision,
                "curiosity_strength",
                0.0
            )
        )
    )

    information_gap = (
        normalize_level(

            getattr(
                decision,
                "information_gap",
                "none"
            ),

            VALID_INFORMATION_GAPS,

            "none"
        )
    )

    topic_interest = (
        normalize_level(

            getattr(
                decision,
                "topic_interest",
                "medium"
            ),

            VALID_TOPIC_INTEREST,

            "medium"
        )
    )

    (
        question_pressure,
        recent_question_count,
        recent_two_questions
    ) = (
        calculate_question_pressure(
            recent_evilnae_messages
        )
    )

    conversation_mode = str(
        conversation_mode
        or
        "direct"
    ).strip().lower()

    # =====================================================
    # NO QUESTION REQUESTED
    # =====================================================

    if not requested:

        _disable_question(
            decision
        )

        return _result(

            requested=False,

            allowed=False,

            question_type=(
                question_type
            ),

            question_goal=(
                question_goal
            ),

            curiosity_strength=(
                curiosity_strength
            ),

            information_gap=(
                information_gap
            ),

            topic_interest=(
                topic_interest
            ),

            question_pressure=(
                question_pressure
            ),

            recent_question_count=(
                recent_question_count
            ),

            recent_two_questions=(
                recent_two_questions
            ),

            reason=(
                "brain_did_not_want_question"
            )
        )

    # =====================================================
    # STRUCTURE REQUIRED
    # =====================================================

    if (
        question_type
        ==
        QUESTION_NONE
    ):

        _disable_question(
            decision
        )

        return _result(

            requested=True,

            allowed=False,

            question_type=(
                question_type
            ),

            question_goal=(
                question_goal
            ),

            curiosity_strength=(
                curiosity_strength
            ),

            information_gap=(
                information_gap
            ),

            topic_interest=(
                topic_interest
            ),

            question_pressure=(
                question_pressure
            ),

            recent_question_count=(
                recent_question_count
            ),

            recent_two_questions=(
                recent_two_questions
            ),

            reason=(
                "missing_question_type"
            )
        )

    if not goal_is_specific(
        question_goal
    ):

        _disable_question(
            decision
        )

        return _result(

            requested=True,

            allowed=False,

            question_type=(
                question_type
            ),

            question_goal=(
                question_goal
            ),

            curiosity_strength=(
                curiosity_strength
            ),

            information_gap=(
                information_gap
            ),

            topic_interest=(
                topic_interest
            ),

            question_pressure=(
                question_pressure
            ),

            recent_question_count=(
                recent_question_count
            ),

            recent_two_questions=(
                recent_two_questions
            ),

            reason=(
                "question_goal_not_specific"
            )
        )

    # =====================================================
    # CLARIFICATION
    #
    # Verständnis darf Interview-Druck überschreiben,
    # wenn die Informationslücke wirklich wichtig ist.
    # =====================================================

    if (
        question_type
        ==
        QUESTION_CLARIFICATION
    ):

        if (
            information_gap
            ==
            "high"
        ):

            _allow_question(
                decision
            )

            return _result(

                requested=True,

                allowed=True,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "needed_clarification"
                )
            )

        if (
            information_gap
            ==
            "medium"
            and
            curiosity_strength
            >=
            0.40
            and
            question_pressure
            <
            0.75
        ):

            _allow_question(
                decision
            )

            return _result(

                requested=True,

                allowed=True,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "useful_clarification"
                )
            )

        _disable_question(
            decision
        )

        return _result(

            requested=True,

            allowed=False,

            question_type=(
                question_type
            ),

            question_goal=(
                question_goal
            ),

            curiosity_strength=(
                curiosity_strength
            ),

            information_gap=(
                information_gap
            ),

            topic_interest=(
                topic_interest
            ),

            question_pressure=(
                question_pressure
            ),

            recent_question_count=(
                recent_question_count
            ),

            recent_two_questions=(
                recent_two_questions
            ),

            reason=(
                "clarification_not_needed"
            )
        )

    # =====================================================
    # GENUINE CURIOSITY
    # =====================================================

    if (
        question_type
        ==
        QUESTION_CURIOSITY
    ):

        if (
            topic_interest
            ==
            "low"
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "topic_not_interesting_enough"
                )
            )

        if (
            information_gap
            not in {
                "medium",
                "high",
            }
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "no_useful_information_gap"
                )
            )

        if (
            curiosity_strength
            <
            0.55
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "curiosity_too_low"
                )
            )

        # -------------------------------------------------
        # Hoher Interview-Druck
        #
        # Nur wirklich starke Neugier darf durch.
        # -------------------------------------------------

        if (
            question_pressure
            >=
            0.75
        ):

            exceptional_interest = (

                curiosity_strength
                >=
                0.85

                and

                information_gap
                ==
                "high"

                and

                topic_interest
                ==
                "high"
            )

            if not exceptional_interest:

                _disable_question(
                    decision
                )

                return _result(

                    requested=True,

                    allowed=False,

                    question_type=(
                        question_type
                    ),

                    question_goal=(
                        question_goal
                    ),

                    curiosity_strength=(
                        curiosity_strength
                    ),

                    information_gap=(
                        information_gap
                    ),

                    topic_interest=(
                        topic_interest
                    ),

                    question_pressure=(
                        question_pressure
                    ),

                    recent_question_count=(
                        recent_question_count
                    ),

                    recent_two_questions=(
                        recent_two_questions
                    ),

                    reason=(
                        "recent_question_pressure"
                    )
                )

        # -------------------------------------------------
        # Mittlerer Druck.
        #
        # Eine mittelmäßige Frage wird blockiert.
        #
        # Eine klar interessante Frage darf bleiben.
        # -------------------------------------------------

        elif (
            question_pressure
            >=
            0.50
            and
            curiosity_strength
            <
            0.75
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "question_not_worth_pressure"
                )
            )

        _allow_question(
            decision
        )

        return _result(

            requested=True,

            allowed=True,

            question_type=(
                question_type
            ),

            question_goal=(
                question_goal
            ),

            curiosity_strength=(
                curiosity_strength
            ),

            information_gap=(
                information_gap
            ),

            topic_interest=(
                topic_interest
            ),

            question_pressure=(
                question_pressure
            ),

            recent_question_count=(
                recent_question_count
            ),

            recent_two_questions=(
                recent_two_questions
            ),

            reason=(
                "genuine_curiosity"
            )
        )

    # =====================================================
    # SOCIAL QUESTION
    #
    # Bewusst selten.
    # =====================================================

    if (
        question_type
        ==
        QUESTION_SOCIAL
    ):

        if (
            topic_interest
            !=
            "high"
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "social_question_interest_too_low"
                )
            )

        if (
            curiosity_strength
            <
            0.75
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "social_question_curiosity_too_low"
                )
            )

        # Eine Social-Gegenfrage direkt nach
        # einer anderen Frage wirkt schnell interviewig.

        if (
            recent_two_questions
            >=
            1
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "social_question_too_soon"
                )
            )

        if (
            question_pressure
            >=
            0.50
        ):

            _disable_question(
                decision
            )

            return _result(

                requested=True,

                allowed=False,

                question_type=(
                    question_type
                ),

                question_goal=(
                    question_goal
                ),

                curiosity_strength=(
                    curiosity_strength
                ),

                information_gap=(
                    information_gap
                ),

                topic_interest=(
                    topic_interest
                ),

                question_pressure=(
                    question_pressure
                ),

                recent_question_count=(
                    recent_question_count
                ),

                recent_two_questions=(
                    recent_two_questions
                ),

                reason=(
                    "social_question_pressure"
                )
            )

        _allow_question(
            decision
        )

        return _result(

            requested=True,

            allowed=True,

            question_type=(
                question_type
            ),

            question_goal=(
                question_goal
            ),

            curiosity_strength=(
                curiosity_strength
            ),

            information_gap=(
                information_gap
            ),

            topic_interest=(
                topic_interest
            ),

            question_pressure=(
                question_pressure
            ),

            recent_question_count=(
                recent_question_count
            ),

            recent_two_questions=(
                recent_two_questions
            ),

            reason=(
                "natural_social_curiosity"
            )
        )

    # =====================================================
    # FALLBACK
    # =====================================================

    _disable_question(
        decision
    )

    return _result(

        requested=True,

        allowed=False,

        question_type=(
            question_type
        ),

        question_goal=(
            question_goal
        ),

        curiosity_strength=(
            curiosity_strength
        ),

        information_gap=(
            information_gap
        ),

        topic_interest=(
            topic_interest
        ),

        question_pressure=(
            question_pressure
        ),

        recent_question_count=(
            recent_question_count
        ),

        recent_two_questions=(
            recent_two_questions
        ),

        reason=(
            "question_policy_fallback"
        )
    )


# =========================================================
# FINAL QUESTION OUTPUT GUARD
#
# Curiosity ist eine logische Entscheidung.
#
# Writer und Qwen dürfen diese Entscheidung
# danach NICHT wieder verändern.
# =========================================================

def question_output_violation_reasons(
    answer: str,
    result: CuriosityResult
) -> list[str]:

    answer = str(
        answer
        or ""
    ).strip()

    if not answer:

        return []

    question_marks = (
        answer.count(
            "?"
        )
    )

    reasons = []

    # -----------------------------------------------------
    # Curiosity sagt NEIN.
    #
    # Dann darf Writer/Qwen keine neue
    # Gegenfrage einschmuggeln.
    # -----------------------------------------------------

    if (
        not result.allowed
        and
        question_marks
        >
        0
    ):

        reasons.append(
            "question_not_allowed_by_curiosity"
        )

    # -----------------------------------------------------
    # Curiosity sagt JA.
    #
    # Trotzdem maximal EINE Frage.
    #
    # Verhindert:
    #
    # "wie wars?
    #  hast du Bosse gemacht
    #  oder bist du rumgelaufen?"
    # -----------------------------------------------------

    if (
        result.allowed
        and
        question_marks
        >
        1
    ):

        reasons.append(
            "multiple_questions_after_curiosity"
        )

    return reasons


# =========================================================
# WRITER GUIDANCE
# =========================================================

def format_curiosity_for_writer(
    result: CuriosityResult
) -> str:

    if not result.allowed:

        return """
[CURIOSITY / QUESTION POLICY]

Evilnae hat entschieden,
in dieser Antwort KEINE Frage zu stellen.

Das ist eine feste Response-Plan-Entscheidung.

Keine Gegenfrage anhängen.

Auch nicht:

- "und du?"
- "wie sieht es bei dir aus?"
- "was hast du gemacht?"
- "was meinst du?"
- "wie war es?"
- "was spielst du?"
- "oder hast du ...?"

Die Antwort darf einfach enden.

Nicht versuchen,
das Gespräch künstlich weiterzuführen.

WICHTIG:

0 Fragezeichen.
""".strip()

    if (
        result.question_type
        ==
        QUESTION_CLARIFICATION
    ):

        return f"""
[CURIOSITY / QUESTION POLICY]

Evilnae möchte genau EINE
Clarification-Frage stellen.

Ziel:

{result.question_goal}

Die Frage soll genau die Information klären,
die zum Verständnis fehlt.

Maximal EINE Frage.
Maximal EIN Fragezeichen.

Keine zweite Gegenfrage.
Keine Auswahl aus mehreren Fragen.
Kein Interview.
""".strip()

    if (
        result.question_type
        ==
        QUESTION_CURIOSITY
    ):

        return f"""
[CURIOSITY / QUESTION POLICY]

Evilnae ist an einem konkreten Detail
wirklich interessiert.

Question goal:

{result.question_goal}

Information gap:
{result.information_gap}

Topic interest:
{result.topic_interest}

Curiosity strength:
{result.curiosity_strength:.2f}

Formuliere genau EINE
kurze natürliche Frage,
die dieses Ziel erfüllt.

Maximal EIN Fragezeichen.

Nicht:

"wie wars?
hast du X gemacht
oder Y?"

Nicht mehrere Alternativen abfragen.

Nicht interviewen.

Ein Gedanke + eine Frage
ODER einfach nur die Frage
ist völlig ausreichend.
""".strip()

    return f"""
[CURIOSITY / QUESTION POLICY]

Eine einzelne lockere Social-Frage
ist in diesem Moment erlaubt.

Ziel:

{result.question_goal}

Diese Frage entsteht aus echtem Interesse,
nicht aus Gesprächspflicht.

Maximal EINE Frage.
Maximal EIN Fragezeichen.

Keine zweite Follow-up-Frage.
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_curiosity_debug(
    result: CuriosityResult
) -> str:

    return (

        "[CURIOSITY] "
        f"v={CURIOSITY_VERSION} "
        f"requested={result.requested} "
        f"allowed={result.allowed} "
        f"type={result.question_type} "
        f"curiosity="
        f"{result.curiosity_strength:.2f} "
        f"gap={result.information_gap} "
        f"interest={result.topic_interest} "
        f"pressure="
        f"{result.question_pressure:.2f} "
        f"recent_questions="
        f"{result.recent_question_count} "
        f"recent_two="
        f"{result.recent_two_questions} "
        f"goal={result.question_goal!r} "
        f"reason={result.reason}"
    )


# =========================================================
# SELF TEST
# =========================================================

class _Decision:

    def __init__(
        self,
        *,
        ask_question=False,
        question_type="none",
        question_goal="",
        curiosity_strength=0.0,
        information_gap="none",
        topic_interest="medium"
    ):

        self.ask_question = (
            ask_question
        )

        self.question_type = (
            question_type
        )

        self.question_goal = (
            question_goal
        )

        self.curiosity_strength = (
            curiosity_strength
        )

        self.information_gap = (
            information_gap
        )

        self.topic_interest = (
            topic_interest
        )


def _self_test():

    tests = []

    # -----------------------------------------------------
    # 1
    # -----------------------------------------------------

    (
        pressure,
        count,
        recent_two
    ) = calculate_question_pressure(
        []
    )

    tests.append(
        (
            "empty history pressure zero",

            pressure
            ==
            0.0
        )
    )

    # -----------------------------------------------------
    # 2
    #
    # Wichtigster Regression Test:
    #
    # 1 Frage darf NICHT wieder pressure 1.00 werden.
    # -----------------------------------------------------

    (
        pressure,
        count,
        recent_two
    ) = calculate_question_pressure(
        [
            "wie wars?"
        ]
    )

    tests.append(
        (
            "single question is only light pressure",

            (
                0.20
                <=
                pressure
                <=
                0.35
            )
        )
    )

    # -----------------------------------------------------
    # 3
    # -----------------------------------------------------

    (
        pressure,
        count,
        recent_two
    ) = calculate_question_pressure(
        [
            "wie wars?",
            "welcher boss?"
        ]
    )

    tests.append(
        (
            "two consecutive questions create pressure",

            pressure
            >=
            0.70
        )
    )

    # -----------------------------------------------------
    # 4
    #
    # Genau dein Elden Ring Fall:
    #
    # Eine Frage vorher.
    # Neue echte Info-Lücke.
    # Curiosity .70.
    #
    # MUSS erlaubt bleiben.
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "herausfinden welcher Boss "
            "den User gestoppt hat"
        ),

        curiosity_strength=0.70,

        information_gap="medium",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "wie war dein Elden Ring Run?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "boss curiosity survives one prior question",

            result.allowed
        )
    )

    # -----------------------------------------------------
    # 5
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "wissen warum der User "
            "das Spiel beendet hat"
        ),

        curiosity_strength=0.65,

        information_gap="medium",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "wie wars?",
                "welcher boss?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "interview loop blocked after two questions",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 6
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "wissen welches überraschende "
            "Ereignis gerade passiert ist"
        ),

        curiosity_strength=0.92,

        information_gap="high",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "wie wars?",
                "was ist passiert?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "exceptional curiosity may override pressure",

            result.allowed
        )
    )

    # -----------------------------------------------------
    # 7
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=False
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "brain no question stays no question",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 8
    # -----------------------------------------------------

    violations = (
        question_output_violation_reasons(

            (
                "geht so, und bei dir?"
            ),

            result
        )
    )

    tests.append(
        (
            "qwen cannot reintroduce blocked question",

            (
                "question_not_allowed_by_curiosity"

                in
                violations
            )
        )
    )

    # -----------------------------------------------------
    # 9
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "herausfinden welcher Boss "
            "gemeint ist"
        ),

        curiosity_strength=0.80,

        information_gap="high",

        topic_interest="high"
    )

    allowed_result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[],

            conversation_mode="continuation"
        )
    )

    violations = (
        question_output_violation_reasons(

            (
                "wie wars? "
                "welcher boss war das?"
            ),

            allowed_result
        )
    )

    tests.append(
        (
            "multiple questions blocked",

            (
                "multiple_questions_after_curiosity"

                in
                violations
            )
        )
    )

    # -----------------------------------------------------
    # 10
    # -----------------------------------------------------

    violations = (
        question_output_violation_reasons(

            (
                "welcher boss war das?"
            ),

            allowed_result
        )
    )

    tests.append(
        (
            "single allowed question accepted",

            not violations
        )
    )

    # -----------------------------------------------------
    # 11
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="social",

        question_goal=(
            "wissen welches Spiel "
            "der User gerade mag"
        ),

        curiosity_strength=0.80,

        information_gap="low",

        topic_interest="high"
    )

    social_result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "gaming geht schon klar.",
                "kein fester go-to."
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "social question can still happen occasionally",

            social_result.allowed
        )
    )

    # -----------------------------------------------------
    # 12
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="social",

        question_goal=(
            "wissen was Hanae gerade macht"
        ),

        curiosity_strength=0.90,

        information_gap="low",

        topic_interest="high"
    )

    social_result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "wie gehts dir?",
                "alles gut."
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "social question not directly after question",

            not social_result.allowed
        )
    )

    # -----------------------------------------------------
    # 13
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="clarification",

        question_goal=(
            "klären wen der User mit sie meint"
        ),

        curiosity_strength=0.30,

        information_gap="high",

        topic_interest="medium"
    )

    clarification_result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "was meinst du?",
                "hä?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "important clarification survives pressure",

            clarification_result.allowed
        )
    )

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    passed = 0

    print("")
    print(
        "============================================"
    )

    print(
        f"CURIOSITY v"
        f"{CURIOSITY_VERSION} TEST"
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
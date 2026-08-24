from dataclasses import dataclass


# =========================================================
# VERSION
# =========================================================

CURIOSITY_VERSION = "1.0"


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
        or default
    ).strip().lower()

    if value not in allowed:

        return default

    return value


def normalize_question_type(
    value
):

    value = str(
        value
        or QUESTION_NONE
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
# GENERIC / BAD QUESTION GOALS
#
# Eine Frage braucht einen konkreten Zweck.
#
# Nicht:
#
# "Gespräch weiterführen"
# "mehr erfahren"
# "Interesse zeigen"
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
# QUESTION PRESSURE
#
# Keine harte Quote.
#
# Das ist nur ein soziales Signal:
#
# Hat Evilnae gerade schon ständig gefragt?
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

    question_count = sum(

        1

        for message
        in recent_messages

        if "?" in message
    )

    recent_two = (
        recent_messages[
            -2:
        ]
    )

    recent_two_questions = sum(

        1

        for message
        in recent_two

        if "?" in message
    )

    pressure = clamp(

        question_count
        /
        max(
            1,
            min(
                3,
                len(
                    recent_messages
                )
            )
        )
    )

    return (
        pressure,
        question_count,
        recent_two_questions
    )


# =========================================================
# DISABLE QUESTION
# =========================================================

def _disable_question(
    decision
):

    decision.ask_question = (
        False
    )

    return decision


# =========================================================
# ALLOW QUESTION
# =========================================================

def _allow_question(
    decision
):

    decision.ask_question = (
        True
    )

    return decision


# =========================================================
# APPLY CURIOSITY POLICY
#
# Brain denkt frei.
#
# Dieses Modul prüft danach:
#
# Ist die Frage wirklich begründet?
#
# Es entscheidet NICHT anhand
# einer Zufallswahrscheinlichkeit.
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
    ) = calculate_question_pressure(
        recent_evilnae_messages
    )

    conversation_mode = str(
        conversation_mode
        or
        "direct"
    ).strip().lower()

    # =====================================================
    # Brain hat gar keine Frage gewollt.
    # =====================================================

    if not requested:

        _disable_question(
            decision
        )

        return CuriosityResult(

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

            reason=(
                "brain_did_not_want_question"
            )
        )

    # =====================================================
    # Eine Frage braucht einen konkreten Zweck.
    # =====================================================

    if (
        question_type
        ==
        QUESTION_NONE
    ):

        _disable_question(
            decision
        )

        return CuriosityResult(

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

        return CuriosityResult(

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

            reason=(
                "question_goal_not_specific"
            )
        )

    # =====================================================
    # CLARIFICATION
    #
    # Evilnae versteht sonst etwas Wichtiges nicht.
    #
    # Diese Fragen dürfen auch dann vorkommen,
    # wenn sie vorher schon gefragt hat.
    #
    # Verständnis ist wichtiger als eine künstliche
    # Anti-Frage-Quote.
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

            return CuriosityResult(

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
            0.80
        ):

            _allow_question(
                decision
            )

            return CuriosityResult(

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

                reason=(
                    "useful_clarification"
                )
            )

        _disable_question(
            decision
        )

        return CuriosityResult(

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

            reason=(
                "clarification_not_needed"
            )
        )

    # =====================================================
    # CURIOSITY
    #
    # "Ich will das wirklich wissen."
    #
    # Dafür braucht Evilnae:
    #
    # - echtes Interesse
    # - eine Informationslücke
    # - genug Neugier
    #
    # Beispiel:
    #
    # "Ich bin an einem Boss hängen geblieben."
    #
    # Wenn Gaming sie interessiert:
    # "welcher boss?"
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

            return CuriosityResult(

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

            return CuriosityResult(

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

            return CuriosityResult(

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

                reason=(
                    "curiosity_too_low"
                )
            )

        # -------------------------------------------------
        # Schon viele Fragen.
        #
        # Eine wirklich starke neue Informationslücke
        # darf trotzdem durchkommen.
        # -------------------------------------------------

        if (
            question_pressure
            >=
            0.66
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

                return CuriosityResult(

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

                    reason=(
                        "recent_question_pressure"
                    )
                )

        elif (
            question_pressure
            >=
            0.33
            and
            curiosity_strength
            <
            0.70
        ):

            _disable_question(
                decision
            )

            return CuriosityResult(

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

                reason=(
                    "question_not_worth_pressure"
                )
            )

        _allow_question(
            decision
        )

        return CuriosityResult(

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

            reason=(
                "genuine_curiosity"
            )
        )

    # =====================================================
    # SOCIAL QUESTION
    #
    # Diese Kategorie darf existieren.
    #
    # Aber:
    #
    # "und du?"
    #
    # darf NICHT das Standard-Ende jeder Antwort sein.
    #
    # Social Questions brauchen:
    #
    # - echtes Thema-Interesse
    # - starke aktuelle Neugier
    # - wenig Recent Question Pressure
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

            return CuriosityResult(

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

            return CuriosityResult(

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

                reason=(
                    "social_question_curiosity_too_low"
                )
            )

        if (
            recent_two_questions
            >=
            1
        ):

            _disable_question(
                decision
            )

            return CuriosityResult(

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

            return CuriosityResult(

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

                reason=(
                    "social_question_pressure"
                )
            )

        _allow_question(
            decision
        )

        return CuriosityResult(

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

    return CuriosityResult(

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

        reason=(
            "question_policy_fallback"
        )
    )


# =========================================================
# WRITER GUIDANCE
# =========================================================

def format_curiosity_for_writer(
    result: CuriosityResult
) -> str:

    if not result.allowed:

        return """
[CURIOSITY / QUESTION POLICY]

Keine Gegenfrage anhängen.

Die Antwort darf einfach enden.

Nicht künstlich:

- "und du?"
- "was meinst du?"
- "wie sieht es bei dir aus?"
- "was machst du so?"

anhängen, nur um das Gespräch
weiterlaufen zu lassen.

Wenn die eigentliche Reaktion
gesagt ist, darf die Nachricht vorbei sein.
""".strip()

    if (
        result.question_type
        ==
        QUESTION_CLARIFICATION
    ):

        return f"""
[CURIOSITY / QUESTION POLICY]

Eine kurze Clarification-Frage ist sinnvoll.

Ziel der Frage:

{result.question_goal}

Die Frage soll Evilnae helfen,
den aktuellen Inhalt wirklich zu verstehen.

Nur EINE Frage.

Keine zusätzliche Social-Gegenfrage.
Kein Interview-Stil.
""".strip()

    if (
        result.question_type
        ==
        QUESTION_CURIOSITY
    ):

        return f"""
[CURIOSITY / QUESTION POLICY]

Evilnae ist an diesem konkreten Punkt
wirklich neugierig.

Ziel der Frage:

{result.question_goal}

Information gap:
{result.information_gap}

Topic interest:
{result.topic_interest}

Curiosity:
{result.curiosity_strength:.2f}

Eine kurze natürliche Frage ist sinnvoll.

Nur EINE Frage.

Sie soll genau die Information betreffen,
die Evilnae tatsächlich wissen möchte.

Nicht noch eine zweite Frage anhängen.
Nicht wie ein Interviewer formulieren.
""".strip()

    return f"""
[CURIOSITY / QUESTION POLICY]

Eine lockere Social-Frage ist
in diesem Moment erlaubt.

Ziel:

{result.question_goal}

Sie ist NICHT nötig,
weil ein Bot das Gespräch
am Leben halten muss.

Sie entsteht aus echtem Interesse.

Nur EINE kurze Frage.
Keine zweite Frage.
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
    # 1. No question requested
    # -----------------------------------------------------

    decision = _Decision(
        ask_question=False
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[],

            conversation_mode="direct"
        )
    )

    tests.append(
        (
            "no requested question stays off",

            (
                not result.allowed
                and
                not decision.ask_question
            )
        )
    )

    # -----------------------------------------------------
    # 2. Genuine Gaming Curiosity
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "herausfinden welcher Boss "
            "den User gestoppt hat"
        ),

        curiosity_strength=0.82,

        information_gap="high",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "elden ring ist schon brutal."
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "genuine curiosity allowed",

            (
                result.allowed
                and
                decision.ask_question
            )
        )
    )

    # -----------------------------------------------------
    # 3. Low curiosity
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "wissen welches Essen gemeint ist"
        ),

        curiosity_strength=0.30,

        information_gap="high",

        topic_interest="medium"
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
            "low curiosity blocked",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 4. Low topic interest
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "mehr über das Thema erfahren"
        ),

        curiosity_strength=0.90,

        information_gap="high",

        topic_interest="low"
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
            "low interest blocked",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 5. No information gap
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "wissen welcher Boss gemeint ist"
        ),

        curiosity_strength=0.90,

        information_gap="none",

        topic_interest="high"
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
            "no information gap blocked",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 6. Important clarification allowed
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="clarification",

        question_goal=(
            "klären welchen Boss "
            "der User beschreibt"
        ),

        curiosity_strength=0.45,

        information_gap="high",

        topic_interest="medium"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "was genau meinst du?",
                "ah okay?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "needed clarification allowed",

            result.allowed
        )
    )

    # -----------------------------------------------------
    # 7. Weak clarification blocked
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="clarification",

        question_goal=(
            "noch ein kleines Detail erfahren"
        ),

        curiosity_strength=0.20,

        information_gap="low",

        topic_interest="medium"
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
            "weak clarification blocked",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 8. Social question occasionally allowed
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="social",

        question_goal=(
            "wissen welche Games "
            "der User aktuell mag"
        ),

        curiosity_strength=0.80,

        information_gap="low",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "gaming geht eigentlich immer.",
                "ich hab da keinen festen go-to."
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "social question can happen",

            result.allowed
        )
    )

    # -----------------------------------------------------
    # 9. Social question not after recent question
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="social",

        question_goal=(
            "wissen welches Spiel "
            "der User gerade zockt"
        ),

        curiosity_strength=0.90,

        information_gap="low",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "welcher boss war das?",
                "ah der 💀"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "social followup not too soon",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 10. Generic goal blocked
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="social",

        question_goal=(
            "Gespräch weiterführen"
        ),

        curiosity_strength=1.0,

        information_gap="medium",

        topic_interest="high"
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
            "generic conversation goal blocked",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 11. Interview pressure blocks normal curiosity
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "wissen warum der User "
            "das Spiel aufgehört hat"
        ),

        curiosity_strength=0.70,

        information_gap="medium",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "was spielst du?",
                "welches davon?",
                "warum genau?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "question pressure blocks interview loop",

            not result.allowed
        )
    )

    # -----------------------------------------------------
    # 12. Strong important curiosity may override pressure
    # -----------------------------------------------------

    decision = _Decision(

        ask_question=True,

        question_type="curiosity",

        question_goal=(
            "herausfinden welcher Boss "
            "der zentrale Punkt der Story ist"
        ),

        curiosity_strength=0.92,

        information_gap="high",

        topic_interest="high"
    )

    result = (
        apply_curiosity_policy(

            decision=decision,

            recent_evilnae_messages=[
                "was hast du gezockt?",
                "wie weit warst du?",
                "war das schwer?"
            ],

            conversation_mode="continuation"
        )
    )

    tests.append(
        (
            "very strong curiosity may override pressure",

            result.allowed
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
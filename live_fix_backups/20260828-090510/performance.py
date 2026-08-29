import contextvars
import re
import time

from dataclasses import dataclass


# =========================================================
# VERSION
# =========================================================

PERFORMANCE_VERSION = "1.0"


# =========================================================
# CONFIG
# =========================================================

RESPONSE_REPAIR_BUDGET = 2

LOCAL_VOICE_FAST_PATH_MAX_WORDS = 10


# =========================================================
# CONTEXT LOCAL STATE
#
# ContextVar:
#
# Jede Discord-Nachricht hat ihren eigenen
# Repair-Zähler, auch wenn mehrere Antworten
# gleichzeitig laufen.
# =========================================================

_repair_used_var = contextvars.ContextVar(
    "evilnae_response_repair_used",
    default=0,
)


# =========================================================
# RESULT
# =========================================================

@dataclass
class RepairBudgetDecision:

    allowed: bool

    used_before: int

    used_after: int

    limit: int

    label: str = ""


# =========================================================
# RESPONSE TIMER
# =========================================================

def start_response_timer():

    return (
        time.perf_counter()
    )


def elapsed_response_time(
    started_at
):

    try:

        return max(
            0.0,
            time.perf_counter()
            -
            float(
                started_at
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return 0.0


# =========================================================
# REPAIR BUDGET
# =========================================================

def reset_response_repair_budget():

    _repair_used_var.set(
        0
    )


def get_response_repair_count():

    return int(
        _repair_used_var.get()
        or
        0
    )


def claim_response_repair_slot(
    label=""
):

    used = (
        get_response_repair_count()
    )

    if (
        used
        >=
        RESPONSE_REPAIR_BUDGET
    ):

        return (
            RepairBudgetDecision(

                allowed=False,

                used_before=used,

                used_after=used,

                limit=(
                    RESPONSE_REPAIR_BUDGET
                ),

                label=str(
                    label
                    or ""
                )
            )
        )

    after = (
        used
        +
        1
    )

    _repair_used_var.set(
        after
    )

    return (
        RepairBudgetDecision(

            allowed=True,

            used_before=used,

            used_after=after,

            limit=(
                RESPONSE_REPAIR_BUDGET
            ),

            label=str(
                label
                or ""
            )
        )
    )


def format_repair_budget_debug(
    decision
):

    return (
        "[REPAIR BUDGET] "
        f"v={PERFORMANCE_VERSION} "
        f"allowed={decision.allowed} "
        f"used="
        f"{decision.used_after}/"
        f"{decision.limit} "
        f"label={decision.label!r}"
    )


# =========================================================
# LOCAL VOICE FAST PATH
#
# Qwen muss nicht jeden bereits sauberen
# 5-Wort-Satz erneut analysieren.
#
# Nur SEHR konservativ skippen:
#
# - keine Coherence-Probleme
# - kein Rewrite-Druck
# - ein kurzer Gedanke
# - keine Frage
# - kein offensichtlicher Bot-Wrapper
#
# Alles Komplexere geht weiterhin durch Qwen.
# =========================================================

GENERIC_FAST_PATH_BLOCKERS = [

    re.compile(
        r"\bdas\s+klingt\b",
        re.IGNORECASE
    ),

    re.compile(
        (
            r"\bich\s+kann\s+"
            r"(?:das\s+)?"
            r"(?:verstehen|nachvollziehen)\b"
        ),
        re.IGNORECASE
    ),

    re.compile(
        (
            r"\bich\s+kann\s+mir\s+"
            r"(?:gut\s+)?vorstellen\b"
        ),
        re.IGNORECASE
    ),

    re.compile(
        r"\bviel\s+erfolg\b",
        re.IGNORECASE
    ),

    re.compile(
        (
            r"\b(?:"
            r"lass\s+mich\s+wissen|"
            r"sag\s+bescheid"
            r")\b"
        ),
        re.IGNORECASE
    ),

    re.compile(
        r"\bich\s+bin\s+gespannt\b",
        re.IGNORECASE
    ),

    re.compile(
        (
            r"\b(?:schön|gut)"
            r"\s+zu\s+hören\b"
        ),
        re.IGNORECASE
    ),

    re.compile(
        r"\bdu\s+schaffst\s+das\b",
        re.IGNORECASE
    ),
]


def should_fast_path_local_voice(
    draft,
    *,
    violation_score=0,
    deterministic_pressure=False
):

    text = str(
        draft
        or ""
    ).strip()

    if not text:

        return False

    if deterministic_pressure:

        return False

    try:

        violation_score = int(
            violation_score
            or
            0
        )

    except (
        TypeError,
        ValueError
    ):

        violation_score = (
            999
        )

    if violation_score > 0:

        return False

    # -----------------------------------------------------
    # Fragen weiterhin durch Voice.
    #
    # Gerade dort sind Rhythmus und Perspektive
    # besonders wichtig.
    # -----------------------------------------------------

    if "?" in text:

        return False

    # -----------------------------------------------------
    # Mehrzeilige Antworten nicht fast-pathen.
    # -----------------------------------------------------

    if "\n" in text:

        return False

    words = re.findall(
        r"[A-Za-zÄÖÜäöüß0-9]+",
        text
    )

    if len(
        words
    ) < 2:

        return False

    if (
        len(
            words
        )
        >
        LOCAL_VOICE_FAST_PATH_MAX_WORDS
    ):

        return False

    # -----------------------------------------------------
    # Mehrere Gedanken?
    #
    # Dann lieber Voice prüfen lassen.
    # -----------------------------------------------------

    sentence_marks = re.findall(
        r"[.!]+",
        text
    )

    if len(
        sentence_marks
    ) > 1:

        return False

    # -----------------------------------------------------
    # Offensichtlicher Assistant Wrapper?
    #
    # Nicht skippen.
    # -----------------------------------------------------

    if any(

        pattern.search(
            text
        )

        for pattern
        in GENERIC_FAST_PATH_BLOCKERS
    ):

        return False

    return True


# =========================================================
# SELF TEST
# =========================================================

def _self_test():

    tests = []

    # -----------------------------------------------------
    # REPAIR BUDGET
    # -----------------------------------------------------

    reset_response_repair_budget()

    first = (
        claim_response_repair_slot(
            "first"
        )
    )

    second = (
        claim_response_repair_slot(
            "second"
        )
    )

    third = (
        claim_response_repair_slot(
            "third"
        )
    )

    tests.append(
        (
            "first repair allowed",
            (
                first.allowed
                and
                first.used_after
                ==
                1
            )
        )
    )

    tests.append(
        (
            "second repair allowed",
            (
                second.allowed
                and
                second.used_after
                ==
                2
            )
        )
    )

    tests.append(
        (
            "third repair blocked",
            (
                not third.allowed
                and
                third.used_after
                ==
                2
            )
        )
    )

    # -----------------------------------------------------
    # LOCAL VOICE FAST PATH
    # -----------------------------------------------------

    tests.append(
        (
            "clean short reply fast path",
            should_fast_path_local_voice(
                "der boss lebt aus trotz."
            )
        )
    )

    tests.append(
        (
            "question keeps local voice",
            not (
                should_fast_path_local_voice(
                    "ernsthaft, warum?"
                )
            )
        )
    )

    tests.append(
        (
            "generic wrapper keeps local voice",
            not (
                should_fast_path_local_voice(
                    "das klingt echt spannend."
                )
            )
        )
    )

    tests.append(
        (
            "coherence pressure keeps local voice",
            not (
                should_fast_path_local_voice(
                    "jo, passt.",
                    deterministic_pressure=True
                )
            )
        )
    )

    tests.append(
        (
            "violation keeps local voice",
            not (
                should_fast_path_local_voice(
                    "jo, passt.",
                    violation_score=1
                )
            )
        )
    )

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"PERFORMANCE "
        f"v{PERFORMANCE_VERSION} TEST"
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
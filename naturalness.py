import re

from dataclasses import dataclass, field


# =========================================================
# VERSION
# =========================================================

NATURALNESS_VERSION = "1.0"


# =========================================================
# SOFT BOT PATTERNS
#
# Ein einzelnes Pattern ist nicht zwingend schlimm.
#
# Mehrere davon in einer kurzen Discord-Nachricht
# erzeugen aber genau dieses:
#
# "AI versucht locker zu klingen"
#
# Gefühl.
# =========================================================

SOFT_BOT_PATTERNS = {

    "taste_is_subjective":
        re.compile(
            r"\bgeschmack\s+"
            r"(?:ist|bleibt)\s+"
            r"(?:ja\s+)?subjektiv\b",
            flags=re.IGNORECASE
        ),

    "but_hey":
        re.compile(
            r"\baber\s+hey\b",
            flags=re.IGNORECASE
        ),

    "sounds_like":
        re.compile(
            r"\bdas\s+klingt\s+"
            r"(?:ja\s+|erstmal\s+|echt\s+|"
            r"wirklich\s+|total\s+)?"
            r"(?:nach|wie)\b",
            flags=re.IGNORECASE
        ),

    "sounds_adjective":
        re.compile(
            r"\bdas\s+klingt\s+"
            r"(?:ja\s+|erstmal\s+|echt\s+|"
            r"wirklich\s+|total\s+)?"
            r"(?:spannend|crazy|wild|cool|gut)\b",
            flags=re.IGNORECASE
        ),

    "never_thought":
        re.compile(
            r"\bich\s+hätte\s+nie\s+gedacht\b",
            flags=re.IGNORECASE
        ),

    "maybe_i_should":
        re.compile(
            r"\bvielleicht\s+sollte\s+ich\b",
            flags=re.IGNORECASE
        ),

    "everyone_has_own_taste":
        re.compile(
            r"\bjeder\s+hat\s+"
            r"(?:halt\s+)?"
            r"(?:seinen|ihren)\s+"
            r"eigenen\s+geschmack\b",
            flags=re.IGNORECASE
        ),

    "personally_i_stick":
        re.compile(
            r"\bich\s+persönlich\b"
            r".{0,50}"
            r"\b(?:bleib|halte|mag)\w*\b",
            flags=re.IGNORECASE
        ),

    "interesting_choice":
        re.compile(
            r"\b(?:interessante|spezielle|"
            r"eigenwillige)\s+wahl\b",
            flags=re.IGNORECASE
        ),

    "generic_validation":
        re.compile(
            r"\b(?:kann ich verstehen|"
            r"versteh ich total|"
            r"klingt nachvollziehbar)\b",
            flags=re.IGNORECASE
        ),

    "service_success":
        re.compile(
            r"\bviel\s+erfolg\b",
            flags=re.IGNORECASE
        ),

    "generic_excited":
        re.compile(
            r"\bich\s+bin\s+gespannt\b",
            flags=re.IGNORECASE
        ),
}


# =========================================================
# WEIGHTS
#
# Manche Patterns sind allein schon
# stark bot-typisch.
# =========================================================

PATTERN_WEIGHTS = {

    "taste_is_subjective":
        1,

    "but_hey":
        1,

    "sounds_like":
        1,

    "sounds_adjective":
        1,

    "never_thought":
        1,

    "maybe_i_should":
        1,

    "everyone_has_own_taste":
        2,

    "personally_i_stick":
        1,

    "interesting_choice":
        1,

    "generic_validation":
        1,

    "service_success":
        2,

    "generic_excited":
        2,
}


# =========================================================
# ANALYSIS
# =========================================================

@dataclass
class NaturalnessAnalysis:

    matches: list[str] = field(
        default_factory=list
    )

    score: int = 0

    rewrite_required: bool = False

    reason: str = "clean"


# =========================================================
# ANALYZE
# =========================================================

def analyze_naturalness(
    text: str
) -> NaturalnessAnalysis:

    text = (
        text
        or ""
    )

    matches = []

    score = 0

    for (
        name,
        pattern
    ) in SOFT_BOT_PATTERNS.items():

        if pattern.search(
            text
        ):

            matches.append(
                name
            )

            score += (
                PATTERN_WEIGHTS.get(
                    name,
                    1
                )
            )

    # -----------------------------------------------------
    # Zwei weiche Signale
    # oder ein hart gewichtetes Signal.
    # -----------------------------------------------------

    rewrite_required = (
        score >= 2
    )

    if rewrite_required:

        reason = (
            "soft_bot_pattern_cluster"
        )

    else:

        reason = (
            "clean"
        )

    return NaturalnessAnalysis(

        matches=(
            matches
        ),

        score=(
            score
        ),

        rewrite_required=(
            rewrite_required
        ),

        reason=(
            reason
        )
    )


# =========================================================
# WRITER GUIDANCE
# =========================================================

def format_naturalness_for_writer(
    analysis: NaturalnessAnalysis
) -> str:

    if not analysis.rewrite_required:

        return (
            "[NATURALNESS]\n"
            "No strong soft-bot cluster."
        )

    matches = (
        ", ".join(
            analysis.matches
        )
    )

    return f"""
[NATURALNESS GUARD v{NATURALNESS_VERSION}]

Die Antwort enthält mehrere
typische LLM-/Assistant-Sprachmuster.

Gefundene Muster:

{matches}

Score:
{analysis.score}

Formuliere denselben Gedanken
wie eine normale Discord-Person.

WICHTIG:

Nicht einfach ein anderes
"cool / wild / spannend"-Template benutzen.

Nicht erklären,
warum die Antwort natürlicher ist.

Keine Service-Struktur.

Keine künstliche Zusammenfassung.

Lieber ein konkreter,
kleiner eigener Gedanke.
""".strip()


# =========================================================
# DEBUG
# =========================================================

def format_naturalness_debug(
    analysis: NaturalnessAnalysis
) -> str:

    return (

        "[NATURALNESS] "
        f"v={NATURALNESS_VERSION} "
        f"score={analysis.score} "
        f"rewrite="
        f"{analysis.rewrite_required} "
        f"matches={analysis.matches}"
    )


# =========================================================
# SELF TEST
# =========================================================

def _self_test():

    tests = []

    first_real_example = (
        "ananas auf pizza? klingt erstmal crazy, "
        "aber hey, geschmack ist ja subjektiv. "
        "ich persönlich bleib bei klassikern!"
    )

    second_real_example = (
        "pizza mit oliven? das klingt ja nach "
        "einer wagemutigen kombination! "
        "ich hätte nie gedacht, dass das zusammenpasst. "
        "vielleicht sollte ich es auch mal ausprobieren."
    )

    clean_one = (
        "ananas geht klar. oliven dazu wär mir "
        "aber wahrscheinlich zu viel."
    )

    clean_two = (
        "thunfisch wär nicht meine erste wahl."
    )

    service = (
        "ich bin gespannt, viel erfolg!"
    )

    one_soft = (
        "aber hey, kann passieren."
    )

    first_analysis = (
        analyze_naturalness(
            first_real_example
        )
    )

    second_analysis = (
        analyze_naturalness(
            second_real_example
        )
    )

    clean_one_analysis = (
        analyze_naturalness(
            clean_one
        )
    )

    clean_two_analysis = (
        analyze_naturalness(
            clean_two
        )
    )

    service_analysis = (
        analyze_naturalness(
            service
        )
    )

    one_soft_analysis = (
        analyze_naturalness(
            one_soft
        )
    )

    tests.extend(
        [

            (
                "real example 1 detected",
                first_analysis
                .rewrite_required
            ),

            (
                "real example 1 multiple patterns",
                len(
                    first_analysis.matches
                )
                >= 2
            ),

            (
                "real example 2 detected",
                second_analysis
                .rewrite_required
            ),

            (
                "real example 2 multiple patterns",
                len(
                    second_analysis.matches
                )
                >= 2
            ),

            (
                "clean example 1 passes",
                not clean_one_analysis
                .rewrite_required
            ),

            (
                "clean example 2 passes",
                not clean_two_analysis
                .rewrite_required
            ),

            (
                "service style detected",
                service_analysis
                .rewrite_required
            ),

            (
                "single weak phrase allowed",
                not one_soft_analysis
                .rewrite_required
            ),
        ]
    )

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"NATURALNESS v"
        f"{NATURALNESS_VERSION} TEST"
    )
    print(
        "============================================"
    )
    print("")

    print(
        "REAL EXAMPLE 1:"
    )

    print(
        first_analysis
    )

    print("")

    print(
        "REAL EXAMPLE 2:"
    )

    print(
        second_analysis
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
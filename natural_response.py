import re
from dataclasses import dataclass, field


# =========================================================
# VERSION
# =========================================================

NATURAL_RESPONSE_VERSION = "1.0"


# =========================================================
# LOW VALUE USER REPLIES
# =========================================================

LOW_VALUE_ACKS = {

    "ja",
    "jap",
    "jup",
    "jo",
    "okay",
    "ok",
    "nice",
    "true",
    "same",
    "genau",
    "stimmt",
    "stimmt schon",
    "durchaus wahr",
    "vollkommen wahr",
    "korrekt",
    "passt",
    "mhm",
    "hm",
    "real",
    "fr",
    "lol",
    "lmao",
}


# =========================================================
# STOPWORDS
# =========================================================

STOPWORDS = {

    "aber",
    "als",
    "am",
    "an",
    "auch",
    "auf",
    "aus",
    "bei",
    "bin",
    "bis",
    "da",
    "das",
    "dass",
    "dein",
    "deine",
    "dem",
    "den",
    "der",
    "des",
    "die",
    "dir",
    "du",
    "ein",
    "eine",
    "einer",
    "einem",
    "einen",
    "er",
    "es",
    "für",
    "fuer",
    "hab",
    "habe",
    "hat",
    "ich",
    "im",
    "in",
    "ist",
    "ja",
    "mal",
    "man",
    "mein",
    "meine",
    "mit",
    "nach",
    "nicht",
    "noch",
    "nur",
    "oder",
    "schon",
    "sehr",
    "sie",
    "so",
    "und",
    "uns",
    "von",
    "war",
    "was",
    "wie",
    "wieder",
    "wir",
    "zu",
    "zum",
    "zur",
    "echt",
    "halt",
    "doch",
    "denn",
    "dann",
}


# =========================================================
# GENERIC / BOT-LIKE STRUCTURES
#
# Ziel:
#
# Nicht einfach einzelne Wörter bannen.
#
# Wir erkennen Strukturen, die zusammen
# diesen typischen:
#
# "LLM versucht freundlich zu reagieren"
#
# Stil erzeugen.
# =========================================================

PATTERNS = {

    # -----------------------------------------------------
    # "Ich kann nachvollziehen..."
    # -----------------------------------------------------

    "assistant_empathy": (

        re.compile(

            r"\b(?:"
            r"ich\s+kann\s+(?:das\s+)?"
            r"(?:nachvollziehen|verstehen)"
            r"|"
            r"kann\s+ich\s+(?:gut\s+)?"
            r"(?:nachvollziehen|verstehen)"
            r")\b",

            re.IGNORECASE
        ),

        3
    ),

    # -----------------------------------------------------
    # "Ich kann mir vorstellen..."
    # -----------------------------------------------------

    "imagined_empathy": (

        re.compile(

            r"\bich\s+kann\s+mir\s+vorstellen\b",

            re.IGNORECASE
        ),

        2
    ),

    # -----------------------------------------------------
    # Motivational Coach
    # -----------------------------------------------------

    "motivational_coach": (

        re.compile(

            r"\b(?:"
            r"nicht\s+aufgeben"
            r"|"
            r"du\s+schaffst\s+das"
            r"|"
            r"du\s+kriegst\s+das\s+schon"
            r"|"
            r"das\s+wird\s+schon"
            r"|"
            r"wird\s+schon\s+werden"
            r"|"
            r"viel\s+erfolg"
            r")\b",

            re.IGNORECASE
        ),

        3
    ),

    # -----------------------------------------------------
    # Memory-System Sprache
    # -----------------------------------------------------

    "formal_memory_unknown": (

        re.compile(

            r"\b(?:"
            r"keine\s+klare\s+erinnerung"
            r"|"
            r"keine\s+eindeutige\s+erinnerung"
            r"|"
            r"ich\s+erinnere\s+mich\s+nicht\s+"
            r"(?:klar|eindeutig)"
            r"|"
            r"dazu\s+(?:habe|hab)\s+ich\s+"
            r"keine\s+(?:klare\s+)?erinnerung"
            r")\b",

            re.IGNORECASE
        ),

        3
    ),

    # -----------------------------------------------------
    # Therapie-/Coach Frage
    #
    # "Wie hat sich das angefühlt?"
    # -----------------------------------------------------

    "coach_feeling_question": (

        re.compile(

            r"\bwie\s+hat\s+sich\s+das\s+"
            r"(?:für\s+dich\s+|fuer\s+dich\s+)?"
            r"angefühlt\b"
            r"|"
            r"\bwie\s+fühlst\s+du\s+dich\s+"
            r"(?:damit|dabei)\b",

            re.IGNORECASE
        ),

        3
    ),

    # -----------------------------------------------------
    # "klingt frustrierend..."
    # -----------------------------------------------------

    "sounds_like_wrapper": (

        re.compile(

            r"\b(?:das\s+)?klingt\s+"
            r"(?:"
            r"ja\s+|"
            r"doch\s+|"
            r"echt\s+|"
            r"wirklich\s+|"
            r"ziemlich\s+|"
            r"total\s+"
            r")?"
            r"(?:"
            r"nach|"
            r"wie|"
            r"frustrierend|"
            r"anstrengend|"
            r"entspannt|"
            r"schwierig|"
            r"nervig"
            r")\b",

            re.IGNORECASE
        ),

        1
    ),

    # -----------------------------------------------------
    # "aber hey"
    # -----------------------------------------------------

    "but_hey_wrapper": (

        re.compile(

            r"\baber\s+hey\b",

            re.IGNORECASE
        ),

        1
    ),

    # -----------------------------------------------------
    # Generische Bestätigung
    # -----------------------------------------------------

    "generic_validation": (

        re.compile(

            r"\b(?:"
            r"schön\s+zu\s+hören"
            r"|"
            r"gut\s+zu\s+hören"
            r"|"
            r"das\s+ist\s+doch\s+(?:gut|schön)"
            r"|"
            r"manchmal\s+reicht\s+das\s+ja\s+"
            r"auch\s+schon"
            r")\b",

            re.IGNORECASE
        ),

        2
    ),

    # -----------------------------------------------------
    # "da verliert man leicht..."
    # -----------------------------------------------------

    "generic_generalization": (

        re.compile(

            r"\bda\s+(?:verliert|wird|kann)\s+man\b"
            r"|"
            r"\bkein\s+wunder\s*,?\s+dass\b",

            re.IGNORECASE
        ),

        2
    ),

    # -----------------------------------------------------
    # Wiederholung:
    #
    # "geht einem auf die Nerven"
    # -----------------------------------------------------

    "generic_restate_nerves": (

        re.compile(

            r"\bgeht\s+einem\b"
            r".{0,45}"
            r"\bauf\s+die\s+nerven\b",

            re.IGNORECASE
        ),

        1
    ),

    # -----------------------------------------------------
    # "definitiv kein gemütlicher Kampf"
    # -----------------------------------------------------

    "generic_definitely": (

        re.compile(

            r"\bdefinitiv\s+"
            r"kein(?:e|en|er|es)?\b",

            re.IGNORECASE
        ),

        1
    ),

    # -----------------------------------------------------
    # "Bosse sind echt dafür gemacht..."
    # -----------------------------------------------------

    "generic_made_to_frustrate": (

        re.compile(

            r"\b(?:ist|sind)\s+"
            r"echt\s+dafür\s+gemacht\b",

            re.IGNORECASE
        ),

        2
    ),

    # -----------------------------------------------------
    # "klingt fast wie ein Geheimnis..."
    # -----------------------------------------------------

    "fake_poetic_comparison": (

        re.compile(

            r"\bklingt\s+"
            r"(?:ja\s+)?"
            r"fast\s+wie\b",

            re.IGNORECASE
        ),

        2
    ),

    # -----------------------------------------------------
    # Filler
    # -----------------------------------------------------

    "filler_visibility": (

        re.compile(

            r"\bkann\s+man\s+ja\s+"
            r"kaum\s+übersehen\b",

            re.IGNORECASE
        ),

        1
    ),

    # -----------------------------------------------------
    # Generische Intensität
    # -----------------------------------------------------

    "generic_interest_adjective": (

        re.compile(

            r"\b(?:mega|echt|richtig)\s+"
            r"(?:spannend|intensiv|interessant)\b",

            re.IGNORECASE
        ),

        1
    ),
}


# =========================================================
# ANALYSIS
# =========================================================

@dataclass
class NaturalResponseAnalysis:

    matches: list[str] = field(
        default_factory=list
    )

    score: int = 0

    rewrite_required: bool = False

    reason: str = "clean"

    overlap_ratio: float = 0.0

    low_value_user: bool = False


# =========================================================
# NORMALIZE
# =========================================================

def _normalize(
    text: str
) -> str:

    text = str(
        text
        or ""
    ).lower()

    text = re.sub(
        r"<a?:[a-zA-Z0-9_]+:\d+>",
        " ",
        text
    )

    text = re.sub(
        r"[^a-z0-9äöüß]+",
        " ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# CONTENT TOKENS
# =========================================================

def _content_tokens(
    text: str
) -> set[str]:

    tokens = set()

    for token in (
        _normalize(
            text
        ).split()
    ):

        if (
            token
            in STOPWORDS
        ):

            continue

        if len(
            token
        ) <= 2:

            continue

        tokens.add(
            token
        )

    return tokens


# =========================================================
# LEXICAL MIRRORING
# =========================================================

def _lexical_overlap(
    user_text: str,
    answer: str
) -> float:

    user_tokens = (
        _content_tokens(
            user_text
        )
    )

    answer_tokens = (
        _content_tokens(
            answer
        )
    )

    if not (
        user_tokens
        and
        answer_tokens
    ):

        return 0.0

    overlap = (
        user_tokens
        &
        answer_tokens
    )

    return (

        len(
            overlap
        )

        /

        max(
            1,
            len(
                answer_tokens
            )
        )
    )


# =========================================================
# LOW VALUE USER
# =========================================================

def _is_low_value_user(
    text: str
) -> bool:

    return (
        _normalize(
            text
        )
        in
        LOW_VALUE_ACKS
    )


# =========================================================
# ANALYZE
# =========================================================

def analyze_natural_response(
    text: str,
    *,
    user_text: str = "",
    curiosity_allowed: bool = False,
    self_unknown: bool = False
) -> NaturalResponseAnalysis:

    text = str(
        text
        or ""
    ).strip()

    matches = []

    score = 0

    # -----------------------------------------------------
    # PATTERNS
    # -----------------------------------------------------

    for (
        name,
        (
            pattern,
            weight
        )
    ) in PATTERNS.items():

        if pattern.search(
            text
        ):

            matches.append(
                name
            )

            score += (
                weight
            )

    # -----------------------------------------------------
    # MIRRORING
    # -----------------------------------------------------

    overlap_ratio = (
        _lexical_overlap(
            user_text,
            text
        )
    )

    low_value_user = (
        _is_low_value_user(
            user_text
        )
    )

    if (
        overlap_ratio
        >=
        0.72
        and
        len(
            _content_tokens(
                text
            )
        )
        >= 4
    ):

        matches.append(
            "high_lexical_mirroring"
        )

        score += 2

    # -----------------------------------------------------
    # SHORT USER ACK
    #
    # User:
    # "Durchaus wahr"
    #
    # Evilnae:
    # 25 Wörter Reiter-Erklärung
    #
    # → nein.
    # -----------------------------------------------------

    if (
        low_value_user
        and
        len(
            _normalize(
                text
            ).split()
        )
        >
        8
    ):

        matches.append(
            "overexplained_acknowledgement"
        )

        score += 3

    # -----------------------------------------------------
    # QUESTION + GENERIC TAIL
    #
    # "Welcher Boss ist es?
    #  Ich kann mir vorstellen..."
    # -----------------------------------------------------

    if (
        curiosity_allowed
        and
        "?"
        in text
    ):

        first_question_end = (
            text.find(
                "?"
            )
        )

        tail = (
            text[
                first_question_end
                +
                1:
            ]
            .strip()
        )

        if tail:

            tail_score = 0

            for (
                name,
                (
                    pattern,
                    weight
                )
            ) in PATTERNS.items():

                if pattern.search(
                    tail
                ):

                    tail_score += (
                        weight
                    )

            if (
                tail_score
                >=
                2
            ):

                matches.append(
                    "question_plus_generic_filler"
                )

                score += 2

    # -----------------------------------------------------
    # UNKNOWN SELF FACT
    #
    # Nicht wie Memory-DB sprechen.
    # -----------------------------------------------------

    if (
        self_unknown
        and
        "erinnerung"
        in _normalize(
            text
        )
    ):

        if (
            "formal_memory_unknown"
            not in matches
        ):

            matches.append(
                "memory_system_language"
            )

            score += 2

    matches = list(
        dict.fromkeys(
            matches
        )
    )

    rewrite_required = (
        score
        >=
        2
    )

    if rewrite_required:

        reason = (
            "generic_response_structure"
        )

    else:

        reason = (
            "clean"
        )

    return NaturalResponseAnalysis(

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
        ),

        overlap_ratio=(
            overlap_ratio
        ),

        low_value_user=(
            low_value_user
        )
    )


# =========================================================
# WRITER GUIDANCE
# =========================================================

def format_natural_response_for_writer(
    analysis: NaturalResponseAnalysis,
    *,
    user_text: str,
    curiosity_allowed: bool,
    question_goal: str = "",
    self_unknown: bool = False
) -> str:

    if analysis.matches:

        matches = (
            ", ".join(
                analysis.matches
            )
        )

    else:

        matches = (
            "none"
        )

    # -----------------------------------------------------
    # QUESTION
    # -----------------------------------------------------

    if not curiosity_allowed:

        question_rule = """
Curiosity hat KEINE Frage erlaubt.

Die Antwort darf einfach enden.

Keine Gegenfrage hinzufügen.
""".strip()

    else:

        question_rule = f"""
Curiosity erlaubt genau EINE Frage.

Question goal:

{question_goal or "konkretes Detail aus echtem Interesse"}

Diese eine Frage darf die GANZE Antwort sein,
wenn davor kein echter eigener Gedanke nötig ist.

Keinen Empathie-/Füllsatz
hinter die Frage setzen.
""".strip()

    # -----------------------------------------------------
    # UNKNOWN
    # -----------------------------------------------------

    if self_unknown:

        unknown_rule = """
Die Antwort betrifft einen
unbekannten Self-Fact.

Die Unsicherheit muss erhalten bleiben,
aber NICHT wie ein Memory-System formulieren.

Gut:

- "kp, hab ich bei mir grad nicht drin"
- "weiß ich tatsächlich nicht mehr"
- "uff, keine ahnung ob ich das selber gezockt hab"

Nicht:

- "ich habe keine klare Erinnerung"
- neue Vergangenheit erfinden
""".strip()

    else:

        unknown_rule = (
            "Keine besondere "
            "Self-Unknown-Regel."
        )

    # -----------------------------------------------------
    # LOW VALUE
    # -----------------------------------------------------

    if analysis.low_value_user:

        low_value_rule = """
Der User hat nur kurz bestätigt
oder zugestimmt.

Wenn überhaupt eine Antwort nötig ist,
halte sie SEHR kurz.

Nicht das ganze Thema nochmal erklären.
""".strip()

    else:

        low_value_rule = ""

    return f"""
[NATURAL RESPONSE GUARD v{NATURAL_RESPONSE_VERSION}]

Die aktuelle Antwort wirkt zu sehr wie
eine vollständige LLM-/Assistant-Antwort.

Gefundene Muster:

{matches}

Score:

{analysis.score}

User-Nachricht:

{user_text}


==================================================
ZIEL
==================================================

Schreibe denselben zulässigen Inhalt
wie Evilnae in einem echten Discord-Chat.


==================================================
1. REAGIEREN, NICHT NACHERZÄHLEN
==================================================

Wiederhole nicht einfach die Aussage
des Users mit anderen Worten.


==================================================
2. EIN GUTER GEDANKE REICHT
==================================================

Keine Struktur aus:

Bestätigung
+
Empathie
+
Erklärung
+
Abschluss


==================================================
3. KEIN AUTOMATISCHES COACHING
==================================================

Vermeide standardmäßig:

- "ich kann nachvollziehen"
- "ich kann mir vorstellen"
- "klingt frustrierend"
- "aber hey"
- "nicht aufgeben"
- "du schaffst das"
- "das wird schon"


==================================================
4. CHARAKTER VOR VOLLSTÄNDIGKEIT
==================================================

Eine kurze:

- trockene
- freche
- amüsierte
- ehrliche

Reaktion ist besser
als ein perfekt abgerundeter
Assistant-Absatz.


==================================================
5. NICHT KÜNSTLICH SLANG ERZWINGEN
==================================================

Nicht aus jedem Satz:

"bro fr lmao 💀"

machen.

Der konkrete Moment entscheidet.


==================================================
6. KEINE NEUEN FAKTEN
==================================================

Knowledge-, Self-
und Source-Authority-Regeln
bleiben vollständig bestehen.


==================================================
7. AUFHÖREN
==================================================

Wenn der Gedanke fertig ist:

AUFHÖREN.

Kein Füllsatz nur für einen
runden Abschluss.


==================================================
QUESTION
==================================================

{question_rule}


==================================================
SELF UNKNOWN
==================================================

{unknown_rule}


==================================================
LOW VALUE
==================================================

{low_value_rule}


Antworte nur mit
der reparierten Discord-Nachricht.
""".strip()


# =========================================================
# BETTER THAN
# =========================================================

def better_than(
    candidate: str,
    original: str,
    *,
    user_text: str,
    curiosity_allowed: bool,
    self_unknown: bool
) -> bool:

    candidate_analysis = (
        analyze_natural_response(

            candidate,

            user_text=(
                user_text
            ),

            curiosity_allowed=(
                curiosity_allowed
            ),

            self_unknown=(
                self_unknown
            )
        )
    )

    original_analysis = (
        analyze_natural_response(

            original,

            user_text=(
                user_text
            ),

            curiosity_allowed=(
                curiosity_allowed
            ),

            self_unknown=(
                self_unknown
            )
        )
    )

    return (
        candidate_analysis.score
        <
        original_analysis.score
    )


# =========================================================
# DEBUG
# =========================================================

def format_natural_response_debug(
    analysis: NaturalResponseAnalysis
) -> str:

    return (

        "[NATURAL RESPONSE] "
        f"v={NATURAL_RESPONSE_VERSION} "
        f"score={analysis.score} "
        f"rewrite={analysis.rewrite_required} "
        f"overlap="
        f"{analysis.overlap_ratio:.2f} "
        f"low_value="
        f"{analysis.low_value_user} "
        f"matches="
        f"{analysis.matches}"
    )


# =========================================================
# SELF TEST
# =========================================================

def _self_test():

    tests = []

    # -----------------------------------------------------
    # CLEAN QUESTION
    # -----------------------------------------------------

    clean = (
        analyze_natural_response(

            "welcher boss war das?",

            user_text=(
                "bin an einem boss "
                "hängen geblieben"
            ),

            curiosity_allowed=True
        )
    )

    tests.append(
        (
            "clean curiosity question stays clean",

            not clean.rewrite_required
        )
    )

    # -----------------------------------------------------
    # ASSISTANT EMPATHY
    # -----------------------------------------------------

    empathy = (
        analyze_natural_response(

            (
                "ich kann nachvollziehen, "
                "warum das nervt."
            ),

            user_text=(
                "der boss nervt mich"
            )
        )
    )

    tests.append(
        (
            "assistant empathy blocked",

            empathy.rewrite_required
        )
    )

    # -----------------------------------------------------
    # MOTIVATION
    # -----------------------------------------------------

    coach = (
        analyze_natural_response(

            (
                "irgendwann kriegst du "
                "den schon. "
                "einfach nicht aufgeben!"
            ),

            user_text=(
                "hoffentlich schaff ich "
                "den bald"
            )
        )
    )

    tests.append(
        (
            "motivational coaching blocked",

            coach.rewrite_required
        )
    )

    # -----------------------------------------------------
    # MEMORY LANGUAGE
    # -----------------------------------------------------

    memory = (
        analyze_natural_response(

            (
                "dazu hab ich keine "
                "klare Erinnerung."
            ),

            user_text=(
                "hast du elden ring gespielt?"
            ),

            self_unknown=True
        )
    )

    tests.append(
        (
            "formal memory language blocked",

            memory.rewrite_required
        )
    )

    # -----------------------------------------------------
    # COACH QUESTION
    # -----------------------------------------------------

    feeling = (
        analyze_natural_response(

            (
                "und, wie hat sich das "
                "angefühlt dieses mal?"
            ),

            user_text=(
                "ich hab gestern "
                "elden ring gespielt"
            ),

            curiosity_allowed=True
        )
    )

    tests.append(
        (
            "coach feeling question blocked",

            feeling.rewrite_required
        )
    )

    # -----------------------------------------------------
    # QUESTION + FILLER
    # -----------------------------------------------------

    filler = (
        analyze_natural_response(

            (
                "welcher boss ist es? "
                "ich kann mir vorstellen, "
                "dass der frustrierend ist."
            ),

            user_text=(
                "bin an diesem boss "
                "hängen geblieben"
            ),

            curiosity_allowed=True
        )
    )

    tests.append(
        (
            "question plus filler blocked",

            filler.rewrite_required
        )
    )

    # -----------------------------------------------------
    # GENERALIZATION
    # -----------------------------------------------------

    generalization = (
        analyze_natural_response(

            (
                "der ist echt nervig, "
                "da verliert man leicht "
                "die geduld."
            ),

            user_text=(
                "der reiter ist "
                "verdammt schnell"
            )
        )
    )

    tests.append(
        (
            "generic generalization blocked",

            generalization.rewrite_required
        )
    )

    # -----------------------------------------------------
    # RESTATEMENT CLUSTER
    # -----------------------------------------------------

    restate = (
        analyze_natural_response(

            (
                "der geht einem echt schnell "
                "auf die nerven. "
                "definitiv kein gemütlicher kampf."
            ),

            user_text=(
                "der reiter ist so "
                "verdammt schnell"
            )
        )
    )

    tests.append(
        (
            "generic restatement cluster blocked",

            restate.rewrite_required
        )
    )

    # -----------------------------------------------------
    # LOW VALUE ACK
    # -----------------------------------------------------

    ack = (
        analyze_natural_response(

            (
                "der schnelle reiter ist "
                "wirklich ein nerviger gegner "
                "und kostet viel geduld."
            ),

            user_text=(
                "durchaus wahr"
            )
        )
    )

    tests.append(
        (
            "overexplained acknowledgement blocked",

            ack.rewrite_required
        )
    )

    # -----------------------------------------------------
    # CASUAL UNKNOWN
    # -----------------------------------------------------

    casual_unknown = (
        analyze_natural_response(

            (
                "kp, weiß ich tatsächlich "
                "nicht mehr."
            ),

            user_text=(
                "hast du das gespielt?"
            ),

            self_unknown=True
        )
    )

    tests.append(
        (
            "casual unknown allowed",

            not casual_unknown.rewrite_required
        )
    )

    # -----------------------------------------------------
    # FAKE POETIC
    # -----------------------------------------------------

    poetic = (
        analyze_natural_response(

            (
                "klingt ja fast wie ein "
                "geheimnis, das du nur "
                "manchmal lüftest 😂"
            ),

            user_text=(
                "aber nur manchmal lmao"
            )
        )
    )

    tests.append(
        (
            "fake poetic comparison blocked",

            poetic.rewrite_required
        )
    )

    # -----------------------------------------------------
    # SUPPORT WRAPPER
    # -----------------------------------------------------

    combo = (
        analyze_natural_response(

            (
                "klingt echt frustrierend, "
                "aber hey, du schaffst das schon."
            ),

            user_text=(
                "ich hoffe ich schaff den bald"
            )
        )
    )

    tests.append(
        (
            "support wrapper cluster blocked",

            combo.rewrite_required
        )
    )

    # -----------------------------------------------------
    # CHARACTER REACTION
    # -----------------------------------------------------

    direct = (
        analyze_natural_response(

            (
                "oh nein, wieder freiwillig "
                "leiden gegangen 💀"
            ),

            user_text=(
                "ich hab gestern wieder "
                "elden ring gespielt"
            )
        )
    )

    tests.append(
        (
            "short character reaction allowed",

            not direct.rewrite_required
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
        f"NATURAL RESPONSE v"
        f"{NATURAL_RESPONSE_VERSION} TEST"
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
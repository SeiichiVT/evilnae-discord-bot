import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Optional

OUTPUT_QUALITY_VERSION = "2.1"

STOPWORDS = {
    "aber","als","am","an","auch","auf","aus","bei","bin","bist","bis","da","das","dass",
    "dein","deine","dem","den","der","des","die","dir","dich","du","ein","eine","einer",
    "einem","einen","er","es","für","fuer","hab","habe","hat","ich","im","in","ist","ja",
    "mal","man","mein","meine","mit","nach","nicht","noch","nur","oder","schon","sehr",
    "sie","so","und","uns","von","war","was","wie","wieder","wir","zu","zum","zur","echt",
    "halt","doch","denn","dann","wenn","weil","ob","mich","mir","ihr","ihre","sein","sind",
    "wird","werden",
}

GENERIC_PATTERNS = {
    "sounds_like_wrapper": (
        re.compile(
            r"\b(?:das\s+)?klingt\s+(?:ja\s+|echt\s+|wirklich\s+|ziemlich\s+|total\s+)?"
            r"(?:nach|wie|spannend|interessant|frustrierend|anstrengend|entspannt|"
            r"schwierig|nervig|gut|cool)\b", re.I
        ), 2
    ),
    "assistant_empathy": (
        re.compile(
            r"\b(?:ich\s+kann\s+(?:das\s+)?(?:gut\s+)?(?:verstehen|nachvollziehen)|"
            r"das\s+kann\s+ich\s+(?:gut\s+)?(?:verstehen|nachvollziehen))\b", re.I
        ), 3
    ),
    "imagined_empathy": (
        re.compile(
            r"\bich\s+kann\s+mir\s+(?:gut\s+)?vorstellen\b",
            re.I
        ), 2
    ),
    "support_closure": (
        re.compile(
            r"\b(?:lass\s+mich\s+wissen|sag\s+bescheid|"
            r"halt\s+mich\s+auf\s+dem\s+laufenden)\b",
            re.I
        ), 2
    ),
    "service_success": (
        re.compile(
            r"\bviel\s+erfolg\b",
            re.I
        ), 2
    ),
    "generic_excited": (
        re.compile(
            r"\b(?:ich\s+bin\s+gespannt|bin\s+mal\s+gespannt)\b",
            re.I
        ), 2
    ),
    "generic_validation": (
        re.compile(
            r"\b(?:schön\s+zu\s+hören|gut\s+zu\s+hören|"
            r"das\s+freut\s+mich(?:\s+zu\s+hören)?|"
            r"das\s+ist\s+doch\s+schon\s+mal\s+(?:gut|schön))\b",
            re.I
        ), 2
    ),
    "motivational_coach": (
        re.compile(
            r"\b(?:du\s+schaffst\s+das|du\s+kriegst\s+das\s+schon|"
            r"das\s+wird\s+schon|nicht\s+aufgeben|"
            r"wird\s+schon\s+werden)\b",
            re.I
        ), 3
    ),
    "generic_good_idea": (
        re.compile(
            r"\b(?:frühstück|fruehstueck|essen|pause|schlaf)\b"
            r".{0,35}\b(?:ist|sind)\b.{0,20}\b"
            r"(?:immer\s+)?(?:eine\s+)?gute\s+idee\b",
            re.I
        ), 2
    ),
    "but_hey": (
        re.compile(
            r"\baber\s+hey\b",
            re.I
        ), 1
    ),
    "generic_conclusion": (
        re.compile(
            r"\b(?:am\s+ende\s+des\s+tages|letztendlich|"
            r"im\s+großen\s+und\s+ganzen|"
            r"im\s+grossen\s+und\s+ganzen)\b",
            re.I
        ), 2
    ),
    "therapy_question": (
        re.compile(
            r"\bwie\s+(?:hat\s+sich\s+das|fühlst\s+du\s+dich|"
            r"fuehlst\s+du\s+dich).{0,35}"
            r"\b(?:angefühlt|angefuehlt|damit|dabei)\b",
            re.I
        ), 3
    ),
}

PHRASE_FAMILIES = {
    "goodnight_spooky": (
        re.compile(
            r"\bträum\w*.{0,35}\b(?:grusel|creepy|horror|albtraum)",
            re.I
        ),
        re.compile(
            r"\b(?:grusel|creepy|horror|albtraum).{0,35}\bträum\w*",
            re.I
        ),
    ),
    "support_closure": (
        re.compile(
            r"\b(?:viel\s+erfolg|du\s+schaffst\s+das|"
            r"das\s+wird\s+schon|lass\s+mich\s+wissen|"
            r"sag\s+bescheid)\b",
            re.I
        ),
    ),
    "sounds_like": (
        re.compile(
            r"\b(?:das\s+)?klingt\s+"
            r"(?:ja\s+|echt\s+|wirklich\s+)?"
            r"(?:nach|wie|spannend|wild|cool|gut|frustrierend|nervig)\b",
            re.I
        ),
    ),
    "curiosity_wait_and_see": (
        re.compile(
            r"\b(?:ich\s+bin\s+gespannt|bin\s+mal\s+gespannt|"
            r"mal\s+sehen(?:,\s*)?\s+wie|"
            r"mal\s+gucken(?:,\s*)?\s+wie)\b",
            re.I
        ),
    ),
    "generic_good_idea": (
        re.compile(
            r"\b(?:frühstück|fruehstueck|essen|pause|schlaf)\b"
            r".{0,45}\bgute\s+idee\b",
            re.I
        ),
    ),
    "boss_congrats": (
        re.compile(
            r"\b(?:congrats|glückwunsch|glueckwunsch)"
            r".{0,45}\bboss\b",
            re.I
        ),
        re.compile(
            r"\bboss\b.{0,45}"
            r"\b(?:geschafft|gelegt|besiegt|zerlegt)\b",
            re.I
        ),
    ),
    "chaos_recap": (
        re.compile(
            r"\b(?:chaos|wirbel)\b.{0,45}"
            r"\b(?:heute|wieder|angerichtet|gemacht)\b",
            re.I
        ),
    ),
}

SAFE_GENERIC_TAILS = (
    re.compile(
        r"(?:lass\s+mich\s+wissen|sag\s+bescheid),?\s+"
        r"(?:wie|ob)\s+.{1,80}[.!]?\s*$",
        re.I
    ),
    re.compile(
        r"\bviel\s+erfolg[!.]?\s*$",
        re.I
    ),
    re.compile(
        r"\bich\s+bin\s+gespannt[!.]?\s*$",
        re.I
    ),
)

BROKEN_CASE_PATTERN = re.compile(
    r"\bder\s+dich\b.{0,60}"
    r"\bdas\s+leben\s+schwer\s+gemacht\b",
    re.I
)

UNFINISHED_END_PATTERN = re.compile(
    r"\b(?:und|aber|weil|dass|wenn|ob|während|waehrend|"
    r"damit|obwohl|sondern|denn)\s*[,.!?…-]*\s*$",
    re.I
)

REPEATED_WORD_PATTERN = re.compile(
    r"\b([A-Za-zÄÖÜäöüß]{2,})\s+\1\b",
    re.I
)

ISOLATED_WORD_COMMA_CHAIN = re.compile(
    r"(?:\b[A-Za-zÄÖÜäöüß]+\b\s*,\s*){3,}",
    re.I
)


@dataclass
class ResponseQualityAnalysis:
    total_penalty: int = 0
    generic_score: int = 0
    grammar_score: int = 0
    repetition_score: int = 0
    rhythm_score: int = 0
    echo_score: int = 0
    issues: list[str] = field(default_factory=list)
    semantic_families: list[str] = field(default_factory=list)
    max_recent_similarity: float = 0.0
    user_overlap: float = 0.0
    word_count: int = 0
    sentence_count: int = 0
    severe: bool = False


@dataclass
class CandidateDecision:
    accepted: bool
    reason: str
    candidate: ResponseQualityAnalysis
    baseline: ResponseQualityAnalysis
    meaning_preserved: float = 1.0


@dataclass
class BestCandidate:
    source: str
    text: str
    analysis: ResponseQualityAnalysis


def _normalize(text: str) -> str:
    text = str(
        text
        or ""
    ).lower()

    text = re.sub(
        r"<a?:[A-Za-z0-9_]+:\d+>",
        " ",
        text
    )

    text = re.sub(
        r"[^a-z0-9äöüß]+",
        " ",
        text,
        flags=re.I
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def _words(text: str) -> list[str]:
    return re.findall(
        r"[A-Za-zÄÖÜäöüß0-9]+",
        str(
            text
            or ""
        ).lower()
    )


# =========================================================
# 2.1 TEXTUAL CONTENT CHECK
# =========================================================

_QUALITY_CUSTOM_EMOJI_RE = re.compile(
    r"<a?:[A-Za-z0-9_]+:\d+>"
)
_QUALITY_MENTION_RE = re.compile(
    r"<(?:@!?|@&|#)\d+>"
)
_QUALITY_COLON_EMOJI_RE = re.compile(
    r"(?<!\w):[A-Za-z0-9_+\-]{2,}:(?!\w)"
)


def _has_textual_content(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    value = _QUALITY_CUSTOM_EMOJI_RE.sub(" ", value)
    value = _QUALITY_MENTION_RE.sub(" ", value)
    value = _QUALITY_COLON_EMOJI_RE.sub(" ", value)
    return bool(
        re.search(
            r"[^\W_]",
            value,
            flags=re.UNICODE,
        )
    )


def _content_tokens(
    text: str
) -> set[str]:

    return {
        word

        for word
        in _words(
            text
        )

        if (
            len(
                word
            )
            >
            2
            and
            word
            not in STOPWORDS
        )
    }


def _token_overlap(
    left: str,
    right: str
) -> float:

    left_tokens = (
        _content_tokens(
            left
        )
    )

    right_tokens = (
        _content_tokens(
            right
        )
    )

    if (
        not left_tokens
        or
        not right_tokens
    ):

        return 0.0

    return (
        len(
            left_tokens
            &
            right_tokens
        )
        /
        max(
            1,
            len(
                right_tokens
            )
        )
    )


def _similarity(
    left: str,
    right: str
) -> float:

    left = (
        _normalize(
            left
        )
    )

    right = (
        _normalize(
            right
        )
    )

    if (
        not left
        or
        not right
    ):

        return 0.0

    sequence_similarity = (
        SequenceMatcher(
            None,
            left,
            right
        ).ratio()
    )

    left_tokens = (
        _content_tokens(
            left
        )
    )

    right_tokens = (
        _content_tokens(
            right
        )
    )

    if (
        left_tokens
        and
        right_tokens
    ):

        jaccard = (
            len(
                left_tokens
                &
                right_tokens
            )
            /
            max(
                1,
                len(
                    left_tokens
                    |
                    right_tokens
                )
            )
        )

    else:

        jaccard = (
            0.0
        )

    return max(
        sequence_similarity,
        jaccard
    )


def _sentence_count(
    text: str
) -> int:

    return len([
        chunk

        for chunk
        in re.split(
            r"[.!?]+",
            str(
                text
                or ""
            )
        )

        if chunk.strip()
    ])


def _semantic_families(
    text: str
) -> list[str]:

    return [
        family

        for (
            family,
            patterns
        )
        in PHRASE_FAMILIES.items()

        if any(
            pattern.search(
                text
                or ""
            )

            for pattern
            in patterns
        )
    ]


def trim_safe_generic_tail(
    text: str
) -> str:

    original = str(
        text
        or ""
    ).strip()

    if not original:

        return ""

    current = (
        original
    )

    for pattern in (
        SAFE_GENERIC_TAILS
    ):

        match = (
            pattern.search(
                current
            )
        )

        if not match:

            continue

        prefix = (
            current[
                :match.start()
            ]
            .strip(
                " \t,;:-"
            )
        )

        if len(
            _words(
                prefix
            )
        ) >= 3:

            current = (
                prefix.rstrip()
            )

    return (
        current
        or
        original
    )


def analyze_response_quality(
    text: str,
    *,
    user_text: str = "",
    recent_evilnae_messages: Optional[
        Iterable[str]
    ] = None,
) -> ResponseQualityAnalysis:

    text = str(
        text
        or ""
    ).strip()

    recent = [
        str(
            item
            or ""
        ).strip()

        for item
        in (
            recent_evilnae_messages
            or []
        )

        if str(
            item
            or ""
        ).strip()
    ]

    if not text:

        return (
            ResponseQualityAnalysis(
                total_penalty=10,
                grammar_score=10,
                issues=[
                    "empty_output"
                ],
                severe=True
            )
        )

    issues = []

    generic_score = 0
    grammar_score = 0
    repetition_score = 0
    rhythm_score = 0
    echo_score = 0

    word_count = len(
        _words(
            text
        )
    )

    sentence_count = (
        _sentence_count(
            text
        )
    )

    # =====================================================
    # TEXTUAL CONTENT FLOOR
    # =====================================================

    if not _has_textual_content(
        text
    ):

        issues.append(
            "no_textual_content"
        )

        grammar_score += 10

    # =====================================================
    # GENERIC / BOT STYLE
    # =====================================================

    for (
        name,
        (
            pattern,
            weight
        )
    ) in GENERIC_PATTERNS.items():

        if pattern.search(
            text
        ):

            issues.append(
                name
            )

            generic_score += (
                weight
            )

    # =====================================================
    # ONE-THOUGHT / RHYTHM
    # =====================================================

    if sentence_count >= 4:

        issues.append(
            "too_many_thought_units"
        )

        rhythm_score += 2

    elif (
        sentence_count == 3
        and
        word_count >= 24
    ):

        issues.append(
            "multi_thought_reply"
        )

        rhythm_score += 1

    if word_count >= 45:

        issues.append(
            "overlong_discord_reply"
        )

        rhythm_score += 2

    elif word_count >= 32:

        issues.append(
            "long_discord_reply"
        )

        rhythm_score += 1

    if (
        0
        <
        len(
            _words(
                user_text
            )
        )
        <=
        3
        and
        word_count
        >
        18
    ):

        issues.append(
            "overexplained_short_user_message"
        )

        rhythm_score += 2

    # =====================================================
    # USER ECHO
    # =====================================================

    user_overlap = (
        _token_overlap(
            user_text,
            text
        )
    )

    if (
        user_overlap >= 0.72
        and
        len(
            _content_tokens(
                text
            )
        )
        >=
        4
    ):

        issues.append(
            "high_user_restatement"
        )

        echo_score += 2

    # =====================================================
    # GRAMMAR / GARBLED
    # =====================================================

    comma_segments = [
        segment.strip()

        for segment
        in text.split(
            ","
        )

        if segment.strip()
    ]

    if len(
        comma_segments
    ) >= 3:

        short_segments = sum(
            1

            for segment
            in comma_segments

            if len(
                _words(
                    segment
                )
            ) <= 2
        )

        if short_segments >= 3:

            issues.append(
                "comma_fragment_chain"
            )

            grammar_score += 4

    if ISOLATED_WORD_COMMA_CHAIN.search(
        text
    ):

        issues.append(
            "isolated_word_chain"
        )

        grammar_score += 3

    if BROKEN_CASE_PATTERN.search(
        text
    ):

        issues.append(
            "broken_case_construction"
        )

        grammar_score += 3

    if UNFINISHED_END_PATTERN.search(
        text
    ):

        issues.append(
            "unfinished_clause"
        )

        grammar_score += 3

    if REPEATED_WORD_PATTERN.search(
        text
    ):

        issues.append(
            "repeated_word"
        )

        grammar_score += 2

    if re.search(
        r"[,;:]\s*[,;:]",
        text
    ):

        issues.append(
            "broken_punctuation_chain"
        )

        grammar_score += 2

    if (
        text.count(
            ","
        )
        >=
        5
        and
        word_count
        <=
        14
    ):

        issues.append(
            "comma_density"
        )

        grammar_score += 2

    # =====================================================
    # SEMANTIC REPETITION
    # =====================================================

    semantic_families = (
        _semantic_families(
            text
        )
    )

    recent_family_counts = {}

    max_recent_similarity = (
        0.0
    )

    for recent_message in (
        recent[
            -10:
        ]
    ):

        max_recent_similarity = max(
            max_recent_similarity,
            _similarity(
                text,
                recent_message
            )
        )

        for family in (
            _semantic_families(
                recent_message
            )
        ):

            recent_family_counts[
                family
            ] = (
                recent_family_counts.get(
                    family,
                    0
                )
                +
                1
            )

    repeated_families = [
        family

        for family
        in semantic_families

        if (
            recent_family_counts.get(
                family,
                0
            )
            >=
            1
        )
    ]

    if repeated_families:

        issues.extend(
            f"semantic_family_repeat:{family}"

            for family
            in repeated_families
        )

        repetition_score += min(
            4,
            2
            *
            len(
                repeated_families
            )
        )

    if (
        max_recent_similarity
        >=
        0.78
        and
        word_count
        >=
        4
    ):

        issues.append(
            "high_recent_similarity"
        )

        repetition_score += 3

    elif (
        max_recent_similarity
        >=
        0.68
        and
        word_count
        >=
        6
    ):

        issues.append(
            "moderate_recent_similarity"
        )

        repetition_score += 1

    issues = list(
        dict.fromkeys(
            issues
        )
    )

    total_penalty = (
        generic_score
        +
        grammar_score
        +
        repetition_score
        +
        rhythm_score
        +
        echo_score
    )

    severe = (
        grammar_score >= 3
        or
        repetition_score >= 4
        or
        total_penalty >= 7
    )

    return (
        ResponseQualityAnalysis(
            total_penalty=total_penalty,
            generic_score=generic_score,
            grammar_score=grammar_score,
            repetition_score=repetition_score,
            rhythm_score=rhythm_score,
            echo_score=echo_score,
            issues=issues,
            semantic_families=semantic_families,
            max_recent_similarity=max_recent_similarity,
            user_overlap=user_overlap,
            word_count=word_count,
            sentence_count=sentence_count,
            severe=severe,
        )
    )


def compare_response_candidates(
    *,
    candidate: str,
    baseline: str,
    user_text: str = "",
    recent_evilnae_messages: Optional[
        Iterable[str]
    ] = None,
    meaning_preserved: float = 1.0,
) -> CandidateDecision:

    candidate = str(
        candidate
        or ""
    ).strip()

    baseline = str(
        baseline
        or ""
    ).strip()

    candidate_analysis = (
        analyze_response_quality(
            candidate,
            user_text=user_text,
            recent_evilnae_messages=(
                recent_evilnae_messages
            ),
        )
    )

    baseline_analysis = (
        analyze_response_quality(
            baseline,
            user_text=user_text,
            recent_evilnae_messages=(
                recent_evilnae_messages
            ),
        )
    )

    try:

        meaning_preserved = float(
            meaning_preserved
        )

    except (
        TypeError,
        ValueError
    ):

        meaning_preserved = (
            0.0
        )

    def result(
        accepted,
        reason
    ):

        return (
            CandidateDecision(
                accepted=accepted,
                reason=reason,
                candidate=candidate_analysis,
                baseline=baseline_analysis,
                meaning_preserved=meaning_preserved,
            )
        )

    if not candidate:

        return result(
            False,
            "empty_candidate"
        )

    if candidate_analysis.severe:

        return result(
            False,
            "candidate_severe_quality_issue"
        )

    if (
        _normalize(
            candidate
        )
        ==
        _normalize(
            baseline
        )
        and
        candidate
    ):

        return result(
            True,
            "same_content"
        )

    if meaning_preserved < 0.86:

        return result(
            False,
            "meaning_preservation_too_low"
        )

    if (
        candidate_analysis
        .grammar_score
        >
        baseline_analysis
        .grammar_score
    ):

        return result(
            False,
            "grammar_worse"
        )

    if (
        candidate_analysis
        .repetition_score
        >
        baseline_analysis
        .repetition_score
    ):

        return result(
            False,
            "repetition_worse"
        )

    if (
        candidate_analysis
        .total_penalty
        <
        baseline_analysis
        .total_penalty
    ):

        return result(
            True,
            "quality_improved"
        )

    baseline_words = max(
        1,
        baseline_analysis.word_count
    )

    if (
        candidate_analysis
        .total_penalty
        ==
        baseline_analysis
        .total_penalty
        and
        candidate_analysis
        .word_count
        <=
        max(
            baseline_words + 3,
            int(
                baseline_words
                *
                1.20
            )
        )
    ):

        return result(
            True,
            "quality_equal_not_longer"
        )

    return result(
        False,
        "no_quality_gain"
    )


def select_best_quality_candidate(
    *,
    candidates: Iterable[
        tuple[
            str,
            str
        ]
    ],
    user_text: str = "",
    recent_evilnae_messages: Optional[
        Iterable[str]
    ] = None,
) -> BestCandidate:

    best = None

    seen = set()

    for (
        source,
        text
    ) in candidates:

        text = (
            trim_safe_generic_tail(
                str(
                    text
                    or ""
                ).strip()
            )
        )

        normalized = (
            _normalize(
                text
            )
        )

        if (
            not text
            or
            not normalized
            or
            normalized
            in seen
        ):

            continue

        seen.add(
            normalized
        )

        analysis = (
            analyze_response_quality(
                text,
                user_text=user_text,
                recent_evilnae_messages=(
                    recent_evilnae_messages
                ),
            )
        )

        key = (
            1
            if analysis.severe
            else 0,
            analysis.grammar_score,
            analysis.repetition_score,
            analysis.total_penalty,
            analysis.generic_score,
            analysis.rhythm_score,
            analysis.word_count,
        )

        if (
            best is None
            or
            key
            <
            best[0]
        ):

            best = (
                key,
                BestCandidate(
                    source=source,
                    text=text,
                    analysis=analysis,
                )
            )

    if best is None:

        return (
            BestCandidate(
                source="none",
                text="",
                analysis=(
                    analyze_response_quality(
                        ""
                    )
                )
            )
        )

    return (
        best[1]
    )


def format_quality_for_writer(
    analysis: ResponseQualityAnalysis
) -> str:

    issues = (
        ", ".join(
            analysis.issues
        )
        if analysis.issues
        else "none"
    )

    return f"""
[OUTPUT QUALITY v{OUTPUT_QUALITY_VERSION}]

Penalty:
{analysis.total_penalty}

Issues:
{issues}

Schreibe denselben zulässigen Inhalt neu.

- Reagiere statt die User-Nachricht nachzuerzählen.
- Ein echter Gedanke reicht.
- Kein Support-/Coach-Abschluss.
- Kein "klingt nach..." als Standardwrapper.
- Kein "lass mich wissen, wie es läuft".
- Kein generisches "viel Erfolg".
- Keine künstliche Empathie.
- Keine neuen Fakten.
- Keine kürzlich benutzte Gag-/Phrasenfamilie wiederholen.
- Keine kaputten Satzfragmente oder Komma-Wortketten.
- Die Antwort braucht echten Text mit mindestens einem Wort.
- Keine Unicode-Emojis oder Discord-Custom-Emotes; der Emote-Layer kommt später.
- Wenn der Gedanke fertig ist: aufhören.
""".strip()


def format_quality_debug(
    analysis: ResponseQualityAnalysis,
    *,
    label: str = "QUALITY"
) -> str:

    return (
        f"[{label}] "
        f"v={OUTPUT_QUALITY_VERSION} "
        f"penalty={analysis.total_penalty} "
        f"generic={analysis.generic_score} "
        f"grammar={analysis.grammar_score} "
        f"repeat={analysis.repetition_score} "
        f"rhythm={analysis.rhythm_score} "
        f"echo={analysis.echo_score} "
        f"similarity={analysis.max_recent_similarity:.2f} "
        f"severe={analysis.severe} "
        f"issues={analysis.issues}"
    )


def format_candidate_decision_debug(
    decision: CandidateDecision,
    *,
    label: str = "QWEN QUALITY"
) -> str:

    return (
        f"[{label}] "
        f"v={OUTPUT_QUALITY_VERSION} "
        f"accepted={decision.accepted} "
        f"reason={decision.reason} "
        f"meaning={decision.meaning_preserved:.2f} "
        f"candidate={decision.candidate.total_penalty} "
        f"baseline={decision.baseline.total_penalty} "
        f"candidate_issues={decision.candidate.issues}"
    )


def _self_test():

    tests = []

    generic = (
        analyze_response_quality(
            (
                "Das klingt echt frustrierend. "
                "Aber hey, du schaffst das."
            ),
            user_text=(
                "der boss nervt mich"
            )
        )
    )

    tests.append(
        (
            "assistant wrapper detected",
            generic.total_penalty >= 4
        )
    )

    clean = (
        analyze_response_quality(
            "der boss lebt nur noch aus trotz.",
            user_text="der boss nervt mich"
        )
    )

    tests.append(
        (
            "clean short reaction allowed",
            (
                not clean.severe
                and
                clean.total_penalty == 0
            )
        )
    )

    garbled = (
        analyze_response_quality(
            "hast, keine, ahnung, ehrlich"
        )
    )

    tests.append(
        (
            "comma fragments detected",
            garbled.grammar_score >= 3
        )
    )

    unfinished = (
        analyze_response_quality(
            "ja okay, das wäre schon wild aber"
        )
    )

    tests.append(
        (
            "unfinished clause detected",
            unfinished.grammar_score >= 3
        )
    )

    repeated = (
        analyze_response_quality(
            (
                "schlaf gut, "
                "träum was gruseliges."
            ),
            recent_evilnae_messages=[
                (
                    "gute nacht, "
                    "träum schön gruselig."
                )
            ]
        )
    )

    tests.append(
        (
            "semantic phrase family repetition detected",
            repeated.repetition_score >= 2
        )
    )

    tail = (
        trim_safe_generic_tail(
            (
                "der boss ist cursed. "
                "lass mich wissen, wie es läuft."
            )
        )
    )

    tests.append(
        (
            "generic tail trimmed",
            tail
            ==
            "der boss ist cursed."
        )
    )

    good_qwen = (
        compare_response_candidates(
            candidate=(
                "der boss lebt aus trotz."
            ),
            baseline=(
                "Das klingt nach einem "
                "nervigen Boss."
            ),
            user_text=(
                "der boss nervt mich"
            ),
            meaning_preserved=0.95
        )
    )

    tests.append(
        (
            "better qwen accepted",
            good_qwen.accepted
        )
    )

    bad_qwen = (
        compare_response_candidates(
            candidate=(
                "also, boss, leben, "
                "schwer, gemacht"
            ),
            baseline=(
                "der boss lebt aus trotz."
            ),
            user_text=(
                "der boss nervt mich"
            ),
            meaning_preserved=0.95
        )
    )

    tests.append(
        (
            "garbled qwen rejected",
            not bad_qwen.accepted
        )
    )

    meaning_bad = (
        compare_response_candidates(
            candidate=(
                "jo, anderes thema."
            ),
            baseline=(
                "der boss lebt aus trotz."
            ),
            user_text=(
                "der boss nervt mich"
            ),
            meaning_preserved=0.40
        )
    )

    tests.append(
        (
            "meaning drift rejected",
            not meaning_bad.accepted
        )
    )

    best = (
        select_best_quality_candidate(
            candidates=[
                (
                    "bad",
                    (
                        "Das klingt echt "
                        "frustrierend. "
                        "Viel Erfolg!"
                    )
                ),
                (
                    "good",
                    "der boss lebt aus trotz."
                ),
            ],
            user_text=(
                "der boss nervt mich"
            )
        )
    )

    tests.append(
        (
            "best candidate selected",
            best.source == "good"
        )
    )

    passed = 0

    print("")
    print(
        "============================================"
    )
    print(
        f"OUTPUT QUALITY "
        f"v{OUTPUT_QUALITY_VERSION} TEST"
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
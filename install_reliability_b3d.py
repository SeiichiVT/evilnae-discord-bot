from pathlib import Path
from datetime import datetime

import ast
import shutil
import sys


# =========================================================
# CONFIG
# =========================================================

BOT_PATH = Path(
    "bot.py"
)

EXPECTED_BOT_VERSION = (
    "2.12.0-context-b3c"
)

TARGET_BOT_VERSION = (
    "2.12.1-reliability-b3d"
)


# =========================================================
# OUTPUT
# =========================================================

def fail(
    message
):

    print("")

    print(
        f"[INSTALL ERROR] {message}"
    )

    print("")

    sys.exit(
        1
    )


def ok(
    message
):

    print(
        f"[OK] {message}"
    )


def replace_once(
    text,
    old,
    new,
    label
):

    if new in text:

        print(
            f"[SKIP] {label}"
        )

        return text

    count = (
        text.count(
            old
        )
    )

    if count != 1:

        fail(
            f"{label}: "
            f"expected 1 match, "
            f"found {count}"
        )

    text = (
        text.replace(
            old,
            new,
            1
        )
    )

    ok(
        label
    )

    return text


def insert_before_once(
    text,
    marker,
    insert,
    label
):

    if insert in text:

        print(
            f"[SKIP] {label}"
        )

        return text

    count = (
        text.count(
            marker
        )
    )

    if count != 1:

        fail(
            f"{label}: "
            f"expected 1 marker, "
            f"found {count}"
        )

    text = text.replace(
        marker,
        insert + marker,
        1
    )

    ok(
        label
    )

    return text


# =========================================================
# START
# =========================================================

print(
    "[B3D RELIABILITY PACK] starting..."
)


if not BOT_PATH.exists():

    fail(
        "bot.py missing"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# VERSION CHECK
# =========================================================

if (
    f'BOT_VERSION = "{TARGET_BOT_VERSION}"'
    in bot
):

    print(
        "B3D already installed."
    )

    sys.exit(
        0
    )


if (
    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"'
    not in bot
):

    fail(
        "Unexpected bot version. "
        f"Expected {EXPECTED_BOT_VERSION}."
    )


required_b3c = [

    "CONVERSATION_UNDERSTANDING_VERSION",

    "salvage_question_shape",

    "analyze_garbled_output",

    "Question Guard Fail-Safe: ACTIVE",
]


for marker in required_b3c:

    if marker not in bot:

        fail(
            "B3C feature missing: "
            f"{marker}"
        )


# =========================================================
# VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"',

    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',

    "Bot version"
)


# =========================================================
# RELIABILITY HELPER
#
# IMPORTANT:
#
# This fallback intentionally does NOT
# enforce style-only rules.
#
# A slightly generic reply is preferable
# to silently dropping a harmless direct reply.
#
# It DOES enforce:
#
# - Question Policy
# - Self Knowledge
# - Knowledge Authority
# - Garbled Output
# - Permanent bans
# =========================================================

reliability_helper = r'''
# =========================================================
# B3D RESPONSE RELIABILITY
# =========================================================

def choose_reliability_fallback(
    *,
    candidates,
    curiosity_result,
    self_evidence,
    knowledge_constraint,
    username,
    stage
):

    seen = set()

    for (
        source_name,
        candidate
    ) in candidates:

        candidate = (
            clean_generated_answer(
                candidate
                or ""
            )
        )

        candidate = (
            enforce_permanent_expression_bans(
                candidate
            )
        )

        if not candidate:

            continue

        if candidate in seen:

            continue

        seen.add(
            candidate
        )

        # -------------------------------------------------
        # QUESTION POLICY
        #
        # Try deterministic salvage before rejecting.
        # -------------------------------------------------

        question_violations = (
            question_output_violation_reasons(
                candidate,
                curiosity_result
            )
        )

        if question_violations:

            candidate = (
                salvage_question_shape(

                    candidate,

                    allow_question=bool(
                        getattr(
                            curiosity_result,
                            "allowed",
                            False
                        )
                    )
                )
            )

            candidate = (
                clean_generated_answer(
                    candidate
                )
            )

            candidate = (
                enforce_permanent_expression_bans(
                    candidate
                )
            )

            if not candidate:

                print(
                    "[RELIABILITY CANDIDATE REJECTED] "
                    f"user={username} "
                    f"stage={stage} "
                    f"source={source_name} "
                    "reason=question_salvage_empty"
                )

                continue

            question_violations = (
                question_output_violation_reasons(
                    candidate,
                    curiosity_result
                )
            )

        if question_violations:

            print(
                "[RELIABILITY CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source_name} "
                f"question={question_violations}"
            )

            continue

        # -------------------------------------------------
        # SELF KNOWLEDGE
        # -------------------------------------------------

        self_violations = []

        if self_evidence is not None:

            self_violations = (
                self_knowledge_violation_reasons(
                    candidate,
                    self_evidence
                )
            )

        if self_violations:

            print(
                "[RELIABILITY CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source_name} "
                f"self={self_violations}"
            )

            continue

        # -------------------------------------------------
        # KNOWLEDGE AUTHORITY
        # -------------------------------------------------

        knowledge_violations = []

        if knowledge_constraint is not None:

            knowledge_violations = (
                knowledge_violation_reasons(
                    candidate,
                    knowledge_constraint
                )
            )

        if knowledge_violations:

            print(
                "[RELIABILITY CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source_name} "
                f"knowledge={knowledge_violations}"
            )

            continue

        # -------------------------------------------------
        # GARBLED OUTPUT
        # -------------------------------------------------

        garbled = (
            analyze_garbled_output(
                candidate
            )
        )

        if garbled.garbled:

            print(
                "[RELIABILITY CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source_name} "
                f"garbled={garbled.matches}"
            )

            continue

        print(
            "[RELIABILITY FALLBACK] "
            f"user={username} "
            f"stage={stage} "
            f"source={source_name} "
            f"answer={candidate!r}"
        )

        return candidate

    return ""


'''

marker = '''# =========================================================
# SOCIAL ACTION TEXT
# =========================================================
'''


bot = insert_before_once(

    bot,
    marker,
    reliability_helper,

    "Reliability fallback helper"
)


# =========================================================
# STARTUP STATUS
# =========================================================

old = '''    print(
        "Garbled Output Guard: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


new = '''    print(
        "Garbled Output Guard: ACTIVE"
    )

    print(
        "Response Reliability v1: ACTIVE"
    )

    print(
        "No Lost Harmless Replies: ACTIVE"
    )

    print(
        "Safe Draft Fallback: ACTIVE"
    )

    print(
        "Explicit Silence Diagnostics: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


bot = replace_once(

    bot,
    old,
    new,

    "Reliability startup status"
)


# =========================================================
# PARTICIPATION SILENCE LOGGING
# =========================================================

old = '''        if not PARTICIPATION_ENABLED:

            return
'''


new = '''        if not PARTICIPATION_ENABLED:

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=participation "
                "reason=participation_disabled"
            )

            return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Participation disabled silence log"
)


old = '''        if (
            participation_decision.action
            != "join"
        ):

            return
'''


new = '''        if (
            participation_decision.action
            != "join"
        ):

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=participation "
                f"reason="
                f"{getattr(participation_decision, 'reason', 'not_joining')}"
            )

            return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Participation decision silence log"
)


# =========================================================
# AGENCY SILENCE LOG
# =========================================================

old = '''            print(
                "[RESPONSE SKIPPED] "
                f"user={username} "
                "reason=agency_stay_silent"
            )

            return
'''


new = '''            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=agency "
                f"reason={agency_result.reason or 'agency_stay_silent'}"
            )

            return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Agency silence diagnostics"
)


# =========================================================
# WRITER API ERROR DIAGNOSTIC
# =========================================================

old = '''            print(
                "[WRITER ERROR] "
                f"user={username} "
                f"error="
                f"{type(error).__name__}: "
                f"{error}"
            )

            return
'''


new = '''            print(
                "[WRITER ERROR] "
                f"user={username} "
                f"error="
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=writer "
                "reason=writer_api_failure"
            )

            return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Writer API silence diagnostic"
)


# =========================================================
# FINALIZE WRITER FAILURE
#
# Previously:
#
# invalid Writer after repairs
# -> return
#
# Now:
#
# try raw Writer draft again through
# the critical deterministic guards.
# =========================================================

old = '''        if not answer:

            print(
                "[RESPONSE ABORTED] "
                f"user={username} "
                "reason=no_valid_writer_output"
            )

            return
'''


new = '''        if not answer:

            recovery_candidates = [
                (
                    "raw_writer",
                    response.output_text
                ),
            ]

            if (
                not autonomous_participation
                and
                (
                    getattr(
                        self_evidence,
                        "matched",
                        False
                    )
                    or
                    getattr(
                        knowledge_constraint,
                        "active",
                        False
                    )
                )
            ):

                recovery_candidates.append(
                    (
                        "epistemic_unknown",
                        "weiß ich grad nicht sicher."
                    )
                )

            answer = (
                choose_reliability_fallback(

                    candidates=(
                        recovery_candidates
                    ),

                    curiosity_result=(
                        curiosity_result
                    ),

                    self_evidence=(
                        self_evidence
                    ),

                    knowledge_constraint=(
                        knowledge_constraint
                    ),

                    username=(
                        username
                    ),

                    stage=(
                        "writer_finalize"
                    )
                )
            )

            if not answer:

                print(
                    "[SILENT FINAL] "
                    f"user={username} "
                    "stage=writer_finalize "
                    "reason=no_safe_fallback"
                )

                return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Writer finalization fallback"
)


# =========================================================
# SELF KNOWLEDGE REPAIR FAILURE
# =========================================================

old = '''            if not self_repair:

                print(
                    "[SELF KNOWLEDGE ABORT] "
                    f"user={username} "
                    "reason=repair_failed"
                )

                return
'''


new = '''            if not self_repair:

                fallback_candidates = [
                    (
                        "self_violation_source",
                        answer
                    ),
                ]

                if not autonomous_participation:

                    fallback_candidates.append(
                        (
                            "epistemic_unknown",
                            "weiß ich grad nicht sicher."
                        )
                    )

                self_repair = (
                    choose_reliability_fallback(

                        candidates=(
                            fallback_candidates
                        ),

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "self_repair_failed"
                        )
                    )
                )

                if not self_repair:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=self_knowledge "
                        "reason=no_safe_fallback"
                    )

                    return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Self repair failure fallback"
)


old = '''                print(
                    "[SELF KNOWLEDGE ABORT] "
                    f"user={username} "
                    f"hard="
                    f"{self_repair_hard} "
                    f"self="
                    f"{self_repair_violations}"
                )

                return
'''


new = '''                fallback_candidates = [
                    (
                        "self_repair_invalid",
                        self_repair
                    ),
                    (
                        "self_violation_source",
                        answer
                    ),
                ]

                if not autonomous_participation:

                    fallback_candidates.append(
                        (
                            "epistemic_unknown",
                            "weiß ich grad nicht sicher."
                        )
                    )

                safe_self_fallback = (
                    choose_reliability_fallback(

                        candidates=(
                            fallback_candidates
                        ),

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "self_repair_invalid"
                        )
                    )
                )

                if not safe_self_fallback:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=self_knowledge "
                        "reason=no_safe_fallback"
                    )

                    return

                self_repair = (
                    safe_self_fallback
                )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Invalid self repair fallback"
)


# =========================================================
# KNOWLEDGE REPAIR FAILURE
# =========================================================

old = '''            if not knowledge_repair:

                print(
                    "[KNOWLEDGE OUTPUT ABORT] "
                    f"user={username} "
                    "reason=repair_failed"
                )

                return
'''


new = '''            if not knowledge_repair:

                fallback_candidates = [
                    (
                        "knowledge_violation_source",
                        answer
                    ),
                ]

                if not autonomous_participation:

                    fallback_candidates.append(
                        (
                            "epistemic_unknown",
                            "weiß ich grad nicht sicher."
                        )
                    )

                knowledge_repair = (
                    choose_reliability_fallback(

                        candidates=(
                            fallback_candidates
                        ),

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "knowledge_repair_failed"
                        )
                    )
                )

                if not knowledge_repair:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=knowledge "
                        "reason=no_safe_fallback"
                    )

                    return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Knowledge repair failure fallback"
)


old = '''                print(
                    "[KNOWLEDGE OUTPUT ABORT] "
                    f"user={username} "
                    f"hard="
                    f"{repair_hard_violations} "
                    f"knowledge="
                    f"{repair_knowledge_violations}"
                )

                return
'''


new = '''                fallback_candidates = [
                    (
                        "knowledge_repair_invalid",
                        knowledge_repair
                    ),
                    (
                        "knowledge_violation_source",
                        answer
                    ),
                ]

                if not autonomous_participation:

                    fallback_candidates.append(
                        (
                            "epistemic_unknown",
                            "weiß ich grad nicht sicher."
                        )
                    )

                safe_knowledge_fallback = (
                    choose_reliability_fallback(

                        candidates=(
                            fallback_candidates
                        ),

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "knowledge_repair_invalid"
                        )
                    )
                )

                if not safe_knowledge_fallback:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=knowledge "
                        "reason=no_safe_fallback"
                    )

                    return

                knowledge_repair = (
                    safe_knowledge_fallback
                )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Invalid knowledge repair fallback"
)


# =========================================================
# CAPTURE SAFE BASELINE
#
# This happens AFTER:
#
# Writer hard rules
# Self Guard
# Knowledge Guard
#
# This becomes our recovery draft
# if a later style/voice layer breaks.
# =========================================================

marker = '''        # -------------------------------------------------
        # FRESH CHANNEL HISTORY FOR LOCAL VOICE
        # -------------------------------------------------
'''


baseline_block = '''        # =====================================================
        # B3D SAFE BASELINE CAPTURE
        # =====================================================

        reliability_baseline_answer = (
            choose_reliability_fallback(

                candidates=[
                    (
                        "post_knowledge_writer",
                        answer
                    ),
                ],

                curiosity_result=(
                    curiosity_result
                ),

                self_evidence=(
                    self_evidence
                ),

                knowledge_constraint=(
                    knowledge_constraint
                ),

                username=(
                    username
                ),

                stage=(
                    "baseline_capture"
                )
            )
        )

        if reliability_baseline_answer:

            answer = (
                reliability_baseline_answer
            )

            print(
                "[RELIABILITY BASELINE] "
                f"user={username} "
                f"answer={answer!r}"
            )

        else:

            print(
                "[RELIABILITY BASELINE WARNING] "
                f"user={username} "
                "reason=no_clean_baseline"
            )

'''


bot = insert_before_once(

    bot,
    marker,
    baseline_block,

    "Safe baseline capture"
)


# =========================================================
# PRE-VOICE QUESTION SHAPE
# =========================================================

old = '''                else:
                    print(
                        "[QUESTION SHAPE ABORT] "
                        f"user={username} "
                        "reason=repair_and_failsafe_failed"
                    )
                    return
'''


new = '''                else:

                    safe_question_fallback = (
                        choose_reliability_fallback(

                            candidates=[
                                (
                                    "pre_question_source",
                                    source_before_question_repair
                                ),
                                (
                                    "safe_baseline",
                                    reliability_baseline_answer
                                ),
                            ],

                            curiosity_result=(
                                curiosity_result
                            ),

                            self_evidence=(
                                self_evidence
                            ),

                            knowledge_constraint=(
                                knowledge_constraint
                            ),

                            username=(
                                username
                            ),

                            stage=(
                                "pre_voice_question"
                            )
                        )
                    )

                    if not safe_question_fallback:

                        print(
                            "[SILENT FINAL] "
                            f"user={username} "
                            "stage=pre_voice_question "
                            "reason=no_safe_fallback"
                        )

                        return

                    answer = (
                        safe_question_fallback
                    )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Pre-Voice Question no-abort fallback"
)


# =========================================================
# LOCAL VOICE QUESTION ABORT
# =========================================================

old = '''                print(
                    "[LOCAL VOICE QUESTION ABORT] "
                    f"user={username} "
                    f"violations="
                    f"{reverted_question_violations}"
                )

                return
'''


new = '''                safe_voice_question_fallback = (
                    choose_reliability_fallback(

                        candidates=[
                            (
                                "safe_baseline",
                                reliability_baseline_answer
                            ),
                            (
                                "writer_before_voice",
                                original_writer_answer
                            ),
                        ],

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "post_voice_question"
                        )
                    )
                )

                if not safe_voice_question_fallback:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=post_voice_question "
                        "reason=no_safe_fallback"
                    )

                    return

                answer = (
                    safe_voice_question_fallback
                )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Post-Voice Question no-abort fallback"
)


# =========================================================
# LOCAL VOICE SELF ABORT
# =========================================================

old = '''                print(
                    "[LOCAL VOICE SELF ABORT] "
                    f"user={username} "
                    f"violations="
                    f"{reverted_self_violations}"
                )

                return
'''


new = '''                safe_voice_self_fallback = (
                    choose_reliability_fallback(

                        candidates=[
                            (
                                "safe_baseline",
                                reliability_baseline_answer
                            ),
                            (
                                "writer_before_voice",
                                original_writer_answer
                            ),
                        ],

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "post_voice_self"
                        )
                    )
                )

                if not safe_voice_self_fallback:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=post_voice_self "
                        "reason=no_safe_fallback"
                    )

                    return

                answer = (
                    safe_voice_self_fallback
                )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Post-Voice Self no-abort fallback"
)


# =========================================================
# QUESTION GUARD 2.1 - REPAIR FAILED
# =========================================================

old = '''                if not question_repair:

                    print(
                        "[QUESTION GUARD ABORT] "
                        f"user={username}"
                    )

                    return
'''


new = '''                if not question_repair:

                    question_repair = (
                        choose_reliability_fallback(

                            candidates=[
                                (
                                    "safe_baseline",
                                    reliability_baseline_answer
                                ),
                                (
                                    "writer_before_voice",
                                    original_writer_answer
                                ),
                                (
                                    "current_answer",
                                    answer
                                ),
                            ],

                            curiosity_result=(
                                curiosity_result
                            ),

                            self_evidence=(
                                self_evidence
                            ),

                            knowledge_constraint=(
                                knowledge_constraint
                            ),

                            username=(
                                username
                            ),

                            stage=(
                                "question_guard_repair_failed"
                            )
                        )
                    )

                    if not question_repair:

                        print(
                            "[SILENT FINAL] "
                            f"user={username} "
                            "stage=question_guard "
                            "reason=no_safe_fallback"
                        )

                        return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Question Guard repair failure fallback"
)


old = '''                    print(
                        "[QUESTION GUARD ABORT] "
                        f"user={username} "
                        "reason=repair_still_question"
                    )

                    return
'''


new = '''                    safe_question_guard_fallback = (
                        choose_reliability_fallback(

                            candidates=[
                                (
                                    "safe_baseline",
                                    reliability_baseline_answer
                                ),
                                (
                                    "writer_before_voice",
                                    original_writer_answer
                                ),
                                (
                                    "question_repair",
                                    question_repair
                                ),
                            ],

                            curiosity_result=(
                                curiosity_result
                            ),

                            self_evidence=(
                                self_evidence
                            ),

                            knowledge_constraint=(
                                knowledge_constraint
                            ),

                            username=(
                                username
                            ),

                            stage=(
                                "question_guard_still_question"
                            )
                        )
                    )

                    if not safe_question_guard_fallback:

                        print(
                            "[SILENT FINAL] "
                            f"user={username} "
                            "stage=question_guard "
                            "reason=no_safe_fallback"
                        )

                        return

                    question_repair = (
                        safe_question_guard_fallback
                    )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Question Guard still-question fallback"
)


# =========================================================
# EXPRESSION FINAL - REPAIR FAILED
# =========================================================

old = '''            if not expression_repair:

                print(
                    "[EXPRESSION FINAL ABORT] "
                    f"user={username} "
                    "reason=repair_failed "
                    f"violations="
                    f"{expression_guard.violations_after}"
                )

                return
'''


new = '''            if not expression_repair:

                expression_repair = (
                    choose_reliability_fallback(

                        candidates=[
                            (
                                "safe_baseline",
                                reliability_baseline_answer
                            ),
                            (
                                "writer_before_voice",
                                original_writer_answer
                            ),
                            (
                                "expression_cleaned",
                                expression_guard.cleaned
                            ),
                        ],

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "expression_repair_failed"
                        )
                    )
                )

                if not expression_repair:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=expression "
                        "reason=no_safe_fallback"
                    )

                    return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Expression repair failure fallback"
)


# =========================================================
# EXPRESSION FINAL - HARD GUARD AFTER REPAIR
# =========================================================

old = '''            if repair_hard_violations:

                print(
                    "[EXPRESSION FINAL ABORT] "
                    f"user={username} "
                    "reason=hard_guard_after_repair "
                    f"violations="
                    f"{repair_hard_violations}"
                )

                return
'''


new = '''            if repair_hard_violations:

                expression_repair = (
                    choose_reliability_fallback(

                        candidates=[
                            (
                                "safe_baseline",
                                reliability_baseline_answer
                            ),
                            (
                                "writer_before_voice",
                                original_writer_answer
                            ),
                        ],

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "expression_hard_after_repair"
                        )
                    )
                )

                if not expression_repair:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=expression "
                        "reason=no_safe_fallback"
                    )

                    return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Expression hard-guard fallback"
)


# =========================================================
# EXPRESSION SECOND GUARD
#
# This needs a structural replacement because the old
# code unconditionally assigns cleaned after the abort.
# =========================================================

old = '''            if not (
                second_expression_guard
                .send_allowed
            ):

                print(
                    "[EXPRESSION FINAL ABORT] "
                    f"user={username} "
                    "reason=still_blocked_after_repair "
                    f"violations="
                    f"{second_expression_guard.violations_after}"
                )

                return

            answer = (
                second_expression_guard.cleaned
            )
'''


new = '''            if not (
                second_expression_guard
                .send_allowed
            ):

                safe_expression_fallback = (
                    choose_reliability_fallback(

                        candidates=[
                            (
                                "safe_baseline",
                                reliability_baseline_answer
                            ),
                            (
                                "writer_before_voice",
                                original_writer_answer
                            ),
                            (
                                "expression_repair",
                                expression_repair
                            ),
                        ],

                        curiosity_result=(
                            curiosity_result
                        ),

                        self_evidence=(
                            self_evidence
                        ),

                        knowledge_constraint=(
                            knowledge_constraint
                        ),

                        username=(
                            username
                        ),

                        stage=(
                            "expression_still_blocked"
                        )
                    )
                )

                if not safe_expression_fallback:

                    print(
                        "[SILENT FINAL] "
                        f"user={username} "
                        "stage=expression "
                        "reason=no_safe_fallback"
                    )

                    return

                answer = (
                    safe_expression_fallback
                )

            else:

                answer = (
                    second_expression_guard.cleaned
                )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Expression second-guard fallback"
)


# =========================================================
# FINAL QUESTION GUARD
# =========================================================

old = '''        if final_question_violations:

            print(
                "[QUESTION FINAL ABORT] "
                f"user={username} "
                f"violations="
                f"{final_question_violations} "
                f"answer={answer!r}"
            )

            return
'''


new = '''        if final_question_violations:

            safe_final_question = (
                choose_reliability_fallback(

                    candidates=[
                        (
                            "current_answer",
                            answer
                        ),
                        (
                            "safe_baseline",
                            reliability_baseline_answer
                        ),
                        (
                            "writer_before_voice",
                            original_writer_answer
                        ),
                    ],

                    curiosity_result=(
                        curiosity_result
                    ),

                    self_evidence=(
                        self_evidence
                    ),

                    knowledge_constraint=(
                        knowledge_constraint
                    ),

                    username=(
                        username
                    ),

                    stage=(
                        "final_question"
                    )
                )
            )

            if not safe_final_question:

                print(
                    "[SILENT FINAL] "
                    f"user={username} "
                    "stage=final_question "
                    "reason=no_safe_fallback"
                )

                return

            answer = (
                safe_final_question
            )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Final Question no-abort fallback"
)


# =========================================================
# FINAL SELF GUARD
# =========================================================

old = '''        if final_self_violations:

            print(
                "[SELF FINAL ABORT] "
                f"user={username} "
                f"violations="
                f"{final_self_violations} "
                f"answer={answer!r}"
            )

            return
'''


new = '''        if final_self_violations:

            safe_final_self = (
                choose_reliability_fallback(

                    candidates=[
                        (
                            "safe_baseline",
                            reliability_baseline_answer
                        ),
                        (
                            "writer_before_voice",
                            original_writer_answer
                        ),
                        (
                            "epistemic_unknown",
                            "weiß ich grad nicht sicher."
                        ),
                    ],

                    curiosity_result=(
                        curiosity_result
                    ),

                    self_evidence=(
                        self_evidence
                    ),

                    knowledge_constraint=(
                        knowledge_constraint
                    ),

                    username=(
                        username
                    ),

                    stage=(
                        "final_self"
                    )
                )
            )

            if not safe_final_self:

                print(
                    "[SILENT FINAL] "
                    f"user={username} "
                    "stage=final_self "
                    "reason=no_safe_fallback"
                )

                return

            answer = (
                safe_final_self
            )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Final Self no-abort fallback"
)


# =========================================================
# GARBLED FALLBACK SHOULD USE SAFE BASELINE FIRST
# =========================================================

old = '''            fallback_candidate = clean_generated_answer(
                original_writer_answer
            )
'''


new = '''            fallback_candidate = clean_generated_answer(
                reliability_baseline_answer
                or
                original_writer_answer
            )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Garbled uses safe baseline"
)


old = '''                    print(
                        "[GARBLED OUTPUT ABORT] "
                        f"user={username} "
                        "reason=no_safe_fallback"
                    )
                    return
'''


new = '''                    emergency_garbled_fallback = (
                        choose_reliability_fallback(

                            candidates=[
                                (
                                    "safe_baseline",
                                    reliability_baseline_answer
                                ),
                                (
                                    "writer_before_voice",
                                    original_writer_answer
                                ),
                            ],

                            curiosity_result=(
                                curiosity_result
                            ),

                            self_evidence=(
                                self_evidence
                            ),

                            knowledge_constraint=(
                                knowledge_constraint
                            ),

                            username=(
                                username
                            ),

                            stage=(
                                "final_garbled"
                            )
                        )
                    )

                    if not emergency_garbled_fallback:

                        print(
                            "[SILENT FINAL] "
                            f"user={username} "
                            "stage=garbled "
                            "reason=no_safe_fallback"
                        )

                        return

                    answer = (
                        emergency_garbled_fallback
                    )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Final Garbled emergency fallback"
)


# =========================================================
# CONTEXT FRESHNESS
#
# OLD:
#
# all direct/continuation = max 2
#
# NEW:
#
# participation = 1
# continuation  = at least 3
# direct        = at least 6
#
# Direct Discord replies remain anchored to the original
# message even in a busy channel.
# =========================================================

old = '''            if autonomous_participation:

                freshness_limit = (
                    min(
                        1,
                        CONTEXT_FRESHNESS_MAX_NEW_MESSAGES
                    )
                )

            else:

                freshness_limit = (
                    CONTEXT_FRESHNESS_MAX_NEW_MESSAGES
                )
'''


new = '''            if autonomous_participation:

                freshness_limit = (
                    1
                )

            elif conversation_continuation:

                freshness_limit = (
                    max(
                        3,
                        CONTEXT_FRESHNESS_MAX_NEW_MESSAGES
                    )
                )

            else:

                freshness_limit = (
                    max(
                        6,
                        CONTEXT_FRESHNESS_MAX_NEW_MESSAGES
                    )
                )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Context freshness by conversation mode"
)


old = '''                print(
                    "[CONTEXT STALE] "
                    f"user={username} "
                    f"mode="
                    f"{voice_conversation_mode} "
                    f"start_revision="
                    f"{response_start_revision} "
                    f"delta="
                    f"{freshness_delta} "
                    f"limit="
                    f"{freshness_limit} "
                    f"answer="
                    f"{answer!r}"
                )

                return
'''


new = '''                print(
                    "[CONTEXT STALE] "
                    f"user={username} "
                    f"mode="
                    f"{voice_conversation_mode} "
                    f"start_revision="
                    f"{response_start_revision} "
                    f"delta="
                    f"{freshness_delta} "
                    f"limit="
                    f"{freshness_limit} "
                    f"answer="
                    f"{answer!r}"
                )

                print(
                    "[SILENT FINAL] "
                    f"user={username} "
                    "stage=freshness "
                    f"reason=context_stale "
                    f"delta={freshness_delta} "
                    f"limit={freshness_limit}"
                )

                return
'''


bot = replace_once(

    bot,
    old,
    new,

    "Context stale silence diagnostics"
)


# =========================================================
# SYNTAX CHECK BEFORE WRITE
# =========================================================

try:

    ast.parse(
        bot,
        filename=str(
            BOT_PATH
        )
    )

except SyntaxError as error:

    fail(
        "bot.py syntax error after patch: "
        f"line={error.lineno} "
        f"{error.msg}. "
        "Nothing overwritten."
    )


ok(
    "bot.py syntax check"
)


# =========================================================
# BACKUP
# =========================================================

stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)


backup = Path(

    f"bot.py.before-B3D-"
    f"{stamp}.bak"
)


shutil.copy2(
    BOT_PATH,
    backup
)


print(
    f"[BACKUP] {backup}"
)


# =========================================================
# WRITE
# =========================================================

tmp = Path(
    "bot.py.B3D.tmp"
)


tmp.write_text(
    bot,
    encoding="utf-8"
)


tmp.replace(
    BOT_PATH
)


ok(
    "bot.py written"
)


# =========================================================
# VERIFY
# =========================================================

installed = (
    BOT_PATH.read_text(
        encoding="utf-8"
    )
)


required = [

    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',

    "choose_reliability_fallback",

    "[RELIABILITY FALLBACK]",

    "[RELIABILITY BASELINE]",

    "[SILENT FINAL]",

    "Response Reliability v1: ACTIVE",

    "No Lost Harmless Replies: ACTIVE",

    "Safe Draft Fallback: ACTIVE",

    "Explicit Silence Diagnostics: ACTIVE",

    "max(\n                        6,",

    "max(\n                        3,",
]


missing = [

    marker

    for marker
    in required

    if marker not in installed
]


if missing:

    fail(
        "Verification missing: "
        +
        ", ".join(
            missing
        )
    )


print("")

print(
    "============================================"
)

print(
    "EVILNAE B3D RELIABILITY COMPLETE"
)

print(
    "============================================"
)

print(
    f"Bot Version: "
    f"{TARGET_BOT_VERSION}"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] No Lost Harmless Replies"
)

print(
    "  [✓] Safe Writer Baseline"
)

print(
    "  [✓] Writer Finalization Recovery"
)

print(
    "  [✓] Self Guard Recovery"
)

print(
    "  [✓] Knowledge Guard Recovery"
)

print(
    "  [✓] Question Guard Recovery"
)

print(
    "  [✓] Expression Guard Recovery"
)

print(
    "  [✓] Final Self/Question Recovery"
)

print(
    "  [✓] Garbled Draft Recovery"
)

print(
    "  [✓] Direct Freshness = 6+"
)

print(
    "  [✓] Continuation Freshness = 3+"
)

print(
    "  [✓] Participation Freshness = 1"
)

print(
    "  [✓] Explicit SILENT FINAL logging"
)

print("")

print(
    "Character / Lore / Preferences:"
)

print(
    "  UNCHANGED"
)

print("")

print(
    f"Backup: {backup}"
)

print("")

print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py participation.py "
    "evilnae_emotes.py "
    "conversation_understanding.py "
    "brain.py curiosity.py "
    "self_model.py agency.py "
    "conversation_world.py "
    "understanding.py perception.py "
    "natural_response.py naturalness.py "
    "coherence.py expression.py "
    "inner_state.py local_voice.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
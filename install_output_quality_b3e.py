from pathlib import Path
from datetime import datetime
import ast
import shutil

BOT = Path("bot.py")
QUALITY = Path("response_quality.py")

EXPECTED = (
    "2.12.1-reliability-b3d"
)

TARGET = (
    "2.13.0-output-quality-b3e"
)


def fail(
    message
):

    raise SystemExit(
        f"\n[INSTALL ERROR] {message}\n"
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

    ok(
        label
    )

    return (
        text.replace(
            old,
            new,
            1
        )
    )


def insert_before(
    text,
    marker,
    block,
    label
):

    if block in text:

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

    ok(
        label
    )

    return (
        text.replace(
            marker,
            block + marker,
            1
        )
    )


def insert_after(
    text,
    marker,
    block,
    label
):

    if block in text:

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

    ok(
        label
    )

    return (
        text.replace(
            marker,
            marker + block,
            1
        )
    )


print(
    "[B3E OUTPUT QUALITY PACK] starting..."
)


if not BOT.exists():

    fail(
        "bot.py missing"
    )


if not QUALITY.exists():

    fail(
        "response_quality.py missing"
    )


quality_text = (
    QUALITY.read_text(
        encoding="utf-8"
    )
)


if (
    'OUTPUT_QUALITY_VERSION = "2.0"'
    not in quality_text
):

    fail(
        "response_quality.py is not v2.0"
    )


try:

    ast.parse(
        quality_text,
        filename=str(
            QUALITY
        )
    )

except SyntaxError as error:

    fail(
        "response_quality.py syntax error: "
        f"line={error.lineno} "
        f"{error.msg}"
    )


ok(
    "response_quality.py v2.0"
)


bot = (
    BOT.read_text(
        encoding="utf-8"
    )
)


if (
    f'BOT_VERSION = "{TARGET}"'
    in bot
):

    print(
        "B3E already installed."
    )

    raise SystemExit(
        0
    )


if (
    f'BOT_VERSION = "{EXPECTED}"'
    not in bot
):

    fail(
        "Unexpected bot version. "
        f"Expected {EXPECTED}."
    )


for required in (
    "choose_reliability_fallback",
    "Response Reliability v1: ACTIVE",
    "reliability_baseline_answer",
    "[SILENT FINAL]",
):

    if required not in bot:

        fail(
            "B3D feature missing: "
            f"{required}"
        )


ok(
    "B3D base detected"
)


# =========================================================
# IMPORT
# =========================================================

bot = insert_before(

    bot,

    "from dotenv import load_dotenv\n",

    '''from response_quality import (
    OUTPUT_QUALITY_VERSION,
    analyze_response_quality,
    compare_response_candidates,
    select_best_quality_candidate,
    trim_safe_generic_tail,
    format_quality_for_writer,
    format_quality_debug,
    format_candidate_decision_debug,
)

''',

    "Output Quality import"
)


# =========================================================
# VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED}"',

    f'BOT_VERSION = "{TARGET}"',

    "Bot version"
)


# =========================================================
# STARTUP STATUS
# =========================================================

bot = insert_after(

    bot,

    '''    print(
        "Explicit Silence Diagnostics: ACTIVE"
    )

''',

    '''    print(
        f"Output Quality v{OUTPUT_QUALITY_VERSION}: ACTIVE"
    )

    print(
        "Qwen Acceptance v2: ACTIVE"
    )

    print(
        "Semantic Repetition v2: ACTIVE"
    )

    print(
        "Grammar / Garbled v2: ACTIVE"
    )

    print(
        "One-Thought Quality Check v2: ACTIVE"
    )

    print(
        "Targeted Quality Repair: ACTIVE"
    )

''',

    "Output Quality startup status"
)


# =========================================================
# FRESHNESS STARTUP TEXT
# =========================================================

bot = replace_once(

    bot,

    '''    print(
        "Context Freshness Guard: ACTIVE "
        f"(max={CONTEXT_FRESHNESS_MAX_NEW_MESSAGES})"
    )
''',

    '''    print(
        "Context Freshness Guard: ACTIVE "
        f"(base={CONTEXT_FRESHNESS_MAX_NEW_MESSAGES}, "
        "direct>=6, continuation>=3, participation=1)"
    )
''',

    "Freshness startup diagnostics"
)


# =========================================================
# WRITER QUALITY BASELINE
# =========================================================

bot = replace_once(

    bot,

    '''        original_writer_answer = (
            answer
        )

        try:
''',

    '''        original_writer_answer = (
            answer
        )

        # =====================================================
        # B3E WRITER QUALITY BASELINE
        # =====================================================

        writer_quality_analysis = (
            analyze_response_quality(

                original_writer_answer,

                user_text=(
                    user_text
                ),

                recent_evilnae_messages=(
                    voice_channel_evilnae_messages
                )
            )
        )

        print(
            format_quality_debug(
                writer_quality_analysis,
                label="WRITER QUALITY"
            )
        )

        try:
''',

    "Writer quality baseline"
)


# =========================================================
# QWEN ACCEPTANCE v2
# =========================================================

bot = insert_before(

    bot,

    '''            # ---------------------------------------------
            # FINAL EVILNAE HARD GUARD
''',

    '''            # ---------------------------------------------
            # B3E QWEN ACCEPTANCE v2
            #
            # Qwen is a candidate,
            # not an authority.
            # ---------------------------------------------

            voice_quality_decision = (
                compare_response_candidates(

                    candidate=(
                        voice_candidate
                    ),

                    baseline=(
                        original_writer_answer
                    ),

                    user_text=(
                        user_text
                    ),

                    recent_evilnae_messages=(
                        voice_channel_evilnae_messages
                    ),

                    meaning_preserved=(
                        getattr(
                            voice_result,
                            "meaning_preserved",
                            1.0
                        )
                    )
                )
            )

            print(
                format_candidate_decision_debug(
                    voice_quality_decision
                )
            )

            if not (
                voice_quality_decision
                .accepted
            ):

                print(
                    "[QWEN CANDIDATE REJECTED] "
                    f"user={username} "
                    f"reason="
                    f"{voice_quality_decision.reason}"
                )

                voice_candidate = ""

            else:

                print(
                    "[QWEN CANDIDATE ACCEPTED] "
                    f"user={username} "
                    f"reason="
                    f"{voice_quality_decision.reason}"
                )

''',

    "Qwen Acceptance v2"
)


# =========================================================
# FINAL OUTPUT QUALITY v2
# =========================================================

bot = insert_before(

    bot,

    '''        # =================================================
        # 11.9 EVILNAE APPLICATION EMOTE LAYER
''',

    '''        # =================================================
        # B3E FINAL OUTPUT QUALITY v2
        # =================================================

        answer = (
            trim_safe_generic_tail(
                answer
            )
        )

        pre_final_quality_analysis = (
            analyze_response_quality(

                answer,

                user_text=(
                    user_text
                ),

                recent_evilnae_messages=(
                    final_channel_evilnae_messages
                )
            )
        )

        print(
            format_quality_debug(
                pre_final_quality_analysis,
                label="OUTPUT QUALITY PRE-FINAL"
            )
        )

        quality_repair_needed = (
            pre_final_quality_analysis
            .grammar_score
            >= 3

            or

            pre_final_quality_analysis
            .repetition_score
            >= 2

            or

            pre_final_quality_analysis
            .generic_score
            >= 3

            or

            pre_final_quality_analysis
            .total_penalty
            >= 5
        )

        if quality_repair_needed:

            quality_repair_context = (
                writer_context
                + "\\n\\n"
                + format_quality_for_writer(
                    pre_final_quality_analysis
                )
            )

            quality_repair = (
                await repair_writer_answer(

                    original_answer=(
                        answer
                    ),

                    violation_reasons=[
                        "output_quality_v2",
                        *pre_final_quality_analysis.issues,
                    ],

                    writer_context=(
                        quality_repair_context
                    ),

                    current_mood=(
                        current_mood
                    ),

                    username=(
                        username
                    ),

                    token_limit=(
                        writer_token_limit
                    ),

                    autonomous_participation=(
                        autonomous_participation
                    )
                )
            )

            if quality_repair:

                quality_repair = (
                    clean_generated_answer(
                        quality_repair
                    )
                )

                quality_repair = (
                    enforce_permanent_expression_bans(
                        quality_repair
                    )
                )

                quality_repair_hard = (
                    get_writer_violation_reasons(

                        answer=(
                            quality_repair
                        ),

                        decision=(
                            decision
                        ),

                        autonomous_participation=(
                            autonomous_participation
                        )
                    )
                )

                quality_repair_questions = (
                    question_output_violation_reasons(
                        quality_repair,
                        curiosity_result
                    )
                )

                quality_repair_self = (
                    self_knowledge_violation_reasons(
                        quality_repair,
                        self_evidence
                    )
                )

                quality_repair_knowledge = (
                    knowledge_violation_reasons(
                        quality_repair,
                        knowledge_constraint
                    )
                )

                quality_repair_garbled = (
                    analyze_garbled_output(
                        quality_repair
                    )
                )

                quality_expression_guard = (
                    apply_expression_final_guard(
                        quality_repair,
                        final_expression_plan
                    )
                )

                repair_safe = (
                    not quality_repair_hard

                    and

                    not quality_repair_questions

                    and

                    not quality_repair_self

                    and

                    not quality_repair_knowledge

                    and

                    not quality_repair_garbled
                    .garbled

                    and

                    quality_expression_guard
                    .send_allowed
                )

                if repair_safe:

                    quality_repair_candidate = (
                        trim_safe_generic_tail(
                            quality_expression_guard
                            .cleaned
                        )
                    )

                    quality_repair_analysis = (
                        analyze_response_quality(

                            quality_repair_candidate,

                            user_text=(
                                user_text
                            ),

                            recent_evilnae_messages=(
                                final_channel_evilnae_messages
                            )
                        )
                    )

                    if (
                        quality_repair_analysis
                        .total_penalty
                        <
                        pre_final_quality_analysis
                        .total_penalty
                    ):

                        print(
                            "[OUTPUT QUALITY REPAIR ACCEPTED] "
                            f"user={username} "
                            f"before="
                            f"{pre_final_quality_analysis.total_penalty} "
                            f"after="
                            f"{quality_repair_analysis.total_penalty}"
                        )

                        answer = (
                            quality_repair_candidate
                        )

                    else:

                        print(
                            "[OUTPUT QUALITY REPAIR REJECTED] "
                            f"user={username} "
                            "reason=no_quality_gain "
                            f"before="
                            f"{pre_final_quality_analysis.total_penalty} "
                            f"after="
                            f"{quality_repair_analysis.total_penalty}"
                        )

                else:

                    print(
                        "[OUTPUT QUALITY REPAIR REJECTED] "
                        f"user={username} "
                        "reason=guard_failure "
                        f"hard={quality_repair_hard} "
                        f"question={quality_repair_questions} "
                        f"self={quality_repair_self} "
                        f"knowledge={quality_repair_knowledge} "
                        f"garbled="
                        f"{quality_repair_garbled.garbled} "
                        f"expression="
                        f"{quality_expression_guard.send_allowed}"
                    )

            else:

                print(
                    "[OUTPUT QUALITY REPAIR FAILED] "
                    f"user={username}"
                )

        # -------------------------------------------------
        # BEST SAFE STAGE
        # -------------------------------------------------

        final_quality_selection = (
            select_best_quality_candidate(

                candidates=[
                    (
                        "final",
                        answer
                    ),
                    (
                        "writer",
                        original_writer_answer
                    ),
                    (
                        "reliability_baseline",
                        reliability_baseline_answer
                    ),
                ],

                user_text=(
                    user_text
                ),

                recent_evilnae_messages=(
                    final_channel_evilnae_messages
                )
            )
        )

        if final_quality_selection.text:

            if (
                final_quality_selection
                .source
                !=
                "final"
            ):

                print(
                    "[OUTPUT QUALITY FALLBACK] "
                    f"user={username} "
                    f"source="
                    f"{final_quality_selection.source}"
                )

            answer = (
                final_quality_selection
                .text
            )

        final_quality_analysis = (
            analyze_response_quality(

                answer,

                user_text=(
                    user_text
                ),

                recent_evilnae_messages=(
                    final_channel_evilnae_messages
                )
            )
        )

        print(
            format_quality_debug(
                final_quality_analysis,
                label="OUTPUT QUALITY FINAL"
            )
        )

''',

    "Final Output Quality v2"
)


# =========================================================
# VALIDATE BEFORE WRITE
# =========================================================

try:

    ast.parse(
        bot,
        filename=str(
            BOT
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
# BACKUP + WRITE
# =========================================================

stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)


backup = Path(
    f"bot.py.before-B3E-{stamp}.bak"
)


shutil.copy2(
    BOT,
    backup
)


print(
    f"[BACKUP] {backup}"
)


tmp = Path(
    "bot.py.B3E.tmp"
)


tmp.write_text(
    bot,
    encoding="utf-8"
)


tmp.replace(
    BOT
)


ok(
    "bot.py written"
)


# =========================================================
# VERIFY
# =========================================================

installed = (
    BOT.read_text(
        encoding="utf-8"
    )
)


for required in (

    f'BOT_VERSION = "{TARGET}"',

    "OUTPUT_QUALITY_VERSION",

    "Qwen Acceptance v2: ACTIVE",

    "Semantic Repetition v2: ACTIVE",

    "Grammar / Garbled v2: ACTIVE",

    "Targeted Quality Repair: ACTIVE",

    "[QWEN CANDIDATE REJECTED]",

    "[OUTPUT QUALITY REPAIR ACCEPTED]",

    "[OUTPUT QUALITY FINAL]",

    "direct>=6, continuation>=3, participation=1",
):

    if required not in installed:

        fail(
            f"Verification missing: "
            f"{required}"
        )


print("")
print(
    "============================================"
)
print(
    "EVILNAE B3E OUTPUT QUALITY COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: {TARGET}"
)

print(
    "Output Quality: 2.0"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] Generic/Bot Response Guard v2"
)

print(
    "  [✓] One-Thought Quality Check v2"
)

print(
    "  [✓] Qwen Acceptance v2"
)

print(
    "  [✓] Grammar/Garbled Quality v2"
)

print(
    "  [✓] Semantic Phrase Family Repetition"
)

print(
    "  [✓] Safe Generic Tail Cleanup"
)

print(
    "  [✓] Targeted Quality Repair"
)

print(
    "  [✓] Best Safe Draft Selection"
)

print(
    "  [✓] Freshness Startup Diagnostics"
)

print("")

print(
    "Character / Lore / Preferences: UNCHANGED"
)

print(
    f"Backup: {backup}"
)

print("")

print(
    "NEXT:"
)

print(
    "python response_quality.py"
)

print(
    "python -m py_compile "
    "bot.py response_quality.py "
    "participation.py evilnae_emotes.py "
    "conversation_understanding.py brain.py "
    "curiosity.py self_model.py agency.py "
    "conversation_world.py understanding.py "
    "perception.py natural_response.py "
    "naturalness.py coherence.py expression.py "
    "inner_state.py local_voice.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
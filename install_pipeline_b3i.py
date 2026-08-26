from pathlib import Path
from datetime import datetime

import ast
import shutil


BOT_PATH = Path("bot.py")

EXPECTED_BOT_VERSION = "2.16.0-performance-b3h"
TARGET_BOT_VERSION = "2.17.0-pipeline-b3i"
PIPELINE_VERSION = "1.0"


def fail(message):
    raise SystemExit(
        f"\n[INSTALL ERROR] {message}\n"
    )


def ok(message):
    print(
        f"[OK] {message}"
    )


def replace_once(
    text,
    old,
    new,
    label,
):
    count = text.count(old)

    if count != 1:
        fail(
            f"{label}: expected 1 match, found {count}"
        )

    ok(label)

    return text.replace(
        old,
        new,
        1,
    )


def insert_before_once(
    text,
    marker,
    block,
    label,
):
    count = text.count(marker)

    if count != 1:
        fail(
            f"{label}: expected 1 marker, found {count}"
        )

    ok(label)

    return text.replace(
        marker,
        block + marker,
        1,
    )


def insert_after_once(
    text,
    marker,
    block,
    label,
):
    count = text.count(marker)

    if count != 1:
        fail(
            f"{label}: expected 1 marker, found {count}"
        )

    ok(label)

    return text.replace(
        marker,
        marker + block,
        1,
    )


def replace_between_once(
    text,
    start_marker,
    end_marker,
    replacement,
    label,
):
    start_count = text.count(
        start_marker
    )

    if start_count != 1:
        fail(
            f"{label}: expected 1 start marker, "
            f"found {start_count}"
        )

    start_index = text.index(
        start_marker
    )

    end_index = text.find(
        end_marker,
        start_index
        +
        len(
            start_marker
        )
    )

    if end_index < 0:
        fail(
            f"{label}: end marker not found "
            "after start marker"
        )

    if end_index <= start_index:
        fail(
            f"{label}: invalid marker order"
        )

    ok(label)

    return (
        text[:start_index]
        +
        replacement
        +
        text[end_index:]
    )


def syntax_check(
    text,
    filename,
):
    try:
        ast.parse(
            text,
            filename=filename,
        )

    except SyntaxError as error:
        fail(
            f"{filename} syntax error after patch: "
            f"line={error.lineno} "
            f"{error.msg}. "
            "Nothing overwritten."
        )

    ok(
        f"{filename} syntax check"
    )


print(
    "[B3I PIPELINE CONSOLIDATION] starting..."
)


if not BOT_PATH.exists():
    fail(
        "bot.py missing"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


if (
    f'BOT_VERSION = "{TARGET_BOT_VERSION}"'
    in bot
):
    print(
        "B3I already installed."
    )

    raise SystemExit(
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


required_previous_features = (
    "PERFORMANCE_VERSION",
    "OUTPUT_QUALITY_VERSION",
    "ROUTING_HARDENING_VERSION",
    "DISCORD_ACTIONS_VERSION",
    "choose_reliability_fallback",
    "reliability_baseline_answer",
    "compare_response_candidates",
    "apply_expression_final_guard",
    "Response Repair API Budget",
)


for marker in required_previous_features:
    if marker not in bot:
        fail(
            "Previous feature missing: "
            f"{marker}"
        )


ok(
    "B3H base detected"
)


# =========================================================
# VERSION
# =========================================================

bot = replace_once(
    bot,
    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"',
    (
        f'BOT_VERSION = "{TARGET_BOT_VERSION}"\n'
        f'PIPELINE_CONSOLIDATION_VERSION = "{PIPELINE_VERSION}"'
    ),
    "Bot + pipeline version",
)


# =========================================================
# CENTRAL PIPELINE CHOOSER
# =========================================================

pipeline_helper = r'''
# =========================================================
# B3I CONSOLIDATED PIPELINE CANDIDATE CHOOSER
#
# Uses B3D as the critical deterministic validator.
# No API call is made here.
#
# A candidate must pass:
#
# - question policy
# - self knowledge
# - source / knowledge authority
# - garbled output
# - Writer hard rules
#
# Safe candidates are then ranked by:
#
# - Output Quality
# - Natural Response score
# - grammar
# - repetition
# =========================================================

def choose_pipeline_candidate(
    *,
    candidates,
    decision,
    curiosity_result,
    self_evidence,
    knowledge_constraint,
    user_text,
    recent_evilnae_messages,
    username,
    stage,
    autonomous_participation=False,
):

    safe_results = []

    for (
        index,
        (
            source,
            candidate
        )
    ) in enumerate(
        candidates
    ):

        candidate = (
            choose_reliability_fallback(

                candidates=[
                    (
                        source,
                        candidate
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
                    f"{stage}/{source}"
                )
            )
        )

        if not candidate:

            print(
                "[PIPELINE CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source} "
                "reason=critical_guard"
            )

            continue

        hard_violations = (
            get_writer_violation_reasons(

                answer=(
                    candidate
                ),

                decision=(
                    decision
                ),

                autonomous_participation=(
                    autonomous_participation
                )
            )
        )

        if hard_violations:

            print(
                "[PIPELINE CANDIDATE REJECTED] "
                f"user={username} "
                f"stage={stage} "
                f"source={source} "
                f"reason=writer_hard "
                f"violations={hard_violations}"
            )

            continue

        quality_analysis = (
            analyze_response_quality(

                candidate,

                user_text=(
                    user_text
                ),

                recent_evilnae_messages=(
                    recent_evilnae_messages
                )
            )
        )

        natural_analysis = (
            analyze_natural_response(

                candidate,

                user_text=(
                    user_text
                ),

                curiosity_allowed=bool(
                    getattr(
                        curiosity_result,
                        "allowed",
                        False
                    )
                ),

                self_unknown=bool(
                    getattr(
                        self_evidence,
                        "strict_unknown",
                        False
                    )
                )
                if self_evidence is not None
                else False
            )
        )

        quality_penalty = int(
            getattr(
                quality_analysis,
                "total_penalty",
                0
            )
            or
            0
        )

        natural_penalty = int(
            getattr(
                natural_analysis,
                "score",
                0
            )
            or
            0
        )

        grammar_penalty = int(
            getattr(
                quality_analysis,
                "grammar_score",
                0
            )
            or
            0
        )

        repetition_penalty = int(
            getattr(
                quality_analysis,
                "repetition_score",
                0
            )
            or
            0
        )

        combined_penalty = (
            quality_penalty
            +
            min(
                5,
                natural_penalty
            )
        )

        print(
            "[PIPELINE CANDIDATE SAFE] "
            f"user={username} "
            f"stage={stage} "
            f"source={source} "
            f"combined={combined_penalty} "
            f"quality={quality_penalty} "
            f"natural={natural_penalty} "
            f"grammar={grammar_penalty} "
            f"repeat={repetition_penalty}"
        )

        safe_results.append(
            (
                (
                    combined_penalty,
                    grammar_penalty,
                    repetition_penalty,
                    index,
                ),
                source,
                candidate
            )
        )

    if not safe_results:

        print(
            "[PIPELINE NO SAFE CANDIDATE] "
            f"user={username} "
            f"stage={stage}"
        )

        return (
            "",
            "none"
        )

    safe_results.sort(
        key=lambda item:
            item[0]
    )

    (
        _,
        source,
        candidate
    ) = safe_results[
        0
    ]

    print(
        "[PIPELINE CHOICE] "
        f"user={username} "
        f"stage={stage} "
        f"source={source} "
        f"answer={candidate!r}"
    )

    return (
        candidate,
        source
    )


'''


social_action_marker = '''# =========================================================
# SOCIAL ACTION TEXT
# =========================================================
'''


bot = insert_before_once(
    bot,
    social_action_marker,
    pipeline_helper,
    "Central pipeline candidate chooser",
)


# =========================================================
# PRE-VOICE CONSOLIDATION
# =========================================================

prevoice_start = '''        # =====================================================
        # B3B.1B NATURAL RESPONSE GUARD
'''

prevoice_end = '''        original_writer_answer = (
            answer
        )
'''

prevoice_replacement = r'''        # =====================================================
        # B3I CONSOLIDATED PRE-VOICE GATE
        #
        # Critical Writer/Self/Knowledge checks already ran.
        #
        # Soft Natural Response problems are logged and
        # delegated to Local Voice / Output Quality instead
        # of spending another OpenAI repair call here.
        # =====================================================

        prevoice_natural_analysis = (
            analyze_natural_response(

                answer,

                user_text=(
                    user_text
                ),

                curiosity_allowed=(
                    curiosity_result.allowed
                ),

                self_unknown=bool(
                    getattr(
                        self_evidence,
                        "strict_unknown",
                        False
                    )
                )
            )
        )

        print(
            format_natural_response_debug(
                prevoice_natural_analysis
            )
        )

        if (
            prevoice_natural_analysis
            .rewrite_required
        ):

            print(
                "[PIPELINE SOFT DEFERRED] "
                f"user={username} "
                "stage=pre_voice "
                f"matches="
                f"{prevoice_natural_analysis.matches}"
            )

        (
            prevoice_answer,
            prevoice_source
        ) = choose_pipeline_candidate(

            candidates=[
                (
                    "writer_after_critical",
                    answer
                ),
                (
                    "reliability_baseline",
                    reliability_baseline_answer
                ),
            ],

            decision=(
                decision
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

            user_text=(
                user_text
            ),

            recent_evilnae_messages=(
                voice_channel_evilnae_messages
            ),

            username=(
                username
            ),

            stage=(
                "pre_voice"
            ),

            autonomous_participation=(
                autonomous_participation
            )
        )

        if not prevoice_answer:

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=pre_voice "
                "reason=no_safe_candidate"
            )

            return

        answer = (
            prevoice_answer
        )

        print(
            "[PIPELINE PRE-VOICE READY] "
            f"user={username} "
            f"source={prevoice_source}"
        )

'''


bot = replace_between_once(
    bot,
    prevoice_start,
    prevoice_end,
    prevoice_replacement,
    "Pre-Voice consolidation",
)


# =========================================================
# POST-VOICE CONSOLIDATION
# =========================================================

postvoice_start = '''        # =====================================================
        # B3B.1B POST-VOICE NATURAL RESPONSE GUARD
'''

postvoice_end = '''        # =================================================
        # 11.6 EXPRESSION FINAL GUARD
'''

postvoice_replacement = r'''        # =====================================================
        # B3I CONSOLIDATED POST-VOICE GATE
        #
        # Replaces the old chain of:
        #
        # Natural Response revert
        # Question revert
        # Self revert
        # Knowledge revert
        # Question Guard 2.1
        # Naturalness repair
        #
        # One deterministic candidate choice.
        # No API repair here.
        # =====================================================

        (
            post_voice_answer,
            post_voice_source
        ) = choose_pipeline_candidate(

            candidates=[
                (
                    "voice_or_writer",
                    answer
                ),
                (
                    "reliability_baseline",
                    reliability_baseline_answer
                ),
                (
                    "writer_before_voice",
                    original_writer_answer
                ),
            ],

            decision=(
                decision
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

            user_text=(
                user_text
            ),

            recent_evilnae_messages=(
                voice_channel_evilnae_messages
            ),

            username=(
                username
            ),

            stage=(
                "post_voice"
            ),

            autonomous_participation=(
                autonomous_participation
            )
        )

        if not post_voice_answer:

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=post_voice "
                "reason=no_safe_candidate"
            )

            return

        answer = (
            post_voice_answer
        )

        print(
            "[PIPELINE POST-VOICE READY] "
            f"user={username} "
            f"source={post_voice_source}"
        )

'''


bot = replace_between_once(
    bot,
    postvoice_start,
    postvoice_end,
    postvoice_replacement,
    "Post-Voice consolidation",
)


# =========================================================
# PRE-QUALITY CONSOLIDATION
# =========================================================

final_old_start = '''        # =================================================
        # B3B.1B FINAL NATURAL RESPONSE CHECK
'''

quality_marker = '''        # =================================================
        # B3E FINAL OUTPUT QUALITY v2
'''

prequality_replacement = r'''        # =================================================
        # B3I CONSOLIDATED PRE-QUALITY CRITICAL GATE
        #
        # Expression may have changed the surface.
        # Revalidate once, deterministically.
        #
        # This replaces the old Final Question,
        # Final Self and Final Garbled repair chain.
        # =================================================

        (
            pre_quality_answer,
            pre_quality_source
        ) = choose_pipeline_candidate(

            candidates=[
                (
                    "post_expression",
                    answer
                ),
                (
                    "reliability_baseline",
                    reliability_baseline_answer
                ),
                (
                    "writer_before_voice",
                    original_writer_answer
                ),
            ],

            decision=(
                decision
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

            user_text=(
                user_text
            ),

            recent_evilnae_messages=(
                final_channel_evilnae_messages
            ),

            username=(
                username
            ),

            stage=(
                "pre_quality"
            ),

            autonomous_participation=(
                autonomous_participation
            )
        )

        if not pre_quality_answer:

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=pre_quality "
                "reason=no_safe_candidate"
            )

            return

        answer = (
            pre_quality_answer
        )

        print(
            "[PIPELINE PRE-QUALITY READY] "
            f"user={username} "
            f"source={pre_quality_source}"
        )

'''


bot = replace_between_once(
    bot,
    final_old_start,
    quality_marker,
    prequality_replacement,
    "Final critical guards consolidation",
)


# =========================================================
# FINAL SEND GATE
# =========================================================

emote_marker = '''        # =================================================
        # 11.9 EVILNAE APPLICATION EMOTE LAYER
'''

final_send_gate = r'''        # =================================================
        # B3I FINAL SEND CANDIDATE GATE
        #
        # Output Quality can repair or reselect a draft.
        # Before emotes + Discord send, do exactly one
        # last deterministic critical candidate choice.
        # =================================================

        (
            final_send_answer,
            final_send_source
        ) = choose_pipeline_candidate(

            candidates=[
                (
                    "quality_final",
                    answer
                ),
                (
                    "reliability_baseline",
                    reliability_baseline_answer
                ),
                (
                    "writer_before_voice",
                    original_writer_answer
                ),
            ],

            decision=(
                decision
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

            user_text=(
                user_text
            ),

            recent_evilnae_messages=(
                final_channel_evilnae_messages
            ),

            username=(
                username
            ),

            stage=(
                "final_send"
            ),

            autonomous_participation=(
                autonomous_participation
            )
        )

        if not final_send_answer:

            print(
                "[SILENT FINAL] "
                f"user={username} "
                "stage=final_send "
                "reason=no_safe_candidate"
            )

            return

        answer = (
            final_send_answer
        )

        print(
            "[PIPELINE FINAL READY] "
            f"user={username} "
            f"source={final_send_source} "
            f"repairs={get_response_repair_count()}"
        )

'''


bot = insert_before_once(
    bot,
    emote_marker,
    final_send_gate,
    "Final send candidate gate",
)


# =========================================================
# STARTUP STATUS
# =========================================================

startup_marker = '''    print(
        "End-to-End Latency Telemetry: ACTIVE"
    )

'''

startup_block = r'''    print(
        f"Pipeline Consolidation v"
        f"{PIPELINE_CONSOLIDATION_VERSION}: ACTIVE"
    )

    print(
        "Legacy Mid-Pipeline API Repairs: DISABLED"
    )

    print(
        "Pre-Voice Critical Gate: CONSOLIDATED"
    )

    print(
        "Post-Voice Critical Gate: CONSOLIDATED"
    )

    print(
        "Pre-Quality Critical Gate: CONSOLIDATED"
    )

    print(
        "Final Send Critical Gate: CONSOLIDATED"
    )

'''


bot = insert_after_once(
    bot,
    startup_marker,
    startup_block,
    "Pipeline startup status",
)


# =========================================================
# VERIFY REMOVED LEGACY BLOCKS
# =========================================================

removed_markers = (
    "# B3B.1B NATURAL RESPONSE GUARD",
    "# B3B.1B POST-VOICE NATURAL RESPONSE GUARD",
    "# B3B.1B FINAL NATURAL RESPONSE CHECK",
)


for marker in removed_markers:
    if marker in bot:
        fail(
            "Legacy pipeline block still present: "
            f"{marker}"
        )


required_new_markers = (
    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',
    (
        f'PIPELINE_CONSOLIDATION_VERSION = '
        f'"{PIPELINE_VERSION}"'
    ),
    "def choose_pipeline_candidate(",
    "[PIPELINE SOFT DEFERRED]",
    "[PIPELINE PRE-VOICE READY]",
    "[PIPELINE POST-VOICE READY]",
    "[PIPELINE PRE-QUALITY READY]",
    "[PIPELINE FINAL READY]",
    "Legacy Mid-Pipeline API Repairs: DISABLED",
    "Final Send Critical Gate: CONSOLIDATED",
)


for marker in required_new_markers:
    if marker not in bot:
        fail(
            "Verification missing: "
            f"{marker}"
        )


syntax_check(
    bot,
    "bot.py"
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
    f"bot.py.before-B3I-{stamp}.bak"
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
    "bot.py.B3I.tmp"
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
# POST-WRITE VERIFY
# =========================================================

installed = BOT_PATH.read_text(
    encoding="utf-8"
)


for marker in required_new_markers:
    if marker not in installed:
        fail(
            "Post-write verification missing: "
            f"{marker}"
        )


print("")
print(
    "============================================"
)
print(
    "EVILNAE B3I PIPELINE CONSOLIDATION COMPLETE"
)
print(
    "============================================"
)
print(
    f"Bot Version: {TARGET_BOT_VERSION}"
)
print(
    f"Pipeline Consolidation: {PIPELINE_VERSION}"
)
print("")
print(
    "Installed:"
)
print(
    "  [✓] Central deterministic candidate chooser"
)
print(
    "  [✓] Pre-Voice API repair loop removed"
)
print(
    "  [✓] Post-Voice duplicate guards consolidated"
)
print(
    "  [✓] Question repair loop removed"
)
print(
    "  [✓] Naturalness repair loop removed"
)
print(
    "  [✓] Final Question/Self/Garbled loops consolidated"
)
print(
    "  [✓] Safe baseline remains recovery authority"
)
print(
    "  [✓] Output Quality remains soft-quality owner"
)
print(
    "  [✓] Expression remains surface-structure owner"
)
print(
    "  [✓] Final deterministic send gate"
)
print(
    "  [✓] Character/Lore/Preferences unchanged"
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
    "bot.py performance.py discord_actions.py "
    "routing_hardening.py response_quality.py "
    "participation.py evilnae_emotes.py "
    "conversation_understanding.py brain.py curiosity.py "
    "self_model.py agency.py conversation_world.py "
    "understanding.py perception.py natural_response.py "
    "naturalness.py coherence.py expression.py "
    "inner_state.py local_voice.py"
)
print(
    "python bot.py"
)
print(
    "============================================"
)
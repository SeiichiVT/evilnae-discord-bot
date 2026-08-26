from pathlib import Path
from datetime import datetime

import ast
import shutil


# =========================================================
# PATHS
# =========================================================

BOT = Path(
    "bot.py"
)

VOICE = Path(
    "local_voice.py"
)

PERFORMANCE = Path(
    "performance.py"
)


# =========================================================
# VERSION
# =========================================================

EXPECTED_BOT = (
    "2.15.0-discord-actions-b3g"
)

TARGET_BOT = (
    "2.16.0-performance-b3h"
)

EXPECTED_VOICE = (
    "1.2.6"
)

TARGET_VOICE = (
    "1.3.0"
)


# =========================================================
# HELPERS
# =========================================================

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

    result = (
        text.replace(
            old,
            new,
            1
        )
    )

    ok(
        label
    )

    return result


def insert_before(
    text,
    marker,
    block,
    label
):

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

    result = (
        text.replace(
            marker,
            block
            +
            marker,
            1
        )
    )

    ok(
        label
    )

    return result


def insert_after(
    text,
    marker,
    block,
    label
):

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

    result = (
        text.replace(
            marker,
            marker
            +
            block,
            1
        )
    )

    ok(
        label
    )

    return result


def syntax_check(
    text,
    filename
):

    try:

        ast.parse(
            text,
            filename=filename
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


# =========================================================
# START
# =========================================================

print(
    "[B3H PERFORMANCE PACK] starting..."
)


for path in (
    BOT,
    VOICE,
    PERFORMANCE,
):

    if not path.exists():

        fail(
            f"{path} missing"
        )


bot = BOT.read_text(
    encoding="utf-8"
)

voice = VOICE.read_text(
    encoding="utf-8"
)

performance = (
    PERFORMANCE.read_text(
        encoding="utf-8"
    )
)


# =========================================================
# PERFORMANCE MODULE
# =========================================================

if (
    'PERFORMANCE_VERSION = "1.0"'
    not in performance
):

    fail(
        "performance.py is not v1.0"
    )


syntax_check(
    performance,
    "performance.py"
)


# =========================================================
# VERSION CHECK
# =========================================================

if (
    f'BOT_VERSION = "{TARGET_BOT}"'
    in bot
):

    raise SystemExit(
        "B3H already installed."
    )


if (
    f'BOT_VERSION = "{EXPECTED_BOT}"'
    not in bot
):

    fail(
        "Unexpected bot version. "
        f"Expected {EXPECTED_BOT}."
    )


if (
    f'LOCAL_VOICE_VERSION = "{EXPECTED_VOICE}"'
    not in voice
):

    fail(
        "Unexpected Local Voice version. "
        f"Expected {EXPECTED_VOICE}."
    )


for marker in (

    "DISCORD_ACTIONS_VERSION",

    "ROUTING_HARDENING_VERSION",

    "OUTPUT_QUALITY_VERSION",

    "choose_reliability_fallback",

    "apply_text_emote_cooldown",
):

    if marker not in bot:

        fail(
            f"Previous feature missing: "
            f"{marker}"
        )


ok(
    "B3G base detected"
)


# =========================================================
# BOT PERFORMANCE IMPORT
# =========================================================

bot = insert_before(

    bot,

    "from discord_actions import (\n",

    '''from performance import (
    PERFORMANCE_VERSION,
    RESPONSE_REPAIR_BUDGET,
    reset_response_repair_budget,
    claim_response_repair_slot,
    format_repair_budget_debug,
    start_response_timer,
    elapsed_response_time,
)

''',

    "Performance import"
)


# =========================================================
# LOCAL VOICE PERFORMANCE IMPORT
# =========================================================

voice = insert_before(

    voice,

    "from dotenv import load_dotenv\n",

    '''from performance import (
    PERFORMANCE_VERSION,
    should_fast_path_local_voice,
)

''',

    "Local Voice Performance import"
)


# =========================================================
# VERSIONS
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT}"',

    f'BOT_VERSION = "{TARGET_BOT}"',

    "Bot version"
)


voice = replace_once(

    voice,

    f'LOCAL_VOICE_VERSION = "{EXPECTED_VOICE}"',

    f'LOCAL_VOICE_VERSION = "{TARGET_VOICE}"',

    "Local Voice version"
)


# =========================================================
# RESPONSE RETRIES
#
# Background Memory / Reflection keeps global 3.
#
# User-facing responses use maximum 2.
# =========================================================

bot = replace_once(

    bot,

    '''OPENAI_MAX_RETRIES = 3

RETRY_BASE_DELAY = 1.5
''',

    '''OPENAI_MAX_RETRIES = 3

OPENAI_RESPONSE_MAX_RETRIES = 2

RETRY_BASE_DELAY = 1.5
''',

    "Response retry config"
)


bot = replace_once(

    bot,

    '''    last_error = None

    for attempt in range(
        1,
        OPENAI_MAX_RETRIES + 1
    ):
''',

    '''    last_error = None

    if (
        request_type
        in {
            "memory",
            "reflection",
        }
    ):

        max_attempts = (
            OPENAI_MAX_RETRIES
        )

    else:

        max_attempts = min(
            OPENAI_RESPONSE_MAX_RETRIES,
            OPENAI_MAX_RETRIES
        )

    for attempt in range(
        1,
        max_attempts + 1
    ):
''',

    "Response retry selection"
)


bot = replace_once(

    bot,

    '''        if (
            attempt
            < OPENAI_MAX_RETRIES
        ):
''',

    '''        if (
            attempt
            < max_attempts
        ):
''',

    "Retry loop limit"
)


bot = replace_once(

    bot,

    '''    raise RuntimeError(
        f"OpenAI request failed after "
        f"{OPENAI_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )
''',

    '''    raise RuntimeError(
        f"OpenAI request failed after "
        f"{max_attempts} attempts. "
        f"Last error: {last_error}"
    )
''',

    "Retry failure diagnostic"
)


# =========================================================
# WRITER VALIDATION REPAIRS
#
# Old:
# Writer may repair twice.
#
# New:
# one validation repair.
#
# B3D Safe Baseline handles failure.
# =========================================================

bot = replace_once(

    bot,

    "WRITER_MAX_REPAIRS = 2",

    "WRITER_MAX_REPAIRS = 1",

    "Writer validation repair limit"
)


# =========================================================
# RESPONSE-LENGTH TOKEN LIMITS
#
# Still plenty for Discord replies,
# but less room for accidental essays.
# =========================================================

bot = replace_once(

    bot,

    '''    limits = {
        "tiny": 60,
        "short": 120,
        "medium": 220,
        "long": 400,
    }

    base_limit = (
        limits.get(
            response_length,
            150
        )
    )
''',

    '''    limits = {
        "tiny": 50,
        "short": 90,
        "medium": 160,
        "long": 280,
    }

    base_limit = (
        limits.get(
            response_length,
            110
        )
    )
''',

    "Writer token limits"
)


# =========================================================
# RESET BUDGET + START TOTAL TIMER
# =========================================================

bot = replace_once(

    bot,

    """    channel_id = (
        perception.channel_id
    )

    user_id = (
        perception.user_id
    )

    username = (
        perception.username
    )

    # =====================================================
    # CONTEXT REVISION
""",

    """    channel_id = (
        perception.channel_id
    )

    user_id = (
        perception.user_id
    )

    username = (
        perception.username
    )

    # =====================================================
    # B3H RESPONSE PERFORMANCE STATE
    # =====================================================

    reset_response_repair_budget()

    response_pipeline_started_at = (
        start_response_timer()
    )

    # =====================================================
    # CONTEXT REVISION
""",

    "Response performance state"
)


# =========================================================
# GLOBAL WRITER REPAIR BUDGET
#
# Applies to:
#
# - initial Writer validation
# - Self repair
# - Knowledge repair
# - Natural Response repair
# - Question repair
# - Naturalness repair
# - Expression repair
# - Quality repair
#
# Maximum API repair calls per response: 2.
# =========================================================

repair_function_marker = '''async def repair_writer_answer(
    *,
    original_answer,
    violation_reasons,
    writer_context,
    current_mood,
    username,
    token_limit,
    autonomous_participation=False
):

'''


repair_budget_block = '''    repair_budget_decision = (
        claim_response_repair_slot(

            label=(
                "+"
                .join(
                    str(reason)

                    for reason
                    in (
                        violation_reasons
                        or []
                    )[:3]
                )
            )
        )
    )

    print(
        format_repair_budget_debug(
            repair_budget_decision
        )
    )

    if not (
        repair_budget_decision
        .allowed
    ):

        print(
            "[WRITER REPAIR BUDGET SKIP] "
            f"user={username} "
            f"used="
            f"{repair_budget_decision.used_after}/"
            f"{repair_budget_decision.limit}"
        )

        return ""

'''


bot = insert_after(

    bot,

    repair_function_marker,

    repair_budget_block,

    "Global Writer repair budget"
)


# =========================================================
# STARTUP
# =========================================================

bot = insert_after(

    bot,

    '''    print(
        "Targeted Quality Repair: ACTIVE"
    )

''',

    '''    print(
        f"Performance v{PERFORMANCE_VERSION}: ACTIVE"
    )

    print(
        f"Response Repair API Budget: "
        f"{RESPONSE_REPAIR_BUDGET}"
    )

    print(
        f"Writer Validation Repairs: "
        f"{WRITER_MAX_REPAIRS}"
    )

    print(
        f"Response API Retries: "
        f"{OPENAI_RESPONSE_MAX_RETRIES}"
    )

    print(
        "Local Voice Clean-Short Fast Path: ACTIVE"
    )

    print(
        "End-to-End Latency Telemetry: ACTIVE"
    )

''',

    "Performance startup status"
)


# =========================================================
# END-TO-END LATENCY
#
# Sent replies get one simple total duration.
#
# Individual OpenAI requests are already timed
# by safe_openai_request.
#
# Local Voice already reports its own duration.
# =========================================================

send_marker = '''            register_channel_message(
                is_bot=True
            )

        # =================================================
        # 13. DIRECT USER CONTEXT UPDATE
'''


send_replacement = '''            register_channel_message(
                is_bot=True
            )

            response_total_duration = (
                elapsed_response_time(
                    response_pipeline_started_at
                )
            )

            print(
                "[RESPONSE LATENCY] "
                f"user={username} "
                f"mode={voice_conversation_mode} "
                f"total={response_total_duration:.2f}s "
                f"repairs="
                f"{getattr("
                f"__import__('performance'), "
                f"'get_response_repair_count', "
                f"lambda: -1"
                f")()}"
            )

        # =================================================
        # 13. DIRECT USER CONTEXT UPDATE
'''


# The dynamic import above is intentionally NOT used.
# Replace it with direct get_response_repair_count import
# before writing.
send_replacement = (
    send_replacement
    .replace(
        '''f"repairs="
                f"{getattr("
                f"__import__('performance'), "
                f"'get_response_repair_count', "
                f"lambda: -1"
                f")()}"''',
        '''f"repairs="
                f"{get_response_repair_count()}"'''
    )
)


# Add the missing direct import.
bot = replace_once(

    bot,

    '''    reset_response_repair_budget,
    claim_response_repair_slot,
    format_repair_budget_debug,
''',

    '''    reset_response_repair_budget,
    get_response_repair_count,
    claim_response_repair_slot,
    format_repair_budget_debug,
''',

    "Repair count import"
)


bot = replace_once(

    bot,

    send_marker,

    send_replacement,

    "End-to-end response latency"
)


# =========================================================
# LOCAL VOICE QUEUE
#
# Waiting 5 seconds for Qwen while another
# reply is using the GPU is too expensive.
#
# Safe Writer baseline already exists.
# =========================================================

voice = replace_once(

    voice,

    '''LOCAL_VOICE_QUEUE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_QUEUE_TIMEOUT",
        "5"
    )
)
''',

    '''LOCAL_VOICE_QUEUE_TIMEOUT = float(
    os.getenv(
        "LOCAL_VOICE_QUEUE_TIMEOUT",
        "1.5"
    )
)
''',

    "Local Voice queue timeout"
)


# =========================================================
# LOCAL VOICE OUTPUT BUDGETS
# =========================================================

voice = replace_once(

    voice,

    '''LOCAL_VOICE_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_NUM_PREDICT",
        "240"
    )
)
''',

    '''LOCAL_VOICE_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_NUM_PREDICT",
        "200"
    )
)
''',

    "Local Voice prediction budget"
)


voice = replace_once(

    voice,

    '''LOCAL_VOICE_REPAIR_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_REPAIR_NUM_PREDICT",
        "180"
    )
)
''',

    '''LOCAL_VOICE_REPAIR_NUM_PREDICT = int(
    os.getenv(
        "LOCAL_VOICE_REPAIR_NUM_PREDICT",
        "120"
    )
)
''',

    "Local Voice repair prediction budget"
)


voice = replace_once(

    voice,

    '''LOCAL_VOICE_REPAIR_MAX_ATTEMPTS = int(
    os.getenv(
        "LOCAL_VOICE_REPAIR_MAX_ATTEMPTS",
        "2"
    )
)
''',

    '''LOCAL_VOICE_REPAIR_MAX_ATTEMPTS = int(
    os.getenv(
        "LOCAL_VOICE_REPAIR_MAX_ATTEMPTS",
        "1"
    )
)
''',

    "Local Voice repair attempts"
)


# =========================================================
# LOCAL VOICE CLEAN-SHORT FAST PATH
#
# Happens AFTER deterministic Coherence analysis.
#
# So replies with repetition / assistant structure /
# concept cooldown etc. STILL go through Qwen.
# =========================================================

voice_fast_path_marker = '''    # =====================================================
    # QUEUE
    # =====================================================
'''


voice_fast_path_block = '''    # =====================================================
    # B3H CLEAN-SHORT FAST PATH
    #
    # No local model call if the Writer already produced
    # one short, clean, deterministic-safe thought.
    # =====================================================

    if should_fast_path_local_voice(

        draft,

        violation_score=(
            draft_violation_score
        ),

        deterministic_pressure=(
            deterministic_pressure
        )
    ):

        print(
            "[LOCAL VOICE FAST PATH] "
            f"v={PERFORMANCE_VERSION} "
            f"words={len(extract_words(draft))} "
            "reason=clean_short_writer_draft"
        )

        return fallback(

            "fast_path_clean_short",

            duration=0.0,

            deterministic_violations=(
                draft_violations
            ),

            forced_rewrite=False,

            pre_score=(
                draft_violation_score
            )
        )

'''


voice = insert_before(

    voice,

    voice_fast_path_marker,

    voice_fast_path_block,

    "Local Voice clean-short fast path"
)


# =========================================================
# SYNTAX BEFORE WRITE
# =========================================================

syntax_check(
    bot,
    "bot.py"
)

syntax_check(
    voice,
    "local_voice.py"
)


# =========================================================
# BACKUPS
# =========================================================

stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)


bot_backup = Path(
    f"bot.py.before-B3H-{stamp}.bak"
)

voice_backup = Path(
    f"local_voice.py.before-B3H-{stamp}.bak"
)


shutil.copy2(
    BOT,
    bot_backup
)

shutil.copy2(
    VOICE,
    voice_backup
)


print(
    f"[BACKUP] {bot_backup}"
)

print(
    f"[BACKUP] {voice_backup}"
)


# =========================================================
# WRITE
# =========================================================

bot_tmp = Path(
    "bot.py.B3H.tmp"
)

voice_tmp = Path(
    "local_voice.py.B3H.tmp"
)


bot_tmp.write_text(
    bot,
    encoding="utf-8"
)

voice_tmp.write_text(
    voice,
    encoding="utf-8"
)


bot_tmp.replace(
    BOT
)

voice_tmp.replace(
    VOICE
)


ok(
    "bot.py written"
)

ok(
    "local_voice.py written"
)


# =========================================================
# VERIFY
# =========================================================

installed_bot = (
    BOT.read_text(
        encoding="utf-8"
    )
)

installed_voice = (
    VOICE.read_text(
        encoding="utf-8"
    )
)


required_bot = (

    f'BOT_VERSION = "{TARGET_BOT}"',

    "PERFORMANCE_VERSION",

    "RESPONSE_REPAIR_BUDGET",

    "OPENAI_RESPONSE_MAX_RETRIES = 2",

    "WRITER_MAX_REPAIRS = 1",

    "claim_response_repair_slot",

    "[WRITER REPAIR BUDGET SKIP]",

    "[RESPONSE LATENCY]",

    "Performance v{PERFORMANCE_VERSION}: ACTIVE",

    "Local Voice Clean-Short Fast Path: ACTIVE",

    "End-to-End Latency Telemetry: ACTIVE",
)


for marker in required_bot:

    if marker not in installed_bot:

        fail(
            "bot.py verification missing: "
            f"{marker}"
        )


required_voice = (

    f'LOCAL_VOICE_VERSION = "{TARGET_VOICE}"',

    "should_fast_path_local_voice",

    "[LOCAL VOICE FAST PATH]",

    '"1.5"',

    '"200"',

    '"120"',

    '"1"',
)


for marker in required_voice:

    if marker not in installed_voice:

        fail(
            "local_voice.py verification missing: "
            f"{marker}"
        )


print("")
print(
    "============================================"
)

print(
    "EVILNAE B3H PERFORMANCE COMPLETE"
)

print(
    "============================================"
)

print(
    f"Bot Version: {TARGET_BOT}"
)

print(
    f"Local Voice: {TARGET_VOICE}"
)

print(
    "Performance: 1.0"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] Global repair API budget = 2"
)

print(
    "  [✓] Writer validation repair max = 1"
)

print(
    "  [✓] Response API retries max = 2"
)

print(
    "  [✓] Background memory retries unchanged"
)

print(
    "  [✓] Writer output-token budgets reduced"
)

print(
    "  [✓] Local Voice queue 5s -> 1.5s"
)

print(
    "  [✓] Local Voice predict 240 -> 200"
)

print(
    "  [✓] Local Voice repair predict 180 -> 120"
)

print(
    "  [✓] Local Voice repair attempts 2 -> 1"
)

print(
    "  [✓] Clean short Writer fast path"
)

print(
    "  [✓] End-to-end latency telemetry"
)

print("")

print(
    "Character / Lore / Preferences: UNCHANGED"
)

print("")

print(
    "NEXT:"
)

print(
    "python performance.py"
)

print(
    "python -m py_compile "
    "bot.py performance.py discord_actions.py "
    "routing_hardening.py response_quality.py "
    "participation.py evilnae_emotes.py "
    "conversation_understanding.py brain.py "
    "curiosity.py self_model.py agency.py "
    "conversation_world.py understanding.py "
    "perception.py natural_response.py naturalness.py "
    "coherence.py expression.py inner_state.py "
    "local_voice.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
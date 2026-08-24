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

CURIOSITY_PATH = Path(
    "curiosity.py"
)


EXPECTED_BOT_VERSION = (
    "2.11.5-curiosity-b3b1a"
)

TARGET_BOT_VERSION = (
    "2.11.6-curiosity-stable-b3b1a1"
)


EXPECTED_CURIOSITY_VERSION = (
    'CURIOSITY_VERSION = "1.1"'
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
            f"{label}: expected 1 match, "
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


# =========================================================
# START
# =========================================================

print(
    "[B3B.1A.1 INSTALLER] starting..."
)


if not BOT_PATH.exists():

    fail(
        "bot.py missing"
    )


if not CURIOSITY_PATH.exists():

    fail(
        "curiosity.py missing"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


curiosity = (
    CURIOSITY_PATH.read_text(
        encoding="utf-8"
    )
)


# =========================================================
# VERSION CHECKS
# =========================================================

if (
    f'BOT_VERSION = "{TARGET_BOT_VERSION}"'
    in bot
):

    print(
        "B3B.1A.1 already installed."
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


if (
    EXPECTED_CURIOSITY_VERSION
    not in curiosity
):

    fail(
        "curiosity.py is not v1.1. "
        "Replace curiosity.py first."
    )


if (
    "question_output_violation_reasons"
    not in curiosity
):

    fail(
        "curiosity.py does not contain "
        "the v1.1 output guard."
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


bot_backup = Path(

    f"bot.py.before-B3B1A1-"
    f"{stamp}.bak"
)


shutil.copy2(
    BOT_PATH,
    bot_backup
)


print(
    f"[BACKUP] {bot_backup}"
)


# =========================================================
# 1. IMPORT OUTPUT GUARD
# =========================================================

old = '''from curiosity import (
    CURIOSITY_VERSION,
    apply_curiosity_policy,
    format_curiosity_for_writer,
    format_curiosity_debug,
)
'''


new = '''from curiosity import (
    CURIOSITY_VERSION,
    apply_curiosity_policy,
    format_curiosity_for_writer,
    format_curiosity_debug,
    question_output_violation_reasons,
)
'''


bot = replace_once(
    bot,
    old,
    new,
    "Curiosity output guard import"
)


# =========================================================
# 2. BOT VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"',

    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',

    "Bot version"
)


# =========================================================
# 3. STARTUP STATUS
# =========================================================

old = '''    print(
        "Anti-Interview Question Pressure: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


new = '''    print(
        "Anti-Interview Question Pressure: ACTIVE"
    )

    print(
        "Post-Voice Question Guard: ACTIVE"
    )

    print(
        "Single Question Shape Guard: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


bot = replace_once(
    bot,
    old,
    new,
    "Question Guard startup status"
)


# =========================================================
# 4. PRE-VOICE QUESTION SHAPE GUARD
#
# Writer muss bereits sauber sein,
# bevor Qwen startet.
# =========================================================

old = '''        original_writer_answer = (
            answer
        )

        try:
'''


new = '''        # =====================================================
        # B3B.1A.1 PRE-VOICE QUESTION SHAPE GUARD
        #
        # Curiosity entscheidet:
        #
        # - keine Frage
        # ODER
        # - maximal eine Frage
        #
        # Writer darf diese Entscheidung nicht umgehen.
        # =====================================================

        pre_voice_question_violations = (
            question_output_violation_reasons(
                answer,
                curiosity_result
            )
        )

        if pre_voice_question_violations:

            print(
                "[QUESTION SHAPE VIOLATION] "
                f"user={username} "
                f"violations="
                f"{pre_voice_question_violations} "
                f"answer={answer!r}"
            )

            question_repair_context = (
                writer_context
                +
                "\\n\\n"
                +
                format_curiosity_for_writer(
                    curiosity_result
                )
            )

            question_repair = (
                await repair_writer_answer(

                    original_answer=(
                        answer
                    ),

                    violation_reasons=(
                        pre_voice_question_violations
                    ),

                    writer_context=(
                        question_repair_context
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

            if not question_repair:

                print(
                    "[QUESTION SHAPE ABORT] "
                    f"user={username} "
                    "reason=repair_failed"
                )

                return

            question_repair = (
                clean_generated_answer(
                    question_repair
                )
            )

            question_repair = (
                enforce_permanent_expression_bans(
                    question_repair
                )
            )

            question_repair_hard = (
                get_writer_violation_reasons(

                    answer=(
                        question_repair
                    ),

                    decision=(
                        decision
                    ),

                    autonomous_participation=(
                        autonomous_participation
                    )
                )
            )

            question_repair_violations = (
                question_output_violation_reasons(
                    question_repair,
                    curiosity_result
                )
            )

            if (
                question_repair_hard
                or
                question_repair_violations
            ):

                print(
                    "[QUESTION SHAPE ABORT] "
                    f"user={username} "
                    f"hard="
                    f"{question_repair_hard} "
                    f"question="
                    f"{question_repair_violations}"
                )

                return

            answer = (
                question_repair
            )

            print(
                "[QUESTION SHAPE REPAIR SUCCESS] "
                f"user={username}"
            )

        original_writer_answer = (
            answer
        )

        try:
'''


bot = replace_once(
    bot,
    old,
    new,
    "Pre-Voice Question Shape Guard"
)


# =========================================================
# 5. POST-QWEN QUESTION GUARD
#
# Qwen darf niemals wieder:
#
# Curiosity False
# → "und bei dir?"
#
# machen.
# =========================================================

old = '''        # =====================================================
        # POST-VOICE SELF KNOWLEDGE GUARD
'''


new = '''        # =====================================================
        # B3B.1A.1 POST-VOICE QUESTION GUARD
        # =====================================================

        post_voice_question_violations = (
            question_output_violation_reasons(
                answer,
                curiosity_result
            )
        )

        if post_voice_question_violations:

            print(
                "[LOCAL VOICE QUESTION REVERT] "
                f"user={username} "
                f"violations="
                f"{post_voice_question_violations} "
                f"answer={answer!r}"
            )

            # Original Writer Draft wurde bereits
            # vor Qwen validiert.
            #
            # Deshalb zuerst sauber zurückfallen.
            answer = (
                original_writer_answer
            )

            reverted_question_violations = (
                question_output_violation_reasons(
                    answer,
                    curiosity_result
                )
            )

            if reverted_question_violations:

                print(
                    "[LOCAL VOICE QUESTION ABORT] "
                    f"user={username} "
                    f"violations="
                    f"{reverted_question_violations}"
                )

                return

            print(
                "[LOCAL VOICE QUESTION REVERT SUCCESS] "
                f"user={username}"
            )

        # =====================================================
        # POST-VOICE SELF KNOWLEDGE GUARD
'''


bot = replace_once(
    bot,
    old,
    new,
    "Post-Voice Question Guard"
)


# =========================================================
# 6. FINAL QUESTION GUARD
#
# Naturalness / Expression / spätere Repairs
# dürfen ebenfalls keine Frage zurückbringen.
# =========================================================

old = '''        # =================================================
        # FINAL SELF KNOWLEDGE GUARD
'''


new = '''        # =================================================
        # B3B.1A.1 FINAL QUESTION GUARD
        # =================================================

        final_question_violations = (
            question_output_violation_reasons(
                answer,
                curiosity_result
            )
        )

        if final_question_violations:

            print(
                "[QUESTION FINAL ABORT] "
                f"user={username} "
                f"violations="
                f"{final_question_violations} "
                f"answer={answer!r}"
            )

            return

        # =================================================
        # FINAL SELF KNOWLEDGE GUARD
'''


bot = replace_once(
    bot,
    old,
    new,
    "Final Question Guard"
)


# =========================================================
# SYNTAX CHECK
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
        "Patched bot.py syntax error: "
        f"line={error.lineno} "
        f"{error.msg}. "
        "Nothing overwritten."
    )


ok(
    "bot.py syntax check"
)


# =========================================================
# WRITE
# =========================================================

tmp = Path(
    "bot.py.B3B1A1.tmp"
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

    (
        f'BOT_VERSION = '
        f'"{TARGET_BOT_VERSION}"'
    ),

    "question_output_violation_reasons",

    "[QUESTION SHAPE VIOLATION]",

    "[LOCAL VOICE QUESTION REVERT]",

    "[QUESTION FINAL ABORT]",

    "Post-Voice Question Guard: ACTIVE",

    "Single Question Shape Guard: ACTIVE",
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


# =========================================================
# DONE
# =========================================================

print("")
print(
    "============================================"
)

print(
    "EVILNAE B3B.1A.1 INSTALL COMPLETE"
)

print(
    "============================================"
)

print(
    f"Bot Version: "
    f"{TARGET_BOT_VERSION}"
)

print(
    "Curiosity Version: 1.1"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] Smoothed Question Pressure"
)

print(
    "  [✓] One prior question no longer blocks curiosity"
)

print(
    "  [✓] Two-question interview pressure"
)

print(
    "  [✓] Pre-Voice Question Shape Guard"
)

print(
    "  [✓] Post-Qwen Question Guard"
)

print(
    "  [✓] Final Question Guard"
)

print(
    "  [✓] Maximum one question per reply"
)

print(
    "  [✓] Qwen cannot reintroduce blocked questions"
)

print("")

print(
    f"Backup:"
)

print(
    f"  {bot_backup}"
)

print("")

print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py brain.py curiosity.py "
    "self_model.py agency.py "
    "conversation_world.py "
    "understanding.py naturalness.py "
    "coherence.py expression.py "
    "perception.py inner_state.py "
    "local_voice.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
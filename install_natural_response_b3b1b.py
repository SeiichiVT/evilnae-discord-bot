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

NATURAL_RESPONSE_PATH = Path(
    "natural_response.py"
)


EXPECTED_BOT_VERSION = (
    "2.11.6-curiosity-stable-b3b1a1"
)

TARGET_BOT_VERSION = (
    "2.11.7-natural-response-b3b1b"
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


# =========================================================
# START
# =========================================================

print(
    "[B3B.1B INSTALLER] starting..."
)


if not BOT_PATH.exists():

    fail(
        "bot.py missing"
    )


if not NATURAL_RESPONSE_PATH.exists():

    fail(
        "natural_response.py missing"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


natural_response = (
    NATURAL_RESPONSE_PATH.read_text(
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
        "B3B.1B already installed."
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
    'NATURAL_RESPONSE_VERSION = "1.0"'
    not in natural_response
):

    fail(
        "natural_response.py is not v1.0"
    )


if (
    "analyze_natural_response"
    not in natural_response
):

    fail(
        "natural_response.py incomplete"
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

    f"bot.py.before-B3B1B-"
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
# 1. IMPORTS
# =========================================================

old = '''from naturalness import (
    NATURALNESS_VERSION,
    analyze_naturalness,
    format_naturalness_for_writer,
    format_naturalness_debug,
)
'''


new = '''from naturalness import (
    NATURALNESS_VERSION,
    analyze_naturalness,
    format_naturalness_for_writer,
    format_naturalness_debug,
)

from natural_response import (
    NATURAL_RESPONSE_VERSION,
    analyze_natural_response,
    format_natural_response_for_writer,
    better_than as natural_response_better_than,
    format_natural_response_debug,
)
'''


bot = replace_once(

    bot,
    old,
    new,

    "Natural Response imports"
)


# =========================================================
# 2. VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = '
    f'"{EXPECTED_BOT_VERSION}"',

    f'BOT_VERSION = '
    f'"{TARGET_BOT_VERSION}"',

    "Bot version"
)


# =========================================================
# 3. STARTUP STATUS
# =========================================================

old = '''    print(
        "Single Question Shape Guard: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


new = '''    print(
        "Single Question Shape Guard: ACTIVE"
    )

    print(
        f"Natural Response Guard v"
        f"{NATURAL_RESPONSE_VERSION}: ACTIVE"
    )

    print(
        "React-Don't-Restate Guard: ACTIVE"
    )

    print(
        "Assistant Coaching Guard: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


bot = replace_once(

    bot,
    old,
    new,

    "Natural Response startup status"
)


# =========================================================
# 4. PRE-VOICE NATURAL RESPONSE GUARD
# =========================================================

marker = '''        # =====================================================
        # B3B.1A.1 PRE-VOICE QUESTION SHAPE GUARD
'''


block = '''        # =====================================================
        # B3B.1B NATURAL RESPONSE GUARD
        #
        # Ziel:
        #
        # - reagieren statt User paraphrasieren
        # - kein Support-/Coach-Wrapper
        # - kein künstlicher Empathie-Füllsatz
        # - Unknown nicht wie Datenbankfehler formulieren
        # - lieber kurz aufhören als Antwort abrunden
        #
        # Kein zusätzlicher API-Call,
        # wenn die Antwort sauber ist.
        # =====================================================

        natural_response_analysis = (
            analyze_natural_response(

                answer,

                user_text=(
                    user_text
                ),

                curiosity_allowed=(
                    curiosity_result.allowed
                ),

                self_unknown=(
                    bool(
                        getattr(
                            self_evidence,
                            "strict_unknown",
                            False
                        )
                    )
                )
            )
        )

        print(
            format_natural_response_debug(
                natural_response_analysis
            )
        )

        if natural_response_analysis.rewrite_required:

            natural_response_context = (
                writer_context
                +
                "\\n\\n"
                +
                format_natural_response_for_writer(

                    natural_response_analysis,

                    user_text=(
                        user_text
                    ),

                    curiosity_allowed=(
                        curiosity_result.allowed
                    ),

                    question_goal=(
                        curiosity_result.question_goal
                    ),

                    self_unknown=(
                        bool(
                            getattr(
                                self_evidence,
                                "strict_unknown",
                                False
                            )
                        )
                    )
                )
            )

            natural_response_repair = (
                await repair_writer_answer(

                    original_answer=(
                        answer
                    ),

                    violation_reasons=(
                        natural_response_analysis.matches
                    ),

                    writer_context=(
                        natural_response_context
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

            if natural_response_repair:

                natural_response_repair = (
                    clean_generated_answer(
                        natural_response_repair
                    )
                )

                natural_response_repair = (
                    enforce_permanent_expression_bans(
                        natural_response_repair
                    )
                )

                repair_hard_violations = (
                    get_writer_violation_reasons(

                        answer=(
                            natural_response_repair
                        ),

                        decision=(
                            decision
                        ),

                        autonomous_participation=(
                            autonomous_participation
                        )
                    )
                )

                repair_question_violations = (
                    question_output_violation_reasons(
                        natural_response_repair,
                        curiosity_result
                    )
                )

                repair_self_violations = (
                    self_knowledge_violation_reasons(
                        natural_response_repair,
                        self_evidence
                    )
                )

                repair_is_better = (
                    natural_response_better_than(

                        natural_response_repair,
                        answer,

                        user_text=(
                            user_text
                        ),

                        curiosity_allowed=(
                            curiosity_result.allowed
                        ),

                        self_unknown=(
                            bool(
                                getattr(
                                    self_evidence,
                                    "strict_unknown",
                                    False
                                )
                            )
                        )
                    )
                )

                if (
                    not repair_hard_violations
                    and
                    not repair_question_violations
                    and
                    not repair_self_violations
                    and
                    repair_is_better
                ):

                    print(
                        "[NATURAL RESPONSE REPAIR SUCCESS] "
                        f"user={username} "
                        f"before_score="
                        f"{natural_response_analysis.score}"
                    )

                    answer = (
                        natural_response_repair
                    )

                else:

                    print(
                        "[NATURAL RESPONSE REPAIR REJECTED] "
                        f"user={username} "
                        f"hard={repair_hard_violations} "
                        f"question="
                        f"{repair_question_violations} "
                        f"self={repair_self_violations} "
                        f"better={repair_is_better}"
                    )

            else:

                print(
                    "[NATURAL RESPONSE REPAIR FAILED] "
                    f"user={username}"
                )

''' + marker


bot = replace_once(

    bot,
    marker,
    block,

    "Pre-Voice Natural Response Guard"
)


# =========================================================
# 5. POST-QWEN NATURAL RESPONSE GUARD
# =========================================================

marker = '''        # =====================================================
        # B3B.1A.1 POST-VOICE QUESTION GUARD
'''


block = '''        # =====================================================
        # B3B.1B POST-VOICE NATURAL RESPONSE GUARD
        #
        # Qwen darf eine vorher saubere
        # Writer-Antwort nicht wieder in
        # Assistant-/Coach-Sprache verwandeln.
        # =====================================================

        post_voice_natural_analysis = (
            analyze_natural_response(

                answer,

                user_text=(
                    user_text
                ),

                curiosity_allowed=(
                    curiosity_result.allowed
                ),

                self_unknown=(
                    bool(
                        getattr(
                            self_evidence,
                            "strict_unknown",
                            False
                        )
                    )
                )
            )
        )

        if post_voice_natural_analysis.rewrite_required:

            original_natural_analysis = (
                analyze_natural_response(

                    original_writer_answer,

                    user_text=(
                        user_text
                    ),

                    curiosity_allowed=(
                        curiosity_result.allowed
                    ),

                    self_unknown=(
                        bool(
                            getattr(
                                self_evidence,
                                "strict_unknown",
                                False
                            )
                        )
                    )
                )
            )

            if (
                original_natural_analysis.score
                <
                post_voice_natural_analysis.score
            ):

                print(
                    "[LOCAL VOICE NATURAL REVERT] "
                    f"user={username} "
                    f"qwen_score="
                    f"{post_voice_natural_analysis.score} "
                    f"writer_score="
                    f"{original_natural_analysis.score} "
                    f"matches="
                    f"{post_voice_natural_analysis.matches}"
                )

                answer = (
                    original_writer_answer
                )

''' + marker


bot = replace_once(

    bot,
    marker,
    block,

    "Post-Voice Natural Response Guard"
)


# =========================================================
# 6. FINAL NATURAL RESPONSE CHECK
#
# Für den Community-Test:
#
# Style-Probleme NICHT hard-aborten.
#
# Wir wollen heute Abend echte Gespräche
# + saubere Fehlerlogs sammeln.
# =========================================================

marker = '''        # =================================================
        # B3B.1A.1 FINAL QUESTION GUARD
'''


block = '''        # =================================================
        # B3B.1B FINAL NATURAL RESPONSE CHECK
        #
        # Für den Community-Test bewusst KEIN Hard Abort.
        #
        # Wenn nach allen Layern noch ein Bot-Muster
        # übrig ist, sehen wir es im Log und können
        # es gezielt auswerten.
        # =================================================

        final_natural_response_analysis = (
            analyze_natural_response(

                answer,

                user_text=(
                    user_text
                ),

                curiosity_allowed=(
                    curiosity_result.allowed
                ),

                self_unknown=(
                    bool(
                        getattr(
                            self_evidence,
                            "strict_unknown",
                            False
                        )
                    )
                )
            )
        )

        if final_natural_response_analysis.rewrite_required:

            print(
                "[NATURAL RESPONSE FINAL WARNING] "
                f"user={username} "
                f"score="
                f"{final_natural_response_analysis.score} "
                f"matches="
                f"{final_natural_response_analysis.matches} "
                f"answer={answer!r}"
            )

''' + marker


bot = replace_once(

    bot,
    marker,
    block,

    "Final Natural Response Check"
)


# =========================================================
# SYNTAX
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
    "bot.py.B3B1B.tmp"
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

    "NATURAL_RESPONSE_VERSION",

    "analyze_natural_response(",

    "[NATURAL RESPONSE REPAIR SUCCESS]",

    "[LOCAL VOICE NATURAL REVERT]",

    "[NATURAL RESPONSE FINAL WARNING]",

    "Natural Response Guard v",

    "React-Don't-Restate Guard: ACTIVE",

    "Assistant Coaching Guard: ACTIVE",
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
    "EVILNAE B3B.1B INSTALL COMPLETE"
)

print(
    "============================================"
)

print(
    f"Bot Version: "
    f"{TARGET_BOT_VERSION}"
)

print(
    "Natural Response Version: 1.0"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] React, don't restate"
)

print(
    "  [✓] Assistant empathy detection"
)

print(
    "  [✓] Motivational-coach detection"
)

print(
    "  [✓] Casual Self-Unknown wording guidance"
)

print(
    "  [✓] Question + filler detection"
)

print(
    "  [✓] Low-value acknowledgement brevity"
)

print(
    "  [✓] Pre-Voice focused repair"
)

print(
    "  [✓] Qwen regression revert"
)

print(
    "  [✓] Final warning logs for community test"
)

print(
    "  [✓] No hard final abort for style-only issues"
)

print("")

print(
    f"Backup: "
    f"{bot_backup}"
)

print("")

print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py natural_response.py "
    "brain.py curiosity.py "
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
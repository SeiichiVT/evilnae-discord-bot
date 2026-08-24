from pathlib import Path
from datetime import datetime
import ast
import shutil
import sys
import textwrap


# =========================================================
# CONFIG
# =========================================================

BOT_PATH = Path(
    "bot.py"
)

EXPECTED_VERSION = (
    "2.11.0-coherence-a"
)

TARGET_VERSION = (
    "2.11.1-understanding-b1"
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


# =========================================================
# BASIC REPLACE
# =========================================================

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
            f"{label}: expected once, "
            f"found {count}"
        )

    text = text.replace(
        old,
        new,
        1
    )

    ok(
        label
    )

    return text


# =========================================================
# INSERT BEFORE MARKER
# =========================================================

def insert_before_once(
    text,
    marker,
    insertion,
    label
):

    if insertion.strip() in text:

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
            f"{label}: marker expected once, "
            f"found {count}"
        )

    index = (
        text.find(
            marker
        )
    )

    line_start = (
        text.rfind(
            "\n",
            0,
            index
        )
        + 1
    )

    marker_line = (
        text[
            line_start:index
        ]
    )

    indent = ""

    for char in marker_line:

        if char in {
            " ",
            "\t",
        }:

            indent += char

        else:

            break

    prepared = textwrap.indent(
        insertion.strip()
        +
        "\n\n",
        indent
    )

    return (
        text[:line_start]
        +
        prepared
        +
        text[line_start:]
    )


# =========================================================
# AST FUNCTION
# =========================================================

def find_function(
    tree,
    name
):

    for node in ast.walk(
        tree
    ):

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            )
            and
            node.name == name
        ):

            return node

    return None


# =========================================================
# FIND ASSIGNMENT IN FUNCTION
# =========================================================

def find_assignment(
    tree,
    function_name,
    variable_name
):

    function = (
        find_function(
            tree,
            function_name
        )
    )

    if function is None:

        fail(
            f"Function {function_name} not found"
        )

    matches = []

    for node in ast.walk(
        function
    ):

        if isinstance(
            node,
            ast.Assign
        ):

            for target in (
                node.targets
            ):

                if (
                    isinstance(
                        target,
                        ast.Name
                    )
                    and
                    target.id
                    ==
                    variable_name
                ):

                    matches.append(
                        node
                    )

        elif isinstance(
            node,
            ast.AnnAssign
        ):

            target = (
                node.target
            )

            if (
                isinstance(
                    target,
                    ast.Name
                )
                and
                target.id
                ==
                variable_name
            ):

                matches.append(
                    node
                )

    if len(matches) != 1:

        fail(
            f"{variable_name} assignment in "
            f"{function_name}: expected 1, "
            f"found {len(matches)}"
        )

    return matches[0]


# =========================================================
# INSERT AFTER AST NODE
# =========================================================

def insert_after_assignment(
    text,
    function_name,
    variable_name,
    insertion,
    unique_marker,
    label
):

    if unique_marker in text:

        print(
            f"[SKIP] {label}"
        )

        return text

    tree = ast.parse(
        text
    )

    node = find_assignment(
        tree,
        function_name,
        variable_name
    )

    lines = (
        text.splitlines(
            keepends=True
        )
    )

    end_line = (
        node.end_lineno
    )

    indent = (
        " "
        *
        node.col_offset
    )

    prepared = (
        textwrap.indent(
            insertion.strip(),
            indent
        )
        +
        "\n\n"
    )

    lines.insert(
        end_line,
        prepared
    )

    result = "".join(
        lines
    )

    ok(
        label
    )

    return result


# =========================================================
# LOAD
# =========================================================

if not BOT_PATH.exists():

    fail(
        "bot.py not found"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# VERSION
# =========================================================

if (
    f'BOT_VERSION = "{TARGET_VERSION}"'
    in bot
):

    print(
        "2.11B1 already installed."
    )

    sys.exit(
        0
    )


if (
    f'BOT_VERSION = "{EXPECTED_VERSION}"'
    not in bot
):

    fail(
        "Unexpected bot.py version. "
        f"Expected {EXPECTED_VERSION}."
    )


# =========================================================
# REQUIRED FILES
# =========================================================

for required in (
    "understanding.py",
    "naturalness.py",
):

    if not Path(
        required
    ).exists():

        fail(
            f"{required} missing"
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

backup_path = Path(
    f"bot.py.before-2.11B1-{stamp}.bak"
)

shutil.copy2(
    BOT_PATH,
    backup_path
)

print(
    f"[BACKUP] {backup_path}"
)


# =========================================================
# IMPORT:
# remove old Question Guard import
# from local_voice
# =========================================================

old_local_voice_import = '''from local_voice import (
    LOCAL_VOICE_VERSION,
    LOCAL_VOICE_ENABLED,
    humanize_evilnae_response,
    format_local_voice_debug,
    warm_local_voice,
    count_genuine_questions,
)
'''


new_local_voice_import = '''from local_voice import (
    LOCAL_VOICE_VERSION,
    LOCAL_VOICE_ENABLED,
    humanize_evilnae_response,
    format_local_voice_debug,
    warm_local_voice,
)
'''


bot = replace_once(
    bot,
    old_local_voice_import,
    new_local_voice_import,
    "Remove old Local Voice question detector"
)


# =========================================================
# UNDERSTANDING + NATURALNESS IMPORTS
# =========================================================

voice_memory_marker = '''from voice_memory import (
'''


new_imports = '''from understanding import (
    UNDERSTANDING_VERSION,
    classify_conversation_target,
    format_target_debug,
    count_genuine_questions,
    build_knowledge_constraint,
    format_knowledge_constraint,
    format_knowledge_debug,
    knowledge_violation_reasons,
)

from naturalness import (
    NATURALNESS_VERSION,
    analyze_naturalness,
    format_naturalness_for_writer,
    format_naturalness_debug,
)

'''


if new_imports.strip() not in bot:

    bot = bot.replace(
        voice_memory_marker,
        new_imports
        +
        voice_memory_marker,
        1
    )

    ok(
        "Understanding/Naturalness imports"
    )


# =========================================================
# VERSION
# =========================================================

bot = replace_once(
    bot,
    f'BOT_VERSION = "{EXPECTED_VERSION}"',
    f'BOT_VERSION = "{TARGET_VERSION}"',
    "Bot version"
)


# =========================================================
# TARGET GUARD AFTER
# conversation_continuation assignment
# =========================================================

target_guard_code = '''
# =====================================================
# 2.11B1 TARGET GUARD
#
# Active Conversation darf NICHT über eine
# eindeutige Ansprache an eine andere Person
# drüberfahren.
# =====================================================

conversation_target = (
    classify_conversation_target(

        perception,

        bot_user_id=(
            bot.user.id
        ),

        hanae_user_id=(
            HANAE_USER_ID
        )
    )
)

print(
    format_target_debug(
        conversation_target
    )
)

if (
    conversation_target
    .blocks_active_continuation
):

    if conversation_continuation:

        print(
            "[ACTIVE CONVERSATION BLOCKED] "
            f"user={username} "
            f"target="
            f"{conversation_target.target_kind} "
            f"reason="
            f"{conversation_target.reason}"
        )

    conversation_continuation = False
'''


bot = insert_after_assignment(
    bot,
    "on_message",
    "conversation_continuation",
    target_guard_code,
    "[ACTIVE CONVERSATION BLOCKED]",
    "Target Guard / Active Conversation v2"
)


# =========================================================
# KNOWLEDGE CONSTRAINT
# directly after writer_context
# =========================================================

knowledge_context_code = '''
# =====================================================
# KNOWLEDGE GUARD v3 FOUNDATION
#
# Wenn Brain sagt:
#
# knowledge_available=False
#
# und der User fragt nach einem Fakt
# über eine andere bekannte Person,
# darf Writer nicht plausibel raten.
# =====================================================

knowledge_constraint = (
    build_knowledge_constraint(

        user_text=(
            user_text
        ),

        decision=(
            decision
        ),

        hanae_user_id=(
            HANAE_USER_ID
        )
    )
)

print(
    format_knowledge_debug(
        knowledge_constraint
    )
)

if knowledge_constraint.active:

    writer_context += (
        "\\n\\n"
        +
        format_knowledge_constraint(
            knowledge_constraint
        )
    )
'''


bot = insert_after_assignment(
    bot,
    "on_message",
    "writer_context",
    knowledge_context_code,
    "[KNOWLEDGE CONSTRAINT]",
    "Knowledge Guard writer context"
)


# =========================================================
# PRE-LOCAL-VOICE KNOWLEDGE CHECK
# =========================================================

local_voice_marker = '''        # -------------------------------------------------
        # FRESH CHANNEL HISTORY FOR LOCAL VOICE
'''


pre_voice_guard = '''
# =====================================================
# KNOWLEDGE OUTPUT GUARD
#
# Prompt-Regel allein reicht nicht.
#
# Deshalb wird die fertige Writer-Antwort
# nochmal deterministisch geprüft.
# =====================================================

knowledge_violations = (
    knowledge_violation_reasons(
        answer,
        knowledge_constraint
    )
)

if knowledge_violations:

    print(
        "[KNOWLEDGE OUTPUT VIOLATION] "
        f"user={username} "
        f"violations="
        f"{knowledge_violations} "
        f"answer={answer!r}"
    )

    knowledge_repair_context = (
        writer_context
        +
        "\\n\\n"
        +
        format_knowledge_constraint(
            knowledge_constraint
        )
    )

    knowledge_repair = (
        await repair_writer_answer(

            original_answer=(
                answer
            ),

            violation_reasons=(
                knowledge_violations
            ),

            writer_context=(
                knowledge_repair_context
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

    if not knowledge_repair:

        print(
            "[KNOWLEDGE OUTPUT ABORT] "
            f"user={username} "
            "reason=repair_failed"
        )

        return

    knowledge_repair = (
        clean_generated_answer(
            knowledge_repair
        )
    )

    knowledge_repair = (
        enforce_permanent_expression_bans(
            knowledge_repair
        )
    )

    repair_hard_violations = (
        get_writer_violation_reasons(

            answer=(
                knowledge_repair
            ),

            decision=(
                decision
            ),

            autonomous_participation=(
                autonomous_participation
            )
        )
    )

    repair_knowledge_violations = (
        knowledge_violation_reasons(
            knowledge_repair,
            knowledge_constraint
        )
    )

    if (
        repair_hard_violations
        or
        repair_knowledge_violations
    ):

        print(
            "[KNOWLEDGE OUTPUT ABORT] "
            f"user={username} "
            f"hard="
            f"{repair_hard_violations} "
            f"knowledge="
            f"{repair_knowledge_violations}"
        )

        return

    answer = (
        knowledge_repair
    )
'''


if (
    "[KNOWLEDGE OUTPUT VIOLATION]"
    not in bot
):

    count = (
        bot.count(
            local_voice_marker
        )
    )

    if count != 1:

        fail(
            "Local Voice insertion marker "
            f"found {count} times"
        )

    bot = bot.replace(
        local_voice_marker,
        textwrap.indent(
            pre_voice_guard.strip(),
            "        "
        )
        +
        "\n\n"
        +
        local_voice_marker,
        1
    )

    ok(
        "Knowledge output final check"
    )


# =========================================================
# POST LOCAL VOICE:
#
# 1. Knowledge recheck
# 2. Question Guard 2.1
# 3. Naturalness Guard
# =========================================================

expression_final_marker = '''        # =================================================
        # 11.6 EXPRESSION FINAL GUARD
'''


post_voice_guards = '''
# =====================================================
# POST-VOICE UNDERSTANDING GUARDS
#
# Qwen darf einen bereits sicheren Writer-Draft
# nicht wieder semantisch kaputtmachen.
# =====================================================

post_voice_knowledge_violations = (
    knowledge_violation_reasons(
        answer,
        knowledge_constraint
    )
)

if post_voice_knowledge_violations:

    print(
        "[LOCAL VOICE KNOWLEDGE REVERT] "
        f"user={username} "
        f"violations="
        f"{post_voice_knowledge_violations}"
    )

    answer = (
        original_writer_answer
    )


# =====================================================
# QUESTION GUARD 2.1
#
# Beispiel aus dem Test:
#
# "ich bin kein Fan. was ist der Reiz daran?"
#
# wird jetzt als echte Gegenfrage erkannt.
# =====================================================

if (
    not decision.ask_question
    and
    count_genuine_questions(
        answer
    )
    > 0
):

    print(
        "[QUESTION GUARD 2.1] "
        f"user={username} "
        f"answer={answer!r}"
    )

    if (
        count_genuine_questions(
            original_writer_answer
        )
        ==
        0
    ):

        answer = (
            original_writer_answer
        )

    else:

        question_repair = (
            await repair_writer_answer(

                original_answer=(
                    answer
                ),

                violation_reasons=[
                    "question_not_allowed"
                ],

                writer_context=(
                    writer_context
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
                "[QUESTION GUARD ABORT] "
                f"user={username}"
            )

            return

        question_repair = (
            clean_generated_answer(
                question_repair
            )
        )

        if (
            count_genuine_questions(
                question_repair
            )
            > 0
        ):

            print(
                "[QUESTION GUARD ABORT] "
                f"user={username} "
                "reason=repair_still_question"
            )

            return

        answer = (
            question_repair
        )


# =====================================================
# NATURALNESS GUARD
#
# Erkennt nicht nur harte:
#
# "Das klingt spannend!"
#
# sondern Cluster wie:
#
# "aber hey"
# +
# "Geschmack ist subjektiv"
# +
# "ich persönlich..."
# =====================================================

naturalness_analysis = (
    analyze_naturalness(
        answer
    )
)

print(
    format_naturalness_debug(
        naturalness_analysis
    )
)

if (
    naturalness_analysis
    .rewrite_required
):

    naturalness_repair_context = (
        writer_context
        +
        "\\n\\n"
        +
        format_naturalness_for_writer(
            naturalness_analysis
        )
    )

    naturalness_repair = (
        await repair_writer_answer(

            original_answer=(
                answer
            ),

            violation_reasons=[
                "soft_bot_pattern_cluster",
                *naturalness_analysis.matches
            ],

            writer_context=(
                naturalness_repair_context
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

    if naturalness_repair:

        naturalness_repair = (
            clean_generated_answer(
                naturalness_repair
            )
        )

        naturalness_repair = (
            enforce_permanent_expression_bans(
                naturalness_repair
            )
        )

        repaired_naturalness = (
            analyze_naturalness(
                naturalness_repair
            )
        )

        repaired_knowledge = (
            knowledge_violation_reasons(
                naturalness_repair,
                knowledge_constraint
            )
        )

        repaired_questions = (
            count_genuine_questions(
                naturalness_repair
            )
        )

        repaired_hard = (
            get_writer_violation_reasons(

                answer=(
                    naturalness_repair
                ),

                decision=(
                    decision
                ),

                autonomous_participation=(
                    autonomous_participation
                )
            )
        )

        if (
            not repaired_knowledge
            and
            (
                decision.ask_question
                or
                repaired_questions == 0
            )
            and
            not repaired_hard
            and
            repaired_naturalness.score
            <
            naturalness_analysis.score
        ):

            print(
                "[NATURALNESS REPAIR ACCEPTED] "
                f"user={username} "
                f"before="
                f"{naturalness_analysis.score} "
                f"after="
                f"{repaired_naturalness.score}"
            )

            answer = (
                naturalness_repair
            )

        else:

            print(
                "[NATURALNESS REPAIR REJECTED] "
                f"user={username} "
                f"old_score="
                f"{naturalness_analysis.score} "
                f"new_score="
                f"{repaired_naturalness.score} "
                f"knowledge="
                f"{repaired_knowledge} "
                f"questions="
                f"{repaired_questions} "
                f"hard="
                f"{repaired_hard}"
            )
'''


if (
    "[NATURALNESS REPAIR ACCEPTED]"
    not in bot
):

    count = (
        bot.count(
            expression_final_marker
        )
    )

    if count != 1:

        fail(
            "Expression Final marker "
            f"found {count} times"
        )

    bot = bot.replace(
        expression_final_marker,
        textwrap.indent(
            post_voice_guards.strip(),
            "        "
        )
        +
        "\n\n"
        +
        expression_final_marker,
        1
    )

    ok(
        "Post-Voice Understanding Guards"
    )


# =========================================================
# SYNTAX
# =========================================================

try:

    ast.parse(
        bot,
        filename=(
            str(
                BOT_PATH
            )
        )
    )

except SyntaxError as error:

    print("")
    print(
        "============================================"
    )
    print(
        "SYNTAX CHECK FAILED"
    )
    print(
        "============================================"
    )

    print(
        f"Line: {error.lineno}"
    )

    print(
        f"Offset: {error.offset}"
    )

    print(
        f"Error: {error.msg}"
    )

    print("")
    print(
        "bot.py was NOT overwritten."
    )

    print(
        f"Backup: {backup_path}"
    )

    sys.exit(
        1
    )


ok(
    "Python syntax check"
)


# =========================================================
# WRITE
# =========================================================

temp_path = Path(
    "bot.py.2.11B1.tmp"
)

temp_path.write_text(
    bot,
    encoding="utf-8"
)

temp_path.replace(
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

required_markers = [

    f'BOT_VERSION = "{TARGET_VERSION}"',

    "classify_conversation_target",

    "[ACTIVE CONVERSATION BLOCKED]",

    "build_knowledge_constraint",

    "[KNOWLEDGE OUTPUT VIOLATION]",

    "[QUESTION GUARD 2.1]",

    "analyze_naturalness",

    "[NATURALNESS REPAIR ACCEPTED]",
]


missing = [

    marker

    for marker
    in required_markers

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
    "EVILNAE 2.11B1 INSTALL COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: {TARGET_VERSION}"
)

print(
    f"Backup: {backup_path}"
)

print("")
print(
    "Installed:"
)

print(
    "  [✓] Conversation Target Guard"
)

print(
    "  [✓] Active Conversation v2 routing"
)

print(
    "  [✓] Question Guard 2.1"
)

print(
    "  [✓] Knowledge Guard v3 foundation"
)

print(
    "  [✓] Unknown-person output validation"
)

print(
    "  [✓] Post-Qwen knowledge recheck"
)

print(
    "  [✓] Naturalness soft-bot cluster guard"
)

print("")
print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py understanding.py naturalness.py "
    "coherence.py perception.py expression.py "
    "inner_state.py local_voice.py"
)

print("")
print(
    "Then:"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
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

SELF_MODEL_PATH = Path(
    "self_model.py"
)

GITIGNORE_PATH = Path(
    ".gitignore"
)


EXPECTED_BOT_VERSION = (
    "2.11.3-agency-b3a"
)

TARGET_BOT_VERSION = (
    "2.11.4-self-b3b"
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
# REPLACE ONCE
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
            f"{label}: expected 1 match, "
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
# REQUIRED FILES
# =========================================================

if not BOT_PATH.exists():

    fail(
        "bot.py missing"
    )


if not SELF_MODEL_PATH.exists():

    fail(
        "self_model.py missing"
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
        "B3B already installed."
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
    f"bot.py.before-2.11B3B-{stamp}.bak"
)


shutil.copy2(
    BOT_PATH,
    bot_backup
)


print(
    f"[BACKUP] {bot_backup}"
)


gitignore_backup = None


if GITIGNORE_PATH.exists():

    gitignore_backup = Path(
        f".gitignore.before-2.11B3B-{stamp}.bak"
    )

    shutil.copy2(
        GITIGNORE_PATH,
        gitignore_backup
    )

    print(
        f"[BACKUP] {gitignore_backup}"
    )


# =========================================================
# 1. BRAIN VERSION IMPORT
#
# Behebt nebenbei:
#
# Startup sagte bisher noch Brain v2.1,
# obwohl tatsächlich Brain 2.2-agency läuft.
# =========================================================

old = '''from brain import (
    run_brain,
    format_brain_debug,
    format_brain_decision,
)
'''


new = '''from brain import (
    BRAIN_VERSION,
    run_brain,
    format_brain_debug,
    format_brain_decision,
)
'''


bot = replace_once(
    bot,
    old,
    new,
    "Brain version import"
)


# =========================================================
# 2. SELF MODEL IMPORTS
# =========================================================

old = '''from agency import (
    AGENCY_VERSION,
    ACTION_REPLY,
    ACTION_REACT,
    ACTION_STAY_SILENT,
    apply_agency_guard,
    format_agency_debug,
)

from voice_memory import (
'''


new = '''from agency import (
    AGENCY_VERSION,
    ACTION_REPLY,
    ACTION_REACT,
    ACTION_STAY_SILENT,
    apply_agency_guard,
    format_agency_debug,
)

from self_model import (
    SELF_MODEL_VERSION,
    resolve_self_query,
    apply_self_evidence_to_decision,
    format_self_model_for_brain,
    format_self_evidence_for_writer,
    self_knowledge_violation_reasons,
    format_self_model_debug,
    format_self_evidence_debug,
)

from voice_memory import (
'''


bot = replace_once(
    bot,
    old,
    new,
    "Self Model imports"
)


# =========================================================
# 3. BOT VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"',

    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',

    "Bot version"
)


# =========================================================
# 4. REAL BRAIN VERSION AT STARTUP
# =========================================================

old = '''    print(
        "Brain v2.1: ACTIVE"
    )
'''


new = '''    print(
        f"Brain v{BRAIN_VERSION}: ACTIVE"
    )
'''


bot = replace_once(
    bot,
    old,
    new,
    "Dynamic Brain startup version"
)


# =========================================================
# 5. SELF MODEL STARTUP
# =========================================================

old = '''    print(
        "Source Authority: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


new = '''    print(
        "Source Authority: ACTIVE"
    )

    print(
        f"Self Model v"
        f"{SELF_MODEL_VERSION}: ACTIVE"
    )

    print(
        "Self Knowledge Guard: ACTIVE"
    )

    print(
        format_self_model_debug()
    )

    print(
        f"Response Agency v"
'''


bot = replace_once(
    bot,
    old,
    new,
    "Self Model startup status"
)


# =========================================================
# 6. SELF MODEL -> BRAIN CONTEXT
#
# Conversation World sagt:
# "Was passiert zwischen Personen?"
#
# Self Model sagt:
# "Was ist über Evilnae selbst etabliert?"
# =========================================================

old = '''        group_context_text += (
            "\\n\\n"
            +
            world_brain_text
        )

        reply_context_text = (
'''


new = '''        self_model_brain_text = (
            format_self_model_for_brain()
        )

        group_context_text += (
            "\\n\\n"
            +
            world_brain_text
            +
            "\\n\\n"
            +
            self_model_brain_text
        )

        reply_context_text = (
'''


bot = replace_once(
    bot,
    old,
    new,
    "Self Model -> Brain context"
)


# =========================================================
# 7. SELF EVIDENCE AFTER WORLD EVIDENCE
#
# Sehr wichtig:
#
# Brain könnte sagen:
#
# knowledge=True
# source=recent_context
#
# bei:
#
# "Hast du den Boss besiegt?"
#
# Self Model darf das danach zurück auf UNKNOWN setzen.
# =========================================================

old = '''        if world_evidence.matched:

            print(
                format_world_evidence_debug(
                    world_evidence
                )
            )

        print(
            format_brain_debug(
                decision
            )
        )
'''


new = '''        if world_evidence.matched:

            print(
                format_world_evidence_debug(
                    world_evidence
                )
            )

        # =================================================
        # 2.11B3B SELF KNOWLEDGE AUTHORITY
        # =================================================

        self_evidence = (
            resolve_self_query(
                user_text
            )
        )

        apply_self_evidence_to_decision(
            decision,
            self_evidence
        )

        if self_evidence.matched:

            print(
                format_self_evidence_debug(
                    self_evidence
                )
            )

        print(
            format_brain_debug(
                decision
            )
        )
'''


bot = replace_once(
    bot,
    old,
    new,
    "Self Knowledge authority override"
)


# =========================================================
# 8. SELF EVIDENCE -> WRITER
# =========================================================

old = '''        # =====================================================
        # KNOWLEDGE GUARD v3 FOUNDATION
'''


new = '''        # =====================================================
        # 2.11B3B SELF EVIDENCE -> WRITER
        # =====================================================

        if self_evidence.matched:

            writer_context += (
                "\\n\\n"
                +
                format_self_evidence_for_writer(
                    self_evidence
                )
            )

        # =====================================================
        # KNOWLEDGE GUARD v3 FOUNDATION
'''


bot = replace_once(
    bot,
    old,
    new,
    "Self Evidence -> Writer"
)


# =========================================================
# 9. WRITER SELF KNOWLEDGE GUARD
#
# Prompt allein reicht nicht.
#
# Wir prüfen die fertige Writer-Antwort
# deterministisch, BEVOR Qwen drankommt.
# =========================================================

old = '''        # =====================================================
        # KNOWLEDGE OUTPUT GUARD
'''


new = '''        # =====================================================
        # SELF KNOWLEDGE OUTPUT GUARD
        # =====================================================

        self_violations = (
            self_knowledge_violation_reasons(
                answer,
                self_evidence
            )
        )

        if self_violations:

            print(
                "[SELF KNOWLEDGE VIOLATION] "
                f"user={username} "
                f"violations="
                f"{self_violations} "
                f"answer={answer!r}"
            )

            self_repair_context = (
                writer_context
                +
                "\\n\\n"
                +
                format_self_evidence_for_writer(
                    self_evidence
                )
            )

            self_repair = (
                await repair_writer_answer(

                    original_answer=(
                        answer
                    ),

                    violation_reasons=(
                        self_violations
                    ),

                    writer_context=(
                        self_repair_context
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

            if not self_repair:

                print(
                    "[SELF KNOWLEDGE ABORT] "
                    f"user={username} "
                    "reason=repair_failed"
                )

                return

            self_repair = (
                clean_generated_answer(
                    self_repair
                )
            )

            self_repair = (
                enforce_permanent_expression_bans(
                    self_repair
                )
            )

            self_repair_hard = (
                get_writer_violation_reasons(

                    answer=(
                        self_repair
                    ),

                    decision=(
                        decision
                    ),

                    autonomous_participation=(
                        autonomous_participation
                    )
                )
            )

            self_repair_violations = (
                self_knowledge_violation_reasons(
                    self_repair,
                    self_evidence
                )
            )

            if (
                self_repair_hard
                or
                self_repair_violations
            ):

                print(
                    "[SELF KNOWLEDGE ABORT] "
                    f"user={username} "
                    f"hard="
                    f"{self_repair_hard} "
                    f"self="
                    f"{self_repair_violations}"
                )

                return

            print(
                "[SELF KNOWLEDGE REPAIR SUCCESS] "
                f"user={username}"
            )

            answer = (
                self_repair
            )

        # =====================================================
        # KNOWLEDGE OUTPUT GUARD
'''


bot = replace_once(
    bot,
    old,
    new,
    "Writer Self Knowledge Guard"
)


# =========================================================
# 10. POST-QWEN SELF GUARD
#
# Qwen darf aus:
#
# "dazu hab ich keine klare Erinnerung"
#
# nicht wieder:
#
# "ja, hab ich besiegt"
#
# machen.
# =========================================================

old = '''        # =====================================================
        # POST-VOICE UNDERSTANDING GUARDS
'''


new = '''        # =====================================================
        # POST-VOICE SELF KNOWLEDGE GUARD
        # =====================================================

        post_voice_self_violations = (
            self_knowledge_violation_reasons(
                answer,
                self_evidence
            )
        )

        if post_voice_self_violations:

            print(
                "[LOCAL VOICE SELF REVERT] "
                f"user={username} "
                f"violations="
                f"{post_voice_self_violations}"
            )

            answer = (
                original_writer_answer
            )

            reverted_self_violations = (
                self_knowledge_violation_reasons(
                    answer,
                    self_evidence
                )
            )

            if reverted_self_violations:

                print(
                    "[LOCAL VOICE SELF ABORT] "
                    f"user={username} "
                    f"violations="
                    f"{reverted_self_violations}"
                )

                return

        # =====================================================
        # POST-VOICE UNDERSTANDING GUARDS
'''


bot = replace_once(
    bot,
    old,
    new,
    "Post-Qwen Self Knowledge Guard"
)


# =========================================================
# 11. FINAL SELF GUARD
#
# Nach Naturalness + Expression Repair
# nochmal prüfen.
#
# Damit kann auch ein später Repair-Layer
# keine falsche Evilnae-Vergangenheit
# wieder hineinbringen.
# =========================================================

old = '''        # =================================================
        # 12. CONTEXT FRESHNESS + SEND
'''


new = '''        # =================================================
        # FINAL SELF KNOWLEDGE GUARD
        # =================================================

        final_self_violations = (
            self_knowledge_violation_reasons(
                answer,
                self_evidence
            )
        )

        if final_self_violations:

            print(
                "[SELF FINAL ABORT] "
                f"user={username} "
                f"violations="
                f"{final_self_violations} "
                f"answer={answer!r}"
            )

            return

        # =================================================
        # 12. CONTEXT FRESHNESS + SEND
'''


bot = replace_once(
    bot,
    old,
    new,
    "Final Self Knowledge Guard"
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
        "Nothing was overwritten."
    )


ok(
    "bot.py syntax check"
)


# =========================================================
# WRITE BOT
# =========================================================

temp_path = Path(
    "bot.py.2.11B3B.tmp"
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
# GITIGNORE
#
# Das spätere gelernte Self Model
# darf nicht versehentlich öffentlich
# ins Repo gepusht werden.
# =========================================================

if GITIGNORE_PATH.exists():

    gitignore = (
        GITIGNORE_PATH.read_text(
            encoding="utf-8"
        )
    )

else:

    gitignore = ""


if (
    "evilnae_self_model.json"
    not in gitignore
):

    if (
        gitignore
        and
        not gitignore.endswith(
            "\\n"
        )
    ):

        gitignore += (
            "\\n"
        )

    gitignore += (
        "evilnae_self_model.json\\n"
    )

    GITIGNORE_PATH.write_text(
        gitignore,
        encoding="utf-8"
    )

    ok(
        ".gitignore Self Model state"
    )

else:

    print(
        "[SKIP] .gitignore Self Model state"
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

    "BRAIN_VERSION",

    "SELF_MODEL_VERSION",

    "resolve_self_query(",

    "apply_self_evidence_to_decision(",

    "[SELF KNOWLEDGE VIOLATION]",

    "[LOCAL VOICE SELF REVERT]",

    "[SELF FINAL ABORT]",

    "Self Knowledge Guard: ACTIVE",
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


gitignore_after = (
    GITIGNORE_PATH.read_text(
        encoding="utf-8"
    )
)


if (
    "evilnae_self_model.json"
    not in gitignore_after
):

    fail(
        ".gitignore verification failed"
    )


# =========================================================
# DONE
# =========================================================

print("")
print(
    "============================================"
)
print(
    "EVILNAE 2.11B3B INSTALL COMPLETE"
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
    "  [✓] Persistent Self Model foundation"
)

print(
    "  [✓] Fixed Evilnae core facts"
)

print(
    "  [✓] Broad interests without fake specifics"
)

print(
    "  [✓] Self Knowledge authority"
)

print(
    "  [✓] Unknown self-experience protection"
)

print(
    "  [✓] No random game history"
)

print(
    "  [✓] No random favorites"
)

print(
    "  [✓] Writer Self Guard"
)

print(
    "  [✓] Post-Qwen Self Guard"
)

print(
    "  [✓] Final Self Guard"
)

print(
    "  [✓] Real Brain startup version"
)

print(
    "  [✓] Self Model state gitignored"
)

print("")
print(
    "NOT ENABLED YET:"
)

print(
    "  [ ] automatic Self Learning"
)

print(
    "  [ ] Episodes deciding new Self Facts"
)

print(
    "  [ ] automatic opinion evolution"
)

print("")
print(
    f"Backup:"
)

print(
    f"  {bot_backup}"
)

if gitignore_backup:

    print(
        f"  {gitignore_backup}"
    )

print("")
print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py self_model.py brain.py "
    "agency.py conversation_world.py "
    "understanding.py naturalness.py "
    "coherence.py perception.py "
    "expression.py inner_state.py "
    "local_voice.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
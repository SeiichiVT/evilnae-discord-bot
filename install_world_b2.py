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

EXPECTED_VERSION = (
    "2.11.1-understanding-b1"
)

TARGET_VERSION = (
    "2.11.2-world-b2"
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
# SAFE REPLACE
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
# LOAD
# =========================================================

if not BOT_PATH.exists():

    fail(
        "bot.py not found"
    )


if not Path(
    "conversation_world.py"
).exists():

    fail(
        "conversation_world.py missing"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


# =========================================================
# VERSION CHECK
# =========================================================

if (
    f'BOT_VERSION = "{TARGET_VERSION}"'
    in bot
):

    print(
        "2.11B2 already installed."
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
# BACKUP
# =========================================================

stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)

backup = Path(
    f"bot.py.before-2.11B2-"
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
# 1. IMPORTS
# =========================================================

old = '''from naturalness import (
    NATURALNESS_VERSION,
    analyze_naturalness,
    format_naturalness_for_writer,
    format_naturalness_debug,
)

from voice_memory import (
'''


new = '''from naturalness import (
    NATURALNESS_VERSION,
    analyze_naturalness,
    format_naturalness_for_writer,
    format_naturalness_debug,
)

from conversation_world import (
    WORLD_VERSION,
    observe_world_message,
    resolve_world_query,
    apply_world_evidence_to_decision,
    format_world_for_brain,
    format_world_evidence_for_writer,
    format_world_observation_debug,
    format_world_evidence_debug,
)

from voice_memory import (
'''


bot = replace_once(
    bot,
    old,
    new,
    "Conversation World imports"
)


# =========================================================
# 2. BOT VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_VERSION}"',

    f'BOT_VERSION = "{TARGET_VERSION}"',

    "Bot version"
)


# =========================================================
# 3. STARTUP STATUS
# =========================================================

old = '''    print(
        "Knowledge Guard: ACTIVE"
    )

    print(
        f"Expression Layer v"
'''


new = '''    print(
        "Knowledge Guard: ACTIVE"
    )

    print(
        f"Conversation World v"
        f"{WORLD_VERSION}: ACTIVE"
    )

    print(
        "Source Authority: ACTIVE"
    )

    print(
        f"Expression Layer v"
'''


bot = replace_once(
    bot,
    old,
    new,
    "Startup World status"
)


# =========================================================
# 4. OBSERVE EVERY USER MESSAGE
#
# Wichtig:
#
# Conversation World läuft BEVOR entschieden wird,
# ob Evilnae antwortet.
#
# Deshalb kann Hanae sagen:
#
# "Meine Lieblingspizza ist Thunfisch"
#
# Evilnae kann schweigen,
# aber Conversation World hat es trotzdem gesehen.
# =========================================================

old = '''    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    # =====================================================
    # CHANNEL-WIDE EVILNAE HISTORY
'''


new = '''    channel_snapshot = list(
        get_channel_context(
            channel_id
        )
    )

    # =====================================================
    # 2.11B2 CONVERSATION WORLD OBSERVATION
    #
    # Läuft VOR Routing / Participation.
    #
    # Dadurch beobachtet Evilnae auch Aussagen,
    # auf die sie bewusst nicht antwortet.
    # =====================================================

    world_claims = (
        observe_world_message(

            channel_id=channel_id,

            user_id=user_id,

            username=username,

            text=(
                perception.text
                or
                perception.raw_content
                or ""
            ),

            hanae_user_id=(
                HANAE_USER_ID
            )
        )
    )

    if world_claims:

        print(
            format_world_observation_debug(
                world_claims
            )
        )

    # =====================================================
    # CHANNEL-WIDE EVILNAE HISTORY
'''


bot = replace_once(
    bot,
    old,
    new,
    "Observe Conversation World"
)


# =========================================================
# 5. WORLD -> BRAIN CONTEXT
# =========================================================

old = '''        group_context_text = (
            format_channel_context(
                channel_snapshot
            )
        )

        reply_context_text = (
'''


new = '''        group_context_text = (
            format_channel_context(
                channel_snapshot
            )
        )

        world_brain_text = (
            format_world_for_brain(
                channel_id
            )
        )

        group_context_text += (
            "\\n\\n"
            +
            world_brain_text
        )

        reply_context_text = (
'''


bot = replace_once(
    bot,
    old,
    new,
    "World -> Brain context"
)


# =========================================================
# 6. SOURCE AUTHORITY AFTER BRAIN
# =========================================================

old = '''        brain_duration = (
            time.perf_counter()
            - brain_start
        )

        print(
            format_brain_debug(
                decision
            )
        )
'''


new = '''        brain_duration = (
            time.perf_counter()
            - brain_start
        )

        # =================================================
        # 2.11B2 SOURCE AUTHORITY OVERRIDE
        #
        # Das Brain darf einen eigenen Self-Report
        # nicht durch eine fremde Behauptung,
        # Troll-Aussage oder Spekulation ersetzen.
        # =================================================

        world_evidence = (
            resolve_world_query(

                channel_id=channel_id,

                user_text=user_text,

                hanae_user_id=(
                    HANAE_USER_ID
                )
            )
        )

        apply_world_evidence_to_decision(
            decision,
            world_evidence
        )

        if world_evidence.matched:

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


bot = replace_once(
    bot,
    old,
    new,
    "Source Authority override"
)


# =========================================================
# 7. WORLD EVIDENCE -> WRITER
# =========================================================

old = '''        # =====================================================
        # KNOWLEDGE GUARD v3 FOUNDATION
        #
        # Wenn Brain sagt:
'''


new = '''        # =====================================================
        # 2.11B2 WORLD EVIDENCE -> WRITER
        # =====================================================

        if world_evidence.matched:

            writer_context += (
                "\\n\\n"
                +
                format_world_evidence_for_writer(
                    world_evidence
                )
            )

        # =====================================================
        # KNOWLEDGE GUARD v3 FOUNDATION
        #
        # Wenn Brain sagt:
'''


bot = replace_once(
    bot,
    old,
    new,
    "World evidence -> Writer"
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
        "Patched bot.py syntax error "
        f"line={error.lineno}: "
        f"{error.msg}. "
        "Original file was not overwritten. "
        f"Backup={backup}"
    )


ok(
    "Python syntax check"
)


# =========================================================
# WRITE
# =========================================================

temp_path = Path(
    "bot.py.2.11B2.tmp"
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

installed = BOT_PATH.read_text(
    encoding="utf-8"
)

required = [

    f'BOT_VERSION = "{TARGET_VERSION}"',

    "Conversation World v",

    "observe_world_message(",

    "format_world_for_brain(",

    "apply_world_evidence_to_decision(",

    "format_world_evidence_for_writer(",
]


missing = [

    item

    for item
    in required

    if item not in installed
]


if missing:

    fail(
        "Verification failed: "
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
    "EVILNAE 2.11B2 INSTALL COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: "
    f"{TARGET_VERSION}"
)

print(
    f"Backup: {backup}"
)

print("")
print(
    "Installed:"
)

print(
    "  [✓] Runtime Conversation World"
)

print(
    "  [✓] Self-report claim extraction"
)

print(
    "  [✓] Third-party claims stay unverified"
)

print(
    "  [✓] Source Authority override"
)

print(
    "  [✓] Hanae self-report beats troll/speculation"
)

print(
    "  [✓] World evidence reaches Brain + Writer"
)

print("")
print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py conversation_world.py "
    "understanding.py naturalness.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
from pathlib import Path
from datetime import datetime
import ast
import shutil
import sys

BOT = Path("bot.py")
PART = Path("participation.py")
ROUTING = Path("routing_hardening.py")

EXPECTED_BOT = "2.13.0-output-quality-b3e"
TARGET_BOT = "2.14.0-routing-b3f"

EXPECTED_PART = "1.1"
TARGET_PART = "1.2"


def fail(message):

    raise SystemExit(
        f"\n[INSTALL ERROR] {message}\n"
    )


def replace_once(
    text,
    old,
    new,
    label,
):

    count = text.count(
        old
    )

    if count != 1:

        fail(
            f"{label}: "
            f"expected 1 match, "
            f"found {count}"
        )

    print(
        f"[OK] {label}"
    )

    return text.replace(
        old,
        new,
        1,
    )


def insert_before(
    text,
    marker,
    block,
    label,
):

    count = text.count(
        marker
    )

    if count != 1:

        fail(
            f"{label}: "
            f"expected 1 marker, "
            f"found {count}"
        )

    print(
        f"[OK] {label}"
    )

    return text.replace(
        marker,
        block + marker,
        1,
    )


def insert_after(
    text,
    marker,
    block,
    label,
):

    count = text.count(
        marker
    )

    if count != 1:

        fail(
            f"{label}: "
            f"expected 1 marker, "
            f"found {count}"
        )

    print(
        f"[OK] {label}"
    )

    return text.replace(
        marker,
        marker + block,
        1,
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

    print(
        f"[OK] {filename} syntax check"
    )


print(
    "[B3F ROUTING HARDENING PACK] starting..."
)


for path in (
    BOT,
    PART,
    ROUTING,
):

    if not path.exists():

        fail(
            f"{path} missing"
        )


bot = BOT.read_text(
    encoding="utf-8"
)

part = PART.read_text(
    encoding="utf-8"
)

routing = ROUTING.read_text(
    encoding="utf-8"
)


if (
    'ROUTING_HARDENING_VERSION = "1.0"'
    not in routing
):

    fail(
        "routing_hardening.py is not v1.0"
    )


syntax_check(
    routing,
    "routing_hardening.py",
)


if (
    f'BOT_VERSION = "{TARGET_BOT}"'
    in bot
):

    raise SystemExit(
        "B3F already installed."
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
    f'PARTICIPATION_VERSION = "{EXPECTED_PART}"'
    not in part
):

    fail(
        "Unexpected Participation version. "
        f"Expected {EXPECTED_PART}."
    )


for marker in (
    "Output Quality v{OUTPUT_QUALITY_VERSION}: ACTIVE",
    "Qwen Acceptance v2: ACTIVE",
    "Response Reliability v1: ACTIVE",
    "Direct Address Resolver v2: ACTIVE",
):

    if marker not in bot:

        fail(
            f"Previous feature missing: {marker}"
        )


print(
    "[OK] B3E base detected"
)


bot = insert_before(
    bot,

    "from response_quality import (\n",

    '''from routing_hardening import (
    ROUTING_HARDENING_VERSION,
    harden_perception_addressing,
    build_routing_context,
    apply_participation_routing_boost,
    format_routing_debug,
    format_participation_boost_debug,
)

''',

    "Routing import",
)


bot = replace_once(
    bot,

    f'BOT_VERSION = "{EXPECTED_BOT}"',

    f'BOT_VERSION = "{TARGET_BOT}"',

    "Bot version",
)


bot = replace_once(
    bot,

    "ACTIVE_CONVERSATION_CONTEXT_GAP = 4",

    "ACTIVE_CONVERSATION_CONTEXT_GAP = 8",

    "Group thread scan depth",
)


part = replace_once(
    part,

    f'PARTICIPATION_VERSION = "{EXPECTED_PART}"',

    f'PARTICIPATION_VERSION = "{TARGET_PART}"',

    "Participation version",
)


bot = insert_after(
    bot,

    '''    print(
        "Targeted Quality Repair: ACTIVE"
    )

''',

    '''    print(
        f"Routing Hardening v{ROUTING_HARDENING_VERSION}: ACTIVE"
    )

    print(
        "Stretched Evil/Evilnae Vocatives: ACTIVE"
    )

    print(
        "Reply-To Priority Routing: ACTIVE"
    )

    print(
        "Reference Resolver v2: ACTIVE"
    )

    print(
        "Parallel Group Thread Scan: ACTIVE "
        f"(depth={ACTIVE_CONVERSATION_CONTEXT_GAP})"
    )

    print(
        "Participation Routing Boost: ACTIVE"
    )

''',

    "Startup status",
)


bot = insert_before(
    bot,

    '''    print(
        format_perception_debug(
            perception
        )
    )
''',

    '''    # =====================================================
    # B3F ROUTING HARDENING
    # =====================================================

    routing_signals = (
        harden_perception_addressing(
            perception,
            bot_user_id=(
                str(bot.user.id)
                if bot.user
                else None
            )
        )
    )

    if (
        routing_signals.changed
        or routing_signals.name_variant
        or routing_signals.reply_to_evilnae
        or routing_signals.reference_types
    ):

        print(
            format_routing_debug(
                routing_signals
            )
        )

''',

    "Address / Reply priority integration",
)


bot = insert_before(
    bot,

    '''    # =====================================================
    # 2.11B2 CONVERSATION WORLD OBSERVATION
''',

    '''    # =====================================================
    # B3F ROUTING / REFERENCE CONTEXT
    # =====================================================

    b3f_routing_context_text = (
        build_routing_context(
            perception,
            channel_snapshot,
            current_user_id=user_id,
            bot_user_id=(
                str(bot.user.id)
                if bot.user
                else None
            )
        )
    )

''',

    "Routing context build",
)


bot = insert_before(
    bot,

    '''        reply_context_text = (
            "Keine direkte Discord-Antwort."
        )
''',

    '''        # B3F -> BRAIN

        group_context_text += (
            "\\n\\n"
            + b3f_routing_context_text
        )

''',

    "Routing context to Brain",
)


bot = insert_before(
    bot,

    '''        # =====================================================
        # 2.11B2 WORLD EVIDENCE -> WRITER
''',

    '''        # B3F -> WRITER

        writer_context += (
            "\\n\\n"
            + b3f_routing_context_text
        )

''',

    "Routing context to Writer",
)


bot = insert_before(
    bot,

    '''        if (
            participation_decision.action
            != "join"
        ):
''',

    '''        # =================================================
        # B3F PARTICIPATION ROUTING BOOST
        # =================================================

        participation_routing_boost = (
            apply_participation_routing_boost(
                participation_decision,
                perception=perception,
                channel_snapshot=channel_snapshot,
                current_user_id=user_id,
            )
        )

        if participation_routing_boost.changed:

            print(
                format_participation_boost_debug(
                    participation_routing_boost
                )
            )

''',

    "Participation routing boost",
)


bot = insert_before(
    bot,

    '''    # =====================================================
    # RESPONSE LOCK
''',

    '''    # =====================================================
    # B3F FINAL ROUTING DIAGNOSTIC
    # =====================================================

    if directly_addressed:

        final_route_mode = (
            "direct"
        )

    elif conversation_continuation:

        final_route_mode = (
            "continuation"
        )

    elif autonomous_participation:

        final_route_mode = (
            "participation"
        )

    else:

        final_route_mode = (
            "silent"
        )

    print(
        "[ROUTING FINAL] "
        f"user={username} "
        f"mode={final_route_mode} "
        f"direct={directly_addressed} "
        f"continuation={conversation_continuation} "
        f"participation={autonomous_participation}"
    )

''',

    "Final routing diagnostic",
)


syntax_check(
    bot,
    "bot.py",
)

syntax_check(
    part,
    "participation.py",
)


stamp = (
    datetime.now()
    .strftime(
        "%Y%m%d-%H%M%S"
    )
)


bot_backup = Path(
    f"bot.py.before-B3F-{stamp}.bak"
)

part_backup = Path(
    f"participation.py.before-B3F-{stamp}.bak"
)


shutil.copy2(
    BOT,
    bot_backup,
)

shutil.copy2(
    PART,
    part_backup,
)


print(
    f"[BACKUP] {bot_backup}"
)

print(
    f"[BACKUP] {part_backup}"
)


bot_tmp = Path(
    "bot.py.B3F.tmp"
)

part_tmp = Path(
    "participation.py.B3F.tmp"
)


bot_tmp.write_text(
    bot,
    encoding="utf-8",
)

part_tmp.write_text(
    part,
    encoding="utf-8",
)


bot_tmp.replace(
    BOT
)

part_tmp.replace(
    PART
)


print(
    "[OK] bot.py written"
)

print(
    "[OK] participation.py written"
)


installed = BOT.read_text(
    encoding="utf-8"
)

installed_part = PART.read_text(
    encoding="utf-8"
)


for marker in (
    f'BOT_VERSION = "{TARGET_BOT}"',
    "ROUTING_HARDENING_VERSION",
    "Stretched Evil/Evilnae Vocatives: ACTIVE",
    "Reply-To Priority Routing: ACTIVE",
    "Reference Resolver v2: ACTIVE",
    "Participation Routing Boost: ACTIVE",
    "harden_perception_addressing(",
    "build_routing_context(",
    "apply_participation_routing_boost(",
    '"[ROUTING FINAL] "',
    "ACTIVE_CONVERSATION_CONTEXT_GAP = 8",
):

    if marker not in installed:

        fail(
            f"Verification missing: {marker}"
        )


if (
    f'PARTICIPATION_VERSION = "{TARGET_PART}"'
    not in installed_part
):

    fail(
        "Participation version verification failed"
    )


print("")
print(
    "============================================"
)
print(
    "EVILNAE B3F ROUTING HARDENING COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: {TARGET_BOT}"
)

print(
    "Routing Hardening: 1.0"
)

print(
    f"Participation: {TARGET_PART}"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] Stretched Evil/Evilnae recognition"
)

print(
    "  [✓] Reply-To priority"
)

print(
    "  [✓] Direct vs third-person separation"
)

print(
    "  [✓] Reference / Ellipsis v2 hints"
)

print(
    "  [✓] Group thread scan depth 8"
)

print(
    "  [✓] Participation routing correction"
)

print(
    "  [✓] No forced reply for 'Arme Evil'"
)

print(
    "  [✓] Final routing logs"
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
    "python routing_hardening.py"
)

print(
    "python -m py_compile "
    "bot.py routing_hardening.py response_quality.py "
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
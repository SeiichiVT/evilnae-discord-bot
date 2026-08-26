from pathlib import Path
from datetime import datetime

import ast
import shutil


BOT = Path(
    "bot.py"
)

ACTIONS = Path(
    "discord_actions.py"
)


EXPECTED_BOT = (
    "2.14.0-routing-b3f"
)

TARGET_BOT = (
    "2.15.0-discord-actions-b3g"
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
            block
            +
            marker,
            1
        )
    )


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

    ok(
        label
    )

    return (
        text.replace(
            marker,
            marker
            +
            block,
            1
        )
    )


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


print(
    "[B3G DISCORD ACTIONS PACK] starting..."
)


for path in (
    BOT,
    ACTIONS,
):

    if not path.exists():

        fail(
            f"{path} missing"
        )


bot = BOT.read_text(
    encoding="utf-8"
)

actions = ACTIONS.read_text(
    encoding="utf-8"
)


if (
    'DISCORD_ACTIONS_VERSION = "1.0"'
    not in actions
):

    fail(
        "discord_actions.py is not v1.0"
    )


syntax_check(
    actions,
    "discord_actions.py"
)


if (
    f'BOT_VERSION = "{TARGET_BOT}"'
    in bot
):

    raise SystemExit(
        "B3G already installed."
    )


if (
    f'BOT_VERSION = "{EXPECTED_BOT}"'
    not in bot
):

    fail(
        "Unexpected bot version. "
        f"Expected {EXPECTED_BOT}."
    )


for marker in (
    "ROUTING_HARDENING_VERSION",
    "OUTPUT_QUALITY_VERSION",
    "Response Reliability v1: ACTIVE",
    "apply_evilnae_emote_layer",
):

    if marker not in bot:

        fail(
            "Previous feature missing: "
            f"{marker}"
        )


ok(
    "B3F base detected"
)


# =========================================================
# IMPORT
# =========================================================

bot = insert_before(

    bot,

    "from routing_hardening import (\n",

    '''from discord_actions import (
    DISCORD_ACTIONS_VERSION,
    prepare_application_reaction,
    register_application_reaction,
    apply_text_emote_cooldown,
    format_application_reaction_debug,
    format_text_emote_cooldown_debug,
)

''',

    "Discord Actions import"
)


# =========================================================
# VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT}"',

    f'BOT_VERSION = "{TARGET_BOT}"',

    "Bot version"
)


# =========================================================
# STARTUP
# =========================================================

bot = insert_after(

    bot,

    '''    print(
        "Maximum One Evilnae Emote Per Reply: ACTIVE"
    )

''',

    '''    print(
        f"Discord Actions v{DISCORD_ACTIONS_VERSION}: ACTIVE"
    )

    print(
        "Application Emoji Reactions Only: ACTIVE"
    )

    print(
        "Unicode Reaction Fallback: DISABLED"
    )

    print(
        "Thumbs-Up Fallback: DISABLED"
    )

    print(
        "Reaction Cooldowns: ACTIVE"
    )

    print(
        "Text Emote Cooldowns: ACTIVE"
    )

''',

    "Discord Actions startup status"
)


# =========================================================
# REACTION PATH
# =========================================================

old_reaction = '''        if (
            agency_result.action
            ==
            ACTION_REACT
        ):

            reaction = (
                agency_result.reaction
                or
                "👍"
            )

            try:

                await message.add_reaction(
                    reaction
                )

                register_channel_message(
                    is_bot=True
                )

                print(
                    "[AGENCY REACTION] "
                    f"user={username} "
                    f"reaction={reaction!r}"
                )

            except Exception as error:

                print(
                    "[AGENCY REACTION ERROR] "
                    f"user={username} "
                    f"error="
                    f"{type(error).__name__}: "
                    f"{error}"
                )

            return
'''


new_reaction = '''        if (
            agency_result.action
            ==
            ACTION_REACT
        ):

            application_reaction = (
                prepare_application_reaction(

                    user_text=(
                        user_text
                    ),

                    suggested_reaction=(
                        agency_result.reaction
                    ),

                    channel_id=(
                        channel_id
                    )
                )
            )

            print(
                format_application_reaction_debug(
                    application_reaction
                )
            )

            if not (
                application_reaction.allowed
                and
                application_reaction.rendered
                and
                application_reaction.semantic
            ):

                print(
                    "[REACTION SILENT] "
                    f"user={username} "
                    f"reason={application_reaction.reason}"
                )

                return

            try:

                reaction_value = (
                    discord.PartialEmoji.from_str(
                        application_reaction.rendered
                    )
                )

                await message.add_reaction(
                    reaction_value
                )

                register_application_reaction(

                    channel_id=(
                        channel_id
                    ),

                    semantic=(
                        application_reaction.semantic
                    )
                )

                register_channel_message(
                    is_bot=True
                )

                print(
                    "[AGENCY APPLICATION REACTION] "
                    f"user={username} "
                    f"semantic="
                    f"{application_reaction.semantic!r} "
                    f"reaction="
                    f"{application_reaction.rendered!r}"
                )

            except Exception as error:

                print(
                    "[AGENCY REACTION ERROR] "
                    f"user={username} "
                    f"semantic="
                    f"{application_reaction.semantic!r} "
                    f"error="
                    f"{type(error).__name__}: "
                    f"{error}"
                )

            return
'''


bot = replace_once(

    bot,
    old_reaction,
    new_reaction,

    "Application reaction path"
)


# =========================================================
# TEXT EMOTE COOLDOWN
# =========================================================

emote_log_marker = '''        print(
            format_evilnae_emote_debug(
                evilnae_emote_result
            )
        )
'''


emote_cooldown_block = '''        (
            answer,
            text_emote_cooldown_result
        ) = apply_text_emote_cooldown(

            answer,
            evilnae_emote_result,

            channel_id=(
                channel_id
            )
        )

        print(
            format_text_emote_cooldown_debug(
                text_emote_cooldown_result
            )
        )

'''


bot = insert_before(

    bot,
    emote_log_marker,
    emote_cooldown_block,

    "Text emote cooldown integration"
)


# =========================================================
# SYNTAX
# =========================================================

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
    f"bot.py.before-B3G-{stamp}.bak"
)


shutil.copy2(
    BOT,
    backup
)


print(
    f"[BACKUP] {backup}"
)


# =========================================================
# WRITE
# =========================================================

tmp = Path(
    "bot.py.B3G.tmp"
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

installed = BOT.read_text(
    encoding="utf-8"
)


required = (

    f'BOT_VERSION = "{TARGET_BOT}"',

    "DISCORD_ACTIONS_VERSION",

    "prepare_application_reaction",

    "register_application_reaction",

    "apply_text_emote_cooldown",

    "Application Emoji Reactions Only: ACTIVE",

    "Unicode Reaction Fallback: DISABLED",

    "Thumbs-Up Fallback: DISABLED",

    "Reaction Cooldowns: ACTIVE",

    "Text Emote Cooldowns: ACTIVE",

    "[AGENCY APPLICATION REACTION]",

    "[REACTION SILENT]",

    "discord.PartialEmoji.from_str",
)


for marker in required:

    if marker not in installed:

        fail(
            "Verification missing: "
            f"{marker}"
        )


print("")
print(
    "============================================"
)
print(
    "EVILNAE B3G DISCORD ACTIONS COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: {TARGET_BOT}"
)

print(
    "Discord Actions: 1.0"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] Evilnae Application Emoji reactions"
)

print(
    "  [✓] No Unicode reaction output"
)

print(
    "  [✓] No thumbs-up fallback"
)

print(
    "  [✓] Semantic reaction selection"
)

print(
    "  [✓] Serious-context reaction suppression"
)

print(
    "  [✓] Negative-context fire protection"
)

print(
    "  [✓] Reaction cooldowns"
)

print(
    "  [✓] Text emote cooldowns"
)

print(
    "  [✓] Repeated wave suppression"
)

print("")

print(
    "Character / Lore / Preferences: UNCHANGED"
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
    "python discord_actions.py"
)

print(
    "python -m py_compile "
    "bot.py discord_actions.py routing_hardening.py "
    "response_quality.py participation.py evilnae_emotes.py "
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
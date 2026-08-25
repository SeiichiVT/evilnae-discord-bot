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

EMOTE_PATH = Path(
    "evilnae_emotes.py"
)


EXPECTED_BOT_VERSION = (
    "2.11.8-human-rhythm-b3b1b1"
)

TARGET_BOT_VERSION = (
    "2.11.9-evilnae-emotes-v1"
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
    "[EVILNAE EMOTES v1 INSTALLER] "
    "starting..."
)


if not BOT_PATH.exists():

    fail(
        "bot.py missing"
    )


if not EMOTE_PATH.exists():

    fail(
        "evilnae_emotes.py missing"
    )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)


emotes = EMOTE_PATH.read_text(
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
        "Evilnae Emotes v1 already installed."
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
    'EVILNAE_EMOTE_VERSION = "1.0"'
    not in emotes
):

    fail(
        "evilnae_emotes.py is not v1.0"
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

    f"bot.py.before-evilnae-emotes-v1-"
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
# 1. IMPORT
# =========================================================

old = '''from voice_memory import (
    VOICE_MEMORY_VERSION,
    register_voice_feedback,
    format_voice_memory_debug,
)
'''


new = '''from voice_memory import (
    VOICE_MEMORY_VERSION,
    register_voice_feedback,
    format_voice_memory_debug,
)

from evilnae_emotes import (
    EVILNAE_EMOTE_VERSION,
    load_application_emojis,
    apply_evilnae_emote_layer,
    format_evilnae_emote_debug,
)
'''


bot = replace_once(

    bot,
    old,
    new,

    "Evilnae Emote imports"
)


# =========================================================
# 2. VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"',

    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',

    "Bot version"
)


# =========================================================
# 3. LOAD APP EMOJIS ON READY
#
# Direkt in on_ready,
# bevor Startup-Status ausgegeben wird.
# =========================================================

old = '''@bot.event
async def on_ready():

    global initiative_task
    global initiative_target_channel_id

    apply_time_decay()
'''


new = '''@bot.event
async def on_ready():

    global initiative_task
    global initiative_target_channel_id

    apply_time_decay()

    # -----------------------------------------------------
    # EVILNAE APPLICATION EMOJIS
    # -----------------------------------------------------

    await load_application_emojis(
        bot
    )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Load Evilnae Application Emojis"
)


# =========================================================
# 4. STARTUP STATUS
# =========================================================

old = '''    print(
        "No Forced Completion: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


new = '''    print(
        "No Forced Completion: ACTIVE"
    )

    print(
        f"Evilnae Emote Layer v"
        f"{EVILNAE_EMOTE_VERSION}: ACTIVE"
    )

    print(
        "Evilnae Application Emojis Only: ACTIVE"
    )

    print(
        "Maximum One Evilnae Emote Per Reply: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


bot = replace_once(

    bot,
    old,
    new,

    "Evilnae Emote startup status"
)


# =========================================================
# 5. WRITER PROMPT
#
# Writer soll bewusst KEINE Emojis mehr erzeugen.
#
# Das macht der finale Emote-Layer.
# =========================================================

old = '''==================================================
CUSTOM EMOTES
==================================================

Discord-Emote-Namen
sind keine Tatsachen.
'''


new = '''==================================================
CUSTOM EMOTES
==================================================

Discord-Emote-Namen
in Nachrichten des Users
sind keine Tatsachen.

WICHTIG:

Schreibe in Evilnaes eigener Antwort
KEINE Unicode-Emojis
und KEINE Discord-Custom-Emotes.

Also nicht:

😂
😭
💀
😈
❤️

und auch nicht:

<:irgendein_emote:123>

Evilnaes eigene Emotes werden
nach allen Writer-/Voice-/Guard-Schritten
separat durch den
Evilnae Emote Layer ausgewählt.

Konzentriere dich nur
auf den eigentlichen Text.
'''


bot = replace_once(

    bot,
    old,
    new,

    "Writer no-emoji rule"
)


# =========================================================
# 6. FINAL EMOTE LAYER
#
# Direkt VOR Context Freshness + Send.
#
# Damit kann danach:
#
# - Writer
# - Repair
# - Qwen
# - Naturalness
# - Expression Guard
#
# nichts mehr am Emote verändern.
# =========================================================

marker = '''        # =================================================
        # 12. CONTEXT FRESHNESS + SEND
'''


block = '''        # =================================================
        # 11.9 EVILNAE APPLICATION EMOTE LAYER
        #
        # Der eigentliche Text ist jetzt vollständig fertig.
        #
        # Ab hier:
        #
        # - Unicode-Emojis raus
        # - fremde Discord-Emotes raus
        # - höchstens EIN passendes Evilnae-App-Emote
        # - bei neutralen / ernsten Antworten auch KEINS
        # =================================================

        (
            answer,
            evilnae_emote_result
        ) = apply_evilnae_emote_layer(

            answer,

            user_text=(
                user_text
            ),

            mood=(
                current_mood
            ),

            inner_state=(
                current_inner_state
            ),

            is_hanae=(
                is_hanae
            )
        )

        print(
            format_evilnae_emote_debug(
                evilnae_emote_result
            )
        )

''' + marker


bot = replace_once(

    bot,
    marker,
    block,

    "Final Evilnae Emote Layer"
)


# =========================================================
# 7. SAFETY FALLBACKS
#
# Diese zwei Antworten laufen VOR Writer/Qwen.
#
# Deshalb entfernen wir auch dort normale Emojis,
# damit Evilnae wirklich konsequent nur ihre
# eigenen Application Emojis benutzt.
# =========================================================

old = '''            await message.reply(
                "darüber reden wir lieber nicht 😭",
                mention_author=False
            )
'''


new = '''            await message.reply(
                "darüber reden wir lieber nicht.",
                mention_author=False
            )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Blocked-word fallback Unicode cleanup"
)


old = '''            await message.reply(
                "hey, das klingt grad ernst. "
                "bitte hol dir jemanden dazu, "
                "mit dem du direkt reden kannst ❤️",
                mention_author=False
            )
'''


new = '''            await message.reply(
                "hey, das klingt grad ernst. "
                "bitte hol dir jemanden dazu, "
                "mit dem du direkt reden kannst.",
                mention_author=False
            )
'''


bot = replace_once(

    bot,
    old,
    new,

    "Crisis fallback Unicode cleanup"
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
    "bot.py.evilnae-emotes-v1.tmp"
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

    "EVILNAE_EMOTE_VERSION",

    "load_application_emojis",

    "apply_evilnae_emote_layer",

    "[EVILNAE APPLICATION EMOTE LAYER]",

    "Evilnae Emote Layer v",

    "Evilnae Application Emojis Only: ACTIVE",

    "Maximum One Evilnae Emote Per Reply: ACTIVE",
]


missing = [

    item

    for item
    in required

    if item not in installed
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
    "EVILNAE EMOTES v1 INSTALL COMPLETE"
)

print(
    "============================================"
)

print(
    f"Bot Version: "
    f"{TARGET_BOT_VERSION}"
)

print(
    "Emote Layer: 1.0"
)

print("")

print(
    "Installed:"
)

print(
    "  [✓] Evilnae Application Emoji Loader"
)

print(
    "  [✓] Discord API + ID fallback"
)

print(
    "  [✓] Unicode Emoji Removal"
)

print(
    "  [✓] Foreign Custom Emoji Removal"
)

print(
    "  [✓] Semantic Evilnae Emote Selection"
)

print(
    "  [✓] Serious Context -> No Emote"
)

print(
    "  [✓] Maximum One Emote"
)

print(
    "  [✓] Writer/Qwen Cannot Choose Emote"
)

print(
    "  [✓] User Emotes Still Understood"
)

print("")

print(
    f"Backup:"
)

print(
    f"  {backup}"
)

print("")

print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py evilnae_emotes.py "
    "natural_response.py brain.py "
    "curiosity.py self_model.py "
    "agency.py conversation_world.py "
    "understanding.py naturalness.py "
    "coherence.py expression.py "
    "perception.py inner_state.py "
    "local_voice.py"
)

print(
    "python evilnae_emotes.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
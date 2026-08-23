from pathlib import Path
from datetime import datetime
import re
import shutil
import sys


# =========================================================
# PATHS
# =========================================================

BOT_PATH = Path(
    "bot.py"
)

GITIGNORE_PATH = Path(
    ".gitignore"
)


# =========================================================
# HELPERS
# =========================================================

def fail(
    message
):

    print(
        f"[INSTALL ERROR] {message}"
    )

    sys.exit(
        1
    )


def replace_once(
    text,
    old,
    new,
    label
):

    if new in text:

        print(
            f"[SKIP] {label} already installed"
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
            f"expected marker exactly once, "
            f"found {count}"
        )

    print(
        f"[OK] {label}"
    )

    return text.replace(
        old,
        new,
        1
    )


# =========================================================
# CHECK BOT
# =========================================================

if not BOT_PATH.exists():

    fail(
        "bot.py not found. "
        "Run this script inside "
        "the Evilnae project folder."
    )


bot = (
    BOT_PATH.read_text(
        encoding="utf-8"
    )
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
    f"bot.py.before-local-voice-{stamp}.bak"
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

old_imports = '''from participation import (
    PARTICIPATION_VERSION,
    run_participation_brain,
    format_participation_for_writer,
    format_participation_debug,
)
'''


new_imports = old_imports + '''
from local_voice import (
    LOCAL_VOICE_VERSION,
    LOCAL_VOICE_ENABLED,
    humanize_evilnae_response,
    format_local_voice_debug,
    warm_local_voice,
)

from voice_memory import (
    VOICE_MEMORY_VERSION,
    register_voice_feedback,
    format_voice_memory_debug,
)
'''


bot = replace_once(
    bot,
    old_imports,
    new_imports,
    "Local Voice imports"
)


# =========================================================
# 2. BOT VERSION
# =========================================================

version_pattern = (
    r'BOT_VERSION\s*=\s*"[^"]+"'
)

if not re.search(
    version_pattern,
    bot
):

    fail(
        "BOT_VERSION not found"
    )


bot = re.sub(

    version_pattern,

    'BOT_VERSION = "2.10.0-local-voice"',

    bot,

    count=1
)


print(
    "[OK] Bot version -> "
    "2.10.0-local-voice"
)


# =========================================================
# 3. VOICE FEEDBACK PAIR HELPER
# =========================================================

ready_marker = '''# =========================================================
# READY
# =========================================================
'''


helper_block = '''# =========================================================
# LOCAL VOICE FEEDBACK PAIR
#
# Findet die letzte Evilnae-Antwort im Channel
# und die User-Nachricht, auf die sie reagiert hat.
#
# Dadurch kann auch jemand anderes sagen:
#
# "das klang wie ein Bot"
#
# oder:
#
# "das klang menschlich"
# =========================================================

def find_latest_voice_training_pair(
    channel_snapshot
):

    if not channel_snapshot:

        return None

    # -----------------------------------------------------
    # Die aktuelle User-Nachricht wurde
    # bereits in den Channel Context geschrieben.
    # -----------------------------------------------------

    previous_items = (
        channel_snapshot[:-1]
    )

    bot_index = None

    bot_item = None

    # -----------------------------------------------------
    # LETZTE EVILNAE-NACHRICHT
    # -----------------------------------------------------

    for index in range(
        len(previous_items) - 1,
        -1,
        -1
    ):

        item = (
            previous_items[
                index
            ]
        )

        if (
            item.get(
                "type"
            )
            != "bot"
        ):

            continue

        # -------------------------------------------------
        # Initiative hat nicht zwingend
        # eine konkrete User-Nachricht als Ursprung.
        # -------------------------------------------------

        if (
            item.get(
                "origin"
            )
            == "initiative"
        ):

            return None

        bot_index = (
            index
        )

        bot_item = (
            item
        )

        break

    if bot_item is None:

        return None

    evilnae_response = str(
        bot_item.get(
            "content",
            ""
        )
    ).strip()

    if not evilnae_response:

        return None

    # -----------------------------------------------------
    # USER-NACHRICHT VOR DER EVILNAE-ANTWORT
    # -----------------------------------------------------

    for index in range(
        bot_index - 1,
        -1,
        -1
    ):

        item = (
            previous_items[
                index
            ]
        )

        if (
            item.get(
                "type"
            )
            != "user"
        ):

            continue

        user_message = str(
            item.get(
                "content",
                ""
            )
        ).strip()

        if not user_message:

            continue

        return {

            "username":
                str(
                    item.get(
                        "username",
                        "unknown"
                    )
                ),

            "user_message":
                user_message,

            "evilnae_response":
                evilnae_response
        }

    return None


'''


if (
    "def find_latest_voice_training_pair("
    not in bot
):

    if ready_marker not in bot:

        fail(
            "READY marker not found"
        )

    bot = bot.replace(
        ready_marker,
        helper_block
        + ready_marker,
        1
    )

    print(
        "[OK] Voice feedback pair helper"
    )

else:

    print(
        "[SKIP] Voice feedback pair helper "
        "already installed"
    )


# =========================================================
# 4. STARTUP WARMUP
# =========================================================

old_ready_decay = '''    apply_time_decay()
'''


new_ready_decay = '''    apply_time_decay()

    # -----------------------------------------------------
    # LOCAL VOICE WARMUP
    #
    # Qwen wird im Hintergrund vorgeladen.
    # Discord-Startup wird nicht blockiert.
    # -----------------------------------------------------

    if LOCAL_VOICE_ENABLED:

        asyncio.create_task(
            warm_local_voice()
        )
'''


ready_pos = (
    bot.find(
        "async def on_ready():"
    )
)

if ready_pos == -1:

    fail(
        "on_ready not found"
    )


decay_pos = (
    bot.find(
        old_ready_decay,
        ready_pos
    )
)


if decay_pos == -1:

    if (
        "LOCAL VOICE WARMUP"
        not in bot
    ):

        fail(
            "apply_time_decay inside "
            "on_ready not found"
        )

else:

    ready_area = (
        bot[
            ready_pos:
            ready_pos + 2500
        ]
    )

    if (
        "LOCAL VOICE WARMUP"
        not in ready_area
    ):

        bot = (
            bot[:decay_pos]
            + new_ready_decay
            + bot[
                decay_pos
                + len(
                    old_ready_decay
                ):
            ]
        )

        print(
            "[OK] Local Voice startup warmup"
        )

    else:

        print(
            "[SKIP] Local Voice startup warmup "
            "already installed"
        )


# =========================================================
# 5. STARTUP DEBUG
# =========================================================

social_print = '''    print(
        "Social Actions: ACTIVE"
    )
'''


voice_print = social_print + '''
    print(
        f"Local Voice v{LOCAL_VOICE_VERSION}: "
        f"{'ACTIVE' if LOCAL_VOICE_ENABLED else 'DISABLED'}"
    )

    print(
        f"Voice Memory v{VOICE_MEMORY_VERSION}: ACTIVE"
    )

    print(
        format_local_voice_debug()
    )

    print(
        format_voice_memory_debug()
    )
'''


bot = replace_once(
    bot,
    social_print,
    voice_print,
    "Startup Local Voice debug"
)


# =========================================================
# 6. VOICE FEEDBACK LEARNING
# =========================================================

feedback_marker = '''    if feedback_safe_for_learning:

        feedback_detected = (
'''


feedback_block = '''    # =====================================================
    # VOICE FEEDBACK LEARNING
    #
    # Nur explizite Voice-Signale werden gespeichert.
    #
    # Beispiele:
    #
    # "das klingt wie ein Bot"
    # "das klang richtig menschlich"
    #
    # Normale Gespräche ändern nichts.
    # =====================================================

    voice_feedback_saved = False

    if feedback_safe_for_learning:

        voice_pair = (
            find_latest_voice_training_pair(
                channel_snapshot
            )
        )

        if voice_pair:

            voice_feedback_saved = (
                register_voice_feedback(

                    username=username,

                    user_message=(
                        voice_pair[
                            "user_message"
                        ]
                    ),

                    evilnae_response=(
                        voice_pair[
                            "evilnae_response"
                        ]
                    ),

                    feedback_text=(
                        feedback_text
                    )
                )
            )

            if voice_feedback_saved:

                print(
                    "[VOICE FEEDBACK] "
                    f"user={username} "
                    "saved=yes"
                )

    if feedback_safe_for_learning:

        feedback_detected = (
'''


bot = replace_once(
    bot,
    feedback_marker,
    feedback_block,
    "Voice feedback learning"
)


# =========================================================
# 7. LOCAL VOICE BETWEEN WRITER AND SEND
# =========================================================

expression_marker = '''        # =================================================
        # EXPRESSION LOGGING
        # =================================================
'''


voice_integration = '''        # =================================================
        # 11.5 LOCAL VOICE / HUMANIZATION
        #
        # OpenAI hat:
        #
        # - Inhalt
        # - Wissen
        # - Brain Decision
        # - Inner State
        #
        # bereits festgelegt.
        #
        # Qwen darf nur die sprachliche Oberfläche
        # natürlicher machen.
        #
        # Danach läuft erneut Evilnaes Hard Guard.
        # =================================================

        if autonomous_participation:

            voice_conversation_mode = (
                "participation"
            )

        elif conversation_continuation:

            voice_conversation_mode = (
                "continuation"
            )

        else:

            voice_conversation_mode = (
                "direct"
            )

        original_writer_answer = (
            answer
        )

        try:

            voice_result = (
                await humanize_evilnae_response(

                    user_message=(
                        user_text
                    ),

                    draft=(
                        answer
                    ),

                    conversation_mode=(
                        voice_conversation_mode
                    ),

                    response_goal=(
                        decision.response_goal
                        or
                        decision.intent
                    ),

                    allow_question=(
                        decision.ask_question
                    ),

                    inner_state_guidance=(
                        inner_state_guidance
                    ),

                    recent_evilnae_messages=(
                        state.history
                        .recent_evilnae_messages
                    )
                )
            )

            voice_candidate = (
                clean_generated_answer(
                    voice_result.output_text
                )
            )

            voice_candidate = (
                enforce_permanent_expression_bans(
                    voice_candidate
                )
            )

            # ---------------------------------------------
            # FINAL EVILNAE HARD GUARD
            #
            # Der lokale Writer darf weiterhin nicht:
            #
            # - fair benutzen
            # - unerlaubte Fragen erzeugen
            # - unbekannte aktuelle Fakten behaupten
            # - Füllantwort erzeugen
            # - Participation falsch beginnen
            # ---------------------------------------------

            voice_guard_reasons = (
                get_writer_violation_reasons(

                    answer=(
                        voice_candidate
                    ),

                    decision=(
                        decision
                    ),

                    autonomous_participation=(
                        autonomous_participation
                    )
                )
            )

            if voice_guard_reasons:

                print(
                    "[LOCAL VOICE REJECTED] "
                    f"user={username} "
                    f"reasons="
                    f"{voice_guard_reasons}"
                )

                answer = (
                    original_writer_answer
                )

            elif voice_candidate:

                answer = (
                    voice_candidate
                )

        except Exception as error:

            print(
                "[LOCAL VOICE INTEGRATION ERROR] "
                f"user={username} "
                f"error="
                f"{type(error).__name__}: "
                f"{error}"
            )

            # ---------------------------------------------
            # Qwen darf den Hauptbot niemals kaputt machen.
            # ---------------------------------------------

            answer = (
                original_writer_answer
            )

'''


if (
    "# 11.5 LOCAL VOICE / HUMANIZATION"
    not in bot
):

    marker_count = (
        bot.count(
            expression_marker
        )
    )

    if marker_count != 1:

        fail(
            "Expression logging marker "
            f"expected once, found "
            f"{marker_count}"
        )

    bot = bot.replace(
        expression_marker,
        voice_integration
        + expression_marker,
        1
    )

    print(
        "[OK] Local Voice writer integration"
    )

else:

    print(
        "[SKIP] Local Voice writer integration "
        "already installed"
    )


# =========================================================
# WRITE BOT
# =========================================================

BOT_PATH.write_text(
    bot,
    encoding="utf-8"
)

print(
    "[WRITE] bot.py updated"
)


# =========================================================
# GITIGNORE
# =========================================================

ignore_lines = []

if GITIGNORE_PATH.exists():

    ignore_lines = (
        GITIGNORE_PATH
        .read_text(
            encoding="utf-8"
        )
        .splitlines()
    )


for entry in [
    "voice_memory.json",
    "*.bak",
]:

    if entry not in ignore_lines:

        ignore_lines.append(
            entry
        )

        print(
            f"[OK] .gitignore + {entry}"
        )


GITIGNORE_PATH.write_text(

    "\n".join(
        ignore_lines
    ).rstrip()
    + "\n",

    encoding="utf-8"
)


# =========================================================
# DONE
# =========================================================

print("")
print(
    "============================================"
)

print(
    "LOCAL VOICE INSTALL COMPLETE"
)

print(
    "============================================"
)

print(
    "Next:"
)

print(
    "python -m py_compile "
    "bot.py "
    "local_voice.py "
    "voice_memory.py "
    "perception.py "
    "conversation_state.py "
    "brain.py "
    "social_actions.py "
    "expression.py "
    "inner_state.py "
    "initiative.py "
    "reflection.py "
    "participation.py"
)

print(
    "python bot.py"
)
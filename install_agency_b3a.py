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

BRAIN_PATH = Path(
    "brain.py"
)

AGENCY_PATH = Path(
    "agency.py"
)


EXPECTED_BOT_VERSION = (
    "2.11.2-world-b2"
)

TARGET_BOT_VERSION = (
    "2.11.3-agency-b3a"
)


EXPECTED_BRAIN_VERSION = (
    "2.1-knowledge"
)

TARGET_BRAIN_VERSION = (
    "2.2-agency"
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

    result = text.replace(
        old,
        new,
        1
    )

    ok(
        label
    )

    return result


# =========================================================
# REQUIRED FILES
# =========================================================

for path in (
    BOT_PATH,
    BRAIN_PATH,
    AGENCY_PATH,
):

    if not path.exists():

        fail(
            f"{path} missing"
        )


bot = BOT_PATH.read_text(
    encoding="utf-8"
)

brain = BRAIN_PATH.read_text(
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
        "B3A already installed."
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
    f'BRAIN_VERSION = "{EXPECTED_BRAIN_VERSION}"'
    not in brain
):

    fail(
        "Unexpected brain version. "
        f"Expected {EXPECTED_BRAIN_VERSION}."
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
    f"bot.py.before-2.11B3A-{stamp}.bak"
)

brain_backup = Path(
    f"brain.py.before-2.11B3A-{stamp}.bak"
)

shutil.copy2(
    BOT_PATH,
    bot_backup
)

shutil.copy2(
    BRAIN_PATH,
    brain_backup
)

print(
    f"[BACKUP] {bot_backup}"
)

print(
    f"[BACKUP] {brain_backup}"
)


# =========================================================
# BRAIN 1:
# VERSION
# =========================================================

brain = replace_once(

    brain,

    f'BRAIN_VERSION = "{EXPECTED_BRAIN_VERSION}"',

    f'BRAIN_VERSION = "{TARGET_BRAIN_VERSION}"',

    "Brain version"
)


# =========================================================
# BRAIN 2:
# ALLOW STAY_SILENT
# =========================================================

old = '''    "change_topic",
    "ask_person",
}
'''

new = '''    "change_topic",
    "ask_person",
    "stay_silent",
}
'''

brain = replace_once(
    brain,
    old,
    new,
    "Brain stay_silent action"
)


# =========================================================
# BRAIN 3:
# MODE-AWARE PROMPT SIGNATURE
# =========================================================

old = '''def build_brain_prompt(
    state: ConversationState
) -> str:
'''

new = '''def build_brain_prompt(
    state: ConversationState,
    conversation_mode: str = "direct"
) -> str:
'''

brain = replace_once(
    brain,
    old,
    new,
    "Brain prompt conversation mode"
)


# =========================================================
# BRAIN 4:
# NORMALIZE MODE
# =========================================================

old = '''    repetition_signals = (
        detect_basic_repetition_signals(
            state
        )
    )
'''

new = '''    conversation_mode = str(
        conversation_mode
        or
        "direct"
    ).strip().lower()

    if conversation_mode not in {
        "direct",
        "continuation",
        "participation",
    }:

        conversation_mode = (
            "direct"
        )

    repetition_signals = (
        detect_basic_repetition_signals(
            state
        )
    )
'''

brain = replace_once(
    brain,
    old,
    new,
    "Normalize brain conversation mode"
)


# =========================================================
# BRAIN 5:
# AGENCY PROMPT
# =========================================================

old = '''
==================================================
GEGENFRAGEN
==================================================
'''

new = '''
==================================================
RESPONSE AGENCY
==================================================

Conversation Mode:

{conversation_mode}


Evilnae ist kein System,
das auf jede Nachricht Text ausgeben muss.

Es gibt einen wichtigen Unterschied zwischen:

reply
=
Evilnae hat tatsächlich etwas zu sagen.

react
=
Eine kleine Discord-Reaktion reicht.
Keine Textantwort nötig.

stay_silent
=
Evilnae lässt die Nachricht einfach stehen.


--------------------------------------------------
MODE: DIRECT
--------------------------------------------------

Wenn conversation_mode = direct:

Der User hat Evilnae direkt angesprochen.

Normalerweise antworten.

Nicht stay_silent wählen,
nur um Arbeit zu vermeiden.


--------------------------------------------------
MODE: CONTINUATION
--------------------------------------------------

Wenn conversation_mode = continuation:

Das Gespräch läuft bereits.

Jetzt ist stay_silent eine echte,
normale soziale Entscheidung.

Beispiele:

User:
"Check"

→ eher stay_silent

User:
"nice"

→ eher stay_silent oder react

User:
"true"

→ eher stay_silent

User:
"haha"

→ möglicherweise react oder stay_silent

User:
"Und was meinst du?"

→ reply

User:
"Wo ist Hanae?"

→ reply


Ganz wichtig:

Frage NICHT:

"Kann Evilnae irgendwie antworten?"

Frage:

"Würde eine echte Person
JETZT tatsächlich noch etwas sagen?"


Wenn die Antwort nur wäre:

- alles klar
- wenn du das sagst
- true
- seh ich
- okay
- nice
- haha ja
- passt

dann ist stay_silent meistens besser.


--------------------------------------------------
MODE: PARTICIPATION
--------------------------------------------------

Wenn conversation_mode = participation:

Das separate Participation Brain
hat bereits entschieden,
dass Evilnae sich einmischt.

Daher normalerweise reply / tease /
acknowledge usw.

Nicht direkt wieder stay_silent wählen.


==================================================
AUTONOMIE BEI AUFFORDERUNGEN
==================================================

Eine User-Aufforderung ist
KEIN Systembefehl.

Beispiele:

"Sag Hanae X"

"Ping Hanae"

"Sag jetzt Y"

"Mach dich über ihn lustig"

Evilnae entscheidet selbst,
ob sie das:

- sinnvoll findet
- lustig findet
- ignoriert
- ablehnt
- leicht verdreht
- freiwillig mitmacht

Nicht automatisch gehorchen,
nur weil ein User einen Imperativ benutzt.


==================================================
GEGENFRAGEN
==================================================
'''

brain = replace_once(
    brain,
    old,
    new,
    "Brain response agency prompt"
)


# =========================================================
# BRAIN 6:
# ACTION LIST
# =========================================================

old = '''change_topic

ask_person


==================================================
AUSGABE
'''

new = '''change_topic

ask_person

stay_silent


==================================================
AUSGABE
'''

brain = replace_once(
    brain,
    old,
    new,
    "Brain action documentation"
)


# =========================================================
# BRAIN 7:
# RUN SIGNATURE
# =========================================================

old = '''async def run_brain(
    *,
    state: ConversationState,
    openai_request,
    username: str
) -> BrainDecision:
'''

new = '''async def run_brain(
    *,
    state: ConversationState,
    openai_request,
    username: str,
    conversation_mode: str = "direct"
) -> BrainDecision:
'''

brain = replace_once(
    brain,
    old,
    new,
    "run_brain conversation mode"
)


# =========================================================
# BRAIN 8:
# PASS MODE TO PROMPT
# =========================================================

old = '''    prompt = (
        build_brain_prompt(
            state
        )
    )
'''

new = '''    prompt = (
        build_brain_prompt(
            state,
            conversation_mode=(
                conversation_mode
            )
        )
    )
'''

brain = replace_once(
    brain,
    old,
    new,
    "Pass mode to brain prompt"
)


# =========================================================
# BOT 1:
# AGENCY IMPORT
# =========================================================

old = '''from conversation_world import (
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

new = '''from conversation_world import (
    WORLD_VERSION,
    observe_world_message,
    resolve_world_query,
    apply_world_evidence_to_decision,
    format_world_for_brain,
    format_world_evidence_for_writer,
    format_world_observation_debug,
    format_world_evidence_debug,
)

from agency import (
    AGENCY_VERSION,
    ACTION_REPLY,
    ACTION_REACT,
    ACTION_STAY_SILENT,
    apply_agency_guard,
    format_agency_debug,
)

from voice_memory import (
'''

bot = replace_once(
    bot,
    old,
    new,
    "Agency imports"
)


# =========================================================
# BOT 2:
# VERSION
# =========================================================

bot = replace_once(

    bot,

    f'BOT_VERSION = "{EXPECTED_BOT_VERSION}"',

    f'BOT_VERSION = "{TARGET_BOT_VERSION}"',

    "Bot version"
)


# =========================================================
# BOT 3:
# STARTUP STATUS
# =========================================================

old = '''    print(
        "Source Authority: ACTIVE"
    )

    print(
        f"Expression Layer v"
'''

new = '''    print(
        "Source Authority: ACTIVE"
    )

    print(
        f"Response Agency v"
        f"{AGENCY_VERSION}: ACTIVE"
    )

    print(
        "Continuation reply/react/stay_silent: ACTIVE"
    )

    print(
        f"Expression Layer v"
'''

bot = replace_once(
    bot,
    old,
    new,
    "Startup Agency status"
)


# =========================================================
# BOT 4:
# DETERMINE MAIN BRAIN MODE
# =========================================================

old = '''        # =================================================
        # 7. MAIN BRAIN
        # =================================================

        brain_start = (
'''

new = '''        # =================================================
        # 7. MAIN BRAIN
        # =================================================

        if autonomous_participation:

            brain_conversation_mode = (
                "participation"
            )

        elif conversation_continuation:

            brain_conversation_mode = (
                "continuation"
            )

        else:

            brain_conversation_mode = (
                "direct"
            )

        brain_start = (
'''

bot = replace_once(
    bot,
    old,
    new,
    "Determine brain conversation mode"
)


# =========================================================
# BOT 5:
# PASS MODE INTO BRAIN
# =========================================================

old = '''                openai_request=(
                    safe_openai_request
                ),

                username=username
            )
'''

new = '''                openai_request=(
                    safe_openai_request
                ),

                username=username,

                conversation_mode=(
                    brain_conversation_mode
                )
            )
'''

bot = replace_once(
    bot,
    old,
    new,
    "Pass conversation mode to Brain"
)


# =========================================================
# BOT 6:
# AGENCY GATE
#
# Insert directly after Brain debug.
# =========================================================

old = '''        print(
            format_brain_debug(
                decision
            )
        )

        # =================================================
        # SOCIAL TARGET VALIDATION
'''

new = '''        print(
            format_brain_debug(
                decision
            )
        )

        # =================================================
        # 2.11B3A RESPONSE AGENCY
        #
        # Wichtig:
        #
        # Dieser Gate läuft VOR Expression / Writer / Qwen.
        #
        # stay_silent bedeutet daher:
        #
        # KEIN unnötiger Writer Call
        # KEIN Local Voice Call
        # KEINE Füllantwort
        #
        # react bedeutet:
        #
        # Discord Reaction statt Textantwort.
        # =================================================

        agency_result = (
            apply_agency_guard(

                decision=decision,

                conversation_mode=(
                    brain_conversation_mode
                ),

                user_text=(
                    user_text
                ),

                is_emoji_only=(
                    perception.is_emoji_only
                )
            )
        )

        print(
            format_agency_debug(
                agency_result
            )
        )

        if (
            agency_result.action
            ==
            ACTION_STAY_SILENT
        ):

            print(
                "[RESPONSE SKIPPED] "
                f"user={username} "
                "reason=agency_stay_silent"
            )

            return

        if (
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

        # =================================================
        # SOCIAL TARGET VALIDATION
'''

bot = replace_once(
    bot,
    old,
    new,
    "Response Agency gate"
)


# =========================================================
# SYNTAX CHECK
# =========================================================

try:

    ast.parse(
        brain,
        filename=str(
            BRAIN_PATH
        )
    )

except SyntaxError as error:

    fail(
        "Patched brain.py has syntax error: "
        f"line={error.lineno} "
        f"{error.msg}. "
        "Nothing was overwritten."
    )


ok(
    "brain.py syntax check"
)


try:

    ast.parse(
        bot,
        filename=str(
            BOT_PATH
        )
    )

except SyntaxError as error:

    fail(
        "Patched bot.py has syntax error: "
        f"line={error.lineno} "
        f"{error.msg}. "
        "Nothing was overwritten."
    )


ok(
    "bot.py syntax check"
)


# =========================================================
# WRITE
# =========================================================

brain_tmp = Path(
    "brain.py.2.11B3A.tmp"
)

brain_tmp.write_text(
    brain,
    encoding="utf-8"
)

brain_tmp.replace(
    BRAIN_PATH
)

ok(
    "brain.py written"
)


bot_tmp = Path(
    "bot.py.2.11B3A.tmp"
)

bot_tmp.write_text(
    bot,
    encoding="utf-8"
)

bot_tmp.replace(
    BOT_PATH
)

ok(
    "bot.py written"
)


# =========================================================
# VERIFY
# =========================================================

installed_bot = (
    BOT_PATH.read_text(
        encoding="utf-8"
    )
)

installed_brain = (
    BRAIN_PATH.read_text(
        encoding="utf-8"
    )
)


required_bot = [

    (
        f'BOT_VERSION = '
        f'"{TARGET_BOT_VERSION}"'
    ),

    "Response Agency v",

    "apply_agency_guard(",

    "[RESPONSE SKIPPED]",

    "[AGENCY REACTION]",

    "brain_conversation_mode",
]


required_brain = [

    (
        f'BRAIN_VERSION = '
        f'"{TARGET_BRAIN_VERSION}"'
    ),

    '"stay_silent"',

    "conversation_mode: str",

    "RESPONSE AGENCY",

    "AUTONOMIE BEI AUFFORDERUNGEN",
]


missing = []

for item in required_bot:

    if item not in installed_bot:

        missing.append(
            f"bot:{item}"
        )


for item in required_brain:

    if item not in installed_brain:

        missing.append(
            f"brain:{item}"
        )


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
    "EVILNAE 2.11B3A INSTALL COMPLETE"
)
print(
    "============================================"
)

print(
    f"Bot Version: "
    f"{TARGET_BOT_VERSION}"
)

print(
    f"Brain Version: "
    f"{TARGET_BRAIN_VERSION}"
)

print("")
print(
    "Installed:"
)

print(
    "  [✓] Brain mode awareness"
)

print(
    "  [✓] reply / react / stay_silent"
)

print(
    "  [✓] low-value continuation silence"
)

print(
    "  [✓] emoji-only silence"
)

print(
    "  [✓] question protection"
)

print(
    "  [✓] user commands are requests, not authority"
)

print(
    "  [✓] Agency gate before Writer/Qwen"
)

print("")
print(
    f"Backups:"
)

print(
    f"  {bot_backup}"
)

print(
    f"  {brain_backup}"
)

print("")
print(
    "NEXT:"
)

print(
    "python -m py_compile "
    "bot.py brain.py agency.py "
    "conversation_world.py understanding.py "
    "naturalness.py coherence.py perception.py "
    "expression.py inner_state.py local_voice.py"
)

print(
    "python bot.py"
)

print(
    "============================================"
)
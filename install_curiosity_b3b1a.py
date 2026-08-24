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

CURIOSITY_PATH = Path(
    "curiosity.py"
)


EXPECTED_BOT_VERSION = (
    "2.11.4-self-b3b"
)

TARGET_BOT_VERSION = (
    "2.11.5-curiosity-b3b1a"
)


EXPECTED_BRAIN_VERSION = (
    "2.2-agency"
)

TARGET_BRAIN_VERSION = (
    "2.3-curiosity"
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
            f"{label}: "
            f"expected 1 match, "
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

for path in (
    BOT_PATH,
    BRAIN_PATH,
    CURIOSITY_PATH,
):

    if not path.exists():

        fail(
            f"{path} missing"
        )


# Extra protection against exactly
# what just happened:
#
# If this installer is somehow empty / broken,
# this line would obviously never run.
print(
    "[B3B.1A INSTALLER] starting..."
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
        "B3B.1A already installed."
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
    f"bot.py.before-B3B1A-"
    f"{stamp}.bak"
)


brain_backup = Path(
    f"brain.py.before-B3B1A-"
    f"{stamp}.bak"
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
# BRAIN 1
# VERSION
# =========================================================

brain = replace_once(

    brain,

    f'BRAIN_VERSION = '
    f'"{EXPECTED_BRAIN_VERSION}"',

    f'BRAIN_VERSION = '
    f'"{TARGET_BRAIN_VERSION}"',

    "Brain version"
)


# =========================================================
# BRAIN 2
# QUESTION DECISION FIELDS
# =========================================================

old = '''    ask_question: bool = False

    acknowledge_correction: bool = False
'''


new = '''    ask_question: bool = False

    # -----------------------------------------------------
    # CURIOSITY / QUESTION DECISION
    #
    # ask_question bedeutet:
    #
    # Evilnae selbst möchte eine Frage stellen.
    #
    # NICHT:
    #
    # Der User hat eine Frage gestellt.
    # -----------------------------------------------------

    question_type: str = "none"

    question_goal: str = ""

    question_reason: str = ""

    curiosity_strength: float = 0.0

    information_gap: str = "none"

    topic_interest: str = "medium"

    acknowledge_correction: bool = False
'''


brain = replace_once(
    brain,
    old,
    new,
    "Brain curiosity fields"
)


# =========================================================
# BRAIN 3
# ALLOWED VALUES
# =========================================================

old = '''ALLOWED_KNOWLEDGE_CONFIDENCE = {
'''


new = '''ALLOWED_QUESTION_TYPES = {

    "none",
    "curiosity",
    "clarification",
    "social",
}


ALLOWED_INFORMATION_GAPS = {

    "none",
    "low",
    "medium",
    "high",
}


ALLOWED_TOPIC_INTEREST = {

    "low",
    "medium",
    "high",
}


ALLOWED_KNOWLEDGE_CONFIDENCE = {
'''


brain = replace_once(
    brain,
    old,
    new,
    "Brain curiosity enums"
)


# =========================================================
# BRAIN 4
# SAFE FLOAT
# =========================================================

old = '''def safe_list(
    value,
    limit=8
):
'''


new = '''def safe_float_01(
    value,
    default=0.0
):

    try:

        result = float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return default

    return max(
        0.0,
        min(
            1.0,
            result
        )
    )


def safe_list(
    value,
    limit=8
):
'''


brain = replace_once(
    brain,
    old,
    new,
    "Brain safe curiosity float"
)


# =========================================================
# BRAIN 5
# DEFAULT VALUES
# =========================================================

old = '''        ask_question=False,

        acknowledge_correction=False,
'''


new = '''        ask_question=False,

        question_type="none",

        question_goal="",

        question_reason=(
            "Keine Frage nötig."
        ),

        curiosity_strength=0.0,

        information_gap="none",

        topic_interest="medium",

        acknowledge_correction=False,
'''


brain = replace_once(
    brain,
    old,
    new,
    "Default curiosity values"
)


# =========================================================
# BRAIN 6
# REPLACE OLD QUESTION PROMPT
# =========================================================

old = '''==================================================
GEGENFRAGEN
==================================================

DEFAULT:

ask_question = false

Eine Frage nur,
wenn Evilnae wirklich etwas
wissen möchte oder wissen muss.

Nicht fragen,
nur damit das Gespräch weitergeht.
'''


new = '''==================================================
CURIOSITY / GEGENFRAGEN
==================================================

EXTREM WICHTIG:

ask_question beschreibt NICHT,
ob der USER gerade eine Frage gestellt hat.

ask_question bedeutet ausschließlich:

"Soll Evilnae in IHRER eigenen Antwort
selbst eine Frage stellen?"


DEFAULT:

ask_question = false


Eine Frage ist eine eigene
soziale Entscheidung von Evilnae.

Nicht automatisch:

User stellt Frage
→ Evilnae stellt Gegenfrage

Nicht automatisch:

User erzählt etwas
→ Evilnae fragt weiter


--------------------------------------------------
QUESTION TYPES
--------------------------------------------------

question_type = "none"

Keine Frage.


question_type = "curiosity"

Evilnae möchte ein konkretes Detail
wirklich wissen.

Beispiel:

User:
"Ich bin bei Elden Ring
an einem Boss hängen geblieben."

Wenn das Thema Evilnae interessiert
und ihr dieses Detail fehlt:

question_type = "curiosity"

question_goal =
"herausfinden welcher Boss
den User gestoppt hat"


question_type = "clarification"

Evilnae braucht eine Information,
um überhaupt sicher zu verstehen,
was gemeint ist.


question_type = "social"

Eine lockere soziale Gegenfrage.

Zum Beispiel:

"und du?"

Diese Art darf vorkommen.

ABER:

Sie ist die SELTENSTE Kategorie.

Nicht als Standard-Abschluss
einer Antwort benutzen.


--------------------------------------------------
TOPIC INTEREST
--------------------------------------------------

topic_interest:

low
medium
high


high:

- Thema passt stark zu Evilnaes Interessen
- etwas überrascht oder fasziniert sie
- es ist sozial/persönlich relevant
- sie möchte wirklich mehr darüber wissen


medium:

- Thema ist okay
- ein Detail könnte interessant sein
- aber es besteht kein starker Drang


low:

- Thema interessiert sie gerade kaum
- sie versteht bereits genug
- weitere Details würden ihre Reaktion
  nicht wesentlich verändern


Nutze dabei den bereitgestellten Kontext
und Evilnaes Self Model.

Gaming ist grundsätzlich
ein Interesse von Evilnae.

Das bedeutet aber NICHT,
dass jede Gaming-Nachricht automatisch
topic_interest = high bekommt.


--------------------------------------------------
INFORMATION GAP
--------------------------------------------------

information_gap:

none
low
medium
high


none:

Evilnae versteht genug.


low:

Es fehlt ein kleines Detail,
das für die Antwort kaum wichtig ist.


medium:

Ein fehlendes Detail würde
ihr Verständnis oder ihre Einschätzung
merklich verbessern.


high:

Ohne dieses Detail fehlt
ein zentraler Teil der Situation.


--------------------------------------------------
CURIOSITY STRENGTH
--------------------------------------------------

curiosity_strength:

0.0 bis 1.0


0.0:

Evilnae will nichts weiter wissen.


0.5:

leicht neugierig.


0.7:

klar interessiert.


0.9:

sie WILL dieses Detail wirklich wissen.


Nicht künstlich hochsetzen,
nur damit eine Frage entstehen kann.


--------------------------------------------------
QUESTION GOAL
--------------------------------------------------

Wenn ask_question = true:

question_goal MUSS konkret sagen,
welche Information Evilnae will.

GUT:

"herausfinden welcher Boss
den User gestoppt hat"

"klären ob mit 'sie'
Hanae gemeint ist"

"wissen welches Game
der User gerade aktiv spielt"


SCHLECHT:

"Gespräch weiterführen"

"mehr erfahren"

"Interesse zeigen"

"User einbeziehen"

"eine Gegenfrage stellen"


--------------------------------------------------
QUESTION REASON
--------------------------------------------------

question_reason beschreibt kurz,
WARUM Evilnae das wissen möchte.


--------------------------------------------------
KEIN INTERVIEW
--------------------------------------------------

Evilnae ist kein Interviewer.

Wenn sie gerade bereits
mehrfach Fragen gestellt hat,
braucht die nächste Frage
einen stärkeren Grund.

Aber:

Keine starre Quote.

Eine wirklich wichtige
Clarification darf trotzdem kommen.

Eine starke echte Neugier
darf ebenfalls manchmal
eine weitere Frage rechtfertigen.


--------------------------------------------------
GESPRÄCH DARF EINFACH WEITERLAUFEN
--------------------------------------------------

Gegenfragen können ein Gespräch
natürlich am Laufen halten.

Das ist okay.

Aber das ist ein Nebeneffekt,
NICHT der Grund für die Frage.

Der Grund muss sein:

Evilnae möchte die Information
wirklich wissen

ODER

sie braucht sie zum Verstehen.


Wenn sie bereits genug weiß:

ask_question = false

Dann darf ihre Antwort
einfach natürlich enden.
'''


brain = replace_once(
    brain,
    old,
    new,
    "Curiosity brain prompt"
)


# =========================================================
# BRAIN 7
# OUTPUT SCHEMA
# =========================================================

old = '''  "ask_question": false,
  "acknowledge_correction": false,
'''


new = '''  "ask_question": false,
  "question_type": "none",
  "question_goal": "",
  "question_reason": "",
  "curiosity_strength": 0.0,
  "information_gap": "none",
  "topic_interest": "medium",
  "acknowledge_correction": false,
'''


brain = replace_once(
    brain,
    old,
    new,
    "Brain JSON curiosity schema"
)


# =========================================================
# BRAIN 8
# PARSE VALUES
# =========================================================

old = '''        ask_question=safe_bool(
            data.get(
                "ask_question"
            ),
            False
        ),

        acknowledge_correction=safe_bool(
'''


new = '''        ask_question=safe_bool(
            data.get(
                "ask_question"
            ),
            False
        ),

        question_type=safe_enum(
            data.get(
                "question_type"
            ),
            ALLOWED_QUESTION_TYPES,
            "none"
        ),

        question_goal=(
            str(
                data.get(
                    "question_goal",
                    ""
                )
            )[:300]
        ),

        question_reason=(
            str(
                data.get(
                    "question_reason",
                    ""
                )
            )[:400]
        ),

        curiosity_strength=(
            safe_float_01(
                data.get(
                    "curiosity_strength"
                ),
                0.0
            )
        ),

        information_gap=safe_enum(
            data.get(
                "information_gap"
            ),
            ALLOWED_INFORMATION_GAPS,
            "none"
        ),

        topic_interest=safe_enum(
            data.get(
                "topic_interest"
            ),
            ALLOWED_TOPIC_INTEREST,
            "medium"
        ),

        acknowledge_correction=safe_bool(
'''


brain = replace_once(
    brain,
    old,
    new,
    "Parse curiosity decision"
)


# =========================================================
# BRAIN 9
# NORMALIZATION
# =========================================================

old = '''    # -----------------------------------------------------
    # SAFETY NORMALIZATION
    # -----------------------------------------------------

    if (
        decision.action
'''


new = '''    # -----------------------------------------------------
    # QUESTION NORMALIZATION
    # -----------------------------------------------------

    if not decision.ask_question:

        decision.question_type = (
            "none"
        )

        decision.question_goal = (
            ""
        )

    # -----------------------------------------------------
    # SAFETY NORMALIZATION
    # -----------------------------------------------------

    if (
        decision.action
'''


brain = replace_once(
    brain,
    old,
    new,
    "Question normalization"
)


# =========================================================
# BRAIN 10
# WRITER FORMAT
# =========================================================

old = '''Ask question:
{decision.ask_question}

Acknowledge correction:
'''


new = '''Ask question:
{decision.ask_question}

Question type:
{decision.question_type}

Question goal:
{decision.question_goal}

Question reason:
{decision.question_reason}

Curiosity strength:
{decision.curiosity_strength:.2f}

Information gap:
{decision.information_gap}

Topic interest:
{decision.topic_interest}

Acknowledge correction:
'''


brain = replace_once(
    brain,
    old,
    new,
    "Writer curiosity format"
)


# =========================================================
# BOT 1
# IMPORT CURIOSITY
# =========================================================

old = '''from self_model import (
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


new = '''from self_model import (
    SELF_MODEL_VERSION,
    resolve_self_query,
    apply_self_evidence_to_decision,
    format_self_model_for_brain,
    format_self_evidence_for_writer,
    self_knowledge_violation_reasons,
    format_self_model_debug,
    format_self_evidence_debug,
)

from curiosity import (
    CURIOSITY_VERSION,
    apply_curiosity_policy,
    format_curiosity_for_writer,
    format_curiosity_debug,
)

from voice_memory import (
'''


bot = replace_once(
    bot,
    old,
    new,
    "Curiosity imports"
)


# =========================================================
# BOT 2
# VERSION
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
# BOT 3
# STARTUP
# =========================================================

old = '''    print(
        "Self Knowledge Guard: ACTIVE"
    )

    print(
        format_self_model_debug()
    )

    print(
        f"Response Agency v"
'''


new = '''    print(
        "Self Knowledge Guard: ACTIVE"
    )

    print(
        format_self_model_debug()
    )

    print(
        f"Curiosity / Question Policy v"
        f"{CURIOSITY_VERSION}: ACTIVE"
    )

    print(
        "Information Gap Questions: ACTIVE"
    )

    print(
        "Anti-Interview Question Pressure: ACTIVE"
    )

    print(
        f"Response Agency v"
'''


bot = replace_once(
    bot,
    old,
    new,
    "Curiosity startup status"
)


# =========================================================
# BOT 4
# CURIOSITY POLICY
# =========================================================

old = '''        if self_evidence.matched:

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


new = '''        if self_evidence.matched:

            print(
                format_self_evidence_debug(
                    self_evidence
                )
            )

        # =================================================
        # 2.11 B3B.1A CURIOSITY / QUESTION POLICY
        # =================================================

        curiosity_result = (
            apply_curiosity_policy(

                decision=decision,

                recent_evilnae_messages=(
                    state.history
                    .recent_evilnae_messages
                ),

                conversation_mode=(
                    brain_conversation_mode
                )
            )
        )

        # run_brain() created state.brain before this
        # deterministic policy runs.
        #
        # Keep the final writer-facing state synchronized.
        state.brain.ask_question = (
            decision.ask_question
        )

        print(
            format_curiosity_debug(
                curiosity_result
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
    "Apply Curiosity Policy"
)


# =========================================================
# BOT 5
# CURIOSITY -> WRITER
# =========================================================

old = '''        if self_evidence.matched:

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


new = '''        if self_evidence.matched:

            writer_context += (
                "\\n\\n"
                +
                format_self_evidence_for_writer(
                    self_evidence
                )
            )

        # =====================================================
        # 2.11 B3B.1A CURIOSITY -> WRITER
        # =====================================================

        writer_context += (
            "\\n\\n"
            +
            format_curiosity_for_writer(
                curiosity_result
            )
        )

        # =====================================================
        # KNOWLEDGE GUARD v3 FOUNDATION
'''


bot = replace_once(
    bot,
    old,
    new,
    "Curiosity Writer guidance"
)


# =========================================================
# SYNTAX CHECKS
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
        "Patched brain.py syntax error "
        f"line={error.lineno}: "
        f"{error.msg}. "
        "Nothing overwritten."
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
        "Patched bot.py syntax error "
        f"line={error.lineno}: "
        f"{error.msg}. "
        "Nothing overwritten."
    )


ok(
    "bot.py syntax check"
)


# =========================================================
# WRITE
# =========================================================

brain_tmp = Path(
    "brain.py.B3B1A.tmp"
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
    "bot.py.B3B1A.tmp"
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

installed_brain = (
    BRAIN_PATH.read_text(
        encoding="utf-8"
    )
)


installed_bot = (
    BOT_PATH.read_text(
        encoding="utf-8"
    )
)


required_brain = [

    (
        f'BRAIN_VERSION = '
        f'"{TARGET_BRAIN_VERSION}"'
    ),

    "question_type:",

    "question_goal:",

    "curiosity_strength:",

    "information_gap:",

    "topic_interest:",

    "CURIOSITY / GEGENFRAGEN",

    '"question_type": "none"',

    "ALLOWED_QUESTION_TYPES",
]


required_bot = [

    (
        f'BOT_VERSION = '
        f'"{TARGET_BOT_VERSION}"'
    ),

    "CURIOSITY_VERSION",

    "apply_curiosity_policy(",

    "format_curiosity_for_writer(",

    "Curiosity / Question Policy v",

    "Anti-Interview Question Pressure",
]


missing = []


for marker in required_brain:

    if marker not in installed_brain:

        missing.append(
            f"brain:{marker}"
        )


for marker in required_bot:

    if marker not in installed_bot:

        missing.append(
            f"bot:{marker}"
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
    "EVILNAE B3B.1A INSTALL COMPLETE"
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
    "  [✓] Structured Curiosity"
)

print(
    "  [✓] Topic Interest"
)

print(
    "  [✓] Information Gap"
)

print(
    "  [✓] Question Goal"
)

print(
    "  [✓] Curiosity Strength"
)

print(
    "  [✓] Curiosity Questions"
)

print(
    "  [✓] Clarification Questions"
)

print(
    "  [✓] Rare Social Questions"
)

print(
    "  [✓] Recent Question Pressure"
)

print(
    "  [✓] Anti-Interview Guard"
)

print(
    "  [✓] No random question quota"
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
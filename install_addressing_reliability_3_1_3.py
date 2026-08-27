from pathlib import Path
from datetime import datetime

import ast
import shutil


# =========================================================
# EVILNAE 3.1.3 — ADDRESSING + NO-LOST-DIRECT
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent

BOT_PATH = PROJECT_ROOT / "bot.py"
ROUTING_PATH = PROJECT_ROOT / "routing_hardening.py"

BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.1.2-social-context"'
TARGET_BOT = 'BOT_VERSION = "3.1.3-addressing-reliability"'

EXPECTED_ROUTING = 'ROUTING_HARDENING_VERSION = "1.1"'
TARGET_ROUTING = 'ROUTING_HARDENING_VERSION = "1.2"'


def header(text):
    print()
    print("=" * 76)
    print(text)
    print("=" * 76)


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[INSTALL ERROR] {text}")
    print("Nothing was overwritten by this installer.")
    print()
    raise SystemExit(1)


def read_utf8(path):
    if not path.exists():
        fail(f"Missing required file: {path.name}")

    try:
        return path.read_text(encoding="utf-8")
    except Exception as error:
        fail(
            f"Could not read {path.name}: "
            f"{type(error).__name__}: {error}"
        )


def atomic_write(path, text):
    temp = Path(str(path) + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def replace_once(text, old, new, label):
    count = text.count(old)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 match, found {count}"
        )

    ok(label)
    return text.replace(old, new, 1)


def insert_before_once(text, marker, block, label):
    count = text.count(marker)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 marker, found {count}"
        )

    ok(label)
    return text.replace(marker, block + marker, 1)


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch at "
            f"line {error.lineno}: {error.msg}"
        )

    ok(f"{filename} syntax check")


header("EVILNAE 3.1.3 ADDRESSING + NO-LOST-DIRECT")
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()

bot = read_utf8(BOT_PATH)
routing = read_utf8(ROUTING_PATH)

if (
    TARGET_BOT in bot
    and
    TARGET_ROUTING in routing
):
    print("3.1.3 is already installed.")
    raise SystemExit(0)

if EXPECTED_BOT not in bot:
    fail(
        "Unexpected bot.py version. "
        "Expected 3.1.2-social-context."
    )

if EXPECTED_ROUTING not in routing:
    fail(
        "Unexpected routing_hardening.py version. "
        "Expected Routing Hardening 1.1."
    )

for marker in (
    "SOCIAL STANCE / EVILNAE EGO v1",
    "_HANAE_COMPARISON_PROVOCATION_PATTERN",
    "RELIABILITY DIRECT RESCUE FAILED",
    "FAILED_DIRECT_CONTINUATION_WINDOW = 90",
):
    if marker not in bot:
        fail(
            f"Required 3.1.2 invariant missing in bot.py: {marker}"
        )

for marker in (
    "def _looks_like_direct_vocative(",
    "evilnae_subject_not_direct",
    "EVIL_VARIANT_PATTERN",
):
    if marker not in routing:
        fail(
            f"Required routing invariant missing: {marker}"
        )

ok("3.1.2 social-context base detected")


# =========================================================
# VERSIONS
# =========================================================

bot = replace_once(
    bot,
    EXPECTED_BOT,
    TARGET_BOT,
    "Bot version -> 3.1.3-addressing-reliability",
)

routing = replace_once(
    routing,
    EXPECTED_ROUTING,
    TARGET_ROUTING,
    "Routing Hardening version -> 1.2",
)


# =========================================================
# ROUTING — SOCIAL VOCATIVE SIGNALS
# =========================================================

ROUTING_PATTERNS = r"""
# =========================================================
# v1.2 SOCIAL VOCATIVE ADDRESSING
# =========================================================
#
# DIRECT:
#   "WOW Evil WOW..."
#   "Ach Evil..."
#   "Wow evil.. mehr nicht?"
#
# THIRD PERSON:
#   "Wow, Evil ist heute ruhig."
#   "Evil hat das gestern gesagt."
# =========================================================

SOCIAL_VOCATIVE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:(?:"
    r"wow+|ach+|ey+|hey+|yo+|boah+|bro+|bruh+|"
    r"alter+|wtf+|lol+|haha+|hahaha+|uff+|pff+"
    r")[\s,;:!?._\-–—]*)+$",
    re.IGNORECASE,
)

THIRD_PERSON_AFTER_EVIL_PATTERN = re.compile(
    r"^\s*(?:"
    r"ist|war|hat|hatte|wird|macht|mag|findet|kann|"
    r"will|kommt|geht|schläft|schlaeft|sagt|meint|"
    r"denkt|braucht|sollte|würde|wuerde|hätte|haette"
    r")\b",
    re.IGNORECASE,
)

DIRECT_SOCIAL_FOLLOWUP_PATTERN = re.compile(
    r"^\s*(?:"
    r"wow+|wtf+|bro+|bruh+|mehr\s+nicht|ernsthaft|"
    r"echt\s+jetzt|really|aha|okay|ok|ach\s+komm|"
    r"komm\s+schon|was\s+soll\s+das|na\s+toll|"
    r"nicht\s+dein\s+ernst"
    r")\b",
    re.IGNORECASE,
)


"""

routing = insert_before_once(
    routing,
    "REFERENCE_PATTERNS = {\n",
    ROUTING_PATTERNS,
    "Routing: social vocative patterns",
)


# =========================================================
# ROUTING — UPGRADE _looks_like_direct_vocative
# =========================================================

OLD_VOCATIVE_SETUP = """    before = text[
        :match.start()
    ].strip(
        " \\t,;:!?._-–—"
    )

    after = text[
        match.end():
    ].strip(
        " \\t,;:!?._-–—"
    )

    is_start = not before
    is_end = not after

    if is_start:
"""

NEW_VOCATIVE_SETUP = """    raw_before = text[
        :match.start()
    ]

    raw_after = text[
        match.end():
    ]

    before = raw_before.strip(
        " \\t,;:!?._-–—"
    )

    after = raw_after.strip(
        " \\t,;:!?._-–—"
    )

    is_start = not before
    is_end = not after

    # -----------------------------------------------------
    # v1.2 INTERJECTION + NAME = SOCIAL VOCATIVE
    #
    # "WOW Evil WOW..." addresses Evilnae.
    #
    # "Wow, Evil ist heute ruhig" remains third-person.
    # -----------------------------------------------------

    if SOCIAL_VOCATIVE_PREFIX_PATTERN.fullmatch(
        raw_before
    ):
        after_social = raw_after.lstrip(
            " \\t,;:!?._-–—"
        )

        if not after_social:
            return True

        if DIRECT_SOCIAL_FOLLOWUP_PATTERN.search(
            after_social
        ):
            return True

        if not THIRD_PERSON_AFTER_EVIL_PATTERN.search(
            after_social
        ):
            return True

    if is_start:
"""

routing = replace_once(
    routing,
    OLD_VOCATIVE_SETUP,
    NEW_VOCATIVE_SETUP,
    "Routing: interjection-name vocative resolver",
)


# =========================================================
# BOT — SECOND DIRECT STATEMENT-ONLY RESCUE
# =========================================================

OLD_DIRECT_RESCUE_END = """                else:
                    print(
                        "[RELIABILITY DIRECT RESCUE FAILED] "
                        f"user={username}"
                    )

        # -------------------------------------------------
        # FRESH CHANNEL HISTORY FOR LOCAL VOICE
"""

NEW_DIRECT_RESCUE_END = """                else:
                    print(
                        "[RELIABILITY DIRECT RESCUE FAILED] "
                        f"user={username}"
                    )

                    # -----------------------------------------
                    # 3.1.3 SECOND DIRECT RESCUE
                    #
                    # Harmless direct turns must not disappear
                    # only because Writer + first rescue both
                    # returned forbidden counter-questions.
                    #
                    # Use the remaining repair-budget slot for
                    # one generated statement-only attempt.
                    # No canned deterministic fallback.
                    # -----------------------------------------

                    statement_only_context = (
                        writer_context
                        + "\\n\\n"
                        + (
                            "[DIRECT STATEMENT-ONLY RESCUE]\\n\\n"
                            "Die Antwort darf auf keinen Fall verloren gehen.\\n\\n"
                            "Schreibe jetzt GENAU EINE kurze natürliche Aussage, "
                            "die direkt auf die aktuelle User-Nachricht reagiert.\\n\\n"
                            "HARD:\\n"
                            "- KEIN Fragezeichen.\\n"
                            "- KEINE Gegenfrage.\\n"
                            "- Nicht 'was meinst du?', 'und du?' oder ähnlich.\\n"
                            "- Kein generischer Support-/Bot-Füllsatz.\\n"
                            "- Nicht bloß die User-Nachricht wiederholen.\\n"
                            "- Evilnae darf trocken, smug oder leicht frech klingen.\\n"
                            "- Nutze den aktuellen Kontext und ihre aktuelle Tätigkeit, "
                            "wenn das natürlich passt.\\n"
                            "- Mindestens ein echtes Wort."
                        )
                    )

                    statement_only_rescue = (
                        await repair_writer_answer(
                            original_answer=(
                                direct_rescue
                                or
                                answer
                                or
                                response.output_text
                                or
                                ""
                            ),
                            violation_reasons=[
                                "direct_reply_must_not_disappear",
                                "statement_only_no_counterquestion",
                            ],
                            writer_context=(
                                statement_only_context
                            ),
                            current_mood=current_mood,
                            username=username,
                            token_limit=writer_token_limit,
                            autonomous_participation=False,
                        )
                    )

                    if statement_only_rescue:
                        reliability_baseline_answer = (
                            choose_reliability_fallback(
                                candidates=[
                                    (
                                        "direct_statement_rescue",
                                        statement_only_rescue,
                                    ),
                                ],
                                curiosity_result=curiosity_result,
                                self_evidence=self_evidence,
                                knowledge_constraint=knowledge_constraint,
                                username=username,
                                stage="baseline_direct_statement_rescue",
                            )
                        )

                    if reliability_baseline_answer:
                        answer = reliability_baseline_answer

                        print(
                            "[RELIABILITY DIRECT STATEMENT RESCUE SUCCESS] "
                            f"user={username} "
                            f"answer={answer!r}"
                        )

                    else:
                        print(
                            "[RELIABILITY DIRECT STATEMENT RESCUE FAILED] "
                            f"user={username}"
                        )

        # -------------------------------------------------
        # FRESH CHANNEL HISTORY FOR LOCAL VOICE
"""

bot = replace_once(
    bot,
    OLD_DIRECT_RESCUE_END,
    NEW_DIRECT_RESCUE_END,
    "Bot: second statement-only Direct rescue",
)


# =========================================================
# VERIFY INVARIANTS
# =========================================================

for marker in (
    TARGET_BOT,
    "[RELIABILITY DIRECT STATEMENT RESCUE SUCCESS]",
    "statement_only_no_counterquestion",
    "DIRECT STATEMENT-ONLY RESCUE",
):
    if marker not in bot:
        fail(
            f"Patched bot.py missing invariant: {marker}"
        )

for marker in (
    TARGET_ROUTING,
    "SOCIAL_VOCATIVE_PREFIX_PATTERN",
    "THIRD_PERSON_AFTER_EVIL_PATTERN",
    "DIRECT_SOCIAL_FOLLOWUP_PATTERN",
    "v1.2 INTERJECTION + NAME",
):
    if marker not in routing:
        fail(
            f"Patched routing_hardening.py missing invariant: {marker}"
        )


# =========================================================
# SYNTAX CHECK BEFORE WRITE
# =========================================================

syntax_check(
    bot,
    "bot.py",
)

syntax_check(
    routing,
    "routing_hardening.py",
)


# =========================================================
# ROUTING LOGIC SELF TEST
# =========================================================

EVIL_VARIANT_TEST = re.compile(
    r"(?<![A-Za-zÄÖÜäöüß0-9_])"
    r"e+v+i+l+(?:\s*n+a+e+)?"
    r"(?![A-Za-zÄÖÜäöüß0-9_])",
    re.IGNORECASE,
)

PREFIX_TEST = re.compile(
    r"^\s*(?:(?:"
    r"wow+|ach+|ey+|hey+|yo+|boah+|bro+|bruh+|"
    r"alter+|wtf+|lol+|haha+|hahaha+|uff+|pff+"
    r")[\s,;:!?._\-–—]*)+$",
    re.IGNORECASE,
)

THIRD_AFTER_TEST = re.compile(
    r"^\s*(?:"
    r"ist|war|hat|hatte|wird|macht|mag|findet|kann|"
    r"will|kommt|geht|schläft|schlaeft|sagt|meint|"
    r"denkt|braucht|sollte|würde|wuerde|hätte|haette"
    r")\b",
    re.IGNORECASE,
)

FOLLOW_TEST = re.compile(
    r"^\s*(?:"
    r"wow+|wtf+|bro+|bruh+|mehr\s+nicht|ernsthaft|"
    r"echt\s+jetzt|really|aha|okay|ok|ach\s+komm|"
    r"komm\s+schon|was\s+soll\s+das|na\s+toll|"
    r"nicht\s+dein\s+ernst"
    r")\b",
    re.IGNORECASE,
)


def installer_vocative(text):
    match = EVIL_VARIANT_TEST.search(text)

    if not match:
        return False

    raw_before = text[:match.start()]
    raw_after = text[match.end():]

    if not PREFIX_TEST.fullmatch(raw_before):
        return False

    after = raw_after.lstrip(
        " \t,;:!?._-–—"
    )

    if not after:
        return True

    if FOLLOW_TEST.search(after):
        return True

    if THIRD_AFTER_TEST.search(after):
        return False

    return True


tests = {
    "uploaded WOW Evil comparison is direct":
        installer_vocative(
            "WOW Evil WOW... Hanae hätte da süßer reagiert"
        ),

    "uploaded Wow evil mehr nicht is direct":
        installer_vocative(
            "Wow evil.. mehr nicht? Hanae hätte da süßer reagiert"
        ),

    "Ach Evil is direct":
        installer_vocative(
            "Ach Evil, mehr nicht?"
        ),

    "third-person copula remains non-direct":
        not installer_vocative(
            "Wow, Evil ist heute ruhig"
        ),

    "third-person has remains non-direct":
        not installer_vocative(
            "Wow Evil hat das gestern gesagt"
        ),
}

failed = [
    name
    for name, passed in tests.items()
    if not passed
]

if failed:
    fail(
        "Routing behavior self-test failed: "
        + ", ".join(failed)
    )

ok(
    f"Routing behavior self-test: "
    f"{len(tests)}/{len(tests)} PASS"
)


# =========================================================
# BACKUP — COLLISION SAFE
# =========================================================

timestamp = (
    datetime.now()
    .astimezone()
    .strftime("%Y%m%d-%H%M%S")
)

backup_directory = (
    BACKUP_ROOT
    /
    timestamp
)

if backup_directory.exists():
    suffix = 1

    while True:
        candidate = (
            BACKUP_ROOT
            /
            f"{timestamp}_{suffix:02d}"
        )

        if not candidate.exists():
            backup_directory = candidate
            break

        suffix += 1

        if suffix > 99:
            fail(
                f"Could not find free backup suffix "
                f"for {timestamp}"
            )

try:
    backup_directory.mkdir(
        parents=True,
        exist_ok=False,
    )
except Exception as error:
    fail(
        "Could not create backup directory: "
        f"{type(error).__name__}: {error}"
    )

for path in (
    BOT_PATH,
    ROUTING_PATH,
):
    try:
        shutil.copy2(
            path,
            backup_directory / path.name,
        )
    except Exception as error:
        fail(
            f"Backup failed for {path.name}: "
            f"{type(error).__name__}: {error}"
        )

    ok(
        f"Backup: {path.name}"
    )


# =========================================================
# WRITE
# =========================================================

try:
    atomic_write(
        BOT_PATH,
        bot
    )
    ok(
        "Updated: bot.py"
    )

    atomic_write(
        ROUTING_PATH,
        routing
    )
    ok(
        "Updated: routing_hardening.py"
    )

except Exception as error:
    print()
    print(
        f"[WRITE ERROR] "
        f"{type(error).__name__}: {error}"
    )
    print(
        f"Backups: {backup_directory}"
    )
    raise


header(
    "EVILNAE 3.1.3 ADDRESSING + RELIABILITY INSTALLED"
)

print("Installed:")
print("  [✓] 'WOW Evil ...' social vocatives become DIRECT")
print("  [✓] 'Wow evil.. mehr nicht?' becomes DIRECT")
print("  [✓] real third-person 'Evil ist/hat...' stays third-person")
print("  [✓] Hanae-comparison messages can reach Social Ego layer")
print("  [✓] second statement-only rescue for lost harmless Direct replies")
print("  [✓] no canned deterministic fallback added")
print()
print("Unchanged:")
print("  [✓] Foundation / Excel")
print("  [✓] Character State / Learning")
print("  [✓] Understanding 1.2 social comparison logic")
print("  [✓] Expression 2.4 / Output Quality 2.4")
print("  [✓] DB / Memories")
print()
print(f"Backup: {backup_directory}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  python bot.py")
print()

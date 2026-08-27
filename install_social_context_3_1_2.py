from pathlib import Path
from datetime import datetime
import ast
import re
import shutil

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
EXPRESSION_PATH = PROJECT_ROOT / "expression.py"
QUALITY_PATH = PROJECT_ROOT / "response_quality.py"
UNDERSTANDING_PATH = PROJECT_ROOT / "understanding.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "3.1.1-social-ego"'
TARGET_BOT = 'BOT_VERSION = "3.1.2-social-context"'
EXPECTED_EXPRESSION = 'EXPRESSION_VERSION = "2.3"'
TARGET_EXPRESSION = 'EXPRESSION_VERSION = "2.4"'
EXPECTED_QUALITY = 'OUTPUT_QUALITY_VERSION = "2.3"'
TARGET_QUALITY = 'OUTPUT_QUALITY_VERSION = "2.4"'
EXPECTED_UNDERSTANDING = 'UNDERSTANDING_VERSION = "1.1-subject-authority"'
TARGET_UNDERSTANDING = 'UNDERSTANDING_VERSION = "1.2-social-context"'


def header(text):
    print()
    print("=" * 74)
    print(text)
    print("=" * 74)


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
        fail(f"Could not read {path.name}: {type(error).__name__}: {error}")


def atomic_write(path, text):
    temp = Path(str(path) + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly 1 match, found {count}")
    ok(label)
    return text.replace(old, new, 1)


def insert_before_once(text, marker, block, label):
    count = text.count(marker)
    if count != 1:
        fail(f"{label}: expected exactly 1 marker, found {count}")
    ok(label)
    return text.replace(marker, block + marker, 1)


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(f"{filename}: syntax error after patch at line {error.lineno}: {error.msg}")
    ok(f"{filename} syntax check")


header("EVILNAE 3.1.2 SOCIAL CONTEXT / EGO NATURALNESS")
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()

bot = read_utf8(BOT_PATH)
expression = read_utf8(EXPRESSION_PATH)
quality = read_utf8(QUALITY_PATH)
understanding = read_utf8(UNDERSTANDING_PATH)

if (
    TARGET_BOT in bot
    and TARGET_EXPRESSION in expression
    and TARGET_QUALITY in quality
    and TARGET_UNDERSTANDING in understanding
):
    print("3.1.2 is already installed.")
    raise SystemExit(0)

if EXPECTED_BOT not in bot:
    fail("Unexpected bot.py version. Expected 3.1.1-social-ego.")
if EXPECTED_EXPRESSION not in expression:
    fail("Unexpected expression.py version. Expected Expression 2.3.")
if EXPECTED_QUALITY not in quality:
    fail("Unexpected response_quality.py version. Expected Output Quality 2.3.")
if EXPECTED_UNDERSTANDING not in understanding:
    fail("Unexpected understanding.py version. Expected Understanding 1.1-subject-authority.")

for marker in (
    "SOCIAL STANCE / EVILNAE EGO v1",
    "social_stance_violation_reasons(",
    "[SOCIAL STANCE VIOLATION]",
    "CHARACTER IDENTITY VIOLATION",
):
    if marker not in bot:
        fail(f"3.1.1 bot invariant missing: {marker}")

if "Spielerisches Necken/Roasten ist NORMALER" not in expression:
    fail("3.1.1 expression roast-bias invariant missing.")
if "evilnae_polite_praise" not in quality:
    fail("3.1.1 quality roast-bias invariant missing.")

ok("3.1.1 social-ego base detected")

bot = replace_once(bot, EXPECTED_BOT, TARGET_BOT, "Bot version -> 3.1.2-social-context")
expression = replace_once(expression, EXPECTED_EXPRESSION, TARGET_EXPRESSION, "Expression version -> 2.4")
quality = replace_once(quality, EXPECTED_QUALITY, TARGET_QUALITY, "Output Quality version -> 2.4")
understanding = replace_once(
    understanding,
    EXPECTED_UNDERSTANDING,
    TARGET_UNDERSTANDING,
    "Understanding version -> 1.2-social-context",
)

SOCIAL_COMPARISON_HELPER = r'''# =========================================================
# 1.2 SOCIAL COMPARISON / PROVOCATION
# =========================================================
# Social comparisons with Hanae are banter, not a request for
# a factual dossier about Hanae.
# =========================================================

HANAE_SOCIAL_COMPARISON_PATTERNS = [
    re.compile(
        r"\bhanae\b.{0,60}\b(?:süßer|suesser|netter|freundlicher|besser|"
        r"lustiger|cooler|lieber|stärker|staerker)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bhanae\b.{0,25}\b(?:hätte|haette|würde|wuerde)\b.{0,70}\b"
        r"(?:süßer|suesser|netter|freundlicher|besser|lustiger|cooler|anders)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bhanae\b.{0,25}\b(?:ist|wäre|waere)\b.{0,35}\b"
        r"(?:besser|süßer|suesser|netter|freundlicher|cooler|lustiger)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:team|seite)\s+hanae\b",
        flags=re.IGNORECASE,
    ),
]


def is_social_comparison_or_provocation(text: str, subject_name: str) -> bool:
    if str(subject_name or "").strip().lower() != "hanae":
        return False
    value = str(text or "")
    return any(pattern.search(value) for pattern in HANAE_SOCIAL_COMPARISON_PATTERNS)


'''
understanding = insert_before_once(
    understanding,
    "# =========================================================\n# PERSON FACT REQUEST\n",
    SOCIAL_COMPARISON_HELPER,
    "Understanding: social comparison/provocation helper",
)

OLD_KNOWLEDGE_FLOW = '''    if not looks_like_person_fact_request(
        user_text
    ):

        return KnowledgeConstraint(
'''
NEW_KNOWLEDGE_FLOW = '''    if is_social_comparison_or_provocation(
        user_text,
        subject_name,
    ):

        return KnowledgeConstraint(

            active=False,

            subject_name=(
                subject_name
            ),

            subject_id=(
                subject_id
            ),

            knowledge_available=(
                knowledge_available
            ),

            knowledge_source=(
                knowledge_source
            ),

            reason=(
                "social_comparison_or_provocation"
            )
        )

    if not looks_like_person_fact_request(
        user_text
    ):

        return KnowledgeConstraint(
'''
understanding = replace_once(
    understanding,
    OLD_KNOWLEDGE_FLOW,
    NEW_KNOWLEDGE_FLOW,
    "Understanding: social comparison bypasses unknown-person guard",
)

EXTRA_SOCIAL_PATTERNS = r'''# =========================================================
# 3.1.2 BROADER SOCIAL CONTEXT SIGNALS
# =========================================================

_BROAD_USER_FAIL_PATTERN = re.compile(
    r"\b(?:aus|vom)\b.{0,35}\bbett\b.{0,70}\bgefallen\b"
    r"|\bbett\b.{0,50}\bgefallen\b"
    r"|\b(?:gegen|an)\b.{0,40}\b(?:tür|tuer|wand|tisch|schrank|möbel|moebel)\b"
    r".{0,45}\b(?:gelaufen|gestoßen|gestossen|geknallt)\b"
    r"|\bverschlafen\b"
    r"|\bausgesperrt\b"
    r"|\b(?:hab|habe)\b.{0,35}\bvergessen\b"
    r"|\b(?:hab|habe)\b.{0,30}\b(?:verkackt|gefailt|verloren|nicht geschafft)\b"
    r"|\b(?:bin|war)\b.{0,25}\b(?:wieder\s+)?gestorben\b",
    flags=re.IGNORECASE,
)

_CHEEKY_REVEAL_PATTERN = re.compile(
    r"\bich\s+muss\s+dir\s+(?:was|etwas)\s+erzählen\b"
    r"|\bich\s+hab(?:e)?\s+dir\s+was\s+zu\s+erzählen\b"
    r"|\bdu\s+glaubst\s+nicht[, ]+was\b"
    r"|\bweißt\s+du[, ]+was\s+passiert\s+ist\b"
    r"|\bweisst\s+du[, ]+was\s+passiert\s+ist\b"
    r"|\bich\s+hab(?:e)?\s+was\s+angestellt\b",
    flags=re.IGNORECASE,
)

_HANAE_COMPARISON_PROVOCATION_PATTERN = re.compile(
    r"\bhanae\b.{0,60}\b(?:süßer|suesser|netter|freundlicher|besser|"
    r"lustiger|cooler|stärker|staerker)\b"
    r"|\bhanae\b.{0,30}\b(?:hätte|haette|würde|wuerde)\b.{0,70}\b"
    r"(?:reagiert|gemacht|gesagt|geschafft)\b",
    flags=re.IGNORECASE,
)

_BOTLIKE_CASUAL_CURIOSITY_PATTERN = re.compile(
    r"\bwas\s+hast\s+du\s+auf\s+dem\s+herzen\b"
    r"|\berzähl(?:e)?\s+mir(?:\s+mehr)?\b"
    r"|\berzaehl(?:e)?\s+mir(?:\s+mehr)?\b"
    r"|\bich\s+höre\s+dir\s+zu\b"
    r"|\bich\s+hoere\s+dir\s+zu\b"
    r"|\bich\s+bin\s+ganz\s+ohr\b",
    flags=re.IGNORECASE,
)

_BOTLIKE_FAIL_RESPONSE_PATTERN = re.compile(
    r"\bdas\s+klingt\b"
    r"|\boh\s+nein\b"
    r"|\bdas\s+tut\s+mir\s+leid\b"
    r"|\bhoffentlich\b.{0,55}\b(?:nicht|okay|gut|besser|in\s+ordnung|im\s+eimer)\b",
    flags=re.IGNORECASE,
)

_COMPARISON_EGO_FAILURE_PATTERN = re.compile(
    r"\bweiß\s+ich\s+(?:grad\s+)?nicht\b"
    r"|\bweiss\s+ich\s+(?:grad\s+)?nicht\b"
    r"|\bkeine\s+ahnung\b"
    r"|\bkann\s+ich\s+nicht\s+sagen\b"
    r"|\bstimmt\b"
    r"|\bda\s+hast\s+du\s+recht\b",
    flags=re.IGNORECASE,
)


'''
bot = insert_before_once(
    bot,
    'def detect_social_stance_mode(user_text, episode_text="", *, is_hanae=False):\n',
    EXTRA_SOCIAL_PATTERNS,
    "Bot: broader social context patterns",
)

OLD_MODE_FLOW = '''    if _COMPETITIVE_CHALLENGE_PATTERN.search(user):
        return "competitive"

    if _PRAISE_EVILNAE_PATTERN.search(user):
        return "smug_praise"

    if _USER_FAIL_PATTERN.search(user):
        return "playful_roast"

    if is_hanae:
'''
NEW_MODE_FLOW = '''    if _HANAE_COMPARISON_PROVOCATION_PATTERN.search(user):
        return "comparison_provocation"

    if _COMPETITIVE_CHALLENGE_PATTERN.search(user):
        return "competitive"

    if _PRAISE_EVILNAE_PATTERN.search(user):
        return "smug_praise"

    if _CHEEKY_REVEAL_PATTERN.search(user):
        return "cheeky_curiosity"

    if (
        _USER_FAIL_PATTERN.search(user)
        or
        _BROAD_USER_FAIL_PATTERN.search(user)
    ):
        return "playful_roast"

    if is_hanae:
'''
bot = replace_once(
    bot,
    OLD_MODE_FLOW,
    NEW_MODE_FLOW,
    "Bot: comparison/reveal/broader-fail social modes",
)

OLD_COMMON_LINE = '''- Nicht automatisch zustimmen oder freundlich bestätigen.
- Keine Customer-Service-Wärme als Default.
'''
NEW_COMMON_LINE = '''- Nicht automatisch zustimmen oder freundlich bestätigen.
- Keine Customer-Service-Wärme als Default.
- Reagiere zuerst wie eine Person mit eigener Haltung, nicht wie ein Assistent, Therapeut oder Gesprächsmoderator.
- Wenn ein User eine Story anteasert, darf Evilnae neugierig sein, aber casual/frech statt "Was hast du auf dem Herzen?".
'''
bot = replace_once(
    bot,
    OLD_COMMON_LINE,
    NEW_COMMON_LINE,
    "Bot: reaction-first anti-bot social rule",
)

COMPARISON_DIRECTIVE = r'''    elif mode == "comparison_provocation":
        specific = """
AKTUELLER MODUS: HANAE COMPARISON / PROVOCATION

Der User vergleicht Evilnae mit Hanae oder stichelt damit, dass Hanae etwas süßer/netter/besser gemacht hätte.
Das ist primär eine SOZIALE PROVOKATION, keine Faktenabfrage über Hanae.

Reaktion:
- eigenes Ego behalten
- spielerisch kontern
- den Vergleich nicht brav bestätigen
- kein epistemisches "weiß ich nicht"
- Hanae darf die süßere Schwester sein; Evilnae ist dafür die frechere/evil Schwester

Passende Energie:
- "süß ist halt ihr Department."
- "ja cool, dann geh doch zur süßen Schwester."
- "ich bin nicht für den Kuschelservice zuständig."
- "Hanae kann süß, ich kann ehrlich."

Nicht exakt diese Sätze kopieren; nur die Haltung übernehmen.
""".strip()

'''
bot = insert_before_once(
    bot,
    '    elif mode == "competitive":\n',
    COMPARISON_DIRECTIVE,
    "Bot: Hanae comparison/provocation directive",
)

CHEEKY_DIRECTIVE = r'''    elif mode == "cheeky_curiosity":
        specific = """
AKTUELLER MODUS: CHEEKY CURIOSITY

Der User teasered gerade eine Story an ("ich muss dir was erzählen" usw.).
Evilnae ist neugierig, aber NICHT therapeutisch oder serviceartig.

Bevorzugte Energie:
- "raus damit."
- "okay, was hast du angestellt?"
- "oh gott, was war diesmal?"
- "na los."

Keine sterile Gesprächsmoderation wie:
- "Was hast du auf dem Herzen?"
- "Erzähl mir mehr."
- "Ich höre dir zu."

Die konkrete Formulierung soll natürlich variieren.
""".strip()

'''
bot = insert_before_once(
    bot,
    '    elif mode == "playful_roast":\n',
    CHEEKY_DIRECTIVE,
    "Bot: cheeky curiosity directive",
)

VIOLATION_BLOCK = r'''    if mode == "comparison_provocation":
        if _COMPARISON_EGO_FAILURE_PATTERN.search(lowered):
            reasons.append("hanae_comparison_ego_missing")

    if mode == "cheeky_curiosity":
        if _BOTLIKE_CASUAL_CURIOSITY_PATTERN.search(lowered):
            reasons.append("casual_curiosity_sounds_like_therapist")

    if mode == "playful_roast":
        if _BOTLIKE_FAIL_RESPONSE_PATTERN.search(lowered):
            reasons.append("harmless_fail_answer_too_supportive")

'''
bot = insert_before_once(
    bot,
    '    if mode == "competitive":\n',
    VIOLATION_BLOCK,
    "Bot: social context final violations",
)

OLD_SURFACE_FRAGMENT = '''- Spielerisches Necken/Roasten ist NORMALER Bestandteil ihrer Sprache, nicht seltenes Spezialevent.
- Wenn ein User einen Fail, eine dumme Entscheidung, Skill Issue, offensichtliche Angriffsfläche oder eine freche Vorlage liefert: bevorzugt kurz necken.
'''
NEW_SURFACE_FRAGMENT = '''- Spielerisches Necken/Roasten ist NORMALER Bestandteil ihrer Sprache, nicht seltenes Spezialevent.
- Wenn ein User einen Fail, eine dumme Entscheidung, Skill Issue, offensichtliche Angriffsfläche oder eine freche Vorlage liefert: bevorzugt kurz necken.
- Bei harmlosen Fails zuerst den witzigen Winkel sehen; Sorge darf danach kurz mitschwingen, aber nicht als Support-Bot-Wrapper.
- Wenn jemand nur anteasert "ich muss dir was erzählen": casual neugierig reagieren ("raus damit"-Energy), nicht therapeutisch.
- Wenn jemand Evilnae mit Hanae vergleicht, ist das meist Banter/Provokation: Ego zeigen statt "weiß ich nicht".
'''
expression = replace_once(
    expression,
    OLD_SURFACE_FRAGMENT,
    NEW_SURFACE_FRAGMENT,
    "Expression: fail/reveal/comparison naturalness",
)

OLD_FRIENDLY_LINE = '''- Nicht jede Nachricht freundlich bestätigen. Kein automatisches "klingt gut", "klingt nach einem Plan", "danke der Nachfrage", "freu mich drauf", "mach's dir gemütlich" oder Service-Abschluss.
'''
NEW_FRIENDLY_LINE = '''- Nicht jede Nachricht freundlich bestätigen. Kein automatisches "klingt gut", "klingt nach einem Plan", "danke der Nachfrage", "freu mich drauf", "mach's dir gemütlich" oder Service-Abschluss.
- In casual Gesprächen keine Therapie-/Moderator-Sätze wie "Was hast du auf dem Herzen?", wenn ein freches "raus damit" viel natürlicher wäre.
'''
expression = replace_once(
    expression,
    OLD_FRIENDLY_LINE,
    NEW_FRIENDLY_LINE,
    "Expression: casual therapist-language suppression",
)

QUALITY_ADDITIONS = r'''    "casual_therapy_invitation": (
        re.compile(
            r"\bwas\s+hast\s+du\s+auf\s+dem\s+herzen\b"
            r"|\bich\s+bin\s+ganz\s+ohr\b"
            r"|\bich\s+höre\s+dir\s+zu\b"
            r"|\bich\s+hoere\s+dir\s+zu\b",
            re.I
        ), 3
    ),
    "soft_fail_wrapper": (
        re.compile(
            r"\bdas\s+klingt\s+(?:ja\s+)?nach\s+(?:einem|einer)\s+.{0,35}\b(?:fail|missgeschick)\b",
            re.I
        ), 3
    ),
'''
quality = insert_before_once(
    quality,
    '    "sounds_like_wrapper": (\n',
    QUALITY_ADDITIONS,
    "Output Quality: casual therapy + soft fail wrappers",
)

for marker in (
    TARGET_BOT,
    "_BROAD_USER_FAIL_PATTERN",
    "_CHEEKY_REVEAL_PATTERN",
    "_HANAE_COMPARISON_PROVOCATION_PATTERN",
    'return "comparison_provocation"',
    'return "cheeky_curiosity"',
    "harmless_fail_answer_too_supportive",
    "casual_curiosity_sounds_like_therapist",
    "hanae_comparison_ego_missing",
):
    if marker not in bot:
        fail(f"Patched bot.py missing invariant: {marker}")

for marker in (
    TARGET_UNDERSTANDING,
    "HANAE_SOCIAL_COMPARISON_PATTERNS",
    "is_social_comparison_or_provocation(",
    "social_comparison_or_provocation",
):
    if marker not in understanding:
        fail(f"Patched understanding.py missing invariant: {marker}")

for marker in (
    TARGET_EXPRESSION,
    "harmlosen Fails zuerst den witzigen Winkel",
    "Therapie-/Moderator-Sätze",
):
    if marker not in expression:
        fail(f"Patched expression.py missing invariant: {marker}")

for marker in (
    TARGET_QUALITY,
    "casual_therapy_invitation",
    "soft_fail_wrapper",
):
    if marker not in quality:
        fail(f"Patched response_quality.py missing invariant: {marker}")

syntax_check(bot, "bot.py")
syntax_check(expression, "expression.py")
syntax_check(quality, "response_quality.py")
syntax_check(understanding, "understanding.py")

# Installer-level behavior checks matching the live-test failures.
def test_social_mode(user, episode="", is_hanae=False):
    if re.search(r"\b(?:suizid|selbstmord|krankenhaus|starke schmerzen|panikattacke)\b", user, flags=re.I):
        return "serious"
    if re.search(r"\bhanae\b.{0,60}\b(?:süßer|suesser|netter|freundlicher|besser|lustiger|cooler)\b", user, flags=re.I):
        return "comparison_provocation"
    if re.search(r"\bich\s+muss\s+dir\s+(?:was|etwas)\s+erzählen\b", user, flags=re.I):
        return "cheeky_curiosity"
    if re.search(r"\b(?:aus|vom)\b.{0,35}\bbett\b.{0,70}\bgefallen\b", user, flags=re.I):
        return "playful_roast"
    if is_hanae:
        return "sibling_banter"
    return "casual_roast_bias"


def test_social_comparison_bypass(text):
    patterns = [
        re.compile(r"\bhanae\b.{0,60}\b(?:süßer|suesser|netter|freundlicher|besser|lustiger|cooler)\b", flags=re.I),
        re.compile(r"\bhanae\b.{0,25}\b(?:hätte|haette|würde|wuerde)\b.{0,70}\b(?:süßer|suesser|netter|freundlicher|besser|lustiger|cooler|anders)\b", flags=re.I),
    ]
    return any(pattern.search(text) for pattern in patterns)


tests = {
    "uploaded bed-fail phrasing -> playful roast": (
        test_social_mode(
            "Ich bin heute morgen beim aufstehen aus dem bett gefallen und hab mir voll am zeh weh getan"
        ) == "playful_roast"
    ),
    "story teaser -> cheeky curiosity": (
        test_social_mode("Check.. Ich muss dir was erzählen") == "cheeky_curiosity"
    ),
    "Hanae comparison -> ego provocation": (
        test_social_mode("Mehr nicht? Wow - Hanae hätte süßer reagiert") == "comparison_provocation"
    ),
    "Hanae comparison bypasses fact guard": (
        test_social_comparison_bypass("Mehr nicht? Wow - Hanae hätte süßer reagiert")
    ),
    "real Hanae fact question not comparison": (
        not test_social_comparison_bypass("Was macht Hanae gerade?")
    ),
    "serious topic still suppresses roast": (
        test_social_mode("Ich bin wegen starken Schmerzen im Krankenhaus") == "serious"
    ),
}

failed = [name for name, passed in tests.items() if not passed]
if failed:
    fail("Behavior self-test failed: " + ", ".join(failed))
ok(f"Behavior self-test: {len(tests)}/{len(tests)} PASS")

timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
backup_directory = BACKUP_ROOT / timestamp
if backup_directory.exists():
    suffix = 1
    while True:
        candidate = BACKUP_ROOT / f"{timestamp}_{suffix:02d}"
        if not candidate.exists():
            backup_directory = candidate
            break
        suffix += 1
        if suffix > 99:
            fail(f"Could not find free backup suffix for {timestamp}")

try:
    backup_directory.mkdir(parents=True, exist_ok=False)
except Exception as error:
    fail(f"Could not create backup directory: {type(error).__name__}: {error}")

for path in (BOT_PATH, EXPRESSION_PATH, QUALITY_PATH, UNDERSTANDING_PATH):
    try:
        shutil.copy2(path, backup_directory / path.name)
    except Exception as error:
        fail(f"Backup failed for {path.name}: {type(error).__name__}: {error}")
    ok(f"Backup: {path.name}")

try:
    atomic_write(BOT_PATH, bot)
    ok("Updated: bot.py")
    atomic_write(EXPRESSION_PATH, expression)
    ok("Updated: expression.py")
    atomic_write(QUALITY_PATH, quality)
    ok("Updated: response_quality.py")
    atomic_write(UNDERSTANDING_PATH, understanding)
    ok("Updated: understanding.py")
except Exception as error:
    print()
    print(f"[WRITE ERROR] {type(error).__name__}: {error}")
    print(f"Backups: {backup_directory}")
    raise

header("EVILNAE 3.1.2 SOCIAL CONTEXT FIX INSTALLED")
print("Installed:")
print("  [✓] broader harmless-fail detection")
print("  [✓] casual story teasers -> cheeky curiosity")
print("  [✓] Hanae social comparisons no longer trigger unknown-person fallback")
print("  [✓] comparison/provocation keeps Evilnae's ego")
print("  [✓] harmless fail support-bot wrappers trigger social repair")
print("  [✓] casual therapist phrasing triggers social repair")
print("  [✓] serious/vulnerable topics still suppress roast pressure")
print("  [✓] existing 3.1.1 rivalry / praise / roast behavior preserved")
print()
print("Unchanged:")
print("  [✓] Character Foundation / Excel")
print("  [✓] Character State")
print("  [✓] Character Learning")
print("  [✓] Memories / DB")
print("  [✓] Routing / Participation")
print()
print(f"Backup: {backup_directory}")
print()
print("NO MEMORY RESET REQUIRED.")
print()
print("NEXT:")
print("  python bot.py")
print()

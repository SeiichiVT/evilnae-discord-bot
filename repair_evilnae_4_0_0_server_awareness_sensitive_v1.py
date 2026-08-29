from pathlib import Path
from datetime import datetime
import ast
import shutil
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_PATH = PROJECT_ROOT / "bot.py"
LIVE_PATH = PROJECT_ROOT / "live_stability.py"
AGENCY_PATH = PROJECT_ROOT / "agency.py"
INITIATIVE_PATH = PROJECT_ROOT / "initiative.py"
SERVER_PATH = PROJECT_ROOT / "server_awareness.py"
AGENCY_V2_PATH = PROJECT_ROOT / "agency_initiative_v2.py"
BACKUP_ROOT = PROJECT_ROOT / "live_fix_backups"

EXPECTED_BOT = 'BOT_VERSION = "4.0.0-agency-server-awareness"'
EXPECTED_LIVE = 'LIVE_STABILITY_VERSION = "1.4-agency-server-awareness"'
EXPECTED_AGENCY = 'AGENCY_VERSION = "2.0-server-aware"'
EXPECTED_INITIATIVE = 'INITIATIVE_VERSION = "2.0-server-aware"'
OLD_SERVER_VERSION = 'SERVER_AWARENESS_VERSION = "1.0"'
NEW_SERVER_VERSION = 'SERVER_AWARENESS_VERSION = "1.0.1-sensitive-language"'
OLD_CARE_PATTERN = 'CARE_PATTERN = re.compile(\n    r"\\b(?:kopfschmerz|migräne|migraene|schmerzen|"\n    r"krank|fieber|notaufnahme|krankenhaus|"\n    r"mir\\s+geht(?:\'|’)?s\\s+nicht\\s+gut|"\n    r"panik|traurig|weine|heule)\\b",\n    re.I,\n)\n'
NEW_CARE_PATTERN = 'CARE_PATTERN = re.compile(\n    r"(?:"\n    r"\\bkopfschmerz(?:en)?\\b|"\n    r"\\b[A-Za-zÄÖÜäöüß-]*schmerzen\\b|"\n    r"\\bmigräne\\b|"\n    r"\\bmigraene\\b|"\n    r"\\bkrank\\b|"\n    r"\\bfieber\\b|"\n    r"\\bnotaufnahme\\b|"\n    r"\\bkrankenhaus\\b|"\n    r"\\bmir\\s+geht(?:\'|’)?s\\s+nicht\\s+gut\\b|"\n    r"\\bpanik\\b|"\n    r"\\btraurig\\b|"\n    r"\\bweine\\b|"\n    r"\\bheule\\b"\n    r")",\n    re.I,\n)\n'


def ok(text):
    print(f"[OK] {text}")


def fail(text):
    print()
    print(f"[REPAIR ERROR] {text}")
    print("Nothing was overwritten by this repair.")
    raise SystemExit(1)


def replace_once(text, old, new, label):
    count = text.count(old)

    if count != 1:
        fail(
            f"{label}: expected exactly 1 match, "
            f"found {count}"
        )

    ok(label)
    return text.replace(old, new, 1)


def syntax_check(text, filename):
    try:
        ast.parse(text, filename=filename)
    except SyntaxError as error:
        fail(
            f"{filename}: syntax error after patch "
            f"line {error.lineno}: {error.msg}"
        )

    ok(f"{filename} syntax check")


print("=" * 78)
print("EVILNAE 4.0.0 — SERVER AWARENESS SENSITIVE-LANGUAGE REPAIR")
print("=" * 78)
print(f"Project: {PROJECT_ROOT}")
print()
print("WICHTIG: bot.py muss vollständig AUS sein.")
print()


for path in (
    BOT_PATH,
    LIVE_PATH,
    AGENCY_PATH,
    INITIATIVE_PATH,
    SERVER_PATH,
    AGENCY_V2_PATH,
):
    if not path.exists():
        fail(f"Missing required file: {path.name}")


bot = BOT_PATH.read_text(encoding="utf-8")
live = LIVE_PATH.read_text(encoding="utf-8")
agency = AGENCY_PATH.read_text(encoding="utf-8")
initiative = INITIATIVE_PATH.read_text(encoding="utf-8")
server = SERVER_PATH.read_text(encoding="utf-8")


if NEW_SERVER_VERSION in server:
    print("Sensitive-language repair is already installed.")
    raise SystemExit(0)


if EXPECTED_BOT not in bot:
    fail("Expected installed Bot 4.0.0")

if EXPECTED_LIVE not in live:
    fail("Expected Live Stability 1.4-agency-server-awareness")

if EXPECTED_AGENCY not in agency:
    fail("Expected Response Agency 2.0-server-aware")

if EXPECTED_INITIATIVE not in initiative:
    fail("Expected Initiative 2.0-server-aware")

if OLD_SERVER_VERSION not in server:
    fail("Expected Server Awareness v1.0")

if (
    'AGENCY_INITIATIVE_V2_VERSION = "2.0"'
    not in AGENCY_V2_PATH.read_text(encoding="utf-8")
):
    fail("Expected Agency / Initiative Engine v2.0")


ok("Partially installed 4.0.0 base detected")


server = replace_once(
    server,
    OLD_SERVER_VERSION,
    NEW_SERVER_VERSION,
    "Server Awareness -> 1.0.1-sensitive-language",
)

server = replace_once(
    server,
    OLD_CARE_PATTERN,
    NEW_CARE_PATTERN,
    "Sensitive German pain-language matcher",
)


for marker in (
    NEW_SERVER_VERSION,
    r"\bkopfschmerz(?:en)?\b",
    r"[A-Za-zÄÖÜäöüß-]*schmerzen",
    "care_sensitive",
    "sensitive_recent",
):
    if marker not in server:
        fail(
            "Patched server_awareness.py "
            f"missing invariant: {marker}"
        )


syntax_check(server, "server_awareness.py")


namespace = {
    "__name__": "_evilnae_400_server_repair_preflight_",
}


try:
    exec(
        compile(
            server,
            "server_awareness.py",
            "exec",
        ),
        namespace,
    )
except Exception as error:
    fail(
        "Could not load patched Server Awareness: "
        f"{type(error).__name__}: {error}"
    )


flags_for_text = namespace.get("_flags_for_text")
module_self_test = namespace.get("_self_test")


if not callable(flags_for_text):
    fail("_flags_for_text unavailable.")


sensitive_cases = (
    "ich hab Kopfschmerz",
    "ich hab Kopfschmerzen",
    "ich hab Bauchschmerzen",
    "ich habe starke Schmerzen",
    "ich hab Migräne",
    "mir geht's nicht gut",
)


for sample in sensitive_cases:
    flags = flags_for_text(sample)

    if "care_sensitive" not in flags:
        fail(
            "Sensitive-language regression: "
            f"{sample!r}"
        )


non_sensitive_cases = (
    "ich spiel heute Hades",
    "das ist echt lustig xD",
    "was zockt ihr später?",
)


for sample in non_sensitive_cases:
    flags = flags_for_text(sample)

    if "care_sensitive" in flags:
        fail(
            "False sensitive-language match: "
            f"{sample!r}"
        )


ok("Sensitive-language behavior preflight: PASS")


if not callable(module_self_test):
    fail("Server Awareness self-test unavailable.")


if module_self_test() != 0:
    fail("Patched Server Awareness self-test failed.")


ok("Server Awareness behavior self-test: 9/9 PASS")


timestamp = (
    datetime.now()
    .astimezone()
    .strftime("%Y%m%d-%H%M%S")
)

backup_dir = BACKUP_ROOT / timestamp

suffix = 1

while backup_dir.exists():
    backup_dir = (
        BACKUP_ROOT
        /
        f"{timestamp}_{suffix:02d}"
    )
    suffix += 1


backup_dir.mkdir(
    parents=True,
    exist_ok=False,
)


shutil.copy2(
    SERVER_PATH,
    backup_dir / SERVER_PATH.name,
)

ok("Backup: server_awareness.py")


temp = Path(
    str(SERVER_PATH)
    +
    ".tmp"
)

temp.write_text(
    server,
    encoding="utf-8",
)

temp.replace(
    SERVER_PATH
)

ok("Updated: server_awareness.py")


compile_targets = [
    SERVER_PATH,
    AGENCY_V2_PATH,
    AGENCY_PATH,
    INITIATIVE_PATH,
    LIVE_PATH,
    BOT_PATH,
]


result = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        *[
            str(path)
            for path in compile_targets
        ],
    ],
    cwd=str(PROJECT_ROOT),
    check=False,
)


if result.returncode != 0:
    print()
    print("[POST-REPAIR WARNING] py_compile failed.")
    print(f"Backup: {backup_dir}")
    raise SystemExit(result.returncode)


ok("Post-repair py_compile: 6/6")


for test_path, label in (
    (
        SERVER_PATH,
        "Server Awareness",
    ),
    (
        AGENCY_V2_PATH,
        "Agency / Initiative 2.0",
    ),
    (
        AGENCY_PATH,
        "Agency",
    ),
):
    result = subprocess.run(
        [
            sys.executable,
            str(test_path),
        ],
        cwd=str(PROJECT_ROOT),
        check=False,
    )

    if result.returncode != 0:
        print()
        print(
            "[POST-REPAIR WARNING] "
            f"{label} self-test failed."
        )
        print(f"Backup: {backup_dir}")
        raise SystemExit(result.returncode)

    ok(
        f"Post-repair {label} self-test: PASS"
    )


print()
print("=" * 78)
print("EVILNAE 4.0.0 SERVER AWARENESS REPAIR COMPLETE")
print("=" * 78)

print()
print("Fixed:")
print("  [✓] 'Kopfschmerz' detected as sensitive")
print("  [✓] 'Kopfschmerzen' detected as sensitive")
print("  [✓] compound pain words such as 'Bauchschmerzen' detected")
print("  [✓] existing Migräne / Krankheit / Notaufnahme / panic signals preserved")
print("  [✓] casual messages are not marked sensitive")

print()
print("Validation:")
print("  [✓] Server Awareness full self-test")
print("  [✓] Agency / Initiative 2.0 self-test")
print("  [✓] Response Agency self-test")
print("  [✓] complete 4.0 core py_compile")

print()
print("Versions:")
print("  Bot: 4.0.0-agency-server-awareness")
print("  Live Stability: 1.4-agency-server-awareness")
print("  Response Agency: 2.0-server-aware")
print("  Initiative: 2.0-server-aware")
print("  Server Awareness: 1.0.1-sensitive-language")
print("  Agency / Initiative Engine: 2.0")

print()
print("Unchanged:")
print("  [✓] Awareness event/state data")
print("  [✓] Character Foundation / Canon")
print("  [✓] Character Learning / Experiences")
print("  [✓] Self Development / Arcs")
print("  [✓] Social Emotional State")
print("  [✓] Episodes / Salience / Inner State")
print("  [✓] Emotes")

print()
print(f"Backup: {backup_dir}")

print()
print("NO MEMORY RESET REQUIRED.")

print()
print("NEXT:")
print("  python bot.py")
print("  Then we do the broader live/community test.")

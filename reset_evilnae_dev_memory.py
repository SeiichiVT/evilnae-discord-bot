from pathlib import Path
from datetime import datetime

import json
import shutil
import sqlite3
import sys


# =========================================================
# EVILNAE DEVELOPMENT MEMORY RESET
# =========================================================
#
# ZIEL:
#
# Evilnae auf eine saubere Entwicklungsbasis zurücksetzen.
#
# BLEIBT ERHALTEN:
#
# - kompletter Source Code
# - .env
# - Persönlichkeit / SYSTEM_PROMPT
# - Character-Lore aus dem Code
# - Hanae als fest definierte Schwester
# - feste Self-Model Seeds aus self_model.py
# - Voice-Memory Seed-Beispiele aus voice_memory.py
# - Git / Repository
# - Discord Exports / Logs
#
# WIRD ZURÜCKGESETZT:
#
# DATABASE:
# - relationships
# - summaries
# - user_buffers
# - user_profiles
# - user_impressions
# - memory_archives
#
# PERSISTENT STATE:
# - reflection_state.json
# - evilnae_inner_state.json
# - initiative_state.json
# - social_actions_state.json
# - voice_memory.json
# - evilnae_self_model.json
#
# Vorher wird automatisch ein vollständiges
# Development-Backup erstellt.
# =========================================================


RESET_VERSION = "1.1"


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent

DB_PATH = PROJECT_ROOT / "evilnae.db"

BACKUP_ROOT = PROJECT_ROOT / "dev_reset_backups"


# =========================================================
# DATABASE TABLES
# =========================================================

MEMORY_TABLES = [
    "relationships",
    "summaries",
    "user_buffers",
    "user_profiles",
    "user_impressions",
    "memory_archives",
]


# =========================================================
# PERSISTENT STATE FILES
# =========================================================
#
# IMPORTANT:
# evilnae_self_model.json enthält ausschließlich
# gelernte Self-Facts.
#
# Die festen SEED_FACTS leben in self_model.py
# und bleiben deshalb erhalten.
# =========================================================

STATE_FILES = [
    "reflection_state.json",
    "evilnae_inner_state.json",
    "initiative_state.json",
    "social_actions_state.json",
    "voice_memory.json",
    "evilnae_self_model.json",
]

TEMP_STATE_FILES = [
    f"{file_name}.tmp"
    for file_name in STATE_FILES
]


# =========================================================
# OUTPUT HELPERS
# =========================================================

def header(text):
    print("")
    print("=" * 60)
    print(text)
    print("=" * 60)


def ok(text):
    print(f"[OK] {text}")


def info(text):
    print(f"[INFO] {text}")


def warn(text):
    print(f"[WARN] {text}")


def fail(text):
    print("")
    print(f"[RESET ERROR] {text}")
    print("")
    sys.exit(1)


# =========================================================
# DATABASE HELPERS
# =========================================================

def table_exists(connection, table_name):
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_table_count(connection, table_name):
    if not table_exists(connection, table_name):
        return None

    row = connection.execute(
        f'SELECT COUNT(*) FROM "{table_name}"'
    ).fetchone()

    if not row:
        return 0

    return int(row[0])


def database_integrity_ok(connection):
    row = connection.execute(
        "PRAGMA integrity_check;"
    ).fetchone()

    return bool(
        row
        and str(row[0]).lower() == "ok"
    )


# =========================================================
# SQLITE BACKUP
# =========================================================
#
# Wir benutzen die SQLite Backup API statt shutil.copy.
# Dadurch wird auch bei WAL sauber ein konsistenter
# Datenbankstand gesichert.
# =========================================================

def backup_database(backup_database_path):
    if not DB_PATH.exists():
        warn(
            "evilnae.db existiert nicht. "
            "Database-Backup wird übersprungen."
        )
        return False

    source = None
    destination = None

    try:
        source = sqlite3.connect(
            str(DB_PATH),
            timeout=10,
        )

        source.execute(
            "PRAGMA busy_timeout=10000;"
        )

        try:
            source.execute(
                "PRAGMA wal_checkpoint(FULL);"
            )
        except sqlite3.Error:
            # Die SQLite Backup API funktioniert
            # trotzdem konsistent.
            pass

        destination = sqlite3.connect(
            str(backup_database_path)
        )

        source.backup(destination)
        destination.commit()

        ok("SQLite database backup created")
        return True

    except sqlite3.Error as error:
        fail(
            "Database backup failed: "
            f"{type(error).__name__}: {error}"
        )

    finally:
        if destination is not None:
            destination.close()

        if source is not None:
            source.close()


# =========================================================
# STATE BACKUP
# =========================================================

def backup_state_files(backup_directory):
    backed_up = []

    for file_name in (
        STATE_FILES
        + TEMP_STATE_FILES
    ):
        source = (
            PROJECT_ROOT
            / file_name
        )

        if not source.exists():
            continue

        destination = (
            backup_directory
            / file_name
        )

        shutil.copy2(
            source,
            destination,
        )

        backed_up.append(file_name)
        ok(f"Backed up: {file_name}")

    return backed_up


# =========================================================
# DATABASE RESET
# =========================================================

def reset_database():
    if not DB_PATH.exists():
        warn(
            "evilnae.db existiert nicht. "
            "Database reset wird übersprungen."
        )
        return {}

    connection = None
    before_counts = {}

    try:
        connection = sqlite3.connect(
            str(DB_PATH),
            timeout=10,
        )

        connection.execute(
            "PRAGMA busy_timeout=10000;"
        )

        # -------------------------------------------------
        # Integrity BEFORE reset
        # -------------------------------------------------

        if not database_integrity_ok(connection):
            fail(
                "evilnae.db integrity check failed "
                "BEFORE reset. Nothing was deleted."
            )

        ok("Database integrity before reset: OK")

        # -------------------------------------------------
        # Count all persistent memory first
        # -------------------------------------------------

        for table in MEMORY_TABLES:
            before_counts[table] = (
                get_table_count(
                    connection,
                    table,
                )
            )

        # -------------------------------------------------
        # One transaction:
        # either all DB memory gets cleared
        # or nothing gets committed.
        # -------------------------------------------------

        connection.execute(
            "BEGIN IMMEDIATE;"
        )

        for table in MEMORY_TABLES:
            if not table_exists(
                connection,
                table,
            ):
                warn(
                    f"Table not found: {table}"
                )
                continue

            connection.execute(
                f'DELETE FROM "{table}"'
            )

            ok(
                f"Cleared table: {table}"
            )

        # Reset AUTOINCREMENT entries for any
        # reset table that uses sqlite_sequence.
        if table_exists(
            connection,
            "sqlite_sequence",
        ):
            for table in MEMORY_TABLES:
                connection.execute(
                    """
                    DELETE FROM sqlite_sequence
                    WHERE name = ?
                    """,
                    (table,),
                )

            ok(
                "Reset matching AUTOINCREMENT sequences"
            )

        connection.commit()

        # -------------------------------------------------
        # Verify tables are empty
        # -------------------------------------------------

        for table in MEMORY_TABLES:
            if not table_exists(
                connection,
                table,
            ):
                continue

            remaining = get_table_count(
                connection,
                table,
            )

            if remaining != 0:
                fail(
                    f"Table {table} still contains "
                    f"{remaining} rows after reset."
                )

        # -------------------------------------------------
        # Integrity AFTER reset
        # -------------------------------------------------

        if not database_integrity_ok(connection):
            fail(
                "evilnae.db integrity check failed "
                "AFTER reset."
            )

        ok("Database integrity after reset: OK")

        return before_counts

    except sqlite3.OperationalError as error:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

        fail(
            "SQLite operation failed. "
            "Make sure bot.py is completely stopped. "
            f"Error: {error}"
        )

    except sqlite3.Error as error:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

        fail(
            "SQLite reset failed: "
            f"{type(error).__name__}: {error}"
        )

    finally:
        if connection is not None:
            connection.close()


# =========================================================
# REMOVE LEARNED / RUNTIME STATE
# =========================================================
#
# Wir schreiben keine eigenen Defaults.
#
# Beim nächsten Start laden die jeweiligen Module
# ihre offiziellen Defaults / Seed-Daten aus dem Code.
# =========================================================

def reset_state_files():
    removed = []

    for file_name in (
        STATE_FILES
        + TEMP_STATE_FILES
    ):
        path = (
            PROJECT_ROOT
            / file_name
        )

        if not path.exists():
            continue

        try:
            path.unlink()
        except OSError as error:
            fail(
                f"Could not remove {file_name}: "
                f"{type(error).__name__}: {error}"
            )

        removed.append(file_name)
        ok(f"Reset state: {file_name}")

    return removed


# =========================================================
# VERIFY STATE RESET
# =========================================================

def verify_state_reset():
    leftovers = []

    for file_name in (
        STATE_FILES
        + TEMP_STATE_FILES
    ):
        path = (
            PROJECT_ROOT
            / file_name
        )

        if path.exists():
            leftovers.append(file_name)

    if leftovers:
        fail(
            "Some state files still exist after reset: "
            + ", ".join(leftovers)
        )

    ok("Persistent learning/runtime state files cleared")


# =========================================================
# MANIFEST
# =========================================================

def write_manifest(
    backup_directory,
    *,
    database_counts,
    backed_up_files,
    removed_files,
):
    manifest = {
        "reset_version": RESET_VERSION,
        "created_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "project_root": str(PROJECT_ROOT),
        "database": {
            "path": str(DB_PATH),
            "cleared_tables": database_counts,
        },
        "state_files_backed_up": backed_up_files,
        "state_files_reset": removed_files,
        "preserved": [
            "source code",
            ".env",
            "Discord exports",
            "Git repository",
            "character prompts/lore in code",
            (
                "Hanae fixed sister relationship "
                "defined by code"
            ),
            (
                "Self Model fixed/core seeds "
                "defined in self_model.py"
            ),
            (
                "Voice Memory seed examples "
                "defined in voice_memory.py"
            ),
        ],
    }

    manifest_path = (
        backup_directory
        / "reset_manifest.json"
    )

    with open(
        manifest_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )

    ok("Reset manifest created")


# =========================================================
# PRINT DATABASE COUNTS
# =========================================================

def print_database_counts(counts):
    print("")
    print("Persistent DB rows before reset:")

    for table in MEMORY_TABLES:
        value = counts.get(table)

        if value is None:
            display = "table missing"
        else:
            display = str(value)

        print(
            f"  {table:<20} {display}"
        )


# =========================================================
# MAIN
# =========================================================

def main():
    header(
        "EVILNAE DEVELOPMENT MEMORY RESET"
    )

    print(f"Reset Version: {RESET_VERSION}")
    print(f"Project: {PROJECT_ROOT}")
    print("")

    print(
        "Dieser Reset entfernt Evilnaes "
        "gespeicherte Development-/Test-Erfahrungen."
    )

    print("")
    print("WIRD ZURÜCKGESETZT:")

    for table in MEMORY_TABLES:
        print(
            f"  [DB] {table}"
        )

    for file_name in STATE_FILES:
        print(
            f"  [STATE] {file_name}"
        )

    print("")
    print("BLEIBT ERHALTEN:")
    print("  [KEEP] Source Code")
    print("  [KEEP] .env")
    print("  [KEEP] Character / SYSTEM_PROMPT")
    print("  [KEEP] feste Character-Lore")
    print("  [KEEP] Hanae Sister Relationship aus Code")
    print("  [KEEP] Self-Model Core Seeds aus self_model.py")
    print("  [KEEP] Voice-Memory Seeds aus voice_memory.py")
    print("  [KEEP] Git / Repository")
    print("  [KEEP] Discord Exports / Logs")

    print("")
    print(
        "WICHTIG: bot.py muss vollständig AUS sein."
    )
    print("")

    confirmation = input(
        "Zum Reset exakt RESET EVILNAE eingeben: "
    ).strip()

    if confirmation != "RESET EVILNAE":
        print("")
        print(
            "Reset abgebrochen. "
            "Es wurde nichts verändert."
        )
        return

    # -----------------------------------------------------
    # CREATE BACKUP DIRECTORY
    # -----------------------------------------------------

    timestamp = (
        datetime.now()
        .astimezone()
        .strftime("%Y%m%d-%H%M%S")
    )

    backup_directory = (
        BACKUP_ROOT
        / timestamp
    )

    backup_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    print("")
    info(
        f"Backup directory: {backup_directory}"
    )

    # -----------------------------------------------------
    # BACKUP DATABASE
    # -----------------------------------------------------

    database_backup_path = (
        backup_directory
        / "evilnae.db"
    )

    backup_database(
        database_backup_path
    )

    # -----------------------------------------------------
    # BACKUP JSON / STATE FILES
    # -----------------------------------------------------

    backed_up_files = (
        backup_state_files(
            backup_directory
        )
    )

    # -----------------------------------------------------
    # RESET DATABASE
    # -----------------------------------------------------

    header(
        "RESETTING DATABASE MEMORY"
    )

    database_counts = (
        reset_database()
    )

    print_database_counts(
        database_counts
    )

    # -----------------------------------------------------
    # RESET LEARNING / RUNTIME STATE
    # -----------------------------------------------------

    header(
        "RESETTING LEARNING / RUNTIME STATE"
    )

    removed_files = (
        reset_state_files()
    )

    verify_state_reset()

    # -----------------------------------------------------
    # MANIFEST
    # -----------------------------------------------------

    write_manifest(
        backup_directory,
        database_counts=database_counts,
        backed_up_files=backed_up_files,
        removed_files=removed_files,
    )

    # -----------------------------------------------------
    # FINAL
    # -----------------------------------------------------

    header(
        "EVILNAE RESET COMPLETE"
    )

    print(
        "Evilnaes gespeicherte Development-"
        "Erfahrungen wurden zurückgesetzt."
    )

    print("")
    print(
        "Beim nächsten Start bekommt Evilnae:"
    )
    print("  [✓] frischen Inner State")
    print("  [✓] Reflection Defaults")
    print("  [✓] Voice Memory Seeds")
    print("  [✓] frische Initiative")
    print("  [✓] frische Social Actions")
    print("  [✓] frisches Self Model")
    print("  [✓] feste Self-Model Core Seeds")
    print("  [✓] leere User Memories")
    print("  [✓] leere User Impressions")
    print("  [✓] leere Conversation Buffers")
    print("  [✓] leere Relationship-Werte")

    print("")
    print("Nicht verändert:")
    print("  [✓] Evilnae Character / Code")
    print("  [✓] SYSTEM_PROMPT")
    print("  [✓] feste Character-Lore")
    print("  [✓] Hanae Sister Relationship aus Code")

    print("")
    print("Backup:")
    print(f"  {backup_directory}")

    print("")
    print("NEXT:")
    print("  python bot.py")
    print("")


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":
    main()

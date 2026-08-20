import sqlite3
import threading


# =========================================================
# DATABASE CONFIG
# =========================================================

DB_PATH = "evilnae.db"

db_lock = threading.RLock()

conn = sqlite3.connect(
    DB_PATH,
    timeout=30,
    check_same_thread=False
)

conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")
conn.execute("PRAGMA busy_timeout=30000;")


# =========================================================
# HELPERS
# =========================================================

def column_exists(table_name, column_name):

    with db_lock:
        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

    return any(
        row[1] == column_name
        for row in rows
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():

    with db_lock:

        # =========================
        # RELATIONSHIPS
        # =========================

        conn.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            user_id TEXT PRIMARY KEY,
            affection INTEGER DEFAULT 0,
            annoyance INTEGER DEFAULT 0,
            interest INTEGER DEFAULT 0
        )
        """)

        # =========================
        # SUMMARIES
        # =========================

        conn.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            user_id TEXT,
            memory TEXT
        )
        """)

        # =========================
        # USER BUFFER
        # =========================

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_buffers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """)

        # =========================
        # USER PROFILE
        # =========================

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            profile TEXT DEFAULT ''
        )
        """)

        # =========================
        # USER IMPRESSION
        # =========================

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_impressions (
            user_id TEXT PRIMARY KEY,
            impression TEXT DEFAULT ''
        )
        """)

        # =========================
        # MEMORY ARCHIVE
        # =========================

        conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_archives (
            user_id TEXT PRIMARY KEY,
            archive TEXT DEFAULT ''
        )
        """)

        conn.commit()

    # -----------------------------------------------------
    # MIGRATION FÜR ÄLTERE DATENBANK
    # -----------------------------------------------------

    if not column_exists(
        "user_profiles",
        "username"
    ):

        with db_lock:

            conn.execute("""
            ALTER TABLE user_profiles
            ADD COLUMN username TEXT
            """)

            conn.commit()

    # -----------------------------------------------------
    # INDEXES
    # -----------------------------------------------------

    with db_lock:

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_summaries_user
        ON summaries(user_id)
        """)

        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_buffers_user
        ON user_buffers(user_id)
        """)

        conn.commit()


initialize_database()


# =========================================================
# RELATIONSHIPS
# =========================================================

def get_relationship(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT
            affection,
            annoyance,
            interest
        FROM relationships
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

        if row:

            return {
                "affection": row[0],
                "annoyance": row[1],
                "interest": row[2]
            }

        conn.execute("""
        INSERT INTO relationships (
            user_id,
            affection,
            annoyance,
            interest
        )
        VALUES (?, 0, 0, 0)
        """, (
            user_id,
        ))

        conn.commit()

    return {
        "affection": 0,
        "annoyance": 0,
        "interest": 0
    }


def update_relationship(
    user_id,
    affection,
    annoyance,
    interest
):

    user_id = str(user_id)

    with db_lock:

        conn.execute("""
        INSERT INTO relationships (
            user_id,
            affection,
            annoyance,
            interest
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            affection = excluded.affection,
            annoyance = excluded.annoyance,
            interest = excluded.interest
        """, (
            user_id,
            affection,
            annoyance,
            interest
        ))

        conn.commit()


# =========================================================
# SUMMARIES
# =========================================================

def add_summary(
    user_id,
    memory
):

    user_id = str(user_id)

    if memory is None:
        return

    memory = str(memory).strip()

    if not memory:
        return

    with db_lock:

        conn.execute("""
        INSERT INTO summaries (
            user_id,
            memory
        )
        VALUES (?, ?)
        """, (
            user_id,
            memory
        ))

        conn.commit()


def get_summaries(user_id):

    user_id = str(user_id)

    with db_lock:

        rows = conn.execute("""
        SELECT memory
        FROM summaries
        WHERE user_id = ?
        ORDER BY rowid ASC
        """, (
            user_id,
        )).fetchall()

    return [
        row[0]
        for row in rows
        if row[0]
    ]


def get_latest_summaries(
    user_id,
    limit=5
):

    user_id = str(user_id)
    limit = max(1, int(limit))

    with db_lock:

        rows = conn.execute("""
        SELECT memory
        FROM summaries
        WHERE user_id = ?
        ORDER BY rowid DESC
        LIMIT ?
        """, (
            user_id,
            limit
        )).fetchall()

    memories = [
        row[0]
        for row in rows
        if row[0]
    ]

    memories.reverse()

    return memories


def get_summary_count(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT COUNT(*)
        FROM summaries
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    if not row:
        return 0

    return int(row[0])


def get_oldest_summaries(
    user_id,
    limit=8
):

    user_id = str(user_id)
    limit = max(1, int(limit))

    with db_lock:

        rows = conn.execute("""
        SELECT
            rowid,
            memory
        FROM summaries
        WHERE user_id = ?
        ORDER BY rowid ASC
        LIMIT ?
        """, (
            user_id,
            limit
        )).fetchall()

    return [
        {
            "rowid": row[0],
            "memory": row[1]
        }
        for row in rows
        if row[1]
    ]


def delete_summaries_by_rowids(rowids):

    if not rowids:
        return

    placeholders = ",".join(
        "?"
        for _ in rowids
    )

    with db_lock:

        conn.execute(
            f"""
            DELETE FROM summaries
            WHERE rowid IN ({placeholders})
            """,
            tuple(rowids)
        )

        conn.commit()


# =========================================================
# USER BUFFER
# =========================================================

def add_buffer_message(
    user_id,
    message
):

    user_id = str(user_id)

    if message is None:
        return

    message = str(message).strip()

    if not message:
        return

    with db_lock:

        conn.execute("""
        INSERT INTO user_buffers (
            user_id,
            message
        )
        VALUES (?, ?)
        """, (
            user_id,
            message
        ))

        conn.commit()


def get_buffer_messages(user_id):

    user_id = str(user_id)

    with db_lock:

        rows = conn.execute("""
        SELECT message
        FROM user_buffers
        WHERE user_id = ?
        ORDER BY id ASC
        """, (
            user_id,
        )).fetchall()

    return [
        row[0]
        for row in rows
    ]


def get_buffer_count(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT COUNT(*)
        FROM user_buffers
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    if not row:
        return 0

    return int(row[0])


def get_buffer_batch(
    user_id,
    limit
):

    user_id = str(user_id)
    limit = max(1, int(limit))

    with db_lock:

        rows = conn.execute("""
        SELECT
            id,
            message
        FROM user_buffers
        WHERE user_id = ?
        ORDER BY id ASC
        LIMIT ?
        """, (
            user_id,
            limit
        )).fetchall()

    return [
        {
            "id": row[0],
            "message": row[1]
        }
        for row in rows
    ]


def delete_buffer_messages_by_ids(ids):

    if not ids:
        return

    placeholders = ",".join(
        "?"
        for _ in ids
    )

    with db_lock:

        conn.execute(
            f"""
            DELETE FROM user_buffers
            WHERE id IN ({placeholders})
            """,
            tuple(ids)
        )

        conn.commit()


def clear_buffer(user_id):

    user_id = str(user_id)

    with db_lock:

        conn.execute("""
        DELETE FROM user_buffers
        WHERE user_id = ?
        """, (
            user_id,
        ))

        conn.commit()


# =========================================================
# USER PROFILE
# =========================================================

def set_username(
    user_id,
    username
):

    user_id = str(user_id)

    if username is None:
        username = ""

    username = str(username).strip()

    with db_lock:

        conn.execute("""
        INSERT INTO user_profiles (
            user_id,
            username,
            profile
        )
        VALUES (?, ?, '')

        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username
        """, (
            user_id,
            username
        ))

        conn.commit()


def get_username(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT username
        FROM user_profiles
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    if not row:
        return ""

    return row[0] or ""


def get_profile(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT profile
        FROM user_profiles
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    if not row:
        return ""

    return row[0] or ""


def update_profile(
    user_id,
    profile
):

    user_id = str(user_id)

    if profile is None:
        profile = ""

    profile = str(profile).strip()

    with db_lock:

        conn.execute("""
        INSERT INTO user_profiles (
            user_id,
            profile
        )
        VALUES (?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            profile = excluded.profile
        """, (
            user_id,
            profile
        ))

        conn.commit()


# =========================================================
# USER IMPRESSION
# =========================================================

def get_impression(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT impression
        FROM user_impressions
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    if not row:
        return ""

    return row[0] or ""


def update_impression(
    user_id,
    impression
):

    user_id = str(user_id)

    if impression is None:
        impression = ""

    impression = str(impression).strip()

    with db_lock:

        conn.execute("""
        INSERT INTO user_impressions (
            user_id,
            impression
        )
        VALUES (?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            impression = excluded.impression
        """, (
            user_id,
            impression
        ))

        conn.commit()


# =========================================================
# MEMORY ARCHIVE
# =========================================================

def get_memory_archive(user_id):

    user_id = str(user_id)

    with db_lock:

        row = conn.execute("""
        SELECT archive
        FROM memory_archives
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    if not row:
        return ""

    return row[0] or ""


def update_memory_archive(
    user_id,
    archive
):

    user_id = str(user_id)

    if archive is None:
        archive = ""

    archive = str(archive).strip()

    with db_lock:

        conn.execute("""
        INSERT INTO memory_archives (
            user_id,
            archive
        )
        VALUES (?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            archive = excluded.archive
        """, (
            user_id,
            archive
        ))

        conn.commit()


# =========================================================
# DEBUG / STATS
# =========================================================

def get_user_memory_stats(user_id):

    user_id = str(user_id)

    with db_lock:

        summary_count = conn.execute("""
        SELECT COUNT(*)
        FROM summaries
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()[0]

        buffer_count = conn.execute("""
        SELECT COUNT(*)
        FROM user_buffers
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()[0]

        profile_row = conn.execute("""
        SELECT
            username,
            profile
        FROM user_profiles
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

        impression_row = conn.execute("""
        SELECT impression
        FROM user_impressions
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

        archive_row = conn.execute("""
        SELECT archive
        FROM memory_archives
        WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

    return {
        "user_id": user_id,

        "username": (
            profile_row[0]
            if profile_row and profile_row[0]
            else ""
        ),

        "summary_count": int(
            summary_count
        ),

        "buffer_count": int(
            buffer_count
        ),

        "has_profile": bool(
            profile_row
            and profile_row[1]
        ),

        "has_impression": bool(
            impression_row
            and impression_row[0]
        ),

        "has_archive": bool(
            archive_row
            and archive_row[0]
        )
    }


def close_database():

    with db_lock:

        conn.commit()
        conn.close()
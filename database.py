import sqlite3

# Verbindung zur Datenbank
conn = sqlite3.connect("evilnae.db")

# Cursor für SQL Befehle
cursor = conn.cursor()

# User Relationship Tabelle
cursor.execute("""
CREATE TABLE IF NOT EXISTS relationships (
    user_id TEXT PRIMARY KEY,
    affection INTEGER DEFAULT 0,
    annoyance INTEGER DEFAULT 0,
    interest INTEGER DEFAULT 0
)
""")

# Langzeit Memory Tabelle
cursor.execute("""
CREATE TABLE IF NOT EXISTS summaries (
    user_id TEXT,
    memory TEXT
)
""")

try:
    cursor.execute("""
    ALTER TABLE user_profiles
    ADD COLUMN username TEXT
    """)
except:
    pass

# User Message Buffer
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_buffers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    message TEXT
)
""")

try:
    cursor.execute("""
    ALTER TABLE user_profiles
    ADD COLUMN username TEXT
    """)
except:
    pass

# Dauerhaftes User Profil
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    profile TEXT
)
""")

try:
    cursor.execute("""
    ALTER TABLE user_profiles
    ADD COLUMN username TEXT
    """)
except:
    pass

# Evilnaes Eindruck
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_impressions (
    user_id TEXT PRIMARY KEY,
    impression TEXT
)
""")

try:
    cursor.execute("""
    ALTER TABLE user_profiles
    ADD COLUMN username TEXT
    """)
except:
    pass

conn.commit()


# =========================
# RELATIONSHIPS
# =========================

def get_relationship(user_id):

    cursor.execute(
        "SELECT affection, annoyance, interest FROM relationships WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return {
            "affection": result[0],
            "annoyance": result[1],
            "interest": result[2]
        }

    # Falls User noch nicht existiert
    cursor.execute(
        "INSERT INTO relationships (user_id) VALUES (?)",
        (user_id,)
    )

    conn.commit()

    return {
        "affection": 0,
        "annoyance": 0,
        "interest": 0
    }


def update_relationship(user_id, affection, annoyance, interest):

    cursor.execute("""
    UPDATE relationships
    SET affection = ?, annoyance = ?, interest = ?
    WHERE user_id = ?
    """, (affection, annoyance, interest, user_id))

    conn.commit()


# =========================
# SUMMARIES
# =========================

def add_summary(user_id, memory):

    cursor.execute(
        "INSERT INTO summaries (user_id, memory) VALUES (?, ?)",
        (user_id, memory)
    )

    conn.commit()


def get_summaries(user_id):

    cursor.execute(
        "SELECT memory FROM summaries WHERE user_id = ?",
        (user_id,)
    )

    results = cursor.fetchall()

    return [row[0] for row in results]
# =========================
# USER BUFFER
# =========================

def add_buffer_message(user_id, message):

    cursor.execute(
        "INSERT INTO user_buffers (user_id, message) VALUES (?, ?)",
        (user_id, message)
    )

    conn.commit()


def get_buffer_messages(user_id):

    cursor.execute(
        "SELECT message FROM user_buffers WHERE user_id = ?",
        (user_id,)
    )

    results = cursor.fetchall()

    return [row[0] for row in results]


def clear_buffer(user_id):

    cursor.execute(
        "DELETE FROM user_buffers WHERE user_id = ?",
        (user_id,)
    )

    conn.commit()

    # =========================
# USER PROFILE
# =========================

def set_username(user_id, username):

    cursor.execute("""
    INSERT OR REPLACE INTO user_profiles
    (user_id, username, profile)
    VALUES (
        ?,
        ?,
        COALESCE(
            (
                SELECT profile
                FROM user_profiles
                WHERE user_id = ?
            ),
            ''
        )
    )
    """, (
        user_id,
        username,
        user_id
    ))

    conn.commit()


def get_username(user_id):

    cursor.execute(
        "SELECT username FROM user_profiles WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return ""

def get_profile(user_id):

    cursor.execute(
        "SELECT profile FROM user_profiles WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return ""


def update_profile(user_id, profile):

    cursor.execute("""
    INSERT OR REPLACE INTO user_profiles
    (user_id, profile)
    VALUES (?, ?)
    """, (user_id, profile))

    conn.commit()

    # =========================
# USER IMPRESSION
# =========================

def get_impression(user_id):

    cursor.execute(
        "SELECT impression FROM user_impressions WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return ""


def update_impression(user_id, impression):

    cursor.execute("""
    INSERT OR REPLACE INTO user_impressions
    (user_id, impression)
    VALUES (?, ?)
    """, (user_id, impression))

    conn.commit()

def get_latest_summaries(user_id, limit=5):

    cursor.execute("""
    SELECT memory
    FROM summaries
    WHERE user_id = ?
    ORDER BY rowid DESC
    LIMIT ?
    """, (user_id, limit))

    results = cursor.fetchall()

    return [row[0] for row in results]   
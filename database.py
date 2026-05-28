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
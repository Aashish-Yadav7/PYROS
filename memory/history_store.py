"""
memory/history_store.py

Structured memory: conversations, people, and feedback. SQLite, local file
at pyros_data/history.db.

New in this version:
- keyword search across past conversations (fast, exact-text — complements
  the vector store's meaning-based search)
- export conversation history to a readable text file (backup/audit)
- tagging messages (e.g. "gmail", "reminder") for later filtering
- person "last_seen" tracking, useful once face recognition is wired in
"""
import sqlite3
import uuid
import datetime
import os

DB_PATH = os.path.join("pyros_data", "history.db")


def _connect():
    os.makedirs("pyros_data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tag TEXT DEFAULT 'general',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            notes TEXT,
            face_embedding BLOB,
            last_seen TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            rating TEXT NOT NULL,
            correction TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_message(role: str, content: str, tag: str = "general") -> str:
    conn = _connect()
    msg_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO conversations (id, role, content, tag, created_at) VALUES (?, ?, ?, ?, ?)",
        (msg_id, role, content, tag, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return msg_id


def get_recent_messages(limit: int = 20) -> list:
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content FROM conversations ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def search_messages(keyword: str, limit: int = 20) -> list:
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content, created_at FROM conversations WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
        (f"%{keyword}%", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages_by_tag(tag: str, limit: int = 50) -> list:
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content, created_at FROM conversations WHERE tag = ? ORDER BY created_at DESC LIMIT ?",
        (tag, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def export_history(filepath: str = "pyros_data/export.txt"):
    conn = _connect()
    rows = conn.execute("SELECT role, content, created_at FROM conversations ORDER BY created_at ASC").fetchall()
    conn.close()
    with open(filepath, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(f"[{r['created_at']}] {r['role'].upper()}: {r['content']}\n\n")
    return filepath


def clear_conversations():
    conn = _connect()
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()


def add_person(name: str, notes: str = "", face_embedding: bytes = None) -> str:
    conn = _connect()
    person_id = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO people (id, name, notes, face_embedding, last_seen, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (person_id, name, notes, face_embedding, now, now),
    )
    conn.commit()
    conn.close()
    return person_id


def mark_person_seen(name: str):
    conn = _connect()
    conn.execute(
        "UPDATE people SET last_seen = ? WHERE name = ?",
        (datetime.datetime.now().isoformat(), name),
    )
    conn.commit()
    conn.close()


def get_person_by_name(name: str):
    conn = _connect()
    row = conn.execute("SELECT * FROM people WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_people() -> list:
    conn = _connect()
    rows = conn.execute("SELECT * FROM people").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_person(name: str):
    conn = _connect()
    conn.execute("DELETE FROM people WHERE name = ?", (name,))
    conn.commit()
    conn.close()


def add_feedback(message_id: str, rating: str, correction: str = "") -> str:
    conn = _connect()
    fb_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO feedback (id, message_id, rating, correction, created_at) VALUES (?, ?, ?, ?, ?)",
        (fb_id, message_id, rating, correction, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return fb_id


def get_negative_feedback_examples(limit: int = 10) -> list:
    conn = _connect()
    rows = conn.execute(
        "SELECT message_id, correction FROM feedback WHERE rating = 'down' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def feedback_stats() -> dict:
    conn = _connect()
    up = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating = 'up'").fetchone()[0]
    down = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating = 'down'").fetchone()[0]
    conn.close()
    total = up + down
    approval_rate = round((up / total) * 100, 1) if total else None
    return {"up": up, "down": down, "approval_rate_percent": approval_rate}
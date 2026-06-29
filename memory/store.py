import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "thoth.db")

class MemoryStore:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                path TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def get_or_create_session(self, session_id):
        now = datetime.utcnow().isoformat()
        cur = self.conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if cur.fetchone() is None:
            self.conn.execute(
                "INSERT INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
                (session_id, now, now),
            )
            self.conn.commit()

    def save_message(self, session_id, role, content):
        self.get_or_create_session(session_id)
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
        )
        self.conn.commit()

    def get_history(self, session_id, limit=50):
        cur = self.conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit),
        )
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def save_document(self, name, doc_type, content=None, path=None):
        now = datetime.utcnow().isoformat()
        self.conn.execute(
            "INSERT INTO documents (name, type, content, path, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, doc_type, content, path, now),
        )
        self.conn.commit()

    def get_documents(self, doc_type=None):
        if doc_type:
            cur = self.conn.execute(
                "SELECT id, name, type, path, created_at FROM documents WHERE type = ? ORDER BY created_at DESC",
                (doc_type,),
            )
        else:
            cur = self.conn.execute(
                "SELECT id, name, type, path, created_at FROM documents ORDER BY created_at DESC"
            )
        return cur.fetchall()

    def close(self):
        self.conn.close()

import sqlite3
import json
import os
import threading
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "thoth.db")

class MemoryStore:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
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
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'general',
                source_session TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            cur = self.conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            if cur.fetchone() is None:
                self.conn.execute(
                    "INSERT INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
                    (session_id, now, now),
                )
                self.conn.commit()

    def save_message(self, session_id, role, content):
        with self._lock:
            self.get_or_create_session(session_id)
            now = datetime.now(timezone.utc).isoformat()
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

    def save_fact(self, fact, category="general", source_session=None):
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            try:
                cur = self.conn.execute(
                    "INSERT INTO facts (fact, category, source_session, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (fact, category, source_session, now, now),
                )
                self.conn.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                self.conn.execute(
                    "UPDATE facts SET updated_at = ? WHERE fact = ?", (now, fact)
                )
                self.conn.commit()
                cur = self.conn.execute("SELECT id FROM facts WHERE fact = ?", (fact,))
                row = cur.fetchone()
                return row[0] if row else None

    def get_facts(self, search=None):
        if search:
            cur = self.conn.execute(
                "SELECT fact, category, created_at FROM facts WHERE fact LIKE ? ORDER BY updated_at DESC",
                (f"%{search}%",),
            )
        else:
            cur = self.conn.execute(
                "SELECT fact, category, created_at FROM facts ORDER BY updated_at DESC"
            )
        return [{"fact": r[0], "category": r[1], "created_at": r[2]} for r in cur.fetchall()]

    def delete_fact(self, fact):
        with self._lock:
            self.conn.execute("DELETE FROM facts WHERE fact = ?", (fact,))
            self.conn.commit()

    def clear_facts(self):
        with self._lock:
            self.conn.execute("DELETE FROM facts")
            self.conn.commit()

    def save_document(self, name, doc_type, content=None, path=None):
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
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

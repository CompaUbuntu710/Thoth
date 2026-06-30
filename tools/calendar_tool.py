import os
import json
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory", "calendar.db")

LOCKS = {}


def _get_lock(name="main"):
    if name not in LOCKS:
        LOCKS[name] = threading.Lock()
    return LOCKS[name]


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            due_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            done INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            start_at TEXT NOT NULL,
            end_at TEXT,
            source TEXT DEFAULT 'local'
        )
    """)
    conn.commit()
    return conn


def handle_reminder(action, text=None, due_at=None, reminder_id=None):
    """Gestiona recordatorios: create, list, done, delete."""
    conn = _get_conn()
    lock = _get_lock("reminders")
    now = datetime.now(timezone.utc).isoformat()

    try:
        if action == "create":
            if not text or not due_at:
                return "[Error: texto y fecha requeridos]"
            with lock:
                conn.execute(
                    "INSERT INTO reminders (text, due_at, created_at) VALUES (?, ?, ?)",
                    (text, due_at, now),
                )
                conn.commit()
            return f"[Recordatorio creado: '{text}' para {due_at}]"

        elif action == "list":
            with lock:
                rows = conn.execute(
                    "SELECT id, text, due_at, done FROM reminders ORDER BY due_at ASC LIMIT 20"
                ).fetchall()
            if not rows:
                return "[No hay recordatorios]"
            lines = []
            for r in rows:
                status = "✓" if r[3] else "○"
                lines.append(f"  {status} #{r[0]}: {r[1]} (para {r[2]})")
            return "Recordatorios:\n" + "\n".join(lines)

        elif action == "done":
            if reminder_id is None:
                return "[Error: id requerido]"
            with lock:
                conn.execute("UPDATE reminders SET done=1 WHERE id=?", (reminder_id,))
                conn.commit()
            return f"[Recordatorio #{reminder_id} marcado como completado]"

        elif action == "delete":
            if reminder_id is None:
                return "[Error: id requerido]"
            with lock:
                conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
                conn.commit()
            return f"[Recordatorio #{reminder_id} eliminado]"

        return f"[Error: acción '{action}' no válida. Usa: create, list, done, delete]"
    except Exception as e:
        return f"[Error en recordatorio: {e}]"


def handle_alarm(text, due_at):
    """Crea una alarma absoluta."""
    return handle_reminder("create", text=text, due_at=due_at)


def handle_calendar(action, title=None, description="", start_at=None, end_at=None, event_id=None):
    """Gestiona eventos de calendario: create, list, delete."""
    conn = _get_conn()
    lock = _get_lock("calendar")

    try:
        if action == "create":
            if not title or not start_at:
                return "[Error: título y fecha de inicio requeridos]"
            with lock:
                conn.execute(
                    "INSERT INTO events (title, description, start_at, end_at) VALUES (?, ?, ?, ?)",
                    (title, description, start_at, end_at),
                )
                conn.commit()
            return f"[Evento creado: '{title}' para {start_at}]"

        elif action == "list":
            with lock:
                rows = conn.execute(
                    "SELECT id, title, start_at, end_at FROM events ORDER BY start_at ASC LIMIT 20"
                ).fetchall()
            if not rows:
                return "[No hay eventos de calendario]"
            lines = []
            for r in rows:
                    end_str = f" → {r[3]}" if r[3] else ""
                    lines.append(f"  #{r[0]}: {r[1]} ({r[2]}{end_str})")
            return "Calendario:\n" + "\n".join(lines)

        elif action == "delete":
            if event_id is None:
                return "[Error: id requerido]"
            with lock:
                conn.execute("DELETE FROM events WHERE id=?", (event_id,))
                conn.commit()
            return f"[Evento #{event_id} eliminado]"

        return "[Error: acción no válida. Usa: create, list, delete]"
    except Exception as e:
        return f"[Error en calendario: {e}]"


# ─── Background reminder checker ───

_checker_running = False


def _check_reminders_loop(engine=None):
    global _checker_running
    _checker_running = True
    conn = _get_conn()
    lock = _get_lock("reminders")
    while _checker_running:
        try:
            now = datetime.now(timezone.utc).isoformat()
            with lock:
                due = conn.execute(
                    "SELECT id, text FROM reminders WHERE done=0 AND due_at <= ?",
                    (now,),
                ).fetchall()
                if due:
                    for r in due:
                        conn.execute("UPDATE reminders SET done=1 WHERE id=?", (r[0],))
                    conn.commit()
            if due and engine:
                for r in due:
                    msg = f"[ALARMA] {r[1]}"
                    engine.remember(f"Recordatorio cumplido: {r[1]}", "sistema")
                    if hasattr(engine, '_send_notification'):
                        engine._send_notification(msg)
        except Exception:
            pass
        time.sleep(30)


def start_reminder_checker(engine=None):
    t = threading.Thread(target=_check_reminders_loop, args=(engine,), daemon=True)
    t.start()
    return t


def stop_reminder_checker():
    global _checker_running
    _checker_running = False


# Initialize DB on import
_get_conn()

import os
import json
import sqlite3
import threading
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory", "observability.db")

_lock = threading.Lock()

COST_PER_M_TOKENS = {
    "groq": {"llama-3.3-70b-versatile": 0.59, "llama-3.1-8b-instant": 0.05},
    "openrouter": {"openai/gpt-4o": 2.50, "openai/gpt-4o-mini": 0.15},
    "nvidia": {"meta/llama-3.1-70b-instruct": 0.50, "meta/llama-3.1-8b-instruct": 0.05},
    "together": {"mistralai/Mixtral-8x22B-Instruct-v0.1": 0.45, "mistralai/Mistral-7B-Instruct-v0.2": 0.04},
}


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            agent TEXT DEFAULT 'thoth',
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            error TEXT DEFAULT '',
            session_id TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            traceback TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def log_usage(provider, model, agent, prompt_tokens, completion_tokens, cost=None, error="", session_id=""):
    total = prompt_tokens + completion_tokens
    if cost is None:
        model_costs = COST_PER_M_TOKENS.get(provider, {})
        rate = model_costs.get(model, 0.10)
        cost = (total / 1_000_000) * rate
    with _lock:
        conn = _get_conn()
        conn.execute(
            """INSERT INTO usage_log
               (timestamp, provider, model, agent, prompt_tokens, completion_tokens, total_tokens, cost, error, session_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), provider, model, agent,
             prompt_tokens, completion_tokens, total, round(cost, 6), error, session_id),
        )
        conn.commit()


def log_error(source, message, traceback=""):
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO error_log (timestamp, source, message, traceback) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), source, message[:500], traceback[:2000]),
        )
        conn.commit()


def get_usage_summary(hours=24):
    conn = _get_conn()
    cur = conn.execute(
        """SELECT provider, model,
                  COUNT(*) as requests,
                  SUM(prompt_tokens) as prompt_tokens,
                  SUM(completion_tokens) as completion_tokens,
                  SUM(total_tokens) as total_tokens,
                  SUM(cost) as total_cost,
                  SUM(CASE WHEN error != '' THEN 1 ELSE 0 END) as errors
           FROM usage_log
           WHERE timestamp >= datetime('now', ?)
           GROUP BY provider, model
           ORDER BY total_cost DESC""",
        (f"-{hours} hours",),
    )
    rows = cur.fetchall()
    return {
        "period_hours": hours,
        "providers": [
            {
                "provider": r[0],
                "model": r[1],
                "requests": r[2],
                "prompt_tokens": r[3] or 0,
                "completion_tokens": r[4] or 0,
                "total_tokens": r[5] or 0,
                "cost": round(r[6] or 0, 6),
                "errors": r[7] or 0,
            }
            for r in rows
        ],
    }


def get_error_log(limit=50):
    conn = _get_conn()
    cur = conn.execute(
        "SELECT timestamp, source, message FROM error_log ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    )
    return [
        {"timestamp": r[0], "source": r[1], "message": r[2]}
        for r in cur.fetchall()
    ]


def get_usage_chart(hours=24):
    conn = _get_conn()
    cur = conn.execute(
        """SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) as hour,
                  SUM(total_tokens) as tokens,
                  SUM(cost) as cost,
                  COUNT(*) as requests
           FROM usage_log
           WHERE timestamp >= datetime('now', ?)
           GROUP BY hour
           ORDER BY hour""",
        (f"-{hours} hours",),
    )
    return [
        {"hour": r[0], "tokens": r[1] or 0, "cost": round(r[2] or 0, 6), "requests": r[3] or 0}
        for r in cur.fetchall()
    ]


_get_conn()

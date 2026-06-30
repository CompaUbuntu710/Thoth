import os
import json
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Header
from memory.store import MemoryStore

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGO = "HS256"
JWT_EXPIRY_HOURS = 24

AUTH_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory", "auth.db")


def _get_auth_conn():
    import sqlite3
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    conn.commit()
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password):
    conn = _get_auth_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def verify_user(username, password):
    conn = _get_auth_conn()
    cur = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False


def create_token(username):
    token = secrets.token_urlsafe(48)
    expires = (datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)).isoformat()
    conn = _get_auth_conn()
    conn.execute(
        "INSERT INTO tokens (token, username, expires_at) VALUES (?, ?, ?)",
        (token, username, expires),
    )
    conn.commit()
    conn.close()
    return token, expires


def validate_token(token):
    conn = _get_auth_conn()
    cur = conn.execute(
        "SELECT username, expires_at FROM tokens WHERE token = ?",
        (token,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    username, expires_at = row
    if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at):
        return None
    return username


async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Formato: Bearer <token>")
    username = validate_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return username

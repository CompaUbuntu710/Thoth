import os
import time
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from core.engine import ThothEngine
from memory.store import MemoryStore
from pydantic import BaseModel
from api.ws_manager import ws_manager
from api.telegram_bot import start_bot, init_engine

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")

app = FastAPI()
store = MemoryStore()
engine = ThothEngine(store=store)
SERVER_START = time.time()
MSG_COUNT = 0

init_engine(engine)
start_bot()

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ForgetRequest(BaseModel):
    fact: str
    session_id: str = "default"

@app.get("/")
def index():
    return FileResponse(os.path.join(UI_DIR, "index.html"))

@app.get("/api/health")
def health():
    return {"status": "awakening", "message": "Thoth online"}

def _count_rows(table: str) -> int:
    try:
        row = store.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return row[0] if row else 0
    except Exception:
        return 0

@app.get("/api/sysinfo")
def sysinfo():
    uptime_s = int(time.time() - SERVER_START)
    h, m, s = uptime_s // 3600, (uptime_s % 3600) // 60, uptime_s % 60
    facts = store.get_facts()
    return {
        "uptime": f"{h:02d}:{m:02d}:{s:02d}",
        "memories": len(facts),
        "sessions": _count_rows("sessions"),
        "status": "online",
    }

@app.get("/api/stats")
def stats():
    uptime_s = int(time.time() - SERVER_START)
    h, m, s = uptime_s // 3600, (uptime_s % 3600) // 60, uptime_s % 60
    facts = store.get_facts()
    mem_usage = 0
    try:
        import psutil
        mem_usage = psutil.Process().memory_percent()
    except ImportError:
        pass
    msg_count = _count_rows("messages")
    session_count = _count_rows("sessions")
    cat_counts = store.conn.execute(
        "SELECT category, COUNT(*) as cnt FROM facts GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    status = engine.get_status()
    return {
        "provider": status["provider"],
        "model": status["model"],
        "messages": msg_count,
        "memories": len(facts),
        "sessions": session_count,
        "uptime": f"{h:02d}:{m:02d}:{s:02d}",
        "categories": {r[0]: r[1] for r in cat_counts},
        "memory_usage_pct": round(mem_usage, 1) if mem_usage else None,
        "ws_connections": ws_manager.count,
    }

@app.get("/api/sessions")
def list_sessions():
    cur = store.conn.execute(
        "SELECT id, created_at FROM sessions ORDER BY created_at DESC LIMIT 10"
    )
    return {"sessions": [{"id": r[0], "created_at": r[1]} for r in cur.fetchall()]}

@app.post("/chat")
async def chat(req: ChatRequest):
    global MSG_COUNT
    reply = await asyncio.to_thread(engine.chat, req.message, req.session_id)
    MSG_COUNT += 1
    await ws_manager.broadcast("message", {
        "session": req.session_id,
        "user_message": req.message,
        "reply": reply,
    })
    await ws_manager.broadcast("stats_update", {
        "memories": len(store.get_facts()),
        "messages": MSG_COUNT,
    })
    return {"reply": reply}

@app.get("/memories")
def memories():
    return {"facts": engine.recall()}

@app.post("/forget")
def forget(req: ForgetRequest):
    engine.forget(req.fact)
    return {"status": "ok"}

@app.post("/remember")
def remember(req: ChatRequest):
    engine.remember(req.message, "general")
    return {"status": "ok", "fact": req.message}

@app.get("/news")
def news():
    from core.tools import handle_web_search
    raw = handle_web_search("últimas noticias hoy")
    items = []
    if raw and raw != "[Sin resultados]":
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                parts = line[2:].split(": ", 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    items.append({"title": title, "source": "web"})
    if not items:
        items = [
            {"title": "Thoth online — sistema operativo", "source": "thoth"},
            {"title": "Memoria activa: " + str(len(store.get_facts())) + " registros", "source": "thoth"},
        ]
    return {"news": items[:8]}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)

app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

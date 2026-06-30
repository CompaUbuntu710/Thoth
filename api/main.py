import os
import time
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from api.auth import get_current_user
from core.engine import ThothEngine, PROVIDERS
from core.tools import TOOL_SCHEMAS, TOOL_HANDLERS
from memory.store import MemoryStore
from pydantic import BaseModel
from fastapi import UploadFile, File, Form
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
    path = os.path.join(UI_DIR, "index.html")
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(f.read())

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

@app.get("/api/history/{session_id}")
def get_history(session_id: str = "default"):
    msgs = store.get_history(session_id, limit=50)
    return {"messages": msgs}

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

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_stream():
        global MSG_COUNT
        yield f"event: start\ndata: {{\"session\": \"{req.session_id}\"}}\n\n"
        loop = asyncio.get_event_loop()
        async for event, data in _async_yield_from(loop, engine.chat_stream(req.message, req.session_id)):
            if event == "token":
                payload = json.dumps({"token": data})
                yield f"event: token\ndata: {payload}\n\n"
            elif event == "tool_calls_start":
                payload = json.dumps({"interim": data})
                yield f"event: tool_calls_start\ndata: {payload}\n\n"
            elif event == "error":
                payload = json.dumps({"error": data})
                yield f"event: error\ndata: {payload}\n\n"
            elif event == "done":
                MSG_COUNT += 1
                payload = json.dumps({"reply": data})
                yield f"event: done\ndata: {payload}\n\n"
                await ws_manager.broadcast("stats_update", {
                    "memories": len(store.get_facts()),
                    "messages": MSG_COUNT,
                })

    return StreamingResponse(event_stream(), media_type="text/event-stream")

async def _async_yield_from(loop, sync_gen):
    """Convierte un generador síncrono en async iterator."""
    for item in sync_gen:
        yield item
        await asyncio.sleep(0)

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

@app.get("/api/providers")
def list_providers():
    """Lista proveedores disponibles con su estado (key configurada o no)."""
    result = []
    for name, cfg in PROVIDERS.items():
        key = os.getenv(cfg["api_key_env"])
        result.append({
            "name": name,
            "description": cfg["description"],
            "has_key": bool(key),
            "active": name == engine.provider_name,
            "models": cfg["models"],
            "vision_model": cfg.get("vision_model"),
        })
    return {"providers": result}

@app.get("/api/tools")
def list_tools():
    """Lista todas las herramientas disponibles."""
    tools = []
    for s in TOOL_SCHEMAS:
        fn = s.get("function", {})
        tools.append({
            "name": fn.get("name"),
            "description": fn.get("description", ""),
            "parameters": list(fn.get("parameters", {}).get("properties", {}).keys()),
        })
    return {"tools": tools}

@app.get("/api/settings")
def settings_page():
    path = os.path.join(UI_DIR, "settings.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>Settings not found</h1>", status_code=404)
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.post("/api/auth/signup")
def signup(req: Request):
    body = asyncio.run(req.json())
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña requeridos")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Contraseña debe tener al menos 4 caracteres")
    from api.auth import create_user
    if create_user(username, password):
        return {"status": "ok"}
    raise HTTPException(status_code=409, detail="El usuario ya existe")

@app.post("/api/auth/login")
async def login(req: Request):
    body = await req.json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    from api.auth import verify_user, create_token
    if not verify_user(username, password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token, expires = create_token(username)
    return {"token": token, "expires": expires, "username": username}

@app.get("/api/auth/profile")
async def profile(username: str = Depends(get_current_user)):
    return {"username": username}

from memory.document_processor import document_store, UPLOAD_DIR, ensure_upload_dir

@app.get("/api/observability")
def observability(hours: int = 24):
    from core.observability import get_usage_summary, get_error_log, get_usage_chart
    return {
        "summary": get_usage_summary(hours=hours),
        "chart": get_usage_chart(hours=hours),
        "errors": get_error_log(limit=20),
    }

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    ensure_upload_dir()
    safe_name = file.filename.replace("..", "").replace("/", "").replace("\\", "")
    path = os.path.join(UPLOAD_DIR, safe_name)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    result = document_store.index_file(path, original_name=file.filename)
    return result

@app.get("/api/documents")
def list_documents_api():
    docs = document_store.list_documents()
    return {"documents": docs, "total_chunks": document_store.count()}

@app.delete("/api/documents/{file_name}")
def delete_document(file_name: str):
    ok = document_store.delete_file(file_name)
    if ok:
        doc_path = os.path.join(UPLOAD_DIR, file_name)
        if os.path.exists(doc_path):
            os.remove(doc_path)
        return {"status": "ok"}
    return {"status": "error", "message": "Documento no encontrado"}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)

app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

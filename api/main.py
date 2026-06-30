import os
import time
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import asyncio
import collections
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

# ─── Rate limiting ───
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "30"))
_rate_buckets = collections.defaultdict(list)

@app.middleware("http")
async def rate_limit_and_log(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60

    try:
        from core.ratelimit import rate_limit
        allowed = await rate_limit(ip, RATE_LIMIT, window)
    except Exception:
        allowed = None

    if allowed is False:
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit: {RATE_LIMIT} req/min. Espera un momento."}
        )
    elif allowed is None:
        _rate_buckets[ip] = [t for t in _rate_buckets[ip] if t > now - window]
        if len(_rate_buckets[ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"error": f"Rate limit: {RATE_LIMIT} req/min. Espera un momento."}
            )
        _rate_buckets[ip].append(now)

    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    log_line = f"[{time.strftime('%H:%M:%S')}] {request.method} {request.url.path} {response.status_code} {elapsed*1000:.0f}ms {ip}"
    print(log_line)
    try:
        from core.observability import _get_log_conn
        conn = _get_log_conn()
        conn.execute(
            "INSERT INTO request_log (method, path, status, elapsed_ms, ip) VALUES (?, ?, ?, ?, ?)",
            (request.method, request.url.path, response.status_code, int(elapsed*1000), ip),
        )
        conn.commit()
    except Exception:
        pass

    return response
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
    s = _get_setup()
    if not s.get("done") and not s.get("skipped"):
        path = os.path.join(UI_DIR, "setup.html")
        with open(path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    path = os.path.join(UI_DIR, "index.html")
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/setup")
def setup_page():
    path = os.path.join(UI_DIR, "setup.html")
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

@app.post("/api/feedback")
async def submit_feedback(req: Request):
    body = await req.json()
    session_id = body.get("session_id", "default")
    user_message = body.get("user_message", "")
    assistant_reply = body.get("assistant_reply", "")
    rating = body.get("rating", 0)
    reason = body.get("reason", "")
    try:
        from core.observability import _get_conn
        conn = _get_conn()
        conn.execute(
            "INSERT INTO feedback (session_id, user_message, assistant_reply, rating, reason) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_message[:500], assistant_reply[:2000], rating, reason[:200]),
        )
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

SETUP_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "setup.json")

def _get_setup():
    if not os.path.exists(SETUP_FILE):
        return {"done": False, "skipped": False}
    try:
        with open(SETUP_FILE) as f:
            return json.load(f)
    except Exception:
        return {"done": False, "skipped": False}

def _save_setup(data):
    os.makedirs(os.path.dirname(SETUP_FILE), exist_ok=True)
    with open(SETUP_FILE, "w") as f:
        json.dump(data, f)

@app.get("/api/setup/status")
def setup_status():
    s = _get_setup()
    return {"needed": not s.get("done") and not s.get("skipped"), "name": s.get("name", "")}

@app.post("/api/setup/test-key")
async def test_key(req: Request):
    body = await req.json()
    key = body.get("key", "").strip()
    provider = body.get("provider", "groq")
    if not key:
        return {"ok": False, "error": "Key vacía"}
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return {"ok": False, "error": "Proveedor no encontrado"}
    try:
        from openai import OpenAI
        c = OpenAI(base_url=cfg["base_url"], api_key=key)
        r = c.chat.completions.create(
            model=cfg["models"]["extract"],
            messages=[{"role": "user", "content": "responde ok"}],
            max_tokens=5, temperature=0,
        )
        if r.choices:
            return {"ok": True}
        return {"ok": False, "error": "Respuesta inesperada"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

@app.post("/api/setup/complete")
async def setup_complete(req: Request):
    body = await req.json()
    name = body.get("name", "Usuario")
    groq_key = body.get("groq_key", "")
    telegram_token = body.get("telegram_token", "")
    default_provider = body.get("default_provider", "groq")
    _save_setup({"done": True, "skipped": False, "name": name, "default_provider": default_provider})
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if not line.startswith("GROQ_API_KEY=") and not line.startswith("TELEGRAM_BOT_TOKEN="):
                    lines.append(line.rstrip())
    if groq_key:
        lines.append(f"GROQ_API_KEY={groq_key}")
    if telegram_token:
        lines.append(f"TELEGRAM_BOT_TOKEN={telegram_token}")
    lines.append(f"DEFAULT_PROVIDER={default_provider}")
    with open(env_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return {"status": "ok"}

@app.post("/api/setup/skip")
def setup_skip():
    _save_setup({"done": False, "skipped": True})
    return {"status": "ok"}

@app.get("/api/plugins")
def list_plugins_api():
    from core.plugin import list_plugins
    return {"plugins": list_plugins()}

@app.post("/api/plugins/load")
def load_plugin_api(name: str):
    from core.plugin import discover, load_plugin
    for cls in discover():
        cls_name = cls.name or cls.__name__.lower()
        if cls_name == name.lower():
            return {"result": load_plugin(cls, engine)}
    return {"result": f"[Plugin '{name}' no encontrado]"}

@app.post("/api/plugins/unload")
def unload_plugin_api(name: str):
    from core.plugin import unload_plugin
    return {"result": unload_plugin(name, engine)}

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
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)

@app.websocket("/ws/stats")
async def stats_websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            stats = {
                "messages": MSG_COUNT,
                "memories": len(store.get_facts()),
                "uptime": int(time.time() - SERVER_START),
                "provider": engine.provider_name,
                "connections": ws_manager.count,
            }
            await ws.send_json(stats)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass

app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

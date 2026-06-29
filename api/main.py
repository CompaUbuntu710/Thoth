from fastapi import FastAPI
from core.engine import ThothEngine
from memory.store import MemoryStore
from pydantic import BaseModel

app = FastAPI()
store = MemoryStore()
engine = ThothEngine(store=store)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ForgetRequest(BaseModel):
    fact: str
    session_id: str = "default"

@app.get("/")
def root():
    return {"status": "awakening", "message": "Día 1: Thoth despierta"}

@app.post("/chat")
def chat(req: ChatRequest):
    return {"reply": engine.chat(req.message, req.session_id)}

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

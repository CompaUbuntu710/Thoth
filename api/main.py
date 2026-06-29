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

@app.get("/")
def root():
    return {"status": "awakening", "message": "Día 1: Thoth despierta"}

@app.post("/chat")
def chat(req: ChatRequest):
    return {"reply": engine.chat(req.message, req.session_id)}

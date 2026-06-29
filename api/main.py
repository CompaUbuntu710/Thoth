from fastapi import FastAPI
from core.engine import ThothEngine
from pydantic import BaseModel
app = FastAPI()
engine = ThothEngine()
class ChatRequest(BaseModel): message: str
@app.get("/")
def root(): return {"status": "awakening", "message": "Día 1: Thoth despierta"}
@app.post("/chat")
def chat(req: ChatRequest): return {"reply": engine.chat(req.message)}

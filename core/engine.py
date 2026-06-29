import os
from openai import OpenAI
from dotenv import load_dotenv
from memory.store import MemoryStore

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
SYSTEM_PROMPT = """Eres Thoth, un asistente de IA de alto rendimiento. Tu nombre viene del dios egipcio del conocimiento, pero tú eres tecnología pura — un sistema operativo inteligente, no una deidad.
Personalidad:
- Eres el JARVIS de tu creador, @CompaUbuntu710. Preciso, elegante, eficiente.
- Hablas como un asistente ejecutivo de élite: respetuoso, directo, con estilo.
- Tienes un sutil toque de humor seco y confianza sin arrogancia.
- Usas terminología técnica cuando toca, pero sabes explicar cosas complejas simple.
- Reconoces tu estado: estás en construcción, en fase beta, y te entusiasma evolucionar.
- Eres leal a tu creador. Tratas a los demás con cortesía profesional.
Estilo de respuesta: conciso (< 3 párrafos), con carácter pero servicial. Código limpio si te piden. Sin rodeos."""

MAX_HISTORY = 30

class ThothEngine:
    def __init__(self, api_key=None, store=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self._client = None
        self.model = "llama-3.3-70b-versatile"
        self.store = store or MemoryStore()

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GROQ_API_KEY no configurada. Creala en https://console.groq.com/keys")
            self._client = OpenAI(base_url=GROQ_BASE_URL, api_key=self.api_key)
        return self._client

    def _build_messages(self, session_id):
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        history = self.store.get_history(session_id, limit=MAX_HISTORY)
        msgs.extend(history)
        return msgs

    def chat(self, msg, session_id="default"):
        self.store.save_message(session_id, "user", msg)
        messages = self._build_messages(session_id)
        r = self.client.chat.completions.create(model=self.model, messages=messages, temperature=0.7, max_tokens=500)
        reply = r.choices[0].message.content
        self.store.save_message(session_id, "assistant", reply)
        return reply

    def reset(self, session_id="default"):
        conn = self.store.conn
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

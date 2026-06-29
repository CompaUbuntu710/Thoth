import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from memory.store import MemoryStore
from core.tools import TOOL_SCHEMAS, TOOL_HANDLERS

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
Estilo de respuesta: conciso (< 3 párrafos), con carácter pero servicial. Código limpio si te piden. Sin rodeos.

TIENES ACCESO A HERRAMIENTAS. Cuando el usuario pida algo que requiera una herramienta, úsala. No inventes respuestas que puedas verificar con una herramienta."""

EXTRACT_PROMPT = """De la conversación anterior, extrae datos personales, preferencias, gustos, proyectos o información importante sobre el usuario.
Devuelve SOLO un JSON array. Cada elemento: {"fact": "texto del hecho", "category": "preferencia|dato_personal|proyecto|gusto|tarea|otro"}
Ejemplo: [{"fact": "Al usuario le gusta el cafe negro", "category": "gusto"}]
Si no hay nada nuevo que recordar, devuelve [].
NO expliques. NO añadas texto. Solo JSON."""

MAX_HISTORY = 30

class ThothEngine:
    def __init__(self, api_key=None, store=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self._client = None
        self._extractor = None
        self.model = "llama-3.3-70b-versatile"
        self.extract_model = "llama-3.1-8b-instant"
        self.store = store or MemoryStore()
        self._msg_count = 0

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GROQ_API_KEY no configurada. Creala en https://console.groq.com/keys")
            self._client = OpenAI(base_url=GROQ_BASE_URL, api_key=self.api_key)
        return self._client

    @property
    def extractor(self):
        if self._extractor is None:
            self._extractor = OpenAI(base_url=GROQ_BASE_URL, api_key=self.api_key)
        return self._extractor

    def _build_messages(self, session_id):
        facts = self.store.get_facts()
        facts_text = ""
        if facts:
            lines = [f"- ({f['category']}) {f['fact']}" for f in facts]
            facts_text = "\nRecuerdos sobre el usuario:\n" + "\n".join(lines)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT + facts_text}]
        history = self.store.get_history(session_id, limit=MAX_HISTORY)
        msgs.extend(history)
        return msgs

    def _extract_facts(self, session_id):
        try:
            history = self.store.get_history(session_id, limit=6)
            if len(history) < 2:
                return
            extract_msgs = [{"role": "system", "content": EXTRACT_PROMPT}]
            extract_msgs.extend(history[-4:])
            r = self.extractor.chat.completions.create(
                model=self.extract_model, messages=extract_msgs,
                temperature=0.1, max_tokens=300,
            )
            raw = r.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            facts = json.loads(raw)
            if isinstance(facts, list):
                for f in facts:
                    self.store.save_fact(f["fact"], f.get("category", "general"), session_id)
        except Exception:
            pass

    def _run_tools(self, response_message):
        msgs = [response_message]
        for tc in response_message.tool_calls:
            fn = tc.function
            handler = TOOL_HANDLERS.get(fn.name)
            if handler:
                args = json.loads(fn.arguments)
                result = handler(**args)
            else:
                result = f"[Herramienta '{fn.name}' no encontrada]"
            msgs.append({
                "tool_call_id": tc.id,
                "role": "tool",
                "name": fn.name,
                "content": result,
            })
        return msgs

    def chat(self, msg, session_id="default"):
        self.store.save_message(session_id, "user", msg)
        messages = self._build_messages(session_id)
        r = self.client.chat.completions.create(
            model=self.model, messages=messages,
            tools=TOOL_SCHEMAS, temperature=0.7, max_tokens=500,
        )
        reply_msg = r.choices[0].message
        if reply_msg.tool_calls:
            messages.append(reply_msg)
            tool_results = self._run_tools(reply_msg)
            messages.extend(tool_results)
            r2 = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=500,
            )
            reply = r2.choices[0].message.content
        else:
            reply = reply_msg.content
        self.store.save_message(session_id, "assistant", reply)
        self._msg_count += 1
        if self._msg_count % 2 == 0:
            self._extract_facts(session_id)
        return reply

    def remember(self, fact, category="general"):
        self.store.save_fact(fact, category)

    def forget(self, fact):
        self.store.delete_fact(fact)

    def recall(self):
        return self.store.get_facts()

    def reset(self, session_id="default"):
        conn = self.store.conn
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

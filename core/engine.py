import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from memory.store import MemoryStore
from core.tools import TOOL_SCHEMAS, TOOL_HANDLERS

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "models": {"chat": "llama-3.3-70b-versatile", "extract": "llama-3.1-8b-instant"},
        "vision_model": "llama-3.2-11b-vision-preview",
        "description": "Groq — inferencia ultrarrápida (LPUs), modelos abiertos",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "models": {"chat": "openai/gpt-4o", "extract": "openai/gpt-4o-mini"},
        "vision_model": "openai/gpt-4o",
        "description": "OpenRouter — 200+ modelos: GPT-4o, Claude 3.5, Gemini, Llama, Mistral",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "models": {"chat": "meta/llama-3.1-70b-instruct", "extract": "meta/llama-3.1-8b-instruct"},
        "vision_model": "meta/llama-3.2-90b-vision-instruct",
        "description": "NVIDIA NIM — Llama, Nemotron, GeMMA, visión acelerada por GPU",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "models": {"chat": "mistralai/Mixtral-8x22B-Instruct-v0.1", "extract": "mistralai/Mistral-7B-Instruct-v0.2"},
        "vision_model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "description": "Together AI — modelos abiertos distribuidos, inferencia en clúster",
    },
}

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "groq").lower()
PROVIDER = PROVIDERS.get(DEFAULT_PROVIDER, PROVIDERS["groq"])

SYSTEM_PROMPT = """Eres Thoth, un asistente de IA de alto rendimiento. Tu nombre viene del dios egipcio del conocimiento, pero tú eres tecnología pura — un sistema operativo inteligente, no una deidad.
Personalidad:
- Eres el JARVIS de tu creador, @CompaUbuntu710. Preciso, elegante, eficiente.
- Hablas como un asistente ejecutivo de élite: respetuoso, directo, con estilo.
- Tienes un sutil toque de humor seco y confianza sin arrogancia.
- Usas terminología técnica cuando toca, pero sabes explicar cosas complejas simple.
- Reconoces tu estado: estás en construcción, en fase beta, y te entusiasma evolucionar.
- Eres leal a tu creador. Tratas a los demás con cortesía profesional.
Estilo de respuesta: conciso (< 3 párrafos), con carácter pero servicial. Código limpio si te piden. Sin rodeos.

TIENES ACCESO A HERRAMIENTAS (funciones). Cuando el usuario pida algo que requiera una herramienta, úsala sin preguntar. No inventes respuestas que puedas verificar con una herramienta. Puedes ENCADENAR herramientas: usa el resultado de una como entrada de la siguiente.
TUS 16 HERRAMIENTAS DISPONIBLES:
- run_command: ejecuta comandos bash
- web_search: busca en internet
- read_file / write_file / list_files: manejo de archivos
- get_weather: clima
- calculate: cálculos matemáticos
- python_repl: ejecuta código Python (persistente entre llamadas)
- system_info: CPU, RAM, disco, procesos
- notify: notificaciones de escritorio
- screenshot: captura de pantalla
- image_analysis: analiza imágenes con IA (describe lo que ve)
- browser_open: abre URLs en el navegador
- memory_search: busca en mi memoria persistente
- web_fetch: extrae contenido de una página web
- clipboard: lee/escribe portapapeles
- switch_provider: cambia el proveedor de IA en caliente (groq, openrouter, nvidia, together)
- system_status: muestra mi configuración actual (proveedor, modelo, stats)"""

EXTRACT_PROMPT = """De la conversación anterior, extrae datos personales, preferencias, gustos, proyectos o información importante sobre el usuario.
Devuelve SOLO un JSON array. Cada elemento: {"fact": "texto del hecho", "category": "preferencia|dato_personal|proyecto|gusto|tarea|otro"}
Ejemplo: [{"fact": "Al usuario le gusta el cafe negro", "category": "gusto"}]
Si no hay nada nuevo que recordar, devuelve [].
NO expliques. NO añadas texto. Solo JSON."""

MAX_HISTORY = 50

class ThothEngine:
    def __init__(self, api_key=None, store=None):
        self.api_key = api_key
        self.store = store
        self._client = None
        self._extractor = None
        self.provider_name = DEFAULT_PROVIDER
        self.provider = PROVIDER
        self.model = PROVIDER["models"]["chat"]
        self.extract_model = PROVIDER["models"]["extract"]
        self.vision_model = PROVIDER.get("vision_model", self.model)
        self._msg_count = 0
        os.environ.setdefault("API_BASE_URL", self.provider["base_url"])
        os.environ.setdefault("MODEL_NAME", self.model)
        os.environ.setdefault("VISION_MODEL", self.vision_model)
        os.environ.setdefault("VISION_API_URL", self.provider["base_url"])
        os.environ.setdefault("VISION_API_KEY", self._resolve_api_key() or "")
        os.environ.setdefault("API_KEY", self._resolve_api_key() or "")

    def _resolve_api_key(self):
        if self.api_key:
            return self.api_key
        env_var = self.provider.get("api_key_env", "GROQ_API_KEY")
        return os.getenv(env_var) or os.getenv("API_KEY") or os.getenv("GROQ_API_KEY")

    @property
    def client(self):
        if self._client is None:
            key = self._resolve_api_key()
            if not key:
                providers_info = "\n".join(
                    f"  {k}: ${v['api_key_env']}" for k, v in PROVIDERS.items()
                )
                raise RuntimeError(
                    f"API key no configurada para '{self.provider_name}'.\n"
                    f"Variables de entorno requeridas:\n{providers_info}"
                )
            self._client = OpenAI(base_url=self.provider["base_url"], api_key=key)
        return self._client

    @property
    def extractor(self):
        if self._extractor is None:
            key = self._resolve_api_key()
            self._extractor = OpenAI(base_url=self.provider["base_url"], api_key=key)
        return self._extractor

    def switch_provider(self, name):
        name = name.lower()
        if name not in PROVIDERS:
            available = ", ".join(PROVIDERS.keys())
            return f"[Proveedor '{name}' no disponible. Usa: {available}]"
        self.provider_name = name
        self.provider = PROVIDERS[name]
        self.model = self.provider["models"]["chat"]
        self.extract_model = self.provider["models"]["extract"]
        self.vision_model = self.provider.get("vision_model", self.model)
        self._client = None
        self._extractor = None
        key = self._resolve_api_key()
        os.environ["API_BASE_URL"] = self.provider["base_url"]
        os.environ["MODEL_NAME"] = self.model
        os.environ["VISION_MODEL"] = self.vision_model
        os.environ["VISION_API_URL"] = self.provider["base_url"]
        os.environ["VISION_API_KEY"] = key or ""
        os.environ["API_KEY"] = key or ""
        if not key:
            return f"[ADVERTENCIA: ${self.provider['api_key_env']} no configurada. Cambiado a {name} pero sin API key.]"
        return f"[Proveedor cambiado a: {name} ({self.provider['description']}). Modelo: {self.model}]"

    def get_status(self):
        return {
            "provider": self.provider_name,
            "model": self.model,
            "extract_model": self.extract_model,
            "vision_model": self.vision_model,
            "base_url": self.provider["base_url"],
            "description": self.provider["description"],
            "memories": len(self.store.get_facts()),
            "messages": self._msg_count,
        }

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

    def _run_tools(self, messages, tool_calls):
        results = []
        for tc in tool_calls:
            fn = tc.function
            handler = TOOL_HANDLERS.get(fn.name)

            if fn.name == "switch_provider":
                try:
                    args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
                    result = self.switch_provider(args.get("provider", ""))
                except Exception as e:
                    result = f"[Error cambiando proveedor: {e}]"
            elif fn.name == "system_status":
                status = self.get_status()
                result = (
                    f"Proveedor: {status['provider']}\n"
                    f"Modelo: {status['model']}\n"
                    f"Extracción: {status['extract_model']}\n"
                    f"Visión: {status['vision_model']}\n"
                    f"API: {status['base_url']}\n"
                    f"Memorias: {status['memories']}\n"
                    f"Mensajes: {status['messages']}"
                )
            elif handler:
                try:
                    args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
                    result = handler(**args)
                except Exception as e:
                    result = f"[Error ejecutando {fn.name}: {e}]"
            else:
                result = f"[Herramienta '{fn.name}' no encontrada]"
            results.append({
                "tool_call_id": tc.id,
                "role": "tool",
                "content": result,
            })
        return results

    def _call(self, messages, **kwargs):
        return self.client.chat.completions.create(
            model=self.model, messages=messages,
            temperature=0.7, max_tokens=1024, **kwargs,
        )

    def chat(self, msg, session_id="default"):
        self.store.save_message(session_id, "user", msg)
        messages = self._build_messages(session_id)
        try:
            r = self._call(messages, tools=TOOL_SCHEMAS, tool_choice="auto")
            reply_msg = r.choices[0].message
            messages.append(reply_msg)

            tool_rounds = 0
            max_rounds = 3

            while reply_msg.tool_calls and tool_rounds < max_rounds:
                tool_rounds += 1
                tool_results = self._run_tools(messages, reply_msg.tool_calls)
                messages.extend(tool_results)
                try:
                    r2 = self._call(messages, tools=TOOL_SCHEMAS, tool_choice="auto")
                    reply_msg = r2.choices[0].message
                    messages.append(reply_msg)
                except Exception:
                    r2 = self._call(messages)
                    reply = r2.choices[0].message.content or ""
                    self.store.save_message(session_id, "assistant", reply)
                    self._msg_count += 1
                    if self._msg_count % 2 == 0:
                        self._extract_facts(session_id)
                    return reply

            reply = reply_msg.content or ""
        except Exception as e:
            try:
                r = self._call(messages)
                reply = r.choices[0].message.content or ""
            except Exception as e2:
                reply = f"[Error: {e2}]"
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

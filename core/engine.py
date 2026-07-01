import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from memory.store import MemoryStore
from core.tools import TOOL_SCHEMAS, TOOL_HANDLERS
from memory.vector_store import VectorStore, HAS_CHROMA
from core.agent import Agent, AGENT_DEFS

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
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "OLLAMA_API_KEY",
        "models": {"chat": "llama3.2", "extract": "llama3.2:1b"},
        "vision_model": "llava",
        "description": "Ollama — inferencia local con Llama 3, Mistral, Qwen, etc.",
    },
}

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "groq").lower()
PROVIDER = PROVIDERS.get(DEFAULT_PROVIDER, PROVIDERS["groq"])

# Start reminder checker
from tools.calendar_tool import start_reminder_checker
start_reminder_checker()

EXTRACT_PROMPT = """De la conversación anterior, extrae datos personales, preferencias, gustos, proyectos o información importante sobre el usuario.
Devuelve SOLO un JSON array. Cada elemento: {"fact": "texto del hecho", "category": "preferencia|dato_personal|proyecto|gusto|tarea|otro"}
Ejemplo: [{"fact": "Al usuario le gusta el cafe negro", "category": "gusto"}]
Si no hay nada nuevo que recordar, devuelve [].
NO expliques. NO añadas texto. Solo JSON."""

ROUTING_PROMPT = """Classify the user message into one category:
- code: programming, commands, terminal, file editing, scripts
- web: internet search, URLs, online research, browsing
- memory: storing, retrieving, or asking about personal information, remembering facts
- system: system status, provider switch, configuration, technical info
- general: casual chat, questions, opinions, anything else

Respond with ONLY the category name."""

SUMMARIZE_PROMPT = """Resume la siguiente conversación en 2-3 oraciones, capturando los temas principales, información importante, y tareas pendientes. Solo el resumen, sin introducción."""

CRITIC_PROMPT = """Revisa la siguiente respuesta del asistente Thoth. SOLO intervén si hay:
1. Errores factuales graves
2. Respuestas inseguras o dañinas
3. Formato completamente roto

Si la respuesta está bien (incluso si es simple o corta), responde SOLO: OK
Si hay errores graves, responde con la versión corregida.
No añadas explicaciones. No alargues respuestas cortas. No critiques el uso de herramientas."""

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
        self._agents = {}
        self.vector_store = VectorStore() if HAS_CHROMA else None
        self._plugin_tools = []
        self._plugin_schemas = []
        self._plugin_handlers = {}
        self._critic_enabled = True
        self._failover_log = []
        try:
            from core.plugin import load_all
            load_all(self)
        except Exception:
            pass
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

    def _get_failover_chain(self):
        """Returns providers ordered: current first, then others with keys configured."""
        chain = [self.provider_name]
        for name, cfg in PROVIDERS.items():
            if name != self.provider_name and os.getenv(cfg["api_key_env"]):
                chain.append(name)
        return chain

    def _failover(self, error_msg=""):
        """Switch to next available provider. Returns True if switched."""
        chain = self._get_failover_chain()
        if len(chain) < 2:
            return False
        next_provider = chain[1] if chain[0] == self.provider_name else chain[0]
        if next_provider == self.provider_name:
            return False
        result = self.switch_provider(next_provider)
        self._failover_log.append({
            "from": self.provider_name,
            "to": next_provider,
            "reason": error_msg[:100],
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        print(f"[Failover] {result}")
        return True

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
            self._client = OpenAI(base_url=self.provider["base_url"], api_key=key, timeout=60.0)
        return self._client

    @property
    def extractor(self):
        if self._extractor is None:
            key = self._resolve_api_key()
            self._extractor = OpenAI(base_url=self.provider["base_url"], api_key=key, timeout=30.0)
        return self._extractor

    def _get_agent(self, name):
        """Crea o recupera un agente por nombre."""
        if name not in self._agents:
            if name not in AGENT_DEFS:
                name = "thoth"
            defn = AGENT_DEFS[name]
            self._agents[name] = Agent(
                name=name,
                role=defn["role"],
                system_prompt=defn["system_prompt"],
                tool_names=defn["tool_names"],
                model=self.model,
                client=self.client,
                extra_schemas=self._plugin_schemas,
                extra_handlers=self._plugin_handlers,
            )
        return self._agents[name]

    def _route(self, msg):
        """Clasifica el mensaje en una categoría de agente usando el modelo de extracción."""
        try:
            r = self.extractor.chat.completions.create(
                model=self.extract_model,
                messages=[
                    {"role": "system", "content": ROUTING_PROMPT},
                    {"role": "user", "content": msg},
                ],
                temperature=0.1, max_tokens=10,
            )
            category = r.choices[0].message.content.strip().lower()
            if hasattr(r, "usage") and r.usage:
                try:
                    from core.observability import log_usage
                    log_usage(self.provider_name, self.extract_model, "router",
                              r.usage.prompt_tokens or 0, r.usage.completion_tokens or 0)
                except Exception:
                    pass
            if category in ("code", "web", "memory", "system"):
                return category
        except Exception as e:
            try:
                from core.observability import log_error
                log_error("router", str(e))
            except Exception:
                pass
        return "thoth"

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
        self._agents = {}
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
            "agents": list(AGENT_DEFS.keys()),
            "active_agent": getattr(self, "_last_agent", "thoth"),
            "failover_chain": self._get_failover_chain(),
            "failover_count": len(self._failover_log),
        }

    def _handle_plugin(self, action, name=None):
        from core.plugin import list_plugins, load_plugin, unload_plugin, discover
        if action == "list":
            plugins = list_plugins()
            if not plugins:
                return "[No hay plugins cargados]"
            return "Plugins:\n" + "\n".join(
                f"  {p['name']} v{p['version']} — {p['description']}" for p in plugins
            )
        elif action == "load":
            if not name:
                return "[Error: nombre requerido]"
            for cls in discover():
                cls_name = cls.name or cls.__name__.lower()
                if cls_name == name.lower():
                    return load_plugin(cls, self)
            return f"[Plugin '{name}' no encontrado en plugins/]"
        elif action == "unload":
            if not name:
                return "[Error: nombre requerido]"
            return unload_plugin(name, self)
        return "[Error: acción inválida. Usa: list, load, unload]"

    def _build_messages(self, session_id, agent):
        facts = self.store.get_facts()
        facts_text = ""
        if facts:
            lines = [f"- ({f['category']}) {f['fact']}" for f in facts]
            facts_text = "\nRecuerdos sobre el usuario:\n" + "\n".join(lines)

        summaries = ""
        if self.vector_store and HAS_CHROMA:
            try:
                recent = self.vector_store.search(
                    "conversación resumen", n_results=3, category="resumen"
                )
                if recent:
                    summary_lines = [f"- {r['fact']}" for r in recent]
                    summaries = "\nResúmenes de conversaciones anteriores:\n" + "\n".join(summary_lines)
            except Exception:
                pass

        msgs = [{"role": "system", "content": agent.system_prompt + facts_text + summaries}]
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
                    fact_id = self.store.save_fact(f["fact"], f.get("category", "general"), session_id)
                    if self.vector_store and fact_id:
                        self.vector_store.add_fact(fact_id, f["fact"], f.get("category", "general"), session_id)
        except Exception:
            pass

    def _summarize_if_needed(self, session_id):
        """Resume la conversación cuando se acerca al límite de MAX_HISTORY."""
        try:
            history = self.store.get_history(session_id, limit=MAX_HISTORY)
            if len(history) < MAX_HISTORY - 5:
                return
            text_to_summarize = "\n".join(
                f"{m['role']}: {m['content'][:200]}" for m in history[:20]
            )
            r = self.extractor.chat.completions.create(
                model=self.extract_model,
                messages=[
                    {"role": "system", "content": SUMMARIZE_PROMPT},
                    {"role": "user", "content": text_to_summarize},
                ],
                temperature=0.3, max_tokens=200,
            )
            summary = r.choices[0].message.content.strip()
            if summary and self.vector_store:
                from datetime import datetime, timezone
                import hashlib
                sid = hashlib.md5(summary.encode()).hexdigest()[:12]
                self.vector_store.add_fact(sid, summary, "resumen", session_id)
        except Exception:
            pass

    def _critique(self, msg, reply):
        """Revisa la respuesta del agente y la mejora si es necesario."""
        if not self._critic_enabled:
            return reply
        try:
            r = self.extractor.chat.completions.create(
                model=self.extract_model,
                messages=[
                    {"role": "system", "content": CRITIC_PROMPT},
                    {"role": "user", "content": f"Usuario: {msg[:500]}\n\nAsistente: {reply[:1000]}"},
                ],
                temperature=0.2, max_tokens=512, timeout=15,
            )
            critique = r.choices[0].message.content.strip()
            if critique and critique != "OK" and len(critique) > 10:
                return critique
        except Exception as e:
            try:
                from core.observability import log_error
                log_error("critic", str(e)[:100])
            except Exception:
                pass
        return reply

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
                    f"Mensajes: {status['messages']}\n"
                    f"Agentes: {', '.join(status['agents'])}"
                )
            elif fn.name in self._plugin_handlers:
                try:
                    args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
                    result = self._plugin_handlers[fn.name](**args)
                except Exception as e:
                    result = f"[Error ejecutando plugin {fn.name}: {e}]"
            elif fn.name == "plugin":
                try:
                    args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
                    result = self._handle_plugin(**args)
                except Exception as e:
                    result = f"[Error en plugin: {e}]"
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
        try:
            return self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=1024, **kwargs,
            )
        except Exception as e:
            estr = str(e)
            if "429" in estr or "rate_limit" in estr.lower():
                if self._failover(estr):
                    return self._call(messages, **kwargs)
            raise

    def _call_with_log(self, messages, agent_name="thoth", session_id="", **kwargs):
        """Like _call but logs usage to observability."""
        try:
            r = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=1024, **kwargs,
            )
            if hasattr(r, "usage") and r.usage:
                try:
                    from core.observability import log_usage
                    log_usage(
                        provider=self.provider_name,
                        model=self.model,
                        agent=agent_name,
                        prompt_tokens=r.usage.prompt_tokens or 0,
                        completion_tokens=r.usage.completion_tokens or 0,
                        session_id=session_id,
                    )
                except Exception:
                    pass
            return r
        except Exception as e:
            try:
                from core.observability import log_usage, log_error
                log_usage(
                    provider=self.provider_name,
                    model=self.model, agent=agent_name,
                    prompt_tokens=0, completion_tokens=0,
                    error=str(e), session_id=session_id,
                )
                log_error("engine._call_with_log", str(e))
            except Exception:
                pass
            raise

    def chat(self, msg, session_id="default"):
        self.store.save_message(session_id, "user", msg)

        agent_name = self._route(msg)
        self._last_agent = agent_name
        agent = self._get_agent(agent_name)
        messages = self._build_messages(session_id, agent)

        reply, updated_messages = agent.run(messages)

        reply = self._critique(msg, reply)

        self.store.save_message(session_id, "assistant", reply)
        self._msg_count += 1
        if self._msg_count % 2 == 0:
            self._extract_facts(session_id)
        if self._msg_count % 10 == 0:
            self._summarize_if_needed(session_id)
        return reply

    def chat_stream(self, msg, session_id="default"):
        self.store.save_message(session_id, "user", msg)

        agent_name = self._route(msg)
        self._last_agent = agent_name
        agent = self._get_agent(agent_name)
        messages = self._build_messages(session_id, agent)

        try:
            kwargs = {}
            if agent.tool_schemas:
                kwargs["tools"] = agent.tool_schemas
                kwargs["tool_choice"] = "auto"

            stream = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=1024,
                stream=True, **kwargs,
            )

            collected = {"content": "", "tool_calls": {}}

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    collected["content"] += delta.content
                    yield ("token", delta.content)

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in collected["tool_calls"]:
                            collected["tool_calls"][idx] = {
                                "id": tc.id or "",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            collected["tool_calls"][idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                collected["tool_calls"][idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                collected["tool_calls"][idx]["function"]["arguments"] += tc.function.arguments

            if collected["tool_calls"]:
                yield ("tool_calls_start", collected["content"])

                tc_list = []
                for idx in sorted(collected["tool_calls"].keys()):
                    tc_data = collected["tool_calls"][idx]
                    tc_list.append({
                        "id": tc_data["id"],
                        "type": "function",
                        "function": {
                            "name": tc_data["function"]["name"],
                            "arguments": tc_data["function"]["arguments"],
                        }
                    })

                from collections import namedtuple
                ToolCall = namedtuple("ToolCall", ["id", "function"])
                Function = namedtuple("Function", ["name", "arguments"])
                tool_calls = []
                for tc in tc_list:
                    tool_calls.append(ToolCall(
                        id=tc["id"],
                        function=Function(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"],
                        )
                    ))

                tool_results = self._run_tools(messages, tool_calls)
                messages.append({
                    "role": "assistant",
                    "content": collected["content"],
                    "tool_calls": tc_list,
                })
                messages.extend(tool_results)

                tool_rounds = 1
                max_rounds = 3

                while tool_rounds < max_rounds:
                    tool_rounds += 1
                    try:
                        r2 = self._call(messages, tools=agent.tool_schemas, tool_choice="auto")
                        reply_msg = r2.choices[0].message
                        messages.append(reply_msg)

                        if not reply_msg.tool_calls:
                            reply = reply_msg.content or ""
                            reply = self._critique(msg, reply)
                            yield ("token", reply)
                            self.store.save_message(session_id, "assistant", reply)
                            self._msg_count += 1
                            if self._msg_count % 2 == 0:
                                self._extract_facts(session_id)
                            yield ("done", reply)
                            return

                        tool_results = self._run_tools(messages, reply_msg.tool_calls)
                        messages.extend(tool_results)
                    except Exception:
                        r2 = self._call(messages)
                        reply = r2.choices[0].message.content or ""
                        reply = self._critique(msg, reply)
                        self.store.save_message(session_id, "assistant", reply)
                        self._msg_count += 1
                        if self._msg_count % 2 == 0:
                            self._extract_facts(session_id)
                        yield ("done", reply)
                        return

                reply = "[Límite de rondas de herramientas alcanzado]"
                self.store.save_message(session_id, "assistant", reply)
                self._msg_count += 1
                yield ("done", reply)
            else:
                reply = collected["content"]
                reply = self._critique(msg, reply)
                self.store.save_message(session_id, "assistant", reply)
                self._msg_count += 1
                if self._msg_count % 2 == 0:
                    self._extract_facts(session_id)
                yield ("done", reply)

        except Exception as e:
            yield ("error", str(e))

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

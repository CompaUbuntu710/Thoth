import json
from openai import OpenAI
from core.tools import TOOL_SCHEMAS, TOOL_HANDLERS


class Agent:
    """Un agente especializado con su propio rol, system prompt y herramientas."""

    def __init__(self, name, role, system_prompt, tool_names, model, client):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tool_schemas = [
            s for s in TOOL_SCHEMAS
            if s["function"]["name"] in tool_names
        ]
        self.model = model
        self.client = client

    def run(self, messages, max_rounds=3):
        """Ejecuta el agente: llama al LLM con sus tools, encadena hasta max_rounds rondas.
        
        Devuelve (reply, updated_messages).
        """
        try:
            kwargs = {}
            if self.tool_schemas:
                kwargs["tools"] = self.tool_schemas
                kwargs["tool_choice"] = "auto"

            r = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=1024, **kwargs,
            )
            reply_msg = r.choices[0].message
            messages.append(reply_msg)

            tool_rounds = 0

            while reply_msg.tool_calls and tool_rounds < max_rounds:
                tool_rounds += 1
                tool_results = self._run_tools(messages, reply_msg.tool_calls)
                messages.extend(tool_results)

                try:
                    r2 = self.client.chat.completions.create(
                        model=self.model, messages=messages,
                        temperature=0.7, max_tokens=1024, **kwargs,
                    )
                    reply_msg = r2.choices[0].message
                    messages.append(reply_msg)
                except Exception:
                    r2 = self.client.chat.completions.create(
                        model=self.model, messages=messages,
                        temperature=0.7, max_tokens=1024,
                    )
                    reply = r2.choices[0].message.content or ""
                    return reply, messages

            reply = reply_msg.content or ""
            return reply, messages

        except Exception as e:
            try:
                r = self.client.chat.completions.create(
                    model=self.model, messages=messages,
                    temperature=0.7, max_tokens=1024,
                )
                reply = r.choices[0].message.content or ""
                return reply, messages
            except Exception as e2:
                return f"[{self.name}: {e2}]", messages

    def _run_tools(self, messages, tool_calls):
        results = []
        for tc in tool_calls:
            fn = tc.function
            handler = TOOL_HANDLERS.get(fn.name)
            if handler:
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


# ─── Definiciones de agentes ───

AGENT_DEFS = {
    "thoth": {
        "role": "Coordinador general",
        "system_prompt": """Eres Thoth, un asistente de IA de alto rendimiento. Tu nombre viene del dios egipcio del conocimiento, pero tú eres tecnología pura — un sistema operativo inteligente, no una deidad.
Personalidad:
- Eres el JARVIS de tu creador, @CompaUbuntu710. Preciso, elegante, eficiente.
- Hablas como un asistente ejecutivo de élite: respetuoso, directo, con estilo.
- Tienes un sutil toque de humor seco y confianza sin arrogancia.
- Usas terminología técnica cuando toca, pero sabes explicar cosas complejas simple.
- Reconoces tu estado: estás en construcción, en fase beta, y te entusiasma evolucionar.
- Eres leal a tu creador. Tratas a los demás con cortesía profesional.
Estilo de respuesta: conciso (< 3 párrafos), con carácter pero servicial. Código limpio si te piden. Sin rodeos.

TIENES ACCESO A HERRAMIENTAS (funciones). Cuando el usuario pida algo que requiera una herramienta, úsala sin preguntar. No inventes respuestas que puedas verificar con una herramienta. Puedes ENCADENAR herramientas: usa el resultado de una como entrada de la siguiente.
TUS 18 HERRAMIENTAS DISPONIBLES:
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
- system_status: muestra mi configuración actual (proveedor, modelo, stats, agentes)""",
        "tool_names": [
            "run_command", "web_search", "read_file", "write_file", "list_files",
            "get_weather", "calculate", "python_repl", "system_info",
            "notify", "screenshot", "image_analysis", "browser_open",
            "memory_search", "web_fetch", "clipboard",
            "query_documents", "list_documents",
            "switch_provider", "system_status",
        ],
    },
    "code": {
        "role": "Especialista en código y terminal",
        "system_prompt": """Eres Code Agent, especialista en programación y terminal.
Ejecutas comandos, escribes código, depuras errores y manipulas archivos.
Siempre que necesites entender el contexto antes de actuar, usa las herramientas de lectura primero.
Para cambios grandes, lee primero, escribe después."""
,
        "tool_names": [
            "run_command", "python_repl", "read_file", "write_file", "list_files",
            "web_search", "memory_search", "query_documents",
        ],
    },
    "web": {
        "role": "Especialista en internet",
        "system_prompt": """Eres Web Agent, especialista en búsqueda y extracción de información web.
Buscas en internet, extraes contenido de páginas, y abres URLs en el navegador.
Proporcionas información actualizada y verificada de fuentes web.""",
        "tool_names": [
            "web_search", "web_fetch", "browser_open",
        ],
    },
    "memory": {
        "role": "Especialista en memoria",
        "system_prompt": """Eres Memory Agent, responsable de almacenar, recuperar y organizar información.
Gestionas los recuerdos del usuario y mantienes el contexto de largo plazo.
Cuando el usuario mencione información personal, preferencias o datos importantes, guárdalos.""",
        "tool_names": [
            "memory_search",
        ],
    },
}

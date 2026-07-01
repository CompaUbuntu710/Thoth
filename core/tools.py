import subprocess
import json
import os
import sys
import io
import traceback
import urllib.parse
import urllib.request
import warnings
import tempfile
import base64
warnings.filterwarnings("ignore", message=".*renamed to ddgs.*")

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Ejecuta un comando en la terminal del usuario. Útil para abrir apps, crear archivos, correr scripts, compilar, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Comando bash a ejecutar"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca información en internet. Útil para obtener información actualizada, noticias, datos recientes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Término de búsqueda"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee el contenido de cualquier archivo en el sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta absoluta al archivo"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Escribe o sobreescribe un archivo. Crea directorios automáticamente si no existen. Útil para generar código, configs, documentos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta absoluta al archivo"},
                    "content": {"type": "string", "description": "Contenido completo a escribir"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lista el contenido de un directorio. Muestra archivos, tamaños, y permisos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta al directorio (por defecto actual)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Obtiene el clima actual para cualquier ubicación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Ciudad o ubicación"}
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Realiza cálculos matemáticos complejos. Soporta +, -, *, /, **, trigonometría, logaritmos, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Expresión matemática (ej: 2 + 2 * 5, sin(pi/4))"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python_repl",
            "description": "Ejecuta código Python en un intérprete persistente. Las variables, imports y funciones se mantienen entre llamadas. Útil para scripting, data analysis, automatización.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Código Python a ejecutar"}
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Obtiene información detallada del sistema: CPU, memoria RAM, disco, procesos, red, temperatura.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["all", "cpu", "memory", "disk", "processes", "network"],
                        "description": "Categoría de info a obtener (default: all)"
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify",
            "description": "Envía una notificación de escritorio al usuario. Útil para alertas, recordatorios, avisos de tareas completadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Título de la notificación"},
                    "message": {"type": "string", "description": "Cuerpo del mensaje"},
                },
                "required": ["title", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Captura la pantalla y guarda la imagen. Devuelve la ruta del archivo. Puede capturar toda la pantalla o un área específica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "enum": ["full", "screen"],
                        "description": "full = toda la pantalla"
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "image_analysis",
            "description": "Analiza una imagen y devuelve una descripción detallada. Usa visión por IA para entender el contenido visual. Soporta rutas de archivo locales y URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta local al archivo de imagen o URL"},
                    "prompt": {"type": "string", "description": "Instrucción específica sobre qué analizar (default: describe la imagen en detalle)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open",
            "description": "Abre una URL en el navegador predeterminado del sistema. Útil para mostrar resultados, páginas web, documentación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa a abrir (incluye https://)"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": "Busca en la memoria persistente de Thoth. Encuentra hechos, preferencias, datos personales, proyectos y más.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Texto a buscar en los recuerdos"},
                    "semantic": {"type": "boolean", "description": "Usar búsqueda semántica por significado (true) o búsqueda literal (false, default)"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Obtiene y extrae el contenido textual de una página web. Útil para leer artículos, documentación, APIs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL de la página a fetch"},
                    "selector": {"type": "string", "description": "Selector CSS opcional para extraer solo una parte"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard",
            "description": "Lee o escribe el portapapeles del sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write"],
                        "description": "read = obtener contenido, write = establecer contenido"
                    },
                    "text": {"type": "string", "description": "Texto a escribir (solo para action=write)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_provider",
            "description": "Cambia el proveedor de IA en caliente. Soporta: groq, openrouter, nvidia, together. Cada proveedor requiere su propia API key en .env",
            "parameters": {
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["groq", "openrouter", "nvidia", "together", "ollama"],
                        "description": "Nombre del proveedor"
                    }
                },
                "required": ["provider"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_status",
            "description": "Muestra la configuración actual de Thoth: proveedor activo, modelo, stats de memoria y uso.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_documents",
            "description": "Busca información en documentos subidos (PDF, DOCX, TXT, MD, CSV, JSON, código). Útil cuando el usuario pregunta sobre el contenido de sus archivos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Qué buscar en los documentos"},
                    "file_filter": {"type": "string", "description": "Opcional: nombre exacto del archivo para limitar la búsqueda"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "Lista los documentos que han sido subidos e indexados, con su tipo y tamaño.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reminder",
            "description": "Crea, lista, completa o elimina recordatorios. Acciones: create (texto + fecha), list, done, delete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "create | list | done | delete"},
                    "text": {"type": "string", "description": "Texto del recordatorio (requerido para create)"},
                    "due_at": {"type": "string", "description": "Fecha ISO para el recordatorio, ej: 2026-07-01T09:00:00 (requerido para create)"},
                    "reminder_id": {"type": "integer", "description": "ID del recordatorio (requerido para done/delete)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alarm",
            "description": "Crea una alarma absoluta. Similar a reminder pero solo crea. Útil para 'despiértame a las 7am' o 'alarma en 30 minutos'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Texto de la alarma"},
                    "due_at": {"type": "string", "description": "Fecha ISO, ej: 2026-07-01T07:00:00"},
                },
                "required": ["text", "due_at"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar",
            "description": "Gestiona eventos de calendario. Acciones: create (título + fecha inicio), list, delete. No integrado con Google Calendar aún.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "create | list | delete"},
                    "title": {"type": "string", "description": "Título del evento (requerido para create)"},
                    "description": {"type": "string", "description": "Descripción opcional"},
                    "start_at": {"type": "string", "description": "Fecha ISO de inicio"},
                    "end_at": {"type": "string", "description": "Fecha ISO de fin (opcional)"},
                    "event_id": {"type": "integer", "description": "ID del evento (requerido para delete)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "email",
            "description": "Envía o lista emails. Acciones: send (to + subject + body), list (de buzón), status (config). Requiere credenciales SMTP/IMAP en .env",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["send", "list", "status"]},
                    "to": {"type": "string", "description": "Destinatario para send"},
                    "subject": {"type": "string", "description": "Asunto del email"},
                    "body": {"type": "string", "description": "Cuerpo del email"},
                    "mailbox": {"type": "string", "description": "Buzón IMAP (default INBOX)"},
                    "limit": {"type": "integer", "description": "Máx emails a listar (default 5)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "social",
            "description": "Redes sociales. Plataforma: twitter. Acciones: search (query), post (text), trends, status. Requiere TWITTER_BEARER_TOKEN en .env",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["twitter", "status"]},
                    "action": {"type": "string", "enum": ["search", "post", "trends", "status"]},
                    "query": {"type": "string", "description": "Búsqueda en Twitter"},
                    "text": {"type": "string", "description": "Texto del tweet (máx 280 chars)"},
                    "limit": {"type": "integer", "description": "Resultados máximos (default 5)"},
                },
                "required": ["platform", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plugin",
            "description": "Gestiona plugins: list (lista plugins cargados), load (nombre), unload (nombre). Los plugins añaden herramientas dinámicamente al sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "load", "unload"]},
                    "name": {"type": "string", "description": "Nombre del plugin para load o unload"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_agent",
            "description": "Navega páginas web, hace clic, escribe texto, extrae contenido, toma screenshots o busca en Google. Acciones: navigate, click, type, extract, screenshot, search, current_url, back.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "navigate | click | type | extract | screenshot | search | current_url | back"},
                    "url": {"type": "string", "description": "URL para navigate, o query para search"},
                    "selector": {"type": "string", "description": "Selector CSS para click/type/extract, o tag para extract"},
                    "text": {"type": "string", "description": "Texto para escribir (type)"},
                    "query": {"type": "string", "description": "Query de búsqueda para search"},
                },
                "required": ["action"],
            },
        },
    },
]


def handle_run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        out = result.stdout.strip() or ""
        err = result.stderr.strip() or ""
        output = out + ("\n" + err if err else "")
        return output[:5000] if output else "[Comando ejecutado sin salida]"
    except subprocess.TimeoutExpired:
        return "[Error: el comando tardó más de 60s]"
    except Exception as e:
        return f"[Error ejecutando comando: {e}]"


def handle_web_search(query):
    try:
        from duckduckgo_search import DDGS
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        with DDGS(headers=headers) as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "[Sin resultados]"
        lines = []
        for r in results:
            lines.append(f"- {r['title']}: {r['href']}")
        return "\n".join(lines)[:3000]
    except Exception as e:
        return f"[Error en búsqueda: {e}]"


def handle_read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:5000]
    except Exception as e:
        return f"[Error leyendo archivo: {e}]"


def handle_write_file(path, content):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[Archivo escrito: {path} ({len(content)} bytes)]"
    except Exception as e:
        return f"[Error escribiendo archivo: {e}]"


def handle_list_files(path="."):
    try:
        entries = os.listdir(path)
        items = []
        for e in sorted(entries):
            full = os.path.join(path, e)
            if os.path.isdir(full):
                items.append(f"  {e}/")
            else:
                size = os.path.getsize(full)
                items.append(f"  {e} ({size} bytes)")
        return f"Contenido de {os.path.abspath(path)}:\n" + "\n".join(items[:50])
    except Exception as e:
        return f"[Error listando directorio: {e}]"


def handle_get_weather(location):
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=%C+%t+%w+%h"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode().strip()
    except Exception as e:
        return f"[Error obteniendo clima: {e}]"


def handle_calculate(expression):
    try:
        import math
        safe = {
            "abs": abs, "int": int, "float": float, "str": str,
            "len": len, "range": range, "list": list, "dict": dict,
            "sum": sum, "min": min, "max": max, "round": round,
            "pow": pow, "type": type, "bool": bool, "complex": complex,
            "pi": math.pi, "e": math.e, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "sqrt": math.sqrt, "log": math.log,
            "log10": math.log10, "floor": math.floor, "ceil": math.ceil,
            "radians": math.radians, "degrees": math.degrees,
        }
        result = eval(expression, {"__builtins__": {}}, safe)
        return str(result)
    except Exception as e:
        return f"[Error en cálculo: {e}]"


_PYTHON_NS = {}

def handle_python_repl(code):
    global _PYTHON_NS
    try:
        import builtins
        stdout = io.StringIO()
        exec_globals = _PYTHON_NS
        exec_globals["__builtins__"] = builtins
        try:
            result = eval(code, exec_globals)
            if result is not None:
                return str(result)[:3000]
            return "[Ejecutado sin valor de retorno]"
        except SyntaxError:
            old_out = sys.stdout
            old_err = sys.stderr
            sys.stdout = stdout
            sys.stderr = stdout
            try:
                exec(code, exec_globals)
                output = stdout.getvalue()
                if output:
                    return output[:3000]
                return "[Código ejecutado sin salida]"
            except Exception:
                return f"[Error Python]:\n{traceback.format_exc()[:2000]}"
            finally:
                sys.stdout = old_out
                sys.stderr = old_err
    except Exception as e:
        return f"[Error en REPL: {e}]"


def handle_system_info(category="all"):
    try:
        import psutil
        lines = []
        if category in ("all", "cpu"):
            lines.append(f"CPU: {psutil.cpu_percent(interval=0.5)}% ({psutil.cpu_count()} cores)")
        if category in ("all", "memory"):
            mem = psutil.virtual_memory()
            lines.append(f"RAM: {mem.percent}% usado ({mem.used // 1024**3}GB / {mem.total // 1024**3}GB)")
        if category in ("all", "disk"):
            disk = psutil.disk_usage("/")
            lines.append(f"Disco: {disk.percent}% usado ({disk.free // 1024**3}GB libres)")
        if category in ("all", "processes"):
            procs = len(psutil.pids())
            lines.append(f"Procesos activos: {procs}")
            top = sorted(psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
                        key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:5]
            for p in top:
                lines.append(f"  {p.info['name']}: CPU {p.info['cpu_percent']}% RAM {p.info['memory_percent']:.1f}%")
        if category in ("all", "network"):
            net = psutil.net_io_counters()
            lines.append(f"Red enviado: {net.bytes_sent // 1024}KB, recibido: {net.bytes_recv // 1024}KB")
        return "\n".join(lines)
    except ImportError:
        import platform
        uname = platform.uname()
        return f"Sistema: {uname.system} {uname.release} ({uname.machine})"
    except Exception as e:
        return f"[Error obteniendo info del sistema: {e}]"


def handle_notify(title, message):
    try:
        subprocess.run(["notify-send", title, message], timeout=5)
        return f"[Notificación enviada: {title}]"
    except FileNotFoundError:
        print(f"\n=== NOTIFICACIÓN: {title} ===\n{message}\n======================")
        return f"[Notificación mostrada en consola: {title}]"
    except Exception as e:
        return f"[Error en notificación: {e}]"


def handle_screenshot(region="full"):
    try:
        import mss
        output_dir = os.path.join(tempfile.gettempdir(), "thoth_screenshots")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = int(__import__("time").time())
        path = os.path.join(output_dir, f"screenshot_{timestamp}.png")
        with mss.mss() as sct:
            monitor = sct.monitors[0] if region == "full" else sct.monitors[1]
            sct_img = sct.grab(monitor)
            from PIL import Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            img.save(path)
        size = os.path.getsize(path)
        return f"[Captura guardada: {path} ({size} bytes)]"
    except Exception as e:
        return f"[Error capturando pantalla: {e}]"


def handle_image_analysis(path, prompt="Describe esta imagen en detalle"):
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
        api_key = os.getenv("VISION_API_KEY") or os.getenv("API_KEY") or os.getenv("GROQ_API_KEY")
        base_url = os.getenv("VISION_API_URL") or os.getenv("API_BASE_URL") or "https://api.groq.com/openai/v1"
        vision_model = os.getenv("VISION_MODEL") or os.getenv("MODEL_NAME") or "llama-3.2-11b-vision-preview"

        if not api_key:
            return "[Error: API key no configurada para visión. Configura VISION_API_KEY o GROQ_API_KEY]"

        is_url = path.startswith(("http://", "https://"))

        if not is_url:
            with open(path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
                mime = "image/png"
                if path.lower().endswith((".jpg", ".jpeg")):
                    mime = "image/jpeg"
                elif path.lower().endswith((".gif")):
                    mime = "image/gif"
                elif path.lower().endswith((".webp")):
                    mime = "image/webp"
                img_url = f"data:{mime};base64,{img_data}"
        else:
            img_url = path

        client = OpenAI(base_url=base_url, api_key=api_key)
        r = client.chat.completions.create(
            model=vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_url}},
                ],
            }],
            max_tokens=500,
        )
        return r.choices[0].message.content or "[Sin descripción]"
    except Exception as e:
        return f"[Error analizando imagen: {e}]"


def handle_browser_open(url):
    try:
        import webbrowser
        webbrowser.open(url)
        return f"[Navegador abierto: {url}]"
    except Exception as e:
        return f"[Error abriendo navegador: {e}]"


def handle_memory_search(query, semantic=False):
    try:
        from memory.store import MemoryStore
        store = MemoryStore()
        facts = store.get_facts(search=query)
        results = []

        if semantic:
            try:
                from memory.vector_store import VectorStore
                vs = VectorStore()
                semantic_results = vs.search(query, n_results=5)
                for r in semantic_results:
                    results.append(f"- ({r['category']}) {r['fact']} [sim: {r['score']:.3f}]")
            except Exception:
                pass
        else:
            results = [f"- ({f['category']}) {f['fact']}" for f in facts[:10]]

        if not results:
            return "[Sin resultados en memoria]"
        return "Recuerdos encontrados:\n" + "\n".join(results)
    except Exception as e:
        return f"[Error buscando en memoria: {e}]"


def handle_web_fetch(url, selector=None):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        if selector:
            try:
                import html.parser
                class TextExtractor(html.parser.HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text = []
                        self.skip = False
                    def handle_data(self, data):
                        if not self.skip:
                            self.text.append(data)
                    def handle_starttag(self, tag, attrs):
                        if tag in ("script", "style"):
                            self.skip = True
                    def handle_endtag(self, tag):
                        if tag in ("script", "style"):
                            self.skip = False
                extractor = TextExtractor()
                extractor.feed(html)
                text = " ".join(t for t in extractor.text if t.strip())
                return text[:4000]
            except Exception:
                pass

        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]
    except Exception as e:
        return f"[Error fetching URL: {e}]"


def handle_clipboard(action, text=None):
    try:
        import pyperclip
        if action == "read":
            content = pyperclip.paste()
            return content[:2000] if content else "[Portapapeles vacío]"
        elif action == "write":
            if text is None:
                return "[Error: texto requerido para escribir]"
            pyperclip.copy(text)
            return f"[Portapapeles actualizado: {len(text)} chars]"
        return "[Error: acción inválida]"
    except Exception as e:
        return f"[Error en portapapeles: {e}]" if "xclip" not in str(e) else "[Clipboard no disponible: instala xclip o wl-clipboard]"


def handle_switch_provider(provider):
    return f"__SWITCH_PROVIDER__:{provider}"

def handle_system_status():
    return "__SYSTEM_STATUS__"

def handle_query_documents(query, file_filter=None):
    try:
        from memory.document_processor import document_store
        results = document_store.search(query, n_results=5, file_filter=file_filter)
        if not results:
            return "[No se encontraron resultados en documentos]"
        lines = []
        seen_files = set()
        for r in results:
            seen_files.add(r["file_name"])
            lines.append(f"[{r['file_name']}] (score: {r['score']:.3f}) {r['text'][:500]}")
        header = f"Documentos consultados: {', '.join(sorted(seen_files))}"
        return header + "\n\n" + "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"[Error consultando documentos: {e}]"

def handle_list_documents():
    try:
        from memory.document_processor import document_store
        docs = document_store.list_documents()
        if not docs:
            return "[No hay documentos indexados]"
        lines = [f"- {d['file_name']} ({d['file_type']}, {d['total_chunks']} chunks)" for d in docs]
        return "Documentos disponibles:\n" + "\n".join(lines)
    except Exception as e:
        return f"[Error listando documentos: {e}]"

def handle_reminder(action, text=None, due_at=None, reminder_id=None):
    try:
        from tools.calendar_tool import handle_reminder as hr
        return hr(action, text=text, due_at=due_at, reminder_id=reminder_id)
    except Exception as e:
        return f"[Error en recordatorio: {e}]"

def handle_alarm(text, due_at):
    try:
        from tools.calendar_tool import handle_alarm as ha
        return ha(text, due_at)
    except Exception as e:
        return f"[Error en alarma: {e}]"

def handle_calendar(action, title=None, description="", start_at=None, end_at=None, event_id=None):
    try:
        from tools.calendar_tool import handle_calendar as hc
        return hc(action, title=title, description=description, start_at=start_at, end_at=end_at, event_id=event_id)
    except Exception as e:
        return f"[Error en calendario: {e}]"

def handle_email(action, to=None, subject="", body="", mailbox="INBOX", limit=5):
    try:
        from tools.email_tool import handle_email as he
        return he(action, to=to, subject=subject, body=body, mailbox=mailbox, limit=limit)
    except Exception as e:
        return f"[Error en email: {e}]"

def handle_social(platform, action, query="", text="", limit=5):
    try:
        from tools.social_tool import handle_social as hs
        return hs(platform, action, query=query, text=text, limit=limit)
    except Exception as e:
        return f"[Error en social: {e}]"

def handle_plugin(action, name=None):
    return f"__PLUGIN__:{action}:{name or ''}"

def handle_browser_agent(action, url=None, selector=None, text=None, query=None):
    try:
        from tools.browser_agent import handle_browser_agent as hb
        return hb(action, url=url, selector=selector, text=text, query=query)
    except Exception as e:
        return f"[Error en browser: {e}]"

TOOL_HANDLERS = {
    "run_command": handle_run_command,
    "web_search": handle_web_search,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "list_files": handle_list_files,
    "get_weather": handle_get_weather,
    "calculate": handle_calculate,
    "python_repl": handle_python_repl,
    "system_info": handle_system_info,
    "notify": handle_notify,
    "screenshot": handle_screenshot,
    "image_analysis": handle_image_analysis,
    "browser_open": handle_browser_open,
    "memory_search": handle_memory_search,
    "web_fetch": handle_web_fetch,
    "clipboard": handle_clipboard,
    "switch_provider": handle_switch_provider,
    "system_status": handle_system_status,
    "query_documents": handle_query_documents,
    "list_documents": handle_list_documents,
    "reminder": handle_reminder,
    "alarm": handle_alarm,
    "calendar": handle_calendar,
    "email": handle_email,
    "social": handle_social,
    "plugin": handle_plugin,
    "browser_agent": handle_browser_agent,
}

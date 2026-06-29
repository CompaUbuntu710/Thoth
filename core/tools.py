import subprocess
import json
import os
import urllib.parse
import urllib.request
import warnings
warnings.filterwarnings("ignore", message=".*renamed to ddgs.*")

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Ejecuta un comando en la terminal del usuario. Útil para abrir apps, crear archivos, correr scripts, etc.",
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
            "description": "Busca información en internet. Usar cuando no sepas algo o necesites información actualizada.",
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
            "description": "Lee el contenido de un archivo en el sistema.",
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
            "name": "get_weather",
            "description": "Obtiene el clima actual para una ubicación.",
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
            "description": "Realiza cálculos matemáticos. Útil para operaciones precisas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Expresión matemática (ej: 2 + 2 * 5)"}
                },
                "required": ["expression"],
            },
        },
    },
]


def handle_run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        out = result.stdout.strip() or ""
        err = result.stderr.strip() or ""
        output = out + ("\n" + err if err else "")
        return output[:2000] if output else "[Comando ejecutado sin salida]"
    except subprocess.TimeoutExpired:
        return "[Error: el comando tardó más de 30s]"
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
        return "\n".join(lines)[:2000]
    except Exception as e:
        return f"[Error en búsqueda: {e}]"


def handle_read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:2000]
    except Exception as e:
        return f"[Error leyendo archivo: {e}]"


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
        allowed = {"abs", "int", "float", "str", "len", "range", "list", "dict", "sum", "min", "max", "round", "pow"}
        result = eval(expression, {"__builtins__": {}}, {k: __builtins__[k] for k in allowed if k in __builtins__})
        return str(result)
    except Exception as e:
        return f"[Error en cálculo: {e}]"


TOOL_HANDLERS = {
    "run_command": handle_run_command,
    "web_search": handle_web_search,
    "read_file": handle_read_file,
    "get_weather": handle_get_weather,
    "calculate": handle_calculate,
}

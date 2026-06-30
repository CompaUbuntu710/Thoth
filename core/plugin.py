import os
import sys
import importlib
import inspect
import threading

PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins")

_registry = {}
_lock = threading.Lock()


class Plugin:
    name = ""
    version = "1.0.0"
    description = ""
    dependencies = []

    def on_load(self, engine):
        pass

    def on_unload(self, engine):
        pass

    def get_tools(self):
        return []

    def get_handlers(self):
        return {}


def discover():
    if not os.path.isdir(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        _write_sample()
    result = []
    for fname in sorted(os.listdir(PLUGINS_DIR)):
        if fname.endswith(".py") and not fname.startswith("_"):
            name = fname[:-3]
            try:
                spec = importlib.util.spec_from_file_location(name, os.path.join(PLUGINS_DIR, fname))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for _, cls in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(cls, Plugin) and cls is not Plugin:
                        result.append(cls)
            except Exception as e:
                print(f"[Plugin] Error loading {fname}: {e}")
    return result


def load_plugin(plugin_cls, engine):
    with _lock:
        name = plugin_cls.name or plugin_cls.__name__.lower()
        if name in _registry:
            return f"[Plugin '{name}' ya cargado]"
        try:
            inst = plugin_cls()
            inst.on_load(engine)
            _registry[name] = {
                "instance": inst,
                "tools": inst.get_tools(),
                "handlers": inst.get_handlers(),
            }
            return _apply(engine, name)
        except Exception as e:
            return f"[Error cargando plugin '{name}': {e}]"


def unload_plugin(name, engine):
    with _lock:
        if name not in _registry:
            return f"[Plugin '{name}' no encontrado]"
        try:
            inst = _registry[name]["instance"]
            inst.on_unload(engine)
            old_tools = _registry[name]["tools"]
            old_handlers = list(_registry[name]["handlers"].keys())
            for t in old_tools:
                tn = t.get("function", {}).get("name", "")
                if tn in engine._plugin_tools:
                    engine._plugin_tools.remove(tn)
                engine._plugin_schemas[:] = [s for s in engine._plugin_schemas if s.get("function", {}).get("name") != tn]
            for h in old_handlers:
                engine._plugin_handlers.pop(h, None)
            del _registry[name]
            return f"[Plugin '{name}' descargado]"
        except Exception as e:
            return f"[Error descargando plugin '{name}': {e}]"


def list_plugins():
    with _lock:
        return [
            {"name": n, "version": v["instance"].version, "description": v["instance"].description}
            for n, v in _registry.items()
        ]


def _apply(engine, name):
    entry = _registry[name]
    tools = entry["tools"]
    handlers = entry["handlers"]
    count = 0
    for t in tools:
        tn = t.get("function", {}).get("name", "")
        if tn:
            engine._plugin_tools.append(tn)
            engine._plugin_schemas.append(t)
            count += 1
    for hn, hf in handlers.items():
        engine._plugin_handlers[hn] = hf
    return f"[Plugin '{name}' cargado: {count} herramienta(s)]"


def load_all(engine):
    results = []
    for cls in discover():
        r = load_plugin(cls, engine)
        results.append(r)
    return results


def _write_sample():
    sample = os.path.join(PLUGINS_DIR, "ejemplo.py")
    if not os.path.exists(sample):
        with open(sample, "w") as f:
            f.write('''from core.plugin import Plugin


class EjemploPlugin(Plugin):
    name = "ejemplo"
    version = "1.0.0"
    description = "Plugin de ejemplo que añade una herramienta"

    def get_tools(self):
        return [{
            "type": "function",
            "function": {
                "name": "saludar",
                "description": "Saluda a alguien",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nombre": {"type": "string", "description": "Nombre de la persona"},
                    },
                    "required": ["nombre"],
                },
            },
        }]

    def get_handlers(self):
        return {"saludar": self.handle_saludar}

    def handle_saludar(self, nombre="mundo"):
        return f"¡Hola {nombre}! desde el plugin ejemplo v{self.version}"
''')


from core.plugin import Plugin


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

# 𓁞 Thoth — Asistente IA Autónomo

> Construyendo mi propio JARVIS desde cero. Open-source, local y autónomo.

## Stack

| Capa | Tecnología |
|---|---|
| Motor LLM | Groq (llama-3.3-70b-versatile) → próximamente Ollama local |
| Backend | Python + FastAPI + Uvicorn |
| Memoria | SQLite (persistente por sesión) |
| Visión | LLaVA / MiniCPM-V (local, próximamente) |
| Documentos | PDF, JSON, CSV, MD |

## Inicio rápido

```bash
git clone https://github.com/CompaUbuntu710/Thoth.git
cd Thoth
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar API key
echo "GROQ_API_KEY=gsk_tu_key_aqui" > .env

# Arrancar
./thoth.sh
```

## Endpoints

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Health check |
| `/chat` | POST | Enviar mensaje a Thoth |

### Ejemplo `POST /chat`

```json
{"message": "¿Quién eres?", "session_id": "default"}
```

## Estructura

```
Thoth/
├── api/main.py       # FastAPI server
├── core/engine.py    # ThothEngine (Groq)
├── core/readers.py   # Lectura de documentos
├── core/vision.py    # Análisis de imágenes
├── memory/store.py   # Persistencia SQLite
├── chat.py           # Cliente de terminal
├── thoth.sh          # Script todo-en-uno
└── requirements.txt  # Dependencias
```

## Roadmap

- [x] Backend funcional con Groq
- [x] Chat por terminal
- [ ] Memoria persistente entre sesiones
- [ ] Ollama local (modelo open-source)
- [ ] Visión por cámara
- [ ] Voz (texto a voz / voz a texto)
- [ ] Interfaz web
- [ ] Plugins y herramientas externas

## Redes

Construido en público por **@CompaUbuntu710**.

# 𓁞 Thoth — Documentación completa

> Asistente IA autónomo multi-agente. Inspirado en JARVIS. Construido en público por **@CompaUbuntu710**.

---

## 1. Arquitectura

```
┌──────────────────────────────────────────────────┐
│                   CLIENTES                        │
│  Web UI │ Telegram │ Terminal │ API               │
└──────────────────────┬───────────────────────────┘
                       │ WS / HTTP / SSE
┌──────────────────────▼───────────────────────────┐
│              FASTAPI SERVER                        │
│  api/main.py │ api/ws_manager.py │ api/telegram   │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│              THOTH ENGINE                          │
│  core/engine.py                                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │ LLM     │ │ Tools   │ │ Memory  │              │
│  │ Router  │ │ (18)    │ │ Store   │              │
│  └─────────┘ └─────────┘ └─────────┘              │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│              PROVIDERS                             │
│  Groq │ OpenRouter │ NVIDIA │ Together             │
│  (switchable in hot)                               │
└───────────────────────────────────────────────────┘
```

### Flujo de datos

1. Usuario envía mensaje por web UI, Telegram o terminal
2. ThothEngine construye mensajes con system prompt + historia + memoria
3. LLM responde con texto o decide usar una herramienta (tool calling)
4. Si usa herramientas: ejecuta → realimenta → hasta 3 rondas de encadenamiento
5. Cada 2 mensajes: extracción automática de hechos → memoria persistente
6. Respuesta final se guarda en SQLite y se devuelve al cliente
7. Streaming SSE: el frontend recibe tokens en tiempo real

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.14 |
| Backend | FastAPI + Uvicorn |
| LLMs | Groq / OpenRouter / NVIDIA / Together (hot-swappable) |
| Streaming | SSE (Server-Sent Events) |
| Tiempo real | WebSocket |
| Cliente OpenAI | openai >=1.0 |
| STT (voz → texto) | Vosk + modelo español (local) |
| TTS (texto → voz) | Piper TTS + espeak-ng fallback |
| Wake word | Vosk + RMS energy detection |
| Memoria | SQLite (WAL mode, thread-safe) |
| Documentos | PyMuPDF (PDF), JSON, CSV, MD |
| Imágenes | Pillow + LLM visión |
| UI Web | Three.js + CSS vanilla |
| Contenedor | Docker + docker-compose |

---

## 3. Estructura del proyecto

```
~/Thoth/
├── api/
│   ├── main.py              # FastAPI server (15+ endpoints)
│   ├── telegram_bot.py      # Bot de Telegram
│   └── ws_manager.py         # WebSocket connection manager
│
├── core/
│   ├── engine.py             # ThothEngine (multi-provider, tool chaining)
│   ├── tools.py              # 18 herramientas (function calling)
│   ├── readers.py            # PDF / JSON / CSV / MD
│   └── vision.py             # Captura de cámara + metadatos
│
├── memory/
│   └── store.py              # SQLite persistente (thread-safe)
│
├── voice/
│   ├── stt.py                # Speech-to-text con Vosk
│   ├── tts.py                # Text-to-speech (Piper + espeak)
│   └── wake.py               # Wake word detection
│
├── ui/
│   ├── index.html            # Single-page app
│   ├── style.css             # Tema sci-fi / glassmorphism
│   ├── app.js                # 3D scene + chat + HUD + WebSocket
│   └── js/
│       ├── map-view.js       # Mapa mental (canvas)
│       └── music-player.js   # Sintetizador ambiental (Web Audio)
│
├── scripts/                  # Scripts auxiliares
├── Dockerfile                # Contenedor producción
├── docker-compose.yml        # Orquestación
├── chat.py                   # Cliente de terminal
├── requirements.txt          # Dependencias pip
├── README.md                 # Documentación principal
└── .env                      # API keys (no se sube a git)
```

---

## 4. Instalación

### Docker (recomendado — 3 clics)

```bash
git clone https://github.com/CompaUbuntu710/Thoth.git
cd Thoth
# 1. Configura .env con tu API key de Groq
echo "GROQ_API_KEY=gsk_tu_key_aqui" >> .env
# 2. Un comando
docker compose up -d
# 3. Abre http://localhost:8000
```

### Manual

```bash
git clone https://github.com/CompaUbuntu710/Thoth.git
cd Thoth
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=gsk_tu_key_aqui" > .env
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 5. API Endpoints

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Web UI |
| `/api/health` | GET | Health check |
| `/api/sysinfo` | GET | Uptime, memorias, sesiones |
| `/api/stats` | GET | Stats detallados + provider |
| `/api/sessions` | GET | Lista de sesiones |
| `/api/history/{id}` | GET | Historial de mensajes de una sesión |
| `/chat` | POST | Chat (respuesta completa) |
| `/chat/stream` | POST | Chat con streaming SSE |
| `/memories` | GET | Lista de recuerdos |
| `/forget` | POST | Olvidar un hecho |
| `/remember` | POST | Recordar un hecho |
| `/news` | GET | Últimas noticias |
| `/ws` | WebSocket | Conexión tiempo real |
| `/static/*` | GET | Archivos estáticos |

---

## 6. Proveedores disponibles

| Proveedor | Chat | Extracción | Visión |
|---|---|---|---|
| **Groq** | llama-3.3-70b-versatile | llama-3.1-8b-instant | llama-3.2-11b-vision |
| **OpenRouter** | gpt-4o | gpt-4o-mini | gpt-4o |
| **NVIDIA** | llama-3.1-70b-instruct | llama-3.1-8b-instruct | llama-3.2-90b-vision |
| **Together** | Mixtral-8x22B | Mistral-7B | Llama-3.2-11B-Vision |

Cambio en caliente: `switch_provider("openrouter")` desde el chat.

---

## 7. Herramientas (18)

| Herramienta | Descripción |
|---|---|
| `run_command` | Ejecuta comandos bash |
| `web_search` | Busca en internet (DuckDuckGo) |
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `list_files` | Lista directorios |
| `get_weather` | Clima por wttr.in |
| `calculate` | Cálculos matemáticos |
| `python_repl` | Ejecuta Python (persistente) |
| `system_info` | CPU, RAM, disco, procesos |
| `notify` | Notificaciones de escritorio |
| `screenshot` | Captura de pantalla |
| `image_analysis` | Analiza imágenes con IA |
| `browser_open` | Abre URLs |
| `memory_search` | Busca en memoria persistente |
| `web_fetch` | Extrae contenido web |
| `clipboard` | Lee/escribe portapapeles |
| `switch_provider` | Cambia proveedor de IA |
| `system_status` | Muestra configuración actual |

---

## 8. Roadmap

### Completado ✅

- [x] Backend multi-provider (Groq, OpenRouter, NVIDIA, Together)
- [x] 18 herramientas con function calling
- [x] Encadenamiento multi-turno (hasta 3 rondas)
- [x] Memoria SQLite persistente (thread-safe)
- [x] Extracción automática de hechos
- [x] Web UI con Three.js 3D, chat, HUD, mapa mental, música
- [x] Streaming SSE en tiempo real
- [x] Historial de chat persistente en UI
- [x] WebSocket para actualizaciones en vivo
- [x] Bot de Telegram (código listo, requiere token)
- [x] Voz local (Vosk STT + Piper TTS + wake word)
- [x] Visión por IA multi-proveedor
- [x] Docker + docker-compose (3-clicks deploy)
- [x] Proveedores intercambiables en caliente
- [x] Documentación y README

### Pendiente

- [ ] Multi-agente (coordinador + especialistas + crítico)
- [ ] Memoria semántica (ChromaDB embeddings)
- [ ] RAG sobre documentos (subida + chunking + query)
- [ ] Plugins SDK
- [ ] Auto-mejora (feedback loop)
- [ ] Calendario / recordatorios / alarmas
- [ ] Email / notificaciones push
- [ ] Ollama local (modelos offline)
- [ ] Autenticación multi-usuario
- [ ] Stripe billing
- [ ] Dashboard de configuración

---

## 9. Comandos rápidos

```bash
# Arrancar con Docker
docker compose up -d

# Arrancar manual
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Chat por terminal
python3 chat.py

# Chat con voz
python3 chat.py --tts

# Pushear cambios
git add -A && git commit -m "mensaje" && git push

# Ver el repo
xdg-open https://github.com/CompaUbuntu710/Thoth
```

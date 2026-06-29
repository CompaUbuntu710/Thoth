# 𓁞 Thoth — Documentación completa

> Asistente IA autónomo. Inspirado en JARVIS. Construido en público por **@CompaUbuntu710**.

---

## Índice

1. [Arquitectura](#1-arquitectura)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Instalación](#4-instalación)
5. [Uso](#5-uso)
6. [Módulo de voz](#6-módulo-de-voz)
7. [Módulo de memoria](#7-módulo-de-memoria)
8. [Lectura de documentos](#8-lectura-de-documentos)
9. [Visión](#9-visión)
10. [API endpoints](#10-api-endpoints)
11. [Roadmap](#11-roadmap)
12. [Comandos rápidos](#12-comandos-rápidos)

---

## 1. Arquitectura

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐
│ Terminal │────▶│  FastAPI      │────▶│  Groq API    │
│ chat.py  │     │  api/main.py  │     │  Llama 3.3   │
└──────────┘     └──────┬───────┘     └─────────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
        ┌──────────┐       ┌──────────┐
        │ SQLite   │       │  Vosk    │
        │ Memoria  │       │  STT     │
        └──────────┘       └──────────┘
                                │
                                ▼
                          ┌──────────┐
                          │ espeak   │
                          │ TTS      │
                          └──────────┘
```

### Flujo de datos

1. El usuario envía un mensaje (texto o voz)
2. Si es voz → `voice/stt.py` lo transcribe con Vosk (local)
3. `chat.py` envía el texto a `api/main.py` (FastAPI)
4. `api/main.py` llama a `core/engine.py` (ThothEngine)
5. ThothEngine envía el mensaje a Groq API + historial
6. Groq responde → se guarda en SQLite → se devuelve al chat
7. Si TTS activo → `voice/tts.py` habla la respuesta con espeak-ng

---

## 2. Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.14 |
| LLM | Groq (llama-3.3-70b-versatile) | — |
| Servidor | FastAPI + Uvicorn | >=0.100 |
| Cliente OpenAI | openai (Groq-compatible) | >=1.0 |
| STT (voz → texto) | Vosk + vosk-model-small-es-0.42 | 0.3.45 |
| TTS (texto → voz) | pyttsx3 + espeak-ng | 2.99 |
| Memoria | SQLite (WAL mode) | — |
| Documentos | PyMuPDF (PDF), JSON, CSV | >=1.23 |
| Imágenes | Pillow | >=10.0 |
| Dependencias | python-dotenv, requests, pydantic | — |

### Hardware actual

- **Laptop:** HP Laptop 14-dq6xxx
- **CPU:** Intel N150 (4 núcleos)
- **RAM:** 3.2 GB
- **Micrófono:** Integrado (DMIC)
- **SO:** Ubuntu (Resolute)

---

## 3. Estructura del proyecto

```
~/Thoth/
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI server (2 endpoints)
│
├── core/
│   ├── __init__.py
│   ├── engine.py             # ThothEngine → Groq API
│   ├── readers.py            # PDF / JSON / CSV / MD
│   └── vision.py             # Captura + descripción de imágenes
│
├── memory/
│   ├── __init__.py
│   └── store.py              # SQLite persistente (sesiones + docs)
│
├── voice/
│   ├── __init__.py            # Exporta listen(), speak()
│   ├── stt.py                 # Speech-to-text con Vosk
│   ├── tts.py                 # Text-to-speech con espeak-ng
│   └── download_model.sh      # Descarga el modelo Vosk español
│
├── scripts/                   # (vacío — para futuros scripts)
├── ui/                        # (vacío — para futura interfaz web)
│
├── chat.py                    # Cliente de terminal con voz integrada
├── thoth.sh                   # Script todo-en-uno (server + chat)
├── run.sh                     # Solo arranca el servidor
├── requirements.txt           # Dependencias pip
├── README.md                  # Documentación principal
├── thoth-docs.md              # Esta documentación
├── .env                       # GROQ_API_KEY (no se sube a git)
└── .gitignore                 # venv, pycache, .env, .db
```

---

## 4. Instalación

### Requisitos del sistema

```bash
sudo apt install -y espeak-ng portaudio19-dev python3-pyaudio
```

### Clonar e instalar

```bash
git clone https://github.com/CompaUbuntu710/Thoth.git
cd Thoth
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### API key

```bash
# Ve a https://console.groq.com/keys y genera una key
echo "GROQ_API_KEY=gsk_tu_key_aqui" > .env
```

### Modelo de voz (STT)

```bash
# Opción 1: con el script
bash voice/download_model.sh

# Opción 2: manual
cd voice
wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
unzip vosk-model-small-es-0.42.zip
rm vosk-model-small-es-0.42.zip
```

---

## 5. Uso

### Una terminal (recomendado)

```bash
cd ~/Thoth && source venv/bin/activate

# Solo texto
./thoth.sh

# Con voz (Thoth habla las respuestas)
./thoth.sh --tts
```

### Dos terminales (debug)

```bash
# Terminal 1: servidor
cd ~/Thoth && source venv/bin/activate
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: chat
source venv/bin/activate
python3 chat.py            # texto
python3 chat.py --tts      # con voz
```

### Comandos dentro del chat

| Acción | Qué hacer |
|---|---|
| Escribir normal | Envía mensaje de texto a Thoth |
| Enter vacío | Activa el micrófono (5s de grabación) |
| `:tts` | Activa / desactiva la voz de Thoth |
| `salir` / `exit` / `quit` | Cierra el chat |

---

## 6. Módulo de voz

### STT — Speech-to-Text (`voice/stt.py`)

| Función | Descripción |
|---|---|
| `record_audio(duration, samplerate)` | Graba con `arecord` y guarda WAV temporal |
| `transcribe(path, duration)` | Pasa el audio por Vosk y devuelve texto |
| `listen(duration)` | Graba + transcribe + muestra resultado |

**Modelo:** `vosk-model-small-es-0.42` (~40MB, español)
**Latencia:** ~1-2s (en Intel N150)

### TTS — Text-to-Speech (`voice/tts.py`)

| Función | Descripción |
|---|---|
| `speak(text)` | Habla el texto con espeak-ng |
| `say_thoth(reply)` | Ídem (alias) |

**Voz:** espeak-ng, selecciona español automáticamente
**Velocidad:** 160 palabras/minuto
**Volumen:** 0.9

---

## 7. Módulo de memoria

### `memory/store.py` — SQLite

| Tabla | Columnas | Propósito |
|---|---|---|
| `sessions` | id, created_at, updated_at | Sesiones de chat |
| `messages` | id, session_id, role, content, timestamp | Historial de mensajes |
| `facts` | id, fact (UNIQUE), category, source_session, created_at, updated_at | Memoria de largo plazo |
| `documents` | id, name, type, content, path, created_at | Documentos procesados |

### Funciones principales

```python
store = MemoryStore()
store.save_message("default", "user", "Hola Thoth")
store.save_message("default", "assistant", "¡Hola!")
history = store.get_history("default", limit=50)
store.save_fact("Al usuario le gusta el cafe", "gusto")
facts = store.get_facts()         # Todos
facts = store.get_facts("cafe")   # Búsqueda
store.delete_fact("Al usuario le gusta el cafe")
store.save_document("notas.pdf", "pdf", content=texto)
```

### Memoria persistente de largo plazo

Thoth extrae automáticamente hechos cada 2 mensajes usando `llama-3.1-8b-instant`.
Los hechos se inyectan en el system prompt de cada conversación.

**Comandos del chat:**

| Comando | Qué hace |
|---|---|
| `:recuerda X` | Guarda el hecho X explícitamente |
| `:olvida X` | Borra el hecho X |
| `:recuerdos` | Lista todo lo que Thoth recuerda |

**Archivo DB:** `memory/thoth.db` (gitignored)

---

## 8. Lectura de documentos

### `core/readers.py`

| Función | Formatos |
|---|---|
| `read_pdf(path)` | PDF (con PyMuPDF) |
| `read_json(path)` | JSON |
| `read_csv(path)` | CSV (formateado como tabla) |
| `read_md(path)` | Markdown y TXT |
| `read_file(path)` | Detecta extensión automáticamente |

---

## 9. Visión

### `core/vision.py`

| Función | Descripción |
|---|---|
| `capture_camera()` | Captura foto con libcamera-still o fswebcam |
| `describe_image(path)` | Carga imagen con Pillow y devuelve metadatos |

> **Estado:** Básico. Sin LLM multimodal aún. Requiere Pillow + cámara.

---

## 10. API endpoints

### `GET /`

```json
{"status": "awakening", "message": "Día 1: Thoth despierta"}
```

### `POST /chat`

**Request:**
```json
{"message": "¿Quién eres?"}
```

**Response:**
```json
{"reply": "Soy Thoth, el asistente de @CompaUbuntu710..."}
```

**Desde terminal:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Quién eres?"}'
```

---

## 11. Roadmap

### Completado ✅

- [x] Backend funcional con Groq (Llama 3.3 70B)
- [x] Chat por terminal
- [x] README y documentación
- [x] Memoria SQLite persistente (historial por sesión)
- [x] Memoria de largo plazo (hechos extraídos automáticamente)
- [x] Voz local (Vosk STT + espeak-ng TTS)
- [x] Chat con voz integrada (Enter para hablar)
- [x] Script todo-en-uno (server + chat en 1 terminal)
- [x] Lectura de documentos (PDF, JSON, CSV, MD)
- [x] Captura de cámara (básico)
- [x] Limpieza de secretos del historial git
- [x] Repositorio público en GitHub

### Pendiente

- [ ] Tool use / function calling (ejecutar comandos, web search, etc.)
- [ ] Despertar por voz (hotword "Hey Thoth")
- [ ] Ollama local (modelo open-source sin depender de Groq)
- [ ] Visión por cámara con LLaVA / MiniCPM-V
- [ ] Interfaz web (dashboard tipo JARVIS)
- [ ] Plugins (clima, calendario, noticias, etc.)
- [ ] Voz de mayor calidad (Piper TTS)
- [ ] Recordatorios y alarmas
- [ ] Integración con el sistema de archivos

---

## 12. Comandos rápidos

```bash
# Arrancar Thoth completo
./thoth.sh

# Arrancar con voz
./thoth.sh --tts

# Solo servidor (debug)
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Solo chat
python3 chat.py

# Chat con voz
python3 chat.py --tts

# Probar voz (STT + TTS)
python3 -c "from voice import listen, speak; speak('Listo'); print(listen(5))"

# Ver el historial de git
git log --oneline

# Pushear cambios
git add -A && git commit -m "mensaje" && git push

# Ver el repo en GitHub
xdg-open https://github.com/CompaUbuntu710/Thoth
```

---

> **Thoth** — *"El conocimiento no es poder. El poder es aplicar el conocimiento."*
>
> Construido en público por [@CompaUbuntu710](https://github.com/CompaUbuntu710)

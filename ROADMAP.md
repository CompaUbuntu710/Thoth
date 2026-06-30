# ROADMAP — Thoth: De agente personal a plataforma de IA

**Visión:** Thoth no será solo un asistente. Será un **sistema opernico de agentes de IA** — tu propia infraestructura inteligente, local primero, omnipresente por diseño.

> "No compites con Claude/Hermes/OpenClaw. Compites con la idea de que una persona necesite más de un asistente."

---

## 1. DIAGNÓSTICO ACTUAL

| Dimensión | Estado | Nota |
|---|---|---|
| Core LLM loop | ✅ 80% | Multi-provider, tool chaining 3 rounds |
| Tools | ✅ 18 | 16 funcionales, 2 stub (switch_provider, system_status) |
| Memoria persistente | ✅ SQLite básica | Sin búsqueda semántica |
| Web UI | ✅ 3D + chat + HUD | Sin historial en carga, sin streaming |
| Voz local | ✅ STT + TTS + wake word | Solo Linux ALSA, no integrado al server |
| Telegram bot | 🟡 Código listo | Sin TELEGRAM_BOT_TOKEN en .env |
| Visión | ✅ image_analysis tool | camera.py es dead code |
| Documentos | 🟡 Tabla en DB | Sin tool para consultarlos |
| Autenticación | ❌ | Todo abierto |
| Streaming | ❌ | UI espera respuesta completa |
| Multi-agente | ❌ | Un solo engine |
| Plugins | ❌ | Sin sistema de plugins |
| Procesamiento documentos | ❌ | Sin RAG real |
| Calendario/Recordatorios | ❌ | En roadmap original |
| Email/SMS/Notif | ❌ | Solo Telegram stub |
| One-click deploy | ❌ | Sin Dockerfile ni deploy script |
| Dashboard configuración | ❌ | Sin UI de settings |
| Multi-usuario | ❌ | Sin auth ni workspaces |
| Local models (Ollama) | ❌ | Solo APIs cloud |
| Auto-mejora | ❌ | Sin feedback loop |

---

## 2. PILARES ESTRATÉGICOS — Qué hace a Thoth imbatible

### Pilar A: Local-first + Cloud-flex
Thoth corre **100% offline** con Ollama + Whisper + Piper. Cuando necesita poder bruto, escala a Groq/OpenRouter. El usuario no configura nada — Thoth elige automáticamente.

### Pilar B: Memoria que sí funciona
No es RAG pegado con ChatGPT. Es:
- Memoria episódica (conversaciones completas resumidas)
- Memoria semántica (embeddings locales con ChromaDB)
- Memoria procedural (aprende cómo trabajas: "cuando digo X, siempre hago Y")
- Memoria social (recuerda personas, relaciones, preferencias)

### Pilar C: Multi-agente orquestado
No un solo LLM. Una **corte de agentes**:
- **Thoth** (coordinador) — recibe la orden, la descompone
- **Especialistas** — código, archivos, web, calendario, email, redes sociales
- **Crítico** — revisa el output antes de entregarlo
- **Aprendiz** — observa patrones y sugiere automatizaciones

### Pilar D: Omnicanal nativo
Una sesión, cualquier interfaz:
- Web UI ↔ Telegram ↔ WhatsApp ↔ Discord ↔ SMS ↔ Terminal
- Todos ven el mismo historial, la misma memoria, los mismos agentes.

### Pilar E: 3 clicks al paraíso
```
Click 1: docker run thoth
Click 2: Escanea QR → vincula tu Telegram/WhatsApp
Click 3: "Thoth, conóceme"
```

### Pilar F: Auto-mejora continua
Thoth registra cada interacción, detecta patrones de error, ajusta prompts, sugiere nuevas tools, y mejora su system prompt solo.

---

## 3. ROADMAP POR FASES

### FASE 0 — Cimientos rotos (1-2 semanas)
*Lo que hay que arreglar antes de construir*

- [ ] **Dockerizar** — Dockerfile + docker-compose con volúmenes
- [ ] **requirements.txt completo** — añadir mss, pyperclip
- [ ] **TELEGRAM_BOT_TOKEN en .env** — reactivar bot
- [ ] **core/vision.py → integrar o eliminar** — decidir si se usa o se borra
- [ ] **Bugfix: store thread-safety** — conection pool o lock para SQLite multi-thread
- [ ] **Bugfix: streaming básico** — SSE endpoint para no bloquear UI
- [ ] **Cargar historial en UI** — GET /history/:session al cargar página
- [ ] **thoth-docs.md actualizar** — reflejar estado real

### FASE 1 — Producto mínimo vendible (2-4 semanas)
*Alguien paga por esto*

**Onboarding 3 clicks:**
- [ ] `docker-compose up` con auto-configuración
- [ ] Setup wizard web (primera vez: nombre, API keys, Telegram link)
- [ ] QR code para vincular Telegram al instante

**Multi-agente básico:**
- [ ] Refactor engine → `Orchestrator` + `Agent` classes
- [ ] Agente coordinador (Thoth) + 3 especialistas: `code_agent`, `web_agent`, `file_agent`
- [ ] Cada agente con su propio system prompt y tools
- [ ] El coordinador decide qué agente llama según la query

**Memoria mejorada:**
- [ ] ChromaDB local para embeddings semánticos
- [ ] Resumen automático de conversaciones viejas (antes de que caigan del history)
- [ ] Búsqueda híbrida: SQL LIKE + embedding cosine similarity

**Dashboard básico:**
- [ ] Página de settings con provider selector + API key inputs
- [ ] Historial de conversaciones navegable
- [ ] Panel de herramientas (activar/desactivar cada tool)

**Infraestructura:**
- [ ] Autenticación básica (JWT + password)
- [ ] Endpoints rate-limited
- [ ] Logging estructurado

### FASE 2 — Potencia real (1-2 meses)
*Esto ya es mejor que la competencia*

**Procesamiento de documentos (RAG):**
- [ ] Subida de archivos por UI (PDF, DOCX, TXT, MD, CSV, JSON, imágenes)
- [ ] Ingesta → chunking → embeddings → ChromaDB
- [ ] Tool `query_documents(query, file_filter?)` con contexto automático
- [ ] "Thoth, busca en mis documentos del proyecto X..."

**Voz completa integrada al server:**
- [ ] Endpoint WebSocket para STT streaming
- [ ] Botón de micrófono en UI web
- [ ] Wake word desde el server (Thoth escucha aunque no haya UI abierta)
- [ ] TTS en UI web (Browser Web Speech API o streaming al client)

**Calendario y tiempo:**
- [ ] Tool `calendar` — integración CalDAV/Google Calendar
- [ ] Tool `reminder` — recordatorios persistentes con check cada N segundos
- [ ] Tool `alarm` — alarma absoluta o relativa
- [ ] "Thoth, recuérdame enviar el correo mañana a las 9"

**Web avanzado:**
- [ ] Tool `browser_agent` — Playwright headless, navega páginas, extrae datos, llena forms
- [ ] Tool `email` — enviar/leer email por SMTP/IMAP
- [ ] Tool `social` — postear a redes sociales (Twitter/IG via APIs)

**Observabilidad:**
- [ ] Dashboard de uso: tokens, requests, costos por proveedor
- [ ] Alertas de rate limit y fallos
- [ ] Historial de errores con stack traces

### FASE 3 — Autonomía y plugins (2-3 meses)
*Thoth se vuelve plataforma*

**Sistema de plugins:**
- [ ] `~/.thoth/plugins/` — cada plugin es un directorio con `manifest.json` + código
- [ ] Plugin API: hooks para `on_message`, `on_tool_call`, `on_memory_read`
- [ ] Store de plugins (primeros: clima, crypto, noticias, música Spotify)
- [ ] Tool `install_plugin(url)` — instala desde GitHub

**Agente crítico (self-correcting):**
- [ ] Segundo LLM call después de cada respuesta: "¿Esto está bien? Señala errores."
- [ ] Si el crítico detecta un error, Thoth lo corrige antes de mostrar al usuario
- [ ] Modo "confianza": crítico solo para acciones destructivas (rm, delete, etc.)

**Auto-mejora:**
- [ ] Thoth analiza conversaciones fallidas (donde el usuario dijo "no", "eso no", etc.)
- [ ] Ajusta prompts de agentes específicos según patrones de error
- [ ] Sugiere nuevas tools al usuario: "He notado que cada semana me pides X. ¿Quieres que lo automatice?"

**Ollama integration:**
- [ ] Provider `ollama` con auto-detección de modelos instalados
- [ ] Modo híbrido: Ollama para tareas rápidas (extracción, crítica), cloud para razonamiento complejo
- [ ] Fallback automático si Ollama no responde

### FASE 4 — SaaS Multi-usuario (3-4 meses)
*Esto genera $75K/mes*

**Multi-workspace:**
- [ ] Workspaces con usuarios invitados
- [ ] Cada workspace tiene su propia memoria, agentes, tools, plugins
- [ ] Roles: admin, editor, viewer

**Stripe billing:**
- [ ] Plan Free: 1 usuario, 100 msgs/día, 1 agente
- [ ] Plan Pro ($15/mes): usuarios ilimitados, mensajes ilimitados, todos los agentes
- [ ] Plan Enterprise ($50/mes): On-prem, audit logs, SLA
- [ ] Stripe Checkout + portal de facturación

**One-click deploy cloud:**
- [ ] Template de Railway / Fly.io / Render
- [ ] Deploy automático via GitHub Action
- [ ] Managed PostgreSQL + Redis

**Ecommerce / funnel:**
- [ ] Kit "Arma tu Thoth" ($47-97) — template + prompts + setup guiado
- [ ] Curso "Build in Public" ($197)
- [ ] Landing page + Product Hunt launch

### FASE 5 — Visión 20/20 (ongoing)
*Thoth te conoce mejor que tú mismo*

- [ ] **Visión por cámara en tiempo real** — Thoth ve lo que ves (con permiso)
- [ ] **Contexto ambiental** — hora, ubicación, actividad, calendario → respuestas proactivas
- [ ] **Perfil de usuario dinámico** — Thoth construye un modelo de ti: cómo hablas, qué prefieres, tu ritmo
- [ ] **Agentes autónomos en background** — "Thoth, cada noche a las 11 revisa mi email y resúmelo"
- [ ] **Multi-idioma nativo** — sin prompts, detecta y responde en el idioma del usuario

---

## 4. ARQUITECTURA OBJETIVO (Fase 4)

```
┌──────────────────────────────────────────────────────────┐
│                    CLIENTES                               │
│  Web UI │ Telegram │ WhatsApp │ Discord │ Terminal │ API │
└──────────────────────┬───────────────────────────────────┘
                       │ WS / HTTP / Webhook
┌──────────────────────▼───────────────────────────────────┐
│              API GATEWAY (FastAPI)                         │
│  Auth │ Rate Limit │ Routing │ WebSocket Manager          │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│              ORCHESTRATOR                                  │
│  Recibe request → decide agente → ejecuta → devuelve      │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │  Thoth   │ │  Code    │ │  Web     │ │  Critic      │ │
│  │ (coord)  │ │  Agent   │ │  Agent   │ │  Agent       │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │  File/   │ │  Email   │ │  Social  │ │  Learning    │ │
│  │  Doc     │ │  Agent   │ │  Agent   │ │  Agent       │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│              SERVICIOS                                     │
│  LLM Router │ Memory Store │ Plugin Manager │ Task Queue  │
│  (Groq/OR/NV/Tog/Ollama)  │                              │
│  ChromaDB │ SQLite/Postgres │ Redis │ Celery              │
└───────────────────────────────────────────────────────────┘
```

---

## 5. MÉTRICAS CLAVE

| Feature | Competencia lo tiene? | Thoth lo hará mejor porque... |
|---|---|---|
| Memoria larga | ❌ Claude/Hermes apenas会话记忆 | Local + semántica + procedural |
| Multi-agente | 🟡 Solo herramientas | Agentes con personalidad y crítica |
| Offline total | ❌ Ninguno | Ollama + Whisper + Piper |
| Omnicanal | ❌ Solo web o solo chat | Web + Telegram + WhatsApp + API |
| Auto-mejora | ❌ Ninguno | Feedback loop automático |
| Plugins | 🟡 Solo lo que permite el system prompt | SDK real con hooks |
| 3-click deploy | ❌ Claude necesita cuenta + API key | docker compose up |
| Costo predictible | ❌ API-based, variable | Híbrido local/cloud |
| Privacidad | ❌ Todos cloud | Local-first por defecto |

---

## 6. TAM BREAKDOWN ($75K/mes)

| Fuente | Usuarios | Precio | MRR |
|---|---|---|---|
| Kit "Arma tu Thoth" | 200-500 ventas únicas | $47-97 | $9,400-23,500 (one-time) |
| SaaS Pro | 2,500 | $15/mes | $37,500 |
| SaaS Enterprise | 50 | $50/mes | $2,500 |
| Curso | 50-150 ventas únicas | $197 | $9,850-29,550 (one-time) |
| Brand deals | 3/mes | $500-2,000 | $1,500-6,000 |
| Afiliados | — | 10-20% | $100-500 |
| **TOTAL mensual recurrente** | | | **~$40,000-46,000** |
| **+ one-time** | | | **~$19,000-53,000** |

**Camino realista a 12 meses:** 2,500 usuarios Pro × $15 = $37,500 MRR + ingresos complementarios.

---

## 7. PRÓXIMA ACCIÓN INMEDIATA

Lo que hagas esta semana define si Thoth es un proyecto personal o un producto:

1. **Dockerizar** — `docker compose up` debe funcionar en cualquier máquina. Sin eso, no hay "3 clicks".
2. **Poner TELEGRAM_BOT_TOKEN** — es tu canal de mayor tracción potencial (build in público).
3. **Refactor engine a multi-agente** — el core loop actual es monolítico. Separar coordinador de especialistas es la decisión arquitectónica más importante.

El resto del roadmap se construye sobre esas 3 bases.

# Chatbot AI System

A production-grade, multi-tenant AI chatbot platform with multi-provider LLM support, multimodal input (image, audio, video), real-time voice conversation, WebSocket streaming, and modern UI.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** with Poetry
- **Node.js 20+** with npm
- **Docker & Docker Compose** (for PostgreSQL & Redis)
- **Ollama** (for local LLM) - [Install Ollama](https://ollama.ai/)
- **FFmpeg** (for audio/video processing) - `brew install ffmpeg`

### 1. Setup Environment

```bash
# Clone and navigate to project
cd /Users/mk/Documents/chatbot-ai-systems-production

# Copy environment files
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

> [!IMPORTANT]
> **MCP Configuration**: The `.env` file includes sections for MCP server API keys.
> You must populate these keys (e.g., `BRAVE_API_KEY`, `GITHUB_TOKEN`) to enable specific tools.
> See [docs/MCP_SETUP.md](docs/MCP_SETUP.md) for a full guide.

### 2. Install Ollama and Models

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull Qwen 2.5 14B (Required for Decision Discipline)
ollama pull qwen2.5:14b-instruct

# Pull LLaVA 7B (Required for Image Understanding — Phase 5.0)
ollama pull llava:7b

# Pull Nomic embedding model (Required for Semantic Memory)
ollama pull nomic-embed-text
```

### 3. Start Backend & Database

```bash
# Start PostgreSQL & Redis
docker-compose up -d postgres redis

# Install Python dependencies
poetry install

# Apply Database Migrations (First Run)
poetry run alembic upgrade head

# Start the backend server
poetry run uvicorn chatbot_ai_system.server.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start Frontend

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Grafana**: http://localhost:3001 (User: `admin`, Pass: `admin`)
- **Prometheus**: http://localhost:9090

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client Layer"]
        Browser["Browser"]
        UI["Next.js Frontend<br/>localhost:3000"]
        Mic["🎤 Microphone"]
    end
    
    subgraph API["⚡ API Layer"]
        FastAPI["FastAPI Server<br/>localhost:8000"]
        REST["/api/chat<br/>REST Endpoint"]
        WS["/api/chat/stream<br/>WebSocket"]
        Upload["/api/upload<br/>Media Upload"]
        VoiceWS["/api/voice/stream<br/>Voice WebSocket"]
        Health["/health"]
    end
    
    subgraph Core["🧠 Core Layer"]
        Orchestrator["Chat Orchestrator<br/>(9-Phase Pipeline)"]
        Provider["LLM Provider"]
        Registry["Tool Registry"]
        MCPClient["MCP Client Layer"]
        MediaPipe["Media Pipeline"]
    end

    subgraph Multimodal["🖼️ Multimodal Layer"]
        ImgProc["Image Processor<br/>(Pillow)"]
        STT["STT Engine<br/>(Whisper)"]
        TTS["TTS Engine<br/>(say/piper/espeak)"]
        VidProc["Video Processor<br/>(OpenCV)"]
    end

    subgraph Data["💾 Data Layer (Hybrid Memory)"]
        DB[(PostgreSQL\nDatabase)]
        Vector["pgvector\n(Cold Memory)"]
        Summary["Summarization\n(Warm Memory)"]
        Window["Sliding Window\n(Hot Memory)"]
        MediaDB["Media Attachments\nTable"]
    end
    
    subgraph Tools["🛠️ Tool Layer (MCP)"]
        FS["Filesystem"]
        Git["Git & GitHub"]
        Web["Brave Search & Fetch"]
        Brain["Sequential Thinking\n& SQLite"]
        Time["Time & Memory"]
    end

    subgraph Cache["⚡ Cache Layer"]
        Redis[(Redis\nCache)]
    end
    
    subgraph LLM["🤖 LLM Layer"]
        Ollama["Ollama Server<br/>localhost:11434"]
        TextModel["qwen2.5:14b<br/>Text Model"]
        VisionModel["llava:7b<br/>Vision Model"]
        Embed["nomic-embed-text<br/>Embedding Model"]
    end
    
    Browser --> UI
    Mic --> UI
    UI -->|HTTP/REST| REST
    UI -.->|WebSocket| WS
    UI -->|File Upload| Upload
    UI -.->|Voice| VoiceWS
    REST --> Orchestrator
    WS --> Orchestrator
    Upload --> MediaPipe
    VoiceWS --> STT & TTS
    MediaPipe --> ImgProc & STT & VidProc
    Orchestrator --> Provider
    Orchestrator --> Registry
    Orchestrator --> Redis
    Provider --> Ollama
    Ollama --> TextModel & VisionModel & Embed
    Redis --> DB & Vector & Summary & Window
    Registry --> MCPClient --> Tools
    MediaPipe --> MediaDB
```

### Supported MCP Servers

The system supports a wide range of MCP servers, dynamically loaded based on your `.env` configuration:

- **Core**: Filesystem, Time, Memory (Knowledge Graph), PostgreSQL
- **Researcher**: Brave Search, Puppeteer, Fetch (HTTP)
- **Developer**: Git, GitHub, Docker, E2B Interpreter
- **Brain**: Sequential Thinking, SQLite
- **Connector**: Slack, Google Maps, Sentry

See `src/chatbot_ai_system/config/mcp_server_config.py` for dynamic loading logic.

---

## ⚡ Adaptive Execution Flow (Phase 5.5)

The system employs a smart routing mechanism to optimize latency and performance based on query complexity.

```mermaid
flowchart TD
    User["User Query"] --> Classify{Intent Classifier}
    
    Classify -->|Simple Info| FastPath["🚀 FAST PATH<br/>(Direct Response)"]
    Classify -->|Simple Tool| MedPath["🛠️ TOOL PATH<br/>(One-shot Execution)"]
    Classify -->|Complex/Reasoning| SlowPath["🧠 AGENTIC PATH<br/>(Plan + ReAct Loop)"]
    
    FastPath --> LLM[LLM Response]
    MedPath --> Registry[Tool Registry] --> LLM
    
    SlowPath --> Planner[Sequential Thinking]
    Planner --> ReAct[ReAct Loop]
    ReAct --> Registry
    ReAct --> ReAct
    ReAct --> LLM
```

| Path | Complexity | Description | Typical Latency |
| :--- | :--- | :--- | :--- |
| **Fast Path** | `SIMPLE` | Direct LLM response for greetings, facts, and definitions. Tools are explicitly disabled to save tokens and time. | **~5-8s** |
| **Tool Path** | `SIMPLE` | Single-step tool usage for straightforward tasks (e.g., "List files", "Read specific file"). Uses broad keyword matching. | **~20-40s** |
| **Agentic Path** | `COMPLEX` | Full reasoning loop for multi-step tasks (e.g., "Analyze codebase", "Compare files"). Uses the Sequential Thinking planner. | **60s+** |

---

## 🖼️ Multimodal Capabilities (Phase 5.0)

The chatbot accepts image, audio, and video input and can hold real-time voice conversations.

### Image Understanding

Upload an image via `POST /api/upload` or attach it to a chat message. The orchestrator auto-detects image attachments and switches to the **llava:7b** vision model:

```bash
# Upload and analyze an image
curl -F "file=@photo.png" http://localhost:8000/api/upload
```

### Voice Conversation

Connect via WebSocket for full-duplex voice:

| Direction | Format | Content |
|-----------|--------|---------|
| Client → Server | Binary | 16kHz 16-bit PCM mono audio |
| Client → Server | JSON | `{"type": "end_turn"}` |
| Server → Client | JSON | Transcription, response text |
| Server → Client | Binary | WAV audio response |

### Audio & Video Processing

- **Audio**: Converted to 16kHz mono WAV, transcribed via Whisper STT, transcription injected into chat context.
- **Video**: Keyframes extracted at 5-second intervals, audio track transcribed.

See [docs/phase_5.0.md](docs/phase_5.0.md) for full architecture and protocol details.

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/chat` | POST | Send a chat message (REST) |
| `/api/chat/stream` | WebSocket | Stream chat responses |
| `/api/upload` | POST | Upload media (image/audio/video) |
| `/api/voice/config` | GET | Voice capability info |
| `/api/voice/stream` | WebSocket | Real-time voice conversation |
| `/docs` | GET | Swagger UI |
| `/metrics` | GET | Prometheus metrics |

---

## ⚙️ Configuration

Key environment variables (`.env`):

```env
# LLM Provider
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b-instruct

# Database & Cache
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
POSTGRES_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/0

# MCP Capabilities (Add keys to enable)
BRAVE_API_KEY=...
GITHUB_TOKEN=...
SLACK_BOT_TOKEN=...
GOOGLE_MAPS_API_KEY=...
E2B_API_KEY=...
SENTRY_AUTH_TOKEN=...

# Phase 5.0: Multimodal & Voice
MEDIA_STORAGE_PATH=media
MAX_UPLOAD_SIZE_MB=50
VISION_MODEL=llava:7b
STT_MODEL=base
STT_DEVICE=cpu
TTS_VOICE=en_US-lessac-medium
```

---

## 🧪 Testing

```bash
# Verify MCP integration and tool execution
python scripts/test_mcp_capabilities.py

# Verify multimodal pipeline (image, audio, TTS, vision model)
python scripts/test_multimodal.py

# Verify performance and query routing (Phase 5.5)
python scripts/verify_phase_5_5_real.py
```

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** — Modern Python web framework with async support
- **SQLAlchemy** — Async ORM with PostgreSQL
- **Redis** — High-performance caching layer (context cache, session)
- **Model Context Protocol (MCP)** — Standard for connecting LLMs to external tools
- **Ollama** — Local LLM inference (text, vision, embedding)
- **Pydantic** — Data validation and settings management
- **WebSockets** — Real-time streaming for chat and voice

### Multimodal & Voice
- **faster-whisper** — Speech-to-text (Whisper reimplementation, int8 quantized)
- **Pillow** — Image processing (resize, format conversion, base64 encoding)
- **pydub + FFmpeg** — Audio format conversion (any format → 16kHz WAV)
- **OpenCV** — Video keyframe extraction
- **piper-tts / macOS say / espeak** — Text-to-speech (auto-detected backend)
- **llava:7b** — Vision model for image understanding

### Data & Memory
- **PostgreSQL** — Persistent storage with pgvector for semantic search
- **pgvector** — Vector embeddings for cold memory / RAG
- **Alembic** — Database migrations

### DevOps & Observability
- **Docker Compose** — Orchestration (PostgreSQL, Redis, Prometheus, Grafana)
- **Prometheus** — Metrics collection & alerting
- **Grafana** — Visualization & dashboards (port 3001)
- **Node Exporter** — System-level metrics (CPU, memory)

### Frontend
- **Next.js 14** — React framework
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling

---

## 📂 Project Structure

```
chatbot-ai-systems-production/
├── src/chatbot_ai_system/
│   ├── config/              # Settings, MCP server config
│   ├── database/            # SQLAlchemy models, session, Redis
│   ├── models/              # Pydantic schemas (ChatMessage, MediaAttachment)
│   ├── observability/       # Prometheus metrics
│   ├── orchestrator.py      # 9-phase chat orchestrator
│   ├── providers/           # LLM providers (Ollama, OpenAI, Anthropic)
│   ├── repositories/        # DB repositories (conversation, memory)
│   ├── server/              # FastAPI routes, multimodal routes
│   ├── services/            # Media pipeline, STT, TTS, embedding
│   └── tools/               # MCP tool registry and client
├── frontend/                # Next.js frontend
├── alembic/                 # Database migrations
├── docker/                  # Prometheus, Grafana config
├── scripts/                 # Test and utility scripts
└── docs/                    # Phase documentation
```

---

## 📈 Roadmap

- [x] **Phase 1.0**: Core Chatbot with Open Source LLM
- [x] **Phase 1.1**: MCP Tool Support & Streaming Execution — [Docs](docs/phase_1.1.md)
- [x] **Phase 1.2**: Decision Discipline (Smart Routing & Planning) — [Docs](docs/phase_1.2.md)
- [x] **Phase 1.3**: Chat Orchestrator (9-Phase Architecture) — [Docs](docs/phase_1.3.md)
- [x] **Phase 2.0**: Data Persistence & User Memory (PostgreSQL) — [Docs](docs/phase_2.0.md)
- [x] **Phase 2.2**: Embedding & Semantic Search — [Docs](docs/phase_2.2.md)
- [x] **Phase 2.5**: Observability & Schema Scaling — [Docs](docs/phase_2.5.md)
- [x] **Phase 2.6**: Sliding Window Context (Hot Memory)
- [x] **Phase 2.7**: Conversation Summarization (Warm Memory)
- [x] **Phase 3.0**: Redis Caching & Performance Optimization — [Docs](docs/phase_3.0.md)
- [x] **Phase 4.0**: Observability (Prometheus & Grafana) — [Docs](docs/phase_4.0.md)
- [x] **Phase 4.1**: Observability Hardening & Validation — [Docs](docs/phase_4.1.md)
- [x] **Phase 5.0**: Multimodal Input & Voice Conversation — [Docs](docs/phase_5.0.md)
- [x] **Phase 5.5**: Performance Optimization & Reliability — [Docs](docs/phase_5.5.md)
- [x] **Phase 6.0**: Multi-Provider Orchestration (OpenAI, Anthropic, Gemini) — [Docs](docs/phase_6.0.md)
- [x] **Phase 6.5**: Free Tool Integration (Web Search & Coding) — [Docs](docs/phase_6.5.md)
- [ ] **Phase 7.0**: Authentication & Multi-Tenancy

---

## 📝 License

MIT License
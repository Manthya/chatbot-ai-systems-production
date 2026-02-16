# Chatbot AI System

A production-grade, multi-tenant AI chatbot platform with multi-provider LLM support, WebSocket streaming, and modern UI.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** with Poetry
- **Node.js 20+** with npm
- **Docker & Docker Compose** (for PostgreSQL & Redis)
- **Ollama** (for local LLM) - [Install Ollama](https://ollama.ai/)

### 1. Setup Environment

```bash
# Clone and navigate to project
cd /Users/mk/Documents/chatbot-ai-systems-production

# Copy environment files
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

> [!IMPORTANT]
> **MCP Configuration**: The `.env` file now includes sections for MCP server API keys.
> You must populate these keys (e.g., `BRAVE_API_KEY`, `GITHUB_TOKEN`) to enable specific tools.
> See [docs/MCP_SETUP.md](docs/MCP_SETUP.md) for a full guide.

### 2. Install Ollama and Tool Model

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull Qwen 2.5 14B (Required for Decision Discipline)
ollama pull qwen2.5:14b-instruct
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

## 🏗️ System Design

### High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["🖥️ Client Layer"]
        Browser["Browser"]
        UI["Next.js Frontend<br/>localhost:3000"]
    end
    
    subgraph API["⚡ API Layer"]
        FastAPI["FastAPI Server<br/>localhost:8000"]
        REST["/api/chat<br/>REST Endpoint"]
        WS["/api/chat/stream<br/>WebSocket"]
        Health["/health"]
    end
    
    subgraph Core["🧠 Core Layer"]
        Router["Multi-Turn Request Router"]
        Provider["LLM Provider (Ollama)"]
        Registry["Tool Registry"]
        MCPClient["MCP Client Layer"]
        Orchestrator["Chat Orchestrator"]
    end

    subgraph Data["💾 Data Layer (Hybrid Memory)"]
        DB[(PostgreSQL\nDatabase)]
        Vector["pgvector\n(Cold Memory)"]
        Summary["Summarization\n(Warm Memory)"]
        Window["Sliding Window\n(Hot Memory)"]
    end
    
    subgraph Tools["🛠️ Tool Layer (MCP)"]
        FS["Filesystem"]
        Git["Git & GitHub"]
        Web["Brave Search & Fetch"]
        Brain["Sequential Thinking\n& SQLite"]
        Time["Time & Memory"]
    end

    subgraph Cache["⚡ Cache Layer (Fast Memory)"]
        Redis[(Redis\nCache)]
    end
    
    subgraph LLM["🤖 LLM Layer"]
        Ollama["Ollama Server<br/>localhost:11434"]
        Inference["qwen2.5:14b<br/>Inference Model"]
        Embed["nomic-embed-text<br/>Embedding Model"]
    end
    
    Browser --> UI
    UI -->|HTTP/REST| REST
    UI -.->|WebSocket| WS
    REST --> Router
    WS --> Router
    Router --> Orchestrator
    Orchestrator --> Provider
    Orchestrator --> Registry
    Orchestrator --> Redis
    Redis --> DB
    Redis --> Vector
    Redis --> Summary
    Redis --> Window
    Provider --> Ollama
    Ollama --> Inference
    Ollama --> Embed
    Registry --> MCPClient
    MCPClient --> Redis
    MCPClient --> Tools
```

### Supported MCP Servers

The system now supports a wide range of MCP servers, dynamically loaded based on your `.env` configuration:

- **Core**: Filesystem, Time, Memory (Knowledge Graph), PostgreSQL
- **Researcher**: Brave Search, Puppeteer, Fetch (HTTP)
- **Developer**: Git, GitHub, Docker, E2B Interpreter
- **Brain**: Sequential Thinking, SQLite
- **Connector**: Slack, Google Maps, Sentry

See `src/chatbot_ai_system/config/mcp_server_config.py` for dynamic loading logic.

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
```

## 🧪 Testing

Run duplicate verification of MCP capabilities:

```bash
# Verify MCP integration and tool execution
python scripts/test_mcp_capabilities.py
```

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Redis** - High-performance caching layer
- **Model Context Protocol (MCP)** - Standard for connecting LLMs to tools
- **Ollama** - Local LLM inference
- **Pydantic** - Data validation
- **WebSockets** - Real-time streaming

### DevOps & Observability
- **Docker Compose** - Orchestration
- **Prometheus** - Metrics Collection & Alerting
- **Grafana** - Visualization & Dashboards
- **Node Exporter** - System Metrics
- **PostgreSQL** - Vector Database (pgvector)

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling

---

## 📈 Roadmap

- [x] **Phase 1**: Core Chatbot with Open Source LLM
- [x] **Phase 1.1**: MCP Tool Support & Streaming Execution
- [x] **Phase 1.2**: Decision Discipline (Smart Routing & Planning)
- [x] **Phase 1.3**: Chat Orchestrator (9-Phase Architecture)
- [x] **Phase 2**: Data Persistence & User Memory (PostgreSQL)
- [x] **Phase 2.5**: Observability & Schema Scaling
- [x] **Phase 2.6**: Sliding Window Context (Hot Memory)
- [x] **Phase 2.7**: Conversation Summarization (Warm Memory)
- [x] **Phase 3.0**: Redis Caching & Performance Optimization
- [x] **Phase 4.0**: Observability (Prometheus & Grafana) - [Docs](docs/phase_4.0.md)
- [x] **Phase 4.1**: Observability Hardening & Validation - [Docs](docs/phase_4.1.md)
- [ ] **Phase 5.0**: Vector Search (Cold Memory / RAG)
- [ ] **Phase 6.0**: Multi-Provider Orchestration
- [ ] **Phase 7.0**: Authentication & Multi-Tenancy

---

## 📝 License

MIT License
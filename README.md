# JobFalcon

An Agentic AI-Powered Career Opportunity Recommendation System that builds evidence-backed skill profiles, analyzes labor-market dynamics, and discovers, evaluates, and ranks career opportunities based on deterministic eligibility constraints, multidimensional skill fit, and growth potential.

---

## Architecture Specification & Governance References

- **Architecture Specification**: Complete 5-part architecture specification located in [`docs/`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs) (Sections 1–5).
- **Engineering Guidelines & Invariants**: Repository guidelines, determinism requirements, and security rules in [`AGENTS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/AGENTS.md).
- **Development Skill System**: 12 modular Antigravity development skills cataloged in [`docs/SKILLS_INDEX.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/SKILLS_INDEX.md).
- **Architectural Decisions & Calibration Logs**: Open decisions and provisional formulas recorded in [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md).

---

## System Architecture

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                   Next.js Frontend Career Workspace                      │
│                  http://localhost:3000 (React 19 • App Router)           │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ HTTP REST / SSE Telemetry Stream
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend Gateway                          │
│                   http://localhost:8000 (Python 3.12+)                   │
├──────────────────────────────────────────────────────────────────────────┤
│ • Modular Application Services: Candidate Profile, Application Tracking  │
│ • LangGraph StateGraph Multi-Agent Orchestrator (Cyclic Supervisor-Worker)│
│ • 100% Pure Deterministic Eligibility Gate (Zero Probabilistic Bypass)   │
│ • Mathematical 6-Dimensional MCDA Scoring & MinHash LSH Deduplication    │
└──────────────┬───────────────────────────────┬───────────────────────────┘
               │                               │
       ┌───────▼────────┐             ┌────────▼────────┐
       │   AI Gateway   │             │  External Tools │
       │ (LiteLLM/Ollama│             │ & Search Feeds  │
       │    / Mock)     │             └────────┬────────┘
       └────────────────┘                      │
                     ┌─────────────────────────┴──────────────────────────┐
                     │                                                    │
             ┌───────▼────────┐                                   ┌───────▼────────┐
             │ SearXNG Search │                                   │   JobSpy MCP   │
             │ (Meta-Search)  │                                   │(Stdio JSON-RPC)│
             └────────────────┘                                   └────────────────┘
```

### Core Architectural Invariants

1. **Modular Monolith**: Clean separation between standard application services (auth, profiles, tracking) and AI orchestration workflows. Services remain fully functional even when AI models are unavailable.
2. **Deterministic Primacy Over Probabilistic Models**:
   - Hard eligibility constraints (degree, enrollment status, work authorization, location, active deadlines) execute exclusively in pure Python/SQL deterministic code. Language models are strictly forbidden from evaluating or overriding eligibility.
   - Mathematical 6-dimensional MCDA ranking (Skill Match, Growth Potential, Compensation Competitiveness, Role Quality, Commute & Work-Style Fit, Epistemic Uncertainty Discount) is strictly calculated via deterministic arithmetic. LLMs never invent or alter rank scores.
3. **Evidence-Backed Career Intelligence**: Candidate skills and qualifications are bound to verifiable `EvidenceRecord` provenance with explicit epistemic confidence and taxonomy grounding (ESCO v1.2.1 and O*NET v2.0).
4. **Resilient Multi-Agent Orchestration**: LangGraph cyclic `StateGraph` coordinating specialist nodes with adaptive iteration budgets, zero-result recovery cascades, and strict execution guardrails to prevent infinite loops.
5. **Prompt Injection & Data Sanitization**: Untrusted external inputs (uploaded resumes, external job postings, search snippets) are normalized via Unicode NFKC, stripped of control characters, and enclosed in structured `tool_result` wrappers with untrusted trust headers.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend UI** | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons |
| **Backend API** | Python 3.12+, FastAPI, Uvicorn, Pydantic v2, `sse-starlette`, `python-multipart` |
| **Agent Orchestration** | LangGraph (StateGraph, checkpointing, supervised worker fan-out) |
| **Document Extraction** | `pypdf`, `python-docx`, Markdown parsers with fallback resilience |
| **Deduplication & Search** | MinHash LSH (128 permutations), SearXNG meta-search, DuckDuckGo Lite |
| **Tool Protocol (MCP)** | Model Context Protocol (`mcp>=2.3.0`) via JSON-RPC 2.0 stdio pipes (`mcp-jobspy`) |
| **Storage (Zero-Setup)** | SQLite (`sqlite:///./jobfalcon_dev.db`) file persistence |
| **Storage (Production)** | PostgreSQL 16+ with `pgvector` HNSW indexing, Redis Stack (RedisVL semantic cache), MinIO S3 |
| **Containerization** | Docker, multi-stage Alpine/Slim Dockerfiles, Docker Compose |

---

## Required Services & System Dependencies

### Host Prerequisites
- **Python**: Version 3.12+ (Python 3.14 on macOS supported)
- **Node.js**: Version 20.x or 22.x LTS with `npm`
- **Package Manager**: `uv` (strongly recommended for Python) or standard `pip`
- **Docker & Docker Compose**: Required for containerized execution and local SearXNG search engine

### External Discovery Services (Configurable)
- **SearXNG**: Self-hosted meta-search engine running on port 8080 (included in Docker Compose)
- **JobSpy MCP Server**: Python MCP CLI package (`mcp-jobspy`) for scraping public requisitions (Indeed, LinkedIn, Glassdoor, ZipRecruiter) over standard JSON-RPC 2.0 stdio
- **LLM Gateway / Local Runner**:
  - **Mock Provider** (Default): Zero API keys required; offline deterministic mock responses for testing and rapid development.
  - **Ollama**: Local open-weights model execution (e.g. `qwen2.5:14b-instruct`, `llama3.1:8b-instruct`) at `http://localhost:11434/v1`.
  - **LiteLLM / OpenAI**: Hosted or self-hosted API gateways.

---

## Execution Modes: Local Workstation vs. Hosted

JobFalcon introduces distinct execution profiles via the `DISCOVERY_EXECUTION_MODE` environment variable:

| Configuration Parameter | `local` Mode (Default) | `hosted` Mode | Purpose |
| :--- | :--- | :--- | :--- |
| `DISCOVERY_EXECUTION_MODE` | `local` | `hosted` | Selects behavioral profile |
| `DISCOVERY_MAX_ITERATIONS` | **6** iterations | **3** iterations | Bounded loops for search-evaluate-adapt cycles |
| `DISCOVERY_MAX_TOOL_CALLS` | **30** calls (or 0 for unlimited) | **10** calls | Budget ceiling across all external search connectors |
| `DISCOVERY_MAX_CALLS_PER_CONNECTOR` | **15** calls | **5** calls | Prevents a single search connector from monopolizing budget |
| `DISCOVERY_MAX_CONCURRENT_CONNECTOR_CALLS` | **3** parallel calls | **2** parallel calls | Concurrency throttle for external scraping and queries |
| `DISCOVERY_PER_TOOL_TIMEOUT_SECONDS` | **20.0s** | **8.0s** | Timeout per individual connector invocation |
| `DISCOVERY_WORKFLOW_TIMEOUT_SECONDS` | **120.0s** | **30.0s** | Total workflow timeout before returning partial results |
| **Zero-Result Recovery** | **Adaptive Query Broadening** | Single retry fallback | Automatically widens query criteria when initial searches yield 0 results |

---

## Environment Configuration

Both backend and frontend utilize decoupled environment configuration templates.

### Backend Configuration (`backend/.env`)

Copy `backend/.env.example` to `backend/.env`:
```bash
cp backend/.env.example backend/.env
```

Key environment variables:

```bash
# Core Runtime
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Persistence (SQLite default for zero-setup; PostgreSQL pgvector for full production)
DATABASE_URL=sqlite:///./jobfalcon_dev.db

# LLM Gateway (options: 'mock', 'litellm', 'ollama', 'openai')
LLM_PROVIDER=mock
LLM_BASE_URL=http://localhost:4000/v1
LLM_MODEL=qwen2.5:14b-instruct

# Web Search Provider (options: 'searxng', 'duckduckgo', 'mock')
WEB_SEARCH_PROVIDER=searxng
SEARXNG_BASE_URL=http://localhost:8080

# JobSpy MCP Tool Integration
MCP_JOBSPY_COMMAND=mcp-jobspy
MCP_JOBSPY_TIMEOUT_SECONDS=12.0
MCP_JOBSPY_RESULTS_WANTED=5
MCP_JOBSPY_FETCH_DETAILS=true
MCP_JOBSPY_COUNTRY=usa

# Discovery Execution Budgets (Milestone 15)
DISCOVERY_EXECUTION_MODE=local
DISCOVERY_MAX_ITERATIONS=6
DISCOVERY_MAX_TOOL_CALLS=30
DISCOVERY_PER_TOOL_TIMEOUT_SECONDS=20.0
DISCOVERY_WORKFLOW_TIMEOUT_SECONDS=120.0
```

### Frontend Configuration (`frontend/.env.local`)

Copy `frontend/.env.example` to `frontend/.env.local`:
```bash
cp frontend/.env.example frontend/.env.local
```

```bash
# Backend FastAPI API Base URL (must be browser-accessible)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Local Development Startup (Without Docker)

### 1. Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a Python virtual environment
uv venv .venv
source .venv/bin/activate

# 3. Install backend dependencies directly from pyproject.toml
uv pip install -r pyproject.toml

# 4. Copy environment configuration
cp .env.example .env

# 5. Launch FastAPI development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify backend health in another terminal:
```bash
curl -s http://localhost:8000/api/v1/healthz
# Response: {"status":"ok","version":"0.1.0","environment":"development",...}
```

### 2. Frontend Setup

```bash
# 1. In a separate terminal, navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Copy environment configuration
cp .env.example .env.local

# 4. Run Next.js development server
npm run dev
```

Open `http://localhost:3000` in your browser. The application dashboard will load and automatically connect to the backend API.

---

## Docker-Based Startup (Containerized)

JobFalcon provides a multi-container Docker Compose setup supporting both zero-dependency lightweight mode and full infrastructure mode.

### 1. Standard Mode (FastAPI Backend + Next.js Frontend + SearXNG Search)

This mode runs the entire core application with zero external dependencies (uses SQLite database and local SearXNG meta-search):

```bash
# Build images and start all core containers
docker compose up --build
```

Container endpoints:
- **Frontend Workspace**: `http://localhost:3000`
- **Backend API & Swagger Docs**: `http://localhost:8000` (docs at `http://localhost:8000/docs`)
- **SearXNG Meta-Search**: `http://localhost:8080`

To run in the background (detached mode):
```bash
docker compose up -d --build
```

To view logs:
```bash
docker compose logs -f
```

To stop containers:
```bash
docker compose down
```

### 2. Full Infrastructure Mode (PostgreSQL pgvector + Redis Stack + MinIO)

When evaluating vector embeddings, RedisVL semantic caching, or S3 resume storage:

```bash
# Start all core services plus PostgreSQL pgvector, Redis Stack, and MinIO
docker compose --profile full up --build
```

Additional service ports:
- **PostgreSQL 16 (pgvector)**: `localhost:5432` (`jobfalcon:jobfalcon_user:devpassword123`)
- **Redis Stack**: `localhost:6379`
- **MinIO Console**: `http://localhost:9001` (`minioadmin:minioadmin`) / S3 API at `localhost:9000`

---

## Available Discovery Sources & Configuration

JobFalcon connects multiple discovery channels into a unified candidate exploration workflow:

### 1. Web Search Connector (SearXNG / DuckDuckGo)
- **SearXNG (Recommended)**: Privacy-preserving meta-search aggregator querying Google, Bing, DuckDuckGo, and specialized engines without rate limiting.
- **DuckDuckGo Lite**: Fallback web search requiring zero configuration and zero API keys.
- **Sanitization & Provenance**: Search snippets are sanitized via Unicode NFKC normalization, stripped of script tags, and bounded in untrusted data blocks. Direct requisition links are extracted and preserved.

### 2. Model Context Protocol (MCP) JobSpy Connector
- **JobSpy MCP (`mcp-jobspy`)**: Scrapes and standardizes job postings from LinkedIn, Indeed, Glassdoor, and ZipRecruiter over standard JSON-RPC 2.0 stdio pipes.
- **Detail Enrichment**: Automatically retrieves complete job descriptions and direct employer ATS application links (`job_url_direct`).
- **Country Domain Routing**: Automatically resolves ISO country codes (e.g. US, IN, UK, CA, DE, FR, AU, SG) to target job boards.

### 3. Adaptive Discovery & Zero-Result Recovery
- **Multi-Iteration Orchestration**: If initial search queries yield zero opportunities, the LangGraph coordinator enters an adaptive relaxation loop.
- **Query Relaxation**: Progressively broadens title filters, removes overly specific keywords, and expands geographical boundaries.
- **Budget Protection**: Enforces explicit per-run limits (`DISCOVERY_MAX_TOOL_CALLS` and `DISCOVERY_MAX_ITERATIONS`) to prevent runaways while providing sufficient discovery depth.
- **Deduplication**: Cross-connector deduplication uses 128-permutation MinHash LSH to identify near-identical postings across different job boards.

---

## Testing & Verification Commands

JobFalcon maintains rigorous automated testing across all architectural layers.

### Backend Verification

```bash
# Activate backend virtualenv
source backend/.venv/bin/activate

# 1. Run full unit and integration test suite (226+ tests)
PYTHONPATH=backend pytest backend/tests

# 2. Run specific deterministic eligibility engine tests
PYTHONPATH=backend pytest backend/tests/test_eligibility_engine.py

# 3. Run adaptive discovery and budget tests
PYTHONPATH=backend pytest backend/tests/test_adaptive_discovery_budget.py

# 4. Run LangGraph orchestration workflow tests
PYTHONPATH=backend pytest backend/tests/test_langgraph_orchestration.py

# 5. Run Python code linting and style check
ruff check backend/
ruff format --check backend/
```

### Frontend Verification

```bash
cd frontend

# 1. Run TypeScript static type check
npx tsc --noEmit

# 2. Run Next.js / ESLint static analysis
npm run lint

# 3. Verify production build compilation
npm run build
```

### Docker Verification

```bash
# Validate docker-compose.yml configuration syntax
docker compose config
```

---

## Repository Structure

```text
JobFalcon/
├── .agents/skills/          # 12 Antigravity development skills & workflows
├── backend/                 # FastAPI modular monolith application
│   ├── app/
│   │   ├── api/v1/          # Modular API routers (health, candidate, discovery, etc.)
│   │   ├── core/            # Configuration (Settings), security, and logging
│   │   ├── models/          # Relational and vector database models
│   │   ├── schemas/         # Strict Pydantic v2 domain schemas & contracts
│   │   ├── services/        # Business logic services (eligibility, deduplication, etc.)
│   │   └── workflows/       # LangGraph StateGraph agents & discovery orchestrator
│   ├── tests/               # Pytest suite (eligibility, scoring, orchestration, discovery)
│   ├── Dockerfile           # Multi-stage production container build (uv + Python 3.12)
│   ├── .dockerignore        # Excludes virtual environments, caches, and database files
│   ├── .env.example         # Complete environment variable template
│   └── pyproject.toml       # Python packaging and dependency specifications
├── frontend/                # Next.js 15 App Router Career Workspace UI
│   ├── src/
│   │   ├── app/             # Next.js App Router pages and layouts
│   │   ├── components/      # UI components (profile, discovery, recommendations, etc.)
│   │   └── lib/             # Typed API clients and SSE streaming handlers
│   ├── Dockerfile           # Multi-stage production container build (Node.js 20 Alpine)
│   ├── .dockerignore        # Excludes node_modules, build artifacts, and local environments
│   ├── .env.example         # Frontend environment variable template
│   └── package.json         # Frontend dependencies and build scripts
├── docs/                    # Architecture documentation & decision records
├── docker-compose.yml       # Multi-container orchestration (Backend, Frontend, SearXNG, etc.)
├── .dockerignore            # Root-level docker build ignore specification
├── AGENTS.md                # Agent instructions, engineering guidelines & invariants
└── README.md                # Root project documentation (this document)
```

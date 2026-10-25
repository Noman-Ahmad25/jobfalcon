# JobFalcon

An Agentic AI-Powered Career Opportunity Recommendation System that builds evidence-backed skill profiles, analyzes labor-market trends, and discovers, evaluates, and ranks career opportunities based on deterministic eligibility, skill fit, and growth potential.

## Documentation & Architecture References

- **Architecture Specification**: Complete 5-part architecture specification located in [`docs/`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs) (Sections 1–5).
- **Engineering Guidelines & Rules**: Agent instructions, coding standards, and security requirements in [`AGENTS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/AGENTS.md).
- **Development Skill System**: 12 modular Antigravity development skills cataloged in [`docs/SKILLS_INDEX.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/SKILLS_INDEX.md).
- **Architectural Decisions & Calibration Items**: Open decisions and provisional formulas recorded in [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md).

## System Architecture

```text
┌───────────────────────────────┐
│       Next.js Frontend        │ (App Router • React 19 • Tailwind CSS)
│     http://localhost:3000     │
└───────────────┬───────────────┘
                │ HTTP Requests / Health Probes
                ▼
┌───────────────────────────────┐
│        FastAPI Backend        │ (Modular Monolith • Python 3.12+)
│     http://localhost:8000     │
├───────────────────────────────┤
│ • /healthz & /readyz          │ Liveness and readiness probes
│ • /api/v1/healthz             │ Versioned API health diagnostic
│ • /api/v1/...                 │ Future modular domain routers
└───────────────────────────────┘
```

1. **Modular Monolith**: FastAPI backend with decoupled application services and future LangGraph multi-agent orchestration.
2. **Deterministic Primacy**: 100% deterministic rule enforcement for hard eligibility constraints and mathematical 6-dimensional MCDA ranking.
3. **Evidence-Backed Career Intelligence**: Multi-source skill extraction anchored to ESCO v1.2.1 and O*NET v2.0 taxonomies with verifiability weighting and epistemic confidence.
4. **Hierarchical Multi-Agent Supervisor**: Orchestrator coordinating specialist agents (Profile, Market Intelligence, Opportunity Discovery, Ranking, and Explanation) with bounded evaluator-optimizer loops and Map-Reduce parallelism.
5. **Robust Local & Cloud Hybrid AI**: LiteLLM AI Gateway with Redis-backed circuit breakers and fallback cascade to local Ollama open-weights models.

---

## Local Development Quickstart

### Prerequisites
- Python 3.12+ (or Homebrew Python 3.14)
- Node.js v20+ (v24 LTS recommended) and npm
- `uv` (recommended for ultra-fast Python package management) or `pip3`

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment and activate
uv venv .venv
source .venv/bin/activate

# Copy example environment configuration
cp .env.example .env

# Install dependencies
uv pip install fastapi uvicorn pydantic pydantic-settings pytest httpx

# Run automated tests
.venv/bin/pytest -v

# Start FastAPI development server
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The backend API will be available at `http://localhost:8000`. Test the health check endpoint:
```bash
curl http://localhost:8000/healthz
```

### 2. Real Web Search Configuration (Milestone 13)

JobFalcon features genuine, multi-provider web search integration for external opportunity discovery without mandating paid third-party API subscriptions:

```bash
# Option A: Self-Hosted SearXNG (Default, Privacy-Preserving Meta-Search)
docker run -d --name searxng -p 8080:8080 -e "SEARXNG_BASE_URL=http://localhost:8080" searxng/searxng

# Configure in backend/.env:
WEB_SEARCH_PROVIDER=searxng
SEARXNG_BASE_URL=http://localhost:8080
WEB_SEARCH_TIMEOUT_SECONDS=6.0
WEB_SEARCH_MAX_RESULTS=10

# Option B: Zero-Config Public Web Search (Zero API Key, Zero Container Setup)
# Uses DuckDuckGo Lite endpoint with automatic URL decoding and anti-noise classification
WEB_SEARCH_PROVIDER=duckduckgo

# Option C: Custom REST JSON Search Gateway
WEB_SEARCH_PROVIDER=custom_json
CUSTOM_SEARCH_ENDPOINT_URL=https://search.mycompany.internal/api/search
WEB_SEARCH_API_KEY=optional_secret_token
```

**Security & Provenance Invariants**:
- All search result snippets are treated as **untrusted data**, sanitized against script injection and prompt injection attempts, and prepended with `[Search Index Result - Unverified Requisition]`.
- Direct original requisition URLs are strictly preserved.
- Unverified web search listings receive explicit confidence discounting (`trust_score=0.68–0.82`, `completeness_score=0.75`), and cannot alter deterministic eligibility or mathematical 6D ranking scores.
- When providers are unreachable or misconfigured, connectors honestly report `UNAVAILABLE` or `MISCONFIGURED` without hallucinating fake listings or claiming false `CONNECTED` states.

### 3. Frontend Setup

```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Copy example environment configuration
cp .env.example .env.local

# Install dependencies (if not already installed)
npm install

# Run linters and type check
npm run lint
npx tsc --noEmit

# Build production bundle
npm run build

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` in your browser. The initial dashboard will load and probe the live backend health endpoint.

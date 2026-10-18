# JobFalcon — Development Skill System Index

This document serves as the master catalog and invocation matrix for JobFalcon's development skills. The system is organized into a three-tier architecture ensuring non-duplicative, highly cohesive engineering workflows.

---

## 1. Skill System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer A: Project-Wide Engineering Rules (AGENTS.md)             │
│ Core invariants, deterministic primacy, truthfulness, security  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ Layer B: Specialized Reusable Skills (.agents/skills/)          │
│ 12 domain-specific skills with focused workflows and boundaries │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ Layer C: Environment & Diagnostic Skills                        │
│ modern-web-guidance, a11y-debugging, chrome-devtools, etc.     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Specialized Skill Catalog (Layer B)

All skills are located under `.agents/skills/<skill-name>/SKILL.md` (and aliased under `.agent/skills/`):

| Skill Name | Path | Primary Focus & Domain Boundary |
| :--- | :--- | :--- |
| **`jobfalcon-architecture`** | [`.agents/skills/jobfalcon-architecture/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/jobfalcon-architecture/SKILL.md) | High-level system topology, service boundaries, deterministic vs. probabilistic division, and unresolved decision tracking. |
| **`agentic-workflows`** | [`.agents/skills/agentic-workflows/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/agentic-workflows/SKILL.md) | LangGraph `StateGraph`, supervisor-worker subgraphs, pure reducers, `Send` API map-reduce, checkpointing, and loop prevention. |
| **`python-fastapi-engineering`** | [`.agents/skills/python-fastapi-engineering/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/python-fastapi-engineering/SKILL.md) | FastAPI modular monolith, routers, dependency injection, async connection pooling, Pydantic v2 schemas, and SSE streaming. |
| **`database-and-retrieval`** | [`.agents/skills/database-and-retrieval/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/database-and-retrieval/SKILL.md) | PostgreSQL 16 schema design, `pgvector` HNSW index configuration, Alembic migrations, MinHash LSH deduplication, and RedisVL caching. |
| **`frontend-design`** | [`.agents/skills/frontend-design/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/frontend-design/SKILL.md) | Precision career workspace UX, transparent 6D score visualization, verifiable evidence UI, and eliminating cliché AI design tropes. |
| **`frontend-engineering`** | [`.agents/skills/frontend-engineering/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/frontend-engineering/SKILL.md) | Next.js App Router, React, TypeScript, Tailwind CSS, SSE streaming telemetry consumers, and accessible components. |
| **`implementation-workflow`** | [`.agents/skills/implementation-workflow/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/implementation-workflow/SKILL.md) | Code change discipline: inspect-first, minimal surgical diffs, zero placeholders, linters/type checks, and truthful verification. |
| **`ai-security-review`** | [`.agents/skills/ai-security-review/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/ai-security-review/SKILL.md) | Indirect prompt injection defense, NFKC unicode normalization, untrusted data wrapping, tool least-privilege, and secret safety. |
| **`testing-and-evaluation`** | [`.agents/skills/testing-and-evaluation/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/testing-and-evaluation/SKILL.md) | Unit tests, 500-pair synthetic golden eligibility benchmark, RRF/MCDA mathematical verification, and mocked LangGraph tests. |
| **`observability-and-reliability`** | [`.agents/skills/observability-and-reliability/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/observability-and-reliability/SKILL.md) | OpenTelemetry tracing, `thread_id` correlation, LiteLLM circuit breakers, health probes, and separating user events from telemetry. |
| **`deployment-and-local-dev`** | [`.agents/skills/deployment-and-local-dev/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/deployment-and-local-dev/SKILL.md) | Docker Compose orchestration (PostgreSQL, pgvector, Redis Stack, MinIO, Ollama), environment profiles, and reproducible setups. |
| **`engineering-documentation`** | [`.agents/skills/engineering-documentation/SKILL.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/engineering-documentation/SKILL.md) | Architecture Decision Records (ADRs) in `docs/decisions/`, provisional calibration tracking in `docs/UNRESOLVED_DECISIONS.md`. |

---

## 3. Skill Invocation & Cooperation Matrix

Skills in JobFalcon are designed to work together without overlap. When undertaking a specific engineering task, combine the appropriate skills as outlined below:

| Development Task | Primary Skill | Supporting Skills |
| :--- | :--- | :--- |
| **New Agent Workflow / Subgraph** | `agentic-workflows` | `jobfalcon-architecture`, `python-fastapi-engineering`, `testing-and-evaluation` |
| **New Workspace Screen / UI Flow** | `frontend-design` | `frontend-engineering`, `implementation-workflow`, `modern-web-guidance` |
| **New API Route or Domain Service** | `python-fastapi-engineering` | `jobfalcon-architecture`, `ai-security-review`, `testing-and-evaluation` |
| **Database Schema or Vector Search** | `database-and-retrieval` | `jobfalcon-architecture`, `python-fastapi-engineering`, `testing-and-evaluation` |
| **Adversarial Input & Ingestion Defense** | `ai-security-review` | `python-fastapi-engineering`, `testing-and-evaluation` |
| **Docker Compose / Deployment Profiles** | `deployment-and-local-dev` | `jobfalcon-architecture`, `observability-and-reliability` |
| **Scoring Formula or Ranking Changes** | `jobfalcon-architecture` | `testing-and-evaluation`, `engineering-documentation` |
| **General Code Modification / Bugfix** | `implementation-workflow` | *Domain-specific skill for affected module* |

---

## 4. How Skill Invocation Works in Antigravity

1. **Discovery & Semantic Routing**: Antigravity indexes the YAML frontmatter (`name` and `description`) of each skill located in `.agents/skills/` at workspace startup.
2. **On-Demand Progressive Disclosure**: When a prompt matches a skill's capability, the agent loads that specific `SKILL.md` using `view_file` to review detailed procedures and constraints without overloading the global context window.
3. **Multi-Skill Synergy**: For composite tasks (e.g., implementing an SSE streaming endpoint), the agent consults `python-fastapi-engineering` for the backend router and `frontend-engineering` for the client-side consumer.

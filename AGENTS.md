# JobFalcon — Agent & Engineering Guidelines

This repository hosts **JobFalcon**, an Agentic AI-Powered Career Opportunity Recommendation System. All developers and AI coding agents operating on this codebase must strictly observe the instructions, rules, and architectural guidelines defined here.

---

## 1. Core Engineering Principles

1. **Inspect Before Modifying**: Never modify code, schemas, or configurations without first inspecting the surrounding context, related imports, database relationships, and existing tests.
2. **Follow Existing Conventions**: Preserve established patterns in typing, schema definitions, naming conventions, and file organization.
3. **Modular Monolith Architecture**: Avoid premature microservices. Keep backend modules cohesive, boundaries explicit, and domain logic self-contained.
4. **Separation of Concerns**: Strictly decouple standard application services (authentication, authorization, candidate profiles, application tracking, notifications) from AI orchestration workflows. Application services must operate independently of model availability.
5. **Deterministic Primacy Over Probabilistic Models**:
   - Hard eligibility filtering (degree, enrollment status, work authorization/visas, location, active deadlines) must execute strictly in pure Python/SQL deterministic code. Language models are strictly forbidden from evaluating or overriding eligibility.
   - Mathematical ranking and score aggregation must be deterministic. Never allow an LLM to invent scores or arbitrarily re-order ranked candidates.
   - Database mutations, authorization checks, and schema validation must be handled exclusively by deterministic code paths.
6. **Schema Enforcement & Provenance Guarantee**:
   - All agent state exchanges, tool inputs, and tool outputs must be validated using strict Pydantic v2 schemas.
   - Every skill claim, proficiency score, or recommendation explanation must be anchored to verifiable `EvidenceRecord` provenance.
7. **Security & Input Sanitization**:
   - **Never commit secrets** (API keys, database credentials, tokens) to source control. Use environment variables and `.env` files.
   - Treat all external resumes, project descriptions, ATS job listings, and web data as **untrusted**.
   - Strip malicious injection directives, zero-width characters, and script tags via Unicode NFKC normalization and sanitizers before downstream processing.
   - Pass untrusted external text into language models wrapped inside structured `tool_result` blocks with explicit `{"trust_level": "untrusted_data"}` headers.
8. **Avoid Unnecessary Abstractions & Premature Optimization**: Write clean, direct, and readable code. Do not introduce speculative design patterns or framework wrappers without concrete necessity.
9. **Rigorous Verification & Truthfulness**:
   - Write unit, integration, and golden dataset tests for critical business logic (eligibility gate, scoring math, MinHash deduplication, prompt injection sanitization).
   - **Never claim a test, command, or integration succeeded unless it was executed and actually verified.**
   - Run type checks (`mypy` / `tsc`), linters (`ruff` / `eslint`), and tests (`pytest` / `vitest` or `jest`) before concluding any task.
10. **Document Architectural Decisions**: Document non-trivial architectural changes, trade-offs, and decisions in `docs/decisions/` or the technical documentation suite.

---

## 2. Technology Baseline & Tooling Stack

- **Backend API**: Python 3.12+ with FastAPI (asynchronous endpoints, Pydantic v2 schemas).
- **Agent Orchestration**: LangGraph (cyclic `StateGraph`, subgraphs with `checkpoint_ns`, parallel worker dispatch via `Send` API, pure reducers, and `AsyncPostgresSaver` checkpointing).
- **Relational & Vector Storage**: PostgreSQL 16+ with `pgvector` (HNSW indexing) and `psycopg_pool.AsyncConnectionPool`.
- **Model Abstraction**: LiteLLM AI Gateway with Redis-backed circuit breakers and fallback cascade to local Ollama runners (`qwen2.5:14b-instruct`, `llama3.1:8b-instruct`).
- **Cache & Task Queue**: Redis Stack (RedisVL semantic cache, rate limiters) + `arq` for lightweight async background jobs.
- **Taxonomies & De-duplication**: ESCO v1.2.1 and O*NET v2.0 occupational taxonomies; `datasketch` / `rensa` for MinHash LSH near-duplicate job detection.
- **Frontend Application**: Next.js (App Router), React, TypeScript, and Tailwind CSS.

---

## 3. Layered Skill System & Invocation

Development tasks in JobFalcon are governed by a three-layer skill system:
- **Layer A (This Document)**: Non-negotiable repository rules, architectural invariants, determinism guarantees, and truthfulness standards.
- **Layer B (Specialized Skills)**: 12 focused development skills located in [`.agents/skills/`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills) (and aliased under [`.agent/skills/`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agent/skills)). Consult [`docs/SKILLS_INDEX.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/SKILLS_INDEX.md) for the full index and task matrix.
- **Layer C (Environment Skills)**: Built-in tools including `modern-web-guidance`, `a11y-debugging`, `chrome-devtools`, `debug-optimize-lcp`, and `memory-leak-debugging`.

### Core Skill Routing Quick Reference:
- **Architecture & System Boundaries**: Consult [`jobfalcon-architecture`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/jobfalcon-architecture/SKILL.md)
- **LangGraph StateGraph & Subgraphs**: Consult [`agentic-workflows`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/agentic-workflows/SKILL.md)
- **FastAPI, Async APIs & Pydantic v2**: Consult [`python-fastapi-engineering`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/python-fastapi-engineering/SKILL.md)
- **PostgreSQL, pgvector & Deduplication**: Consult [`database-and-retrieval`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/database-and-retrieval/SKILL.md)
- **Career Workspace UI/UX & Aesthetics**: Consult [`frontend-design`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/frontend-design/SKILL.md)
- **Next.js App Router & SSE Telemetry**: Consult [`frontend-engineering`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/frontend-engineering/SKILL.md)
- **Code-Writing Discipline & Surgical Edits**: Consult [`implementation-workflow`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/implementation-workflow/SKILL.md)
- **Threat Modeling & Prompt Injection Defense**: Consult [`ai-security-review`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/ai-security-review/SKILL.md)
- **Unit, Golden Benchmark & Workflow Tests**: Consult [`testing-and-evaluation`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/testing-and-evaluation/SKILL.md)
- **Tracing, Health Probes & Circuit Breakers**: Consult [`observability-and-reliability`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/observability-and-reliability/SKILL.md)
- **Docker Compose & Local Environments**: Consult [`deployment-and-local-dev`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/deployment-and-local-dev/SKILL.md)
- **ADRs & Documentation Governance**: Consult [`engineering-documentation`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/.agents/skills/engineering-documentation/SKILL.md)

---

## 4. Verification Checklists for Code Changes

Before marking any task as complete:
- [ ] Run linting and formatting (`ruff check .` and `ruff format --check .` for Python; `npm run lint` for Frontend).
- [ ] Run type checking (`mypy` for Python; `tsc --noEmit` for TypeScript).
- [ ] Run test suite (`pytest` for backend; test runner for frontend).
- [ ] Verify that no secrets or environment files are staged in git.
- [ ] Verify that hard eligibility rules remain 100% deterministic with zero LLM bypass.

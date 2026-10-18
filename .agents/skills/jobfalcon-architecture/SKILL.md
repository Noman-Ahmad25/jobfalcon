---
name: jobfalcon-architecture
description: Master architectural governance for JobFalcon. Use when evaluating system requirements, defining service boundaries, maintaining deterministic vs. probabilistic separation, or updating system topology and design contracts.
---

# JobFalcon — System Architecture & Engineering Governance

This skill guides architectural decision-making, service boundary enforcement, and system design for **JobFalcon**, an Agentic AI-Powered Career Opportunity Recommendation System.

---

## 1. When to Use This Skill

- Translating high-level product requirements into component specifications, interfaces, and data flows.
- Reviewing system boundary changes between application services and the AI orchestration runtime.
- Ensuring hard eligibility, scoring aggregation, and authorization remain strictly deterministic.
- Evaluating architectural trade-offs, dependencies, failure modes, and performance SLAs.
- Identifying and logging unresolved architectural decisions in `docs/UNRESOLVED_DECISIONS.md`.

---

## 2. Core Architectural Invariants

Every design decision must uphold these core architectural principles established in Sections 1–5:

1. **Modular Monolith Over Microservices**:
   Maintain a cohesive, asynchronous FastAPI backend. Avoid distributed microservice sprawl, event meshes, or premature service splitting.
2. **Decoupled Application Services**:
   Authentication, authorization, user profiles, saved opportunities, and notifications must operate independently of AI model availability. Application services must remain responsive even if external model gateways or third-party ATS feeds are offline.
3. **Deterministic Primacy Over Probabilistic Models**:
   - **Eligibility Filtering**: Mandatory degree, graduation window, work authorization, location/work-mode, and active deadline constraints must execute strictly in pure Python/SQL code (`Eligible(u, o)` boolean gate). Language models are strictly forbidden from evaluating or overriding eligibility.
   - **Ranking & Score Aggregation**: Mathematical formula execution ($Score_{\text{total}} = 0.30 S_{\text{skill}} + 0.20 S_{\text{career}} + 0.20 S_{\text{growth}} + 0.12 S_{\text{market}} + 0.10 S_{\text{pref}} + 0.08 S_{\text{qual}}$) and candidate ordering are strictly deterministic.
   - **Database Mutations**: Authoritative state mutations and access control are deterministic.
4. **Hierarchical Supervisor Multi-Agent Topology**:
   The Recommendation Orchestrator Agent directs five specialized worker subgraphs (`User & Career Profile`, `Market Intelligence`, `Opportunity Discovery & Validation`, `Recommendation & Ranking`, `Recommendation Explanation`) using LangGraph with bounded evaluator-optimizer loops and Map-Reduce parallelism (`Send` API).
5. **Dual-Path Execution SLA**:
   - Synchronous recommendation generation: $\le 8,000\text{ ms}$ (warm cache).
   - Cold-start profile ingestion and live market discovery: Asynchronous via Server-Sent Events (SSE) with a $\le 30,000\text{ ms}$ hard boundary.
6. **Unified AI Gateway with Local Fallback**:
   LiteLLM AI Gateway manages cloud LLM routing with Redis-backed circuit breakers (`allowed_fails = 3`, `cooldown = 60s`) and automatic failover cascade to local Ollama open-weights models (`qwen2.5:14b-instruct`, `llama3.1:8b-instruct`).
7. **Polymorphic Opportunity Domain Model**:
   Seamless support for internships, full-time jobs, apprenticeships, fellowships, and contracts without structural refactoring, anchored to international taxonomies (ESCO v1.2.1 and O*NET v2.0).

---

## 3. Workflow: Architectural Evaluation & Design

Follow this systematic procedure when addressing architectural tasks:

```
[Requirement Ingestion] 
         ↓
[Boundary Classification] → Application Domain vs. AI Agent Orchestration
         ↓
[Determinism Audit]     → Hard rules & math in deterministic code; LLMs for semantics/extraction
         ↓
[Data Contract Design]  → Pydantic v2 schemas, claim-check pointers, pure reducers
         ↓
[Failure Mode Analysis] → Circuit breakers, timeouts, degraded modes, loop bounds
         ↓
[Decision Recording]    → Document approved choices in ADR; log provisional items in UNRESOLVED_DECISIONS.md
```

### Step 1: Boundary Classification
- Determine whether the requirement belongs to:
  - **Application Service Layer**: Deterministic CRUD, user authentication, profile storage, bookmarking, notification delivery.
  - **Agent Orchestration Layer**: Evidence-backed skill extraction, market trend synthesis, semantic opportunity retrieval, personalized explanation generation.

### Step 2: Determinism Audit
- Verify that no probabilistic component has been granted authority over:
  - Disqualification of candidates based on compliance or hard prerequisites.
  - Calculation of numerical ranking scores.
  - State transitions involving monetary, legal, or database mutation operations.

### Step 3: Data Contract & State Review
- Enforce strict typing with Pydantic v2 models.
- Ensure large documents or raw resumes use the **Claim-Check Pattern** (pointers stored in state; raw text in PostgreSQL / MinIO).
- Verify state channels use pure binary reducers to handle parallel worker outputs without race conditions.

### Step 4: Failure & Degradation Design
- Define fallback trajectories: If live market APIs timeout (4,000 ms), serve cached snapshots with `is_stale = True`.
- If discovery yields fewer than $K_{\text{min}} = 5$ eligible opportunities, route through Level 0 $\rightarrow$ Level 1 (soft preference relaxation) $\rightarrow$ Level 2 (adjacent career fan-out via `Send` API) with a hard cap at `MAX_ORCHESTRATOR_LOOPS = 4`.

### Step 5: Documenting Decisions & Trade-Offs
- If a decision alters system interfaces or persistent schemas, record an Architecture Decision Record (ADR) in `docs/decisions/`.
- If a parameter, formula, or threshold lacks empirical validation, mark it as provisional and log it in `docs/UNRESOLVED_DECISIONS.md`.

---

## 4. Architectural Anti-Patterns & Constraints

- ❌ **DO NOT** introduce microservices, message queues, or event brokers unless a demonstrated concurrency bottleneck exceeds the capacity of FastAPI + PostgreSQL + Redis.
- ❌ **DO NOT** allow language models to output arbitrary ranking numbers or sorting orders directly. Ranking is computed deterministically from structured agent outputs.
- ❌ **DO NOT** pass massive raw document text or binary PDFs into LangGraph state channels. Use claim-check URIs.
- ❌ **DO NOT** silently hardcode provisional formulas without documenting them in `docs/UNRESOLVED_DECISIONS.md`.
- ❌ **DO NOT** couple application endpoints directly to third-party AI provider SDKs; always route through the LiteLLM gateway.

---

## 5. Verification Checklist

Before completing an architectural design task:
- [ ] Hard eligibility rules and scoring aggregation are 100% deterministic with zero LLM bypass.
- [ ] Application services remain functional if AI models are unavailable.
- [ ] State contracts and tool inputs use strict Pydantic v2 validation.
- [ ] Failure recovery, timeouts, and fallback modes are explicitly defined.
- [ ] Unresolved questions or provisional parameters are recorded in `docs/UNRESOLVED_DECISIONS.md`.

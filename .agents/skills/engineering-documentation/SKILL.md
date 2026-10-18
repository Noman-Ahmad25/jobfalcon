---
name: engineering-documentation
description: Maintain architecture decision records (ADRs), system documentation, calibration logs, and API specifications for JobFalcon. Use when recording architectural decisions, updating docs/UNRESOLVED_DECISIONS.md, or documenting system contracts.
---

# Technical Documentation & Architectural Decision Records

This skill guides the creation and maintenance of technical documentation, Architecture Decision Records (ADRs), calibration logs, and API contracts for **JobFalcon**.

---

## 1. When to Use This Skill

- Recording significant, non-trivial architectural changes and trade-offs in `docs/decisions/`.
- Logging or updating provisional parameters, formulas, and calibration tasks in `docs/UNRESOLVED_DECISIONS.md`.
- Documenting API contracts, data models, or streaming event formats.
- Keeping architecture diagrams (Mermaid) synchronized with actual code implementation.
- Writing onboarding, deployment, and troubleshooting guides for developers.

---

## 2. Documentation Architecture & Standards

JobFalcon's documentation is organized systematically under `docs/`:

```text
docs/
├── Sections 1.docx ... 5.docx   # Baseline technical architecture reference
├── UNRESOLVED_DECISIONS.md      # Provisional formulas, thresholds, & open decisions
├── decisions/                   # Architecture Decision Records (ADRs)
│   ├── ADR-001-template.md      # Standard ADR template
│   ├── ADR-002-langgraph-supervisor.md
│   ├── ADR-003-deterministic-eligibility-gate.md
│   └── ...
└── api/                         # API specifications & contracts
```

---

## 3. Workflow: Documenting Decisions & Specifications

### Step 1: Architecture Decision Record (ADR) Process
When an architectural choice affects system topology, data boundaries, frameworks, or security models, create a structured ADR in `docs/decisions/ADR-XXX-<slug>.md`:

```markdown
# ADR-002: Hierarchical Supervisor Pattern with LangGraph

## Status
Accepted

## Context
JobFalcon requires coordinating multiple specialized agents (profile parsing, market intelligence, opportunity discovery, ranking, explanation). Static sequential chains lack runtime branching capability, while open-ended multi-agent group chats introduce unpredictable scoring drift and latency.

## Decision
Implement a Hierarchical Orchestrator-Workers (Supervisor) Pattern using LangGraph with:
- `RecommendationGraphState` typed contract with pure binary reducers.
- Dynamic Map-Reduce fan-out via LangGraph's `Send` primitive.
- Subgraph namespace isolation (`checkpoint_ns`).
- A mandatory pure deterministic Python eligibility gate between discovery and ranking.

## Consequences
### Positive
- Strict governance over iteration budgets (`MAX_ORCHESTRATOR_LOOPS = 4`).
- Parallelism eliminates sequential discovery bottlenecks.
- Zero risk of LLM hallucinations overriding hard eligibility constraints.

### Negative / Trade-Offs
- Requires disciplined pure reducer design for concurrent channel merges.
- Checkpointer pool concurrency must be tuned (`AsyncConnectionPool`).

## Compliance & Verification
Verified via workflow unit tests in `tests/workflows/test_agent_graph.py`.
```

### Step 2: Tracking Provisional Formulas & Decisions
When incorporating formulas or thresholds that have not been empirically verified (e.g., Growth Potential bell-curve $\mathcal{B}(\Delta_{\text{gap}})$, decay constants, or ranking weights):
1. **DO NOT** silently claim the formula is final.
2. Record the provisional formula, current baseline values, and necessary validation procedures in `docs/UNRESOLVED_DECISIONS.md`.
3. Link the code comments to `docs/UNRESOLVED_DECISIONS.md`.

### Step 3: Diagram Maintenance
- Always use standard GitHub-compatible Mermaid diagrams (`flowchart TD`, `sequenceDiagram`, `stateDiagram-v2`).
- Quote labels containing special characters to prevent rendering syntax errors: `id["Step (Details)"]`.

---

## 4. Documentation Constraints & Anti-Patterns

- ❌ **DO NOT** claim a feature, test, or benchmark is implemented or verified if it is still a proposal or placeholder.
- ❌ **DO NOT** allow documentation and actual code implementation to drift out of sync. Update docs alongside code changes.
- ❌ **DO NOT** commit secrets, passwords, or production tokens into documentation examples.
- ❌ **DO NOT** invent speculative mathematical formulas without logging them in `docs/UNRESOLVED_DECISIONS.md`.

---

## 5. Verification Checklist

Before completing a documentation task:
- [ ] ADR follows standard sections (Status, Context, Decision, Consequences, Compliance).
- [ ] Mermaid diagrams render validly without syntax errors.
- [ ] Provisional parameters are logged in `docs/UNRESOLVED_DECISIONS.md`.
- [ ] Links and file references use valid markdown paths.
- [ ] Statements regarding system capabilities are strictly truthful.

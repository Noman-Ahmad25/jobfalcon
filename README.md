# JobFalcon

An Agentic AI-Powered Career Opportunity Recommendation System that builds evidence-backed skill profiles, analyzes labor-market trends, and discovers, evaluates, and ranks career opportunities based on deterministic eligibility, skill fit, and growth potential.

## Documentation & Architecture References

- **Architecture Specification**: Complete 5-part architecture specification located in [`docs/`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs) (Sections 1–5).
- **Engineering Guidelines & Rules**: Agent instructions, coding standards, and security requirements in [`AGENTS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/AGENTS.md).
- **Development Skill System**: 12 modular Antigravity development skills cataloged in [`docs/SKILLS_INDEX.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/SKILLS_INDEX.md).
- **Architectural Decisions & Calibration Items**: Open decisions and provisional formulas recorded in [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md).

## Core System Architecture

1. **Modular Monolith**: FastAPI backend with decoupled application services and LangGraph multi-agent orchestration.
2. **Deterministic Gating & Scoring**: 100% deterministic rule enforcement for hard eligibility constraints and mathematical 6-dimensional MCDA ranking.
3. **Evidence-Backed Career Intelligence**: Multi-source skill extraction anchored to ESCO v1.2.1 and O*NET v2.0 taxonomies with verifiability weighting and epistemic confidence.
4. **Hierarchical Multi-Agent Supervisor**: Orchestrator coordinating specialist agents (Profile, Market Intelligence, Opportunity Discovery, Ranking, and Explanation) with bounded evaluator-optimizer loops and Map-Reduce parallelism.
5. **Robust Local & Cloud Hybrid AI**: LiteLLM AI Gateway with Redis-backed circuit breakers and fallback cascade to local Ollama open-weights models.


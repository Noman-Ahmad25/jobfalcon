---
name: python-fastapi-engineering
description: Design, implement, and maintain FastAPI backend services, domain modules, and application APIs. Use when building FastAPI routers, Pydantic v2 models, async database sessions, SSE streaming endpoints, or application service logic.
---

# Python & FastAPI Backend Engineering

This skill guides the implementation of JobFalcon's modular backend services, application APIs, asynchronous data pipelines, and Pydantic v2 data models using **Python 3.12+** and **FastAPI**.

---

## 1. When to Use This Skill

- Building or updating FastAPI route handlers, routers, and middleware.
- Defining Pydantic v2 domain schemas, request bodies, and response envelopes.
- Implementing application domain services (`auth`, `profile`, `opportunity`, `eligibility`, `ranking`).
- Configuring asynchronous database sessions (`SQLAlchemy 2.0`, `psycopg_pool.AsyncConnectionPool`).
- Implementing Server-Sent Events (SSE) streaming endpoints for live agent execution progress.
- Managing backend configuration (`pydantic-settings`), lifecycle events, and structured error responses.

---

## 2. Architecture & Module Boundaries

JobFalcon organizes backend capabilities into a **Modular Monolith** under `backend/app/modules/`:

```text
backend/app/
├── api/
│   ├── v1/
│   │   ├── auth.py              # User authentication & token management
│   │   ├── profile.py           # Career profile & resume upload
│   │   ├── opportunities.py     # Opportunity catalog & filtering
│   │   └── recommendations.py   # Sync & SSE streaming recommendations
│   └── deps.py                  # FastAPI dependency injection (DB, auth, user)
├── core/
│   ├── config.py                # Pydantic v2 BaseSettings
│   ├── security.py              # Password hashing & JWT validation
│   └── sanitization.py          # NFKC normalization & prompt injection sanitizer
├── modules/
│   ├── auth/                    # Application Service: User accounts & sessions
│   ├── profile/                 # Application Service: Profile management & parsing
│   ├── market/                  # Taxonomy resolution (ESCO / O*NET) & demand stats
│   ├── opportunity/             # Opportunity ingestion & MinHash LSH deduplication
│   ├── eligibility/             # Deterministic Engine: Hard boolean rule gate
│   ├── ranking/                 # Deterministic Engine: 6-Dimensional MCDA scoring
│   └── agents/                  # LangGraph StateGraph & Subgraphs
├── db/
│   ├── base.py                  # SQLAlchemy declarative base & async engine
│   ├── models/                  # Relational & pgvector ORM models
│   └── repositories/            # Data access layer
└── schemas/                     # Core Pydantic v2 domain schemas
```

---

## 3. Workflow: Implementing Backend Services & Endpoints

### Step 1: Strict Pydantic v2 Schema Modeling
- Use strict Python 3.12+ type annotations (`list[str]`, `str | None`).
- Use `@field_validator` and `@model_validator` to enforce validation invariants and sanitization:

> [!NOTE] Target Implementation Pattern
> The code patterns below illustrate target implementations for Phase 1. Application code has not yet been implemented in the repository.

```python
from pydantic import BaseModel, Field, model_validator

class SixDimensionalScoreBreakdown(BaseModel):
    skill_match_score: float = Field(..., ge=0.0, le=1.0)
    career_match_score: float = Field(..., ge=0.0, le=1.0)
    growth_potential_score: float = Field(..., ge=0.0, le=1.0)
    market_relevance_score: float = Field(..., ge=0.0, le=1.0)
    user_preference_score: float = Field(..., ge=0.0, le=1.0)
    opportunity_quality_score: float = Field(..., ge=0.0, le=1.0)
    composite_total_score: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _verify_deterministic_weighted_sum(self) -> "SixDimensionalScoreBreakdown":
        # NOTE: Linear weights (0.30, 0.20, 0.20, 0.12, 0.10, 0.08) are provisional baseline
        # parameters from Section 2, pending empirical calibration (see docs/UNRESOLVED_DECISIONS.md).
        expected = (
            0.30 * self.skill_match_score
            + 0.20 * self.career_match_score
            + 0.20 * self.growth_potential_score
            + 0.12 * self.market_relevance_score
            + 0.10 * self.user_preference_score
            + 0.08 * self.opportunity_quality_score
        )
        if abs(self.composite_total_score - expected) > 1e-4:
            raise ValueError(
                f"Composite score ({self.composite_total_score}) violates deterministic formula ({expected:.4f})."
            )
        return self
```

### Step 2: Implement Dependency Injection & Async DB Sessions
- Manage database connections using `AsyncSession` yielding context blocks.
- Avoid holding transactions open during external API calls or LLM inference loops:

```python
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import async_session_factory

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Step 3: Implement SSE Streaming for Long-Running Workflows
- For asynchronous recommendation generation, stream structured progress events via `StreamingResponse`:

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

@router.post("/recommendations/stream")
async def stream_recommendation_progress(
    request: RecommendationRequest,
    current_user: User = Depends(get_current_active_user),
):
    async def event_generator():
        # Yield progress updates as LangGraph supersteps complete
        async for event in run_agent_workflow_streaming(current_user.id, request):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

### Step 4: Deterministic Engine Decoupling
- Keep eligibility and ranking code purely functional, with zero external network or model dependencies:
  - `evaluate_eligibility(profile: CandidateCareerProfile, opportunity: PolymorphicOpportunity) -> EligibilityResult`
  - `compute_six_dimensional_scores(...) -> SixDimensionalScoreBreakdown`

---

## 4. Backend Constraints & Anti-Patterns

- ❌ **DO NOT** execute blocking synchronous I/O (`time.sleep()`, `requests.get()`) in `async def` endpoints. Use `asyncio.sleep()` and `httpx.AsyncClient`.
- ❌ **DO NOT** implement business logic in multiple backends or split endpoints into premature microservices.
- ❌ **DO NOT** let database sessions remain open across LLM generation supersteps.
- ❌ **DO NOT** return raw internal exceptions or stack traces to clients. Use RFC 7807 Problem Details envelopes.
- ❌ **DO NOT** invent custom validation when Pydantic v2 built-in constraints (`ge`, `le`, `min_length`) suffice.

---

## 5. Verification Checklist

Before completing a Python / FastAPI backend task:
- [ ] Code passes formatting and linting: `ruff check .` and `ruff format --check .`.
- [ ] Type checks pass without errors: `mypy .`.
- [ ] Database transactions are properly committed or rolled back with async context managers.
- [ ] Streaming endpoints set appropriate SSE headers (`text/event-stream`, `no-cache`).
- [ ] Unit and integration tests verify new routes, schemas, and error contracts with `pytest`.

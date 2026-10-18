---
name: observability-and-reliability
description: Distributed tracing, telemetry, structured logging, and circuit-breaker reliability for JobFalcon. Use when configuring OpenTelemetry, setting up LiteLLM circuit breakers, implementing correlation trace IDs, or debugging latency and failure cascades.
---

# Observability, Reliability & Telemetry Engineering

This skill guides the implementation of distributed tracing, structured logging, system health checks, and circuit-breaker reliability for **JobFalcon**.

---

## 1. When to Use This Skill

- Implementing distributed tracing with OpenTelemetry and correlation IDs (`thread_id`).
- Configuring LiteLLM AI Gateway circuit breakers and local Ollama failover cascades.
- Designing structured JSON logging and redaction filters for secrets and PII.
- Separating internal operational metrics from user-facing agent progress events.
- Implementing `/healthz` (liveness) and `/readyz` (readiness) probe endpoints.
- Profiling token latency histograms, database query durations, and memory consumption.

---

## 2. Telemetry Architecture & Segregation

A critical architectural distinction is maintained between **Operational Telemetry** and the **User Activity Feed**:

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Execution Event                     │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│  Internal Operational Trace │ │   User-Facing Progress Feed │
│  (Engineers & Observability)│ │   (Candidate UI Stream)     │
├─────────────────────────────┤ ├─────────────────────────────┤
│ • Trace ID / Span ID        │ │ • Phase Milestone           │
│ • Token In/Out Latency      │ │ • High-level summary text   │
│ • Prompt Fingerprints       │ │ • Non-technical status      │
│ • Redis Cache Hit / Miss    │ │ • Estimated completion      │
│ • DB Connection Wait Time   │ │                             │
│ (Exported via OTLP gRPC)    │ │ (Streamed via SSE)          │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 3. Workflow: Implementing Observability & Reliability

### Step 1: Trace Propagation & Correlation IDs
- Assign a deterministic `thread_id = uuid7(user_id + session_id)` to every incoming recommendation request.
- Propagate this correlation ID across FastAPI request contexts, database queries, and LangGraph checkpoints:

```python
import structlog
from uuid_extensions import uuid7

logger = structlog.get_logger()

def create_recommendation_context(user_id: str, session_id: str) -> str:
    thread_id = str(uuid7())
    structlog.contextvars.bind_contextvars(
        thread_id=thread_id,
        user_id=user_id,
        session_id=session_id
    )
    return thread_id
```

### Step 2: Configure LiteLLM Gateway Circuit Breakers
- To safeguard against upstream provider rate limits (HTTP 429) and outages (HTTP 500/503), configure LiteLLM router with Redis-backed circuit breakers:
```python
from litellm import Router

model_list = [
    {
        "model_name": "primary-model",
        "litellm_params": {"model": "gemini/gemini-2.5-pro", "api_key": "..."},
    },
    {
        "model_name": "secondary-model",
        "litellm_params": {"model": "anthropic/claude-3-7-sonnet", "api_key": "..."},
    },
    {
        "model_name": "local-fallback",
        "litellm_params": {
            "model": "ollama/qwen2.5:14b-instruct", 
            "api_base": "http://localhost:11434"
        },
    }
]

router = Router(
    model_list=model_list,
    redis_url="redis://localhost:6379",
    allowed_fails=3,        # Trip circuit breaker after 3 failures in 60s
    cooldown_time=60,       # Cooldown 60s before retrying primary
    fallbacks=[{"primary-model": ["secondary-model", "local-fallback"]}],
)
```

### Step 3: Implement Health & Readiness Probes
- Define distinct liveness and readiness endpoints:
  - `/healthz`: Verifies FastAPI process is running.
  - `/readyz`: Verifies active connection to PostgreSQL, Redis, and LiteLLM gateway:

```python
from fastapi import APIRouter, Response, status
from app.db.base import check_db_health
from app.core.cache import check_redis_health

router = APIRouter()

@router.get("/readyz")
async def readiness_probe():
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()
    if db_ok and redis_ok:
        return {"status": "READY", "database": "OK", "cache": "OK"}
    return Response(
        content='{"status": "UNREADY"}', 
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
        media_type="application/json"
    )
```

### Step 4: Redaction & Safe Logging
- Configure logging processors to automatically strip authentication tokens, passwords, and sensitive PII before serialization.

---

## 4. Observability Constraints & Anti-Patterns

- ❌ **DO NOT** emit raw internal model prompts containing candidate resumes or PII to third-party unencrypted log aggregators.
- ❌ **DO NOT** clutter user-facing streaming feeds with operational debug logs, stack traces, or raw token counts.
- ❌ **DO NOT** introduce unbounded tracing overhead. Set sampling rates (e.g., 100% for errors, 10% for successful requests in high-volume environments).
- ❌ **DO NOT** swallow exceptions silently without logging a correlated error event with `thread_id`.

---

## 5. Verification Checklist

Before finalizing an observability or reliability task:
- [ ] Correlation IDs (`thread_id`) propagate across API, agent execution, and DB layers.
- [ ] Circuit breaker correctly transitions to fallback Ollama models upon simulated provider failure.
- [ ] Redaction filters successfully prevent secrets and PII from appearing in logs.
- [ ] `/healthz` and `/readyz` endpoints accurately report service dependency states.

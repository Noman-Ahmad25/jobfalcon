---
name: deployment-and-local-dev
description: Container orchestration, local developer setup, environment profiles, and deployment configuration for JobFalcon. Use when configuring Docker Compose, setting up PostgreSQL/Redis/MinIO services, writing Dockerfiles, or managing environment variables.
---

# Deployment & Local Developer Experience

This skill guides container packaging, Docker Compose orchestration, environment profile configuration, and local developer workflows for **JobFalcon**.

---

## 1. When to Use This Skill

- Authoring or updating `docker-compose.yml` for local service dependencies.
- Writing Dockerfiles for the FastAPI backend, Next.js frontend, or background workers.
- Managing environment variables, secrets templates (`.env.example`), and configuration profiles.
- Configuring container health checks, dependency startup order, and network bridges.
- Providing reproducible setup, reset, and troubleshooting workflows for contributors.

---

## 2. Infrastructure Topology & Service Profiles

JobFalcon is designed to support both a frictionless **clone-and-run local development setup** and a **hosted demo profile**:

> [!NOTE] Deployment Model Flexibility
> The infrastructure blueprint below illustrates the service stack for local development and demonstration. The final deployment strategy (local-only, dual, or hosted) remains an open decision to be evaluated during implementation (see [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md)).

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                   │
│                                                             │
│  ┌───────────────────────┐   ┌───────────────────────┐      │
│  │     PostgreSQL 16     │   │      Redis Stack      │      │
│  │     with pgvector     │   │ (RedisVL & Cache)     │      │
│  │     (Port 5432)       │   │     (Port 6379)       │      │
│  └───────────────────────┘   └───────────────────────┘      │
│                                                             │
│  ┌───────────────────────┐   ┌───────────────────────┐      │
│  │        MinIO          │   │     Ollama Server     │      │
│  │ (S3-compatible Object)│   │  (Local Quantized LLM)│      │
│  │  (Ports 9000 / 9001)  │   │     (Port 11434)      │      │
│  └───────────────────────┘   └───────────────────────┘      │
│                                                             │
│  ┌───────────────────────┐   ┌───────────────────────┐      │
│  │    FastAPI Backend    │   │   Next.js Frontend    │      │
│  │     (Port 8000)       │   │     (Port 3000)       │      │
│  └───────────────────────┘   └───────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Workflow: Orchestrating Local & Deployment Services

### Step 1: Composable `docker-compose.yml` Specification
- Organize services with explicit health checks and container startup dependency conditions (`depends_on` with `condition: service_healthy`):

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: jobfalcon
      POSTGRES_USER: jobfalcon_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-devpassword123}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U jobfalcon_user -d jobfalcon"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis/redis-stack-server:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### Step 2: Environment Configuration (`.env.example`)
- Maintain a comprehensive `.env.example` documenting all configuration keys:
  - Database URL (`postgresql+asyncpg://...`)
  - Redis URL (`redis://...`)
  - LiteLLM Gateway keys (Google Gemini, Anthropic Claude, OpenAI)
  - Ollama base URL (`http://localhost:11434`)
  - MinIO / S3 credentials and bucket names
  - Application secret keys and JWT algorithms

### Step 3: Automated Startup & Database Migration Sequence
- Ensure backend startup containers execute database migrations before accepting HTTP traffic:
```bash
# In backend entrypoint script
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Safe Reset & Teardown Workflows
- Document safe commands for cleaning state without accidental data loss:
  - Stop services: `docker compose down`
  - Total state reset: `docker compose down -v` (with explicit confirmation prompt)

---

## 4. Deployment Constraints & Anti-Patterns

- ❌ **DO NOT** commit unencrypted `.env` files or hardcoded database passwords to version control.
- ❌ **DO NOT** rely on unverified container images from unknown registries; use official upstream bases.
- ❌ **DO NOT** run database migrations inside individual application worker processes in parallel; run migrations in a single-instance init container.
- ❌ **DO NOT** assume network connectivity to external AI APIs in offline development profiles; ensure Ollama local fallback is operational.

---

## 5. Verification Checklist

Before completing a deployment or environment task:
- [ ] `docker compose up -d` boots all dependencies with healthy statuses.
- [ ] `.env.example` is fully up-to-date with all required configuration variables.
- [ ] Database migrations execute cleanly on fresh database initialization.
- [ ] Services communicate properly over the shared internal Docker network bridge.
- [ ] Reset and teardown procedures are verified.

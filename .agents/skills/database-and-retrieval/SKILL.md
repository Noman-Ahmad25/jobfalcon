---
name: database-and-retrieval
description: Database architecture, relational modeling, pgvector search, deduplication, and caching. Use when designing PostgreSQL schemas, writing Alembic migrations, optimizing pgvector HNSW indexes, implementing MinHash LSH, or tuning RedisVL semantic caching.
---

# Database, Retrieval & Persistence Engineering

This skill guides the design, implementation, and optimization of JobFalcon's persistence layer, vector search indexes, deduplication engines, and caching tiers using **PostgreSQL 16**, **pgvector**, **Alembic**, **MinHash LSH**, and **Redis Stack**.

---

## 1. When to Use This Skill

- Creating or modifying relational tables, foreign key constraints, or Alembic database migrations.
- Designing and configuring `pgvector` HNSW indexes for hybrid semantic-lexical retrieval.
- Implementing MinHash LSH near-duplicate detection (`datasketch` / `rensa`) for syndicated job feeds.
- Configuring RedisVL semantic caching and rate limiters.
- Tuning connection pooling (`psycopg_pool.AsyncConnectionPool`) for LangGraph `AsyncPostgresSaver` checkpointer throughput.
- Implementing data retention and pruning jobs (nightly deletion of checkpoints older than 30 days).

---

## 2. Persistence Architecture Overview

JobFalcon consolidates data storage into two primary engines:

```
┌────────────────────────────────────────────────────────┐
│                   PostgreSQL 16                        │
│                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │   Relational Store    │   │     pgvector HNSW     │ │
│  │ (Profiles, Opps,      │   │ (Dense Opportunity &  │ │
│  │  Evidence, Audits)    │   │  Skill Embeddings)    │ │
│  └───────────────────────┘   └───────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │       LangGraph Checkpoints & Durable Store       │ │
│  │ (Thread Supersteps, PostgresStore User Memory)     │ │
│  └───────────────────────────────────────────────────┘ │
└──────────────────────────┬─────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────┐
│                    Redis Stack                         │
│                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐ │
│  │   RedisVL Semantic    │   │ Distributed Rate      │ │
│  │   Market Cache (168h) │   │ Limiters & Circuit    │ │
│  └───────────────────────┘   └───────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

---

## 3. Workflow: Persistence & Retrieval Implementation

### Step 1: Schema Design with Strict Constraints & Alembic Migrations
- Define SQLAlchemy 2.0 declarative models with non-nullable constraints, foreign keys with explicit on-delete behaviors, and check constraints.

> [!NOTE] Target Implementation Pattern
> The ORM model and index definitions below illustrate target implementations for Phase 1 and 2. Retrieval weights ($w_{\text{dense}}, w_{\text{sparse}}$) and deduplication thresholds ($\ge 0.85$ Jaccard) are baseline parameters subject to empirical calibration (see [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md)).

```python
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class OpportunityModel(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True)
    minhash_signature_hex = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    company_name = Column(String(150), nullable=False)
    occupation_code = Column(String(50), nullable=False, index=True)
    eligibility_rules = Column(JSONB, nullable=False)
    skill_requirements = Column(JSONB, nullable=False)
    embedding = Column(Vector(1536), nullable=True)  # pgvector representation
    posted_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index(
            "ix_opportunities_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
```

- Always generate migrations explicitly via Alembic: `alembic revision --autogenerate -m "create_opportunities"`.

### Step 2: Near-Duplicate Detection via MinHash LSH
- Before persisting an incoming opportunity listing, compute a 128-permutation MinHash signature over 3-word shingles:
- If Jaccard similarity $\ge 0.85$ against an active listing in the LSH index, merge as a duplicate provenance record rather than creating a duplicate row:

```python
from datasketch import MinHash, MinHashLSH

def compute_minhash(text: str) -> MinHash:
    m = MinHash(num_perm=128)
    words = text.lower().split()
    for i in range(len(words) - 2):
        shingle = " ".join(words[i:i+3])
        m.update(shingle.encode("utf-8"))
    return m
```

### Step 3: Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
- For opportunities passing deterministic eligibility, merge dense vector search (cosine distance in pgvector) and sparse lexical search (BM25) with smoothing constant $k = 60$:

$$\text{RRF}(u, o) = \frac{w_{\text{dense}}}{60 + \text{rank}_{\text{dense}}(u, o)} + \frac{w_{\text{sparse}}}{60 + \text{rank}_{\text{sparse}}(u, o)}$$

### Step 4: Checkpointer Concurrency Optimization
- Prevent `AsyncPostgresSaver` pool locks from bottlenecking under concurrent FastAPI requests:
  - Configure `psycopg_pool.AsyncConnectionPool(min_size=10, max_size=100)`.
  - Use `durability="async"` for worker intermediate supersteps and `durability="sync"` at terminal state boundaries.
  - Schedule nightly pruning: `DELETE FROM checkpoints WHERE created_at < NOW() - INTERVAL '30 days'`.

---

## 4. Persistence Constraints & Anti-Patterns

- ❌ **DO NOT** execute unindexed full-table scans over large opportunity catalogs. Always verify index usage with `EXPLAIN ANALYZE`.
- ❌ **DO NOT** store massive raw resumes or HTML files directly in relational rows. Use MinIO object storage with URI pointers in the database.
- ❌ **DO NOT** bypass Alembic migrations by directly altering production database tables.
- ❌ **DO NOT** execute long-running or blocking queries inside HTTP request handler transactions.
- ❌ **DO NOT** omit the 30-day checkpoint pruning policy, as raw state checkpoints will cause database bloat.

---

## 5. Verification Checklist

Before completing a database or retrieval task:
- [ ] Alembic migration scripts generate cleanly and support bidirectional execution (`upgrade` and `downgrade`).
- [ ] pgvector HNSW indexes specify explicit `m`, `ef_construction`, and distance operators.
- [ ] MinHash LSH deduplication correctly identifies duplicates at $\ge 0.85$ Jaccard similarity threshold.
- [ ] Foreign keys, unique constraints, and non-nullability invariants are enforced.
- [ ] Query performance verified with realistic data volumes.

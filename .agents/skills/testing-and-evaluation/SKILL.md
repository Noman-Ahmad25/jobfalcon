---
name: testing-and-evaluation
description: Testing, benchmarking, and evaluation frameworks for JobFalcon. Use when writing unit/integration tests, evaluating deterministic eligibility gates, running golden dataset benchmarks, or testing agent workflows with mocked tools.
---

# Testing, Evaluation & Quality Assurance

This skill guides test engineering, deterministic rule verification, golden dataset benchmarking, and agent workflow testing for **JobFalcon**.

---

## 1. When to Use This Skill

- Writing unit tests for deterministic eligibility rules, scoring formulas, and Pydantic validators.
- Testing LangGraph multi-agent workflows using mocked model and tool responses.
- Executing and updating the **500-pair Golden Benchmark** for deterministic eligibility precision and recall.
- Auditing Gate 4 Explanation Grounding to ensure 100% Claim-to-Evidence Attribution Rate (CEAR = 1.0).
- Testing failure modes, timeouts, circuit breakers, and Level 0–2 query expansion recovery.
- Load-testing checkpointer throughput with reproducible workloads.

---

## 2. Multi-Tier Testing Hierarchy

```text
tests/
├── unit/
│   ├── test_eligibility.py       # Hard boolean gate tests (100% determinism)
│   ├── test_ranking.py           # 6-Dimensional MCDA formula & RRF math tests
│   ├── test_sanitization.py      # Indirect prompt injection & unicode tests
│   ├── test_minhash.py           # Near-duplicate detection & Jaccard threshold tests
│   └── test_schemas.py           # Pydantic v2 validation & error handling tests
├── integration/
│   ├── test_api_auth.py          # User auth, token refresh, and RBAC
│   ├── test_api_profile.py       # Profile upload & persistence
│   ├── test_api_stream.py        # SSE streaming recommendation endpoints
│   └── test_db_repositories.py   # PostgreSQL + pgvector query transactions
├── workflows/
│   ├── test_agent_graph.py       # Mocked LangGraph supervisor execution
│   └── test_self_healing.py      # Circuit breakers, retry loops, & query expansion
└── benchmarks/
    ├── golden_dataset_500.json   # 500 synthetic candidate-opportunity pairs
    └── test_golden_eval.py       # Precision & recall verification suite
```

---

## 3. Workflow: Executing Verification & Evaluation

### Step 1: Unit Testing Pure Deterministic Engines
- Ensure deterministic rule evaluations test boundary conditions, null values, and edge cases.

> [!NOTE] Target Implementation Pattern
> The test structures below illustrate the target patterns for Phase 1 verification suites. Benchmarking thresholds ($Score \ge 0.55$, $K_{\text{min}} = 5$) represent baseline criteria to be evaluated against empirical testbeds (see [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md)).

```python
import pytest
from datetime import date, timedelta
from app.modules.eligibility.engine import evaluate_eligibility
from app.schemas.profile import CandidateEligibilityProfile
from app.schemas.opportunity import OpportunityEligibilityRules

def test_eligibility_fails_on_expired_deadline():
    candidate = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        highest_degree_level="BACHELORS",
        allowed_opportunity_categories=["FULL_TIME_JOB"],
        allowed_work_modes=["REMOTE"],
    )
    yesterday = date.today() - timedelta(days=1)
    opportunity = OpportunityEligibilityRules(
        opportunity_category="FULL_TIME_JOB",
        eligible_country_codes=["US"],
        work_mode="REMOTE",
        application_deadline=yesterday,
    )
    result = evaluate_eligibility(candidate, opportunity)
    assert result.is_eligible is False
    assert "ERR_DEADLINE_EXPIRED" in result.disqualification_codes
```

### Step 2: Golden Dataset Benchmark Evaluation (Phase 1 Exit Gate)
- Run the 500-pair synthetic benchmark to verify 100% precision and recall on hard eligibility constraints:
```bash
pytest tests/benchmarks/test_golden_eval.py -v
```
- The exit gate mandates **zero false positives and zero false negatives** on degree requirements, visa sponsorship, enrollment status, and deadlines.

### Step 3: LangGraph Multi-Agent Workflow Testing with Mocked Providers
- Never execute live paid API calls during automated CI test runs. Use LiteLLM mock responses or custom MockModel instances:
```python
import pytest
from app.modules.agents.graph import compiled_recommendation_graph

@pytest.mark.asyncio
async def test_workflow_recovers_via_expansion_on_empty_pool(mock_litellm, mock_db_pool):
    # Setup initial state yielding zero eligible candidates on Level 0
    initial_state = {
        "thread_id": "test-thread-001",
        "user_id": "user-123",
        "discovery_expansion_level": 0,
        "orchestrator_loop_count": 0,
        "executed_query_hashes": [],
        ...
    }
    final_state = await compiled_recommendation_graph.ainvoke(initial_state)
    # Verify graph expanded to adjacent career paths and terminated gracefully
    assert final_state["discovery_expansion_level"] >= 1
    assert final_state["orchestrator_loop_count"] <= 4
    assert final_state["terminal_status"] in ("SUCCESS", "DEGRADED_PARTIAL")
```

### Step 4: Explanation Grounding & Provenance Audit (Gate 4)
- Verify that every recommended opportunity explanation cites only verified evidence IDs:
```python
def test_explanation_claim_to_evidence_attribution(sample_explanation, sample_ranking):
    # Claim-to-Evidence Attribution Rate must equal 1.0
    for cited_id in sample_explanation.cited_skill_ids:
        assert cited_id in sample_ranking.matched_existing_skill_ids or \
               cited_id in sample_ranking.targeted_growth_skill_ids
```

---

## 4. Testing Constraints & Anti-Patterns

- ❌ **DO NOT** claim a test passed without running it. Always execute the test runner and verify stdout.
- ❌ **DO NOT** rely on flaky, non-deterministic assertions for LLM text. Test structured output conformance, entity ID presence, and mathematical properties.
- ❌ **DO NOT** let integration tests mutate production databases. Use dedicated test schemas with rollback fixtures.
- ❌ **DO NOT** skip testing edge cases (e.g., candidate with 0 skills, expired jobs, missing optional fields).

---

## 5. Verification Checklist

Before completing a testing or evaluation task:
- [ ] All unit and integration tests pass cleanly: `pytest`.
- [ ] Deterministic eligibility rules achieve 100% precision and recall on golden benchmark test cases.
- [ ] Six-dimensional score aggregation tests confirm zero mathematical drift.
- [ ] Workflow recovery from empty pools terminates within $\le 4$ supervisor loops.
- [ ] Test coverage results are truthfully reported without speculation.

---
name: agentic-workflows
description: Design, implement, and maintain multi-agent orchestration workflows using LangGraph. Use when building StateGraphs, configuring supervisor-worker loops, adding pure reducers, implementing checkpointing, or preventing execution loops.
---

# Agentic Workflows & Multi-Agent Orchestration

This skill guides the design, implementation, and testing of multi-agent state machines, subgraphs, and bounded execution loops for JobFalcon using **LangGraph**.

---

## 1. When to Use This Skill

- Implementing or updating the compiled `StateGraph` and its subgraphs.
- Creating or editing agent nodes (`supervisor`, `profile_worker`, `market_worker`, `discovery_worker`, `ranking_worker`, `explanation_worker`).
- Designing state channels, typed state dictionaries (`TypedDict`), and pure binary reducers.
- Implementing dynamic parallel worker dispatch using LangGraph's `Send` API.
- Configuring durable state checkpointing with `AsyncPostgresSaver`.
- Managing context window budgets, token compaction, and bounded evaluator-optimizer retry loops.

---

## 2. Core Orchestration Architecture

JobFalcon uses a **Hierarchical Supervisor Pattern** with **Map-Reduce Fan-Out** and **Bounded Evaluator-Optimizer Loops**:

```
                  ┌───────────────────────────────┐
                  │ S1: Recommendation            │
                  │     Orchestrator (Supervisor) │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │ (Send)                 │ (Send)                 │ (Send)
         ▼                        ▼                        ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│ S2: Profile Agent │    │ S3: Market Agent  │    │ S4: Discovery     │
│     (Subgraph)    │    │     (Subgraph)    │    │     (Subgraph)    │
└────────┬──────────┘    └────────┬──────────┘    └────────┬──────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │ (Sync Barrier)
                                  ▼
                  ┌───────────────────────────────┐
                  │ S5: Deterministic Eligibility │ (Pure Python Gate)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ S6: Recommendation & Ranking  │ (Deterministic MCDA)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ S7: Explanation Synthesis     │ (LLM Grounded)
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │ S8: Critique Gate             │ (Evaluator Loop)
                  └───────────────┬───────────────┘
                                  │ Passes audit
                                  ▼
                  ┌───────────────────────────────┐
                  │ S9: Terminal Success          │
                  └───────────────────────────────┘
```

---

## 3. Workflow: Implementing an Agentic Workflow

### Step 1: Define Typed State Contract & Reducers
Every accumulating channel must have an explicit pure binary reducer to prevent `InvalidUpdateError` during parallel execution.

> [!NOTE] Target Implementation Pattern
> The state definitions and reducer patterns below illustrate target implementations for Phase 3. Loop limits, retry budgets, and expansion levels represent baseline parameters from Section 3, pending empirical calibration (see [`docs/UNRESOLVED_DECISIONS.md`](file:///Users/nomanahmad/WorkSpace/Projects/JobFalcon/docs/UNRESOLVED_DECISIONS.md)).

```python
from typing import Annotated, Dict, List, Literal, Optional
import operator
from typing_extensions import TypedDict

def deduplicate_opportunities_reducer(
    existing: List[PolymorphicOpportunity], 
    incoming: List[PolymorphicOpportunity]
) -> List[PolymorphicOpportunity]:
    """Pure reducer merging parallel discovery outputs while deduplicating by ID and MinHash."""
    seen_ids = {opp.opportunity_id for opp in existing}
    seen_hashes = {opp.minhash_signature_hex for opp in existing}
    merged = list(existing)
    for opp in incoming:
        if opp.opportunity_id not in seen_ids and opp.minhash_signature_hex not in seen_hashes:
            merged.append(opp)
            seen_ids.add(opp.opportunity_id)
            seen_hashes.add(opp.minhash_signature_hex)
    return merged

class RecommendationGraphState(TypedDict):
    thread_id: str
    user_id: str
    raw_artifact_uris: List[str]  # Claim-check pointers to storage; never raw document bytes
    candidate_profile: Optional[CandidateCareerProfile]
    market_reports: Annotated[List[MarketIntelligenceReport], operator.add]
    discovered_opportunities: Annotated[List[PolymorphicOpportunity], deduplicate_opportunities_reducer]
    eligible_opportunity_ids: List[str]
    ineligible_audit_log: Annotated[List[Dict[str, str]], operator.add]
    ranked_recommendations: List[RankedOpportunityRecommendation]
    explanations: List[ExplanationPayload]
    orchestrator_loop_count: int
    discovery_expansion_level: int
    executed_query_hashes: Annotated[List[str], operator.add]
    critique_feedback: Optional[str]
    terminal_status: Literal["IN_PROGRESS", "SUCCESS", "DEGRADED_PARTIAL", "ABORTED_ERROR"]
```

### Step 2: Implement Worker Subgraphs with Namespace Isolation
- Compile each worker agent as an isolated subgraph with its own `checkpoint_ns` (e.g., `checkpoint_ns="market_agent:uuid"`).
- Intermediate tool calls and reasoning scratchpads remain confined to the subgraph's `PrivateState`.
- Return only validated, schema-compliant outputs to the parent `RecommendationGraphState`.

### Step 3: Implement Context Budgeting & Compaction
- Hard-cap worker context budgets at **16,000 tokens** per node.
- Deploy a pre-model middleware hook: If context exceeds 75% of budget, trigger compaction using `RemoveMessage` to tombstone obsolete tool calls and replace them with a concise structured summary.

### Step 4: Enforce Loop Termination Invariants
Protect the state graph against runaway cycles through three orthogonal mechanisms:
1. **Monotonically Incrementing Counter**: `orchestrator_loop_count` incremented on every return edge; evaluated against `MAX_ORCHESTRATOR_LOOPS = 4`.
2. **Cryptographic Action Signature Set**: SHA-256 hashes of executed tool inputs stored in `executed_query_hashes`; blocks identical repeated queries within the same thread.
3. **Hard Runtime Recursion Limit**: Set `recursion_limit = 25` in `RunnableConfig`.

### Step 5: Implement Evaluator-Optimizer Self-Correction
- **Intra-Node Repair**: When schema validation fails or Gate 4 (Explanation Faithfulness) flags ungrounded claims, inject a synthetic diagnostic `ToolMessage` with the exact validation error diff, and set `temperature = 0.0`.
- **Retry Budget**: Allow up to 2 retries (`max_retries = 2`). If still failing, fall back to the **Deterministic Template Fallback** (pure Python text synthesis).

---

## 4. Orchestration Constraints & Anti-Patterns

- ❌ **DO NOT** execute hard eligibility or mathematical scoring inside an LLM prompt. Always route through deterministic nodes.
- ❌ **DO NOT** mutate state in place. Nodes must return partial dictionaries containing only updated keys.
- ❌ **DO NOT** place raw binary files, full resume texts, or large scraped HTML in graph state. Use claim-check URI pointers.
- ❌ **DO NOT** permit unbounded retry loops. Every cyclic edge must be guarded by a counter and action signature check.
- ❌ **DO NOT** mix user-facing activity messages with operational debug traces. Emit structured user events separately.

---

## 5. Verification Checklist

Before finalizing an agentic workflow:
- [ ] Every accumulating state channel has a validated pure reducer function.
- [ ] All worker subgraphs operate in isolated namespaces (`checkpoint_ns`).
- [ ] Context window budget compaction is active with a 16k token ceiling.
- [ ] Loop guards (`orchestrator_loop_count <= 4`, `executed_query_hashes`, `recursion_limit = 25`) are verified.
- [ ] Evaluator-optimizer loops gracefully fall back to deterministic templates on retry exhaustion.
- [ ] Unit tests verify workflow state transitions using mocked tool inputs and responses.

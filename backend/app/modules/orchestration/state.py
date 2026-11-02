from __future__ import annotations

import operator
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict

from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.discovery import (
    ConnectorHealthReport,
    DiscoverySearchQuery,
    RoleMappingTarget,
)
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.orchestration import (
    AdaptationEvent,
    CoverageAssessment,
    SearchStrategy,
    TerminationReason,
    WorkflowStage,
    WorkflowTimelineEvent,
)
from app.schemas.profile import CandidateCareerProfile
from app.schemas.ranking import RankingResponse


def deduplicate_opportunities_reducer(
    existing: list[PolymorphicOpportunity],
    incoming: list[PolymorphicOpportunity],
) -> list[PolymorphicOpportunity]:
    """Pure binary reducer merging opportunity streams with ID and MinHash deduplication."""
    if not existing:
        return list(incoming)
    if not incoming:
        return list(existing)

    seen_ids = {opp.opportunity_id for opp in existing}
    seen_hashes = {opp.minhash_signature_hex for opp in existing if opp.minhash_signature_hex}
    merged = list(existing)

    for opp in incoming:
        if opp.opportunity_id in seen_ids:
            continue
        if opp.minhash_signature_hex and opp.minhash_signature_hex in seen_hashes:
            continue

        merged.append(opp)
        seen_ids.add(opp.opportunity_id)
        if opp.minhash_signature_hex:
            seen_hashes.add(opp.minhash_signature_hex)

    return merged


class AdaptiveDiscoveryGraphState(TypedDict, total=False):
    """LangGraph TypedDict state contract for the Adaptive Discovery Agentic Workflow.

    Guarantees:
    - Pure binary reducers on accumulating channels to prevent update collisions.
    - Strict decoupling between orchestrator workflow state and deterministic services.
    - Full execution traceability without exposing hidden chain-of-thought or model scratchpads.
    """

    # Identifiers & Candidate Context
    workflow_id: str
    candidate_id: str
    candidate_profile: Optional[CandidateCareerProfile]

    # Strategy & Role Mapping
    target_roles: list[RoleMappingTarget]
    adjacent_roles: list[RoleMappingTarget]
    connector_health: list[ConnectorHealthReport]
    search_strategy: Optional[SearchStrategy]
    pending_queries: list[DiscoverySearchQuery]

    # Discovery & Evaluation Streams (accumulated via pure reducers)
    accumulated_raw: Annotated[list[PolymorphicOpportunity], deduplicate_opportunities_reducer]
    canonical_opportunities: list[PolymorphicOpportunity]
    duplicate_clusters: dict[str, OpportunityCluster]
    duplicate_records: list[DuplicateRecord]
    eligibility_results: list[EligibilityResult]

    # Adaptive Loop State & Budgets
    iteration: int
    tool_call_count: int
    target_coverage_goal: int
    max_iterations: int
    max_tool_calls: int
    deduplication_threshold: float
    simulate_failure_connector: Optional[str]
    force_adaptive_gap_for_testing: bool

    # Assessment, Adaptation & History
    coverage_assessment: Optional[CoverageAssessment]
    adaptation_history: Annotated[list[AdaptationEvent], operator.add]
    executed_query_hashes: Annotated[list[str], operator.add]

    # Ranking, Persistence & Results
    rank_recommendations: bool
    weight_profile_name: str
    persist_to_repository: bool
    recommendations: Optional[RankingResponse]

    # Execution Observability & Safety
    timeline_events: Annotated[list[WorkflowTimelineEvent], operator.add]
    rejections_by_code: dict[str, int]
    sources_queried: list[str]
    current_stage: WorkflowStage
    termination_reason: TerminationReason
    error_message: Optional[str]
    execution_metadata: dict[str, Any]

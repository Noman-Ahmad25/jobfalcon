from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.discovery import (
    ConnectorHealthReport,
    DiscoverySearchQuery,
    RoleMappingTarget,
)
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile
from app.schemas.ranking import RankingResponse


class WorkflowStage(str, Enum):
    """Discrete lifecycle stages of the agentic discovery workflow."""

    INITIALIZING = "INITIALIZING"
    STRATEGY_FORMULATION = "STRATEGY_FORMULATION"
    SEARCHING = "SEARCHING"
    EVALUATING = "EVALUATING"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    ADAPTING = "ADAPTING"
    RANKING = "RANKING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TerminationReason(str, Enum):
    """Authoritative reason why the adaptive discovery loop stopped."""

    COVERAGE_SATISFIED = "COVERAGE_SATISFIED"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    ALL_SOURCES_EXHAUSTED = "ALL_SOURCES_EXHAUSTED"
    ABORTED_ERROR = "ABORTED_ERROR"


class WorkflowTimelineEvent(BaseModel):
    """Observable execution event emitted during agent orchestration."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event observation timestamp.",
    )
    stage: WorkflowStage = Field(
        ...,
        description="Workflow stage during which this event occurred.",
    )
    event_type: str = Field(
        ...,
        description="Event classifier (e.g., 'STRATEGY_PLANNED', 'TOOL_INVOKED', 'GAP_DETECTED').",
    )
    summary: str = Field(
        ...,
        description="Human-readable description of what action the agent took or discovered.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured telemetry payload.",
    )


class SearchStrategy(BaseModel):
    """LLM-guided or heuristic search strategy formulated for the candidate."""

    strategy_summary: str = Field(
        ...,
        description="High-level reasoning explaining role focus and source prioritization.",
    )
    target_role_priorities: list[str] = Field(
        default_factory=list,
        description="Ordered list of primary role titles to discover first.",
    )
    target_coverage_goal: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Target minimum number of qualified/eligible opportunities to discover.",
    )
    selected_connector_ids: list[str] = Field(
        default_factory=list,
        description="Connectors selected based on geographic authorization and role fit.",
    )
    initial_queries: list[DiscoverySearchQuery] = Field(
        default_factory=list,
        description="Concrete parameterized search queries for the initial search burst.",
    )


class CoverageAssessment(BaseModel):
    """Evaluation of discovery results against target coverage goals."""

    is_coverage_sufficient: bool = Field(
        ...,
        description="True if target roles have met or exceeded the coverage threshold.",
    )
    total_eligible_canonical: int = Field(
        default=0,
        ge=0,
        description="Number of canonical opportunities passing deterministic eligibility.",
    )
    target_role_coverage: dict[str, int] = Field(
        default_factory=dict,
        description="Count of eligible canonical opportunities per role title.",
    )
    identified_gaps: list[str] = Field(
        default_factory=list,
        description="Specific deficit areas (e.g., 'Target role Backend Engineer has only 1 listing').",
    )
    recommended_action: str = Field(
        ...,
        description="Action directive (e.g., 'STOP', 'QUERY_RELAXATION', 'ADJACENT_EXPANSION').",
    )


class AdaptationEvent(BaseModel):
    """Adaptive adjustment formulated by the agent when a coverage gap is detected."""

    iteration: int = Field(
        ...,
        ge=1,
        description="Workflow iteration when this adaptation was triggered.",
    )
    identified_gap: str = Field(
        ...,
        description="Deficit or failure description that triggered the shift.",
    )
    adaptation_type: str = Field(
        ...,
        description="Classification: 'QUERY_RELAXATION', 'ADJACENT_EXPANSION', 'CONNECTOR_REPLACEMENT'.",
    )
    action_summary: str = Field(
        ...,
        description="Explanation of the adjusted query or alternate source selected.",
    )
    new_query: DiscoverySearchQuery = Field(
        ...,
        description="Adjusted query formulated to fill the identified gap.",
    )
    target_connector_ids: list[str] = Field(
        default_factory=list,
        description="Specific connector(s) routed for this adaptive query.",
    )


class AdaptiveDiscoveryRequest(BaseModel):
    """Payload requesting an end-to-end adaptive agent discovery run."""

    candidate_profile: Optional[CandidateCareerProfile] = Field(
        default=None,
        description="Candidate profile. If omitted, user_id will be loaded from repository.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier to look up candidate profile.",
    )
    target_coverage_goal: int = Field(
        default=3,
        ge=1,
        le=15,
        description="Minimum number of eligible opportunities desired before stopping.",
    )
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Upper bound on search-evaluate-adapt loop iterations.",
    )
    max_tool_calls: int = Field(
        default=10,
        ge=2,
        le=20,
        description="Upper bound on total tool executions allowed.",
    )
    connector_ids: Optional[list[str]] = Field(
        default=None,
        description="Optional connector whitelist. None enables all available.",
    )
    deduplication_threshold: float = Field(
        default=0.85,
        ge=0.50,
        le=1.00,
        description="Jaccard similarity threshold for MinHash LSH deduplication.",
    )
    simulate_failure_connector: Optional[str] = Field(
        default=None,
        description="Optional connector ID to artificially simulate a failure for resilience testing.",
    )
    force_adaptive_gap_for_testing: bool = Field(
        default=False,
        description="Artificially marks initial round as deficient to verify adaptation in tests.",
    )
    persist_to_repository: bool = Field(
        default=True,
        description="Whether to persist canonical listings and clusters to the database.",
    )
    enable_live_discovery: bool = Field(
        default=False,
        description="Whether to query live external career APIs and job aggregators.",
    )
    rank_recommendations: bool = Field(
        default=True,
        description="Whether to execute multi-dimensional ranking and fit scoring on discovered opportunities.",
    )
    weight_profile_name: str = Field(
        default="DEFAULT",
        description="Weight profile name for candidate-job ranking (e.g. DEFAULT, EARLY_CAREER, EXPERIENCED).",
    )


class AdaptiveDiscoveryResponse(BaseModel):
    """Structured response detailing the full agent discovery execution and results."""

    workflow_id: str = Field(
        ...,
        description="Unique identifier for this orchestration execution.",
    )
    candidate_id: str = Field(
        ...,
        description="Candidate user ID.",
    )
    termination_reason: TerminationReason = Field(
        ...,
        description="Authoritative reason why discovery concluded.",
    )
    iterations_completed: int = Field(
        ...,
        ge=1,
        description="Total adaptive loop iterations executed.",
    )
    total_tool_calls: int = Field(
        ...,
        ge=0,
        description="Total tool executions across the workflow.",
    )
    search_strategy: SearchStrategy = Field(
        ...,
        description="Initial search strategy formulated by the agent.",
    )
    coverage_assessment: CoverageAssessment = Field(
        ...,
        description="Final coverage evaluation across target and adjacent roles.",
    )
    adaptation_history: list[AdaptationEvent] = Field(
        default_factory=list,
        description="Sequential list of adaptive shifts made by the agent.",
    )
    total_discovered_raw: int = Field(
        ...,
        description="Total raw opportunities retrieved across all sources and iterations.",
    )
    canonical_count: int = Field(
        ...,
        description="Number of distinct opportunities after MinHash LSH deduplication.",
    )
    duplicate_count: int = Field(
        ...,
        description="Number of syndicated duplicate opportunities clustered.",
    )
    eligible_count: int = Field(
        ...,
        description="Canonical opportunities passing deterministic eligibility.",
    )
    uncertain_count: int = Field(
        ...,
        description="Canonical opportunities passing with missing-information caveats.",
    )
    ineligible_count: int = Field(
        ...,
        description="Opportunities failing hard eligibility rules.",
    )
    canonical_opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Deduplicated canonical opportunities.",
    )
    eligible_opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Opportunities verified as eligible for the candidate.",
    )
    duplicate_clusters: dict[str, OpportunityCluster] = Field(
        default_factory=dict,
        description="Duplicate cluster linkages with original source URLs preserved.",
    )
    duplicate_records: list[DuplicateRecord] = Field(
        default_factory=list,
        description="Specific pair-wise duplicate similarity records.",
    )
    eligibility_results: list[EligibilityResult] = Field(
        default_factory=list,
        description="Deterministic audit logs and constraint check outcomes.",
    )
    connector_health: list[ConnectorHealthReport] = Field(
        default_factory=list,
        description="Operational health status of connectors during workflow.",
    )
    recommendations: Optional[RankingResponse] = Field(
        default=None,
        description="Multi-dimensional evidence-grounded candidate-job rankings and fit scores.",
    )
    timeline_events: list[WorkflowTimelineEvent] = Field(
        default_factory=list,
        description="Observable timeline of workflow stages and actions.",
    )
    execution_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry metadata (duration_ms, query hashes, token budgets).",
    )

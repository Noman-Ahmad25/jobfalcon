from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteOpportunityRepository,
    SQLiteRecommendationRepository,
)
from app.modules.discovery.connectors import (
    BaseDiscoveryConnector,
    get_default_connectors,
)
from app.modules.orchestration.graph import AdaptiveDiscoveryGraphBuilder
from app.modules.orchestration.state import AdaptiveDiscoveryGraphState
from app.modules.profiling.llm_client import BaseLLMClient
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    AdaptiveDiscoveryResponse,
    CoverageAssessment,
    SearchStrategy,
    TerminationReason,
)

logger = logging.getLogger(__name__)


class AdaptiveDiscoveryWorkflow:
    """Agentic Orchestration State Machine for adaptive opportunity discovery powered by LangGraph.

    Orchestrates the multi-agent workflow via a compiled LangGraph StateGraph:
    1. Supervisor Node: Profile resolution, connector health check, role mapping, and strategy formulation.
    2. Discovery Worker: Concurrent multi-source search burst with query hashing and error isolation.
    3. Evaluation Worker: Cross-source MinHash LSH deduplication and deterministic eligibility gating.
    4. Coverage Decision Node: Goal coverage evaluation, loop budgeting, and adaptive shifts.
    5. Ranking Worker: Deterministic 6-dimensional candidate-job fit scoring.
    6. Finalizing Worker: Idempotent repository persistence and execution telemetry compilation.

    Architectural Invariants:
    - LangGraph serves as the single source of truth for workflow state, routing, and loops.
    - Hard eligibility, deduplication, and ranking calculations remain strictly deterministic.
    - State channels use pure binary reducers to avoid update conflicts.
    - Zero exposure of private model reasoning or chain-of-thought in execution traces.
    """

    def __init__(
        self,
        opp_repo: Optional[OpportunityRepository] = None,
        cluster_repo: Optional[DuplicateClusterRepository] = None,
        profile_repo: Optional[CandidateProfileRepository] = None,
        rec_repo: Optional[RecommendationRepository] = None,
        connectors: Optional[list[BaseDiscoveryConnector]] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ) -> None:
        self.opp_repo = opp_repo or SQLiteOpportunityRepository()
        self.cluster_repo = cluster_repo or SQLiteDuplicateClusterRepository()
        self.profile_repo = profile_repo or SQLiteCandidateProfileRepository()
        self.rec_repo = rec_repo or SQLiteRecommendationRepository()
        self._raw_connectors = connectors
        self.llm_client = llm_client

    async def run(self, request: AdaptiveDiscoveryRequest) -> AdaptiveDiscoveryResponse:
        """Executes the compiled LangGraph agent orchestration workflow."""
        t0 = time.perf_counter()
        workflow_id = f"wf-{uuid.uuid4().hex[:12]}"

        # 1. Resolve active connectors
        mock_mode = not request.enable_live_discovery
        active_connectors = self._raw_connectors or get_default_connectors(
            mock_mode=mock_mode,
            simulate_failure_connector=request.simulate_failure_connector,
        )
        if request.connector_ids:
            allowed = set(request.connector_ids)
            active_connectors = [c for c in active_connectors if c.connector_id in allowed]

        # 2. Build the LangGraph StateGraph instance
        graph_builder = AdaptiveDiscoveryGraphBuilder(
            opp_repo=self.opp_repo,
            cluster_repo=self.cluster_repo,
            profile_repo=self.profile_repo,
            rec_repo=self.rec_repo,
            connectors=active_connectors,
            llm_client=self.llm_client,
        )
        compiled_graph = graph_builder.build_graph()

        # 3. Construct initial LangGraph state
        initial_state: AdaptiveDiscoveryGraphState = {
            "workflow_id": workflow_id,
            "candidate_id": request.user_id or (
                request.candidate_profile.user_id if request.candidate_profile else ""
            ),
            "candidate_profile": request.candidate_profile,
            "iteration": 1,
            "tool_call_count": 0,
            "target_coverage_goal": request.target_coverage_goal,
            "max_iterations": request.max_iterations,
            "max_tool_calls": request.max_tool_calls,
            "deduplication_threshold": request.deduplication_threshold,
            "simulate_failure_connector": request.simulate_failure_connector,
            "force_adaptive_gap_for_testing": request.force_adaptive_gap_for_testing,
            "rank_recommendations": request.rank_recommendations,
            "weight_profile_name": request.weight_profile_name,
            "persist_to_repository": request.persist_to_repository,
            "accumulated_raw": [],
            "canonical_opportunities": [],
            "duplicate_clusters": {},
            "duplicate_records": [],
            "eligibility_results": [],
            "timeline_events": [],
            "executed_query_hashes": [],
            "adaptation_history": [],
        }

        # 4. Invoke the LangGraph StateGraph
        final_state: AdaptiveDiscoveryGraphState = await compiled_graph.ainvoke(initial_state)

        # Handle profile resolution failures
        if final_state.get("termination_reason") == TerminationReason.ABORTED_ERROR:
            err = final_state.get("error_message") or "Candidate profile could not be resolved."
            raise ValueError(f"{err} Please provide candidate_profile or valid user_id.")

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # 5. Extract and compute final response metrics
        accumulated_raw = final_state.get("accumulated_raw", [])
        canonical_opportunities = final_state.get("canonical_opportunities", [])
        duplicate_clusters = final_state.get("duplicate_clusters", {})
        duplicate_records = final_state.get("duplicate_records", [])
        eligibility_results = final_state.get("eligibility_results", [])
        timeline_events = final_state.get("timeline_events", [])
        adaptation_history = final_state.get("adaptation_history", [])
        executed_query_hashes = final_state.get("executed_query_hashes", [])
        connector_health = final_state.get("connector_health", [])
        recommendations = final_state.get("recommendations")
        termination_reason = final_state.get("termination_reason", TerminationReason.MAX_ITERATIONS_REACHED)

        # Categorize eligible vs uncertain vs ineligible
        elig_map = {r.opportunity_id: r for r in eligibility_results}
        eligible_canonical = []
        eligible_count = 0
        uncertain_count = 0
        ineligible_count = 0

        for opp in canonical_opportunities:
            res = elig_map.get(opp.opportunity_id)
            if res and res.is_eligible:
                eligible_canonical.append(opp)
                if res.status.value == "ELIGIBLE_WITH_UNCERTAINTY":
                    uncertain_count += 1
                else:
                    eligible_count += 1
            else:
                ineligible_count += 1

        # Count actual search iterations executed
        iteration_events = [
            e for e in timeline_events if "ITERATION_" in e.event_type and "_STARTED" in e.event_type
        ]
        iterations_completed = max(len(iteration_events), 1)

        # Ensure valid SearchStrategy and CoverageAssessment fallbacks
        strategy = final_state.get("search_strategy") or SearchStrategy(
            strategy_summary="Standard targeted discovery plan.",
            target_role_priorities=[],
            target_coverage_goal=request.target_coverage_goal,
            selected_connector_ids=[c.connector_id for c in active_connectors],
            initial_queries=[],
        )

        coverage_assessment = final_state.get("coverage_assessment") or CoverageAssessment(
            is_coverage_sufficient=False,
            total_eligible_canonical=eligible_count,
            target_role_coverage={},
            identified_gaps=["No opportunities retrieved"],
            recommended_action="STOP",
        )

        candidate_id = final_state.get("candidate_id") or (
            final_state["candidate_profile"].user_id if final_state.get("candidate_profile") else "unknown"
        )

        return AdaptiveDiscoveryResponse(
            workflow_id=final_state.get("workflow_id", workflow_id),
            candidate_id=candidate_id,
            termination_reason=termination_reason,
            iterations_completed=iterations_completed,
            total_tool_calls=final_state.get("tool_call_count", 0),
            search_strategy=strategy,
            coverage_assessment=coverage_assessment,
            adaptation_history=adaptation_history,
            total_discovered_raw=len(accumulated_raw),
            canonical_count=len(canonical_opportunities),
            duplicate_count=max(len(accumulated_raw) - len(canonical_opportunities), 0),
            eligible_count=eligible_count,
            uncertain_count=uncertain_count,
            ineligible_count=ineligible_count,
            canonical_opportunities=canonical_opportunities,
            eligible_opportunities=eligible_canonical,
            duplicate_clusters=duplicate_clusters,
            duplicate_records=duplicate_records,
            eligibility_results=eligibility_results,
            connector_health=connector_health,
            recommendations=recommendations,
            timeline_events=timeline_events,
            execution_metadata={
                "duration_ms": elapsed_ms,
                "executed_query_hashes": executed_query_hashes,
                "max_iterations_configured": request.max_iterations,
                "max_tool_calls_configured": request.max_tool_calls,
                "deduplication_threshold": request.deduplication_threshold,
                "orchestrator_engine": "langgraph-stategraph-v1",
            },
        )

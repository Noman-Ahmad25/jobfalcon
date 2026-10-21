from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
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
from app.modules.orchestration.agent import (
    DiscoveryAgentDecisionMaker,
    compute_query_hash,
)
from app.modules.orchestration.tools import (
    DeduplicationArgs,
    DeduplicationTool,
    DeterministicEligibilityArgs,
    DeterministicEligibilityTool,
    OpportunitySearchArgs,
    OpportunitySearchTool,
    PersistenceArgs,
    PersistenceTool,
    ProfileRetrievalArgs,
    ProfileRetrievalTool,
    RankingArgs,
    RankingTool,
    RoleMappingArgs,
    RoleMappingTool,
)
from app.modules.profiling.llm_client import BaseLLMClient
from app.schemas.common import CareerPathRelationship
from app.schemas.discovery import ConnectorHealthReport, ConnectorStatus, DiscoverySearchQuery
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.orchestration import (
    AdaptationEvent,
    AdaptiveDiscoveryRequest,
    AdaptiveDiscoveryResponse,
    CoverageAssessment,
    SearchStrategy,
    TerminationReason,
    WorkflowStage,
    WorkflowTimelineEvent,
)
from app.schemas.profile import CandidateCareerProfile

logger = logging.getLogger(__name__)


class AdaptiveDiscoveryWorkflow:
    """Agentic Orchestration State Machine for adaptive opportunity discovery.

    Orchestrates:
    1. Candidate Profile & Evidence Retrieval.
    2. Taxonomic Skill-to-Role Mapping.
    3. LLM Strategy Formulation with connector routing.
    4. Bounded Adaptive Search Loop with Coverage Gap Analysis.
    5. Cross-Source MinHash LSH Deduplication.
    6. Authoritative Deterministic Eligibility Gating.
    7. Idempotent Repository Persistence.
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

        # Initialize controlled tools
        self.profile_tool = ProfileRetrievalTool(self.profile_repo)
        self.role_mapping_tool = RoleMappingTool()
        self.dedup_tool = DeduplicationTool()
        self.eligibility_tool = DeterministicEligibilityTool()
        self.persistence_tool = PersistenceTool(self.opp_repo, self.cluster_repo)
        self.ranking_tool = RankingTool()
        self.agent_decision_maker = DiscoveryAgentDecisionMaker(self.llm_client)

    async def run(self, request: AdaptiveDiscoveryRequest) -> AdaptiveDiscoveryResponse:
        t0 = time.perf_counter()
        workflow_id = f"wf-{uuid.uuid4().hex[:12]}"
        timeline: list[WorkflowTimelineEvent] = []

        # Helper to emit observable timeline events
        def emit_event(stage: WorkflowStage, event_type: str, summary: str, details: dict | None = None) -> None:
            evt = WorkflowTimelineEvent(
                timestamp=datetime.now(timezone.utc),
                stage=stage,
                event_type=event_type,
                summary=summary,
                details=details or {},
            )
            timeline.append(evt)
            logger.info("[%s][%s] %s", stage.value, event_type, summary)

        emit_event(WorkflowStage.INITIALIZING, "WORKFLOW_INITIALIZED", f"Initialized adaptive discovery run {workflow_id}.")

        # 1. Resolve candidate profile
        profile = request.candidate_profile
        if profile is None and request.user_id:
            res = self.profile_tool.execute(ProfileRetrievalArgs(user_id=request.user_id))
            if res.success and res.data:
                profile = res.data
                emit_event(WorkflowStage.INITIALIZING, "PROFILE_RESOLVED", f"Loaded candidate profile for {request.user_id}.", res.provenance)

        if profile is None:
            emit_event(WorkflowStage.FAILED, "PROFILE_NOT_FOUND", "Candidate profile could not be resolved.")
            raise ValueError("Candidate profile could not be resolved. Please provide candidate_profile or valid user_id.")

        # 2. Check health of available connectors
        mock_mode = not request.enable_live_discovery
        active_connectors = self._raw_connectors or get_default_connectors(
            mock_mode=mock_mode,
            simulate_failure_connector=request.simulate_failure_connector,
        )
        if request.connector_ids:
            allowed = set(request.connector_ids)
            active_connectors = [c for c in active_connectors if c.connector_id in allowed]

        search_tool = OpportunitySearchTool(connectors=active_connectors)

        connector_health: list[ConnectorHealthReport] = []
        for c in active_connectors:
            try:
                h = await c.check_health()
                connector_health.append(h)
            except Exception as exc:
                logger.warning("Connector %s health check failed: %s", c.connector_id, exc)

        emit_event(
            WorkflowStage.INITIALIZING,
            "CONNECTORS_INSPECTED",
            f"Inspected {len(connector_health)} discovery sources ({sum(1 for h in connector_health if h.status != ConnectorStatus.ERROR)} operational).",
            {"connectors": [h.connector_id for h in connector_health]},
        )

        # 3. Strategy Formulation & Skill-to-Role Mapping
        emit_event(WorkflowStage.STRATEGY_FORMULATION, "ROLE_MAPPING_STARTED", "Mapping candidate skills to O*NET career families.")
        rm_res = self.role_mapping_tool.execute(RoleMappingArgs(profile=profile))
        all_targets = rm_res.data or []
        target_roles = [t for t in all_targets if t.relationship_type == CareerPathRelationship.TARGET]
        adjacent_roles = [t for t in all_targets if t.relationship_type == CareerPathRelationship.ADJACENT]

        emit_event(
            WorkflowStage.STRATEGY_FORMULATION,
            "ROLE_MAPPING_COMPLETED",
            f"Mapped {len(target_roles)} target role(s) and {len(adjacent_roles)} adjacent role(s).",
            {"target_roles": [t.role_title for t in target_roles], "adjacent_roles": [t.role_title for t in adjacent_roles]},
        )

        strategy = self.agent_decision_maker.formulate_initial_strategy(
            profile=profile,
            target_roles=target_roles,
            adjacent_roles=adjacent_roles,
            available_connectors=connector_health,
            target_coverage_goal=request.target_coverage_goal,
            simulate_failure_connector=request.simulate_failure_connector,
        )

        emit_event(
            WorkflowStage.STRATEGY_FORMULATION,
            "STRATEGY_FORMULATED",
            strategy.strategy_summary,
            {
                "target_role_priorities": strategy.target_role_priorities,
                "target_coverage_goal": strategy.target_coverage_goal,
                "selected_connector_ids": strategy.selected_connector_ids,
            },
        )

        # 4. Bounded Adaptive Search Loop
        iteration = 1
        tool_call_count = 1  # role mapping tool
        executed_query_hashes: set[str] = set()
        accumulated_raw: list[PolymorphicOpportunity] = []
        canonical_opportunities: list[PolymorphicOpportunity] = []
        duplicate_clusters: dict = {}
        duplicate_records: list = []
        eligibility_results: list = []
        adaptation_history: list[AdaptationEvent] = []
        termination_reason = TerminationReason.MAX_ITERATIONS_REACHED
        latest_assessment: Optional[CoverageAssessment] = None

        pending_queries: list[DiscoverySearchQuery] = list(strategy.initial_queries)

        while iteration <= request.max_iterations and tool_call_count < request.max_tool_calls:
            emit_event(
                WorkflowStage.SEARCHING,
                f"ITERATION_{iteration}_STARTED",
                f"Beginning discovery iteration {iteration}/{request.max_iterations} with {len(pending_queries)} query plan(s).",
            )

            # A. Execute searches
            newly_fetched = 0
            for query in pending_queries:
                for cid in strategy.selected_connector_ids:
                    if tool_call_count >= request.max_tool_calls:
                        break

                    q_hash = compute_query_hash(query.query_string, cid)
                    if q_hash in executed_query_hashes:
                        continue
                    executed_query_hashes.add(q_hash)

                    tool_res = await search_tool.execute(
                        OpportunitySearchArgs(
                            connector_id=cid,
                            query=query,
                            limit=4,
                        )
                    )
                    tool_call_count += 1

                    if tool_res.success and tool_res.data:
                        found = len(tool_res.data.opportunities)
                        newly_fetched += found
                        accumulated_raw.extend(tool_res.data.opportunities)
                        emit_event(
                            WorkflowStage.SEARCHING,
                            "TOOL_INVOKED",
                            f"Queried '{cid}' for '{query.query_string}' -> Found {found} opportunity listing(s).",
                            {"connector_id": cid, "latency_ms": tool_res.latency_ms, "raw_count": found},
                        )
                    else:
                        emit_event(
                            WorkflowStage.SEARCHING,
                            "TOOL_FAILED",
                            f"Connector '{cid}' reported failure or timeout: {tool_res.error_message}",
                            {"connector_id": cid, "error": tool_res.error_message},
                        )

            # B. Cross-source MinHash LSH Deduplication
            emit_event(WorkflowStage.EVALUATING, "DEDUPLICATION_STARTED", f"Deduplicating {len(accumulated_raw)} total retrieved listings across sources.")
            dedup_res = self.dedup_tool.execute(
                DeduplicationArgs(
                    opportunities=accumulated_raw,
                    threshold=request.deduplication_threshold,
                )
            )
            tool_call_count += 1
            if dedup_res.success and dedup_res.data:
                canonical_opportunities = dedup_res.data.canonical_opportunities
                duplicate_clusters = dedup_res.data.clusters
                duplicate_records = dedup_res.data.duplicate_records
                emit_event(
                    WorkflowStage.EVALUATING,
                    "DEDUPLICATION_COMPLETED",
                    f"MinHash LSH yielded {dedup_res.data.canonical_count} canonical opportunities and {dedup_res.data.duplicate_count} syndicated duplicates.",
                    dedup_res.provenance,
                )

            # C. Deterministic Eligibility Gating
            emit_event(WorkflowStage.EVALUATING, "ELIGIBILITY_STARTED", f"Evaluating {len(canonical_opportunities)} canonical listings against deterministic constraints.")
            elig_res = self.eligibility_tool.execute(
                DeterministicEligibilityArgs(
                    candidate_profile=profile,
                    canonical_opportunities=canonical_opportunities,
                )
            )
            tool_call_count += 1
            if elig_res.success and elig_res.data:
                eligibility_results = elig_res.data
                emit_event(
                    WorkflowStage.EVALUATING,
                    "ELIGIBILITY_COMPLETED",
                    f"Deterministic engine verified {elig_res.provenance.get('eligible_count', 0)} eligible opportunities ({elig_res.provenance.get('ineligible_count', 0)} disqualified).",
                    elig_res.provenance,
                )

            # D. Coverage Assessment & Gap Analysis
            emit_event(WorkflowStage.GAP_ANALYSIS, "GAP_ANALYSIS_STARTED", f"Analyzing coverage against target goal of {strategy.target_coverage_goal} listings.")
            force_gap = request.force_adaptive_gap_for_testing and (iteration == 1)
            assessment, adaptation = self.agent_decision_maker.assess_coverage_and_decide_adaptation(
                profile=profile,
                strategy=strategy,
                target_roles=target_roles,
                adjacent_roles=adjacent_roles,
                canonical_opportunities=canonical_opportunities,
                eligibility_results=eligibility_results,
                iteration=iteration,
                max_iterations=request.max_iterations,
                executed_query_hashes=executed_query_hashes,
                force_gap_for_testing=force_gap,
            )
            latest_assessment = assessment

            if assessment.is_coverage_sufficient:
                termination_reason = TerminationReason.COVERAGE_SATISFIED
                emit_event(
                    WorkflowStage.GAP_ANALYSIS,
                    "COVERAGE_SATISFIED",
                    f"Coverage goal satisfied with {assessment.total_eligible_canonical} eligible canonical listings.",
                    {"target_role_coverage": assessment.target_role_coverage},
                )
                break

            if tool_call_count >= request.max_tool_calls:
                termination_reason = TerminationReason.BUDGET_EXHAUSTED
                emit_event(
                    WorkflowStage.GAP_ANALYSIS,
                    "BUDGET_EXHAUSTED",
                    f"Tool execution budget exhausted ({tool_call_count}/{request.max_tool_calls} calls).",
                )
                break

            if iteration >= request.max_iterations:
                termination_reason = TerminationReason.MAX_ITERATIONS_REACHED
                emit_event(
                    WorkflowStage.GAP_ANALYSIS,
                    "MAX_ITERATIONS_REACHED",
                    f"Reached maximum configured search loop iterations ({request.max_iterations}).",
                )
                break

            # E. Adaptive Shift
            if adaptation:
                adaptation_history.append(adaptation)
                pending_queries = [adaptation.new_query]
                emit_event(
                    WorkflowStage.ADAPTING,
                    "ADAPTATION_TRIGGERED",
                    f"Adaptive Shift ({adaptation.adaptation_type}): {adaptation.action_summary}",
                    {
                        "iteration": iteration,
                        "identified_gap": adaptation.identified_gap,
                        "new_query": adaptation.new_query.query_string,
                    },
                )

            iteration += 1

        # 5. Multi-Dimensional Fit Scoring & Candidate-Job Ranking
        recommendations_data = None
        if request.rank_recommendations and canonical_opportunities:
            emit_event(
                WorkflowStage.RANKING,
                "RANKING_STARTED",
                "Evaluating multi-dimensional candidate-job fit scores for discovered opportunities.",
                {
                    "weight_profile": request.weight_profile_name,
                    "candidates_to_rank": len(canonical_opportunities),
                },
            )
            rank_tool_res = self.ranking_tool.execute(
                RankingArgs(
                    candidate_profile=profile,
                    opportunities=canonical_opportunities,
                    eligibility_results=eligibility_results,
                    weight_profile_name=request.weight_profile_name,
                )
            )
            tool_call_count += 1
            if rank_tool_res.success and rank_tool_res.data:
                recommendations_data = rank_tool_res.data
                if request.persist_to_repository and self.rec_repo:
                    try:
                        self.rec_repo.save_evaluation(recommendations_data)
                    except Exception as rec_save_err:
                        logger.warning("Could not persist ranking evaluation: %s", rec_save_err)

                top_score = (
                    recommendations_data.ranked_recommendations[0].overall_fit_score
                    if recommendations_data.ranked_recommendations
                    else 0.0
                )
                emit_event(
                    WorkflowStage.RANKING,
                    "RANKING_COMPLETED",
                    f"Ranked {recommendations_data.total_eligible_ranked} eligible opportunities (top fit score: {top_score:.2f}).",
                    {
                        "total_ranked": recommendations_data.total_eligible_ranked,
                        "total_ineligible": recommendations_data.total_ineligible_excluded,
                        "top_fit_score": top_score,
                    },
                )

        # 6. Finalize & Persist
        emit_event(WorkflowStage.FINALIZING, "FINALIZING_STARTED", "Persisting discovered listings and compiling final telemetry.")
        if request.persist_to_repository and accumulated_raw:
            persist_res = self.persistence_tool.execute(
                PersistenceArgs(
                    opportunities=accumulated_raw,
                    clusters=duplicate_clusters,
                )
            )
            tool_call_count += 1
            if persist_res.success:
                emit_event(
                    WorkflowStage.FINALIZING,
                    "PERSISTENCE_COMPLETED",
                    f"Persisted listings to repository ({persist_res.provenance.get('new_opportunities', 0)} new).",
                    persist_res.provenance,
                )

        emit_event(
            WorkflowStage.COMPLETED,
            "WORKFLOW_COMPLETED",
            f"Adaptive discovery workflow completed with status '{termination_reason.value}' across {iteration} iteration(s).",
        )

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Categorize final eligible vs uncertain vs ineligible
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

        # If no assessment generated (e.g. empty), construct default
        if latest_assessment is None:
            latest_assessment = CoverageAssessment(
                is_coverage_sufficient=False,
                total_eligible_canonical=0,
                target_role_coverage={},
                identified_gaps=["No opportunities retrieved"],
                recommended_action="STOP",
            )

        return AdaptiveDiscoveryResponse(
            workflow_id=workflow_id,
            candidate_id=profile.user_id,
            termination_reason=termination_reason,
            iterations_completed=iteration,
            total_tool_calls=tool_call_count,
            search_strategy=strategy,
            coverage_assessment=latest_assessment,
            adaptation_history=adaptation_history,
            total_discovered_raw=len(accumulated_raw),
            canonical_count=len(canonical_opportunities),
            duplicate_count=len(accumulated_raw) - len(canonical_opportunities),
            eligible_count=eligible_count,
            uncertain_count=uncertain_count,
            ineligible_count=ineligible_count,
            canonical_opportunities=canonical_opportunities,
            eligible_opportunities=eligible_canonical,
            duplicate_clusters=duplicate_clusters,
            duplicate_records=duplicate_records,
            eligibility_results=eligibility_results,
            connector_health=connector_health,
            recommendations=recommendations_data,
            timeline_events=timeline,
            execution_metadata={
                "duration_ms": elapsed_ms,
                "executed_query_hashes": list(executed_query_hashes),
                "max_iterations_configured": request.max_iterations,
                "max_tool_calls_configured": request.max_tool_calls,
                "deduplication_threshold": request.deduplication_threshold,
            },
        )

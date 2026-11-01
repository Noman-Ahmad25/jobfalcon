from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.modules.discovery.connectors import BaseDiscoveryConnector
from app.modules.orchestration.agent import (
    DiscoveryAgentDecisionMaker,
    compute_query_hash,
)
from app.modules.orchestration.state import AdaptiveDiscoveryGraphState
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
    CoverageAssessment,
    SearchStrategy,
    TerminationReason,
    WorkflowStage,
    WorkflowTimelineEvent,
)

logger = logging.getLogger(__name__)


def _make_timeline_event(
    stage: WorkflowStage,
    event_type: str,
    summary: str,
    details: Optional[dict[str, Any]] = None,
) -> WorkflowTimelineEvent:
    """Helper creating standardized, safe execution telemetry events."""
    return WorkflowTimelineEvent(
        timestamp=datetime.now(timezone.utc),
        stage=stage,
        event_type=event_type,
        summary=summary,
        details=details or {},
    )


class AdaptiveDiscoveryGraphBuilder:
    """Constructs and compiles the LangGraph StateGraph for JobFalcon's agentic discovery workflow.

    Architectural Invariants:
    1. LangGraph orchestrates workflow flow, loop bounds, and routing decisions.
    2. Deterministic services (deduplication, eligibility, ranking, persistence) remain 100% deterministic.
    3. State transitions use immutable dict updates and pure binary reducers.
    4. Observable execution telemetry emits safe, structured events without private CoT.
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
        self.opp_repo = opp_repo
        self.cluster_repo = cluster_repo
        self.profile_repo = profile_repo
        self.rec_repo = rec_repo
        self.connectors = connectors or []
        self.llm_client = llm_client

        # Controlled Tools
        self.profile_tool = ProfileRetrievalTool(self.profile_repo) if self.profile_repo else None
        self.role_mapping_tool = RoleMappingTool()
        self.dedup_tool = DeduplicationTool()
        self.eligibility_tool = DeterministicEligibilityTool()
        self.ranking_tool = RankingTool()
        self.persistence_tool = (
            PersistenceTool(self.opp_repo, self.cluster_repo)
            if self.opp_repo and self.cluster_repo
            else None
        )
        self.agent_decision_maker = DiscoveryAgentDecisionMaker(self.llm_client)

    # ==========================================================================
    # Graph Nodes
    # ==========================================================================

    async def supervisor_node(
        self, state: AdaptiveDiscoveryGraphState
    ) -> dict[str, Any]:
        """Supervisor Node: Resolves candidate profile, checks connector health, maps roles, and plans strategy."""
        events: list[WorkflowTimelineEvent] = []
        workflow_id = state.get("workflow_id", "wf-unknown")

        events.append(
            _make_timeline_event(
                WorkflowStage.INITIALIZING,
                "WORKFLOW_INITIALIZED",
                f"Initialized LangGraph adaptive discovery run {workflow_id}.",
            )
        )

        profile = state.get("candidate_profile")
        if profile is None and state.get("candidate_id") and self.profile_tool:
            res = self.profile_tool.execute(
                ProfileRetrievalArgs(user_id=state["candidate_id"])
            )
            if res.success and res.data:
                profile = res.data
                events.append(
                    _make_timeline_event(
                        WorkflowStage.INITIALIZING,
                        "PROFILE_RESOLVED",
                        f"Loaded candidate profile for {state['candidate_id']}.",
                        res.provenance,
                    )
                )

        if profile is None:
            events.append(
                _make_timeline_event(
                    WorkflowStage.FAILED,
                    "PROFILE_NOT_FOUND",
                    "Candidate profile could not be resolved.",
                )
            )
            return {
                "current_stage": WorkflowStage.FAILED,
                "termination_reason": TerminationReason.ABORTED_ERROR,
                "error_message": "Candidate profile could not be resolved.",
                "timeline_events": events,
            }

        # Check health of active connectors
        connector_health: list[ConnectorHealthReport] = []
        for c in self.connectors:
            try:
                h = await c.check_health()
                connector_health.append(h)
            except Exception as exc:
                logger.warning("Connector %s health check failed: %s", c.connector_id, exc)

        events.append(
            _make_timeline_event(
                WorkflowStage.INITIALIZING,
                "CONNECTORS_INSPECTED",
                f"Inspected {len(connector_health)} discovery sources ({sum(1 for h in connector_health if h.status != ConnectorStatus.ERROR)} operational).",
                {"connectors": [h.connector_id for h in connector_health]},
            )
        )

        # Role Mapping
        events.append(
            _make_timeline_event(
                WorkflowStage.STRATEGY_FORMULATION,
                "ROLE_MAPPING_STARTED",
                "Mapping candidate skills to O*NET career families.",
            )
        )
        rm_res = self.role_mapping_tool.execute(RoleMappingArgs(profile=profile))
        all_targets = rm_res.data or []
        target_roles = [t for t in all_targets if t.relationship_type == CareerPathRelationship.TARGET]
        adjacent_roles = [t for t in all_targets if t.relationship_type == CareerPathRelationship.ADJACENT]

        events.append(
            _make_timeline_event(
                WorkflowStage.STRATEGY_FORMULATION,
                "ROLE_MAPPING_COMPLETED",
                f"Mapped {len(target_roles)} target role(s) and {len(adjacent_roles)} adjacent role(s).",
                {
                    "target_roles": [t.role_title for t in target_roles],
                    "adjacent_roles": [t.role_title for t in adjacent_roles],
                },
            )
        )

        # Strategy Formulation
        strategy = self.agent_decision_maker.formulate_initial_strategy(
            profile=profile,
            target_roles=target_roles,
            adjacent_roles=adjacent_roles,
            available_connectors=connector_health,
            target_coverage_goal=state.get("target_coverage_goal", 3),
            simulate_failure_connector=state.get("simulate_failure_connector"),
        )

        events.append(
            _make_timeline_event(
                WorkflowStage.STRATEGY_FORMULATION,
                "STRATEGY_FORMULATED",
                strategy.strategy_summary,
                {
                    "target_role_priorities": strategy.target_role_priorities,
                    "target_coverage_goal": strategy.target_coverage_goal,
                    "selected_connector_ids": strategy.selected_connector_ids,
                },
            )
        )

        return {
            "candidate_profile": profile,
            "target_roles": target_roles,
            "adjacent_roles": adjacent_roles,
            "connector_health": connector_health,
            "search_strategy": strategy,
            "pending_queries": list(strategy.initial_queries),
            "tool_call_count": state.get("tool_call_count", 0) + 1,
            "current_stage": WorkflowStage.STRATEGY_FORMULATION,
            "timeline_events": events,
        }

    async def discovery_worker_node(
        self, state: AdaptiveDiscoveryGraphState
    ) -> dict[str, Any]:
        """Discovery Worker: Concurrently queries approved sources with query hashing and partial failure isolation."""
        events: list[WorkflowTimelineEvent] = []
        iteration = state.get("iteration", 1)
        max_iterations = state.get("max_iterations", 3)
        pending_queries = state.get("pending_queries", [])
        strategy = state.get("search_strategy")
        selected_cids = strategy.selected_connector_ids if strategy else [c.connector_id for c in self.connectors]

        events.append(
            _make_timeline_event(
                WorkflowStage.SEARCHING,
                f"ITERATION_{iteration}_STARTED",
                f"Beginning discovery iteration {iteration}/{max_iterations} with {len(pending_queries)} query plan(s).",
            )
        )

        search_tool = OpportunitySearchTool(connectors=self.connectors)
        newly_fetched: list[PolymorphicOpportunity] = []
        new_hashes: list[str] = []
        tool_call_count = state.get("tool_call_count", 0)
        max_tool_calls = state.get("max_tool_calls", 10)
        existing_hashes = set(state.get("executed_query_hashes", []))

        for query in pending_queries:
            for cid in selected_cids:
                if tool_call_count >= max_tool_calls:
                    break

                q_hash = compute_query_hash(query.query_string, cid)
                if q_hash in existing_hashes:
                    continue
                existing_hashes.add(q_hash)
                new_hashes.append(q_hash)

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
                    newly_fetched.extend(tool_res.data.opportunities)
                    events.append(
                        _make_timeline_event(
                            WorkflowStage.SEARCHING,
                            "TOOL_INVOKED",
                            f"Queried '{cid}' for '{query.query_string}' -> Found {found} opportunity listing(s).",
                            {
                                "connector_id": cid,
                                "latency_ms": tool_res.latency_ms,
                                "raw_count": found,
                            },
                        )
                    )
                else:
                    events.append(
                        _make_timeline_event(
                            WorkflowStage.SEARCHING,
                            "TOOL_FAILED",
                            f"Connector '{cid}' reported failure or timeout: {tool_res.error_message}",
                            {"connector_id": cid, "error": tool_res.error_message},
                        )
                    )

        return {
            "accumulated_raw": newly_fetched,
            "executed_query_hashes": new_hashes,
            "tool_call_count": tool_call_count,
            "current_stage": WorkflowStage.SEARCHING,
            "timeline_events": events,
        }

    async def evaluation_worker_node(
        self, state: AdaptiveDiscoveryGraphState
    ) -> dict[str, Any]:
        """Evaluation Worker: Deterministic cross-source MinHash deduplication and pure Python eligibility gating."""
        events: list[WorkflowTimelineEvent] = []
        accumulated_raw = state.get("accumulated_raw", [])
        tool_call_count = state.get("tool_call_count", 0)

        # 1. Deduplication
        events.append(
            _make_timeline_event(
                WorkflowStage.EVALUATING,
                "DEDUPLICATION_STARTED",
                f"Deduplicating {len(accumulated_raw)} total retrieved listings across sources.",
            )
        )
        dedup_res = self.dedup_tool.execute(
            DeduplicationArgs(
                opportunities=accumulated_raw,
                threshold=state.get("deduplication_threshold", 0.85),
            )
        )
        tool_call_count += 1
        canonical_opportunities = dedup_res.data.canonical_opportunities if dedup_res.data else []
        duplicate_clusters = dedup_res.data.clusters if dedup_res.data else {}
        duplicate_records = dedup_res.data.duplicate_records if dedup_res.data else []

        if dedup_res.success and dedup_res.data:
            events.append(
                _make_timeline_event(
                    WorkflowStage.EVALUATING,
                    "DEDUPLICATION_COMPLETED",
                    f"MinHash LSH yielded {dedup_res.data.canonical_count} canonical opportunities and {dedup_res.data.duplicate_count} syndicated duplicates.",
                    dedup_res.provenance,
                )
            )

        # 2. Deterministic Eligibility Gating
        events.append(
            _make_timeline_event(
                WorkflowStage.EVALUATING,
                "ELIGIBILITY_STARTED",
                f"Evaluating {len(canonical_opportunities)} canonical listings against deterministic constraints.",
            )
        )
        profile = state.get("candidate_profile")
        elig_res = self.eligibility_tool.execute(
            DeterministicEligibilityArgs(
                candidate_profile=profile,
                canonical_opportunities=canonical_opportunities,
            )
        )
        tool_call_count += 1
        eligibility_results = elig_res.data or []

        if elig_res.success:
            events.append(
                _make_timeline_event(
                    WorkflowStage.EVALUATING,
                    "ELIGIBILITY_COMPLETED",
                    f"Deterministic engine verified {elig_res.provenance.get('eligible_count', 0)} eligible opportunities ({elig_res.provenance.get('ineligible_count', 0)} disqualified).",
                    elig_res.provenance,
                )
            )

        return {
            "canonical_opportunities": canonical_opportunities,
            "duplicate_clusters": duplicate_clusters,
            "duplicate_records": duplicate_records,
            "eligibility_results": eligibility_results,
            "tool_call_count": tool_call_count,
            "current_stage": WorkflowStage.EVALUATING,
            "timeline_events": events,
        }

    async def coverage_decision_node(
        self, state: AdaptiveDiscoveryGraphState
    ) -> dict[str, Any]:
        """Coverage Decision Node: Evaluates coverage against target goals, enforces loop bounds, and formulates adaptations."""
        events: list[WorkflowTimelineEvent] = []
        iteration = state.get("iteration", 1)
        max_iterations = state.get("max_iterations", 3)
        tool_call_count = state.get("tool_call_count", 0)
        max_tool_calls = state.get("max_tool_calls", 10)
        strategy = state.get("search_strategy")
        profile = state.get("candidate_profile")
        canonical_opportunities = state.get("canonical_opportunities", [])
        eligibility_results = state.get("eligibility_results", [])
        target_roles = state.get("target_roles", [])
        adjacent_roles = state.get("adjacent_roles", [])
        goal = state.get("target_coverage_goal", 3)

        events.append(
            _make_timeline_event(
                WorkflowStage.GAP_ANALYSIS,
                "GAP_ANALYSIS_STARTED",
                f"Analyzing coverage against target goal of {goal} listings.",
            )
        )

        force_gap = state.get("force_adaptive_gap_for_testing", False) and (iteration == 1)
        executed_hashes = set(state.get("executed_query_hashes", []))

        assessment, adaptation = self.agent_decision_maker.assess_coverage_and_decide_adaptation(
            profile=profile,
            strategy=strategy,
            target_roles=target_roles,
            adjacent_roles=adjacent_roles,
            canonical_opportunities=canonical_opportunities,
            eligibility_results=eligibility_results,
            iteration=iteration,
            max_iterations=max_iterations,
            executed_query_hashes=executed_hashes,
            force_gap_for_testing=force_gap,
        )

        # Check termination conditions in priority order
        if assessment.is_coverage_sufficient:
            events.append(
                _make_timeline_event(
                    WorkflowStage.GAP_ANALYSIS,
                    "COVERAGE_SATISFIED",
                    f"Coverage goal satisfied with {assessment.total_eligible_canonical} eligible canonical listings.",
                    {"target_role_coverage": assessment.target_role_coverage},
                )
            )
            return {
                "coverage_assessment": assessment,
                "termination_reason": TerminationReason.COVERAGE_SATISFIED,
                "current_stage": WorkflowStage.GAP_ANALYSIS,
                "timeline_events": events,
            }

        if tool_call_count >= max_tool_calls:
            events.append(
                _make_timeline_event(
                    WorkflowStage.GAP_ANALYSIS,
                    "BUDGET_EXHAUSTED",
                    f"Tool execution budget exhausted ({tool_call_count}/{max_tool_calls} calls).",
                )
            )
            return {
                "coverage_assessment": assessment,
                "termination_reason": TerminationReason.BUDGET_EXHAUSTED,
                "current_stage": WorkflowStage.GAP_ANALYSIS,
                "timeline_events": events,
            }

        if iteration >= max_iterations:
            events.append(
                _make_timeline_event(
                    WorkflowStage.GAP_ANALYSIS,
                    "MAX_ITERATIONS_REACHED",
                    f"Reached maximum configured search loop iterations ({max_iterations}).",
                )
            )
            return {
                "coverage_assessment": assessment,
                "termination_reason": TerminationReason.MAX_ITERATIONS_REACHED,
                "current_stage": WorkflowStage.GAP_ANALYSIS,
                "timeline_events": events,
            }

        # Adaptive Shift Triggered: Prepare next loop iteration
        adaptation_list: list[AdaptationEvent] = []
        pending_queries: list[DiscoverySearchQuery] = []
        if adaptation:
            adaptation_list.append(adaptation)
            pending_queries = [adaptation.new_query]
            events.append(
                _make_timeline_event(
                    WorkflowStage.ADAPTING,
                    "ADAPTATION_TRIGGERED",
                    f"Adaptive Shift ({adaptation.adaptation_type}): {adaptation.action_summary}",
                    {
                        "iteration": iteration,
                        "identified_gap": adaptation.identified_gap,
                        "new_query": adaptation.new_query.query_string,
                    },
                )
            )

        return {
            "coverage_assessment": assessment,
            "adaptation_history": adaptation_list,
            "pending_queries": pending_queries,
            "iteration": iteration + 1,
            "current_stage": WorkflowStage.ADAPTING,
            "timeline_events": events,
        }

    async def ranking_worker_node(
        self, state: AdaptiveDiscoveryGraphState
    ) -> dict[str, Any]:
        """Ranking Worker: Evaluates 6-dimensional candidate-job fit scores deterministically."""
        events: list[WorkflowTimelineEvent] = []
        canonical_opportunities = state.get("canonical_opportunities", [])
        eligibility_results = state.get("eligibility_results", [])
        profile = state.get("candidate_profile")
        rank_recommendations = state.get("rank_recommendations", True)
        weight_profile = state.get("weight_profile_name", "DEFAULT")
        tool_call_count = state.get("tool_call_count", 0)
        recommendations_data = None

        if rank_recommendations and canonical_opportunities and profile:
            events.append(
                _make_timeline_event(
                    WorkflowStage.RANKING,
                    "RANKING_STARTED",
                    "Evaluating multi-dimensional candidate-job fit scores for discovered opportunities.",
                    {
                        "weight_profile": weight_profile,
                        "candidates_to_rank": len(canonical_opportunities),
                    },
                )
            )
            rank_tool_res = self.ranking_tool.execute(
                RankingArgs(
                    candidate_profile=profile,
                    opportunities=canonical_opportunities,
                    eligibility_results=eligibility_results,
                    weight_profile_name=weight_profile,
                )
            )
            tool_call_count += 1
            if rank_tool_res.success and rank_tool_res.data:
                recommendations_data = rank_tool_res.data
                if state.get("persist_to_repository", False) and self.rec_repo:
                    try:
                        self.rec_repo.save_evaluation(recommendations_data)
                    except Exception as rec_save_err:
                        logger.warning("Could not persist ranking evaluation: %s", rec_save_err)

                top_score = (
                    recommendations_data.ranked_recommendations[0].overall_fit_score
                    if recommendations_data.ranked_recommendations
                    else 0.0
                )
                events.append(
                    _make_timeline_event(
                        WorkflowStage.RANKING,
                        "RANKING_COMPLETED",
                        f"Ranked {recommendations_data.total_eligible_ranked} eligible opportunities (top fit score: {top_score:.2f}).",
                        {
                            "total_ranked": recommendations_data.total_eligible_ranked,
                            "total_ineligible": recommendations_data.total_ineligible_excluded,
                            "top_fit_score": top_score,
                        },
                    )
                )

        return {
            "recommendations": recommendations_data,
            "tool_call_count": tool_call_count,
            "current_stage": WorkflowStage.RANKING,
            "timeline_events": events,
        }

    async def finalizing_worker_node(
        self, state: AdaptiveDiscoveryGraphState
    ) -> dict[str, Any]:
        """Finalizing Worker: Persists opportunities, compiles telemetry, and concludes execution."""
        events: list[WorkflowTimelineEvent] = []
        tool_call_count = state.get("tool_call_count", 0)
        accumulated_raw = state.get("accumulated_raw", [])
        duplicate_clusters = state.get("duplicate_clusters", {})
        persist_to_repo = state.get("persist_to_repository", False)
        iteration = state.get("iteration", 1)
        termination_reason = state.get("termination_reason", TerminationReason.MAX_ITERATIONS_REACHED)

        events.append(
            _make_timeline_event(
                WorkflowStage.FINALIZING,
                "FINALIZING_STARTED",
                "Persisting discovered listings and compiling final telemetry.",
            )
        )

        if persist_to_repo and accumulated_raw and self.persistence_tool:
            persist_res = self.persistence_tool.execute(
                PersistenceArgs(
                    opportunities=accumulated_raw,
                    clusters=duplicate_clusters,
                )
            )
            tool_call_count += 1
            if persist_res.success:
                events.append(
                    _make_timeline_event(
                        WorkflowStage.FINALIZING,
                        "PERSISTENCE_COMPLETED",
                        f"Persisted listings to repository ({persist_res.provenance.get('new_opportunities', 0)} new).",
                        persist_res.provenance,
                    )
                )

        events.append(
            _make_timeline_event(
                WorkflowStage.COMPLETED,
                "WORKFLOW_COMPLETED",
                f"Adaptive discovery workflow completed with status '{termination_reason.value}' across {iteration} iteration(s).",
            )
        )

        return {
            "tool_call_count": tool_call_count,
            "current_stage": WorkflowStage.COMPLETED,
            "timeline_events": events,
        }

    # ==========================================================================
    # Conditional Routing Logic
    # ==========================================================================

    @staticmethod
    def route_after_coverage(state: AdaptiveDiscoveryGraphState) -> str:
        """Determines whether to execute an adaptive search loop or proceed to ranking."""
        termination_reason = state.get("termination_reason")
        if termination_reason in (
            TerminationReason.COVERAGE_SATISFIED,
            TerminationReason.BUDGET_EXHAUSTED,
            TerminationReason.MAX_ITERATIONS_REACHED,
            TerminationReason.ALL_SOURCES_EXHAUSTED,
            TerminationReason.ABORTED_ERROR,
        ):
            return "ranking_worker"

        # Check loop guards
        iteration = state.get("iteration", 1)
        max_iterations = state.get("max_iterations", 3)
        tool_call_count = state.get("tool_call_count", 0)
        max_tool_calls = state.get("max_tool_calls", 10)
        pending_queries = state.get("pending_queries", [])

        if iteration <= max_iterations and tool_call_count < max_tool_calls and pending_queries:
            return "discovery_worker"

        return "ranking_worker"

    @staticmethod
    def route_after_supervisor(state: AdaptiveDiscoveryGraphState) -> str:
        """Routes to discovery worker unless profile resolution aborted the workflow."""
        if state.get("termination_reason") == TerminationReason.ABORTED_ERROR:
            return "finalizing_worker"
        return "discovery_worker"

    # ==========================================================================
    # Graph Compilation
    # ==========================================================================

    def build_graph(self) -> Any:
        """Assembles and compiles the StateGraph with specialized nodes and conditional routing."""
        graph = StateGraph(AdaptiveDiscoveryGraphState)

        # 1. Register specialized worker nodes
        graph.add_node("supervisor", self.supervisor_node)
        graph.add_node("discovery_worker", self.discovery_worker_node)
        graph.add_node("evaluation_worker", self.evaluation_worker_node)
        graph.add_node("coverage_decision", self.coverage_decision_node)
        graph.add_node("ranking_worker", self.ranking_worker_node)
        graph.add_node("finalizing_worker", self.finalizing_worker_node)

        # 2. Add edges and conditional branches
        graph.add_edge(START, "supervisor")

        graph.add_conditional_edges(
            "supervisor",
            self.route_after_supervisor,
            {
                "discovery_worker": "discovery_worker",
                "finalizing_worker": "finalizing_worker",
            },
        )

        graph.add_edge("discovery_worker", "evaluation_worker")
        graph.add_edge("evaluation_worker", "coverage_decision")

        # Bounded adaptive cycle or exit to ranking
        graph.add_conditional_edges(
            "coverage_decision",
            self.route_after_coverage,
            {
                "discovery_worker": "discovery_worker",
                "ranking_worker": "ranking_worker",
            },
        )

        graph.add_edge("ranking_worker", "finalizing_worker")
        graph.add_edge("finalizing_worker", END)

        return graph.compile()

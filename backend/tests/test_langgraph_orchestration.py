from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pytest
from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
    InMemoryRecommendationRepository,
)
from app.modules.discovery.connectors.mcp.connector import JobSpyMCPConnector
from app.modules.discovery.connectors.web_search import WebSearchConnector
from app.modules.orchestration.agent import DiscoveryAgentDecisionMaker
from app.modules.orchestration.graph import AdaptiveDiscoveryGraphBuilder
from app.modules.orchestration.state import (
    AdaptiveDiscoveryGraphState,
    deduplicate_opportunities_reducer,
)
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
from app.modules.profiling.llm_client import MockLLMClient
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import DiscoverySearchQuery
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    TerminationReason,
    WorkflowStage,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def candidate_fixture() -> CandidateCareerProfile:
    """Standard candidate profile fixture for LangGraph orchestration testing."""
    ev = EvidenceRecord(
        evidence_id="ev_lg_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Architected scalable Python backend services using FastAPI, PostgreSQL, and Docker.",
        verifiability_weight=0.90,
    )
    skills = [
        AssessedSkill(
            canonical_skill_id="esco:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.92,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:fastapi",
            skill_name="FastAPI",
            proficiency_score=8.0,
            confidence_score=0.88,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:postgresql",
            skill_name="PostgreSQL",
            proficiency_score=7.8,
            confidence_score=0.85,
            evidence_records=[ev],
        ),
    ]
    target = CareerPathNode(
        occupation_code="15-1252.00",
        title="Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
    )
    eligibility = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        total_full_time_experience_months=36,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, US"],
    )
    return CandidateCareerProfile(
        user_id="usr_langgraph_test_01",
        profile_version=1,
        assessed_skills=skills,
        target_career_paths=[target],
        adjacent_career_paths=[],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.90,
    )


# ==============================================================================
# 1. Graph Compilation & Assembly Tests
# ==============================================================================


def test_langgraph_compilation() -> None:
    """Verifies that the StateGraph compiles cleanly with expected nodes and conditional branches."""
    builder = AdaptiveDiscoveryGraphBuilder()
    compiled_graph = builder.build_graph()

    assert compiled_graph is not None
    # Verify node names in compiled graph
    node_names = set(compiled_graph.nodes.keys())
    assert "supervisor" in node_names
    assert "discovery_worker" in node_names
    assert "evaluation_worker" in node_names
    assert "coverage_decision" in node_names
    assert "ranking_worker" in node_names
    assert "finalizing_worker" in node_names


def test_pure_deduplication_reducer() -> None:
    """Verifies the pure binary reducer merges opportunity lists without mutations or duplicates."""
    from app.modules.discovery.connectors.base import create_normalized_opportunity

    now = datetime.now(timezone.utc)
    opp1 = create_normalized_opportunity(
        title="Software Engineer",
        company_name="Alpha Co",
        description="Engineering role description at Alpha Co.",
        source_url="https://example.com/1",
        source_system="ats_direct",
        category=OpportunityCategory.FULL_TIME_JOB,
        posted_at=now,
    )
    opp2 = create_normalized_opportunity(
        title="Backend Engineer",
        company_name="Beta Co",
        description="Backend role description at Beta Co.",
        source_url="https://example.com/2",
        source_system="ats_direct",
        category=OpportunityCategory.FULL_TIME_JOB,
        posted_at=now,
    )
    # Clone with duplicate ID
    opp1_dup_id = opp1.model_copy(update={"source_url": "https://example.com/1_dup"})
    # Clone with duplicate MinHash
    opp2_dup_hash = opp2.model_copy(update={"opportunity_id": "opp_diff_id"})

    merged = deduplicate_opportunities_reducer([opp1], [opp2, opp1_dup_id, opp2_dup_hash])
    assert len(merged) == 2
    assert {opp.opportunity_id for opp in merged} == {opp1.opportunity_id, opp2.opportunity_id}


# ==============================================================================
# 2. Conditional Routing & Loop Guard Tests
# ==============================================================================


def test_conditional_routing_coverage_satisfied() -> None:
    """When coverage is satisfied, router directs to ranking worker."""
    state: AdaptiveDiscoveryGraphState = {
        "termination_reason": TerminationReason.COVERAGE_SATISFIED,
        "iteration": 1,
        "max_iterations": 3,
        "tool_call_count": 3,
        "max_tool_calls": 10,
        "pending_queries": [
            DiscoverySearchQuery(
                query_id="q1",
                role_title="Dev",
                query_string="Dev",
                category=OpportunityCategory.FULL_TIME_JOB,
            )
        ],
    }
    next_node = AdaptiveDiscoveryGraphBuilder.route_after_coverage(state)
    assert next_node == "ranking_worker"


def test_conditional_routing_budget_exhausted() -> None:
    """When tool call budget is exhausted, router directs to ranking worker."""
    state: AdaptiveDiscoveryGraphState = {
        "termination_reason": TerminationReason.BUDGET_EXHAUSTED,
        "iteration": 1,
        "max_iterations": 3,
        "tool_call_count": 10,
        "max_tool_calls": 10,
    }
    next_node = AdaptiveDiscoveryGraphBuilder.route_after_coverage(state)
    assert next_node == "ranking_worker"


def test_conditional_routing_adaptive_loop() -> None:
    """When a gap exists and budgets permit, router loops back to discovery worker."""
    state: AdaptiveDiscoveryGraphState = {
        "iteration": 2,
        "max_iterations": 3,
        "tool_call_count": 4,
        "max_tool_calls": 10,
        "pending_queries": [
            DiscoverySearchQuery(
                query_id="q_adapt",
                role_title="Backend",
                query_string="Python",
                category=OpportunityCategory.FULL_TIME_JOB,
            )
        ],
    }
    next_node = AdaptiveDiscoveryGraphBuilder.route_after_coverage(state)
    assert next_node == "discovery_worker"


# ==============================================================================
# 3. End-to-End LangGraph Orchestration & Deterministic Guarantees
# ==============================================================================


def test_langgraph_workflow_end_to_end(candidate_fixture: CandidateCareerProfile) -> None:
    """Tests full end-to-end execution of the compiled LangGraph workflow."""

    async def _run() -> None:
        profile_repo = InMemoryCandidateProfileRepository()
        opp_repo = InMemoryOpportunityRepository()
        cluster_repo = InMemoryDuplicateClusterRepository()
        rec_repo = InMemoryRecommendationRepository()

        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=opp_repo,
            cluster_repo=cluster_repo,
            profile_repo=profile_repo,
            rec_repo=rec_repo,
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_fixture,
            target_coverage_goal=2,
            max_iterations=2,
            max_tool_calls=8,
            persist_to_repository=True,
            rank_recommendations=True,
        )

        response = await workflow.run(request)

        # 1. State and termination checks
        assert response.workflow_id.startswith("wf-")
        assert response.candidate_id == candidate_fixture.user_id
        assert response.termination_reason == TerminationReason.COVERAGE_SATISFIED
        assert response.iterations_completed >= 1
        assert response.total_tool_calls > 0

        # 2. Deterministic Results
        assert response.canonical_count > 0
        assert len(response.eligible_opportunities) >= 2
        assert response.recommendations is not None
        assert response.recommendations.total_eligible_ranked > 0

        # 3. Observability Timeline Check
        stages = [e.stage for e in response.timeline_events]
        assert WorkflowStage.INITIALIZING in stages
        assert WorkflowStage.STRATEGY_FORMULATION in stages
        assert WorkflowStage.SEARCHING in stages
        assert WorkflowStage.EVALUATING in stages
        assert WorkflowStage.RANKING in stages
        assert WorkflowStage.FINALIZING in stages
        assert WorkflowStage.COMPLETED in stages

        # 4. Engine Metadata confirms LangGraph execution
        assert response.execution_metadata.get("orchestrator_engine") == "langgraph-stategraph-v1"

    asyncio.run(_run())


def test_langgraph_multi_source_web_search_and_mcp(candidate_fixture: CandidateCareerProfile) -> None:
    """Verifies that WebSearch and JobSpy MCP connectors execute concurrently through the LangGraph workflow."""

    async def _run() -> None:
        mcp_connector = JobSpyMCPConnector(mock_mode=True, artificial_latency_ms=1.0)
        web_connector = WebSearchConnector(mock_mode=True, artificial_latency_ms=1.0)

        workflow = AdaptiveDiscoveryWorkflow(
            connectors=[mcp_connector, web_connector],
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_fixture,
            connector_ids=["jobspy_mcp", "web_search"],
            target_coverage_goal=2,
            max_iterations=1,
            max_tool_calls=6,
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)

        assert response.total_discovered_raw > 0
        assert response.canonical_count > 0

        # Verify both connectors were invoked and reported in health
        cids = {h.connector_id for h in response.connector_health}
        assert "jobspy_mcp" in cids
        assert "web_search" in cids

    asyncio.run(_run())


def test_langgraph_safe_execution_trace_no_private_cot(candidate_fixture: CandidateCareerProfile) -> None:
    """Verifies that execution traces strictly contain safe, structured events without private CoT."""

    async def _run() -> None:
        workflow = AdaptiveDiscoveryWorkflow()

        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_fixture,
            target_coverage_goal=2,
            max_iterations=1,
            persist_to_repository=False,
        )

        response = await workflow.run(request)

        # Inspect all timeline events
        for event in response.timeline_events:
            assert isinstance(event.stage, WorkflowStage)
            assert isinstance(event.event_type, str)
            assert len(event.summary) > 0

            # Ensure no private CoT leakage
            summary_lower = event.summary.lower()
            assert "chain-of-thought" not in summary_lower
            assert "secret" not in summary_lower
            assert "private reasoning" not in summary_lower

    asyncio.run(_run())

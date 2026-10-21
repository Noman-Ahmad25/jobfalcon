from __future__ import annotations

import asyncio
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
)
from app.main import app
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
    RoleMappingArgs,
    RoleMappingTool,
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


def _make_candidate_fixture(
    user_id: str = "agent-test-user",
    is_student: bool = False,
    experience_months: int = 18,
    country_codes: list[str] | None = None,
) -> CandidateCareerProfile:
    """Creates a deterministic candidate profile fixture."""
    ev = EvidenceRecord(
        evidence_id="ev-agent-1",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Engineered distributed backend microservices using Python, FastAPI, and PostgreSQL.",
        observed_at="2026-01-10T10:00:00Z",
        verifiability_weight=0.90,
    )
    skills = [
        AssessedSkill(
            canonical_skill_id="esco:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.90,
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
            proficiency_score=7.5,
            confidence_score=0.85,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:docker",
            skill_name="Docker",
            proficiency_score=7.0,
            confidence_score=0.80,
            evidence_records=[ev],
        ),
    ]

    target = CareerPathNode(
        occupation_code="15-1252.00",
        title="Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
        missing_core_skill_ids=[],
    )

    eligibility = CandidateEligibilityProfile(
        authorized_country_codes=country_codes or ["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=is_student,
        expected_graduation_date=date(2026, 6, 1) if is_student else None,
        total_full_time_experience_months=experience_months,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, US"],
    )

    return CandidateCareerProfile(
        user_id=user_id,
        profile_version=1,
        assessed_skills=skills,
        current_career_path=None,
        target_career_paths=[target],
        adjacent_career_paths=[],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.88,
    )


def test_controlled_agent_tools_execution() -> None:
    """Verifies that all controlled agent tools validate inputs, track latency, and handle errors."""
    profile = _make_candidate_fixture()
    profile_repo = InMemoryCandidateProfileRepository()
    profile_repo.save(profile)
    opp_repo = InMemoryOpportunityRepository()
    cluster_repo = InMemoryDuplicateClusterRepository()

    # 1. ProfileRetrievalTool
    p_tool = ProfileRetrievalTool(profile_repo)
    res_ok = p_tool.execute(ProfileRetrievalArgs(user_id=profile.user_id))
    assert res_ok.success is True
    assert res_ok.data is not None
    assert res_ok.data.user_id == profile.user_id
    assert res_ok.latency_ms >= 0

    res_missing = p_tool.execute(ProfileRetrievalArgs(user_id="non-existent"))
    assert res_missing.success is False
    assert "not found" in res_missing.error_message.lower()

    # 2. RoleMappingTool
    rm_tool = RoleMappingTool()
    rm_res = rm_tool.execute(RoleMappingArgs(profile=profile))
    assert rm_res.success is True
    assert len(rm_res.data) >= 1

    # 3. OpportunitySearchTool
    async def _test_search() -> None:
        search_tool = OpportunitySearchTool()
        q = rm_res.data[0].queries[0]
        s_res = await search_tool.execute(OpportunitySearchArgs(connector_id="web_search", query=q, limit=2))
        assert s_res.success is True
        assert s_res.data is not None
        assert len(s_res.data.opportunities) > 0

        # Unknown connector error handling
        s_err = await search_tool.execute(OpportunitySearchArgs(connector_id="invalid_conn", query=q, limit=2))
        assert s_err.success is False
        assert "unknown" in s_err.error_message.lower()

        # 4. DeduplicationTool
        d_tool = DeduplicationTool()
        d_res = d_tool.execute(DeduplicationArgs(opportunities=s_res.data.opportunities, threshold=0.85))
        assert d_res.success is True
        assert d_res.data.canonical_count > 0

        # 5. DeterministicEligibilityTool
        e_tool = DeterministicEligibilityTool()
        e_res = e_tool.execute(
            DeterministicEligibilityArgs(
                candidate_profile=profile,
                canonical_opportunities=d_res.data.canonical_opportunities,
            )
        )
        assert e_res.success is True
        assert len(e_res.data) == d_res.data.canonical_count

        # 6. PersistenceTool
        persist_tool = PersistenceTool(opp_repo, cluster_repo)
        p_res = persist_tool.execute(PersistenceArgs(opportunities=s_res.data.opportunities, clusters={}))
        assert p_res.success is True
        assert p_res.data.total_fetched > 0

    asyncio.run(_test_search())


def test_adaptive_discovery_workflow_end_to_end_coverage_satisfied() -> None:
    """Verifies that the agentic workflow plans, searches, deduplicates, verifies eligibility,
    satisfies the coverage goal, and terminates with COVERAGE_SATISFIED."""
    async def _run() -> None:
        profile = _make_candidate_fixture()
        profile_repo = InMemoryCandidateProfileRepository()
        profile_repo.save(profile)
        opp_repo = InMemoryOpportunityRepository()
        cluster_repo = InMemoryDuplicateClusterRepository()

        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=opp_repo,
            cluster_repo=cluster_repo,
            profile_repo=profile_repo,
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=profile,
            target_coverage_goal=2,
            max_iterations=3,
            max_tool_calls=10,
            persist_to_repository=True,
        )

        response = await workflow.run(request)

        # 1. Successful termination
        assert response.termination_reason == TerminationReason.COVERAGE_SATISFIED
        assert len(response.eligible_opportunities) >= 2
        assert response.canonical_count > 0

        # 2. Strategy and Coverage telemetry
        assert len(response.search_strategy.selected_connector_ids) >= 1
        assert response.coverage_assessment.is_coverage_sufficient is True

        # 3. Observable timeline verification
        stages = [e.stage for e in response.timeline_events]
        assert WorkflowStage.INITIALIZING in stages
        assert WorkflowStage.STRATEGY_FORMULATION in stages
        assert WorkflowStage.SEARCHING in stages
        assert WorkflowStage.EVALUATING in stages
        assert WorkflowStage.COMPLETED in stages

    asyncio.run(_run())


def test_adaptive_discovery_triggers_adaptation_on_coverage_gap() -> None:
    """CRITICAL TEST: Verifies that when initial search yield has a deficit (or gap),
    the agent detects the gap, triggers an adaptation (Level 1: Query relaxation or Level 2: Adjacent expansion),
    and executes an adaptive second iteration."""
    async def _run() -> None:
        profile = _make_candidate_fixture()
        profile_repo = InMemoryCandidateProfileRepository()
        profile_repo.save(profile)

        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=profile_repo,
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=profile,
            target_coverage_goal=4,
            max_iterations=3,
            max_tool_calls=12,
            force_adaptive_gap_for_testing=True,  # Force gap on round 1 to verify adaptation
            persist_to_repository=False,
        )

        response = await workflow.run(request)

        # Must have completed at least 2 iterations
        assert response.iterations_completed >= 2

        # Must have recorded at least one AdaptationEvent
        assert len(response.adaptation_history) >= 1
        adapt = response.adaptation_history[0]
        assert adapt.iteration == 1
        assert adapt.adaptation_type in ("QUERY_RELAXATION", "ADJACENT_EXPANSION")
        assert len(adapt.action_summary) > 0
        assert adapt.new_query is not None

        # Verify timeline records adaptation
        events = [e.event_type for e in response.timeline_events]
        assert "ADAPTATION_TRIGGERED" in events

    asyncio.run(_run())


def test_workflow_terminates_on_max_iterations() -> None:
    """Verifies that setting max_iterations=1 halts execution after 1 iteration with MAX_ITERATIONS_REACHED."""
    async def _run() -> None:
        profile = _make_candidate_fixture()
        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=InMemoryCandidateProfileRepository(),
        )

        # High goal within valid schema bounds (le=15) that cannot be met in 1 iteration
        request = AdaptiveDiscoveryRequest(
            candidate_profile=profile,
            target_coverage_goal=15,
            max_iterations=1,
            max_tool_calls=12,
            force_adaptive_gap_for_testing=True,
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        assert response.iterations_completed == 1
        assert response.termination_reason == TerminationReason.MAX_ITERATIONS_REACHED

    asyncio.run(_run())


def test_workflow_terminates_on_budget_exhaustion() -> None:
    """Verifies that when tool execution budget is exhausted, workflow stops with BUDGET_EXHAUSTED."""
    async def _run() -> None:
        profile = _make_candidate_fixture()
        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=InMemoryCandidateProfileRepository(),
        )

        # Strict budget: max 2 tool calls
        request = AdaptiveDiscoveryRequest(
            candidate_profile=profile,
            target_coverage_goal=15,
            max_iterations=3,
            max_tool_calls=2,
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        assert response.total_tool_calls <= 5
        assert response.termination_reason == TerminationReason.BUDGET_EXHAUSTED

    asyncio.run(_run())


def test_partial_source_failure_isolation() -> None:
    """Verifies that an error in one connector is shielded and healthy connectors deliver results."""
    async def _run() -> None:
        profile = _make_candidate_fixture()
        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=InMemoryCandidateProfileRepository(),
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=profile,
            target_coverage_goal=2,
            max_iterations=2,
            simulate_failure_connector="web_search",  # simulate web search failure
            persist_to_repository=False,
        )

        response = await workflow.run(request)

        # Workflow still succeeded with remaining connectors
        assert response.total_discovered_raw > 0
        assert response.canonical_count > 0

        # Timeline logged the tool failure event cleanly
        fail_events = [e for e in response.timeline_events if e.event_type == "TOOL_FAILED"]
        assert len(fail_events) >= 1
        assert "web_search" in fail_events[0].details.get("connector_id", "")

    asyncio.run(_run())


def test_duplicate_query_avoidance_via_hash_tracking() -> None:
    """Verifies that query hashing prevents executing the exact same query on the same connector twice."""
    hash1 = compute_query_hash("Backend Engineer", "web_search")
    hash2 = compute_query_hash("backend engineer  ", "WEB_SEARCH")
    assert hash1 == hash2

    hash3 = compute_query_hash("Frontend Engineer", "web_search")
    assert hash1 != hash3


def test_llm_failure_graceful_fallback() -> None:
    """Verifies that if the LLM provider fails or times out, the decision maker transparently
    falls back to calibrated deterministic heuristics without crashing."""
    mock_llm = MockLLMClient(simulate_timeout=True)
    decision_maker = DiscoveryAgentDecisionMaker(llm_client=mock_llm)

    profile = _make_candidate_fixture()
    rm_tool = RoleMappingTool()
    targets = rm_tool.execute(RoleMappingArgs(profile=profile)).data

    # Strategy formulation with simulated LLM timeout
    strategy = decision_maker.formulate_initial_strategy(
        profile=profile,
        target_roles=targets,
        adjacent_roles=[],
        available_connectors=[],
        target_coverage_goal=3,
    )
    assert strategy.target_coverage_goal == 3
    assert len(strategy.target_role_priorities) >= 1
    assert "Prioritizing primary target roles" in strategy.strategy_summary


def test_untrusted_input_sanitization_in_workflow() -> None:
    """Verifies that adversarial prompt injection contained in job descriptions is neutralized."""
    async def _run() -> None:
        profile = _make_candidate_fixture()
        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=InMemoryCandidateProfileRepository(),
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=profile,
            target_coverage_goal=2,
            max_iterations=1,
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        for opp in response.canonical_opportunities:
            # Check summary text is clean
            assert "system prompt" not in opp.sanitized_summary.lower()
            assert "ignore previous instructions" not in opp.sanitized_summary.lower()

    asyncio.run(_run())


def test_api_orchestration_run_endpoint() -> None:
    """Verifies the FastAPI endpoint POST /api/v1/orchestration/discovery/run."""
    client = TestClient(app)
    profile = _make_candidate_fixture().model_dump(mode="json")

    payload = {
        "candidate_profile": profile,
        "target_coverage_goal": 2,
        "max_iterations": 2,
        "max_tool_calls": 8,
        "persist_to_repository": False,
    }

    resp = client.post("/api/v1/orchestration/discovery/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "workflow_id" in data
    assert data["candidate_id"] == "agent-test-user"
    assert data["iterations_completed"] >= 1
    assert data["total_discovered_raw"] > 0
    assert data["canonical_count"] > 0
    assert "coverage_assessment" in data
    assert len(data["timeline_events"]) >= 5

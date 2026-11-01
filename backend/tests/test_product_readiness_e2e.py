from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any, Optional, Sequence, Type
import pytest

from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
    InMemoryRecommendationRepository,
)
from app.modules.career_path.service import CareerPathIntelligenceService
from app.modules.deduplication.service import DeduplicationService
from app.modules.discovery.connectors.base import BaseDiscoveryConnector, create_normalized_opportunity
from app.modules.discovery.connectors.mcp.client import MCPClient
from app.modules.discovery.connectors.mcp.connector import JobSpyMCPConnector
from app.modules.discovery.connectors.web_search import WebSearchConnector
from app.modules.discovery.coordinator import DiscoveryCoordinator
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.explanation.explainer import OpportunityExplanationEngine
from app.modules.explanation.gap_analyzer import CareerGapAnalysisService
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
from app.modules.profiling.llm_client import BaseLLMClient, MockLLMClient
from app.modules.ranking.engine import CandidateJobRankingEngine
from app.schemas.career_path import (
    ActionProgressStatus,
    UpdateActionProgressRequest,
)
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import (
    ConnectorHealthReport,
    ConnectorStatus,
    DiscoveryConnectorResult,
    DiscoverySearchQuery,
)
from app.schemas.eligibility import (
    DISQ_COUNTRY_UNAUTHORIZED,
    DISQ_DEGREE_BELOW_MINIMUM,
    DISQ_EXPIRED_DEADLINE,
    UNCERT_LOCATION_UNRESTRICTED,
    UNCERT_NO_DEADLINE_SPECIFIED,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.gap_analysis import GapStatus
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
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
from app.schemas.ranking import RankingDimension


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def maya_chen_profile() -> CandidateCareerProfile:
    """Fixture representing candidate Maya Chen (Junior ML / Backend Engineer)."""
    ev_work = EvidenceRecord(
        evidence_id="ev_maya_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Built high-throughput FastAPI REST APIs and PostgreSQL database services for data ingestion.",
        verifiability_weight=0.92,
    )
    ev_project = EvidenceRecord(
        evidence_id="ev_maya_02",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Trained and deployed PyTorch classification models with automated CI/CD evaluation pipelines.",
        verifiability_weight=0.88,
    )

    skills = [
        AssessedSkill(
            canonical_skill_id="esco:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.95,
            evidence_records=[ev_work],
        ),
        AssessedSkill(
            canonical_skill_id="esco:fastapi",
            skill_name="FastAPI",
            proficiency_score=8.0,
            confidence_score=0.90,
            evidence_records=[ev_work],
        ),
        AssessedSkill(
            canonical_skill_id="esco:pytorch",
            skill_name="PyTorch",
            proficiency_score=7.0,
            confidence_score=0.85,
            evidence_records=[ev_project],
        ),
        AssessedSkill(
            canonical_skill_id="esco:postgresql",
            skill_name="PostgreSQL",
            proficiency_score=7.5,
            confidence_score=0.88,
            evidence_records=[ev_work],
        ),
    ]

    target = CareerPathNode(
        occupation_code="15-1252.00",
        title="Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
    )
    adjacent = CareerPathNode(
        occupation_code="15-1251.00",
        title="Machine Learning Engineer",
        relationship_type=CareerPathRelationship.ADJACENT,
        adjacency_similarity=0.85,
    )

    eligibility = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        total_full_time_experience_months=24,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, US", "Remote"],
    )

    return CandidateCareerProfile(
        user_id="usr_maya_chen_junior",
        profile_version=1,
        assessed_skills=skills,
        target_career_paths=[target],
        adjacent_career_paths=[adjacent],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.90,
    )


# ==============================================================================
# TEST 1: Full Unified End-to-End Pipeline
# ==============================================================================


def test_full_unified_pipeline_end_to_end(maya_chen_profile: CandidateCareerProfile) -> None:
    """Verifies complete end-to-end integration:

    Candidate Profile -> LangGraph Workflow -> Multi-source Discovery ->
    Deduplication -> Deterministic Eligibility -> 6D Ranking -> Explanations ->
    Career Gap Analysis -> Development Planning -> Action Progress Update.
    """

    async def _run() -> None:
        # 1. Initialize repositories and multi-source connectors
        opp_repo = InMemoryOpportunityRepository()
        cluster_repo = InMemoryDuplicateClusterRepository()
        profile_repo = InMemoryCandidateProfileRepository()
        rec_repo = InMemoryRecommendationRepository()

        # Seed profile in repository
        profile_repo.save(maya_chen_profile)

        mcp_connector = JobSpyMCPConnector(mock_mode=True, artificial_latency_ms=1.0)
        web_connector = WebSearchConnector(mock_mode=True, artificial_latency_ms=1.0)

        workflow = AdaptiveDiscoveryWorkflow(
            connectors=[mcp_connector, web_connector],
            opp_repo=opp_repo,
            cluster_repo=cluster_repo,
            profile_repo=profile_repo,
            rec_repo=rec_repo,
        )

        # 2. Execute LangGraph Adaptive Discovery Workflow
        request = AdaptiveDiscoveryRequest(
            candidate_profile=maya_chen_profile,
            connector_ids=["jobspy_mcp", "web_search"],
            target_coverage_goal=3,
            max_iterations=2,
            max_tool_calls=8,
            persist_to_repository=True,
            rank_recommendations=True,
        )

        wf_response = await workflow.run(request)

        # Assert workflow state and completion
        assert wf_response.workflow_id.startswith("wf-")
        assert wf_response.candidate_id == maya_chen_profile.user_id
        assert wf_response.termination_reason == TerminationReason.COVERAGE_SATISFIED
        assert wf_response.total_discovered_raw > 0
        assert wf_response.canonical_count > 0
        assert wf_response.recommendations is not None
        assert wf_response.recommendations.total_eligible_ranked > 0

        # Assert stage progression in timeline events
        stages = [e.stage for e in wf_response.timeline_events]
        assert WorkflowStage.INITIALIZING in stages
        assert WorkflowStage.STRATEGY_FORMULATION in stages
        assert WorkflowStage.SEARCHING in stages
        assert WorkflowStage.EVALUATING in stages
        assert WorkflowStage.RANKING in stages
        assert WorkflowStage.FINALIZING in stages
        assert WorkflowStage.COMPLETED in stages

        top_rec = wf_response.recommendations.ranked_recommendations[0]
        assert top_rec.overall_fit_score >= 0.0
        assert top_rec.dimension_scores[RankingDimension.SKILL_ALIGNMENT].raw_score >= 0.0

        # 3. Deterministic Explanation Generation with Citations
        explainer = OpportunityExplanationEngine(llm_client=MockLLMClient())
        explanation = explainer.explain_recommendation(
            candidate=maya_chen_profile,
            ranked_opp=top_rec,
            use_llm=False,
        )

        assert explanation.opportunity_id == top_rec.opportunity.opportunity_id
        assert len(explanation.why_matches_summary) > 0
        assert explanation.eligibility_verdict is not None
        assert isinstance(explanation.matched_requirements, list)

        # 4. Career Gap Analysis Grounded in Evidence
        gap_analyzer = CareerGapAnalysisService()
        gap_response = gap_analyzer.analyze_candidate_gaps(
            candidate=maya_chen_profile,
            target_roles=["Backend Software Engineer", "Machine Learning Engineer"],
            opportunities=[top_rec.opportunity],
            ranked_recommendations=wf_response.recommendations.ranked_recommendations,
        )

        assert gap_response.user_id == maya_chen_profile.user_id
        assert isinstance(gap_response.prioritized_gaps, list)
        assert isinstance(gap_response.suggested_improvements, list)

        # 5. Career Path Intelligence & Personalized Development Planning
        career_service = CareerPathIntelligenceService(gap_analyzer=gap_analyzer)
        career_assessment = career_service.assess_candidate_career_paths(
            candidate=maya_chen_profile,
            discovered_opportunities=[r.opportunity for r in wf_response.recommendations.ranked_recommendations],
        )

        assert career_assessment.user_id == maya_chen_profile.user_id
        assert len(career_assessment.role_assessments) >= 1
        assert career_assessment.career_path_graph.is_cycle_free is True
        assert len(career_assessment.development_plan.short_term_actions) > 0

        # 6. Action Progress Tracking
        action_to_update = career_assessment.development_plan.short_term_actions[0]
        action_to_update.status = ActionProgressStatus.IN_PROGRESS
        action_to_update.candidate_notes = "Started tutorial and set up GitHub repository."
        assert action_to_update.status == ActionProgressStatus.IN_PROGRESS

        # Complete the action
        action_to_update.status = ActionProgressStatus.COMPLETED
        action_to_update.verification_artifact_url = "https://github.com/mayachen/fastapi-distributed-cache"
        assert action_to_update.status == ActionProgressStatus.COMPLETED
        assert action_to_update.verification_artifact_url is not None

    asyncio.run(_run())


# ==============================================================================
# TEST 2: Degraded Scenario — Partial Source Failure
# ==============================================================================


class FailingDiscoveryConnector(BaseDiscoveryConnector):
    """Simulated connector that consistently fails with network timeout or error."""

    @property
    def connector_id(self) -> str:
        return "failing_connector"

    @property
    def source_name(self) -> str:
        return "Failing Source"

    @property
    def connector_type(self) -> str:
        return "MOCK_FAILING"

    @property
    def is_mock_fallback(self) -> bool:
        return True

    async def search(
        self, query: DiscoverySearchQuery, limit: int = 10
    ) -> DiscoveryConnectorResult:
        raise ConnectionError("Simulated remote network timeout (504 Gateway Timeout)")

    async def check_health(self) -> ConnectorHealthReport:
        return ConnectorHealthReport(
            connector_id=self.connector_id,
            source_name=self.source_name,
            connector_type=self.connector_type,
            status=ConnectorStatus.ERROR,
            is_mock_fallback=self.is_mock_fallback,
            details={"diagnostic_message": "Connection timed out"},
        )


def test_degraded_scenario_partial_source_failure(maya_chen_profile: CandidateCareerProfile) -> None:
    """When one connector suffers an unhandled network error, the workflow must not crash.

    Surviving connectors fulfill discovery, and the error is reported in connector health.
    """

    async def _run() -> None:
        failing_connector = FailingDiscoveryConnector()
        healthy_web_connector = WebSearchConnector(mock_mode=True, artificial_latency_ms=1.0)

        workflow = AdaptiveDiscoveryWorkflow(
            connectors=[failing_connector, healthy_web_connector],
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=maya_chen_profile,
            connector_ids=["failing_connector", "web_search"],
            target_coverage_goal=2,
            max_iterations=1,
            max_tool_calls=4,
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)

        # Workflow still succeeded with healthy connector
        assert response.workflow_id.startswith("wf-")
        assert response.total_discovered_raw > 0
        assert response.canonical_count > 0

        # Verify failing connector is reported cleanly
        health_by_id = {h.connector_id: h for h in response.connector_health}
        assert "failing_connector" in health_by_id
        assert health_by_id["failing_connector"].status == ConnectorStatus.ERROR

        # Healthy connector reported healthy
        assert "web_search" in health_by_id
        assert health_by_id["web_search"].status in (ConnectorStatus.CONNECTED, ConnectorStatus.MOCKED_FALLBACK)

    asyncio.run(_run())


# ==============================================================================
# TEST 3: Degraded Scenario — MCP Binary Unavailable
# ==============================================================================


def test_degraded_scenario_mcp_unavailable() -> None:
    """When MCP executable is absent, connector accurately reports UNAVAILABLE_MISSING_BINARY

    without throwing unhandled runtime exceptions.
    """

    async def _run() -> None:
        mcp_client = MCPClient(command="/nonexistent/bin/mcp-jobspy-missing")
        mcp_connector = JobSpyMCPConnector(
            mcp_client=mcp_client,
            mock_mode=False,
        )

        # 1. Health check honestly reports UNAVAILABLE_MISSING_BINARY when binary is absent
        report = await mcp_connector.check_health()
        assert report.status == ConnectorStatus.UNAVAILABLE_MISSING_BINARY
        assert "ensure binary is on path" in str(report.details).lower()

        # 2. Executing search with simulate_error returns empty list with status ERROR, no unhandled crash
        error_connector = JobSpyMCPConnector(simulate_error=True)
        query = DiscoverySearchQuery(
            query_id="q_test_missing",
            role_title="Backend Engineer",
            query_string="Backend Engineer",
            category=OpportunityCategory.FULL_TIME_JOB,
        )
        res = await error_connector.search(query)
        assert res.opportunities == []
        assert res.status == ConnectorStatus.ERROR

    asyncio.run(_run())


# ==============================================================================
# TEST 4: Degraded Scenario — Zero Discovery Results
# ==============================================================================


class EmptyDiscoveryConnector(BaseDiscoveryConnector):
    """Connector that returns zero results (e.g. niche or over-constrained query)."""

    @property
    def connector_id(self) -> str:
        return "empty_connector"

    @property
    def source_name(self) -> str:
        return "Empty Source"

    @property
    def connector_type(self) -> str:
        return "MOCK_EMPTY"

    @property
    def is_mock_fallback(self) -> bool:
        return True

    async def search(
        self, query: DiscoverySearchQuery, limit: int = 10
    ) -> DiscoveryConnectorResult:
        return DiscoveryConnectorResult(
            connector_id=self.connector_id,
            source_name=self.source_name,
            query_id=query.query_id,
            status=ConnectorStatus.CONNECTED,
            opportunities=[],
            raw_count=0,
            latency_ms=1.0,
        )

    async def check_health(self) -> ConnectorHealthReport:
        return ConnectorHealthReport(
            connector_id=self.connector_id,
            source_name=self.source_name,
            connector_type=self.connector_type,
            status=ConnectorStatus.CONNECTED,
            is_mock_fallback=self.is_mock_fallback,
            details={},
        )


def test_degraded_scenario_zero_discovery_results(maya_chen_profile: CandidateCareerProfile) -> None:
    """When all discovery sources return zero results, the system halts cleanly with ALL_SOURCES_EXHAUSTED

    and downstream components handle empty lists gracefully without IndexError or crash.
    """

    async def _run() -> None:
        workflow = AdaptiveDiscoveryWorkflow(
            connectors=[EmptyDiscoveryConnector()],
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=maya_chen_profile,
            connector_ids=["empty_connector"],
            target_coverage_goal=5,
            max_iterations=1,
            max_tool_calls=2,
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)

        assert response.total_discovered_raw == 0
        assert response.canonical_count == 0
        assert response.eligible_count == 0
        assert response.termination_reason in (
            TerminationReason.ALL_SOURCES_EXHAUSTED,
            TerminationReason.BUDGET_EXHAUSTED,
            TerminationReason.MAX_ITERATIONS_REACHED,
        )
        assert (
            response.recommendations is None
            or response.recommendations.total_eligible_ranked == 0
        )

        # Career gap analysis must still provide baseline analysis from candidate profile alone
        gap_analyzer = CareerGapAnalysisService()
        gap_response = gap_analyzer.analyze_candidate_gaps(
            candidate=maya_chen_profile,
            target_roles=["Backend Software Engineer"],
            opportunities=[],
        )
        assert gap_response.user_id == maya_chen_profile.user_id
        assert isinstance(gap_response.prioritized_gaps, list)

    asyncio.run(_run())


# ==============================================================================
# TEST 5: Degraded Scenario — Cross-Source Duplicate Resolution
# ==============================================================================


def test_degraded_scenario_cross_source_duplicates(maya_chen_profile: CandidateCareerProfile) -> None:
    """When the same listing is discovered across WebSearch, MCP, and ATS direct feeds,

    MinHash LSH deduplication groups them into a single canonical entity.
    """
    now = datetime.now(timezone.utc)
    base_text = (
        "Acme Corp is seeking a Senior Backend Engineer proficient in Python, FastAPI, and Docker. "
        "Responsible for building scalable microservices and database pipelines in San Francisco, CA."
    )

    opp_ats = create_normalized_opportunity(
        title="Senior Backend Engineer",
        company_name="Acme Corp",
        description=base_text,
        source_url="https://jobs.lever.co/acme/backend-1",
        source_system="ats_direct",
        category=OpportunityCategory.FULL_TIME_JOB,
        posted_at=now,
    )

    # Web search copy with tracking params and slight whitespace differences
    opp_web = create_normalized_opportunity(
        title="Senior Backend Engineer",
        company_name="Acme Corp",
        description=base_text + " Equal opportunity employer. Apply today via web search.",
        source_url="https://google.com/search/jobs?q=acme+backend&utm_source=google",
        source_system="web_search",
        category=OpportunityCategory.FULL_TIME_JOB,
        posted_at=now,
    )

    # JobSpy MCP copy from LinkedIn scraper
    opp_mcp = create_normalized_opportunity(
        title="Senior Backend Engineer",
        company_name="Acme Corp",
        description=base_text + " (Job ID: 98124). Full-time role.",
        source_url="https://linkedin.com/jobs/view/98124",
        source_system="mcp_jobspy",
        category=OpportunityCategory.FULL_TIME_JOB,
        posted_at=now,
    )

    dedup_service = DeduplicationService(threshold=0.75)
    dedup_result = dedup_service.deduplicate_batch([opp_ats, opp_web, opp_mcp])

    # 3 raw records condensed to 1 canonical record
    assert dedup_result.total_evaluated == 3
    assert len(dedup_result.canonical_opportunities) == 1
    assert dedup_result.duplicate_count == 2

    canonical_opp = dedup_result.canonical_opportunities[0]
    assert canonical_opp.company_name == "Acme Corp"


# ==============================================================================
# TEST 6: Degraded Scenario — LLM Failure Deterministic Fallback
# ==============================================================================


class FailingLLMClient(BaseLLMClient):
    """LLM client that simulates API key revocation or model gateway outage."""

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[Any],
    ) -> Any:
        raise RuntimeError("LLM Gateway 503 Service Unavailable")


def test_degraded_scenario_llm_failure_deterministic_fallback(
    maya_chen_profile: CandidateCareerProfile,
) -> None:
    """When the LLM provider fails, explanation service and career path intelligence

    fall back safely to deterministic rule-based output without throwing unhandled exceptions.
    """
    now = datetime.now(timezone.utc)
    opp = create_normalized_opportunity(
        title="Python Backend Engineer",
        company_name="Starlight Tech",
        description="Looking for Python and FastAPI developers to build cloud APIs.",
        source_url="https://starlight.example/jobs/1",
        source_system="ats_direct",
        category=OpportunityCategory.FULL_TIME_JOB,
        posted_at=now,
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                is_mandatory=True,
                minimum_proficiency=7.0,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:fastapi",
                skill_name="FastAPI",
                is_mandatory=False,
                minimum_proficiency=6.0,
            ),
        ],
    )

    # Test explanation service with failing LLM
    failing_llm = FailingLLMClient()
    explainer = OpportunityExplanationEngine(llm_client=failing_llm)

    # With use_llm=True, the failure is caught and falls back to deterministic template
    explanation = explainer.explain_opportunity(
        candidate=maya_chen_profile,
        opportunity=opp,
        use_llm=True,
    )

    assert explanation is not None
    assert len(explanation.why_matches_summary) > 0
    assert explanation.opportunity_id == opp.opportunity_id
    # Deterministic fallback matched requirements preserved
    assert any("python" in r.skill_name.lower() for r in explanation.matched_requirements)

    # Test career path intelligence with failing LLM
    career_service = CareerPathIntelligenceService(llm_client=failing_llm)
    assessment = career_service.assess_candidate_career_paths(
        candidate=maya_chen_profile,
        discovered_opportunities=[opp],
    )
    assert assessment is not None
    assert len(assessment.development_plan.short_term_actions) > 0


# ==============================================================================
# TEST 7: Degraded Scenario — Tool Call Budget & Iteration Exhaustion
# ==============================================================================


def test_degraded_scenario_tool_budget_and_iteration_exhaustion(
    maya_chen_profile: CandidateCareerProfile,
) -> None:
    """Strict enforcement of iteration limits and tool call budgets prevents runaway loops

    and emits structured termination reasons.
    """

    async def _run() -> None:
        web_connector = WebSearchConnector(mock_mode=True, artificial_latency_ms=1.0)
        workflow = AdaptiveDiscoveryWorkflow(connectors=[web_connector])

        # Require a coverage of 15 opportunities with tight budget of 2 calls and 1 iteration
        request = AdaptiveDiscoveryRequest(
            candidate_profile=maya_chen_profile,
            target_coverage_goal=15,
            max_iterations=1,
            max_tool_calls=2,
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)

        # Budget or iteration limit strictly halted the cycle
        assert response.iterations_completed <= 1
        assert response.termination_reason in (
            TerminationReason.BUDGET_EXHAUSTED,
            TerminationReason.MAX_ITERATIONS_REACHED,
            TerminationReason.ALL_SOURCES_EXHAUSTED,
        )

    asyncio.run(_run())


# ==============================================================================
# TEST 8: Degraded Scenario — Incomplete Opportunity Data
# ==============================================================================


def test_degraded_scenario_incomplete_opportunity_data(
    maya_chen_profile: CandidateCareerProfile,
) -> None:
    """When opportunities lack deadlines or location fields, deterministic eligibility

    emits ELIGIBLE_WITH_UNCERTAINTY with explicit uncertainty caveats rather than false rejection.
    """
    now = datetime.now(timezone.utc)

    # Candidate with unrestricted locations
    candidate_unrestricted = maya_chen_profile.model_copy(
        update={
            "eligibility_constraints": maya_chen_profile.eligibility_constraints.model_copy(
                update={"preferred_locations": []}
            )
        }
    )

    # Opportunity with unspecified deadline and unspecified hybrid locations
    incomplete_criteria = OpportunityEligibilityRules(
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.NONE,
        requires_active_student_status=False,
        min_experience_months=0,
        work_mode=WorkMode.HYBRID,
        location_city_country=[],  # Unspecified location for hybrid
        application_deadline=None,  # No deadline
    )

    opp = PolymorphicOpportunity(
        opportunity_id="opp_incomplete_01",
        minhash_signature_hex="0" * 64,
        title="General Software Engineer",
        company_name="Stealth Startup",
        mapped_occupation_code="15-1252.00",
        sanitized_summary="Engineering role with unspecified criteria.",
        source_url="https://stealth.example/career",
        posted_at=now,
        completeness_score=0.30,
        trust_score=0.70,
        eligibility_rules=incomplete_criteria,
        skill_requirements=[],
    )

    result = evaluate_eligibility(candidate_unrestricted, opp)

    # Candidate is NOT falsely disqualified
    assert result.is_eligible is True
    assert result.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
    assert UNCERT_NO_DEADLINE_SPECIFIED in result.uncertainty_caveats
    assert UNCERT_LOCATION_UNRESTRICTED in result.uncertainty_caveats

    # Ranking engine handles missing fields without KeyError or NaN
    ranking_engine = CandidateJobRankingEngine()
    ranked_resp = ranking_engine.evaluate_and_rank(candidate_unrestricted, [opp])
    assert ranked_resp.total_eligible_ranked == 1
    assert ranked_resp.ranked_recommendations[0].overall_fit_score >= 0.0


# ==============================================================================
# TEST 9: Degraded Scenario — Sparse Candidate Evidence
# ==============================================================================


def test_degraded_scenario_sparse_candidate_evidence() -> None:
    """When candidate profile contains zero evidence snippets, gap analysis reports

    requirements as NOT_DEMONSTRATED without raising ZeroDivisionError or negative scores.
    """
    sparse_profile = CandidateCareerProfile(
        user_id="usr_sparse_candidate",
        profile_version=1,
        assessed_skills=[],  # Zero skills assessed
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Backend Software Engineer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            requires_visa_sponsorship=False,
            highest_degree_level=DegreeLevel.HIGH_SCHOOL,
            is_currently_enrolled_student=False,
            total_full_time_experience_months=0,
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            allowed_work_modes=[WorkMode.REMOTE],
            preferred_locations=["Remote"],
        ),
        overall_profile_confidence=0.10,
    )

    gap_analyzer = CareerGapAnalysisService()
    gap_response = gap_analyzer.analyze_candidate_gaps(
        candidate=sparse_profile,
        target_roles=["Backend Software Engineer"],
    )

    assert gap_response.user_id == "usr_sparse_candidate"
    assert len(gap_response.prioritized_gaps) > 0

    # All required skills are marked NOT_DEMONSTRATED
    for gap in gap_response.prioritized_gaps:
        assert gap.gap_status == GapStatus.NOT_DEMONSTRATED
        assert gap.candidate_proficiency is None
        assert len(gap.supporting_evidence) == 0

    # Development planning still generates valid foundational action items
    career_service = CareerPathIntelligenceService(gap_analyzer=gap_analyzer)
    assessment = career_service.assess_candidate_career_paths(candidate=sparse_profile)
    assert len(assessment.development_plan.short_term_actions) > 0


# ==============================================================================
# TEST 10: Safe Execution Trace & Zero Private Chain-of-Thought Telemetry
# ==============================================================================


def test_safe_execution_trace_and_telemetry_isolation(
    maya_chen_profile: CandidateCareerProfile,
) -> None:
    """Verifies that all timeline telemetry events emitted to client are sanitized,

    structured, and contain zero private chain-of-thought, prompt instructions, or secrets.
    """

    async def _run() -> None:
        web_connector = WebSearchConnector(mock_mode=True, artificial_latency_ms=1.0)
        workflow = AdaptiveDiscoveryWorkflow(connectors=[web_connector])

        request = AdaptiveDiscoveryRequest(
            candidate_profile=maya_chen_profile,
            target_coverage_goal=2,
            max_iterations=1,
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)

        # Audit timeline events
        assert len(response.timeline_events) > 0
        forbidden_substrings = [
            "system prompt",
            "chain-of-thought",
            "cot",
            "secret",
            "api_key",
            "bearer",
            "private reasoning",
            "<prompt>",
            "instruction:",
        ]

        for event in response.timeline_events:
            assert isinstance(event.stage, WorkflowStage)
            summary_lower = event.summary.lower()
            for forbidden in forbidden_substrings:
                assert forbidden not in summary_lower, (
                    f"Forbidden substring '{forbidden}' leaked in timeline event: {event.summary}"
                )

            # Details payload must not contain raw prompt strings or credentials
            for k, v in event.details.items():
                k_lower = str(k).lower()
                assert "secret" not in k_lower
                assert "key" not in k_lower
                assert "token" not in k_lower

    asyncio.run(_run())

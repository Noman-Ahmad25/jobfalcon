from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

import pytest

from app.core.config import Settings, get_settings, resolve_jobspy_country
from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
    InMemoryRecommendationRepository,
)
from app.modules.discovery.connectors.base import (
    BaseDiscoveryConnector,
    create_normalized_opportunity,
)
from app.modules.orchestration.agent import (
    DiscoveryAgentDecisionMaker,
    resolve_geographic_expansion,
    resolve_role_expansion,
)
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
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
    RoleMappingTarget,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    SearchCallOutcome,
    SearchStrategy,
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
def candidate_satna() -> CandidateCareerProfile:
    """Fixture representing the exact scenario: Junior Backend Engineer in Satna, India (Remote allowed)."""
    ev = EvidenceRecord(
        evidence_id="ev_satna_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Designed scalable backend APIs using Python and FastAPI with PostgreSQL databases.",
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
    ]
    target = CareerPathNode(
        occupation_code="15-1252.00",
        title="Junior Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
    )
    eligibility = CandidateEligibilityProfile(
        authorized_country_codes=["IN"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        total_full_time_experience_months=6,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["Satna, IN"],
    )
    return CandidateCareerProfile(
        user_id="usr_satna_dev_01",
        profile_version=1,
        assessed_skills=skills,
        target_career_paths=[target],
        adjacent_career_paths=[],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.90,
    )


class MockCustomConnector(BaseDiscoveryConnector):
    """Configurable mock connector for controlling results, delays, and errors."""

    def __init__(
        self,
        connector_id: str = "mock_c1",
        source_name: str = "Mock Connector 1",
        results_per_call: Optional[list[list[PolymorphicOpportunity]]] = None,
        delay_seconds: float = 0.0,
        raise_error: Optional[Exception] = None,
    ) -> None:
        self._connector_id = connector_id
        self._source_name = source_name
        self._results_per_call = list(results_per_call) if results_per_call else []
        self._call_count = 0
        self.delay_seconds = delay_seconds
        self.raise_error = raise_error
        self.recorded_queries: list[DiscoverySearchQuery] = []

    @property
    def connector_id(self) -> str:
        return self._connector_id

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def connector_type(self) -> str:
        return "MOCK_CUSTOM"

    @property
    def is_mock_fallback(self) -> bool:
        return True

    async def check_health(self) -> ConnectorHealthReport:
        return ConnectorHealthReport(
            connector_id=self._connector_id,
            source_name=self._source_name,
            connector_type=self.connector_type,
            status=ConnectorStatus.CONNECTED,
            is_mock_fallback=True,
            details={"configured": True},
        )

    async def search(
        self,
        query: DiscoverySearchQuery,
        limit: int = 10,
    ) -> DiscoveryConnectorResult:
        self.recorded_queries.append(query)
        self._call_count += 1

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.raise_error:
            raise self.raise_error

        items: list[PolymorphicOpportunity] = []
        if self._results_per_call:
            idx = min(self._call_count - 1, len(self._results_per_call) - 1)
            items = self._results_per_call[idx]

        return DiscoveryConnectorResult(
            connector_id=self._connector_id,
            source_name=self._source_name,
            query_id=query.query_id,
            status=ConnectorStatus.CONNECTED,
            opportunities=items,
            raw_count=len(items),
            latency_ms=10.0,
        )


def _make_opp(title: str, company: str, category: OpportunityCategory = OpportunityCategory.FULL_TIME_JOB) -> PolymorphicOpportunity:
    return create_normalized_opportunity(
        title=title,
        company_name=company,
        description=f"Great opportunity for {title} at {company}. Strong Python and FastAPI skills required.",
        source_url=f"https://example.com/jobs/{company.lower()}-{title.lower().replace(' ', '-')}",
        source_system="mock_custom",
        category=category,
        work_mode=WorkMode.REMOTE,
        location_city_country=["Satna, IN", "Remote, IN"],
        eligible_country_codes=["IN"],
        min_experience_months=0,
        application_deadline=datetime(2028, 1, 1, tzinfo=timezone.utc),
    )


# ==============================================================================
# 1. Local mode with generous budget default
# ==============================================================================

def test_01_local_mode_generous_budget_defaults() -> None:
    settings = Settings(DISCOVERY_EXECUTION_MODE="local")
    assert settings.is_local_discovery_mode is True
    assert settings.get_effective_max_iterations(None) == 6
    assert settings.get_effective_max_tool_calls(None) == 30
    assert settings.DISCOVERY_PER_TOOL_TIMEOUT_SECONDS == 20.0
    assert settings.DISCOVERY_WORKFLOW_TIMEOUT_SECONDS == 120.0
    assert settings.DISCOVERY_MAX_CALLS_PER_CONNECTOR == 15


# ==============================================================================
# 2. Unlimited tool-call setting
# ==============================================================================

def test_02_unlimited_tool_call_setting(candidate_satna: CandidateCareerProfile) -> None:
    settings = Settings(DISCOVERY_EXECUTION_MODE="local")
    assert settings.get_effective_max_tool_calls(0) == 0

    async def _run() -> None:
        c1 = MockCustomConnector(
            connector_id="c1",
            results_per_call=[[], [_make_opp("Python Dev", "Alpha")]],
        )
        workflow = AdaptiveDiscoveryWorkflow(connectors=[c1])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            target_coverage_goal=1,
            max_iterations=2,
            max_tool_calls=0,  # 0 indicates explicit unlimited
            persist_to_repository=False,
        )
        response = await workflow.run(request)
        assert response.termination_reason != TerminationReason.BUDGET_EXHAUSTED
        assert response.total_tool_calls >= 1

    asyncio.run(_run())


# ==============================================================================
# 3. Separate hosted vs local mode configuration
# ==============================================================================

def test_03_separate_hosted_vs_local_mode_configuration() -> None:
    hosted_settings = Settings(DISCOVERY_EXECUTION_MODE="hosted")
    assert hosted_settings.is_local_discovery_mode is False
    assert hosted_settings.get_effective_max_iterations(None) == 3
    assert hosted_settings.get_effective_max_tool_calls(None) == 10

    # Clamping in hosted mode: requests exceeding budget cap are clamped
    assert hosted_settings.get_effective_max_tool_calls(50) == 10
    assert hosted_settings.get_effective_max_iterations(10) == 3

    # In local mode, higher limits are permitted
    local_settings = Settings(DISCOVERY_EXECUTION_MODE="local")
    assert local_settings.get_effective_max_tool_calls(25) == 25
    assert local_settings.get_effective_max_iterations(5) == 5


# ==============================================================================
# 4. Model-specific timeouts & country resolution
# ==============================================================================

def test_04_model_specific_timeouts_and_jobspy_country() -> None:
    assert resolve_jobspy_country(["IN"]) == "india"
    assert resolve_jobspy_country(["US"]) == "usa"
    assert resolve_jobspy_country(["GB"]) == "uk"
    assert resolve_jobspy_country(["CA"]) == "canada"
    assert resolve_jobspy_country([]) == "usa"  # default fallback


# ==============================================================================
# 5. Connector-specific timeouts
# ==============================================================================

def test_05_connector_specific_timeouts(candidate_satna: CandidateCareerProfile, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_PER_TOOL_TIMEOUT_SECONDS", "0.2")
    get_settings.cache_clear()

    async def _run() -> None:
        try:
            slow_connector = MockCustomConnector(
                connector_id="slow_conn",
                source_name="Slow Source",
                delay_seconds=1.0,  # exceeds 0.2s timeout
            )
            fast_connector = MockCustomConnector(
                connector_id="fast_conn",
                source_name="Fast Source",
                results_per_call=[[_make_opp("Junior Python Engineer", "FastTech")]],
            )

            workflow = AdaptiveDiscoveryWorkflow(connectors=[slow_connector, fast_connector])
            request = AdaptiveDiscoveryRequest(
                candidate_profile=candidate_satna,
                connector_ids=["slow_conn", "fast_conn"],
                target_coverage_goal=1,
                max_iterations=1,
                persist_to_repository=False,
            )

            response = await workflow.run(request)
            slow_outcomes = [o for o in response.search_outcomes if o.connector_id == "slow_conn"]
            assert len(slow_outcomes) > 0
            assert slow_outcomes[0].status == "TIMEOUT"
            assert response.search_failures_count >= 1
            assert response.canonical_count >= 1
        finally:
            get_settings.cache_clear()

    asyncio.run(_run())


# ==============================================================================
# 6. Zero results from both initial sources triggers adaptation
# ==============================================================================

def test_06_zero_results_recovery_triggers_adaptation(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        c1 = MockCustomConnector(
            connector_id="c1",
            results_per_call=[[], [_make_opp("Python Developer", "InnovateIN")]],
        )
        c2 = MockCustomConnector(
            connector_id="c2",
            results_per_call=[[], []],
        )

        workflow = AdaptiveDiscoveryWorkflow(connectors=[c1, c2])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            target_coverage_goal=1,
            max_iterations=3,
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        assert response.iterations_completed >= 2
        assert len(response.adaptation_history) >= 1
        assert response.canonical_count >= 1

    asyncio.run(_run())


# ==============================================================================
# 7. Progressive query expansion after zero results
# ==============================================================================

def test_07_progressive_query_expansion_stages() -> None:
    r1, _ = resolve_role_expansion("Junior Backend Software Engineer", "ENTRY_LEVEL", ["Python", "FastAPI"], 1)
    r2, _ = resolve_role_expansion("Junior Backend Software Engineer", "ENTRY_LEVEL", ["Python", "FastAPI"], 2)
    r3, _ = resolve_role_expansion("Junior Backend Software Engineer", "ENTRY_LEVEL", ["Python", "FastAPI"], 3)
    r4, _ = resolve_role_expansion("Junior Backend Software Engineer", "ENTRY_LEVEL", ["Python", "FastAPI"], 4)

    assert r1 == "Junior Backend Developer"
    assert r2 == "Python Developer"
    assert r3 == "Graduate Software Engineer"
    assert r4 == "Graduate Software Engineer"


# ==============================================================================
# 8. Geographic expansion respecting candidate preferences
# ==============================================================================

def test_08_geographic_expansion_for_remote_candidate() -> None:
    locs1, _ = resolve_geographic_expansion(["Satna, IN"], [WorkMode.REMOTE], ["IN"], 1)
    locs2, _ = resolve_geographic_expansion(["Satna, IN"], [WorkMode.REMOTE], ["IN"], 2)
    locs3, _ = resolve_geographic_expansion(["Satna, IN"], [WorkMode.REMOTE], ["IN"], 3)

    assert locs1 == ["Madhya Pradesh, India"]
    assert locs2 == ["Remote"]
    assert locs3 == ["Remote"]

    locs_onsite, _ = resolve_geographic_expansion(["Satna, IN"], [WorkMode.ON_SITE], ["IN"], 2)
    assert locs_onsite == ["India"]


# ==============================================================================
# 9. Junior-role expansion for early-career candidates
# ==============================================================================

def test_09_junior_role_expansion(candidate_satna: CandidateCareerProfile) -> None:
    decision_maker = DiscoveryAgentDecisionMaker()
    target_roles = [
        RoleMappingTarget(
            role_title="Junior Backend Software Engineer",
            canonical_occupation_code="15-1252.00",
            relationship_type=CareerPathRelationship.TARGET,
            confidence_score=0.9,
            matched_skill_names=["Python", "FastAPI"],
            queries=[],
        )
    ]
    strategy = SearchStrategy(
        strategy_summary="Initial search plan",
        target_role_priorities=["Junior Backend Software Engineer"],
        target_coverage_goal=3,
        selected_connector_ids=["c1"],
        initial_queries=[],
    )
    assessment, adapt = decision_maker.assess_coverage_and_decide_adaptation(
        profile=candidate_satna,
        strategy=strategy,
        target_roles=target_roles,
        adjacent_roles=[],
        canonical_opportunities=[],
        eligibility_results=[],
        iteration=1,
        max_iterations=6,
        executed_query_hashes=set(),
    )
    assert adapt is not None
    assert str(adapt.adaptation_type) in ("COVERAGE_EXPANSION", "ADAPTIVE_QUERY_EXPANSION", "QUERY_RELAXATION")
    assert "Satna" in adapt.action_summary or "Madhya Pradesh" in adapt.action_summary or "Backend" in adapt.action_summary


# ==============================================================================
# 10. Connector failure recovery
# ==============================================================================

def test_10_connector_failure_recovery(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        broken_connector = MockCustomConnector(
            connector_id="broken_conn",
            source_name="Broken ATS",
            raise_error=RuntimeError("Connection reset by peer"),
        )
        working_connector = MockCustomConnector(
            connector_id="working_conn",
            source_name="Working ATS",
            results_per_call=[[_make_opp("Backend Python Developer", "SolidCo")]],
        )

        workflow = AdaptiveDiscoveryWorkflow(connectors=[broken_connector, working_connector])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            connector_ids=["broken_conn", "working_conn"],
            target_coverage_goal=1,
            max_iterations=1,
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        assert response.search_failures_count >= 1
        assert any(o.status == "PROVIDER_ERROR" for o in response.search_outcomes)
        assert response.canonical_count >= 1

    asyncio.run(_run())


# ==============================================================================
# 11. No repeated identical queries
# ==============================================================================

def test_11_no_repeated_identical_queries(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        connector = MockCustomConnector(
            connector_id="c_dedup",
            results_per_call=[[], [], []],
        )
        workflow = AdaptiveDiscoveryWorkflow(connectors=[connector])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            target_coverage_goal=5,
            max_iterations=3,
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        hashes = response.execution_metadata.get("executed_query_hashes", [])
        assert len(hashes) == len(set(hashes)), "Duplicate query hashes were executed!"

    asyncio.run(_run())


# ==============================================================================
# 12. Correct accounting when planned calls are skipped
# ==============================================================================

def test_12_correct_accounting_when_calls_skipped(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        c1 = MockCustomConnector(connector_id="c1", results_per_call=[[_make_opp("Dev 1", "Co1")]])
        c2 = MockCustomConnector(connector_id="c2", results_per_call=[[_make_opp("Dev 2", "Co2")]])
        c3 = MockCustomConnector(connector_id="c3", results_per_call=[[_make_opp("Dev 3", "Co3")]])

        workflow = AdaptiveDiscoveryWorkflow(connectors=[c1, c2, c3])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            connector_ids=["c1", "c2", "c3"],
            target_coverage_goal=5,
            max_iterations=1,
            max_tool_calls=1,  # Strictly 1 call allowed
            persist_to_repository=False,
        )

        response = await workflow.run(request)
        assert response.total_tool_calls == 1
        budget_event = next(
            (e for e in response.timeline_events if "Tool execution budget reached" in e.summary),
            None,
        )
        assert budget_event is not None
        assert "skipped" in budget_event.summary

    asyncio.run(_run())


# ==============================================================================
# 13. No contradictory budget telemetry
# ==============================================================================

def test_13_no_contradictory_budget_telemetry(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        c1 = MockCustomConnector(connector_id="c1", results_per_call=[[], []])
        c2 = MockCustomConnector(connector_id="c2", results_per_call=[[], []])

        workflow = AdaptiveDiscoveryWorkflow(connectors=[c1, c2])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            connector_ids=["c1", "c2"],
            target_coverage_goal=5,
            max_iterations=3,
            max_tool_calls=2,  # Budget limit = 2
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)
        assert response.total_tool_calls == 2
        assert response.termination_reason == TerminationReason.BUDGET_EXHAUSTED

        budget_events = [
            e for e in response.timeline_events
            if "budget reached" in e.summary.lower() or "budget exhausted" in e.summary.lower()
        ]
        assert len(budget_events) > 0
        for be in budget_events:
            assert "(2/2 calls)" in be.summary, f"Discrepancy found in event summary: {be.summary}"

    asyncio.run(_run())


# ==============================================================================
# 14. Partial-result persistence when execution stops
# ==============================================================================

def test_14_partial_result_persistence_on_stop(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        opp_repo = InMemoryOpportunityRepository()
        rec_repo = InMemoryRecommendationRepository()

        c1 = MockCustomConnector(
            connector_id="c1",
            results_per_call=[[_make_opp("Junior Python Dev", "PartialTech")]],
        )

        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=opp_repo,
            rec_repo=rec_repo,
            connectors=[c1],
        )
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            target_coverage_goal=5,
            max_iterations=1,
            max_tool_calls=1,
            persist_to_repository=True,
            rank_recommendations=True,
        )

        response = await workflow.run(request)
        assert response.canonical_count == 1
        assert response.recommendations is not None
        assert response.recommendations.total_eligible_ranked == 1

        saved_opps = opp_repo.list_all()
        assert len(saved_opps) >= 1

    asyncio.run(_run())


# ==============================================================================
# 15. Successful termination when sufficient opportunities are found
# ==============================================================================

def test_15_successful_termination_when_coverage_satisfied(candidate_satna: CandidateCareerProfile) -> None:
    async def _run() -> None:
        c1 = MockCustomConnector(
            connector_id="c1",
            results_per_call=[
                [
                    _make_opp("Junior Backend Software Engineer 1", "CoA"),
                    _make_opp("Junior Backend Software Engineer 2", "CoB"),
                ]
            ],
        )

        workflow = AdaptiveDiscoveryWorkflow(connectors=[c1])
        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_satna,
            target_coverage_goal=2,
            max_iterations=4,
            persist_to_repository=False,
            rank_recommendations=True,
        )

        response = await workflow.run(request)
        for opp in response.canonical_opportunities:
            print("OPP_ID:", opp.opportunity_id)
        for r in response.eligibility_results:
            print("ELIG:", r.opportunity_id, r.is_eligible, r.status, r.uncertainty_caveats)
        assert response.termination_reason == TerminationReason.COVERAGE_SATISFIED
        assert response.eligible_count >= 2
        assert "Reached target coverage goal" in response.stopping_condition_summary
        assert "Identified" in response.discovery_summary_notice

    asyncio.run(_run())

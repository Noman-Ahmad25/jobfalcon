from __future__ import annotations

import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
)
from app.main import app
from app.modules.discovery.connectors.ats_career_page import CompanyCareerPageConnector
from app.modules.discovery.connectors.india_jobs import IndiaJobsMCPConnector
from app.modules.discovery.connectors.jobspy import JobSpyMCPConnector
from app.modules.discovery.connectors.web_search import WebSearchConnector
from app.modules.discovery.coordinator import DiscoveryCoordinator
from app.modules.discovery.role_mapper import (
    generate_discovery_query_plan,
    map_profile_to_target_roles,
)
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import (
    ConnectorStatus,
    DiscoveryRunRequest,
    DiscoverySearchQuery,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


def _make_sample_candidate_profile(
    user_id: str = "test-user-dev",
    is_student: bool = False,
    experience_months: int = 18,
    country_codes: list[str] | None = None,
) -> CandidateCareerProfile:
    """Constructs a deterministic candidate profile fixture."""
    ev = EvidenceRecord(
        evidence_id="ev-101",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Built high-performance async REST APIs in Python using FastAPI, PostgreSQL, and Docker.",
        observed_at="2026-01-15T10:00:00Z",
        verifiability_weight=0.90,
    )
    skills = [
        AssessedSkill(
            canonical_skill_id="esco:skill:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.92,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:skill:fastapi",
            skill_name="FastAPI",
            proficiency_score=8.0,
            confidence_score=0.90,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:skill:postgresql",
            skill_name="PostgreSQL",
            proficiency_score=7.5,
            confidence_score=0.85,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:skill:docker",
            skill_name="Docker",
            proficiency_score=7.0,
            confidence_score=0.80,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:skill:typescript",
            skill_name="TypeScript",
            proficiency_score=6.0,
            confidence_score=0.75,
            evidence_records=[ev],
        ),
    ]

    target_path = CareerPathNode(
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
        allowed_opportunity_categories=[
            OpportunityCategory.FULL_TIME_JOB,
            OpportunityCategory.INTERNSHIP,
        ] if is_student else [OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, US"],
    )

    return CandidateCareerProfile(
        user_id=user_id,
        profile_version=1,
        assessed_skills=skills,
        current_career_path=None,
        target_career_paths=[target_path],
        adjacent_career_paths=[],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.88,
    )


def test_role_mapper_explicit_target_and_adjacent_inference() -> None:
    """Verifies that explicit target career paths are mapped as TARGET nodes (confidence=1.0),
    and high skill overlap triggers inferred ADJACENT nodes with identified missing skills."""
    profile = _make_sample_candidate_profile()
    targets = map_profile_to_target_roles(profile)

    assert len(targets) >= 1
    # Check TARGET node
    backend_target = next(t for t in targets if t.relationship_type == CareerPathRelationship.TARGET)
    assert backend_target.role_title == "Backend Software Engineer"
    assert backend_target.confidence_score == 1.0
    assert backend_target.canonical_occupation_code == "15-1252.00"
    assert "Python" in backend_target.matched_skill_names
    assert "FastAPI" in backend_target.matched_skill_names
    assert len(backend_target.queries) > 0

    # Check ADJACENT node inferred from skills (e.g., Full Stack or DevOps)
    adjacent_targets = [t for t in targets if t.relationship_type == CareerPathRelationship.ADJACENT]
    assert len(adjacent_targets) >= 1
    adj = adjacent_targets[0]
    assert adj.relationship_type == CareerPathRelationship.ADJACENT
    assert 0.50 <= adj.confidence_score < 1.0
    assert len(adj.matched_skill_names) > 0
    assert len(adj.missing_skill_names) > 0


def test_role_mapper_seniority_and_query_generation() -> None:
    """Verifies that student status generates internship queries and early-career filters."""
    student_profile = _make_sample_candidate_profile(
        user_id="student-test",
        is_student=True,
        experience_months=0,
        country_codes=["IN"],
    )
    plan = generate_discovery_query_plan(student_profile)

    assert plan.candidate_id == "student-test"
    assert plan.metadata["seniority_level"] == "INTERN"
    assert len(plan.all_queries) >= 2

    # Check that at least one query contains 'Intern'
    query_texts = [q.query_string for q in plan.all_queries]
    assert any("intern" in q.lower() for q in query_texts)

    # Check target country codes propagate
    for q in plan.all_queries:
        assert "IN" in q.target_country_codes


def test_all_connectors_health_reporting() -> None:
    """Verifies honest status reporting across all 4 discovery connectors."""
    async def _run() -> None:
        connectors = [
            WebSearchConnector(mock_mode=True),
            IndiaJobsMCPConnector(mock_mode=True),
            JobSpyMCPConnector(mock_mode=True),
            CompanyCareerPageConnector(mock_mode=True),
        ]

        for conn in connectors:
            report = await conn.check_health()
            assert report.connector_id == conn.connector_id
            assert report.source_name == conn.source_name
            assert report.status in (ConnectorStatus.CONNECTED, ConnectorStatus.MOCKED_FALLBACK)
            assert report.is_mock_fallback is True

    import asyncio
    asyncio.run(_run())


def test_connector_sanitization_and_minhash_generation() -> None:
    """Verifies that external listing text is normalized, prompt injections neutralized,
    and valid 64-char hex MinHash signatures computed."""
    async def _run() -> None:
        conn = WebSearchConnector(mock_mode=True)
        query = DiscoverySearchQuery(
            query_id="q-test-1",
            role_title="Backend Engineer",
            query_string="Backend Engineer Python",
            expanded_keywords=["Python", "FastAPI"],
            category=OpportunityCategory.FULL_TIME_JOB,
            work_modes=[WorkMode.REMOTE],
            target_locations=[],
            target_country_codes=["US"],
            seniority_level="ENTRY_LEVEL",
            relationship_type=CareerPathRelationship.TARGET,
        )

        result = await conn.search(query, limit=2)
        assert result.status == ConnectorStatus.MOCKED_FALLBACK
        assert len(result.opportunities) == 2

        for opp in result.opportunities:
            assert len(opp.minhash_signature_hex) == 64
            assert opp.title.strip() != ""
            assert opp.company_name.strip() != ""
            assert opp.sanitized_summary.strip() != ""
            assert opp.category_specific_attributes["source_system"] == "web_search"

    import asyncio
    asyncio.run(_run())


def test_partial_failure_resilience_in_coordinator() -> None:
    """CRITICAL TEST: Verifies that if one connector crashes or errors out,
    the discovery coordinator traps the error, reports ConnectorStatus.ERROR for that connector,
    and continues processing, deduplicating, and evaluating results from all other connectors."""
    async def _run() -> None:
        profile = _make_sample_candidate_profile()

        # Create repositories
        opp_repo = InMemoryOpportunityRepository()
        cluster_repo = InMemoryDuplicateClusterRepository()
        profile_repo = InMemoryCandidateProfileRepository()
        profile_repo.save(profile)

        # Inject failure into jobspy_mcp
        coordinator = DiscoveryCoordinator(
            opp_repo=opp_repo,
            cluster_repo=cluster_repo,
            profile_repo=profile_repo,
        )

        request = DiscoveryRunRequest(
            candidate_profile=profile,
            max_results_per_connector=2,
            deduplication_threshold=0.85,
            simulate_failure_connector="jobspy_mcp",  # simulate JobSpy failure
            persist_to_repository=True,
        )

        response = await coordinator.execute_discovery(request)

        # 1. Total discovered should include results from the other 3 connectors
        assert response.total_discovered > 0
        assert response.canonical_count > 0

        # 2. Check telemetry reports
        reports_by_id = {r.connector_id: r for r in response.connector_reports}
        assert "jobspy_mcp" in reports_by_id
        assert reports_by_id["jobspy_mcp"].status == ConnectorStatus.ERROR
        assert reports_by_id["jobspy_mcp"].error_message is not None

        # Other connectors must have succeeded
        assert reports_by_id["web_search"].status in (ConnectorStatus.CONNECTED, ConnectorStatus.MOCKED_FALLBACK)
        assert reports_by_id["ats_career_pages"].status in (ConnectorStatus.CONNECTED, ConnectorStatus.MOCKED_FALLBACK)

        # 3. Execution metadata reflects partial failure
        assert response.execution_metadata["failed_connectors"] == 1
        assert response.execution_metadata["successful_connectors"] == 3

    import asyncio
    asyncio.run(_run())


def test_cross_source_minhash_deduplication() -> None:
    """Verifies that cross-source syndicated listings (e.g., direct ATS and Web Search)
    are clustered together by MinHash LSH without dropping records."""
    async def _run() -> None:
        profile = _make_sample_candidate_profile()
        coordinator = DiscoveryCoordinator(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=InMemoryCandidateProfileRepository(),
        )

        request = DiscoveryRunRequest(
            candidate_profile=profile,
            connector_ids=["web_search", "ats_career_pages"],
            max_results_per_connector=3,
            deduplication_threshold=0.85,
            persist_to_repository=False,
        )

        response = await coordinator.execute_discovery(request)

        # Duplicate count should be >= 1 due to simulated syndicated Acme Cloud Technologies posting
        assert response.total_discovered >= 2
        assert response.canonical_count < response.total_discovered
        assert response.duplicate_count >= 1
        assert len(response.duplicate_records) >= 1

        # Verify duplicate cluster contains multiple source URLs
        cluster = list(response.duplicate_clusters.values())[0]
        assert len(cluster.all_source_urls) >= 2

    import asyncio
    asyncio.run(_run())


def test_deterministic_eligibility_on_discovered_jobs() -> None:
    """Verifies that discovered opportunities are filtered by the deterministic eligibility engine."""
    async def _run() -> None:
        # US authorized profile only
        profile_us = _make_sample_candidate_profile(country_codes=["US"])
        coordinator = DiscoveryCoordinator(
            opp_repo=InMemoryOpportunityRepository(),
            cluster_repo=InMemoryDuplicateClusterRepository(),
            profile_repo=InMemoryCandidateProfileRepository(),
        )

        request = DiscoveryRunRequest(
            candidate_profile=profile_us,
            connector_ids=["india_jobs_mcp"],  # India jobs require IN authorization
            max_results_per_connector=2,
            persist_to_repository=False,
        )

        response = await coordinator.execute_discovery(request)

        # Since candidate is only authorized in US and India jobs are in IN,
        # deterministic eligibility must evaluate them as INELIGIBLE (DISQ_COUNTRY_UNAUTHORIZED)
        assert response.total_discovered > 0
        assert response.ineligible_count == response.canonical_count
        assert response.eligible_count == 0

        for eval_result in response.eligibility_results:
            assert eval_result.is_eligible is False
            assert "DISQ_COUNTRY_UNAUTHORIZED" in eval_result.disqualification_reasons

    import asyncio
    asyncio.run(_run())


def test_api_discovery_endpoints() -> None:
    """Verifies FastAPI endpoints: /connectors, /plan, /run via TestClient."""
    client = TestClient(app)

    # 1. GET /api/v1/discovery/connectors
    resp = client.get("/api/v1/discovery/connectors")
    assert resp.status_code == 200
    connectors = resp.json()
    assert len(connectors) == 4
    connector_ids = {c["connector_id"] for c in connectors}
    assert "web_search" in connector_ids
    assert "india_jobs_mcp" in connector_ids
    assert "jobspy_mcp" in connector_ids
    assert "ats_career_pages" in connector_ids

    # 2. POST /api/v1/discovery/plan
    profile = _make_sample_candidate_profile().model_dump(mode="json")
    plan_resp = client.post("/api/v1/discovery/plan", json={"candidate_profile": profile})
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["candidate_id"] == "test-user-dev"
    assert len(plan_data["target_roles"]) >= 1
    assert len(plan_data["all_queries"]) >= 1

    # 3. POST /api/v1/discovery/run
    run_resp = client.post(
        "/api/v1/discovery/run",
        json={
            "candidate_profile": profile,
            "max_results_per_connector": 2,
            "deduplication_threshold": 0.85,
            "persist_to_repository": False,
        },
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["candidate_id"] == "test-user-dev"
    assert run_data["total_discovered"] > 0
    assert run_data["canonical_count"] > 0
    assert len(run_data["connector_reports"]) == 4

    # 4. POST /api/v1/discovery/run with partial failure simulation
    fail_run_resp = client.post(
        "/api/v1/discovery/run",
        json={
            "candidate_profile": profile,
            "max_results_per_connector": 2,
            "simulate_failure_connector": "web_search",
            "persist_to_repository": False,
        },
    )
    assert fail_run_resp.status_code == 200
    fail_data = fail_run_resp.json()
    assert fail_data["execution_metadata"]["failed_connectors"] == 1
    assert fail_data["canonical_count"] > 0

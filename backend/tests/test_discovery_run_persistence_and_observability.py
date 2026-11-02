from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.connection import DatabaseManager
from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDiscoveryRunRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
    InMemoryRecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDiscoveryRunRepository,
)
from app.main import app
from app.modules.discovery.connectors.ats_career_page import CompanyCareerPageConnector
from app.modules.discovery.connectors.india_jobs import IndiaJobsMCPConnector
from app.modules.discovery.connectors.jobspy import JobSpyMCPConnector
from app.modules.discovery.connectors.web_search import WebSearchConnector
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import ConnectorStatus, DiscoverySearchQuery
from app.schemas.evidence import EvidenceRecord
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    DiscoveryRun,
    DiscoveryRunStatus,
    TerminationReason,
    WorkflowStage,
    WorkflowTimelineEvent,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def candidate_profile_fixture() -> CandidateCareerProfile:
    ev = EvidenceRecord(
        evidence_id="ev_persist_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Implemented high-throughput distributed microservices in Python with FastAPI.",
        verifiability_weight=0.95,
    )
    skills = [
        AssessedSkill(
            canonical_skill_id="esco:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.90,
            evidence_records=[ev],
        )
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
        total_full_time_experience_months=24,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE],
        preferred_locations=["Remote"],
    )
    return CandidateCareerProfile(
        user_id="usr_cand_persist_test",
        profile_version=1,
        assessed_skills=skills,
        target_career_paths=[target],
        adjacent_career_paths=[],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.92,
    )


@pytest.fixture
def sqlite_test_db(tmp_path) -> DatabaseManager:
    db_file = tmp_path / "test_discovery_runs.db"
    manager = DatabaseManager(f"sqlite:///{db_file}")
    manager.initialize_schema()
    return manager


# ==============================================================================
# 1. SQLite DiscoveryRun Repository Persistence Tests
# ==============================================================================

def test_sqlite_discovery_run_crud(sqlite_test_db: DatabaseManager) -> None:
    repo = SQLiteDiscoveryRunRepository(manager=sqlite_test_db)
    now = datetime.now(timezone.utc)

    # 1. Create and Save
    run = DiscoveryRun(
        run_id="run-test-001",
        candidate_id="cand-123",
        status=DiscoveryRunStatus.INITIALIZING,
        started_at=now,
        target_coverage_goal=4,
        total_discovered_raw=10,
        canonical_count=8,
        duplicate_count=2,
        timeline_events=[
            WorkflowTimelineEvent(
                timestamp=now,
                stage=WorkflowStage.INITIALIZING,
                event_type="WORKFLOW_INITIALIZED",
                summary="Run initialized",
            )
        ],
    )
    repo.save(run)

    # 2. Retrieve by ID
    loaded = repo.get("run-test-001")
    assert loaded is not None
    assert loaded.run_id == "run-test-001"
    assert loaded.candidate_id == "cand-123"
    assert loaded.status == DiscoveryRunStatus.INITIALIZING
    assert loaded.total_discovered_raw == 10
    assert len(loaded.timeline_events) == 1

    # 3. Retrieve Active Run
    active = repo.get_active_run_for_candidate("cand-123")
    assert active is not None
    assert active.run_id == "run-test-001"

    # 4. Update to COMPLETED
    loaded.status = DiscoveryRunStatus.COMPLETED
    loaded.termination_reason = TerminationReason.COVERAGE_SATISFIED
    loaded.completed_at = datetime.now(timezone.utc)
    loaded.eligible_count = 5
    repo.save(loaded)

    # Verify active run is now None (since it's terminal)
    active_after = repo.get_active_run_for_candidate("cand-123")
    assert active_after is None

    # Latest run should still return the completed run
    latest = repo.get_latest_for_candidate("cand-123")
    assert latest is not None
    assert latest.status == DiscoveryRunStatus.COMPLETED
    assert latest.eligible_count == 5


# ==============================================================================
# 2. Workflow Persistence & Real-Time Event Integration
# ==============================================================================

def test_workflow_persists_discovery_run(candidate_profile_fixture: CandidateCareerProfile) -> None:
    async def _run() -> None:
        profile_repo = InMemoryCandidateProfileRepository()
        opp_repo = InMemoryOpportunityRepository()
        cluster_repo = InMemoryDuplicateClusterRepository()
        rec_repo = InMemoryRecommendationRepository()
        run_repo = InMemoryDiscoveryRunRepository()

        profile_repo.save(candidate_profile_fixture)

        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=opp_repo,
            cluster_repo=cluster_repo,
            profile_repo=profile_repo,
            rec_repo=rec_repo,
            run_repo=run_repo,
        )

        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_profile_fixture,
            target_coverage_goal=2,
            max_iterations=1,
            max_tool_calls=5,
            enable_live_discovery=False,
        )

        response = await workflow.run(request)

        assert response.workflow_id is not None
        persisted_run = run_repo.get(response.workflow_id)
        assert persisted_run is not None
        assert persisted_run.status == DiscoveryRunStatus.COMPLETED
        assert persisted_run.candidate_id == candidate_profile_fixture.user_id
        assert persisted_run.response is not None
        assert len(persisted_run.timeline_events) > 0
        assert persisted_run.completed_at is not None

    asyncio.run(_run())


# ==============================================================================
# 3. Disconnect & Recovery: No Duplicate Run Creation
# ==============================================================================

def test_workflow_start_run_reconnect_no_duplicate(
    candidate_profile_fixture: CandidateCareerProfile,
) -> None:
    async def _run() -> None:
        run_repo = InMemoryDiscoveryRunRepository()
        workflow = AdaptiveDiscoveryWorkflow(run_repo=run_repo)

        request = AdaptiveDiscoveryRequest(
            candidate_profile=candidate_profile_fixture,
            target_coverage_goal=3,
            enable_live_discovery=False,
        )

        # First call creates the run
        run_1 = await workflow.start_run(request)
        assert run_1.status in (DiscoveryRunStatus.CREATED, DiscoveryRunStatus.INITIALIZING)

        # Second call for the same candidate while active returns the EXACT SAME run
        run_2 = await workflow.start_run(request)
        assert run_2.run_id == run_1.run_id

    asyncio.run(_run())


# ==============================================================================
# 4. Strict Isolation: Zero Synthetic/Fixture Opportunities in Real Discovery
# ==============================================================================

def test_fixture_data_isolation_from_real_discovery() -> None:
    """Confirms that in live discovery mode (mock_mode=False), connectors NEVER inject fake fixtures."""
    async def _run() -> None:
        query = DiscoverySearchQuery(
            query_id="q_iso_01",
            role_title="Nonexistent Quantum Intern",
            query_string="Nonexistent Quantum Intern",
            expanded_keywords=["qubit", "teleportation"],
            category=OpportunityCategory.INTERNSHIP,
            work_modes=[WorkMode.REMOTE],
            target_locations=["Remote"],
            target_country_codes=["US"],
            seniority_level="INTERN",
            relationship_type=CareerPathRelationship.TARGET,
        )

        # 1. ATS Connector in live mode
        ats_conn = CompanyCareerPageConnector(mock_mode=False)
        ats_res = await ats_conn.search(query, limit=5)
        # Must NOT generate fake 'Acme Cloud' or 'Vercel' mock jobs
        assert ats_res.status != ConnectorStatus.MOCKED_FALLBACK
        for opp in ats_res.opportunities:
            assert "Acme Cloud" not in opp.company_name
            assert opp.category_specific_attributes.get("mode") != "MOCKED_FIXTURE"

        # 2. JobSpy MCP Connector in live mode without binary
        jobspy_conn = JobSpyMCPConnector(mock_mode=False)
        jobspy_res = await jobspy_conn.search(query, limit=5)
        # Must report UNAVAILABLE_MISSING_BINARY honestly rather than returning fake mock listings
        if not jobspy_conn.client.is_binary_available():
            assert jobspy_res.status == ConnectorStatus.UNAVAILABLE_MISSING_BINARY
            assert len(jobspy_res.opportunities) == 0

        # 3. India Jobs MCP Connector in live mode
        india_conn = IndiaJobsMCPConnector(mock_mode=False)
        india_res = await india_conn.search(query, limit=5)
        # Must report UNAVAILABLE_MISSING_BINARY with 0 fake Swiggy/CRED opportunities
        assert india_res.status == ConnectorStatus.UNAVAILABLE_MISSING_BINARY
        assert len(india_res.opportunities) == 0

    asyncio.run(_run())


# ==============================================================================
# 5. Connector Failure Handling & Truthful Reporting
# ==============================================================================

def test_connector_failure_reporting_honesty() -> None:
    async def _run() -> None:
        query = DiscoverySearchQuery(
            query_id="q_fail_01",
            role_title="Backend Engineer",
            query_string="Backend Engineer",
            expanded_keywords=["python"],
            category=OpportunityCategory.FULL_TIME_JOB,
            work_modes=[WorkMode.REMOTE],
            target_locations=["Remote"],
            target_country_codes=["US"],
            seniority_level="MID",
            relationship_type=CareerPathRelationship.TARGET,
        )

        # Fault injection in ATS connector
        failing_ats = CompanyCareerPageConnector(mock_mode=True, simulate_error=True)
        res = await failing_ats.search(query, limit=5)
        assert res.status == ConnectorStatus.ERROR
        assert len(res.opportunities) == 0
        assert res.error_message is not None

    asyncio.run(_run())


# ==============================================================================
# 6. FastAPI Endpoints & Session Recovery (SSE & Polling)
# ==============================================================================

def test_discovery_endpoints_persistence_and_reload(
    candidate_profile_fixture: CandidateCareerProfile,
) -> None:
    import uuid

    # Isolate test run with unique candidate ID to prevent cross-test collisions
    candidate_profile_fixture.user_id = f"usr_cand_reload_{uuid.uuid4().hex[:8]}"

    async def _run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Start discovery run
            start_payload = {
                "candidate_profile": candidate_profile_fixture.model_dump(mode="json"),
                "target_coverage_goal": 2,
                "max_iterations": 1,
                "max_tool_calls": 5,
                "enable_live_discovery": False,
            }
            start_resp = await client.post("/api/v1/orchestration/discovery/start", json=start_payload)
            assert start_resp.status_code == 200
            run_data = start_resp.json()
            run_id = run_data["run_id"]
            assert run_id.startswith("wf-")

            # 2. Session Recovery: Query latest run for candidate
            latest_resp = await client.get(
                f"/api/v1/orchestration/discovery/candidate/{candidate_profile_fixture.user_id}/latest-run"
            )
            assert latest_resp.status_code == 200
            assert latest_resp.json()["run_id"] == run_id

            # 3. Retrieve run by ID
            get_resp = await client.get(f"/api/v1/orchestration/discovery/runs/{run_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["candidate_id"] == candidate_profile_fixture.user_id

            # 4. SSE Stream endpoint initial state test
            req = client.build_request("GET", f"/api/v1/orchestration/discovery/runs/{run_id}/stream")
            stream_resp = await client.send(req, stream=True)
            assert stream_resp.status_code == 200
            assert "text/event-stream" in stream_resp.headers["content-type"]
            first_line = ""
            async for line in stream_resp.aiter_lines():
                if "event: initial_state" in line or "data:" in line:
                    first_line = line
                    break
            assert first_line != ""
            await stream_resp.aclose()

    asyncio.run(_run())


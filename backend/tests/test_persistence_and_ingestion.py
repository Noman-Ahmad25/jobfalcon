from __future__ import annotations

import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.db.connection import DatabaseManager
from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryEligibilityAuditRepository,
    InMemoryOpportunityRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteEligibilityAuditRepository,
    SQLiteOpportunityRepository,
)
from app.modules.ingestion.fixture_adapter import JSONFixtureOpportunityAdapter
from app.modules.ingestion.importer import OpportunityImporter
from app.modules.pipeline.service import run_deterministic_pipeline
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import (
    ConstraintCheckResult,
    ConstraintStatus,
    EligibilityResult,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.pipeline import PipelineEvaluationRequest
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    p = Path(path)
    if p.exists():
        p.unlink()


@pytest.fixture
def db_mgr(temp_db_path):
    mgr = DatabaseManager(f"sqlite:///{temp_db_path}")
    mgr.initialize_schema()
    return mgr


@pytest.fixture
def sample_candidate() -> CandidateCareerProfile:
    ev = EvidenceRecord(
        evidence_id="ev-pers-001",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        source_uri="file:///resumes/candidate_jane.pdf",
        extracted_snippet="Designed high-throughput distributed message bus in Go.",
        observed_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        verifiability_weight=0.9,
    )
    skill = AssessedSkill(
        canonical_skill_id="skill_dist_sys_01",
        skill_name="Distributed Systems",
        proficiency_score=9.0,
        confidence_score=0.95,
        evidence_records=[ev],
        last_practiced_date=date(2026, 8, 1),
    )
    constraints = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        expected_graduation_date=None,
        total_full_time_experience_months=60,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.HYBRID, WorkMode.REMOTE],
        preferred_locations=["San Francisco, CA"],
    )
    return CandidateCareerProfile(
        user_id="usr-jane-100",
        profile_version=1,
        assessed_skills=[skill],
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Senior Distributed Systems Engineer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        adjacent_career_paths=[
            CareerPathNode(
                occupation_code="15-1254.00",
                title="Site Reliability Engineer",
                relationship_type=CareerPathRelationship.ADJACENT,
                adjacency_similarity=0.85,
            )
        ],
        eligibility_constraints=constraints,
        overall_profile_confidence=0.92,
    )


def test_sqlite_candidate_profile_persistence_and_restart(temp_db_path, sample_candidate):
    """Verifies that a candidate profile persists across simulated application restarts."""
    mgr1 = DatabaseManager(f"sqlite:///{temp_db_path}")
    mgr1.initialize_schema()
    repo1 = SQLiteCandidateProfileRepository(mgr1)

    repo1.save(sample_candidate)

    # Simulate restart by instantiating a new DatabaseManager and repository
    mgr2 = DatabaseManager(f"sqlite:///{temp_db_path}")
    repo2 = SQLiteCandidateProfileRepository(mgr2)

    loaded = repo2.get("usr-jane-100")
    assert loaded is not None
    assert loaded.user_id == "usr-jane-100"
    assert loaded.eligibility_constraints.highest_degree_level == DegreeLevel.BACHELORS
    assert loaded.eligibility_constraints.authorized_country_codes == ["US"]
    assert len(loaded.assessed_skills) == 1
    assert loaded.assessed_skills[0].skill_name == "Distributed Systems"
    assert loaded.assessed_skills[0].proficiency_score == 9.0
    assert len(loaded.assessed_skills[0].evidence_records) == 1
    assert loaded.assessed_skills[0].evidence_records[0].source_uri == "file:///resumes/candidate_jane.pdf"

    # List all
    all_profiles = repo2.list_all()
    assert len(all_profiles) == 1

    # Delete
    deleted = repo2.delete("usr-jane-100")
    assert deleted is True
    assert repo2.get("usr-jane-100") is None


def test_ingestion_fixture_and_idempotent_reimport(db_mgr):
    """Verifies fixture ingestion, duplicate clustering, and idempotent repeated imports."""
    opp_repo = SQLiteOpportunityRepository(db_mgr)
    cluster_repo = SQLiteDuplicateClusterRepository(db_mgr, opp_repo=opp_repo)
    importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)

    adapter = JSONFixtureOpportunityAdapter()

    # 1. Initial import
    report1 = importer.import_from_adapter(
        adapter, reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc)
    )
    assert report1.total_fetched == 5
    assert report1.new_opportunities == 5
    assert report1.updated_opportunities == 0
    assert report1.duplicate_opportunities >= 1
    assert opp_repo.count(active_only=False) == 5

    # 2. Re-importing identical fixture must be completely idempotent
    report2 = importer.import_from_adapter(
        adapter, reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc)
    )
    assert report2.total_fetched == 5
    assert report2.new_opportunities == 0
    assert report2.updated_opportunities == 0
    # Opportunity count remains identical
    assert opp_repo.count(active_only=False) == 5


def test_source_update_handling(db_mgr):
    """Verifies that changed descriptions or attributes update existing records without creating duplicates."""
    opp_repo = SQLiteOpportunityRepository(db_mgr)
    cluster_repo = SQLiteDuplicateClusterRepository(db_mgr, opp_repo=opp_repo)
    importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)

    adapter = JSONFixtureOpportunityAdapter()
    importer.import_from_adapter(adapter, reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc))

    original = opp_repo.get("opp_greenhouse_001")
    assert original is not None

    # Simulate updated listing from source
    updated_opp = original.model_copy(deep=True)
    updated_opp.title = "Principal Distributed Systems Engineer"
    updated_opp.sanitized_summary = (
        "Updated summary: Principal Distributed Systems Engineer leading consensus architectures."
    )

    report = importer.import_opportunities([updated_opp], source_system="greenhouse")
    assert report.total_fetched == 1
    assert report.new_opportunities == 0
    assert report.updated_opportunities == 1

    stored = opp_repo.get("opp_greenhouse_001")
    assert stored is not None
    assert stored.title == "Principal Distributed Systems Engineer"
    assert "Principal" in stored.sanitized_summary
    assert opp_repo.count(active_only=False) == 5


def test_duplicate_cluster_provenance_retention(db_mgr):
    """Verifies that duplicate clusters retain all source URLs and do not destructively delete records."""
    opp_repo = SQLiteOpportunityRepository(db_mgr)
    cluster_repo = SQLiteDuplicateClusterRepository(db_mgr, opp_repo=opp_repo)
    importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)

    adapter = JSONFixtureOpportunityAdapter()
    importer.import_from_adapter(adapter, reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc))

    clusters = cluster_repo.list_clusters()
    assert len(clusters) >= 1

    # Find the cluster with opp_greenhouse_001
    gh_cluster = cluster_repo.get_cluster("opp_greenhouse_001")
    assert gh_cluster is not None
    assert gh_cluster.cluster_size >= 2
    assert len(gh_cluster.duplicate_records) >= 1
    assert gh_cluster.duplicate_records[0].duplicate_opportunity_id == "opp_lever_002"

    # Both URLs must be preserved in all_source_urls
    assert "https://boards.greenhouse.io/falconcloud/jobs/401" in gh_cluster.all_source_urls
    assert "https://jobs.lever.co/falconcloud/401-dup" in gh_cluster.all_source_urls

    # Lever listing still exists independently in repository
    lever_opp = opp_repo.get("opp_lever_002")
    assert lever_opp is not None
    assert lever_opp.is_duplicate is True


def test_transaction_rollback_on_failure(db_mgr):
    """Verifies that an error inside manager.transaction() completely rolls back all modifications."""
    opp_repo = SQLiteOpportunityRepository(db_mgr)
    initial_count = opp_repo.count(active_only=False)

    with pytest.raises(RuntimeError, match="Simulated mid-transaction database crash"):
        with db_mgr.transaction() as conn:
            conn.execute(
                """
                INSERT INTO opportunities (
                    opportunity_id, minhash_signature_hex, title, company_name,
                    company_domain_verified, mapped_occupation_code, opportunity_category,
                    work_mode, source_url, source_system, source_job_id,
                    eligibility_rules_json, skill_requirements_json,
                    category_specific_attributes_json, sanitized_summary,
                    posted_at, discovered_at, updated_at, completeness_score,
                    trust_score, is_active, is_duplicate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    "opp_crash_test",
                    "0" * 64,
                    "Crash Test Role",
                    "Crash Corp",
                    1,
                    "15-1252.00",
                    "full_time",
                    "remote",
                    "https://example.com/crash",
                    "test",
                    "crash-1",
                    "{}",
                    "[]",
                    "{}",
                    "Crash summary",
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    1.0,
                    1.0,
                    1,
                    0,
                ),
            )
            # Raise exception midway
            raise RuntimeError("Simulated mid-transaction database crash")

    # Verify that the uncommitted insertion was rolled back
    assert opp_repo.count(active_only=False) == initial_count
    assert opp_repo.get("opp_crash_test") is None


def test_eligibility_audit_persistence_and_pruning(db_mgr, sample_candidate):
    """Verifies saving, retrieving, and pruning deterministic eligibility audit records."""
    profile_repo = SQLiteCandidateProfileRepository(db_mgr)
    profile_repo.save(sample_candidate)

    opp_repo = SQLiteOpportunityRepository(db_mgr)
    cluster_repo = SQLiteDuplicateClusterRepository(db_mgr, opp_repo=opp_repo)
    importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)
    adapter = JSONFixtureOpportunityAdapter()
    importer.import_from_adapter(adapter, reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc))

    audit_repo = SQLiteEligibilityAuditRepository(db_mgr)
    now = datetime.now(timezone.utc)

    # 1. Recent audit
    recent_result = EligibilityResult(
        opportunity_id="opp_greenhouse_001",
        user_id="usr-jane-100",
        status=EligibilityStatus.ELIGIBLE,
        is_eligible=True,
        disqualification_reasons=[],
        uncertainty_caveats=[],
        constraint_checks={
            "degree": ConstraintCheckResult(
                constraint_name="degree",
                status=ConstraintStatus.PASSED,
                rule_code="RULE_DEGREE_PASSED",
                message="Bachelor's satisfied",
                details={},
            )
        },
        evaluated_at=now,
    )
    audit_repo.save_audit(recent_result)

    # 2. Old audit (60 days ago)
    old_result = EligibilityResult(
        opportunity_id="opp_remote_003",
        user_id="usr-jane-100",
        status=EligibilityStatus.INELIGIBLE,
        is_eligible=False,
        disqualification_reasons=["LOCATION_DISQUALIFIED"],
        uncertainty_caveats=[],
        constraint_checks={},
        evaluated_at=now - timedelta(days=60),
    )
    audit_repo.save_audit(old_result)

    user_audits = audit_repo.list_audits_for_user("usr-jane-100")
    assert len(user_audits) == 2

    latest_gh = audit_repo.get_latest_audit("opp_greenhouse_001", "usr-jane-100")
    assert latest_gh is not None
    assert latest_gh.status == EligibilityStatus.ELIGIBLE
    assert latest_gh.is_eligible is True
    assert "degree" in latest_gh.constraint_checks

    # 3. Prune older than 30 days
    pruned_count = audit_repo.prune_older_than(days=30)
    assert pruned_count == 1

    remaining_audits = audit_repo.list_audits_for_user("usr-jane-100")
    assert len(remaining_audits) == 1
    assert remaining_audits[0].opportunity_id == "opp_greenhouse_001"


def test_end_to_end_persisted_deterministic_pipeline(db_mgr, sample_candidate):
    """Verifies end-to-end integration: ingestion -> database -> pipeline evaluation -> audit persistence."""
    profile_repo = SQLiteCandidateProfileRepository(db_mgr)
    opp_repo = SQLiteOpportunityRepository(db_mgr)
    cluster_repo = SQLiteDuplicateClusterRepository(db_mgr, opp_repo=opp_repo)
    audit_repo = SQLiteEligibilityAuditRepository(db_mgr)

    # 1. Ingest opportunities
    importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)
    adapter = JSONFixtureOpportunityAdapter()
    importer.import_from_adapter(adapter, reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc))

    # 2. Persist candidate profile
    profile_repo.save(sample_candidate)

    # 3. Retrieve loaded entities from database
    persisted_profile = profile_repo.get("usr-jane-100")
    persisted_opps = opp_repo.list_all(active_only=True)

    assert persisted_profile is not None
    assert len(persisted_opps) >= 4

    # 4. Run deterministic pipeline
    req = PipelineEvaluationRequest(
        candidate_profile=persisted_profile,
        opportunities=persisted_opps,
        reference_time=datetime(2026, 9, 15, tzinfo=timezone.utc),
    )
    pipeline_res = run_deterministic_pipeline(req)

    assert pipeline_res.canonical_count >= 3
    assert pipeline_res.eligible_canonical_count >= 1

    # 5. Persist audit logs for all evaluation results
    for eval_res in pipeline_res.eligibility_results:
        audit_repo.save_audit(eval_res)

    saved_audits = audit_repo.list_audits_for_user("usr-jane-100")
    assert len(saved_audits) == len(pipeline_res.eligibility_results)


def test_in_memory_repositories_contract_parity(sample_candidate):
    """Verifies that in-memory repository implementations faithfully implement repository contracts."""
    prof_repo = InMemoryCandidateProfileRepository()
    opp_repo = InMemoryOpportunityRepository()
    cluster_repo = InMemoryDuplicateClusterRepository(opp_repo=opp_repo)
    audit_repo = InMemoryEligibilityAuditRepository()

    # Profile
    prof_repo.save(sample_candidate)
    assert prof_repo.get(sample_candidate.user_id) is not None
    assert len(prof_repo.list_all()) == 1
    assert prof_repo.delete(sample_candidate.user_id) is True
    assert prof_repo.get(sample_candidate.user_id) is None

    # Opportunity
    opp = PolymorphicOpportunity(
        opportunity_id="opp_inmem_01",
        minhash_signature_hex="f" * 64,
        title="Test Role",
        company_name="Test Corp",
        company_domain_verified=True,
        mapped_occupation_code="15-1252.00",
        eligibility_rules=OpportunityEligibilityRules(
            opportunity_category=OpportunityCategory.FULL_TIME_JOB,
            work_mode=WorkMode.REMOTE,
            eligible_country_codes=["US"],
            minimum_degree_required=DegreeLevel.BACHELORS,
        ),
        skill_requirements=[],
        category_specific_attributes={"source_job_id": "test-101"},
        sanitized_summary="Test role description with sufficient length for validation.",
        source_url="https://example.com/test",
        posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        discovered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completeness_score=0.9,
        trust_score=0.9,
    )
    opp_repo.save(opp, source_system="greenhouse", source_job_id="test-101")
    assert opp_repo.count() == 1
    assert opp_repo.get("opp_inmem_01") is not None
    assert opp_repo.get_by_source("greenhouse", "test-101") is not None

    # Audit & Prune
    now = datetime.now(timezone.utc)
    res_recent = EligibilityResult(
        opportunity_id="opp_inmem_01",
        user_id="usr-01",
        status=EligibilityStatus.ELIGIBLE,
        is_eligible=True,
        disqualification_reasons=[],
        uncertainty_caveats=[],
        constraint_checks={},
        evaluated_at=now,
    )
    res_old = EligibilityResult(
        opportunity_id="opp_inmem_01",
        user_id="usr-01",
        status=EligibilityStatus.INELIGIBLE,
        is_eligible=False,
        disqualification_reasons=["DEGREE_DISQUALIFIED"],
        uncertainty_caveats=[],
        constraint_checks={},
        evaluated_at=now - timedelta(days=50),
    )
    audit_repo.save_audit(res_recent)
    audit_repo.save_audit(res_old)
    assert len(audit_repo.list_audits_for_user("usr-01")) == 2
    pruned = audit_repo.prune_older_than(days=30)
    assert pruned == 1
    assert len(audit_repo.list_audits_for_user("usr-01")) == 1

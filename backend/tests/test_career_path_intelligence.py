from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteCareerPathRepository,
    SQLiteOpportunityRepository,
)
from app.main import app
from app.modules.career_path.service import CareerPathIntelligenceService
from app.modules.profiling.llm_client import BaseLLMClient
from app.schemas.career_path import (
    ActionHorizon,
    ActionProgressStatus,
    CareerPathAssessmentResponse,
    OpportunityMarketInsight,
    RoleReadiness,
    RoleTargetAssessment,
    SkillRequirementImportance,
    TargetRoleRelationship,
)
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.gap_analysis import ActionType, GapImportance
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def candidate_backend_dev() -> CandidateCareerProfile:
    """Creates a junior backend candidate with Python and PostgreSQL evidence."""
    ev1 = EvidenceRecord(
        evidence_id="ev_py_101",
        source_type=EvidenceSourceType.VERIFIED_CODE_REPOSITORY,
        source_uri="https://github.com/candidate/backend-api",
        extracted_snippet="Built asynchronous REST API using Python and FastAPI with pytest suite.",
        verifiability_weight=0.90,
    )
    ev2 = EvidenceRecord(
        evidence_id="ev_pg_101",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        source_uri="https://github.com/candidate/backend-api",
        extracted_snippet="Designed relational schemas in PostgreSQL with index optimization.",
        verifiability_weight=0.85,
    )
    ev3 = EvidenceRecord(
        evidence_id="ev_sql_101",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        source_uri="https://github.com/candidate/backend-api",
        extracted_snippet="Wrote complex analytical SQL queries and database migrations.",
        verifiability_weight=0.85,
    )

    skill_py = AssessedSkill(
        canonical_skill_id="http://data.europa.eu/esco/skill/python",
        skill_name="Python",
        proficiency_score=8.0,
        confidence_score=0.90,
        evidence_records=[ev1],
    )
    skill_pg = AssessedSkill(
        canonical_skill_id="http://data.europa.eu/esco/skill/postgresql",
        skill_name="PostgreSQL",
        proficiency_score=7.5,
        confidence_score=0.85,
        evidence_records=[ev2],
    )
    skill_sql = AssessedSkill(
        canonical_skill_id="http://data.europa.eu/esco/skill/sql",
        skill_name="SQL",
        proficiency_score=8.0,
        confidence_score=0.85,
        evidence_records=[ev3],
    )

    return CandidateCareerProfile(
        user_id="usr_cand_backend_01",
        profile_version=1,
        assessed_skills=[skill_py, skill_pg, skill_sql],
        current_career_path=CareerPathNode(
            occupation_code="15-1252.00",
            title="Software Developer",
            relationship_type=CareerPathRelationship.CURRENT,
            adjacency_similarity=1.0,
        ),
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Backend Software Engineer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        adjacent_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Full Stack Developer",
                relationship_type=CareerPathRelationship.ADJACENT,
                adjacency_similarity=0.80,
            )
        ],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            requires_visa_sponsorship=False,
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled_student=False,
            total_full_time_experience_months=18,
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
            preferred_locations=["San Francisco, CA"],
        ),
        overall_profile_confidence=0.88,
    )


@pytest.fixture
def candidate_student_with_uncertainties() -> CandidateCareerProfile:
    """Creates a student candidate with missing graduation date and visa requirement."""
    ev = EvidenceRecord(
        evidence_id="ev_py_stud",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Coursework project analyzing datasets with Python pandas.",
        verifiability_weight=0.60,
    )
    skill_py = AssessedSkill(
        canonical_skill_id="http://data.europa.eu/esco/skill/python",
        skill_name="Python",
        proficiency_score=6.0,
        confidence_score=0.60,
        evidence_records=[ev],
    )

    return CandidateCareerProfile(
        user_id="usr_cand_student_02",
        profile_version=1,
        assessed_skills=[skill_py],
        current_career_path=None,
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1251.00",
                title="Machine Learning Engineer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        adjacent_career_paths=[],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["IN"],
            requires_visa_sponsorship=True,
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled_student=True,
            expected_graduation_date=None,  # Missing graduation window
            total_full_time_experience_months=0,
            allowed_opportunity_categories=[OpportunityCategory.INTERNSHIP, OpportunityCategory.FULL_TIME_JOB],
            allowed_work_modes=[WorkMode.REMOTE],
            preferred_locations=[],
        ),
        overall_profile_confidence=0.65,
    )


@pytest.fixture
def sample_opportunities() -> list[PolymorphicOpportunity]:
    """Sample opportunity fixtures representing real ATS listings."""
    now_utc = datetime.now(timezone.utc)
    rules = OpportunityEligibilityRules(
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        work_mode=WorkMode.REMOTE,
        location_city_country=[],
    )

    opp1 = PolymorphicOpportunity(
        opportunity_id="opp_be_001",
        minhash_signature_hex="abcdef0123456789",
        title="Backend Software Engineer",
        company_name="CloudScale Systems",
        mapped_occupation_code="15-1252.00",
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        work_mode=WorkMode.REMOTE,
        source_url="https://jobs.example.com/be001",
        category_specific_attributes={"source_system": "greenhouse"},
        eligibility_rules=rules,
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="http://data.europa.eu/esco/skill/python",
                skill_name="Python",
                is_mandatory=True,
                minimum_proficiency_expected=7.0,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="http://data.europa.eu/esco/skill/docker",
                skill_name="Docker",
                is_mandatory=True,
                minimum_proficiency_expected=6.0,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="http://data.europa.eu/esco/skill/redis",
                skill_name="Redis",
                is_mandatory=False,
                minimum_proficiency_expected=5.0,
            ),
        ],
        sanitized_summary="Scale distributed backend microservices in Python with Docker.",
        posted_at=now_utc,
        discovered_at=now_utc,
        updated_at=now_utc,
        completeness_score=0.95,
        trust_score=0.90,
    )

    opp2 = PolymorphicOpportunity(
        opportunity_id="opp_be_002",
        minhash_signature_hex="1234567890abcdef",
        title="Python Backend Developer",
        company_name="FinTech Dynamics",
        mapped_occupation_code="15-1252.00",
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        work_mode=WorkMode.REMOTE,
        source_url="https://jobs.example.com/be002",
        category_specific_attributes={"source_system": "ashby"},
        eligibility_rules=rules,
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="http://data.europa.eu/esco/skill/python",
                skill_name="Python",
                is_mandatory=True,
                minimum_proficiency_expected=7.5,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="http://data.europa.eu/esco/skill/postgresql",
                skill_name="PostgreSQL",
                is_mandatory=True,
                minimum_proficiency_expected=7.0,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="http://data.europa.eu/esco/skill/docker",
                skill_name="Docker",
                is_mandatory=False,
                minimum_proficiency_expected=5.5,
            ),
        ],
        sanitized_summary="Design robust APIs with Python, PostgreSQL, and containerization.",
        posted_at=now_utc,
        discovered_at=now_utc,
        updated_at=now_utc,
        completeness_score=0.92,
        trust_score=0.88,
    )

    return [opp1, opp2]


# ==============================================================================
# 1. Target and Adjacent Role Classification
# ==============================================================================

def test_target_and_adjacent_role_classification(
    candidate_backend_dev: CandidateCareerProfile,
    sample_opportunities: list[PolymorphicOpportunity],
) -> None:
    """Verifies that direct targets, adjacent options, and exploratory roles are accurately categorized."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(
        candidate=candidate_backend_dev,
        discovered_opportunities=sample_opportunities,
    )

    assert assessment.total_target_roles >= 1
    assert assessment.total_adjacent_roles >= 1
    assert assessment.total_exploratory_roles >= 1

    # Backend Engineer should be DIRECT_TARGET
    be_eval = next((r for r in assessment.role_assessments if r.role_title == "Backend Software Engineer"), None)
    assert be_eval is not None
    assert be_eval.relationship == TargetRoleRelationship.DIRECT_TARGET
    assert be_eval.canonical_occupation_code == "15-1252.00"
    assert be_eval.skill_overlap_ratio > 0.20

    # Full Stack should be ADJACENT_OPTION
    fs_eval = next((r for r in assessment.role_assessments if r.role_title == "Full Stack Developer"), None)
    assert fs_eval is not None
    assert fs_eval.relationship == TargetRoleRelationship.ADJACENT_OPTION

    # Mobile Developer should be EXPLORATORY_POSSIBILITY (zero mobile evidence)
    mobile_eval = next((r for r in assessment.role_assessments if r.role_title == "Mobile Developer"), None)
    assert mobile_eval is not None
    assert mobile_eval.relationship == TargetRoleRelationship.EXPLORATORY_POSSIBILITY
    assert mobile_eval.readiness == RoleReadiness.EXPLORATORY


# ==============================================================================
# 2. Evidence Traceability & Provenance Grounding
# ==============================================================================

def test_evidence_traceability_and_citations(
    candidate_backend_dev: CandidateCareerProfile,
) -> None:
    """Verifies that assessed roles link back to authentic candidate EvidenceRecord citations."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(candidate=candidate_backend_dev)

    be_eval = next(r for r in assessment.role_assessments if r.role_title == "Backend Software Engineer")
    assert len(be_eval.supporting_skills) > 0
    assert "Python" in be_eval.supporting_skills or "PostgreSQL" in be_eval.supporting_skills

    # Supporting evidence must contain valid citation IDs matching the candidate profile
    assert len(be_eval.supporting_evidence) > 0
    citation_ids = [c.evidence_id for c in be_eval.supporting_evidence]
    assert "ev_py_101" in citation_ids or "ev_pg_101" in citation_ids
    assert be_eval.supporting_evidence[0].snippet != ""


# ==============================================================================
# 3. Unsupported Role Transitions & Explicit Uncertainty
# ==============================================================================

def test_unsupported_or_uncertain_role_transitions(
    candidate_backend_dev: CandidateCareerProfile,
) -> None:
    """Verifies that requesting an unmapped or unevidenced target role returns explicit uncertainty."""
    service = CareerPathIntelligenceService()
    custom_target = "Quantum Cryptography Architect"

    assessment = service.assess_candidate_career_paths(
        candidate=candidate_backend_dev,
        target_role_overrides=[custom_target],
    )

    custom_eval = next((r for r in assessment.role_assessments if r.role_title == custom_target), None)
    assert custom_eval is not None
    assert custom_eval.relationship == TargetRoleRelationship.DIRECT_TARGET
    assert custom_eval.readiness == RoleReadiness.EXPLORATORY
    assert custom_eval.canonical_occupation_code is None
    assert "insufficient" in custom_eval.feasibility_rationale.lower()
    assert len(custom_eval.eligibility_uncertainties) > 0


# ==============================================================================
# 4. Missing and Contradictory Evidence & Eligibility Caveats
# ==============================================================================

def test_student_missing_graduation_and_visa_uncertainty(
    candidate_student_with_uncertainties: CandidateCareerProfile,
) -> None:
    """Verifies that missing graduation windows and visa requirements are surfaced explicitly."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(candidate=candidate_student_with_uncertainties)

    for role_eval in assessment.role_assessments:
        unc_text = " ".join(role_eval.eligibility_uncertainties)
        assert "Graduation date not specified" in unc_text
        assert "visa sponsorship" in unc_text.lower()


# ==============================================================================
# 5. Career Path Graph Consistency & Cycle Handling
# ==============================================================================

def test_career_path_graph_cycle_safety(
    candidate_backend_dev: CandidateCareerProfile,
) -> None:
    """Verifies that the generated career path transition graph is strictly cycle-free."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(candidate=candidate_backend_dev)

    graph = assessment.career_path_graph
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
    assert graph.is_cycle_free is True
    assert graph.baseline_role_title is not None

    # Verify each edge has meaningful basis and development gaps
    for edge in graph.edges:
        assert edge.source_role != edge.target_role
        assert edge.feasibility_score >= 0.0 and edge.feasibility_score <= 1.0
        assert edge.estimated_effort_level in ("LOW", "MEDIUM", "HIGH")
        assert len(edge.basis_description) > 10


# ==============================================================================
# 6. Development Action Relevance to Actual Gaps
# ==============================================================================

def test_development_plan_practical_actions(
    candidate_backend_dev: CandidateCareerProfile,
    sample_opportunities: list[PolymorphicOpportunity],
) -> None:
    """Verifies that development actions address genuine skill gaps with concrete, measurable criteria."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(
        candidate=candidate_backend_dev,
        discovered_opportunities=sample_opportunities,
    )

    plan = assessment.development_plan
    assert plan.total_actions > 0
    assert len(plan.short_term_actions) + len(plan.long_term_actions) == plan.total_actions

    for action in plan.short_term_actions + plan.long_term_actions:
        # Must have practical activities rather than generic course lists
        assert action.action_type in (
            ActionType.PORTFOLIO_BUILD,
            ActionType.PROJECT_ENHANCEMENT,
            ActionType.CONCEPT_STUDY,
            ActionType.EVIDENCE_COLLECTION,
        )
        assert "repository" in action.concrete_activity.lower() or "tests" in action.concrete_activity.lower() or "architectural" in action.concrete_activity.lower()
        # Must have measurable completion criterion
        assert len(action.measurable_completion_criterion) > 15
        # Must have verifiable evidence to produce
        assert len(action.verifiable_evidence_to_produce) > 10
        # Must have priority rationale
        assert len(action.priority_rationale) > 10


# ==============================================================================
# 7. Action Dependencies and Horizon Separation
# ==============================================================================

def test_action_dependencies_and_horizons(
    candidate_backend_dev: CandidateCareerProfile,
) -> None:
    """Verifies clear separation of short-term vs long-term actions and appropriate dependency wiring."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(candidate=candidate_backend_dev)

    plan = assessment.development_plan
    # Verify short term vs long term classification
    for st_act in plan.short_term_actions:
        assert st_act.horizon == ActionHorizon.SHORT_TERM
    for lt_act in plan.long_term_actions:
        assert lt_act.horizon == ActionHorizon.LONG_TERM

    # If long-term actions exist, check that they can depend on foundational short-term actions
    if plan.long_term_actions and plan.short_term_actions:
        assert len(plan.long_term_actions[0].dependencies) >= 1
        assert plan.long_term_actions[0].dependencies[0] == plan.short_term_actions[0].action_id


# ==============================================================================
# 8. Opportunity-Aware Prioritization & Honest Limitation Disclosure
# ==============================================================================

def test_opportunity_aware_prioritization_and_disclosure(
    candidate_backend_dev: CandidateCareerProfile,
    sample_opportunities: list[PolymorphicOpportunity],
) -> None:
    """Verifies that discovered opportunities calibrate skill importance with honest disclosure."""
    service = CareerPathIntelligenceService()

    # Case A: Discovered opportunities present
    with_opps = service.assess_candidate_career_paths(
        candidate=candidate_backend_dev,
        discovered_opportunities=sample_opportunities,
    )
    insights = with_opps.development_plan.market_insights
    assert insights.total_opportunities_analyzed == 2
    assert insights.data_sufficiency_level == "LIMITED_SAMPLE"
    assert "greenhouse" in insights.sources_represented
    assert "ashby" in insights.sources_represented
    assert "does not represent an exhaustive census" in insights.limitation_disclosure

    # Docker should be detected as explicitly required across sample
    docker_signal = next((s for s in insights.recurring_skills if s.skill_name.lower() == "docker"), None)
    assert docker_signal is not None
    assert docker_signal.signal_type == SkillRequirementImportance.EXPLICITLY_REQUIRED

    # Case B: Zero discovered opportunities (graceful fallback)
    no_opps = service.assess_candidate_career_paths(
        candidate=candidate_backend_dev,
        discovered_opportunities=[],
    )
    no_opps_insights = no_opps.development_plan.market_insights
    assert no_opps_insights.total_opportunities_analyzed == 0
    assert no_opps_insights.data_sufficiency_level == "NO_DISCOVERED_DATA"
    assert "purely from standardized O*NET/ESCO" in no_opps_insights.limitation_disclosure


# ==============================================================================
# 9. LLM Failure & Deterministic Fallback
# ==============================================================================

class CrashingMockLLM(BaseLLMClient):
    """Mock LLM client that intentionally fails to simulate outage or network crash."""

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model, max_retries: int = 2):
        raise ConnectionResetError("LiteLLM Gateway Unreachable (Simulated Outage)")


def test_deterministic_fallback_on_llm_failure(
    candidate_backend_dev: CandidateCareerProfile,
) -> None:
    """Verifies that LLM crashes do not corrupt plan generation or cause system exceptions."""
    crashing_llm = CrashingMockLLM()
    service = CareerPathIntelligenceService(llm_client=crashing_llm)

    # Should execute successfully without throwing exceptions
    assessment = service.assess_candidate_career_paths(candidate=candidate_backend_dev)
    assert assessment.development_plan.total_actions > 0
    assert len(assessment.development_plan.short_term_actions) > 0
    assert "Personalized development plan" in assessment.development_plan.plan_summary


# ==============================================================================
# 10. Persistence, API Endpoints & Progress Tracking
# ==============================================================================

def test_api_career_path_endpoints_and_progress_tracking(
    candidate_backend_dev: CandidateCareerProfile,
    sample_opportunities: list[PolymorphicOpportunity],
) -> None:
    """Verifies FastAPI career path endpoints, SQLite persistence, and action progress updating."""
    # Seed candidate and opportunities in SQLite repositories
    cand_repo = SQLiteCandidateProfileRepository()
    opp_repo = SQLiteOpportunityRepository()
    career_repo = SQLiteCareerPathRepository()

    cand_repo.save(candidate_backend_dev)
    opp_repo.save_batch(sample_opportunities)

    client = TestClient(app)

    # 1. GET /api/v1/career-path/candidate/{user_id}/assessment
    resp = client.get(f"/api/v1/career-path/candidate/{candidate_backend_dev.user_id}/assessment")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == candidate_backend_dev.user_id
    assert len(data["role_assessments"]) > 0
    assert data["career_path_graph"]["is_cycle_free"] is True

    # 2. GET /api/v1/career-path/candidate/{user_id}/roles
    roles_resp = client.get(f"/api/v1/career-path/candidate/{candidate_backend_dev.user_id}/roles")
    assert roles_resp.status_code == 200
    roles_data = roles_resp.json()
    assert len(roles_data) >= 2

    # 3. GET /api/v1/career-path/candidate/{user_id}/plan
    plan_resp = client.get(f"/api/v1/career-path/candidate/{candidate_backend_dev.user_id}/plan")
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert len(plan_data["short_term_actions"]) > 0

    first_action_id = plan_data["short_term_actions"][0]["action_id"]

    # 4. PATCH /api/v1/career-path/candidate/{user_id}/actions/{action_id}
    patch_resp = client.patch(
        f"/api/v1/career-path/candidate/{candidate_backend_dev.user_id}/actions/{first_action_id}",
        json={
            "status": "COMPLETED",
            "verification_artifact_url": "https://github.com/candidate/completed-demo-repo",
            "candidate_notes": "Implemented multi-stage Docker build with automated pytest suite in GitHub Actions.",
        },
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["action_id"] == first_action_id
    assert patched_data["status"] == "COMPLETED"
    assert patched_data["completed_at"] is not None
    assert patched_data["verification_artifact_url"] == "https://github.com/candidate/completed-demo-repo"

    # 5. Verify persistence in subsequent GET
    actions_resp = client.get(f"/api/v1/career-path/candidate/{candidate_backend_dev.user_id}/actions")
    assert actions_resp.status_code == 200
    actions_list = actions_resp.json()
    updated_item = next(a for a in actions_list if a["action_id"] == first_action_id)
    assert updated_item["status"] == "COMPLETED"
    assert updated_item["verification_artifact_url"] == "https://github.com/candidate/completed-demo-repo"

    # 6. POST refresh endpoint
    refresh_resp = client.post(
        f"/api/v1/career-path/candidate/{candidate_backend_dev.user_id}/refresh",
        json={"include_repo_opportunities": True},
    )
    assert refresh_resp.status_code == 200

    # 7. Non-existent candidate returns 404
    missing_resp = client.get("/api/v1/career-path/candidate/non_existent_user_9999/assessment")
    assert missing_resp.status_code == 404


# ==============================================================================
# 11. Ethical Disclaimer Invariant
# ==============================================================================

def test_mandatory_ethical_disclaimer(
    candidate_backend_dev: CandidateCareerProfile,
) -> None:
    """Verifies that development plans always present a non-negotiable ethical disclaimer."""
    service = CareerPathIntelligenceService()
    assessment = service.assess_candidate_career_paths(candidate=candidate_backend_dev)
    disclaimer = assessment.development_plan.ethical_disclaimer
    assert "does not guarantee employment" in disclaimer.lower()

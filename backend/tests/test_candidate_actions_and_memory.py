from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest

from app.db.repositories.sqlite_repository import (
    SQLiteCandidateActionRepository,
    SQLiteCandidateProfileRepository,
    SQLiteCareerMemoryRepository,
    SQLiteOpportunityRepository,
)
from app.main import app
from app.modules.eligibility.engine import evaluate_eligibility
from app.schemas.action import (
    ActionReasonCategory,
    ActionType,
    CandidateOpportunityActionRecord,
    RecordActionRequest,
)
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.eligibility import (
    DISQ_CATEGORY_MISMATCH,
    DISQ_EXPERIENCE_BELOW_MINIMUM,
    DISQ_LOCATION_MISMATCH,
    DISQ_VISA_SPONSORSHIP_UNAVAILABLE,
    DISQ_WORK_MODE_MISMATCH,
    VACANCY_EXPIRED_UNAVAILABLE,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.memory import (
    CandidateCareerMemoryItem,
    CreateMemoryRequest,
    MemoryType,
    ProvenanceLevel,
    UpdateMemoryRequest,
)
from app.schemas.opportunity import OpportunityEligibilityRules, PolymorphicOpportunity
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def test_client():
    return TestClient(app)


def create_candidate_fixture(user_id: str) -> CandidateCareerProfile:
    rec = EvidenceRecord(
        evidence_id=f"ev_{user_id}",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Built Python APIs for 2 years",
        verifiability_weight=0.9,
    )
    skill = AssessedSkill(
        canonical_skill_id="esco:skill:python",
        skill_name="Python",
        proficiency_score=8.0,
        confidence_score=0.9,
        evidence_records=[rec],
    )
    target = CareerPathNode(
        occupation_code="2512.1",
        title="Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
    )
    elig = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        expected_graduation_date=date(2025, 5, 15),
        total_full_time_experience_months=24,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE],
        preferred_locations=["San Francisco, CA"],
    )
    return CandidateCareerProfile(
        user_id=user_id,
        assessed_skills=[skill],
        target_career_paths=[target],
        eligibility_constraints=elig,
        overall_profile_confidence=0.9,
    )


def create_opportunity_fixture(opp_id: str, min_exp: int = 36) -> PolymorphicOpportunity:
    return PolymorphicOpportunity(
        opportunity_id=opp_id,
        minhash_signature_hex="1234567890abcdef",
        title="Software Engineer",
        company_name="FalconCorp",
        mapped_occupation_code="2512.1",
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        sanitized_summary="A Python backend engineering role.",
        source_url="https://falconcorp.example.com/apply",
        posted_at=datetime.now(timezone.utc),
        completeness_score=0.9,
        trust_score=0.95,
        eligibility_rules=OpportunityEligibilityRules(
            opportunity_category=OpportunityCategory.FULL_TIME_JOB,
            eligible_country_codes=["US"],
            sponsors_work_visa=False,
            minimum_degree_required=DegreeLevel.BACHELORS,
            requires_active_student_status=False,
            min_experience_months=min_exp,  # Candidate has 24, so shortfall if >24
            work_mode=WorkMode.REMOTE,
        ),
    )


# =====================================================================
# 1. ACTION LEDGER AND TRANSITION TESTS
# =====================================================================


def test_candidate_action_transitions():
    user_repo = SQLiteCandidateProfileRepository()
    opp_repo = SQLiteOpportunityRepository()
    action_repo = SQLiteCandidateActionRepository()

    user_id = f"usr_trans_{int(datetime.now().timestamp() * 1000)}"
    user_repo.save(create_candidate_fixture(user_id))

    opp_101 = f"opp_trans_101_{int(datetime.now().timestamp() * 1000)}"
    opp_102 = f"opp_trans_102_{int(datetime.now().timestamp() * 1000)}"
    opp_repo.save(create_opportunity_fixture(opp_101))
    opp_repo.save(create_opportunity_fixture(opp_102))

    # Step 1: Save an opportunity
    action_1 = CandidateOpportunityActionRecord(
        id=f"act_001_{int(datetime.now().timestamp() * 1000)}",
        user_id=user_id,
        opportunity_id=opp_101,
        action_type=ActionType.SAVED,
        previous_state=None,
        reason_category=ActionReasonCategory.GENERAL,
        user_notes="Looks like an interesting role",
    )
    action_repo.record_action(action_1)

    latest = action_repo.get_latest_actions(user_id)
    assert opp_101 in latest
    assert latest[opp_101].action_type == ActionType.SAVED

    # Step 2: Transition from SAVED to APPLIED
    action_2 = CandidateOpportunityActionRecord(
        id=f"act_002_{int(datetime.now().timestamp() * 1000)}",
        user_id=user_id,
        opportunity_id=opp_101,
        action_type=ActionType.APPLIED,
        previous_state=ActionType.SAVED.value,
        reason_category=ActionReasonCategory.GENERAL,
        user_notes="Submitted direct application via company career page",
    )
    action_repo.record_action(action_2)

    latest_after_apply = action_repo.get_latest_actions(user_id)
    assert latest_after_apply[opp_101].action_type == ActionType.APPLIED
    assert latest_after_apply[opp_101].previous_state == ActionType.SAVED.value

    # Step 3: Dismiss another opportunity due to SALARY
    action_3 = CandidateOpportunityActionRecord(
        id=f"act_003_{int(datetime.now().timestamp() * 1000)}",
        user_id=user_id,
        opportunity_id=opp_102,
        action_type=ActionType.DISMISSED,
        previous_state=None,
        reason_category=ActionReasonCategory.SALARY,
        user_notes="Compensation is below target minimum",
    )
    action_repo.record_action(action_3)

    summary = action_repo.get_actions_summary(user_id)
    assert opp_101 in summary.applied_opportunity_ids
    assert opp_101 not in summary.saved_opportunity_ids
    assert opp_102 in summary.dismissed_opportunity_ids
    assert summary.total_actions_recorded == 3

    # Step 4: Verify audit history order
    history = action_repo.get_action_history(user_id, opportunity_id=opp_101)
    assert len(history) == 2
    assert history[0].action_type == ActionType.APPLIED
    assert history[1].action_type == ActionType.SAVED


def test_soft_override_action():
    user_repo = SQLiteCandidateProfileRepository()
    opp_repo = SQLiteOpportunityRepository()
    action_repo = SQLiteCandidateActionRepository()

    user_id = f"usr_over_{int(datetime.now().timestamp() * 1000)}"
    user_repo.save(create_candidate_fixture(user_id))

    opp_id = f"opp_over_{int(datetime.now().timestamp() * 1000)}"
    opp_repo.save(create_opportunity_fixture(opp_id))

    action = CandidateOpportunityActionRecord(
        id=f"act_over_{int(datetime.now().timestamp() * 1000)}",
        user_id=user_id,
        opportunity_id=opp_id,
        action_type=ActionType.SOFT_OVERRIDDEN,
        previous_state=None,
        reason_category=ActionReasonCategory.EXPERIENCE_OVERRIDE,
        soft_override_rationale="I have 2 years of professional open-source production experience equivalent to 3 years full-time.",
    )
    action_repo.record_action(action)

    overridden = action_repo.get_overridden_opportunity_ids(user_id)
    assert opp_id in overridden

    summary = action_repo.get_actions_summary(user_id)
    assert opp_id in summary.soft_overridden_opportunity_ids


# =====================================================================
# 2. CAREER MEMORY VERSIONING TESTS
# =====================================================================


def test_career_memory_versioning_and_provenance():
    user_repo = SQLiteCandidateProfileRepository()
    memory_repo = SQLiteCareerMemoryRepository()

    user_id = f"usr_mem_{int(datetime.now().timestamp() * 1000)}"
    user_repo.save(create_candidate_fixture(user_id))

    # Create initial version
    mem_v1_id = f"mem_v1_{int(datetime.now().timestamp() * 1000)}"
    item_v1 = CandidateCareerMemoryItem(
        memory_id=mem_v1_id,
        user_id=user_id,
        memory_type=MemoryType.CAREER_GOAL,
        statement="Targeting Senior Backend Engineer roles with FastAPI and Python.",
        provenance_level=ProvenanceLevel.USER_PROVIDED,
        confidence_score=1.0,
        version=1,
    )
    memory_repo.add_memory(item_v1)

    active_items = memory_repo.list_active_memories(user_id)
    assert len(active_items) == 1
    assert active_items[0].statement == "Targeting Senior Backend Engineer roles with FastAPI and Python."
    assert active_items[0].version == 1
    assert active_items[0].is_active is True

    # Update to Version 2 with explicit change reason
    item_v2 = memory_repo.update_memory(
        user_id=user_id,
        current_memory_id=mem_v1_id,
        new_statement="Pivoting to AI Systems & Agentic Orchestration roles using Python and LangGraph.",
        change_reason="Candidate completed multi-agent certification and wants to focus on agentic systems.",
        provenance_level=ProvenanceLevel.USER_PROVIDED,
        confidence_score=0.95,
    )

    assert item_v2.version == 2
    assert item_v2.is_active is True
    assert item_v2.change_reason == "Candidate completed multi-agent certification and wants to focus on agentic systems."

    # Check that previous version was superseded
    old_v1 = memory_repo.get_memory(mem_v1_id)
    assert old_v1 is not None
    assert old_v1.is_active is False
    assert old_v1.superseded_by == item_v2.memory_id
    assert old_v1.effective_to is not None

    # Check active list returns only the new active version
    active_now = memory_repo.list_active_memories(user_id)
    assert len(active_now) == 1
    assert active_now[0].memory_id == item_v2.memory_id
    assert active_now[0].version == 2

    # Check full version lineage
    lineage = memory_repo.get_memory_history(user_id, item_v2.memory_id)
    assert len(lineage) == 2
    versions = [m.version for m in lineage]
    assert 1 in versions
    assert 2 in versions


# =====================================================================
# 3. ELIGIBILITY HARD VS SOFT VS UNAVAILABLE TESTS
# =====================================================================


def test_soft_vs_hard_disqualification():
    cand = create_candidate_fixture("user_soft_test")
    opp = create_opportunity_fixture("opp_soft_test", min_exp=36)

    # Experience is 24 months, opportunity requires 36 months -> Soft failure
    result = evaluate_eligibility(cand, opp)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_EXPERIENCE_BELOW_MINIMUM in result.soft_disqualifications
    assert result.hard_disqualifications == []
    assert result.is_soft_ineligible is True  # Eligible for user soft-override
    assert result.is_vacancy_expired is False


def test_hard_disqualification_cannot_be_soft_ineligible():
    cand = create_candidate_fixture("user_hard_test")
    opp = create_opportunity_fixture("opp_hard_test", min_exp=36)

    # Add hard failure (visa sponsorship required but not provided)
    cand.eligibility_constraints.requires_visa_sponsorship = True
    opp.eligibility_rules.sponsors_work_visa = False

    result = evaluate_eligibility(cand, opp)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_VISA_SPONSORSHIP_UNAVAILABLE in result.hard_disqualifications
    assert DISQ_EXPERIENCE_BELOW_MINIMUM in result.soft_disqualifications
    assert result.is_soft_ineligible is False  # Cannot soft-override because of hard visa disqualification


def test_expired_deadline_classified_as_vacancy_unavailable():
    cand = create_candidate_fixture("user_exp_test")
    opp = create_opportunity_fixture("opp_exp_test", min_exp=12)

    past_deadline = datetime(2025, 1, 1, tzinfo=timezone.utc)
    opp.eligibility_rules.application_deadline = past_deadline
    ref_time = datetime(2026, 6, 1, tzinfo=timezone.utc)

    result = evaluate_eligibility(cand, opp, reference_time=ref_time)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert result.is_vacancy_expired is True
    assert VACANCY_EXPIRED_UNAVAILABLE in result.disqualification_reasons
    # Verify reason message explains vacancy is closed rather than candidate disqualified
    check = result.constraint_checks["application_deadline"]
    assert check.is_vacancy_unavailable is True
    assert "Vacancy is closed/unavailable" in check.message


# =====================================================================
# 4. API ENDPOINTS TESTS
# =====================================================================


def test_actions_api_endpoints(test_client):
    user_repo = SQLiteCandidateProfileRepository()
    opp_repo = SQLiteOpportunityRepository()

    user_id = f"api_user_{int(datetime.now().timestamp() * 1000)}"
    user_repo.save(create_candidate_fixture(user_id))

    opp_id = f"opp_api_test_{int(datetime.now().timestamp() * 1000)}"
    opp_repo.save(create_opportunity_fixture(opp_id))

    # POST action
    resp = test_client.post(
        f"/api/v1/actions/opportunities/{opp_id}?user_id={user_id}",
        json={
            "action_type": "SAVED",
            "reason_category": "ROLE_MISMATCH",
            "user_notes": "Great engineering tech stack",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["action_type"] == "SAVED"
    assert data["opportunity_id"] == opp_id
    assert data["previous_state"] is None

    # GET summary
    resp_summary = test_client.get(f"/api/v1/actions/candidate/{user_id}")
    assert resp_summary.status_code == 200
    summary_data = resp_summary.json()
    assert opp_id in summary_data["saved_opportunity_ids"]

    # POST soft override with rationale
    resp_override = test_client.post(
        f"/api/v1/actions/opportunities/{opp_id}?user_id={user_id}",
        json={
            "action_type": "SOFT_OVERRIDDEN",
            "reason_category": "EXPERIENCE_OVERRIDE",
            "soft_override_rationale": "Strong relevant personal portfolio projects.",
        },
    )
    assert resp_override.status_code == 201
    override_data = resp_override.json()
    assert override_data["action_type"] == "SOFT_OVERRIDDEN"
    assert override_data["previous_state"] == "SAVED"


def test_memory_api_endpoints(test_client):
    user_repo = SQLiteCandidateProfileRepository()

    user_id = f"api_mem_user_{int(datetime.now().timestamp() * 1000)}"
    user_repo.save(create_candidate_fixture(user_id))

    # POST memory item
    resp = test_client.post(
        f"/api/v1/memory/candidate/{user_id}",
        json={
            "memory_type": "CAREER_GOAL",
            "statement": "Seeking remote Staff AI Engineer positions.",
            "provenance_level": "USER_PROVIDED",
            "confidence_score": 1.0,
        },
    )
    assert resp.status_code == 201
    mem = resp.json()
    mem_id = mem["memory_id"]
    assert mem["version"] == 1
    assert mem["statement"] == "Seeking remote Staff AI Engineer positions."

    # PUT memory item to update
    resp_update = test_client.put(
        f"/api/v1/memory/candidate/{user_id}/{mem_id}",
        json={
            "statement": "Seeking remote Principal AI Engineer or Architect positions.",
            "change_reason": "Refined target career scope to leadership level.",
        },
    )
    assert resp_update.status_code == 200
    updated_mem = resp_update.json()
    assert updated_mem["version"] == 2
    assert updated_mem["memory_id"] != mem_id

    # GET lineage
    resp_lineage = test_client.get(f"/api/v1/memory/candidate/{user_id}/lineage/{updated_mem['memory_id']}")
    assert resp_lineage.status_code == 200
    lineage_data = resp_lineage.json()
    assert len(lineage_data["version_history"]) == 2

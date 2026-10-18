from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from app.modules.eligibility.engine import (
    evaluate_eligibility,
    filter_eligible_opportunities,
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
    DISQ_COUNTRY_UNAUTHORIZED,
    DISQ_DEGREE_BELOW_MINIMUM,
    DISQ_EXPERIENCE_BELOW_MINIMUM,
    DISQ_EXPERIENCE_EXCEEDS_MAXIMUM,
    DISQ_EXPIRED_DEADLINE,
    DISQ_GRADUATION_DATE_AFTER_WINDOW,
    DISQ_GRADUATION_DATE_BEFORE_WINDOW,
    DISQ_LOCATION_MISMATCH,
    DISQ_STUDENT_STATUS_REQUIRED,
    DISQ_VISA_SPONSORSHIP_UNAVAILABLE,
    DISQ_WORK_MODE_MISMATCH,
    UNCERT_GRADUATION_DATE_MISSING,
    UNCERT_LOCATION_UNRESTRICTED,
    UNCERT_NO_DEADLINE_SPECIFIED,
    UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    PolymorphicOpportunity,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def base_candidate() -> CandidateCareerProfile:
    """Fixture providing a baseline eligible candidate profile."""
    rec = EvidenceRecord(
        evidence_id="ev-101",
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
        title="Backend Software Engineer",
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
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, CA"],
    )
    return CandidateCareerProfile(
        user_id="usr-test-001",
        assessed_skills=[skill],
        target_career_paths=[target],
        eligibility_constraints=elig,
        overall_profile_confidence=0.9,
    )


@pytest.fixture
def base_opportunity() -> PolymorphicOpportunity:
    """Fixture providing a baseline matching opportunity."""
    rules = OpportunityEligibilityRules(
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=12,
        max_experience_months=60,
        work_mode=WorkMode.HYBRID,
        location_city_country=["San Francisco, CA"],
        application_deadline=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )
    return PolymorphicOpportunity(
        opportunity_id="opp-test-001",
        minhash_signature_hex="1234567890abcdef",
        title="Backend Software Engineer",
        company_name="Apex Systems",
        mapped_occupation_code="2512.1",
        eligibility_rules=rules,
        sanitized_summary="Join our core platform engineering team.",
        source_url="https://apex.example.com/jobs/001",
        posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completeness_score=0.9,
        trust_score=0.95,
    )


def test_baseline_eligible_case(base_candidate, base_opportunity):
    """A candidate satisfying all criteria evaluates strictly to ELIGIBLE with no disqualifications or caveats."""
    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.is_eligible is True
    assert result.disqualification_reasons == []
    assert result.uncertainty_caveats == []


def test_category_mismatch(base_candidate, base_opportunity):
    """Candidate only accepting FULL_TIME_JOB fails if opportunity is an INTERNSHIP."""
    base_opportunity.eligibility_rules.opportunity_category = OpportunityCategory.INTERNSHIP
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_CATEGORY_MISMATCH in result.disqualification_reasons


def test_country_unauthorized(base_candidate, base_opportunity):
    """Candidate authorized only in US fails if opportunity is in GB."""
    base_candidate.eligibility_constraints.authorized_country_codes = ["US"]
    base_opportunity.eligibility_rules.eligible_country_codes = ["GB"]
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_COUNTRY_UNAUTHORIZED in result.disqualification_reasons


def test_visa_sponsorship_required_but_unavailable(base_candidate, base_opportunity):
    """Candidate needing visa sponsorship fails if employer does not sponsor visas."""
    base_candidate.eligibility_constraints.requires_visa_sponsorship = True
    base_opportunity.eligibility_rules.sponsors_work_visa = False
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_VISA_SPONSORSHIP_UNAVAILABLE in result.disqualification_reasons


def test_visa_sponsorship_required_and_provided(base_candidate, base_opportunity):
    """Candidate needing visa sponsorship passes if employer sponsors visas."""
    base_candidate.eligibility_constraints.requires_visa_sponsorship = True
    base_opportunity.eligibility_rules.sponsors_work_visa = True
    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert result.is_eligible is True
    assert DISQ_VISA_SPONSORSHIP_UNAVAILABLE not in result.disqualification_reasons


def test_visa_sponsorship_not_required_passes_without_sponsorship(base_candidate, base_opportunity):
    """Candidate who does not require visa sponsorship passes regardless of employer sponsorship."""
    base_candidate.eligibility_constraints.requires_visa_sponsorship = False
    base_opportunity.eligibility_rules.sponsors_work_visa = False
    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert result.is_eligible is True
    assert DISQ_VISA_SPONSORSHIP_UNAVAILABLE not in result.disqualification_reasons


def test_degree_hierarchy_below_minimum(base_candidate, base_opportunity):
    """Candidate with Associate degree fails if Master's is required."""
    base_candidate.eligibility_constraints.highest_degree_level = DegreeLevel.ASSOCIATE
    base_opportunity.eligibility_rules.minimum_degree_required = DegreeLevel.MASTERS
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_DEGREE_BELOW_MINIMUM in result.disqualification_reasons


def test_degree_hierarchy_exceeds_minimum(base_candidate, base_opportunity):
    """Candidate with Doctorate passes if Bachelor's is required."""
    base_candidate.eligibility_constraints.highest_degree_level = DegreeLevel.DOCTORATE
    base_opportunity.eligibility_rules.minimum_degree_required = DegreeLevel.BACHELORS
    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert result.is_eligible is True
    assert DISQ_DEGREE_BELOW_MINIMUM not in result.disqualification_reasons


def test_degree_not_required(base_candidate, base_opportunity):
    """Opportunity with NONE degree required passes even for candidate with NONE degree."""
    base_candidate.eligibility_constraints.highest_degree_level = DegreeLevel.NONE
    base_opportunity.eligibility_rules.minimum_degree_required = DegreeLevel.NONE
    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert result.is_eligible is True
    assert DISQ_DEGREE_BELOW_MINIMUM not in result.disqualification_reasons


def test_student_status_required_but_not_enrolled(base_candidate, base_opportunity):
    """Academic internship requires student enrollment; non-student fails."""
    base_opportunity.eligibility_rules.requires_active_student_status = True
    base_candidate.eligibility_constraints.is_currently_enrolled_student = False
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_STUDENT_STATUS_REQUIRED in result.disqualification_reasons


def test_student_status_required_and_enrolled(base_candidate, base_opportunity):
    """Academic internship passes when candidate is an active student."""
    base_opportunity.eligibility_rules.requires_active_student_status = True
    base_candidate.eligibility_constraints.is_currently_enrolled_student = True
    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert result.is_eligible is True
    assert DISQ_STUDENT_STATUS_REQUIRED not in result.disqualification_reasons


def test_graduation_window_boundary_checks(base_candidate, base_opportunity):
    """Test graduation window start and end dates."""
    base_opportunity.eligibility_rules.allowed_graduation_window_start = date(2025, 5, 1)
    base_opportunity.eligibility_rules.allowed_graduation_window_end = date(2025, 12, 31)

    # Candidate graduation date before window start fails
    base_candidate.eligibility_constraints.expected_graduation_date = date(2025, 4, 30)
    res_early = evaluate_eligibility(base_candidate, base_opportunity)
    assert DISQ_GRADUATION_DATE_BEFORE_WINDOW in res_early.disqualification_reasons

    # Candidate graduation date after window end fails
    base_candidate.eligibility_constraints.expected_graduation_date = date(2026, 1, 1)
    res_late = evaluate_eligibility(base_candidate, base_opportunity)
    assert DISQ_GRADUATION_DATE_AFTER_WINDOW in res_late.disqualification_reasons

    # Candidate graduation date exactly on window boundaries passes
    base_candidate.eligibility_constraints.expected_graduation_date = date(2025, 5, 1)
    res_start = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert res_start.is_eligible is True

    base_candidate.eligibility_constraints.expected_graduation_date = date(2025, 12, 31)
    res_end = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert res_end.is_eligible is True


def test_missing_graduation_date_preserves_uncertainty(base_candidate, base_opportunity):
    """When an opportunity specifies a graduation window but candidate has no graduation date,

    the system must preserve uncertainty (ELIGIBLE_WITH_UNCERTAINTY) rather than false pass or false fail.
    """
    base_opportunity.eligibility_rules.allowed_graduation_window_start = date(2025, 1, 1)
    base_candidate.eligibility_constraints.expected_graduation_date = None

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
    assert result.is_eligible is True
    assert UNCERT_GRADUATION_DATE_MISSING in result.uncertainty_caveats
    assert result.disqualification_reasons == []


def test_experience_below_minimum(base_candidate, base_opportunity):
    """Candidate with 6 months fails if 12 months minimum is required."""
    base_candidate.eligibility_constraints.total_full_time_experience_months = 6
    base_opportunity.eligibility_rules.min_experience_months = 12
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_EXPERIENCE_BELOW_MINIMUM in result.disqualification_reasons


def test_experience_exceeds_maximum(base_candidate, base_opportunity):
    """Candidate with 48 months fails if early-career opportunity caps at 24 months."""
    base_candidate.eligibility_constraints.total_full_time_experience_months = 48
    base_opportunity.eligibility_rules.max_experience_months = 24
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_EXPERIENCE_EXCEEDS_MAXIMUM in result.disqualification_reasons


def test_work_mode_mismatch(base_candidate, base_opportunity):
    """Candidate only accepting REMOTE fails if opportunity is ON_SITE."""
    base_candidate.eligibility_constraints.allowed_work_modes = [WorkMode.REMOTE]
    base_opportunity.eligibility_rules.work_mode = WorkMode.ON_SITE
    result = evaluate_eligibility(base_candidate, base_opportunity)

    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_WORK_MODE_MISMATCH in result.disqualification_reasons


def test_remote_work_waives_geographic_commute(base_candidate, base_opportunity):
    """For REMOTE opportunities, city/commute constraints are waived."""
    base_candidate.eligibility_constraints.preferred_locations = ["London, UK"]
    base_opportunity.eligibility_rules.work_mode = WorkMode.REMOTE
    base_opportunity.eligibility_rules.location_city_country = ["San Francisco, CA"]
    base_opportunity.eligibility_rules.eligible_country_codes = ["US"]
    base_candidate.eligibility_constraints.authorized_country_codes = ["US"]

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.is_eligible is True
    assert DISQ_LOCATION_MISMATCH not in result.disqualification_reasons
    assert result.constraint_checks["geographic_location"].rule_code == "RULE_LOCATION_WAIVED_REMOTE"


def test_on_site_location_mismatch(base_candidate, base_opportunity):
    """On-site opportunity in New York fails candidate who only specified Austin."""
    base_candidate.eligibility_constraints.preferred_locations = ["Austin, TX"]
    base_opportunity.eligibility_rules.work_mode = WorkMode.ON_SITE
    base_opportunity.eligibility_rules.location_city_country = ["New York, NY"]

    result = evaluate_eligibility(base_candidate, base_opportunity)
    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_LOCATION_MISMATCH in result.disqualification_reasons


def test_on_site_location_matched_case_insensitive(base_candidate, base_opportunity):
    """On-site opportunity matches candidate with case-insensitive token comparison."""
    base_candidate.eligibility_constraints.preferred_locations = ["san francisco"]
    base_opportunity.eligibility_rules.work_mode = WorkMode.HYBRID
    base_opportunity.eligibility_rules.location_city_country = ["San Francisco, CA"]

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.is_eligible is True
    assert DISQ_LOCATION_MISMATCH not in result.disqualification_reasons


def test_unrestricted_candidate_location_preserves_uncertainty(base_candidate, base_opportunity):
    """Candidate with empty preferred_locations indicates relocation flexibility,

    flagged as ELIGIBLE_WITH_UNCERTAINTY with UNCERT_LOCATION_UNRESTRICTED.
    """
    base_candidate.eligibility_constraints.preferred_locations = []
    base_opportunity.eligibility_rules.work_mode = WorkMode.HYBRID
    base_opportunity.eligibility_rules.location_city_country = ["Chicago, IL"]

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
    assert result.is_eligible is True
    assert UNCERT_LOCATION_UNRESTRICTED in result.uncertainty_caveats


def test_unspecified_opportunity_location_preserves_uncertainty(base_candidate, base_opportunity):
    """On-site opportunity without specified cities is flagged with UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED."""
    base_candidate.eligibility_constraints.preferred_locations = ["Boston, MA"]
    base_opportunity.eligibility_rules.work_mode = WorkMode.HYBRID
    base_opportunity.eligibility_rules.location_city_country = []

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
    assert result.is_eligible is True
    assert UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED in result.uncertainty_caveats


def test_expired_application_deadline(base_candidate, base_opportunity):
    """Opportunity with a deadline in the past fails with DISQ_EXPIRED_DEADLINE."""
    base_opportunity.eligibility_rules.application_deadline = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ref_time = datetime(2026, 2, 1, tzinfo=timezone.utc)

    result = evaluate_eligibility(base_candidate, base_opportunity, reference_time=ref_time)
    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_EXPIRED_DEADLINE in result.disqualification_reasons


def test_missing_application_deadline_preserves_uncertainty(base_candidate, base_opportunity):
    """Opportunity without application deadline (rolling) is flagged with UNCERT_NO_DEADLINE_SPECIFIED."""
    base_opportunity.eligibility_rules.application_deadline = None

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
    assert result.is_eligible is True
    assert UNCERT_NO_DEADLINE_SPECIFIED in result.uncertainty_caveats


def test_multiple_simultaneous_disqualifications(base_candidate, base_opportunity):
    """When multiple hard criteria fail simultaneously, all are captured in disqualification_reasons."""
    base_opportunity.eligibility_rules.opportunity_category = OpportunityCategory.INTERNSHIP
    base_opportunity.eligibility_rules.eligible_country_codes = ["DE"]
    base_opportunity.eligibility_rules.minimum_degree_required = DegreeLevel.DOCTORATE
    base_opportunity.eligibility_rules.application_deadline = datetime(2020, 1, 1, tzinfo=timezone.utc)

    result = evaluate_eligibility(
        base_candidate,
        base_opportunity,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    assert result.status == EligibilityStatus.INELIGIBLE
    assert result.is_eligible is False
    assert DISQ_CATEGORY_MISMATCH in result.disqualification_reasons
    assert DISQ_COUNTRY_UNAUTHORIZED in result.disqualification_reasons
    assert DISQ_DEGREE_BELOW_MINIMUM in result.disqualification_reasons
    assert DISQ_EXPIRED_DEADLINE in result.disqualification_reasons


def test_batch_filtering(base_candidate, base_opportunity):
    """filter_eligible_opportunities accurately partitions eligible and ineligible items."""
    # Create copy for second ineligible opportunity
    opp_inelig = base_opportunity.model_copy(deep=True)
    opp_inelig.opportunity_id = "opp-inelig-002"
    opp_inelig.eligibility_rules.opportunity_category = OpportunityCategory.FELLOWSHIP

    opps = [base_opportunity, opp_inelig]
    eligible, all_results = filter_eligible_opportunities(
        base_candidate,
        opps,
        reference_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    assert len(eligible) == 1
    assert eligible[0].opportunity_id == "opp-test-001"
    assert len(all_results) == 2
    assert all_results[0].is_eligible is True
    assert all_results[1].is_eligible is False


def test_pure_determinism_repeatability(base_candidate, base_opportunity):
    """Running evaluation 100 times on identical inputs produces bit-for-bit identical results."""
    ref_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    baseline_result = evaluate_eligibility(base_candidate, base_opportunity, reference_time=ref_time)

    for _ in range(100):
        run_res = evaluate_eligibility(base_candidate, base_opportunity, reference_time=ref_time)
        assert run_res.status == baseline_result.status
        assert run_res.is_eligible == baseline_result.is_eligible
        assert run_res.disqualification_reasons == baseline_result.disqualification_reasons
        assert run_res.uncertainty_caveats == baseline_result.uncertainty_caveats

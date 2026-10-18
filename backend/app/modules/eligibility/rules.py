from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.schemas.common import DEGREE_HIERARCHY, DegreeLevel, WorkMode
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
    ConstraintCheckResult,
    ConstraintStatus,
)
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile


def check_category_match(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_type: Verifies opportunity category alignment with candidate allowed categories."""
    opp_cat = opportunity.eligibility_rules.opportunity_category
    allowed_cats = candidate.eligibility_constraints.allowed_opportunity_categories

    if opp_cat not in allowed_cats:
        return ConstraintCheckResult(
            constraint_name="opportunity_category",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_CATEGORY_MISMATCH,
            message=f"Opportunity category '{opp_cat.value}' is not accepted by candidate (allowed: {[c.value for c in allowed_cats]}).",
            details={"opportunity_category": opp_cat.value, "allowed_categories": [c.value for c in allowed_cats]},
        )

    return ConstraintCheckResult(
        constraint_name="opportunity_category",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_CATEGORY_MATCH",
        message=f"Opportunity category '{opp_cat.value}' matches candidate allowed categories.",
        details={"opportunity_category": opp_cat.value},
    )


def check_work_authorization(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_auth: Verifies legal work authorization countries and visa sponsorship compatibility."""
    cand_countries = set(candidate.eligibility_constraints.authorized_country_codes)
    opp_countries = set(opportunity.eligibility_rules.eligible_country_codes)
    common_countries = cand_countries.intersection(opp_countries)

    if not common_countries:
        return ConstraintCheckResult(
            constraint_name="work_authorization",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_COUNTRY_UNAUTHORIZED,
            message=f"Candidate authorized countries {list(cand_countries)} do not overlap with opportunity eligible countries {list(opp_countries)}.",
            details={"candidate_countries": list(cand_countries), "opportunity_countries": list(opp_countries)},
        )

    if candidate.eligibility_constraints.requires_visa_sponsorship:
        if not opportunity.eligibility_rules.sponsors_work_visa:
            return ConstraintCheckResult(
                constraint_name="work_authorization",
                status=ConstraintStatus.FAILED,
                rule_code=DISQ_VISA_SPONSORSHIP_UNAVAILABLE,
                message="Candidate requires visa sponsorship, but employer does not sponsor work visas for this opportunity.",
                details={"requires_visa_sponsorship": True, "sponsors_work_visa": False},
            )

    return ConstraintCheckResult(
        constraint_name="work_authorization",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_WORK_AUTHORIZATION_PASSED",
        message="Candidate meets work authorization country and visa sponsorship requirements.",
        details={"authorized_countries": list(common_countries), "sponsors_work_visa": opportunity.eligibility_rules.sponsors_work_visa},
    )


def check_degree_level(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_acad (Degree): Verifies candidate academic degree meets or exceeds minimum requirement."""
    min_degree = opportunity.eligibility_rules.minimum_degree_required

    if min_degree == DegreeLevel.NONE:
        return ConstraintCheckResult(
            constraint_name="degree_level",
            status=ConstraintStatus.PASSED,
            rule_code="RULE_DEGREE_NOT_REQUIRED",
            message="No minimum degree required for this opportunity.",
            details={"minimum_degree_required": DegreeLevel.NONE.value},
        )

    cand_degree = candidate.eligibility_constraints.highest_degree_level
    cand_rank = DEGREE_HIERARCHY.get(cand_degree, 0)
    required_rank = DEGREE_HIERARCHY.get(min_degree, 0)

    if cand_rank < required_rank:
        return ConstraintCheckResult(
            constraint_name="degree_level",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_DEGREE_BELOW_MINIMUM,
            message=f"Candidate highest degree '{cand_degree.value}' (rank {cand_rank}) is below minimum requirement '{min_degree.value}' (rank {required_rank}).",
            details={"candidate_degree": cand_degree.value, "minimum_degree_required": min_degree.value},
        )

    return ConstraintCheckResult(
        constraint_name="degree_level",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_DEGREE_PASSED",
        message=f"Candidate degree '{cand_degree.value}' meets or exceeds requirement '{min_degree.value}'.",
        details={"candidate_degree": cand_degree.value, "minimum_degree_required": min_degree.value},
    )


def check_student_status(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_acad (Student Status): Verifies active student enrollment if mandatory."""
    req_student = opportunity.eligibility_rules.requires_active_student_status
    is_student = candidate.eligibility_constraints.is_currently_enrolled_student

    if req_student and not is_student:
        return ConstraintCheckResult(
            constraint_name="student_enrollment",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_STUDENT_STATUS_REQUIRED,
            message="Opportunity strictly requires active student enrollment, but candidate is not currently enrolled.",
            details={"requires_active_student_status": True, "is_currently_enrolled_student": False},
        )

    return ConstraintCheckResult(
        constraint_name="student_enrollment",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_STUDENT_STATUS_PASSED",
        message="Active student requirement satisfied." if req_student else "Active student enrollment not required.",
        details={"requires_active_student_status": req_student, "is_currently_enrolled_student": is_student},
    )


def check_graduation_window(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_acad (Graduation Window): Verifies expected graduation date falls within specified cohort window."""
    win_start = opportunity.eligibility_rules.allowed_graduation_window_start
    win_end = opportunity.eligibility_rules.allowed_graduation_window_end

    if win_start is None and win_end is None:
        return ConstraintCheckResult(
            constraint_name="graduation_window",
            status=ConstraintStatus.WAIVED,
            rule_code="RULE_GRADUATION_WINDOW_NOT_RESTRICTED",
            message="No graduation window specified by opportunity.",
            details={},
        )

    grad_date = candidate.eligibility_constraints.expected_graduation_date
    if grad_date is None:
        return ConstraintCheckResult(
            constraint_name="graduation_window",
            status=ConstraintStatus.UNCERTAIN,
            rule_code=UNCERT_GRADUATION_DATE_MISSING,
            message="Opportunity enforces a graduation window, but candidate profile does not specify an expected graduation date.",
            details={"window_start": str(win_start) if win_start else None, "window_end": str(win_end) if win_end else None},
        )

    if win_start is not None and grad_date < win_start:
        return ConstraintCheckResult(
            constraint_name="graduation_window",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_GRADUATION_DATE_BEFORE_WINDOW,
            message=f"Candidate expected graduation date ({grad_date}) is before the allowed window start ({win_start}).",
            details={"candidate_graduation_date": str(grad_date), "window_start": str(win_start)},
        )

    if win_end is not None and grad_date > win_end:
        return ConstraintCheckResult(
            constraint_name="graduation_window",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_GRADUATION_DATE_AFTER_WINDOW,
            message=f"Candidate expected graduation date ({grad_date}) is after the allowed window end ({win_end}).",
            details={"candidate_graduation_date": str(grad_date), "window_end": str(win_end)},
        )

    return ConstraintCheckResult(
        constraint_name="graduation_window",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_GRADUATION_WINDOW_PASSED",
        message=f"Candidate expected graduation date ({grad_date}) is within the allowable window.",
        details={"candidate_graduation_date": str(grad_date), "window_start": str(win_start), "window_end": str(win_end)},
    )


def check_experience_duration(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_acad (Experience): Verifies full-time experience meets minimum and does not exceed maximum."""
    cand_exp = candidate.eligibility_constraints.total_full_time_experience_months
    min_exp = opportunity.eligibility_rules.min_experience_months
    max_exp = opportunity.eligibility_rules.max_experience_months

    if cand_exp < min_exp:
        return ConstraintCheckResult(
            constraint_name="experience_duration",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_EXPERIENCE_BELOW_MINIMUM,
            message=f"Candidate full-time experience ({cand_exp} months) is below minimum requirement ({min_exp} months).",
            details={"candidate_months": cand_exp, "min_experience_months": min_exp},
        )

    if max_exp is not None and cand_exp > max_exp:
        return ConstraintCheckResult(
            constraint_name="experience_duration",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_EXPERIENCE_EXCEEDS_MAXIMUM,
            message=f"Candidate full-time experience ({cand_exp} months) exceeds maximum allowable limit ({max_exp} months).",
            details={"candidate_months": cand_exp, "max_experience_months": max_exp},
        )

    return ConstraintCheckResult(
        constraint_name="experience_duration",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_EXPERIENCE_PASSED",
        message=f"Candidate full-time experience ({cand_exp} months) satisfies experience constraints.",
        details={"candidate_months": cand_exp, "min_experience_months": min_exp, "max_experience_months": max_exp},
    )


def check_work_mode(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_loc (Work Mode): Verifies workplace arrangement (Remote/Hybrid/On-site) compatibility."""
    opp_mode = opportunity.eligibility_rules.work_mode
    allowed_modes = candidate.eligibility_constraints.allowed_work_modes

    if opp_mode not in allowed_modes:
        return ConstraintCheckResult(
            constraint_name="work_mode",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_WORK_MODE_MISMATCH,
            message=f"Opportunity work mode '{opp_mode.value}' is not acceptable to candidate (allowed: {[m.value for m in allowed_modes]}).",
            details={"opportunity_work_mode": opp_mode.value, "allowed_work_modes": [m.value for m in allowed_modes]},
        )

    return ConstraintCheckResult(
        constraint_name="work_mode",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_WORK_MODE_PASSED",
        message=f"Work mode '{opp_mode.value}' matches candidate allowed modes.",
        details={"work_mode": opp_mode.value},
    )


def check_location(
    candidate: CandidateCareerProfile, opportunity: PolymorphicOpportunity
) -> ConstraintCheckResult:
    """I_loc (Geographic Location): Verifies location for non-remote opportunities with explicit uncertainty handling."""
    opp_mode = opportunity.eligibility_rules.work_mode

    # Remote opportunity: geographic commute constraint is completely waived
    if opp_mode == WorkMode.REMOTE:
        return ConstraintCheckResult(
            constraint_name="geographic_location",
            status=ConstraintStatus.WAIVED,
            rule_code="RULE_LOCATION_WAIVED_REMOTE",
            message="Remote opportunity: geographic commute constraint waived (country authorization applies).",
            details={"work_mode": WorkMode.REMOTE.value},
        )

    # Hybrid or On-Site role:
    cand_locations = candidate.eligibility_constraints.preferred_locations
    opp_locations = opportunity.eligibility_rules.location_city_country

    if not cand_locations:
        # Candidate has no geographic restrictions (willing to relocate/commute anywhere)
        return ConstraintCheckResult(
            constraint_name="geographic_location",
            status=ConstraintStatus.UNCERTAIN,
            rule_code=UNCERT_LOCATION_UNRESTRICTED,
            message="Candidate specifies no location restrictions; on-site/hybrid commute or relocation requires confirmation.",
            details={"candidate_preferred_locations": [], "opportunity_locations": opp_locations},
        )

    if not opp_locations:
        # Opportunity has not listed specific cities
        return ConstraintCheckResult(
            constraint_name="geographic_location",
            status=ConstraintStatus.UNCERTAIN,
            rule_code=UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED,
            message="Opportunity does not specify city/location details for hybrid/on-site role.",
            details={"candidate_preferred_locations": cand_locations, "opportunity_locations": []},
        )

    # Case-insensitive substring/token match
    matched = []
    for c_loc in cand_locations:
        c_clean = c_loc.lower().strip()
        for o_loc in opp_locations:
            o_clean = o_loc.lower().strip()
            if c_clean in o_clean or o_clean in c_clean:
                matched.append((c_loc, o_loc))

    if matched:
        return ConstraintCheckResult(
            constraint_name="geographic_location",
            status=ConstraintStatus.PASSED,
            rule_code="RULE_LOCATION_MATCHED",
            message=f"Location match confirmed between candidate and opportunity.",
            details={"matches": [f"{c} <-> {o}" for c, o in matched]},
        )

    return ConstraintCheckResult(
        constraint_name="geographic_location",
        status=ConstraintStatus.FAILED,
        rule_code=DISQ_LOCATION_MISMATCH,
        message=f"Candidate preferred locations {cand_locations} do not match opportunity locations {opp_locations}.",
        details={"candidate_preferred_locations": cand_locations, "opportunity_locations": opp_locations},
    )


def check_application_deadline(
    opportunity: PolymorphicOpportunity, reference_time: Optional[datetime] = None
) -> ConstraintCheckResult:
    """I_time: Verifies opportunity application deadline is still active relative to reference time."""
    deadline = opportunity.eligibility_rules.application_deadline

    if deadline is None:
        return ConstraintCheckResult(
            constraint_name="application_deadline",
            status=ConstraintStatus.UNCERTAIN,
            rule_code=UNCERT_NO_DEADLINE_SPECIFIED,
            message="Opportunity has no explicit application deadline; assumed active/rolling.",
            details={},
        )

    ref = reference_time or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if deadline < ref:
        return ConstraintCheckResult(
            constraint_name="application_deadline",
            status=ConstraintStatus.FAILED,
            rule_code=DISQ_EXPIRED_DEADLINE,
            message=f"Application deadline ({deadline.isoformat()}) has expired relative to reference time ({ref.isoformat()}).",
            details={"deadline": deadline.isoformat(), "reference_time": ref.isoformat()},
        )

    return ConstraintCheckResult(
        constraint_name="application_deadline",
        status=ConstraintStatus.PASSED,
        rule_code="RULE_DEADLINE_ACTIVE",
        message=f"Application deadline ({deadline.isoformat()}) is active.",
        details={"deadline": deadline.isoformat(), "reference_time": ref.isoformat()},
    )

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.modules.eligibility.rules import (
    check_application_deadline,
    check_category_match,
    check_degree_level,
    check_experience_duration,
    check_graduation_window,
    check_location,
    check_student_status,
    check_work_authorization,
    check_work_mode,
)
from app.schemas.eligibility import (
    ConstraintStatus,
    EligibilityResult,
    EligibilityStatus,
)
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile


def evaluate_eligibility(
    candidate: CandidateCareerProfile,
    opportunity: PolymorphicOpportunity,
    reference_time: Optional[datetime] = None,
) -> EligibilityResult:
    """Deterministically evaluates whether an opportunity is eligible for a candidate.

    Strictly satisfies:
    Eligible(u, o) = I_type(u, o) and I_auth(u, o) and I_acad(u, o) and I_loc(u, o) and I_time(o)

    - Zero probabilistic generation or LLM calls.
    - Explicitly preserves uncertainty when data is missing or unstated.
    - Audits every constraint check in a structured dictionary.
    """
    ref_time = reference_time or datetime.now(timezone.utc)

    # Execute all deterministic constraint checks
    checks = {
        "opportunity_category": check_category_match(candidate, opportunity),
        "work_authorization": check_work_authorization(candidate, opportunity),
        "degree_level": check_degree_level(candidate, opportunity),
        "student_enrollment": check_student_status(candidate, opportunity),
        "graduation_window": check_graduation_window(candidate, opportunity),
        "experience_duration": check_experience_duration(candidate, opportunity),
        "work_mode": check_work_mode(candidate, opportunity),
        "geographic_location": check_location(candidate, opportunity),
        "application_deadline": check_application_deadline(opportunity, reference_time=ref_time),
    }

    disqualification_reasons: list[str] = []
    uncertainty_caveats: list[str] = []

    for check in checks.values():
        if check.status == ConstraintStatus.FAILED:
            disqualification_reasons.append(check.rule_code)
        elif check.status == ConstraintStatus.UNCERTAIN:
            uncertainty_caveats.append(check.rule_code)

    # Determine overall status
    if disqualification_reasons:
        status = EligibilityStatus.INELIGIBLE
        is_eligible = False
    elif uncertainty_caveats:
        status = EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
        is_eligible = True
    else:
        status = EligibilityStatus.ELIGIBLE
        is_eligible = True

    return EligibilityResult(
        opportunity_id=opportunity.opportunity_id,
        user_id=candidate.user_id,
        status=status,
        is_eligible=is_eligible,
        disqualification_reasons=disqualification_reasons,
        uncertainty_caveats=uncertainty_caveats,
        constraint_checks=checks,
        evaluated_at=ref_time,
    )


def filter_eligible_opportunities(
    candidate: CandidateCareerProfile,
    opportunities: list[PolymorphicOpportunity],
    reference_time: Optional[datetime] = None,
) -> tuple[list[PolymorphicOpportunity], list[EligibilityResult]]:
    """Filters a collection of opportunities, returning eligible items and an audit log of all evaluations.

    Returns:
        tuple[list[PolymorphicOpportunity], list[EligibilityResult]]:
            - eligible_opportunities: List of PolymorphicOpportunity where is_eligible is True.
            - all_evaluation_results: Exhaustive audit results for every opportunity evaluated.
    """
    ref_time = reference_time or datetime.now(timezone.utc)
    eligible_opps: list[PolymorphicOpportunity] = []
    all_results: list[EligibilityResult] = []

    for opp in opportunities:
        result = evaluate_eligibility(candidate, opp, reference_time=ref_time)
        all_results.append(result)
        if result.is_eligible:
            eligible_opps.append(opp)

    return eligible_opps, all_results

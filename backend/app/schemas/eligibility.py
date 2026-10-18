from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# =====================================================================
# STANDARDIZED RULE AND CAVEAT CODES
# =====================================================================

# Disqualification Rule Codes (Confirmed Hard Failures)
DISQ_CATEGORY_MISMATCH = "DISQ_CATEGORY_MISMATCH"
DISQ_COUNTRY_UNAUTHORIZED = "DISQ_COUNTRY_UNAUTHORIZED"
DISQ_VISA_SPONSORSHIP_UNAVAILABLE = "DISQ_VISA_SPONSORSHIP_UNAVAILABLE"
DISQ_DEGREE_BELOW_MINIMUM = "DISQ_DEGREE_BELOW_MINIMUM"
DISQ_STUDENT_STATUS_REQUIRED = "DISQ_STUDENT_STATUS_REQUIRED"
DISQ_GRADUATION_DATE_BEFORE_WINDOW = "DISQ_GRADUATION_DATE_BEFORE_WINDOW"
DISQ_GRADUATION_DATE_AFTER_WINDOW = "DISQ_GRADUATION_DATE_AFTER_WINDOW"
DISQ_EXPERIENCE_BELOW_MINIMUM = "DISQ_EXPERIENCE_BELOW_MINIMUM"
DISQ_EXPERIENCE_EXCEEDS_MAXIMUM = "DISQ_EXPERIENCE_EXCEEDS_MAXIMUM"
DISQ_WORK_MODE_MISMATCH = "DISQ_WORK_MODE_MISMATCH"
DISQ_LOCATION_MISMATCH = "DISQ_LOCATION_MISMATCH"
DISQ_EXPIRED_DEADLINE = "DISQ_EXPIRED_DEADLINE"

# Uncertainty Caveat Codes (Unstated / Missing Data Requiring Verification)
UNCERT_NO_DEADLINE_SPECIFIED = "UNCERT_NO_DEADLINE_SPECIFIED"
UNCERT_GRADUATION_DATE_MISSING = "UNCERT_GRADUATION_DATE_MISSING"
UNCERT_LOCATION_UNRESTRICTED = "UNCERT_LOCATION_UNRESTRICTED"
UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED = "UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED"


class EligibilityStatus(str, Enum):
    """Overall outcome of the deterministic eligibility evaluation."""

    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_UNCERTAINTY = "ELIGIBLE_WITH_UNCERTAINTY"
    INELIGIBLE = "INELIGIBLE"


class ConstraintStatus(str, Enum):
    """Status for an individual constraint evaluation."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"
    WAIVED = "WAIVED"


class ConstraintCheckResult(BaseModel):
    """Detailed audit payload for a specific constraint evaluation."""

    constraint_name: str = Field(
        ...,
        description="Identifier of the evaluated constraint (e.g. 'work_authorization', 'degree_level').",
    )
    status: ConstraintStatus = Field(
        ...,
        description="Outcome of this individual check: PASSED, FAILED, UNCERTAIN, or WAIVED.",
    )
    rule_code: str = Field(
        ...,
        description="Deterministic rule code (e.g. 'DISQ_VISA_SPONSORSHIP_UNAVAILABLE' or 'RULE_DEGREE_PASSED').",
    )
    message: str = Field(
        ...,
        description="Human-readable audit explanation of the evaluation result.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value context for verification and debugging.",
    )


class EligibilityResult(BaseModel):
    """Deterministic output contract produced exclusively by pure Python rule engine."""

    opportunity_id: str = Field(
        ...,
        description="Opportunity evaluated.",
    )
    user_id: str = Field(
        ...,
        description="Candidate evaluated.",
    )
    status: EligibilityStatus = Field(
        ...,
        description="Aggregate eligibility verdict: ELIGIBLE, ELIGIBLE_WITH_UNCERTAINTY, or INELIGIBLE.",
    )
    is_eligible: bool = Field(
        ...,
        description="True if no hard constraints failed (eligible or eligible with caveats). False if any hard constraint failed.",
    )
    disqualification_reasons: list[str] = Field(
        default_factory=list,
        description="List of rule codes for confirmed failures. Guaranteed empty if is_eligible is True.",
    )
    uncertainty_caveats: list[str] = Field(
        default_factory=list,
        description="List of caveat codes for unstated or missing attributes that warrant user confirmation.",
    )
    constraint_checks: dict[str, ConstraintCheckResult] = Field(
        default_factory=dict,
        description="Exhaustive breakdown of every individual deterministic constraint check.",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Deterministic evaluation timestamp.",
    )

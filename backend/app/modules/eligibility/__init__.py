"""Deterministic Eligibility Subsystem for JobFalcon.

Guarantees 100% deterministic rule enforcement for hard eligibility constraints
before any probabilistic ranking or AI explanation generation occurs.
"""

from app.modules.eligibility.engine import (
    evaluate_eligibility,
    filter_eligible_opportunities,
)
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

__all__ = [
    "evaluate_eligibility",
    "filter_eligible_opportunities",
    "check_category_match",
    "check_work_authorization",
    "check_degree_level",
    "check_student_status",
    "check_graduation_window",
    "check_experience_duration",
    "check_work_mode",
    "check_location",
    "check_application_deadline",
]

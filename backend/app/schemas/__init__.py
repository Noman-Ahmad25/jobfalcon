"""Pydantic v2 schemas package for JobFalcon."""

from app.schemas.common import (
    DEGREE_HIERARCHY,
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.deduplication import (
    DeduplicationResult,
    DuplicateRecord,
    OpportunityCluster,
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
    ConstraintCheckResult,
    ConstraintStatus,
    EligibilityResult,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.health import HealthStatus, ReadyStatus
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

from app.schemas.pipeline import (
    PipelineEvaluationRequest,
    PipelineEvaluationResponse,
)
from app.schemas.profiling import (
    CandidateProfilingRequest,
    CandidateProfilingResponse,
    EpistemicUncertainties,
    ExtractedEducation,
    ExtractedEvidenceSnippet,
    ExtractedProject,
    ExtractedSkillClaim,
    ExtractedWorkExperience,
    LLMCandidateFactExtraction,
)

__all__ = [
    # Common
    "DegreeLevel",
    "DEGREE_HIERARCHY",
    "OpportunityCategory",
    "WorkMode",
    "EvidenceSourceType",
    "CareerPathRelationship",
    # Health
    "HealthStatus",
    "ReadyStatus",
    # Evidence
    "EvidenceRecord",
    # Profile
    "AssessedSkill",
    "CareerPathNode",
    "CandidateEligibilityProfile",
    "CandidateCareerProfile",
    # Opportunity
    "OpportunityEligibilityRules",
    "OpportunitySkillRequirement",
    "PolymorphicOpportunity",
    # Eligibility
    "EligibilityStatus",
    "ConstraintStatus",
    "ConstraintCheckResult",
    "EligibilityResult",
    "DISQ_CATEGORY_MISMATCH",
    "DISQ_COUNTRY_UNAUTHORIZED",
    "DISQ_VISA_SPONSORSHIP_UNAVAILABLE",
    "DISQ_DEGREE_BELOW_MINIMUM",
    "DISQ_STUDENT_STATUS_REQUIRED",
    "DISQ_GRADUATION_DATE_BEFORE_WINDOW",
    "DISQ_GRADUATION_DATE_AFTER_WINDOW",
    "DISQ_EXPERIENCE_BELOW_MINIMUM",
    "DISQ_EXPERIENCE_EXCEEDS_MAXIMUM",
    "DISQ_WORK_MODE_MISMATCH",
    "DISQ_LOCATION_MISMATCH",
    "DISQ_EXPIRED_DEADLINE",
    "UNCERT_NO_DEADLINE_SPECIFIED",
    "UNCERT_GRADUATION_DATE_MISSING",
    "UNCERT_LOCATION_UNRESTRICTED",
    "UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED",
    # Deduplication
    "DuplicateRecord",
    "OpportunityCluster",
    "DeduplicationResult",
    # Pipeline
    "PipelineEvaluationRequest",
    "PipelineEvaluationResponse",
    # Profiling
    "CandidateProfilingRequest",
    "CandidateProfilingResponse",
    "ExtractedEvidenceSnippet",
    "ExtractedSkillClaim",
    "ExtractedWorkExperience",
    "ExtractedProject",
    "ExtractedEducation",
    "EpistemicUncertainties",
    "LLMCandidateFactExtraction",
]


from __future__ import annotations

from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.evidence import EvidenceRecord


class AssessedSkill(BaseModel):
    """Evidence-calibrated candidate skill proficiency with epistemic confidence."""

    canonical_skill_id: str = Field(
        ...,
        description="Standardized ESCO URI or O*NET skill identifier (e.g., 'http://data.europa.eu/esco/skill/001').",
    )
    skill_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Human-readable canonical skill name.",
    )
    proficiency_score: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="Calibrated proficiency on a 1.0 to 10.0 continuous scale.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Epistemic confidence derived from evidence depth and source verifiability.",
    )
    evidence_records: list[EvidenceRecord] = Field(
        ...,
        min_length=1,
        description="Mandatory list of provenance records grounding this competency claim.",
    )
    last_practiced_date: Optional[date] = Field(
        default=None,
        description="Most recent date when this skill was demonstrated or practiced.",
    )

    @field_validator("skill_name", mode="before")
    @classmethod
    def _sanitize_skill_name(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class CareerPathNode(BaseModel):
    """Occupational taxonomy node representing a current, target, or adjacent trajectory."""

    occupation_code: str = Field(
        ...,
        description="Canonical ESCO or O*NET occupation identifier (e.g., '2512.1' or '15-1252.00').",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Standardized occupation title.",
    )
    relationship_type: CareerPathRelationship = Field(
        ...,
        description="Relationship to candidate profile: CURRENT baseline, TARGET ambition, or ADJACENT expansion.",
    )
    adjacency_similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Taxonomic similarity coefficient (1.0 for TARGET, 0.60-0.90 for ADJACENT).",
    )
    missing_core_skill_ids: list[str] = Field(
        default_factory=list,
        description="Canonical skill IDs required by this career path that the candidate currently lacks.",
    )

    @field_validator("title", mode="before")
    @classmethod
    def _sanitize_title(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class CandidateEligibilityProfile(BaseModel):
    """Deterministic profile attributes evaluated by the eligibility engine."""

    authorized_country_codes: list[str] = Field(
        ...,
        min_length=1,
        description="ISO-3166-1 alpha-2 country codes where candidate is legally authorized to work.",
    )
    requires_visa_sponsorship: bool = Field(
        default=False,
        description="True if candidate requires employer-sponsored work visa.",
    )
    highest_degree_level: DegreeLevel = Field(
        default=DegreeLevel.NONE,
        description="Highest academic degree completed or currently actively pursued.",
    )
    is_currently_enrolled_student: bool = Field(
        default=False,
        description="True if currently enrolled in an accredited academic or degree program.",
    )
    expected_graduation_date: Optional[date] = Field(
        default=None,
        description="Expected graduation or program completion date.",
    )
    total_full_time_experience_months: int = Field(
        default=0,
        ge=0,
        description="Total cumulative full-time professional experience in months.",
    )
    allowed_opportunity_categories: list[OpportunityCategory] = Field(
        ...,
        min_length=1,
        description="Acceptable opportunity types (e.g., INTERNSHIP, FULL_TIME_JOB).",
    )
    allowed_work_modes: list[WorkMode] = Field(
        ...,
        min_length=1,
        description="Permitted workplace arrangements (REMOTE, HYBRID, ON_SITE).",
    )
    preferred_locations: list[str] = Field(
        default_factory=list,
        description="Target cities/regions for on-site/hybrid roles. Empty indicates complete geographic flexibility.",
    )

    @field_validator("authorized_country_codes", mode="before")
    @classmethod
    def _normalize_country_codes(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(code).strip().upper() for code in v if str(code).strip()]
        return v

    @field_validator("preferred_locations", mode="before")
    @classmethod
    def _sanitize_locations(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [sanitize_untrusted_text(str(item)) for item in v if str(item).strip()]
        return v


class CandidateWorkExperience(BaseModel):
    """Structured professional experience record."""

    role_title: str = Field(..., description="Job or internship role title.")
    company_name: str = Field(..., description="Organization or employer name.")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM or YYYY).")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM, YYYY, or 'Present').")
    is_current: bool = Field(default=False, description="True if currently employed in this role.")
    responsibilities: list[str] = Field(default_factory=list, description="Key contributions and achievements.")
    technologies_used: list[str] = Field(default_factory=list, description="Demonstrated technologies.")


class CandidateProject(BaseModel):
    """Structured practical portfolio project record."""

    project_name: str = Field(..., description="Project name or headline.")
    description: str = Field(..., description="Narrative summary of architecture and impact.")
    technologies: list[str] = Field(default_factory=list, description="Demonstrated technologies.")
    repository_url: Optional[str] = Field(default=None, description="Repository or project URL.")


class CandidateEducation(BaseModel):
    """Structured educational credential record."""

    institution_name: str = Field(..., description="University, college, or bootcamp.")
    degree_level: DegreeLevel = Field(default=DegreeLevel.NONE, description="Degree hierarchy level.")
    field_of_study: Optional[str] = Field(default=None, description="Major, discipline, or field of study.")
    graduation_date: Optional[str] = Field(default=None, description="Graduation year or completion date.")
    is_enrolled: bool = Field(default=False, description="True if currently actively pursuing.")


class CandidateCareerProfile(BaseModel):
    """Aggregate career profile contract combining evidence, career paths, and eligibility constraints."""

    user_id: str = Field(
        ...,
        description="Unique identifier of the candidate account.",
    )
    display_name: Optional[str] = Field(
        default=None,
        description="Human-readable display name for the candidate (e.g. 'Jane Doe').",
    )
    headline: Optional[str] = Field(
        default=None,
        description="Professional headline or primary role title.",
    )
    location: Optional[str] = Field(
        default=None,
        description="Candidate residential city/country location.",
    )
    bio: Optional[str] = Field(
        default=None,
        description="Brief professional summary or candidate objective.",
    )
    profile_version: int = Field(
        default=1,
        ge=1,
        description="Monotonically increasing version counter for profile evolutions.",
    )
    assessed_skills: list[AssessedSkill] = Field(
        default_factory=list,
        description="Validated competencies with underlying provenance.",
    )
    work_experiences: list[CandidateWorkExperience] = Field(
        default_factory=list,
        description="Chronological work, internship, and professional experiences.",
    )
    education: list[CandidateEducation] = Field(
        default_factory=list,
        description="Degrees, academic credentials, and educational background.",
    )
    projects: list[CandidateProject] = Field(
        default_factory=list,
        description="Portfolio projects and practical software implementations.",
    )
    current_career_path: Optional[CareerPathNode] = Field(
        default=None,
        description="Baseline role reflecting current skills and experience.",
    )
    target_career_paths: list[CareerPathNode] = Field(
        ...,
        min_length=1,
        description="Primary target career ambition(s).",
    )
    adjacent_career_paths: list[CareerPathNode] = Field(
        default_factory=list,
        description="Adjacent career options for discovery expansion.",
    )
    eligibility_constraints: CandidateEligibilityProfile = Field(
        ...,
        description="Strict deterministic eligibility attributes.",
    )
    overall_profile_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate epistemic confidence across all assessed profile attributes.",
    )


class CandidateProfileSummary(BaseModel):
    """Concise representation of a candidate profile for listing and selector UI."""

    user_id: str
    display_name: str
    overall_profile_confidence: float
    profile_version: int
    skill_count: int
    target_role: Optional[str] = None


class StructuredProfileSkillInput(BaseModel):
    """Input payload for a single self-reported or verified skill during onboarding."""

    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency_score: float = Field(default=7.0, ge=1.0, le=10.0)
    evidence_snippet: str = Field(default="", max_length=1000)


class StructuredProfileCreateRequest(BaseModel):
    """Deterministic, structured profile creation payload bypassing LLM inference."""

    user_id: str = Field(..., min_length=2, max_length=80)
    display_name: str = Field(..., min_length=1, max_length=150)
    headline: Optional[str] = Field(default=None, max_length=200)
    highest_degree_level: DegreeLevel = Field(default=DegreeLevel.BACHELORS)
    is_currently_enrolled_student: bool = Field(default=False)
    expected_graduation_date: Optional[date] = None
    total_full_time_experience_months: int = Field(default=0, ge=0)
    authorized_country_codes: list[str] = Field(default_factory=lambda: ["US"])
    requires_visa_sponsorship: bool = Field(default=False)
    allowed_opportunity_categories: list[OpportunityCategory] = Field(
        default_factory=lambda: [OpportunityCategory.FULL_TIME_JOB]
    )
    allowed_work_modes: list[WorkMode] = Field(
        default_factory=lambda: [WorkMode.REMOTE, WorkMode.HYBRID]
    )
    preferred_locations: list[str] = Field(default_factory=list)
    target_role_title: str = Field(default="Software Engineer", min_length=2, max_length=200)
    target_occupation_code: str = Field(default="15-1252.00")
    adjacent_role_title: Optional[str] = Field(default=None, max_length=200)
    adjacent_occupation_code: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=200)
    bio: Optional[str] = Field(default=None, max_length=2000)
    work_experiences: list[CandidateWorkExperience] = Field(default_factory=list)
    education: list[CandidateEducation] = Field(default_factory=list)
    projects: list[CandidateProject] = Field(default_factory=list)
    initial_skills: list[StructuredProfileSkillInput] = Field(default_factory=list)

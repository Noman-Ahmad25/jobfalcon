from __future__ import annotations

from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.common import (
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.profile import CandidateCareerProfile


class CandidateProfilingRequest(BaseModel):
    """Candidate-provided text submission for AI-powered skill and evidence profiling."""

    user_id: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique identifier for the candidate account.",
    )
    resume_text: Optional[str] = Field(
        default=None,
        description="Raw resume text supplied by the candidate.",
    )
    project_descriptions: list[str] = Field(
        default_factory=list,
        description="Narrative descriptions of portfolio projects or open-source repositories.",
    )
    work_experience_text: Optional[str] = Field(
        default=None,
        description="Detailed work, internship, or apprenticeship history.",
    )
    explicit_skills: list[str] = Field(
        default_factory=list,
        description="Self-declared technical, occupational, or domain skills.",
    )
    education_text: Optional[str] = Field(
        default=None,
        description="Academic degrees, coursework, universities, or academic transcripts.",
    )
    target_roles: list[str] = Field(
        default_factory=list,
        description="Desired job titles or target career ambition(s).",
    )
    save_to_repository: bool = Field(
        default=True,
        description="If True, persists the resulting profile and evidence records to the database.",
    )

    @model_validator(mode="after")
    def validate_non_empty_and_size_bounds(self) -> CandidateProfilingRequest:
        total_len = (
            len((self.resume_text or "").strip())
            + sum(len(p.strip()) for p in self.project_descriptions)
            + len((self.work_experience_text or "").strip())
            + sum(len(s.strip()) for s in self.explicit_skills)
            + len((self.education_text or "").strip())
            + sum(len(r.strip()) for r in self.target_roles)
        )
        if total_len == 0:
            raise ValueError(
                "Candidate profiling requires at least one non-empty input field "
                "(resume_text, project_descriptions, work_experience_text, explicit_skills, or education_text)."
            )

        # Enforce max input character limit (25,000 characters)
        if total_len > 25000:
            raise ValueError(
                f"Total input payload size ({total_len} characters) exceeds the maximum allowed limit of 25,000 characters."
            )
        return self


class ExtractedEvidenceSnippet(BaseModel):
    """Verbatim excerpt from candidate input supporting a factual claim."""

    source_type: EvidenceSourceType = Field(
        ...,
        description="Type of source supporting the claim.",
    )
    exact_quote: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Verbatim text excerpt demonstrating the skill or fact.",
    )
    verifiability_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Empirical reliability weight of this evidence source.",
    )
    context_label: Optional[str] = Field(
        default=None,
        description="Optional tag identifying the project or employer context.",
    )


class ExtractedSkillClaim(BaseModel):
    """Competency claim extracted from candidate text, anchored to supporting evidence."""

    skill_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Human-readable canonical skill name.",
    )
    canonical_skill_id: str = Field(
        ...,
        description="Standardized ESCO URI, O*NET identifier, or standardized skill slug.",
    )
    proficiency_score: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="Evidence-calibrated proficiency score on a 1.0 to 10.0 continuous scale.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Epistemic confidence reflecting evidence depth and source verifiability.",
    )
    evidence_snippets: list[ExtractedEvidenceSnippet] = Field(
        ...,
        min_length=1,
        description="Mandatory list of verbatim supporting excerpts from the candidate's input.",
    )
    is_explicitly_stated: bool = Field(
        default=True,
        description="True if explicitly claimed by candidate; False if inferred from project or work context.",
    )
    last_practiced_date: Optional[date] = Field(
        default=None,
        description="Approximate recent demonstration date if discernible.",
    )


class ExtractedWorkExperience(BaseModel):
    """Structured professional experience record."""

    role_title: str
    company_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    responsibilities: list[str] = Field(default_factory=list)
    technologies_used: list[str] = Field(default_factory=list)


class ExtractedProject(BaseModel):
    """Structured project record."""

    project_name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    repository_url: Optional[str] = None


class ExtractedEducation(BaseModel):
    """Structured education record."""

    institution_name: str
    degree_level: DegreeLevel = DegreeLevel.NONE
    field_of_study: Optional[str] = None
    graduation_date: Optional[str] = None
    is_enrolled: bool = False


class EpistemicUncertainties(BaseModel):
    """Explicit audit record of missing, contradictory, and unsupported candidate data."""

    ambiguities: list[str] = Field(
        default_factory=list,
        description="Critical attributes missing or unstated in candidate text (e.g., missing graduation year).",
    )
    contradictions: list[str] = Field(
        default_factory=list,
        description="Contradictory claims detected in the candidate's input (e.g., conflicting dates).",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Declared skills or credentials lacking concrete evidence in projects or experience.",
    )


class LLMCandidateFactExtraction(BaseModel):
    """Strict structured output contract for language model extraction."""

    extracted_full_name: Optional[str] = None
    highest_degree_level: DegreeLevel = DegreeLevel.NONE
    is_currently_enrolled: bool = False
    expected_graduation_date: Optional[date] = None
    authorized_country_codes: list[str] = Field(default_factory=lambda: ["US"])
    requires_visa_sponsorship: bool = False
    total_experience_months: int = 0
    allowed_opportunity_categories: list[OpportunityCategory] = Field(
        default_factory=lambda: [OpportunityCategory.FULL_TIME_JOB]
    )
    allowed_work_modes: list[WorkMode] = Field(
        default_factory=lambda: [WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ON_SITE]
    )
    preferred_locations: list[str] = Field(default_factory=list)
    current_role_title: Optional[str] = None
    target_role_titles: list[str] = Field(default_factory=list)
    adjacent_role_titles: list[str] = Field(default_factory=list)
    skills: list[ExtractedSkillClaim] = Field(default_factory=list)
    work_experiences: list[ExtractedWorkExperience] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    uncertainties: EpistemicUncertainties = Field(default_factory=EpistemicUncertainties)


class CandidateProfilingResponse(BaseModel):
    """Complete profiling response returned to the API caller and frontend."""

    user_id: str
    profile_version: int
    extracted_profile: CandidateCareerProfile
    work_experiences: list[ExtractedWorkExperience]
    projects: list[ExtractedProject]
    education: list[ExtractedEducation]
    stated_skills_count: int
    inferred_skills_count: int
    epistemic_uncertainties: EpistemicUncertainties
    raw_evidence_count: int
    is_persisted: bool
    metadata: dict[str, Any]

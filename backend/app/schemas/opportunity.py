from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode


class OpportunityEligibilityRules(BaseModel):
    """Hard constraints governing deterministic candidate eligibility."""

    opportunity_category: OpportunityCategory = Field(
        ...,
        description="Category classification (e.g., INTERNSHIP, FULL_TIME_JOB, APPRENTICESHIP).",
    )
    eligible_country_codes: list[str] = Field(
        ...,
        min_length=1,
        description="ISO-3166-1 alpha-2 country codes where the role is legally authorized.",
    )
    sponsors_work_visa: bool = Field(
        default=False,
        description="True if the employer actively provides visa sponsorship for foreign nationals.",
    )
    minimum_degree_required: DegreeLevel = Field(
        default=DegreeLevel.NONE,
        description="Minimum academic degree level required to be eligible.",
    )
    requires_active_student_status: bool = Field(
        default=False,
        description="Mandatory True for academic internships and co-ops; False for standard roles.",
    )
    allowed_graduation_window_start: Optional[date] = Field(
        default=None,
        description="Earliest allowable graduation date (inclusive) for student / new-grad cohorts.",
    )
    allowed_graduation_window_end: Optional[date] = Field(
        default=None,
        description="Latest allowable graduation date (inclusive) for student / new-grad cohorts.",
    )
    min_experience_months: int = Field(
        default=0,
        ge=0,
        description="Minimum mandatory full-time experience in months.",
    )
    max_experience_months: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum experience in months (e.g., early career programs capped at 24 months).",
    )
    work_mode: WorkMode = Field(
        ...,
        description="Workplace flexibility: REMOTE, HYBRID, or ON_SITE.",
    )
    location_city_country: list[str] = Field(
        default_factory=list,
        description="City and country descriptors for on-site/hybrid roles (e.g., ['London, UK']).",
    )
    application_deadline: Optional[datetime] = Field(
        default=None,
        description="Application closing date/time. None indicates rolling or unspecified deadline.",
    )

    @field_validator("eligible_country_codes", mode="before")
    @classmethod
    def _normalize_eligible_country_codes(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(code).strip().upper() for code in v if str(code).strip()]
        return v

    @field_validator("location_city_country", mode="before")
    @classmethod
    def _sanitize_opportunity_locations(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [sanitize_untrusted_text(str(loc)) for loc in v if str(loc).strip()]
        return v


class OpportunitySkillRequirement(BaseModel):
    """Structured skill competency expected or preferred by an opportunity."""

    canonical_skill_id: str = Field(
        ...,
        description="Standardized ESCO URI or O*NET skill identifier.",
    )
    skill_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Human-readable canonical skill name.",
    )
    is_mandatory: bool = Field(
        default=True,
        description="True if mandatory requirement; False if preferred/nice-to-have qualification.",
    )
    minimum_proficiency_expected: float = Field(
        default=5.0,
        ge=1.0,
        le=10.0,
        description="Expected minimum proficiency threshold on a 1.0 to 10.0 scale.",
    )

    @field_validator("skill_name", mode="before")
    @classmethod
    def _sanitize_skill_name(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class PolymorphicOpportunity(BaseModel):
    """Canonical polymorphic representation of an ingested career opportunity."""

    opportunity_id: str = Field(
        ...,
        description="Deterministic internal UUID for the opportunity.",
    )
    minhash_signature_hex: str = Field(
        ...,
        description="128-permutation MinHash hexadecimal digest for LSH near-duplicate detection.",
    )
    title: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Job title or opportunity position name.",
    )
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Hiring employer or sponsoring organization.",
    )
    company_domain_verified: bool = Field(
        default=False,
        description="True if company email domain and corporate web presence have been verified.",
    )
    mapped_occupation_code: str = Field(
        ...,
        description="Canonical ESCO or O*NET occupation identifier.",
    )
    eligibility_rules: OpportunityEligibilityRules = Field(
        ...,
        description="Deterministic eligibility criteria.",
    )
    skill_requirements: list[OpportunitySkillRequirement] = Field(
        default_factory=list,
        description="Required and preferred technical and professional competencies.",
    )
    category_specific_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Category-specific metadata (e.g., duration_weeks, stipend, or compensation).",
    )
    sanitized_summary: str = Field(
        ...,
        max_length=2500,
        description="Normalized and injection-neutralized opportunity description summary.",
    )
    source_url: str = Field(
        ...,
        description="Authoritative ATS posting or career board URL.",
    )
    posted_at: datetime = Field(
        ...,
        description="Original posting timestamp.",
    )
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when JobFalcon discovered and ingested this opportunity.",
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality metric reflecting field completeness (compensation, duration, etc.).",
    )
    trust_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Reputation and verification score of the source domain and posting.",
    )
    is_duplicate: bool = Field(
        default=False,
        description="Flagged True if near-duplicate match with existing canonical opportunity.",
    )

    @field_validator("title", "company_name", "sanitized_summary", mode="before")
    @classmethod
    def _enforce_text_sanitization(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))

    @property
    def source_system(self) -> str:
        """Returns the origin source system recorded in category_specific_attributes."""
        return str(self.category_specific_attributes.get("source_system", "generic"))

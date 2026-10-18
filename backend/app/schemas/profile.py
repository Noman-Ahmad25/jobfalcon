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


class CandidateCareerProfile(BaseModel):
    """Aggregate career profile contract combining evidence, career paths, and eligibility constraints."""

    user_id: str = Field(
        ...,
        description="Unique identifier of the candidate account.",
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

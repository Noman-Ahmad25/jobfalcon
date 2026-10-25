from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.common import EvidenceSourceType
from app.schemas.eligibility import EligibilityStatus


class RequirementEvidenceStatus(str, Enum):
    """Categorization of candidate evidence support for an opportunity requirement."""

    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_EVIDENCED = "NOT_EVIDENCED"
    REQUIREMENT_UNCLEAR = "REQUIREMENT_UNCLEAR"


class EvidenceCitation(BaseModel):
    """Verifiable citation linking an explanation directly to a candidate evidence record."""

    evidence_id: str = Field(
        ...,
        description="Immutable identifier of the backing EvidenceRecord.",
    )
    source_type: EvidenceSourceType = Field(
        ...,
        description="Source artifact category (e.g. RESUME_WORK_EXPERIENCE, CODE_REPOSITORY).",
    )
    source_uri: Optional[str] = Field(
        default=None,
        description="URI pointer to raw artifact storage or external repository.",
    )
    snippet: str = Field(
        ...,
        description="Verbatim excerpt grounding this competency claim.",
    )
    verifiability_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Empirical reliability weight of the backing source artifact.",
    )
    observed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when evidence was observed or ingested.",
    )

    @field_validator("snippet", mode="before")
    @classmethod
    def _sanitize_snippet(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class RequirementExplanation(BaseModel):
    """Evidence-grounded explanation for a specific job requirement."""

    canonical_skill_id: str = Field(
        ...,
        description="Standardized ESCO or O*NET skill identifier.",
    )
    skill_name: str = Field(
        ...,
        description="Human-readable canonical skill name.",
    )
    status: RequirementEvidenceStatus = Field(
        ...,
        description="Evidence support status (SUPPORTED, PARTIALLY_SUPPORTED, NOT_EVIDENCED, REQUIREMENT_UNCLEAR).",
    )
    is_mandatory: bool = Field(
        ...,
        description="True if stated as mandatory requirement; False if preferred.",
    )
    candidate_proficiency: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="Candidate demonstrated proficiency (1.0 to 10.0), if evidence exists.",
    )
    expected_proficiency: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="Opportunity minimum expected proficiency threshold.",
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Epistemic confidence derived from evidence depth and source verifiability.",
    )
    citations: list[EvidenceCitation] = Field(
        default_factory=list,
        description="Verifiable evidence citations supporting this requirement match.",
    )
    status_rationale: str = Field(
        ...,
        description="Objective explanation for why this requirement was assigned this status.",
    )


class OpportunityExplanation(BaseModel):
    """Complete, evidence-grounded explanation for a recommended opportunity."""

    opportunity_id: str = Field(
        ...,
        description="Unique identifier of the recommended opportunity.",
    )
    title: str = Field(
        ...,
        description="Job title.",
    )
    company_name: str = Field(
        ...,
        description="Hiring organization name.",
    )
    overall_fit_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic overall fit score.",
    )
    rank: Optional[int] = Field(
        default=None,
        description="Ordinal recommendation rank, if part of a ranked batch.",
    )
    why_matches_summary: str = Field(
        ...,
        description="Concise summary explaining the strongest factors driving the recommendation.",
    )
    top_driving_dimensions: list[str] = Field(
        default_factory=list,
        description="Highest contributing fit dimensions with normalized scores.",
    )
    matched_requirements: list[RequirementExplanation] = Field(
        default_factory=list,
        description="Requirements backed by verifiable candidate evidence meeting or exceeding threshold.",
    )
    partially_supported_requirements: list[RequirementExplanation] = Field(
        default_factory=list,
        description="Requirements with evidence present but below proficiency threshold or low confidence.",
    )
    skill_gaps: list[RequirementExplanation] = Field(
        default_factory=list,
        description="Requirements with no corroborating evidence in candidate profile.",
    )
    eligibility_verdict: EligibilityStatus = Field(
        ...,
        description="Deterministic eligibility status (ELIGIBLE or ELIGIBLE_WITH_UNCERTAINTY).",
    )
    eligibility_explanation: str = Field(
        ...,
        description="Explanation of eligibility checks and any unverified constraints.",
    )
    eligibility_caveats: list[str] = Field(
        default_factory=list,
        description="Specific caveats requiring candidate verification.",
    )
    career_relevance: str = Field(
        ...,
        description="Assessment of alignment with candidate's target ambition or adjacent path.",
    )
    growth_opportunity: str = Field(
        ...,
        description="Competencies and career growth offered by this role based on deterministic growth score.",
    )
    limitations_and_uncertainties: list[str] = Field(
        default_factory=list,
        description="Material caveats (e.g. unstated compensation, missing requirement details, unverified domain).",
    )
    is_llm_polished: bool = Field(
        default=False,
        description="True if language was polished by an LLM; False if generated deterministically.",
    )
    fallback_used: bool = Field(
        default=False,
        description="True if LLM polishing failed or was rejected due to fact violation and fallback was used.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when this explanation was generated.",
    )


class LLMPolishedExplanation(BaseModel):
    """Strict schema for LLM-assisted explanation text polishing."""

    why_matches_summary: str = Field(
        ...,
        description="Polished concise summary of why the job matches candidate evidence.",
    )
    career_relevance: str = Field(
        ...,
        description="Polished assessment of role alignment with target career goals.",
    )
    growth_opportunity: str = Field(
        ...,
        description="Polished explanation of learning and career growth potential.",
    )
    limitations_and_uncertainties: list[str] = Field(
        default_factory=list,
        description="Clearly stated material caveats and missing job information.",
    )

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.eligibility import EligibilityStatus
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile


class RankingDimension(str, Enum):
    """Discrete, transparent dimensions evaluated in candidate-opportunity fit scoring."""

    SKILL_ALIGNMENT = "SKILL_ALIGNMENT"
    CAREER_ALIGNMENT = "CAREER_ALIGNMENT"
    GROWTH_POTENTIAL = "GROWTH_POTENTIAL"
    MARKET_RELEVANCE = "MARKET_RELEVANCE"
    PREFERENCE_FIT = "PREFERENCE_FIT"
    QUALIFICATION_FIT = "QUALIFICATION_FIT"


DEFAULT_RANKING_WEIGHTS: dict[RankingDimension, float] = {
    RankingDimension.SKILL_ALIGNMENT: 0.30,
    RankingDimension.CAREER_ALIGNMENT: 0.20,
    RankingDimension.GROWTH_POTENTIAL: 0.20,
    RankingDimension.MARKET_RELEVANCE: 0.12,
    RankingDimension.PREFERENCE_FIT: 0.10,
    RankingDimension.QUALIFICATION_FIT: 0.08,
}

EARLY_CAREER_WEIGHTS: dict[RankingDimension, float] = {
    RankingDimension.SKILL_ALIGNMENT: 0.25,
    RankingDimension.CAREER_ALIGNMENT: 0.20,
    RankingDimension.GROWTH_POTENTIAL: 0.28,
    RankingDimension.MARKET_RELEVANCE: 0.12,
    RankingDimension.PREFERENCE_FIT: 0.10,
    RankingDimension.QUALIFICATION_FIT: 0.05,
}

EXPERIENCED_WEIGHTS: dict[RankingDimension, float] = {
    RankingDimension.SKILL_ALIGNMENT: 0.35,
    RankingDimension.CAREER_ALIGNMENT: 0.20,
    RankingDimension.GROWTH_POTENTIAL: 0.15,
    RankingDimension.MARKET_RELEVANCE: 0.10,
    RankingDimension.PREFERENCE_FIT: 0.10,
    RankingDimension.QUALIFICATION_FIT: 0.10,
}


class SkillMatchEvidence(BaseModel):
    """Evidence-grounded match between an opportunity requirement and a candidate skill."""

    canonical_skill_id: str = Field(
        ...,
        description="Standardized ESCO URI or O*NET skill identifier.",
    )
    skill_name: str = Field(
        ...,
        description="Canonical human-readable skill title.",
    )
    candidate_proficiency: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="Candidate demonstrated proficiency (1.0 to 10.0 scale).",
    )
    expected_proficiency: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="Opportunity minimum expected proficiency threshold.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Epistemic confidence derived from evidence verifiability.",
    )
    is_mandatory: bool = Field(
        ...,
        description="True if mandatory requirement; False if preferred/nice-to-have qualification.",
    )
    evidence_snippets: list[str] = Field(
        default_factory=list,
        description="Verbatim excerpts from candidate profile grounding this skill claim.",
    )
    match_quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized match quality factor incorporating proficiency ratio and confidence.",
    )


class SkillGap(BaseModel):
    """Identified deficit or unverified qualification relative to opportunity requirements."""

    canonical_skill_id: str = Field(
        ...,
        description="Canonical skill identifier.",
    )
    skill_name: str = Field(
        ...,
        description="Skill title.",
    )
    is_mandatory: bool = Field(
        ...,
        description="True if mandatory requirement; False if preferred.",
    )
    expected_proficiency: float = Field(
        ...,
        description="Minimum expected proficiency threshold.",
    )
    candidate_proficiency: Optional[float] = Field(
        default=None,
        description="Demonstrated proficiency if present but below expectation; None if missing from profile.",
    )
    gap_type: str = Field(
        ...,
        description="Classification: 'MISSING_FROM_PROFILE' or 'PROFICIENCY_DEFICIT'.",
    )


class DimensionScoreBreakdown(BaseModel):
    """Auditable mathematical breakdown of an individual ranking dimension."""

    dimension: RankingDimension = Field(
        ...,
        description="Dimension evaluated.",
    )
    raw_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized dimension score between 0.00 and 1.00.",
    )
    weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relative weight assigned to this dimension.",
    )
    weighted_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Product of raw_score and weight.",
    )
    rationale: str = Field(
        ...,
        description="Transparent explanation of factors contributing to this dimension's score.",
    )
    caveats_or_missing_data: list[str] = Field(
        default_factory=list,
        description="Unstated fields or missing evidence that influenced this dimension.",
    )


class RankedOpportunity(BaseModel):
    """Comprehensive, evidence-grounded recommendation result for an individual opportunity."""

    rank: int = Field(
        ...,
        ge=1,
        description="1-based ordinal ranking position among eligible opportunities.",
    )
    overall_fit_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Total weighted candidate-opportunity fit score (0.00 to 1.00).",
    )
    opportunity: PolymorphicOpportunity = Field(
        ...,
        description="Underlying canonical opportunity listing.",
    )
    eligibility_status: EligibilityStatus = Field(
        ...,
        description="Deterministic eligibility verdict: ELIGIBLE or ELIGIBLE_WITH_UNCERTAINTY.",
    )
    is_eligible: bool = Field(
        default=True,
        description="True if passing all hard eligibility constraints.",
    )
    eligibility_caveats: list[str] = Field(
        default_factory=list,
        description="Caveats requiring candidate verification (e.g. unstated application deadline).",
    )
    dimension_scores: dict[RankingDimension, DimensionScoreBreakdown] = Field(
        ...,
        description="Transparent breakdown across all 6 ranking dimensions.",
    )
    matched_skills: list[SkillMatchEvidence] = Field(
        default_factory=list,
        description="Grounding evidence for verified skill requirements.",
    )
    missing_skills: list[SkillGap] = Field(
        default_factory=list,
        description="Required or preferred skills uncorroborated in candidate profile.",
    )
    growth_skills: list[str] = Field(
        default_factory=list,
        description="Competencies offered by this role that expand candidate's target career goals.",
    )
    recommendation_rationale: str = Field(
        ...,
        description="Clear, concise natural-language justification for why this role is recommended.",
    )
    key_tradeoffs_or_risks: list[str] = Field(
        default_factory=list,
        description="Important considerations (e.g. unstated compensation, rolling deadline, commute).",
    )
    provenance_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Source metadata (source_url, application_url, cluster_size, discovered_at).",
    )


class RankingRequest(BaseModel):
    """Request payload for multi-dimensional candidate-job fit scoring and ranking."""

    candidate_profile: Optional[CandidateCareerProfile] = Field(
        default=None,
        description="Candidate profile. If omitted, user_id will be loaded from repository.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier to load profile from database if profile not directly provided.",
    )
    opportunities: Optional[list[PolymorphicOpportunity]] = Field(
        default=None,
        description="Explicit list of opportunities to score. If omitted, active opportunities in repository are used.",
    )
    weight_profile_name: str = Field(
        default="DEFAULT",
        description="Predefined weight configuration: 'DEFAULT', 'EARLY_CAREER', or 'EXPERIENCED'.",
    )
    custom_weights: Optional[dict[str, float]] = Field(
        default=None,
        description="Optional custom weights dictionary overriding predefined profile.",
    )
    include_ineligible_in_audit: bool = Field(
        default=True,
        description="Whether to include disqualified opportunities in the audit response.",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of top recommendations to return in the ranked output.",
    )


class RankingResponse(BaseModel):
    """Structured response detailing candidate-job ranking, dimension scores, and audit provenance."""

    evaluation_id: str = Field(
        ...,
        description="Unique identifier for this ranking evaluation run.",
    )
    candidate_id: str = Field(
        ...,
        description="Candidate user ID.",
    )
    model_version: str = Field(
        default="jobfalcon-ranking-v1.0-deterministic",
        description="Identifier of the scoring engine model version.",
    )
    weight_profile_used: str = Field(
        ...,
        description="Name of the weight profile applied (e.g. 'DEFAULT', 'EARLY_CAREER').",
    )
    weights: dict[str, float] = Field(
        ...,
        description="Exact normalized dimension weights applied during aggregation.",
    )
    total_candidates_evaluated: int = Field(
        ...,
        description="Total opportunities processed through eligibility and ranking.",
    )
    total_eligible_ranked: int = Field(
        ...,
        description="Number of eligible (or eligible-with-uncertainty) opportunities ranked.",
    )
    total_ineligible_excluded: int = Field(
        ...,
        description="Number of disqualified opportunities strictly excluded from recommendations.",
    )
    ranked_recommendations: list[RankedOpportunity] = Field(
        default_factory=list,
        description="Ordered list of top candidate opportunity recommendations.",
    )
    excluded_ineligible: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Audit records of disqualified listings with their specific failure codes.",
    )
    evaluation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Execution timestamp.",
    )
    execution_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry metadata (duration_ms, baseline_jaccard_comparison, etc.).",
    )

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.common import OpportunityCategory, WorkMode
from app.schemas.opportunity import PolymorphicOpportunity


class OpportunitySearchRequest(BaseModel):
    """Payload for intentional market search across stored and indexed opportunities."""

    query: Optional[str] = Field(
        default=None,
        description="Search keyword matching job title, employer, description, or skills.",
    )
    location: Optional[str] = Field(
        default=None,
        description="Location filter (city, state, or country name).",
    )
    work_mode: Optional[WorkMode] = Field(
        default=None,
        description="Work arrangement: REMOTE, HYBRID, or ON_SITE.",
    )
    category: Optional[OpportunityCategory] = Field(
        default=None,
        description="Opportunity category: FULL_TIME_JOB, INTERNSHIP, APPRENTICESHIP, etc.",
    )
    target_role: Optional[str] = Field(
        default=None,
        description="Standardized role title or occupation focus.",
    )
    min_experience_max_months: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filter for roles requiring at most this many months of experience.",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of specific skill names that must be present in the opportunity.",
    )
    page: int = Field(default=1, ge=1, description="Pagination page index (1-based).")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size limit.")


class OpportunitySearchResponse(BaseModel):
    """Structured response for intentional market search."""

    total: int = Field(..., ge=0, description="Total matching opportunities found.")
    page: int = Field(..., ge=1, description="Current page index.")
    page_size: int = Field(..., ge=1, description="Current page size.")
    total_pages: int = Field(..., ge=0, description="Total number of pages.")
    opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Matched opportunities ordered by recency and relevance.",
    )
    applied_filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of applied search filters.",
    )


class MarketSkillDemand(BaseModel):
    """Grounded empirical demand metric for a specific skill in analyzed opportunities."""

    skill_name: str = Field(..., description="Canonical skill name.")
    count: int = Field(..., ge=0, description="Exact number of opportunities requesting this skill.")
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of analyzed opportunities requiring this skill.",
    )
    is_mandatory_count: int = Field(
        default=0,
        ge=0,
        description="Count of postings where this skill is an explicit mandatory requirement.",
    )
    is_preferred_count: int = Field(
        default=0,
        ge=0,
        description="Count of postings where this skill is preferred or advantageous.",
    )


class MarketSkillCombination(BaseModel):
    """Common co-occurring technology combination grounded in analyzed opportunities."""

    skills: list[str] = Field(..., min_length=2, description="Co-occurring skill names.")
    co_occurrence_count: int = Field(
        ...,
        ge=0,
        description="Number of analyzed opportunities requesting this exact combination.",
    )


class MarketIntelligenceResponse(BaseModel):
    """Empirical market intelligence grounded strictly in verified opportunity listings."""

    total_opportunities_analyzed: int = Field(
        ...,
        ge=0,
        description="Total distinct canonical opportunities analyzed.",
    )
    unique_employers_count: int = Field(
        ...,
        ge=0,
        description="Number of distinct employers represented in the dataset.",
    )
    analysis_scope_summary: str = Field(
        ...,
        description="Honest description of data scope, date window, and source diversity.",
    )
    top_skills: list[MarketSkillDemand] = Field(
        default_factory=list,
        description="Most frequently requested skills ranked strictly by empirical count.",
    )
    top_skill_combinations: list[MarketSkillCombination] = Field(
        default_factory=list,
        description="Frequently co-occurring technology pairs and stacks.",
    )
    experience_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of experience expectations ('Not stated', 'Entry level', etc.).",
    )
    work_mode_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of workplace arrangements (REMOTE, HYBRID, ON_SITE).",
    )
    top_role_families: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Distribution of role categories and occupation codes.",
    )
    data_integrity_notice: str = Field(
        default=(
            "Zero speculative trends: metrics reflect pure empirical distributions "
            "extracted from verified opportunities in this workspace."
        ),
        description="Truthfulness and provenance guarantee.",
    )

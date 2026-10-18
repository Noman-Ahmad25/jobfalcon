from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile


class PipelineEvaluationRequest(BaseModel):
    """Input payload for the deterministic deduplication and eligibility pipeline."""

    candidate_profile: CandidateCareerProfile = Field(
        ...,
        description="Candidate career profile containing skills and eligibility constraints.",
    )
    opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Batch of opportunity records to deduplicate and evaluate.",
    )
    deduplication_threshold: float = Field(
        default=0.85,
        ge=0.50,
        le=1.00,
        description="Provisional MinHash Jaccard similarity threshold for near-duplicate clustering.",
    )
    reference_time: Optional[datetime] = Field(
        default=None,
        description="Optional evaluation timestamp for deadline checks (defaults to UTC now).",
    )


class PipelineEvaluationResponse(BaseModel):
    """Structured output contract for the deterministic evaluation pipeline."""

    candidate_id: str = Field(
        ...,
        description="Identifier of the candidate evaluated.",
    )
    total_submitted: int = Field(
        ...,
        ge=0,
        description="Total opportunity records supplied in the input batch.",
    )
    canonical_count: int = Field(
        ...,
        ge=0,
        description="Count of distinct canonical opportunities after deduplication.",
    )
    duplicate_count: int = Field(
        ...,
        ge=0,
        description="Count of near-duplicate opportunities detected and grouped.",
    )
    eligible_canonical_count: int = Field(
        ...,
        ge=0,
        description="Count of canonical opportunities passing all hard eligibility constraints.",
    )
    uncertain_canonical_count: int = Field(
        ...,
        ge=0,
        description="Count of canonical opportunities passing with unstated/missing caveats.",
    )
    ineligible_canonical_count: int = Field(
        ...,
        ge=0,
        description="Count of canonical opportunities disqualified by hard constraints.",
    )
    canonical_opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Deduplicated canonical opportunities retained for downstream ranking.",
    )
    eligible_opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Subset of canonical opportunities where is_eligible is True.",
    )
    duplicate_records: list[DuplicateRecord] = Field(
        default_factory=list,
        description="Provenance records for all detected duplicates preserving source URLs.",
    )
    clusters: dict[str, OpportunityCluster] = Field(
        default_factory=dict,
        description="Deduplication clusters keyed by canonical opportunity_id.",
    )
    eligibility_results: list[EligibilityResult] = Field(
        default_factory=list,
        description="Deterministic eligibility evaluation breakdown for each canonical opportunity.",
    )
    execution_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata including processing duration and parameter configuration.",
    )

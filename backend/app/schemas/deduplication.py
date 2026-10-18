from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.opportunity import PolymorphicOpportunity


class DuplicateRecord(BaseModel):
    """Provenance record linking a detected near-duplicate listing to its canonical parent."""

    duplicate_id: str = Field(
        ...,
        description="Unique identifier for this deduplication linkage event.",
    )
    canonical_opportunity_id: str = Field(
        ...,
        description="Identifier of the canonical representative opportunity for the cluster.",
    )
    duplicate_opportunity_id: str = Field(
        ...,
        description="Identifier of the opportunity identified as a duplicate.",
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calculated similarity coefficient between duplicate and canonical listing.",
    )
    similarity_method: Literal["EXACT_SHINGLE_JACCARD", "MINHASH_ESTIMATE"] = Field(
        ...,
        description="Mathematical similarity metric used to establish the duplicate match.",
    )
    source_url: str = Field(
        ...,
        description="Original source ATS posting URL of the duplicate listing.",
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when near-duplicate match was detected.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Structured rationale tags (e.g., ['JACCARD_SIMILARITY_EXCEEDS_THRESHOLD']).",
    )


class OpportunityCluster(BaseModel):
    """Group of syndicated listings representing the same underlying career opportunity."""

    canonical_opportunity: PolymorphicOpportunity = Field(
        ...,
        description="Primary opportunity chosen to represent the cluster.",
    )
    duplicate_records: list[DuplicateRecord] = Field(
        default_factory=list,
        description="Associated duplicate provenance records preserving all source identifiers.",
    )
    all_source_urls: list[str] = Field(
        default_factory=list,
        description="Exhaustive list of source URLs where this opportunity was syndicated.",
    )
    cluster_size: int = Field(
        default=1,
        ge=1,
        description="Total count of listings in this cluster (1 canonical + N duplicates).",
    )


class DeduplicationResult(BaseModel):
    """Complete output of a batch deduplication evaluation."""

    canonical_opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="De-duplicated opportunities retained for downstream ranking and display.",
    )
    duplicate_opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Near-duplicate opportunities preserved with is_duplicate=True flag.",
    )
    duplicate_records: list[DuplicateRecord] = Field(
        default_factory=list,
        description="Detailed provenance records for every duplicate detection.",
    )
    clusters: dict[str, OpportunityCluster] = Field(
        default_factory=dict,
        description="Cluster lookup keyed by canonical opportunity_id.",
    )
    total_evaluated: int = Field(0, ge=0)
    canonical_count: int = Field(0, ge=0)
    duplicate_count: int = Field(0, ge=0)

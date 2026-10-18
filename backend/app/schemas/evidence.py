from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.common import EvidenceSourceType


class EvidenceRecord(BaseModel):
    """Verifiable evidence record grounding a candidate skill claim or market claim.

    All untrusted snippets are deterministically normalized and sanitized upon model creation.
    """

    evidence_id: str = Field(
        ...,
        description="Deterministic UUID or cryptographic hash of the source artifact snippet.",
    )
    source_type: EvidenceSourceType = Field(
        ...,
        description="Categorized source artifact type (e.g., repository, transcript, resume).",
    )
    source_uri: Optional[str] = Field(
        default=None,
        description="URI pointer to raw artifact storage (MinIO/S3) or external repository.",
    )
    extracted_snippet: str = Field(
        ...,
        max_length=1000,
        description="Verbatim excerpt or concrete metric supporting the competency claim.",
    )
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the evidence was observed or ingested.",
    )
    verifiability_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Empirical reliability weight of the source artifact (1.0 for production code, 0.25 for uncorroborated keywords).",
    )

    @field_validator("extracted_snippet", mode="before")
    @classmethod
    def _sanitize_snippet(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))

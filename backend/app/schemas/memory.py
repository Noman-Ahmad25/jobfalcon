from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text


class MemoryType(str, Enum):
    """Semantic domain for persistent candidate memory statements."""

    CAREER_GOAL = "CAREER_GOAL"
    SKILL_CORRECTION = "SKILL_CORRECTION"
    PREFERENCE_SHIFT = "PREFERENCE_SHIFT"
    FEEDBACK_SIGNAL = "FEEDBACK_SIGNAL"
    MARKET_NOTE = "MARKET_NOTE"


class ProvenanceLevel(str, Enum):
    """Confidence and epistemic grounding category of candidate intelligence."""

    VERIFIED = "VERIFIED"          # Grounded in official transcripts, confirmed certificates, or validated employer records
    USER_PROVIDED = "USER_PROVIDED" # Explicitly submitted or confirmed by the candidate
    AI_INFERRED = "AI_INFERRED"     # Synthesized or inferred by discovery/profiling models
    OUTDATED = "OUTDATED"           # Historically valid but superseded by newer changes


class CandidateCareerMemoryItem(BaseModel):
    """A versioned statement representing persistent candidate career understanding with provenance."""

    memory_id: str = Field(..., description="Unique memory fact identifier.")
    user_id: str = Field(..., description="Candidate user ID.")
    memory_type: MemoryType = Field(..., description="Semantic type of memory fact.")
    statement: str = Field(..., min_length=2, max_length=1500, description="Clean textual fact or preference.")
    provenance_level: ProvenanceLevel = Field(..., description="Epistemic grounding level.")
    source_context: Optional[str] = Field(default=None, description="Originating workflow, prompt, or artifact context.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence metric (0.0 to 1.0).")
    version: int = Field(default=1, ge=1, description="Sequential version number.")
    superseded_by: Optional[str] = Field(default=None, description="Pointer to memory_id that superseded this fact.")
    change_reason: Optional[str] = Field(default=None, description="Why this fact was updated or superseded.")
    is_active: bool = Field(default=True, description="True if currently applicable; False if archived/superseded.")
    effective_from: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp from which this fact is effective.",
    )
    effective_to: Optional[datetime] = Field(default=None, description="Timestamp when this version was superseded.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp.",
    )

    @field_validator("statement", "source_context", "change_reason", mode="before")
    @classmethod
    def _sanitize_fields(cls, v: Any) -> Optional[str]:
        if v is not None:
            return sanitize_untrusted_text(str(v))
        return None


class CreateMemoryRequest(BaseModel):
    """Payload to create a new career memory fact."""

    memory_type: MemoryType = Field(..., description="Semantic domain category.")
    statement: str = Field(..., min_length=2, max_length=1500, description="Fact, goal, or preference statement.")
    provenance_level: ProvenanceLevel = Field(
        default=ProvenanceLevel.USER_PROVIDED,
        description="Epistemic grounding level.",
    )
    source_context: Optional[str] = Field(default="user_profile_edit", description="Context of discovery or creation.")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("statement", "source_context", mode="before")
    @classmethod
    def _sanitize_create(cls, v: Any) -> Optional[str]:
        if v is not None:
            return sanitize_untrusted_text(str(v))
        return None


class UpdateMemoryRequest(BaseModel):
    """Payload to update an existing memory fact, archiving the current version."""

    statement: str = Field(..., min_length=2, max_length=1500, description="Updated statement.")
    change_reason: str = Field(..., min_length=2, max_length=500, description="Mandatory reason for updating the fact.")
    provenance_level: Optional[ProvenanceLevel] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @field_validator("statement", "change_reason", mode="before")
    @classmethod
    def _sanitize_update(cls, v: Any) -> Optional[str]:
        if v is not None:
            return sanitize_untrusted_text(str(v))
        return None


class MemoryHistoryResponse(BaseModel):
    """Full version audit trail for a memory statement chain."""

    memory_id: str
    user_id: str
    active_version: Optional[CandidateCareerMemoryItem] = None
    version_history: list[CandidateCareerMemoryItem] = Field(default_factory=list)

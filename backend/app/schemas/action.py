from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text


class ActionType(str, Enum):
    """Categorical user opportunity interaction state."""

    SAVED = "SAVED"
    APPLIED = "APPLIED"
    DISMISSED = "DISMISSED"
    SOFT_OVERRIDDEN = "SOFT_OVERRIDDEN"
    UNSAVED = "UNSAVED"
    RESTORED = "RESTORED"


class ActionReasonCategory(str, Enum):
    """Granular rationale category behind user actions and dismissals."""

    SALARY = "SALARY"
    LOCATION = "LOCATION"
    ROLE_MISMATCH = "ROLE_MISMATCH"
    COMPANY_PREFERENCE = "COMPANY_PREFERENCE"
    EXPERIENCE_OVERRIDE = "EXPERIENCE_OVERRIDE"
    COMMUTE_OVERRIDE = "COMMUTE_OVERRIDE"
    QUALIFICATION_OVERRIDE = "QUALIFICATION_OVERRIDE"
    GENERAL = "GENERAL"


class CandidateOpportunityActionRecord(BaseModel):
    """Immutable event-sourced action record tracking historical interaction transitions."""

    id: str = Field(..., description="Unique action identifier.")
    user_id: str = Field(..., description="Candidate user ID.")
    opportunity_id: str = Field(..., description="Target opportunity ID.")
    action_type: ActionType = Field(..., description="Action recorded in this transition.")
    previous_state: Optional[str] = Field(default=None, description="Previous interaction state prior to transition.")
    reason_category: Optional[ActionReasonCategory] = Field(default=None, description="Action rationale category.")
    user_notes: Optional[str] = Field(default=None, description="Optional candidate notes or feedback.")
    soft_override_rationale: Optional[str] = Field(default=None, description="Rationale for soft-rejection overrides.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when interaction transition occurred.",
    )

    @field_validator("user_notes", "soft_override_rationale", mode="before")
    @classmethod
    def _sanitize_notes(cls, v: Any) -> Optional[str]:
        if v is not None:
            return sanitize_untrusted_text(str(v))
        return None


class RecordActionRequest(BaseModel):
    """Request payload to record an opportunity interaction."""

    user_id: Optional[str] = Field(default=None, description="Candidate user ID if not provided as path/query param.")
    action_type: ActionType = Field(..., description="Action type to perform.")
    reason_category: Optional[ActionReasonCategory] = Field(
        default=ActionReasonCategory.GENERAL,
        description="Reason category (e.g. SALARY, LOCATION, ROLE_MISMATCH).",
    )
    user_notes: Optional[str] = Field(default=None, max_length=1000, description="Optional notes or feedback.")
    soft_override_rationale: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Mandatory rationale when overriding a soft eligibility rejection.",
    )

    @field_validator("user_notes", "soft_override_rationale", mode="before")
    @classmethod
    def _sanitize_request_notes(cls, v: Any) -> Optional[str]:
        if v is not None:
            return sanitize_untrusted_text(str(v))
        return None


class CandidateActionsSummary(BaseModel):
    """Aggregated view of latest interaction states for a candidate."""

    user_id: str
    saved_opportunity_ids: list[str] = Field(default_factory=list)
    applied_opportunity_ids: list[str] = Field(default_factory=list)
    dismissed_opportunity_ids: list[str] = Field(default_factory=list)
    soft_overridden_opportunity_ids: list[str] = Field(default_factory=list)
    latest_actions_by_opp: dict[str, ActionType] = Field(default_factory=dict)
    total_actions_recorded: int = 0

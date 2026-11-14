from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.repositories.interfaces import CandidateActionRepository
from app.db.repositories.sqlite_repository import SQLiteCandidateActionRepository
from app.schemas.action import (
    ActionType,
    CandidateActionsSummary,
    CandidateOpportunityActionRecord,
    RecordActionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/actions", tags=["Candidate Opportunity Actions & History"])


def get_candidate_action_repository() -> CandidateActionRepository:
    """Dependency provider for CandidateActionRepository."""
    return SQLiteCandidateActionRepository()


@router.post(
    "/opportunities/{opportunity_id}",
    response_model=CandidateOpportunityActionRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Record Candidate Opportunity Interaction Action",
)
def record_opportunity_action(
    opportunity_id: str,
    request: RecordActionRequest,
    user_id: Optional[str] = Query(None, description="Candidate user ID"),
    repo: CandidateActionRepository = Depends(get_candidate_action_repository),
) -> CandidateOpportunityActionRecord:
    """Records an event-sourced action transition for an opportunity."""
    resolved_user_id = (request.user_id or user_id or "").strip()
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be provided in request body or query parameter.",
        )

    # Validate soft override rationale if overriding
    if request.action_type == ActionType.SOFT_OVERRIDDEN and not (request.soft_override_rationale or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="soft_override_rationale is required when recording a SOFT_OVERRIDDEN action.",
        )

    # Determine previous state if any
    latest_map = repo.get_latest_actions(resolved_user_id)
    previous_record = latest_map.get(opportunity_id)
    prev_state = previous_record.action_type.value if previous_record else None

    action_record = CandidateOpportunityActionRecord(
        id=f"act_{uuid4().hex[:12]}",
        user_id=resolved_user_id,
        opportunity_id=opportunity_id,
        action_type=request.action_type,
        previous_state=prev_state,
        reason_category=request.reason_category,
        user_notes=request.user_notes,
        soft_override_rationale=request.soft_override_rationale,
    )

    repo.record_action(action_record)
    logger.info(
        "Candidate %s performed action %s on %s (prev: %s)",
        resolved_user_id,
        request.action_type.value,
        opportunity_id,
        prev_state,
    )
    return action_record


@router.get(
    "/candidate/{user_id}",
    response_model=CandidateActionsSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Aggregated Action Summary for Candidate",
)
def get_actions_summary(
    user_id: str,
    repo: CandidateActionRepository = Depends(get_candidate_action_repository),
) -> CandidateActionsSummary:
    """Returns active saved, applied, dismissed, and soft-overridden opportunity lists."""
    return repo.get_actions_summary(user_id)


@router.get(
    "/candidate/{user_id}/history",
    response_model=list[CandidateOpportunityActionRecord],
    status_code=status.HTTP_200_OK,
    summary="Get Full Action Transition History for Candidate",
)
def get_action_history(
    user_id: str,
    opportunity_id: Optional[str] = Query(None, description="Optional opportunity filter"),
    limit: int = Query(100, ge=1, le=500),
    repo: CandidateActionRepository = Depends(get_candidate_action_repository),
) -> list[CandidateOpportunityActionRecord]:
    """Retrieves full transition event history for auditability and feedback learning."""
    return repo.get_action_history(user_id, opportunity_id=opportunity_id, limit=limit)


@router.get(
    "/candidate/{user_id}/overridden",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="Get Soft-Overridden Opportunity IDs for Candidate",
)
def get_overridden_opportunities(
    user_id: str,
    repo: CandidateActionRepository = Depends(get_candidate_action_repository),
) -> list[str]:
    """Retrieves list of opportunity IDs whose soft rejections were overridden."""
    return repo.get_overridden_opportunity_ids(user_id)

from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.repositories.interfaces import CareerMemoryRepository
from app.db.repositories.sqlite_repository import SQLiteCareerMemoryRepository
from app.schemas.memory import (
    CandidateCareerMemoryItem,
    CreateMemoryRequest,
    MemoryHistoryResponse,
    MemoryType,
    ProvenanceLevel,
    UpdateMemoryRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Candidate Career Memory & Versioned Understanding"])


def get_career_memory_repository() -> CareerMemoryRepository:
    """Dependency provider for CareerMemoryRepository."""
    return SQLiteCareerMemoryRepository()


@router.get(
    "/candidate/{user_id}",
    response_model=list[CandidateCareerMemoryItem],
    status_code=status.HTTP_200_OK,
    summary="List Candidate Active Career Memories",
)
def list_candidate_memories(
    user_id: str,
    memory_type: Optional[MemoryType] = Query(None, description="Optional memory type filter"),
    include_inactive: bool = Query(False, description="Whether to include superseded or inactive memories"),
    repo: CareerMemoryRepository = Depends(get_career_memory_repository),
) -> list[CandidateCareerMemoryItem]:
    """Retrieves persistent career memory facts for candidate understanding."""
    if include_inactive:
        items = repo.list_all_memories_for_candidate(user_id, include_inactive=True)
        if memory_type:
            items = [m for m in items if m.memory_type == memory_type]
        return items
    return repo.list_active_memories(user_id, memory_type=memory_type)


@router.post(
    "/candidate/{user_id}",
    response_model=CandidateCareerMemoryItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record New Career Memory Statement",
)
def create_candidate_memory(
    user_id: str,
    request: CreateMemoryRequest,
    repo: CareerMemoryRepository = Depends(get_career_memory_repository),
) -> CandidateCareerMemoryItem:
    """Persists a new versioned career memory item with epistemic provenance."""
    memory_item = CandidateCareerMemoryItem(
        memory_id=f"mem_{uuid4().hex[:12]}",
        user_id=user_id,
        memory_type=request.memory_type,
        statement=request.statement,
        provenance_level=request.provenance_level,
        source_context=request.source_context,
        confidence_score=request.confidence_score,
        version=1,
    )
    repo.add_memory(memory_item)
    logger.info("Recorded new memory %s for candidate %s (%s)", memory_item.memory_id, user_id, memory_item.memory_type)
    return memory_item


@router.put(
    "/candidate/{user_id}/{memory_id}",
    response_model=CandidateCareerMemoryItem,
    status_code=status.HTTP_200_OK,
    summary="Update Career Memory (Creates Superseding Version)",
)
def update_candidate_memory(
    user_id: str,
    memory_id: str,
    request: UpdateMemoryRequest,
    repo: CareerMemoryRepository = Depends(get_career_memory_repository),
) -> CandidateCareerMemoryItem:
    """Supersedes an existing memory fact, archiving the current one and maintaining lineage."""
    try:
        new_version = repo.update_memory(
            user_id=user_id,
            current_memory_id=memory_id,
            new_statement=request.statement,
            change_reason=request.change_reason,
            provenance_level=request.provenance_level,
            confidence_score=request.confidence_score,
        )
        logger.info(
            "Superseded memory %s -> %s (v%d) for %s",
            memory_id,
            new_version.memory_id,
            new_version.version,
            user_id,
        )
        return new_version
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/candidate/{user_id}/{memory_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Career Memory Statement",
)
def deactivate_candidate_memory(
    user_id: str,
    memory_id: str,
    reason: str = Query("Deactivated by candidate", description="Reason for deactivation"),
    repo: CareerMemoryRepository = Depends(get_career_memory_repository),
) -> dict[str, str]:
    """Deactivates/archives an active memory statement."""
    success = repo.deactivate_memory(user_id=user_id, memory_id=memory_id, reason=reason)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active memory statement '{memory_id}' not found for candidate '{user_id}'.",
        )
    return {"status": "deactivated", "memory_id": memory_id}


@router.get(
    "/candidate/{user_id}/lineage/{memory_id}",
    response_model=MemoryHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Memory Version Lineage and Audit History",
)
def get_memory_lineage(
    user_id: str,
    memory_id: str,
    repo: CareerMemoryRepository = Depends(get_career_memory_repository),
) -> MemoryHistoryResponse:
    """Retrieves full historical audit trail for a memory statement chain."""
    history = repo.get_memory_history(user_id, memory_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No memory statement history found for '{memory_id}'.",
        )
    active = next((m for m in history if m.is_active), None)
    return MemoryHistoryResponse(
        memory_id=memory_id,
        user_id=user_id,
        active_version=active,
        version_history=history,
    )

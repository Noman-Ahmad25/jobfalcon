from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DiscoveryRunRepository,
    DuplicateClusterRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDiscoveryRunRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteOpportunityRepository,
    SQLiteRecommendationRepository,
)
from app.modules.orchestration.events import discovery_event_manager
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    AdaptiveDiscoveryResponse,
    DiscoveryRun,
    DiscoveryRunStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestration", tags=["Agent Orchestration & Adaptive Discovery"])


def get_profile_repository() -> CandidateProfileRepository:
    """Dependency provider for CandidateProfileRepository."""
    return SQLiteCandidateProfileRepository()


def get_opportunity_repository() -> OpportunityRepository:
    """Dependency provider for OpportunityRepository."""
    return SQLiteOpportunityRepository()


def get_cluster_repository() -> DuplicateClusterRepository:
    """Dependency provider for DuplicateClusterRepository."""
    return SQLiteDuplicateClusterRepository()


def get_recommendation_repository() -> RecommendationRepository:
    """Dependency provider for RecommendationRepository."""
    return SQLiteRecommendationRepository()


def get_run_repository() -> DiscoveryRunRepository:
    """Dependency provider for DiscoveryRunRepository."""
    return SQLiteDiscoveryRunRepository()


def get_orchestration_workflow(
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    cluster_repo: DuplicateClusterRepository = Depends(get_cluster_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    run_repo: DiscoveryRunRepository = Depends(get_run_repository),
) -> AdaptiveDiscoveryWorkflow:
    """Dependency provider for AdaptiveDiscoveryWorkflow."""
    return AdaptiveDiscoveryWorkflow(
        opp_repo=opp_repo,
        cluster_repo=cluster_repo,
        profile_repo=profile_repo,
        rec_repo=rec_repo,
        run_repo=run_repo,
    )


@router.post(
    "/discovery/run",
    response_model=AdaptiveDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Agentic Adaptive Opportunity Discovery Workflow (Synchronous)",
)
async def run_adaptive_discovery(
    request: AdaptiveDiscoveryRequest,
    workflow: AdaptiveDiscoveryWorkflow = Depends(get_orchestration_workflow),
) -> AdaptiveDiscoveryResponse:
    """Coordinates an adaptive agent workflow for career opportunity discovery synchronously.

    Persists the full DiscoveryRun and its results for session reloadability.
    """
    try:
        return await workflow.run(request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("Error executing adaptive discovery workflow: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during adaptive opportunity discovery orchestration.",
        ) from None


@router.post(
    "/discovery/start",
    response_model=DiscoveryRun,
    status_code=status.HTTP_200_OK,
    summary="Start or Reconnect to Asynchronous Opportunity Discovery Run",
)
async def start_adaptive_discovery(
    request: AdaptiveDiscoveryRequest,
    workflow: AdaptiveDiscoveryWorkflow = Depends(get_orchestration_workflow),
) -> DiscoveryRun:
    """Launches the LangGraph workflow in the background and returns a persistent DiscoveryRun immediately.

    If an active (non-terminal) run is already executing for the candidate, returns that active run
    rather than launching a redundant duplicate search.
    """
    try:
        return await workflow.start_run(request)
    except Exception as exc:
        logger.error("Error starting discovery run: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate discovery run: {exc!s}",
        ) from None


@router.get(
    "/discovery/runs/{run_id}",
    response_model=DiscoveryRun,
    summary="Retrieve Persistent Discovery Run State & Results",
)
async def get_discovery_run(
    run_id: str,
    run_repo: DiscoveryRunRepository = Depends(get_run_repository),
) -> DiscoveryRun:
    """Retrieves a durable DiscoveryRun by identifier, including telemetry and completed results."""
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery run with ID '{run_id}' not found.",
        )
    return run


@router.get(
    "/discovery/candidate/{candidate_id}/latest-run",
    response_model=DiscoveryRun,
    summary="Retrieve Latest Discovery Run for Candidate",
)
async def get_latest_discovery_run_for_candidate(
    candidate_id: str,
    run_repo: DiscoveryRunRepository = Depends(get_run_repository),
) -> DiscoveryRun:
    """Retrieves the most recent discovery run (active or completed) for the specified candidate."""
    run = run_repo.get_latest_for_candidate(candidate_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No discovery runs found for candidate '{candidate_id}'.",
        )
    return run


@router.get(
    "/discovery/runs/{run_id}/stream",
    summary="Stream Real-Time Workflow Telemetry via Server-Sent Events (SSE)",
)
async def stream_discovery_run_events(
    run_id: str,
    run_repo: DiscoveryRunRepository = Depends(get_run_repository),
) -> StreamingResponse:
    """Provides a live Server-Sent Events stream emitting real workflow events as LangGraph executes."""
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discovery run '{run_id}' not found.",
        )

    async def event_generator():
        # 1. Send initial state snapshot
        initial_data = json.dumps({
            "type": "INITIAL_SNAPSHOT",
            "run_id": run.run_id,
            "candidate_id": run.candidate_id,
            "status": run.status.value,
            "events": [e.model_dump(mode="json") for e in run.timeline_events],
            "total_discovered_raw": run.total_discovered_raw,
            "canonical_count": run.canonical_count,
            "duplicate_count": run.duplicate_count,
            "eligible_count": run.eligible_count,
            "response": run.response.model_dump(mode="json") if run.response else None,
        })
        yield f"event: initial_state\ndata: {initial_data}\n\n"

        # If already completed or failed, terminate stream
        if run.status in SQLiteDiscoveryRunRepository.TERMINAL_STATUSES:
            return

        # 2. Subscribe to live broker
        queue = await discovery_event_manager.subscribe(run_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    payload = json.dumps(event.model_dump(mode="json"))
                    yield f"event: workflow_event\ndata: {payload}\n\n"
                    if event.status in (
                        DiscoveryRunStatus.COMPLETED,
                        DiscoveryRunStatus.FAILED,
                        DiscoveryRunStatus.CANCELLED,
                    ):
                        # Send completed event and close
                        break
                except asyncio.TimeoutError:
                    # Send keepalive ping to maintain connection
                    yield ": keepalive\n\n"
                    # Refresh state from repository in case final event was missed
                    refreshed = run_repo.get(run_id)
                    if (
                        refreshed
                        and refreshed.status in SQLiteDiscoveryRunRepository.TERMINAL_STATUSES
                    ):
                        done_payload = json.dumps({
                            "type": "RUN_TERMINATED",
                            "run_id": run_id,
                            "status": refreshed.status.value,
                            "response": (
                                refreshed.response.model_dump(mode="json")
                                if refreshed.response
                                else None
                            ),
                        })
                        yield f"event: run_completed\ndata: {done_payload}\n\n"
                        break
        finally:
            await discovery_event_manager.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


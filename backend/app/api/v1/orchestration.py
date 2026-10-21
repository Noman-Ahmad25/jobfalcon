from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteOpportunityRepository,
    SQLiteRecommendationRepository,
)
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    AdaptiveDiscoveryResponse,
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


def get_orchestration_workflow(
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    cluster_repo: DuplicateClusterRepository = Depends(get_cluster_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
) -> AdaptiveDiscoveryWorkflow:
    """Dependency provider for AdaptiveDiscoveryWorkflow."""
    return AdaptiveDiscoveryWorkflow(
        opp_repo=opp_repo,
        cluster_repo=cluster_repo,
        profile_repo=profile_repo,
        rec_repo=rec_repo,
    )


@router.post(
    "/discovery/run",
    response_model=AdaptiveDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Agentic Adaptive Opportunity Discovery Workflow",
)
async def run_adaptive_discovery(
    request: AdaptiveDiscoveryRequest,
    workflow: AdaptiveDiscoveryWorkflow = Depends(get_orchestration_workflow),
) -> AdaptiveDiscoveryResponse:
    """Coordinates an adaptive agent workflow for career opportunity discovery.

    Features:
    1. Retrieval of candidate profile and evidence.
    2. Taxonomic skill-to-role mapping.
    3. Multi-source search strategy formulation.
    4. Bounded adaptive search loop with coverage gap analysis and query relaxation/expansion.
    5. Cross-source MinHash LSH deduplication.
    6. Authoritative deterministic eligibility evaluation.
    7. Observable execution timeline with explicit termination reason.
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

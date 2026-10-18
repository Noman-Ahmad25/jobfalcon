from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.repositories.interfaces import CandidateProfileRepository
from app.db.repositories.sqlite_repository import SQLiteCandidateProfileRepository
from app.modules.discovery.connectors import get_default_connectors
from app.modules.discovery.coordinator import DiscoveryCoordinator
from app.modules.discovery.role_mapper import generate_discovery_query_plan
from app.schemas.discovery import (
    ConnectorHealthReport,
    DiscoveryQueryPlan,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
)
from app.schemas.profile import CandidateCareerProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Multi-Source Opportunity Discovery"])


class DiscoveryPlanRequest(BaseModel):
    """Request payload for query plan generation."""

    candidate_profile: Optional[CandidateCareerProfile] = Field(
        default=None,
        description="Full candidate profile. If omitted, user_id will be loaded from repository.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier to retrieve candidate profile from database.",
    )


def get_profile_repository() -> CandidateProfileRepository:
    """Dependency provider for CandidateProfileRepository."""
    return SQLiteCandidateProfileRepository()


def get_discovery_coordinator() -> DiscoveryCoordinator:
    """Dependency provider for DiscoveryCoordinator."""
    return DiscoveryCoordinator()


@router.get(
    "/connectors",
    response_model=list[ConnectorHealthReport],
    status_code=status.HTTP_200_OK,
    summary="List Discovery Connectors and Operational Health",
)
async def list_connectors() -> list[ConnectorHealthReport]:
    """Inspects the operational health and connectivity of configured discovery connectors.

    Reports:
    - Web Search Aggregator
    - India Jobs MCP (@borgius/india-jobs-mcp)
    - JobSpy MCP (jobspy-mcp-server)
    - Direct Company ATS Feeds (Greenhouse, Lever, Ashby)

    Status indicates CONNECTED, MOCKED_FALLBACK, or UNAVAILABLE_MISSING_BINARY without falsified claims.
    """
    connectors = get_default_connectors(mock_mode=True)
    reports = []
    for connector in connectors:
        try:
            report = await connector.check_health()
            reports.append(report)
        except Exception as exc:
            logger.error("Health check failed for connector %s: %s", connector.connector_id, exc)
    return reports


@router.post(
    "/plan",
    response_model=DiscoveryQueryPlan,
    status_code=status.HTTP_200_OK,
    summary="Generate Skill-to-Role Mapping & Multi-Source Query Plan",
)
async def generate_plan(
    request: DiscoveryPlanRequest,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
) -> DiscoveryQueryPlan:
    """Relates candidate skills and career preferences to standardized O*NET role families.

    Generates parameterized search queries with seniority adjustments, location filters,
    and taxonomy adjacency tracking.
    """
    profile = request.candidate_profile
    if profile is None and request.user_id:
        profile = profile_repo.get(request.user_id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile could not be resolved. Please provide 'candidate_profile' or valid 'user_id'.",
        )

    try:
        return generate_discovery_query_plan(profile)
    except Exception as exc:
        logger.error("Failed to generate discovery query plan: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate discovery query plan.",
        ) from None


@router.post(
    "/run",
    response_model=DiscoveryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Multi-Source Discovery, Deduplication & Eligibility Evaluation",
)
async def run_discovery(
    request: DiscoveryRunRequest,
    coordinator: DiscoveryCoordinator = Depends(get_discovery_coordinator),
) -> DiscoveryRunResponse:
    """Coordinates end-to-end multi-source opportunity discovery.

    1. Generates targeted query plan from candidate profile.
    2. Concurrently invokes configured connectors with bounded timeouts.
    3. Traps partial connector errors without failing the overall discovery run.
    4. Runs early cross-source MinHash LSH deduplication across syndicated listings.
    5. Persists opportunities and duplicate clusters to repositories.
    6. Evaluates deterministic eligibility on canonical opportunities with audit provenance.
    """
    try:
        return await coordinator.execute_discovery(request)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("Error executing discovery coordinator: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during multi-source opportunity discovery.",
        ) from None

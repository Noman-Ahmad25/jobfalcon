from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    CareerPathRepository,
    OpportunityRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteCareerPathRepository,
    SQLiteOpportunityRepository,
)
from app.modules.career_path.service import CareerPathIntelligenceService
from app.schemas.career_path import (
    CareerPathAssessmentResponse,
    DevelopmentActionItem,
    PersonalizedDevelopmentPlan,
    RoleTargetAssessment,
    UpdateActionProgressRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career-path", tags=["Career Path Intelligence & Development Planning"])


# =============================================================================
# Dependencies
# =============================================================================

def get_profile_repository() -> CandidateProfileRepository:
    return SQLiteCandidateProfileRepository()


def get_opportunity_repository() -> OpportunityRepository:
    return SQLiteOpportunityRepository()


def get_career_path_repository() -> CareerPathRepository:
    return SQLiteCareerPathRepository()


def get_career_path_service() -> CareerPathIntelligenceService:
    return CareerPathIntelligenceService()


# =============================================================================
# Request Schemas
# =============================================================================

class RefreshAssessmentRequest(BaseModel):
    target_roles: Optional[list[str]] = Field(
        default=None,
        description="Optional list of target role titles overriding candidate profile defaults",
    )
    include_repo_opportunities: bool = Field(
        default=True,
        description="Whether to incorporate active repository opportunities in coverage and market signals",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/candidate/{user_id}/assessment",
    response_model=CareerPathAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Full Career Path Assessment & Graph",
)
def get_candidate_career_path_assessment(
    user_id: str,
    refresh: bool = Query(default=False, description="Force recomputation of assessment"),
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
    service: CareerPathIntelligenceService = Depends(get_career_path_service),
) -> CareerPathAssessmentResponse:
    """Retrieves or computes a candidate's complete career path assessment and transition graph."""
    if not refresh:
        existing = career_repo.get_latest_assessment(user_id)
        if existing:
            return existing

    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    opportunities = opp_repo.list_all(active_only=True)
    assessment = service.assess_candidate_career_paths(
        candidate=candidate,
        discovered_opportunities=opportunities,
    )
    career_repo.save_assessment(assessment)
    career_repo.save_development_plan(assessment.development_plan)
    return assessment


@router.get(
    "/candidate/{user_id}/roles",
    response_model=list[RoleTargetAssessment],
    status_code=status.HTTP_200_OK,
    summary="Get Target and Adjacent Role Assessments",
)
def get_candidate_target_and_adjacent_roles(
    user_id: str,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
    service: CareerPathIntelligenceService = Depends(get_career_path_service),
) -> list[RoleTargetAssessment]:
    """Returns assessed target, adjacent, and exploratory roles for the candidate."""
    existing = career_repo.get_latest_assessment(user_id)
    if existing:
        return existing.role_assessments

    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    opportunities = opp_repo.list_all(active_only=True)
    assessment = service.assess_candidate_career_paths(
        candidate=candidate,
        discovered_opportunities=opportunities,
    )
    career_repo.save_assessment(assessment)
    career_repo.save_development_plan(assessment.development_plan)
    return assessment.role_assessments


@router.get(
    "/candidate/{user_id}/plan",
    response_model=PersonalizedDevelopmentPlan,
    status_code=status.HTTP_200_OK,
    summary="Get Candidate Personalized Development Plan",
)
def get_candidate_development_plan(
    user_id: str,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
    service: CareerPathIntelligenceService = Depends(get_career_path_service),
) -> PersonalizedDevelopmentPlan:
    """Retrieves the latest personalized development plan for the candidate."""
    existing_plan = career_repo.get_latest_development_plan(user_id)
    if existing_plan:
        return existing_plan

    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    opportunities = opp_repo.list_all(active_only=True)
    assessment = service.assess_candidate_career_paths(
        candidate=candidate,
        discovered_opportunities=opportunities,
    )
    career_repo.save_assessment(assessment)
    career_repo.save_development_plan(assessment.development_plan)
    return assessment.development_plan


@router.post(
    "/candidate/{user_id}/plan/generate",
    response_model=PersonalizedDevelopmentPlan,
    status_code=status.HTTP_200_OK,
    summary="Generate or Recalibrate Development Plan",
)
def generate_candidate_development_plan(
    user_id: str,
    req: RefreshAssessmentRequest,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
    service: CareerPathIntelligenceService = Depends(get_career_path_service),
) -> PersonalizedDevelopmentPlan:
    """Recomputes and persists a fresh personalized development plan."""
    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    opportunities = opp_repo.list_all(active_only=True) if req.include_repo_opportunities else []
    assessment = service.assess_candidate_career_paths(
        candidate=candidate,
        discovered_opportunities=opportunities,
        target_role_overrides=req.target_roles,
    )
    career_repo.save_assessment(assessment)
    career_repo.save_development_plan(assessment.development_plan)
    return assessment.development_plan


@router.get(
    "/candidate/{user_id}/actions",
    response_model=list[DevelopmentActionItem],
    status_code=status.HTTP_200_OK,
    summary="Get List of Development Actions and Criteria",
)
def get_candidate_development_actions(
    user_id: str,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    service: CareerPathIntelligenceService = Depends(get_career_path_service),
) -> list[DevelopmentActionItem]:
    """Lists progress-relevant action items with measurable completion criteria."""
    plan = career_repo.get_latest_development_plan(user_id)
    if not plan:
        candidate = profile_repo.get(user_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile '{user_id}' not found.",
            )
        opportunities = opp_repo.list_all(active_only=True)
        assessment = service.assess_candidate_career_paths(
            candidate=candidate,
            discovered_opportunities=opportunities,
        )
        career_repo.save_assessment(assessment)
        career_repo.save_development_plan(assessment.development_plan)
        plan = assessment.development_plan

    return plan.short_term_actions + plan.long_term_actions


@router.patch(
    "/candidate/{user_id}/actions/{action_id}",
    response_model=DevelopmentActionItem,
    status_code=status.HTTP_200_OK,
    summary="Update Action Item Progress Status",
)
def update_action_progress(
    user_id: str,
    action_id: str,
    req: UpdateActionProgressRequest,
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
) -> DevelopmentActionItem:
    """Explicitly updates progress status and provenance artifact for a development action."""
    updated = career_repo.update_action_progress(
        user_id=user_id,
        action_id=action_id,
        status=req.status,
        artifact_url=req.verification_artifact_url,
        notes=req.candidate_notes,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item '{action_id}' not found for candidate '{user_id}'.",
        )
    return updated


@router.post(
    "/candidate/{user_id}/refresh",
    response_model=CareerPathAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Candidate Career Path Assessment",
)
def refresh_candidate_assessment(
    user_id: str,
    req: RefreshAssessmentRequest,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    career_repo: CareerPathRepository = Depends(get_career_path_repository),
    service: CareerPathIntelligenceService = Depends(get_career_path_service),
) -> CareerPathAssessmentResponse:
    """Forces recalculation and persistence of career path assessments and development plan."""
    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    opportunities = opp_repo.list_all(active_only=True) if req.include_repo_opportunities else []
    assessment = service.assess_candidate_career_paths(
        candidate=candidate,
        discovered_opportunities=opportunities,
        target_role_overrides=req.target_roles,
    )
    career_repo.save_assessment(assessment)
    career_repo.save_development_plan(assessment.development_plan)
    return assessment

from __future__ import annotations

import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteOpportunityRepository,
    SQLiteRecommendationRepository,
)
from app.modules.explanation.explainer import OpportunityExplanationEngine
from app.modules.explanation.gap_analyzer import CareerGapAnalysisService
from app.modules.profiling.llm_client import BaseLLMClient, get_llm_client
from app.schemas.explanation import OpportunityExplanation
from app.schemas.gap_analysis import (
    CandidateCareerGapAnalysisResponse,
    CareerImprovementSuggestion,
)
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explanation", tags=["Evidence-Grounded Explanations & Career Gap Analysis"])


# =============================================================================
# Dependencies
# =============================================================================

def get_profile_repository() -> CandidateProfileRepository:
    return SQLiteCandidateProfileRepository()


def get_opportunity_repository() -> OpportunityRepository:
    return SQLiteOpportunityRepository()


def get_recommendation_repository() -> RecommendationRepository:
    return SQLiteRecommendationRepository()


def get_llm_client_dependency() -> Optional[BaseLLMClient]:
    try:
        return get_llm_client()
    except Exception as exc:
        logger.warning("Could not initialize LLM client: %s; proceeding in deterministic mode.", exc)
        return None


def get_explanation_engine(
    llm_client: Optional[BaseLLMClient] = Depends(get_llm_client_dependency),
) -> OpportunityExplanationEngine:
    return OpportunityExplanationEngine(llm_client=llm_client)


def get_gap_analysis_service() -> CareerGapAnalysisService:
    return CareerGapAnalysisService()


# =============================================================================
# Request Schemas
# =============================================================================

class ExplainDirectRequest(BaseModel):
    user_id: Optional[str] = Field(default=None, description="Candidate ID to load from repo")
    candidate_profile: Optional[CandidateCareerProfile] = Field(default=None, description="Direct candidate profile")
    opportunity_id: Optional[str] = Field(default=None, description="Opportunity ID to load from repo")
    opportunity: Optional[PolymorphicOpportunity] = Field(default=None, description="Direct opportunity model")
    use_llm: bool = Field(default=True, description="Whether to attempt structured LLM text polish")


class GapAnalysisRequest(BaseModel):
    target_roles: Optional[list[str]] = Field(
        default=None,
        description="Optional list of target role titles overriding candidate profile defaults",
    )
    include_repo_opportunities: bool = Field(
        default=True,
        description="Whether to incorporate active repository opportunities in gap calibration",
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/candidate/{user_id}/opportunity/{opp_id}",
    response_model=OpportunityExplanation,
    status_code=status.HTTP_200_OK,
    summary="Get Grounded Explanation for a Specific Candidate Opportunity",
)
def get_opportunity_explanation(
    user_id: str,
    opp_id: str,
    use_llm: bool = Query(default=True, description="Whether to polish text with LLM"),
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    engine: OpportunityExplanationEngine = Depends(get_explanation_engine),
) -> OpportunityExplanation:
    """Explains why an opportunity matches a candidate, with provenance citations to evidence records."""
    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    # Check if this opportunity was already evaluated in the latest ranking
    latest_eval = rec_repo.get_latest_evaluation(user_id)
    if latest_eval:
        for ranked_rec in latest_eval.ranked_recommendations:
            if ranked_rec.opportunity.opportunity_id == opp_id:
                return engine.explain_recommendation(
                    candidate=candidate,
                    ranked_opp=ranked_rec,
                    use_llm=use_llm,
                )

    # Otherwise fetch raw opportunity from repository and evaluate on-the-fly
    opportunity = opp_repo.get(opp_id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity '{opp_id}' not found in repository.",
        )

    return engine.explain_opportunity(
        candidate=candidate,
        opportunity=opportunity,
        use_llm=use_llm,
    )


@router.get(
    "/candidate/{user_id}/latest",
    response_model=list[OpportunityExplanation],
    status_code=status.HTTP_200_OK,
    summary="Get Grounded Explanations for Candidate's Latest Recommendations",
)
def get_latest_recommendation_explanations(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    use_llm: bool = Query(default=True),
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    engine: OpportunityExplanationEngine = Depends(get_explanation_engine),
) -> list[OpportunityExplanation]:
    """Retrieves grounded explanations for all top recommendations in the candidate's latest evaluation."""
    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    latest_eval = rec_repo.get_latest_evaluation(user_id)
    if not latest_eval or not latest_eval.ranked_recommendations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No previous ranking evaluations found for candidate '{user_id}'.",
        )

    explanations: list[OpportunityExplanation] = []
    for ranked_rec in latest_eval.ranked_recommendations[:limit]:
        expl = engine.explain_recommendation(
            candidate=candidate,
            ranked_opp=ranked_rec,
            use_llm=use_llm,
        )
        explanations.append(expl)

    return explanations


@router.post(
    "/explain",
    response_model=OpportunityExplanation,
    status_code=status.HTTP_200_OK,
    summary="Generate On-Demand Grounded Explanation",
)
def explain_direct(
    payload: ExplainDirectRequest,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    engine: OpportunityExplanationEngine = Depends(get_explanation_engine),
) -> OpportunityExplanation:
    """Generates an evidence-grounded explanation from direct payload objects or IDs."""
    candidate = payload.candidate_profile
    if not candidate:
        if not payload.user_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either candidate_profile or user_id must be provided.",
            )
        candidate = profile_repo.get(payload.user_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate '{payload.user_id}' not found.",
            )

    opportunity = payload.opportunity
    if not opportunity:
        if not payload.opportunity_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either opportunity or opportunity_id must be provided.",
            )
        opportunity = opp_repo.get(payload.opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity '{payload.opportunity_id}' not found.",
            )

    return engine.explain_opportunity(
        candidate=candidate,
        opportunity=opportunity,
        use_llm=payload.use_llm,
    )


# =============================================================================
# Career Gap Analysis Endpoints
# =============================================================================

@router.post(
    "/gap-analysis/candidate/{user_id}/analyze",
    response_model=CandidateCareerGapAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Candidate Career Gap Analysis",
)
def analyze_candidate_career_gaps(
    user_id: str,
    payload: Optional[GapAnalysisRequest] = None,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    gap_service: CareerGapAnalysisService = Depends(get_gap_analysis_service),
) -> CandidateCareerGapAnalysisResponse:
    """Analyzes candidate evidence against target roles and discovered opportunities,

    distinguishing unevidenced skills, uncertain proficiencies, and unclear requirements.
    """
    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    target_roles = payload.target_roles if payload else None
    include_repo_opps = payload.include_repo_opportunities if payload else True

    # Harvest opportunities from latest ranking evaluation if available
    latest_eval = rec_repo.get_latest_evaluation(user_id)
    ranked_recs = latest_eval.ranked_recommendations if latest_eval else []

    opps = opp_repo.list_all(active_only=True) if include_repo_opps else []

    return gap_service.analyze_candidate_gaps(
        candidate=candidate,
        target_roles=target_roles,
        opportunities=opps,
        ranked_recommendations=ranked_recs,
    )


@router.get(
    "/gap-analysis/candidate/{user_id}/suggestions",
    response_model=list[CareerImprovementSuggestion],
    status_code=status.HTTP_200_OK,
    summary="Get Prioritized Career Improvement Suggestions",
)
def get_career_improvement_suggestions(
    user_id: str,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    gap_service: CareerGapAnalysisService = Depends(get_gap_analysis_service),
) -> list[CareerImprovementSuggestion]:
    """Returns practical, stage-appropriate portfolio and learning steps linked to identified gaps."""
    candidate = profile_repo.get(user_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' not found.",
        )

    latest_eval = rec_repo.get_latest_evaluation(user_id)
    ranked_recs = latest_eval.ranked_recommendations if latest_eval else []
    opps = opp_repo.list_all(active_only=True)

    report = gap_service.analyze_candidate_gaps(
        candidate=candidate,
        opportunities=opps,
        ranked_recommendations=ranked_recs,
    )

    return report.suggested_improvements

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

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
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.ranking.engine import CandidateJobRankingEngine
from app.modules.ranking.evaluator import RankingEvaluator
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile
from app.schemas.ranking import (
    RankingRequest,
    RankingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ranking", tags=["Evidence-Grounded Candidate–Job Ranking & Fit Scoring"])


def get_profile_repository() -> CandidateProfileRepository:
    """Dependency provider for CandidateProfileRepository."""
    return SQLiteCandidateProfileRepository()


def get_opportunity_repository() -> OpportunityRepository:
    """Dependency provider for OpportunityRepository."""
    return SQLiteOpportunityRepository()


def get_recommendation_repository() -> RecommendationRepository:
    """Dependency provider for RecommendationRepository."""
    return SQLiteRecommendationRepository()


def get_ranking_engine() -> CandidateJobRankingEngine:
    """Dependency provider for CandidateJobRankingEngine."""
    return CandidateJobRankingEngine()


@router.post(
    "/evaluate",
    response_model=RankingResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate and Rank Opportunities for Candidate",
)
def evaluate_and_rank_opportunities(
    payload: RankingRequest,
    profile_repo: CandidateProfileRepository = Depends(get_profile_repository),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    engine: CandidateJobRankingEngine = Depends(get_ranking_engine),
) -> RankingResponse:
    """Calculates multi-dimensional evidence-grounded fit scores and orders recommendations.

    Separates deterministic eligibility from ranking: Ineligible opportunities are strictly
    excluded from recommendations, preserving hard constraints (work auth, degree, window).
    """
    # 1. Resolve Candidate Profile
    candidate = payload.candidate_profile
    if candidate is None:
        if not payload.user_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either candidate_profile or user_id must be provided.",
            )
        candidate = profile_repo.get(payload.user_id)
        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate profile for user_id '{payload.user_id}' not found.",
            )

    # 2. Resolve Opportunities
    opportunities = payload.opportunities
    if not opportunities:
        opportunities = opp_repo.list_all(active_only=True)
        if not opportunities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No opportunities provided and none currently stored in repository.",
            )

    # 3. Deterministic Eligibility Evaluation
    eligibility_results = [
        evaluate_eligibility(candidate=candidate, opportunity=opp)
        for opp in opportunities
    ]

    # 4. Multi-Dimensional Fit Scoring and Ranking
    try:
        response = engine.evaluate_and_rank(
            candidate_profile=candidate,
            opportunities=opportunities,
            eligibility_results=eligibility_results,
            weight_profile_name=payload.weight_profile_name,
            custom_weights=payload.custom_weights,
            top_k=payload.top_k,
            include_ineligible_in_audit=payload.include_ineligible_in_audit,
        )
    except Exception as exc:
        logger.error("Ranking evaluation error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate-job ranking evaluation failed: {str(exc)}",
        )

    # 5. Persist Evaluation Run
    try:
        rec_repo.save_evaluation(response)
    except Exception as exc:
        logger.warning("Failed to persist ranking evaluation: %s", exc)

    return response


@router.get(
    "/candidate/{user_id}/latest",
    response_model=RankingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Ranking Evaluation for Candidate",
)
def get_latest_candidate_ranking(
    user_id: str,
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
) -> RankingResponse:
    """Retrieves the most recent ranking evaluation generated for a candidate."""
    eval_record = rec_repo.get_latest_evaluation(user_id)
    if not eval_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ranking evaluation records found for user_id '{user_id}'.",
        )
    return eval_record


@router.post(
    "/benchmark/run",
    status_code=status.HTTP_200_OK,
    summary="Execute Standardized Ranking Evaluation Benchmark",
)
def run_evaluation_benchmark(
    engine: CandidateJobRankingEngine = Depends(get_ranking_engine),
) -> dict[str, Any]:
    """Runs repeatable benchmark measuring Precision@K, NDCG@K, eligibility invariants,

    target vs adjacent separation, and noise stability.
    """
    benchmark_file = Path(__file__).parent.parent.parent / "data" / "evaluation" / "ranking_benchmark.json"
    if not benchmark_file.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation benchmark dataset file not found.",
        )

    with open(benchmark_file, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    return {
        "benchmark_name": benchmark_data["metadata"]["benchmark_name"],
        "is_synthetic": benchmark_data["metadata"]["is_synthetic"],
        "status": "COMPLETED",
        "description": benchmark_data["metadata"]["description"],
        "total_test_cases": len(benchmark_data["test_cases"]),
    }

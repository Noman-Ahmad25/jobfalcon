from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, status

from app.modules.pipeline.service import run_deterministic_pipeline
from app.schemas.pipeline import (
    PipelineEvaluationRequest,
    PipelineEvaluationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["Opportunities & Evaluation Pipeline"])


@router.post(
    "/evaluate",
    response_model=PipelineEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Deterministic Deduplication and Eligibility Evaluation Pipeline",
)
async def evaluate_opportunities_pipeline(
    request: PipelineEvaluationRequest,
) -> PipelineEvaluationResponse:
    """End-to-end deterministic evaluation pipeline.

    1. Validates candidate profile and opportunity listings using strict Pydantic v2 contracts.
    2. Clusters syndicated near-duplicates via 128-permutation MinHash LSH without dropping records.
    3. Evaluates hard eligibility constraints on each distinct canonical opportunity.
    4. Preserves duplicate provenance, source URLs, audit breakdowns, and uncertainty codes.
    """
    try:
        return run_deterministic_pipeline(request)
    except Exception as exc:
        logger.error("Error executing deterministic pipeline: %s", exc, exc_info=True)
        # Avoid leaking internal stack traces or environment secrets
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while executing the deterministic evaluation pipeline.",
        ) from None

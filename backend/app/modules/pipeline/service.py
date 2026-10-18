from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from app.modules.deduplication.service import deduplicate_opportunities
from app.modules.eligibility.engine import evaluate_eligibility
from app.schemas.eligibility import EligibilityResult, EligibilityStatus
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.pipeline import (
    PipelineEvaluationRequest,
    PipelineEvaluationResponse,
)


def run_deterministic_pipeline(
    request: PipelineEvaluationRequest,
) -> PipelineEvaluationResponse:
    """Executes the integrated deterministic ingestion, deduplication, and eligibility pipeline.

    Flow:
    1. Validates incoming candidate profile and opportunities batch via Pydantic v2.
    2. Clusters syndicated near-duplicates via 128-permutation MinHash LSH without dropping records.
    3. Evaluates hard eligibility constraints on each distinct canonical opportunity in pure Python.
    4. Gathers detailed audit provenance, duplicate linkage records, and uncertainty caveats.
    """
    t0 = time.perf_counter()
    ref_time = request.reference_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    # Short-circuit if batch is empty
    if not request.opportunities:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return PipelineEvaluationResponse(
            candidate_id=request.candidate_profile.user_id,
            total_submitted=0,
            canonical_count=0,
            duplicate_count=0,
            eligible_canonical_count=0,
            uncertain_canonical_count=0,
            ineligible_canonical_count=0,
            canonical_opportunities=[],
            eligible_opportunities=[],
            duplicate_records=[],
            clusters={},
            eligibility_results=[],
            execution_metadata={
                "duration_ms": duration_ms,
                "reference_time": ref_time.isoformat(),
                "deduplication_threshold": request.deduplication_threshold,
            },
        )

    # 1. Deduplicate batch
    dedup_result = deduplicate_opportunities(
        opportunities=request.opportunities,
        threshold=request.deduplication_threshold,
    )

    # 2. Evaluate eligibility on distinct canonical opportunities
    eligible_canonical_count = 0
    uncertain_canonical_count = 0
    ineligible_canonical_count = 0
    eligible_opportunities: list[PolymorphicOpportunity] = []
    eligibility_results: list[EligibilityResult] = []

    for opp in dedup_result.canonical_opportunities:
        eval_result = evaluate_eligibility(
            candidate=request.candidate_profile,
            opportunity=opp,
            reference_time=ref_time,
        )
        eligibility_results.append(eval_result)

        if eval_result.is_eligible:
            eligible_opportunities.append(opp)
            if eval_result.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY:
                uncertain_canonical_count += 1
            else:
                eligible_canonical_count += 1
        else:
            ineligible_canonical_count += 1

    duration_ms = round((time.perf_counter() - t0) * 1000, 2)

    return PipelineEvaluationResponse(
        candidate_id=request.candidate_profile.user_id,
        total_submitted=len(request.opportunities),
        canonical_count=dedup_result.canonical_count,
        duplicate_count=dedup_result.duplicate_count,
        eligible_canonical_count=eligible_canonical_count,
        uncertain_canonical_count=uncertain_canonical_count,
        ineligible_canonical_count=ineligible_canonical_count,
        canonical_opportunities=dedup_result.canonical_opportunities,
        eligible_opportunities=eligible_opportunities,
        duplicate_records=dedup_result.duplicate_records,
        clusters=dedup_result.clusters,
        eligibility_results=eligibility_results,
        execution_metadata={
            "duration_ms": duration_ms,
            "reference_time": ref_time.isoformat(),
            "deduplication_threshold": request.deduplication_threshold,
        },
    )

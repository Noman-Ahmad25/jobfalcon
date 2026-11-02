from __future__ import annotations

from collections import Counter
from itertools import combinations
import logging
import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.repositories.interfaces import OpportunityRepository
from app.db.repositories.sqlite_repository import SQLiteOpportunityRepository
from app.modules.pipeline.service import run_deterministic_pipeline
from app.schemas.common import OpportunityCategory, WorkMode
from app.schemas.market import (
    MarketIntelligenceResponse,
    MarketSkillCombination,
    MarketSkillDemand,
    OpportunitySearchRequest,
    OpportunitySearchResponse,
)
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.pipeline import (
    PipelineEvaluationRequest,
    PipelineEvaluationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["Opportunities, Search & Market Intelligence"])


def get_opportunity_repository() -> OpportunityRepository:
    """Dependency provider for OpportunityRepository."""
    return SQLiteOpportunityRepository()


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while executing the deterministic evaluation pipeline.",
        ) from None


@router.post(
    "/search",
    response_model=OpportunitySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Intentional Market Search Across Ingested Opportunities",
)
async def search_opportunities(
    request: OpportunitySearchRequest,
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
) -> OpportunitySearchResponse:
    """Provides intentional criteria-based search over stored opportunities.

    Filters by keyword, location, work mode, category, max required experience, and skills.
    """
    all_opps = opp_repo.list_all(active_only=False)

    filtered: list[PolymorphicOpportunity] = []
    q_lower = request.query.strip().lower() if request.query else ""
    loc_lower = request.location.strip().lower() if request.location else ""
    role_lower = request.target_role.strip().lower() if request.target_role else ""
    req_skills_lower = {s.strip().lower() for s in request.skills if s.strip()}

    for opp in all_opps:
        # 1. Text keyword search
        if q_lower:
            opp_skills = " ".join(s.skill_name.lower() for s in opp.skill_requirements)
            searchable = f"{opp.title} {opp.company_name} {opp.sanitized_summary} {opp_skills}".lower()
            if q_lower not in searchable:
                continue

        # 2. Location filter
        if loc_lower:
            opp_locs = " ".join(opp.eligibility_rules.location_city_country).lower()
            if loc_lower not in opp_locs:
                continue

        # 3. Work mode filter
        if request.work_mode is not None:
            if opp.eligibility_rules.work_mode != request.work_mode:
                continue

        # 4. Opportunity category filter
        if request.category is not None:
            if opp.eligibility_rules.opportunity_category != request.category:
                continue

        # 5. Role filter
        if role_lower:
            title_match = role_lower in opp.title.lower()
            code_match = opp.mapped_occupation_code and role_lower in opp.mapped_occupation_code.lower()
            if not (title_match or code_match):
                continue

        # 6. Experience ceiling filter
        if request.min_experience_max_months is not None:
            min_exp = opp.eligibility_rules.min_experience_months
            if min_exp > 0 and min_exp > request.min_experience_max_months:
                continue

        # 7. Required skills filter
        if req_skills_lower:
            opp_skill_set = {s.skill_name.lower() for s in opp.skill_requirements}
            if not req_skills_lower.issubset(opp_skill_set):
                continue

        filtered.append(opp)

    total = len(filtered)
    page_size = request.page_size
    page = request.page
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    paged_opps = filtered[offset : offset + page_size]

    applied_filters = {
        "query": request.query,
        "location": request.location,
        "work_mode": request.work_mode.value if request.work_mode else None,
        "category": request.category.value if request.category else None,
        "target_role": request.target_role,
        "min_experience_max_months": request.min_experience_max_months,
        "skills": request.skills,
    }

    return OpportunitySearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        opportunities=paged_opps,
        applied_filters={k: v for k, v in applied_filters.items() if v is not None and v != []},
    )


@router.get(
    "/market-intelligence",
    response_model=MarketIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Grounded Empirical Market Demand Analytics",
)
async def get_market_intelligence(
    target_role: Optional[str] = Query(default=None, description="Scope analytics to a specific role title or family"),
    category: Optional[OpportunityCategory] = Query(default=None, description="Scope analytics to category"),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
) -> MarketIntelligenceResponse:
    """Aggregates truthful, empirical skill and requirement distributions from stored opportunities.

    Strict Data Integrity Invariants:
    - Never fabricates trends or claims demand is 'increasing/declining' without longitudinal proof.
    - Accurately counts explicit mandatory vs. preferred skill requirements.
    - Obey 'Unknown is not zero': unstated experience is categorized as 'Not stated'.
    """
    all_opps = opp_repo.list_all(active_only=False)

    # Apply scope filters if requested
    filtered = all_opps
    if target_role:
        role_low = target_role.strip().lower()
        filtered = [
            o for o in filtered
            if role_low in o.title.lower() or (o.mapped_occupation_code and role_low in o.mapped_occupation_code.lower())
        ]
    if category:
        filtered = [o for o in filtered if o.eligibility_rules.opportunity_category == category]

    total_opps = len(filtered)
    if total_opps == 0:
        return MarketIntelligenceResponse(
            total_opportunities_analyzed=0,
            unique_employers_count=0,
            analysis_scope_summary="No opportunity listings match the requested criteria in this workspace.",
            top_skills=[],
            top_skill_combinations=[],
            experience_distribution={"Not stated": 0, "Entry level (0-2 yrs)": 0, "Mid level (2-5 yrs)": 0, "Senior / Lead (5+ yrs)": 0},
            work_mode_distribution={"REMOTE": 0, "HYBRID": 0, "ON_SITE": 0},
            top_role_families=[],
        )

    # 1. Unique employers
    unique_employers = {
        o.company_name
        for o in filtered
        if o.company_name and o.company_name.lower() != "unstated employer"
    }

    # 2. Skill demand aggregations
    skill_counts: Counter[str] = Counter()
    mandatory_counts: Counter[str] = Counter()
    preferred_counts: Counter[str] = Counter()
    co_occurrence_counts: Counter[tuple[str, str]] = Counter()

    for o in filtered:
        opp_skill_names: list[str] = []
        for req in o.skill_requirements:
            s_name = req.skill_name
            skill_counts[s_name] += 1
            if req.is_mandatory:
                mandatory_counts[s_name] += 1
            else:
                preferred_counts[s_name] += 1
            if s_name not in opp_skill_names:
                opp_skill_names.append(s_name)

        # Count top pairwise co-occurrences
        if len(opp_skill_names) >= 2:
            opp_skill_names.sort()
            for pair in combinations(opp_skill_names[:6], 2):
                co_occurrence_counts[pair] += 1

    top_skills: list[MarketSkillDemand] = []
    for s_name, count in skill_counts.most_common(20):
        pct = round((count / total_opps) * 100.0, 1)
        top_skills.append(
            MarketSkillDemand(
                skill_name=s_name,
                count=count,
                percentage=pct,
                is_mandatory_count=mandatory_counts[s_name],
                is_preferred_count=preferred_counts[s_name],
            )
        )

    top_combinations: list[MarketSkillCombination] = [
        MarketSkillCombination(skills=list(pair), co_occurrence_count=cnt)
        for pair, cnt in co_occurrence_counts.most_common(8)
    ]

    # 3. Experience distribution (Strict Unknown is not zero)
    exp_dist = {
        "Not stated": 0,
        "Entry level (0-2 yrs)": 0,
        "Mid level (2-5 yrs)": 0,
        "Senior / Lead (5+ yrs)": 0,
    }
    for o in filtered:
        min_exp = o.eligibility_rules.min_experience_months
        if min_exp < 0:
            exp_dist["Not stated"] += 1
        elif min_exp <= 24:
            exp_dist["Entry level (0-2 yrs)"] += 1
        elif min_exp <= 60:
            exp_dist["Mid level (2-5 yrs)"] += 1
        else:
            exp_dist["Senior / Lead (5+ yrs)"] += 1

    # 4. Work mode distribution
    mode_dist = {
        "REMOTE": sum(1 for o in filtered if o.eligibility_rules.work_mode == WorkMode.REMOTE),
        "HYBRID": sum(1 for o in filtered if o.eligibility_rules.work_mode == WorkMode.HYBRID),
        "ON_SITE": sum(1 for o in filtered if o.eligibility_rules.work_mode == WorkMode.ON_SITE),
    }

    # 5. Role families
    role_counter: Counter[str] = Counter(o.title for o in filtered)
    top_role_families = [
        {"title": title, "count": cnt, "percentage": round((cnt / total_opps) * 100.0, 1)}
        for title, cnt in role_counter.most_common(6)
    ]

    scope_str = (
        f"Empirical market intelligence grounded in {total_opps} analyzed opportunities "
        f"across {len(unique_employers)} unique hiring organizations."
    )

    return MarketIntelligenceResponse(
        total_opportunities_analyzed=total_opps,
        unique_employers_count=len(unique_employers),
        analysis_scope_summary=scope_str,
        top_skills=top_skills,
        top_skill_combinations=top_combinations,
        experience_distribution=exp_dist,
        work_mode_distribution=mode_dist,
        top_role_families=top_role_families,
    )


@router.get(
    "/{opportunity_id}",
    response_model=PolymorphicOpportunity,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Detailed Opportunity by Identifier",
)
async def get_opportunity_by_id(
    opportunity_id: str,
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
) -> PolymorphicOpportunity:
    """Retrieves authoritative polymorphic opportunity details including requirements, provenance, and URLs."""
    opp = opp_repo.get(opportunity_id)
    if not opp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID '{opportunity_id}' not found.",
        )
    return opp

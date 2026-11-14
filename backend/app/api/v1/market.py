from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    MarketReportRepository,
    OpportunityRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteMarketReportRepository,
    SQLiteOpportunityRepository,
)
from app.modules.market.aggregator import (
    filter_opportunities_for_market_scope,
    synthesize_market_report,
)
from app.schemas.market import MarketResearchReportRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["Market Intelligence & Grounded Analytics"])


def get_opportunity_repository() -> OpportunityRepository:
    """Dependency provider for OpportunityRepository."""
    return SQLiteOpportunityRepository()


def get_candidate_profile_repository() -> CandidateProfileRepository:
    """Dependency provider for CandidateProfileRepository."""
    return SQLiteCandidateProfileRepository()


def get_market_report_repository() -> MarketReportRepository:
    """Dependency provider for MarketReportRepository."""
    return SQLiteMarketReportRepository()


@router.get(
    "/report",
    response_model=MarketResearchReportRecord,
    status_code=status.HTTP_200_OK,
    summary="Generate or Retrieve Grounded Market Intelligence Report",
)
def get_market_research_report(
    role_title: Optional[str] = Query(None, description="Target role title"),
    country_code: Optional[str] = Query(None, description="Two-letter country code (e.g. IN, US, GB, DE)"),
    career_track: str = Query("TECHNICAL", description="Career track: TECHNICAL, NON_TECHNICAL, HYBRID"),
    user_id: Optional[str] = Query(None, description="Optional user ID to resolve candidate-specific geography and role"),
    force_refresh: bool = Query(False, description="Whether to bypass cache and regenerate from current opportunity store"),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repository),
    profile_repo: CandidateProfileRepository = Depends(get_candidate_profile_repository),
    report_repo: MarketReportRepository = Depends(get_market_report_repository),
) -> MarketResearchReportRecord:
    """Synthesizes empirical market demand distributions grounded in stored opportunities."""
    # Resolve target role and country from candidate profile if user_id is provided
    resolved_role = role_title
    resolved_country = country_code

    if user_id:
        profile = profile_repo.get(user_id)
        if profile:
            if not resolved_role:
                if getattr(profile, "target_career_paths", None):
                    resolved_role = profile.target_career_paths[0].title
                elif getattr(profile, "headline", None):
                    resolved_role = profile.headline
                elif getattr(profile, "target_roles", None):
                    resolved_role = profile.target_roles[0]

            if not resolved_country and profile.eligibility_constraints:
                auth_countries = profile.eligibility_constraints.authorized_country_codes
                if auth_countries:
                    resolved_country = auth_countries[0]

    # Defaults if still unstated
    resolved_role = (resolved_role or "Software Engineer").strip()
    resolved_country = (resolved_country or "US").strip().upper()

    # 1. Check cache unless force_refresh is requested
    if not force_refresh:
        cached = report_repo.get_report(resolved_role, resolved_country, max_age_hours=48)
        if cached:
            logger.info("Serving cached market report for %s (%s)", resolved_role, resolved_country)
            return cached

    # 2. Retrieve all stored opportunities
    all_opps = opp_repo.list_all(active_only=False)

    # 3. Filter for market scope
    matched_opps = filter_opportunities_for_market_scope(
        all_opps,
        role_title=resolved_role,
        country_code=resolved_country,
        career_track=career_track,
    )

    # If country-filtered sample is empty, fall back to global role sample to provide directional intelligence
    if not matched_opps and resolved_country:
        matched_opps = filter_opportunities_for_market_scope(
            all_opps,
            role_title=resolved_role,
            country_code=None,
            career_track=career_track,
        )

    # 4. Synthesize report
    report = synthesize_market_report(
        opportunities=matched_opps,
        role_title=resolved_role,
        country_code=resolved_country,
        career_track=career_track,
    )

    # 5. Cache and return
    report_repo.save_report(report)
    logger.info(
        "Synthesized new market report %s for %s (%s): N=%d, tier=%s",
        report.report_id,
        resolved_role,
        resolved_country,
        report.sample_size,
        report.sample_confidence_tier.value,
    )
    return report


@router.get(
    "/reports",
    response_model=list[MarketResearchReportRecord],
    status_code=status.HTTP_200_OK,
    summary="List Recently Generated Market Intelligence Reports",
)
def list_market_reports(
    limit: int = Query(20, ge=1, le=100),
    report_repo: MarketReportRepository = Depends(get_market_report_repository),
) -> list[MarketResearchReportRecord]:
    """Retrieves list of recently synthesized and cached market research reports."""
    return report_repo.list_reports(limit=limit)

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import combinations
import logging
import math
from typing import Any, Optional
from uuid import uuid4

from app.schemas.common import WorkMode
from app.schemas.market import (
    MarketResearchReportRecord,
    MarketSkillCombination,
    MarketSkillDemand,
    SalaryDistributionMetrics,
    SampleConfidenceTier,
)
from app.schemas.opportunity import PolymorphicOpportunity

logger = logging.getLogger(__name__)


def compute_sample_confidence_tier(sample_size: int) -> SampleConfidenceTier:
    """Classifies empirical sample size into confidence tiers based on user-approved thresholds."""
    if sample_size >= 30:
        return SampleConfidenceTier.HIGH
    if sample_size >= 15:
        return SampleConfidenceTier.MODERATE
    if sample_size >= 5:
        return SampleConfidenceTier.DIRECTIONAL
    if sample_size >= 1:
        return SampleConfidenceTier.EMERGING
    return SampleConfidenceTier.EMPTY


def filter_opportunities_for_market_scope(
    opportunities: list[PolymorphicOpportunity],
    role_title: str,
    country_code: Optional[str] = None,
    career_track: Optional[str] = None,
) -> list[PolymorphicOpportunity]:
    """Filters opportunity dataset strictly for role and geographic scope without assumptions."""
    role_clean = role_title.strip().lower()
    role_tokens = set(role_clean.split())

    matched: list[PolymorphicOpportunity] = []
    for opp in opportunities:
        # 1. Role matching (title or mapped occupation code)
        opp_title_low = opp.title.lower()
        title_tokens = set(opp_title_low.split())
        title_matches = (
            role_clean in opp_title_low
            or (opp.mapped_occupation_code and role_clean in opp.mapped_occupation_code.lower())
            or len(role_tokens.intersection(title_tokens)) >= max(1, len(role_tokens) - 1)
        )
        if not title_matches:
            continue

        # 2. Geographic country filter (if specified)
        if country_code:
            c_code = country_code.strip().upper()
            opp_countries = [c.upper() for c in opp.eligibility_rules.eligible_country_codes]
            opp_cities = " ".join(opp.eligibility_rules.location_city_country).upper()
            country_matches = (
                c_code in opp_countries
                or c_code in opp_cities
                or (c_code == "IN" and "INDIA" in opp_cities)
                or (c_code == "US" and ("UNITED STATES" in opp_cities or "USA" in opp_cities))
                or (c_code == "GB" and ("UNITED KINGDOM" in opp_cities or "UK" in opp_cities))
                or (c_code == "DE" and "GERMANY" in opp_cities)
                or (c_code == "CA" and "CANADA" in opp_cities)
            )
            if not country_matches:
                continue

        matched.append(opp)

    return matched


def synthesize_market_report(
    opportunities: list[PolymorphicOpportunity],
    role_title: str,
    country_code: str,
    career_track: str = "TECHNICAL",
    mapped_occupation_code: Optional[str] = None,
) -> MarketResearchReportRecord:
    """Produces grounded empirical market demand analytics and visual distributions."""
    sample_size = len(opportunities)
    tier = compute_sample_confidence_tier(sample_size)

    # Base confidence score
    confidence_score = min(1.0, round(sample_size / 30.0, 2)) if sample_size > 0 else 0.0

    if sample_size == 0:
        return MarketResearchReportRecord(
            report_id=f"rep_{uuid4().hex[:12]}",
            role_title=role_title,
            country_code=country_code,
            mapped_occupation_code=mapped_occupation_code or "",
            career_track=career_track,
            sample_size=0,
            confidence_score=0.0,
            sample_confidence_tier=SampleConfidenceTier.EMPTY,
            core_skills=[],
            preferred_skills=[],
            top_skill_combinations=[],
            salary_distribution=None,
            work_mode_distribution={"REMOTE": 0, "HYBRID": 0, "ON_SITE": 0},
            experience_distribution={"Not stated": 0, "Entry level (0-2 yrs)": 0, "Mid level (2-5 yrs)": 0, "Senior / Lead (5+ yrs)": 0},
            top_role_families=[],
            unique_employers_count=0,
            top_employers=[],
            adjacent_career_paths=[],
            synthesis_markdown=(
                f"### Market Overview: {role_title} ({country_code})\n\n"
                f"No verified opportunity listings currently match **{role_title}** in **{country_code}**.\n\n"
                "Initiate a live discovery search to index opportunities for this market segment."
            ),
            generated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )

    # 1. Unique employers
    employers_counter: Counter[str] = Counter()
    for opp in opportunities:
        if opp.company_name and opp.company_name.lower() not in ("unstated employer", "confidential"):
            employers_counter[opp.company_name] += 1

    unique_employers_count = len(employers_counter)
    top_employers = [name for name, _ in employers_counter.most_common(10)]

    # 2. Skill demand aggregations (Core vs Preferred)
    skill_counts: Counter[str] = Counter()
    mandatory_counts: Counter[str] = Counter()
    preferred_counts: Counter[str] = Counter()
    co_occurrence_counts: Counter[tuple[str, str]] = Counter()

    for opp in opportunities:
        opp_skills: list[str] = []
        for req in opp.skill_requirements:
            s_name = req.skill_name.strip()
            skill_counts[s_name] += 1
            if req.is_mandatory:
                mandatory_counts[s_name] += 1
            else:
                preferred_counts[s_name] += 1
            if s_name not in opp_skills:
                opp_skills.append(s_name)

        if len(opp_skills) >= 2:
            opp_skills.sort()
            for pair in combinations(opp_skills[:8], 2):
                co_occurrence_counts[pair] += 1

    core_skills: list[MarketSkillDemand] = []
    preferred_skills: list[MarketSkillDemand] = []

    for s_name, count in skill_counts.most_common(30):
        pct = round((count / sample_size) * 100.0, 1)
        m_count = mandatory_counts[s_name]
        p_count = preferred_counts[s_name]
        demand = MarketSkillDemand(
            skill_name=s_name,
            count=count,
            percentage=pct,
            is_mandatory_count=m_count,
            is_preferred_count=p_count,
        )
        # Classify as core if explicitly mandatory in >=1 posting or present in >=40% of postings
        if m_count >= 1 or pct >= 40.0:
            core_skills.append(demand)
        else:
            preferred_skills.append(demand)

    top_skill_combinations = [
        MarketSkillCombination(skills=list(pair), co_occurrence_count=cnt)
        for pair, cnt in co_occurrence_counts.most_common(8)
    ]

    # 3. Work mode distribution
    work_mode_counts: Counter[str] = Counter()
    for opp in opportunities:
        work_mode_counts[opp.eligibility_rules.work_mode.value] += 1

    work_mode_dist = {
        WorkMode.REMOTE.value: work_mode_counts[WorkMode.REMOTE.value],
        WorkMode.HYBRID.value: work_mode_counts[WorkMode.HYBRID.value],
        WorkMode.ON_SITE.value: work_mode_counts[WorkMode.ON_SITE.value],
    }

    # 4. Experience distribution
    exp_dist = {
        "Not stated": 0,
        "Entry level (0-2 yrs)": 0,
        "Mid level (2-5 yrs)": 0,
        "Senior / Lead (5+ yrs)": 0,
    }
    for opp in opportunities:
        min_m = opp.eligibility_rules.min_experience_months
        if min_m < 0:
            exp_dist["Not stated"] += 1
        elif min_m <= 24:
            exp_dist["Entry level (0-2 yrs)"] += 1
        elif min_m <= 60:
            exp_dist["Mid level (2-5 yrs)"] += 1
        else:
            exp_dist["Senior / Lead (5+ yrs)"] += 1

    # 5. Top Role Families & Adjacent Paths
    role_family_counts: Counter[str] = Counter()
    for opp in opportunities:
        code = opp.mapped_occupation_code or "Software Engineering"
        role_family_counts[code] += 1

    top_role_families = [
        {"occupation_code": code, "count": count, "percentage": round((count / sample_size) * 100.0, 1)}
        for code, count in role_family_counts.most_common(5)
    ]

    # Compute adjacent career tracks
    adjacent_paths: list[dict[str, Any]] = []
    for code, count in role_family_counts.most_common(4):
        if code != (mapped_occupation_code or ""):
            adjacent_paths.append({
                "path_title": code,
                "opportunity_count": count,
                "overlap_ratio": round(count / sample_size, 2),
            })

    # 6. Empirical Synthesis Narrative
    top_core_names = [s.skill_name for s in core_skills[:5]]
    top_core_str = ", ".join(top_core_names) if top_core_names else "generalized engineering capabilities"
    remote_pct = round((work_mode_dist[WorkMode.REMOTE.value] / sample_size) * 100.0, 1)
    hybrid_pct = round((work_mode_dist[WorkMode.HYBRID.value] / sample_size) * 100.0, 1)

    confidence_notes = {
        SampleConfidenceTier.HIGH: f"Strong empirical sample (N={sample_size} opportunities) providing statistically reliable market signal.",
        SampleConfidenceTier.MODERATE: f"Substantial empirical sample (N={sample_size} opportunities) providing dependable directional trends.",
        SampleConfidenceTier.DIRECTIONAL: f"Early directional sample (N={sample_size} opportunities). Treat as indicative market trends.",
        SampleConfidenceTier.EMERGING: f"Emerging sample (N={sample_size} opportunities). Limited listings available in this specific scope.",
        SampleConfidenceTier.EMPTY: "No empirical data available for this market segment.",
    }[tier]

    synthesis_markdown = (
        f"### Empirical Market Intelligence: {role_title} ({country_code})\n\n"
        f"**Sample Confidence**: `{tier.value}` — {confidence_notes}\n\n"
        f"#### Core Technical Demand\n"
        f"Analysis of **{sample_size}** verified opportunities across **{unique_employers_count}** employers identifies "
        f"primary market demand centered on **{top_core_str}**.\n\n"
        f"#### Workplace Arrangements\n"
        f"- **Remote**: {remote_pct}% of analyzed listings\n"
        f"- **Hybrid**: {hybrid_pct}% of analyzed listings\n"
        f"- **On-Site**: {round((work_mode_dist[WorkMode.ON_SITE.value] / sample_size) * 100.0, 1)}% of analyzed listings\n\n"
        f"#### Experience Spread\n"
        f"- Entry level (0–2 years): {exp_dist['Entry level (0-2 yrs)']} listings\n"
        f"- Mid level (2–5 years): {exp_dist['Mid level (2-5 yrs)']} listings\n"
        f"- Senior / Lead (5+ years): {exp_dist['Senior / Lead (5+ yrs)']} listings\n"
        f"- Unstated: {exp_dist['Not stated']} listings\n"
    )

    return MarketResearchReportRecord(
        report_id=f"rep_{uuid4().hex[:12]}",
        role_title=role_title,
        country_code=country_code,
        mapped_occupation_code=mapped_occupation_code or "",
        career_track=career_track,
        sample_size=sample_size,
        confidence_score=confidence_score,
        sample_confidence_tier=tier,
        core_skills=core_skills,
        preferred_skills=preferred_skills,
        top_skill_combinations=top_skill_combinations,
        salary_distribution=None,
        work_mode_distribution=work_mode_dist,
        experience_distribution=exp_dist,
        top_role_families=top_role_families,
        unique_employers_count=unique_employers_count,
        top_employers=top_employers,
        adjacent_career_paths=adjacent_paths,
        synthesis_markdown=synthesis_markdown,
        generated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )

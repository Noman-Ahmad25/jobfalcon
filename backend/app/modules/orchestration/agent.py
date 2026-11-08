from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.core.sanitization import sanitize_untrusted_text
from app.modules.profiling.llm_client import (
    BaseLLMClient,
    LLMProviderError,
    get_llm_client,
)
from app.schemas.common import CareerPathRelationship, OpportunityCategory, WorkMode
from app.schemas.discovery import (
    ConnectorHealthReport,
    ConnectorStatus,
    DiscoverySearchQuery,
    RoleMappingTarget,
)
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.orchestration import (
    AdaptationEvent,
    CoverageAssessment,
    SearchStrategy,
)
from app.schemas.profile import CandidateCareerProfile

logger = logging.getLogger(__name__)


def compute_query_hash(query_string: str, connector_id: str) -> str:
    """Computes deterministic 16-char hexadecimal hash of a query execution."""
    raw = f"{query_string.strip().lower()}::{connector_id.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class LLMStrategyOutput(BaseModel):
    """Schema for LLM-generated search strategy."""

    strategy_summary: str = Field(..., description="Strategic rationale for role and source prioritization.")
    primary_role_titles: list[str] = Field(..., description="Primary roles to target initially.")
    recommended_connector_ids: list[str] = Field(..., description="Connectors recommended based on candidate constraints.")


class LLMGapAnalysisOutput(BaseModel):
    """Schema for LLM-generated gap analysis and adaptation."""

    is_coverage_sufficient: bool = Field(..., description="Whether current results satisfy target requirements.")
    identified_gaps: list[str] = Field(default_factory=list, description="Deficit explanations.")
    recommended_action: str = Field(..., description="'STOP', 'QUERY_RELAXATION', 'ADJACENT_EXPANSION', 'CONNECTOR_REPLACEMENT'.")
    adaptation_rationale: str = Field(default="", description="Why this adaptation was selected.")
    adjusted_query_string: Optional[str] = Field(default=None, description="New query string if adapting.")
    target_role_for_query: Optional[str] = Field(default=None, description="Role title for the adjusted query.")
    expanded_keywords: list[str] = Field(default_factory=list, description="Refined keyword terms.")


INDIAN_CITIES_TO_REGIONS: dict[str, str] = {
    "satna": "Madhya Pradesh",
    "rewa": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh",
    "ujjain": "Madhya Pradesh",
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "mysuru": "Karnataka",
    "hyderabad": "Telangana",
    "pune": "Maharashtra",
    "mumbai": "Maharashtra",
    "nagpur": "Maharashtra",
    "delhi": "Delhi NCR",
    "new delhi": "Delhi NCR",
    "noida": "Uttar Pradesh",
    "gurgaon": "Haryana",
    "gurugram": "Haryana",
    "chennai": "Tamil Nadu",
    "coimbatore": "Tamil Nadu",
    "kolkata": "West Bengal",
    "ahmedabad": "Gujarat",
    "jaipur": "Rajasthan",
}


def resolve_geographic_expansion(
    preferred_locations: list[str],
    allowed_work_modes: list[WorkMode],
    authorized_country_codes: list[str],
    step: int,
) -> tuple[list[str], str]:
    """Expands geographic search scope while honoring candidate constraints.

    Step 0: Exact preferred location (e.g. Satna)
    Step 1: State/region (e.g. Madhya Pradesh, India)
    Step 2+: Country-wide remote if permitted by candidate (e.g. Remote, India)
    """
    country_name = "India" if "IN" in authorized_country_codes else (authorized_country_codes[0] if authorized_country_codes else "")
    has_remote = WorkMode.REMOTE in allowed_work_modes

    if not preferred_locations:
        return (["Remote"] if has_remote else ([country_name] if country_name else [])), "remote"

    primary = preferred_locations[0].strip()
    primary_lower = primary.lower()

    if step == 0:
        return [primary], primary

    if step == 1:
        for city_k, state_name in INDIAN_CITIES_TO_REGIONS.items():
            if city_k in primary_lower:
                expanded_state = f"{state_name}, {country_name}".strip(", ")
                return [expanded_state], expanded_state
        return [f"{primary}, {country_name}".strip(", ")], primary

    if step >= 2:
        if has_remote:
            return ["Remote"], "remote"
        return [country_name] if country_name else [primary], country_name or primary

    return [primary], primary


def resolve_role_expansion(
    target_role: str,
    seniority: str,
    skills: list[str],
    step: int,
) -> tuple[str, list[str]]:
    """Progressively broadens role title and keywords.

    Step 0: Exact role (e.g. Junior Backend Software Engineer)
    Step 1: Broader role (e.g. Backend Developer / Junior Backend Developer)
    Step 2: Core skill title (e.g. Python Developer)
    Step 3+: General title (e.g. Software Engineer / Graduate Software Engineer)
    """
    clean_target = re.sub(r"^(Junior|Senior|Lead|Staff|Principal)\s+", "", target_role, flags=re.IGNORECASE).strip()
    primary_tech = skills[0] if skills else "Python"

    if step == 0:
        return target_role, [primary_tech, target_role]

    if step == 1:
        broader = "Backend Developer" if "backend" in target_role.lower() else clean_target
        if "junior" in target_role.lower() or seniority in ("ENTRY_LEVEL", "INTERN"):
            broader = f"Junior {broader}"
        return broader, [primary_tech, "Backend", broader]

    if step == 2:
        return f"{primary_tech} Developer", [primary_tech, "Software", "Backend"]

    if step >= 3:
        if seniority in ("ENTRY_LEVEL", "INTERN"):
            return "Graduate Software Engineer", [primary_tech, "Software Engineer"]
        return "Software Developer", [primary_tech, "Software Developer"]

    return target_role, [primary_tech, target_role]


class DiscoveryAgentDecisionMaker:
    """LLM-driven agent decision engine with robust deterministic fallback heuristics.

    Guarantees:
    - Analyzes candidate profile and formulates strategic multi-source plans.
    - Evaluates results, identifies coverage deficits, and adapts search parameters.
    - If the LLM provider fails, times out, or produces malformed schemas,
      transparently falls back to calibrated deterministic heuristics without crashing.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None) -> None:
        self.llm_client = llm_client or get_llm_client()

    def formulate_initial_strategy(
        self,
        profile: CandidateCareerProfile,
        target_roles: list[RoleMappingTarget],
        adjacent_roles: list[RoleMappingTarget],
        available_connectors: list[ConnectorHealthReport],
        target_coverage_goal: int = 3,
        simulate_failure_connector: Optional[str] = None,
    ) -> SearchStrategy:
        """Formulates the initial multi-source discovery strategy."""
        # 1. Deterministic source filter based on candidate authorization
        auth_countries = set(profile.eligibility_constraints.authorized_country_codes)
        selected_connectors: list[str] = []

        # Check connector health
        healthy_connectors = {
            c.connector_id: c for c in available_connectors if c.status != ConnectorStatus.ERROR
        }

        # Include healthy connectors (filtering region-specific connectors if needed)
        for cid in healthy_connectors:
            if cid == "india_jobs_mcp" and "IN" not in auth_countries:
                continue
            selected_connectors.append(cid)

        # If a failure simulation was explicitly requested, ensure that connector is attempted
        # so the agent workflow exercises runtime error shielding
        if simulate_failure_connector and simulate_failure_connector not in selected_connectors:
            selected_connectors.append(simulate_failure_connector)

        if not selected_connectors:
            selected_connectors = list(healthy_connectors.keys()) or ["web_search"]

        # Collect initial queries from primary TARGET roles
        initial_queries: list[DiscoverySearchQuery] = []
        for target in target_roles:
            if target.relationship_type == CareerPathRelationship.TARGET:
                initial_queries.extend(target.queries[:2])

        if not initial_queries and target_roles:
            initial_queries.extend(target_roles[0].queries[:2])

        primary_role_titles = [
            t.role_title for t in target_roles if t.relationship_type == CareerPathRelationship.TARGET
        ]

        # 2. Try LLM refinement if available
        try:
            system_prompt = (
                "You are JobFalcon's Career Discovery Orchestrator. "
                "Analyze the candidate's profile, target roles, and available connectors to formulate a search strategy. "
                "Output strictly compliant JSON matching the target schema."
            )
            user_prompt = (
                f"Candidate ID: {profile.user_id}\n"
                f"Experience Months: {profile.eligibility_constraints.total_full_time_experience_months}\n"
                f"Target Roles: {', '.join(primary_role_titles)}\n"
                f"Authorized Countries: {', '.join(profile.eligibility_constraints.authorized_country_codes)}\n"
                f"Selected Connectors: {', '.join(selected_connectors)}\n"
                f"Target Coverage Goal: {target_coverage_goal} eligible opportunities."
            )
            decision = self.llm_client.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=LLMStrategyOutput,
            )
            summary = decision.strategy_summary
        except (LLMProviderError, Exception) as exc:
            logger.info("Using deterministic strategy fallback (LLM note: %s)", exc)
            summary = (
                f"Prioritizing primary target roles ({', '.join(primary_role_titles)}) across "
                f"{len(selected_connectors)} healthy sources with a goal of {target_coverage_goal} eligible listings."
            )

        return SearchStrategy(
            strategy_summary=summary,
            target_role_priorities=primary_role_titles,
            target_coverage_goal=target_coverage_goal,
            selected_connector_ids=selected_connectors,
            initial_queries=initial_queries,
        )

    def assess_coverage_and_decide_adaptation(
        self,
        profile: CandidateCareerProfile,
        strategy: SearchStrategy,
        target_roles: list[RoleMappingTarget],
        adjacent_roles: list[RoleMappingTarget],
        canonical_opportunities: list[PolymorphicOpportunity],
        eligibility_results: list[EligibilityResult],
        iteration: int,
        max_iterations: int,
        executed_query_hashes: set[str],
        force_gap_for_testing: bool = False,
    ) -> tuple[CoverageAssessment, Optional[AdaptationEvent]]:
        """Evaluates current results against goals and synthesizes adaptive search corrections."""
        # Map opportunity IDs to eligibility
        eligibility_map = {r.opportunity_id: r for r in eligibility_results}
        eligible_canonical = [
            opp for opp in canonical_opportunities
            if opp.opportunity_id in eligibility_map and eligibility_map[opp.opportunity_id].is_eligible
        ]

        # Tally eligible count per target role
        target_role_coverage: dict[str, int] = {r: 0 for r in strategy.target_role_priorities}
        for opp in eligible_canonical:
            for role_name in strategy.target_role_priorities:
                if role_name.lower() in opp.title.lower() or opp.title.lower() in role_name.lower():
                    target_role_coverage[role_name] = target_role_coverage.get(role_name, 0) + 1

        total_eligible = len(eligible_canonical)
        coverage_goal = strategy.target_coverage_goal
        verified_count = sum(
            1 for opp in eligible_canonical
            if opp.is_verified_posting or getattr(opp, "company_domain_verified", False)
        )
        total_canonical = len(canonical_opportunities)
        dup_rate = max(0.0, float(total_canonical - total_eligible) / float(max(1, total_canonical)))
        quality_summary = (
            f"{verified_count}/{total_eligible} eligible listings verified authentic; "
            f"{len(canonical_opportunities)} distinct canonical listings."
        )

        # Identify deficit roles
        deficit_roles = [
            role for role, count in target_role_coverage.items()
            if count < max(1, coverage_goal // max(1, len(strategy.target_role_priorities)))
        ]

        # Check sufficiency: goal met and not forced gap for testing
        is_sufficient = (total_eligible >= coverage_goal and not deficit_roles) and not force_gap_for_testing

        if is_sufficient or iteration >= max_iterations:
            action = "STOP"
            gaps = []
            if not is_sufficient:
                gaps.append(
                    f"Iteration limit reached ({iteration}/{max_iterations}) with {total_eligible}/{coverage_goal} eligible listings."
                )
            assessment = CoverageAssessment(
                is_coverage_sufficient=is_sufficient,
                total_eligible_canonical=total_eligible,
                verified_opportunity_count=verified_count,
                duplicate_rate=round(dup_rate, 4),
                quality_summary=quality_summary,
                target_role_coverage=target_role_coverage,
                identified_gaps=gaps,
                recommended_action=action,
            )
            return assessment, None

        # Coverage is inadequate -> Determine adaptation
        identified_gaps = []
        if deficit_roles:
            for dr in deficit_roles:
                identified_gaps.append(f"Low coverage for target role '{dr}' ({target_role_coverage.get(dr, 0)} eligible).")
        else:
            identified_gaps.append(f"Total eligible listings ({total_eligible}) below target goal ({coverage_goal}).")

        # Adaptive strategy selection based on results and iteration count
        target_role = deficit_roles[0] if deficit_roles else strategy.target_role_priorities[0]
        summary = ""
        new_query: Optional[DiscoverySearchQuery] = None
        target_connectors = list(strategy.selected_connector_ids)

        is_early_career = profile.eligibility_constraints.total_full_time_experience_months <= 12
        seniority = "ENTRY_LEVEL" if is_early_career else "MID_LEVEL"
        candidate_skills = [
            s.skill_name for s in profile.assessed_skills[:5]
        ] or ["Python", "FastAPI"]
        primary_tech = candidate_skills[0] if candidate_skills else "Python"
        preferred_locs = profile.eligibility_constraints.preferred_locations or []
        allowed_modes = profile.eligibility_constraints.allowed_work_modes or [WorkMode.REMOTE]
        country_codes = profile.eligibility_constraints.authorized_country_codes or ["IN"]

        # ZERO-RESULT RECOVERY: If initial or previous search yielded 0 leads across all sources
        if total_canonical == 0:
            adaptation_type = "QUERY_RELAXATION"
            if iteration == 1:
                # Level 1: Expand city to state/region and broaden specific role title
                exp_locs, loc_str = resolve_geographic_expansion(preferred_locs, allowed_modes, country_codes, step=1)
                exp_role, exp_kws = resolve_role_expansion(target_role, seniority, candidate_skills, step=1)
                
                first_pref = preferred_locs[0] if preferred_locs else "local"
                summary = (
                    f"Zero results returned from initial search in '{first_pref}'. "
                    f"Broadened search scope to regional area ('{loc_str}') and role to '{exp_role}'."
                )
                query_str = f'"{exp_role}" {primary_tech} {loc_str}'
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_zero_iter_{iteration}_{exp_role[:8].lower()}",
                    role_title=exp_role,
                    query_string=query_str,
                    expanded_keywords=exp_kws,
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=allowed_modes,
                    target_locations=exp_locs,
                    target_country_codes=country_codes,
                    seniority_level=seniority,
                    relationship_type=CareerPathRelationship.TARGET,
                )
            elif iteration == 2 and WorkMode.REMOTE in allowed_modes:
                # Level 2: Expand to country-wide Remote opportunities
                exp_locs, loc_str = resolve_geographic_expansion(preferred_locs, allowed_modes, country_codes, step=2)
                exp_role, exp_kws = resolve_role_expansion(target_role, seniority, candidate_skills, step=2)
                country_name = "India" if "IN" in country_codes else (country_codes[0] if country_codes else "")
                
                summary = (
                    f"Expanded discovery to country-wide remote opportunities across {country_name} "
                    f"in alignment with candidate's remote work preference ('{exp_role}')."
                )
                query_str = f'"{exp_role}" remote {country_name}'.strip()
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_zero_remote_{iteration}_{exp_role[:8].lower()}",
                    role_title=exp_role,
                    query_string=query_str,
                    expanded_keywords=exp_kws + ["Remote"],
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=[WorkMode.REMOTE],
                    target_locations=exp_locs,
                    target_country_codes=country_codes,
                    seniority_level=seniority,
                    relationship_type=CareerPathRelationship.TARGET,
                )
            elif iteration >= 3 and adjacent_roles:
                # Level 3: Taxonomic Adjacent Role Expansion
                adaptation_type = "ADJACENT_EXPANSION"
                adj = adjacent_roles[0]
                target_role = adj.role_title
                exp_locs, _ = resolve_geographic_expansion(preferred_locs, allowed_modes, country_codes, step=2)
                summary = (
                    f"Expanded discovery to taxonomic adjacent role '{adj.role_title}' "
                    f"(Similarity: {int(adj.confidence_score * 100)}%) due to low primary target role yield."
                )
                query_str = f'"{adj.role_title}" {country_codes[0]}'
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_adj_{iteration}_{adj.canonical_occupation_code}",
                    role_title=adj.role_title,
                    query_string=query_str,
                    expanded_keywords=adj.matched_skill_names[:3] + [adj.role_title],
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=allowed_modes,
                    target_locations=exp_locs,
                    target_country_codes=country_codes,
                    seniority_level=seniority,
                    relationship_type=CareerPathRelationship.ADJACENT,
                )
            else:
                # Level 4: General software engineer search with candidate skills
                exp_locs, _ = resolve_geographic_expansion(preferred_locs, allowed_modes, country_codes, step=2)
                exp_role, exp_kws = resolve_role_expansion(target_role, seniority, candidate_skills, step=3)
                summary = f"Broadened query to early-career '{exp_role}' opportunities with '{primary_tech}'."
                query_str = f'"{exp_role}" {primary_tech}'
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_gen_{iteration}_{exp_role[:8].lower()}",
                    role_title=exp_role,
                    query_string=query_str,
                    expanded_keywords=exp_kws,
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=allowed_modes,
                    target_locations=exp_locs,
                    target_country_codes=country_codes,
                    seniority_level=seniority,
                    relationship_type=CareerPathRelationship.TARGET,
                )
        else:
            # PARTIAL COVERAGE ADAPTATION: Some opportunities found, but target role coverage deficient
            if iteration == 1:
                adaptation_type = "QUERY_RELAXATION"
                clean_role = target_role.replace("Senior ", "")
                if is_early_career and "junior" not in clean_role.lower():
                    query_str = f'"{clean_role}" (entry level OR junior) (site:greenhouse.io OR site:lever.co OR site:ashbyhq.com)'
                else:
                    query_str = f'"{clean_role}" hiring (site:greenhouse.io OR site:lever.co OR site:ashbyhq.com)'

                summary = (
                    f"Refined search query for '{clean_role}' targeting direct ATS job postings "
                    f"to optimize authentic individual vacancy precision."
                )
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_iter_{iteration}_{target_role[:10].lower()}",
                    role_title=clean_role,
                    query_string=query_str,
                    expanded_keywords=[primary_tech, "SQL", clean_role],
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=profile.eligibility_constraints.allowed_work_modes,
                    target_locations=profile.eligibility_constraints.preferred_locations,
                    target_country_codes=profile.eligibility_constraints.authorized_country_codes,
                    seniority_level="ENTRY_LEVEL" if is_early_career else "MID_LEVEL",
                    relationship_type=CareerPathRelationship.TARGET,
                )
            elif iteration >= 2 and adjacent_roles:
                adaptation_type = "ADJACENT_EXPANSION"
                adj = adjacent_roles[0]
                target_role = adj.role_title
                query_str = f'"{adj.role_title}" {profile.eligibility_constraints.authorized_country_codes[0]}'
                summary = (
                    f"Expanded discovery to taxonomic adjacent role '{adj.role_title}' "
                    f"(Similarity: {int(adj.confidence_score * 100)}%) due to low primary target role yield."
                )
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_adj_{iteration}_{adj.canonical_occupation_code}",
                    role_title=adj.role_title,
                    query_string=query_str,
                    expanded_keywords=adj.matched_skill_names[:3] + [adj.role_title],
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=profile.eligibility_constraints.allowed_work_modes,
                    target_locations=profile.eligibility_constraints.preferred_locations,
                    target_country_codes=profile.eligibility_constraints.authorized_country_codes,
                    seniority_level="MID_LEVEL",
                    relationship_type=CareerPathRelationship.ADJACENT,
                )
            else:
                adaptation_type = "CONNECTOR_REPLACEMENT"
                target_connectors = ["ats_career_pages", "web_search"]
                query_str = f"{target_role} hiring"
                summary = f"Routing targeted search to direct ATS and Web Search feeds for '{target_role}'."
                new_query = DiscoverySearchQuery(
                    query_id=f"adapt_conn_{iteration}_{target_role[:8].lower()}",
                    role_title=target_role,
                    query_string=query_str,
                    expanded_keywords=["Software", "Engineer", "Remote"],
                    category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                    work_modes=profile.eligibility_constraints.allowed_work_modes,
                    target_locations=profile.eligibility_constraints.preferred_locations,
                    target_country_codes=profile.eligibility_constraints.authorized_country_codes,
                    seniority_level="MID_LEVEL",
                    relationship_type=CareerPathRelationship.TARGET,
                )

        # Check duplicate hash avoidance: ensure new query isn't identical to an already executed query
        q_hash = compute_query_hash(new_query.query_string, target_connectors[0] if target_connectors else "all")
        if q_hash in executed_query_hashes:
            # Vary by technology or year to prevent deadloop
            new_query.query_string = f"{new_query.query_string} {primary_tech}"
            q_hash2 = compute_query_hash(new_query.query_string, target_connectors[0] if target_connectors else "all")
            if q_hash2 in executed_query_hashes:
                # All query variants for this connector have been exhausted
                assessment = CoverageAssessment(
                    is_coverage_sufficient=False,
                    total_eligible_canonical=total_eligible,
                    target_role_coverage=target_role_coverage,
                    identified_gaps=identified_gaps + ["All query variations and sources have been explored."],
                    recommended_action="STOP",
                )
                return assessment, None

        assessment = CoverageAssessment(
            is_coverage_sufficient=False,
            total_eligible_canonical=total_eligible,
            target_role_coverage=target_role_coverage,
            identified_gaps=identified_gaps,
            recommended_action=adaptation_type,
        )

        adaptation_event = AdaptationEvent(
            iteration=iteration,
            identified_gap="; ".join(identified_gaps),
            adaptation_type=adaptation_type,
            action_summary=summary,
            new_query=new_query,
            target_connector_ids=target_connectors,
        )

        return assessment, adaptation_event

from __future__ import annotations

import hashlib
import json
import logging
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

        # India Jobs MCP only if candidate is authorized in IN
        if "IN" in auth_countries and "india_jobs_mcp" in healthy_connectors:
            selected_connectors.append("india_jobs_mcp")

        # JobSpy & ATS Direct for general global / US discovery
        if "jobspy_mcp" in healthy_connectors:
            selected_connectors.append("jobspy_mcp")
        if "ats_career_pages" in healthy_connectors:
            selected_connectors.append("ats_career_pages")
        if "web_search" in healthy_connectors:
            selected_connectors.append("web_search")

        # If a failure simulation was explicitly requested, ensure that connector is attempted
        # so the agent workflow exercises runtime error shielding
        if simulate_failure_connector and simulate_failure_connector not in selected_connectors:
            selected_connectors.append(simulate_failure_connector)

        if not selected_connectors:
            selected_connectors = ["web_search"]

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

        # Adaptive strategy selection based on iteration count
        adaptation_type = "QUERY_RELAXATION"
        target_role = deficit_roles[0] if deficit_roles else strategy.target_role_priorities[0]
        summary = ""
        new_query: Optional[DiscoverySearchQuery] = None
        target_connectors = list(strategy.selected_connector_ids)

        if iteration == 1:
            # Level 1: Query Keyword Relaxation (broader role query)
            adaptation_type = "QUERY_RELAXATION"
            clean_role = target_role.replace("Software Engineer", "Developer").replace("Backend", "Software")
            query_str = f'"{clean_role}" Python remote'
            summary = (
                f"Relaxed search query for '{target_role}' to broader title '{clean_role}' "
                f"to increase opportunity recall."
            )
            new_query = DiscoverySearchQuery(
                query_id=f"adapt_iter_{iteration}_{target_role[:10].lower()}",
                role_title=clean_role,
                query_string=query_str,
                expanded_keywords=["Python", "SQL", clean_role],
                category=profile.eligibility_constraints.allowed_opportunity_categories[0],
                work_modes=profile.eligibility_constraints.allowed_work_modes,
                target_locations=profile.eligibility_constraints.preferred_locations,
                target_country_codes=profile.eligibility_constraints.authorized_country_codes,
                seniority_level="ENTRY_LEVEL" if profile.eligibility_constraints.total_full_time_experience_months <= 12 else "MID_LEVEL",
                relationship_type=CareerPathRelationship.TARGET,
            )
        elif iteration >= 2 and adjacent_roles:
            # Level 2: Adjacent Role Expansion
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
            # Level 3: Connector Focus / Direct ATS Fallback
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

        # Check duplicate hash avoidance
        q_hash = compute_query_hash(new_query.query_string, target_connectors[0] if target_connectors else "all")
        if q_hash in executed_query_hashes:
            # Modify query string slightly to break loop
            new_query.query_string = f"{new_query.query_string} 2026"

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

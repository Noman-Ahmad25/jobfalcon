from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.modules.discovery.role_mapper import ROLE_ARCHETYPES, RoleArchetype
from app.modules.explanation.gap_analyzer import CareerGapAnalysisService
from app.modules.profiling.llm_client import BaseLLMClient
from app.schemas.career_path import (
    ActionHorizon,
    ActionProgressStatus,
    CareerPathAssessmentResponse,
    CareerPathGraph,
    CareerPathNodeView,
    CareerPathTransitionEdge,
    DevelopmentActionItem,
    OpportunityCoverageSummary,
    OpportunityMarketInsight,
    OpportunitySkillSignal,
    PersonalizedDevelopmentPlan,
    RoleReadiness,
    RoleTargetAssessment,
    SkillRequirementImportance,
    TargetRoleRelationship,
)
from app.schemas.common import DegreeLevel, WorkMode
from app.schemas.explanation import EvidenceCitation
from app.schemas.gap_analysis import ActionType, GapImportance, GapStatus
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity
from app.schemas.profile import AssessedSkill, CandidateCareerProfile

logger = logging.getLogger(__name__)


def _normalize_token(text: str) -> str:
    """Normalizes token for case and punctuation insensitive matching."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _extract_source_name(opp: PolymorphicOpportunity) -> str:
    """Extracts human-readable source system name from opportunity metadata or URL."""
    if hasattr(opp, "source_system") and getattr(opp, "source_system"):
        return str(getattr(opp, "source_system"))
    if "source_system" in opp.category_specific_attributes:
        return str(opp.category_specific_attributes["source_system"])
    if "://" in opp.source_url:
        domain = opp.source_url.split("://")[1].split("/")[0]
        return domain.replace("www.", "")
    return "generic_feed"


class CareerPathIntelligenceService:
    """Service providing personalized career path intelligence, graph mapping,

    and grounded development planning based strictly on candidate evidence and market signals.
    """

    def __init__(
        self,
        archetypes: Optional[Sequence[RoleArchetype]] = None,
        gap_analyzer: Optional[CareerGapAnalysisService] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ) -> None:
        self.archetypes = list(archetypes or ROLE_ARCHETYPES)
        self.gap_analyzer = gap_analyzer or CareerGapAnalysisService(archetypes=self.archetypes)
        self.llm_client = llm_client

    # =========================================================================
    # 1. PERSONALIZED TARGET-ROLE ANALYSIS
    # =========================================================================

    def assess_candidate_career_paths(
        self,
        candidate: CandidateCareerProfile,
        discovered_opportunities: Optional[list[PolymorphicOpportunity]] = None,
        target_role_overrides: Optional[list[str]] = None,
    ) -> CareerPathAssessmentResponse:
        """Evaluates candidate evidence against target roles, adjacent options, and exploratory possibilities."""
        opportunities = discovered_opportunities or []

        # 1. Normalize candidate skills for fast lookup
        cand_skill_map: dict[str, AssessedSkill] = {
            _normalize_token(s.skill_name): s for s in candidate.assessed_skills
        }

        # 2. Identify target roles to evaluate
        direct_target_names: list[str] = []
        if target_role_overrides:
            direct_target_names = [r.strip() for r in target_role_overrides if r.strip()]
        else:
            direct_target_names = [p.title for p in candidate.target_career_paths]
            if not direct_target_names and candidate.current_career_path:
                direct_target_names = [candidate.current_career_path.title]

        explicit_adjacent_names = [p.title for p in candidate.adjacent_career_paths]

        # 3. Assess each role archetype
        role_assessments: list[RoleTargetAssessment] = []
        assessed_roles_set: set[str] = set()

        # Helper to check if role matches name list
        def matches_name(role: RoleArchetype, name_list: list[str]) -> bool:
            for name in name_list:
                norm_name = _normalize_token(name)
                if norm_name in _normalize_token(role.role_title) or _normalize_token(role.role_title) in norm_name:
                    return True
                for syn in role.synonyms:
                    if norm_name in _normalize_token(syn) or _normalize_token(syn) in norm_name:
                        return True
            return False

        for archetype in self.archetypes:
            core_skills_norm = {_normalize_token(s): s for s in archetype.core_skills}
            overlap_keys = core_skills_norm.keys() & cand_skill_map.keys()
            overlap_ratio = len(overlap_keys) / len(core_skills_norm) if core_skills_norm else 0.0

            # Determine relationship
            is_direct = matches_name(archetype, direct_target_names)
            is_explicit_adj = matches_name(archetype, explicit_adjacent_names)

            if is_direct:
                relationship = TargetRoleRelationship.DIRECT_TARGET
            elif is_explicit_adj or overlap_ratio >= 0.25:
                relationship = TargetRoleRelationship.ADJACENT_OPTION
            else:
                relationship = TargetRoleRelationship.EXPLORATORY_POSSIBILITY

            # Supporting skills & evidence
            supporting_skills: list[str] = []
            supporting_citations: list[EvidenceCitation] = []
            for k in overlap_keys:
                cand_skill = cand_skill_map[k]
                supporting_skills.append(cand_skill.skill_name)
                for ev in cand_skill.evidence_records:
                    supporting_citations.append(
                        EvidenceCitation(
                            evidence_id=ev.evidence_id,
                            source_type=ev.source_type,
                            source_uri=ev.source_uri,
                            snippet=ev.extracted_snippet,
                            verifiability_weight=ev.verifiability_weight,
                            observed_at=ev.observed_at,
                        )
                    )

            # Deduplicate citations by evidence_id
            unique_citations: list[EvidenceCitation] = []
            seen_ev_ids: set[str] = set()
            for cit in supporting_citations:
                if cit.evidence_id not in seen_ev_ids:
                    seen_ev_ids.add(cit.evidence_id)
                    unique_citations.append(cit)

            # Critical gaps
            missing_skills = [
                name for k, name in core_skills_norm.items() if k not in cand_skill_map
            ]

            # Eligibility uncertainties
            eligibility_uncertainties: list[str] = []
            constraints = candidate.eligibility_constraints
            if constraints.is_currently_enrolled_student and not constraints.expected_graduation_date:
                eligibility_uncertainties.append(
                    "Graduation date not specified; full-time role eligibility may depend on program completion."
                )
            if constraints.requires_visa_sponsorship:
                eligibility_uncertainties.append(
                    "Work authorization requires employer visa sponsorship; opportunities must sponsor target visa."
                )
            if WorkMode.REMOTE not in constraints.allowed_work_modes and not constraints.preferred_locations:
                eligibility_uncertainties.append(
                    "On-site/hybrid preference without specific target locations creates geographic uncertainty."
                )

            # Determine readiness level
            if overlap_ratio >= 0.65 and constraints.total_full_time_experience_months >= 6:
                readiness = RoleReadiness.PURSUABLE_NOW
            elif overlap_ratio >= 0.30:
                readiness = RoleReadiness.ATTAINABLE_WITH_DEVELOPMENT
            else:
                readiness = RoleReadiness.EXPLORATORY

            # Discovered opportunity coverage
            matching_opps = self._filter_opportunities_for_role(archetype, opportunities)
            opp_count = len(matching_opps)
            sample_titles = [o.title for o in matching_opps[:3]]
            sample_sources = list({_extract_source_name(o) for o in matching_opps})

            coverage_note = None
            if opp_count == 0:
                coverage_note = (
                    "No active discovered listings for this role in the current repository sample. "
                    "Requirements are derived from O*NET taxonomy rather than live job data."
                )
            elif opp_count < 3:
                coverage_note = (
                    f"Limited sample size ({opp_count} discovered listings). Observations reflect available "
                    "listings and do not represent the broader labor market."
                )

            opp_coverage = OpportunityCoverageSummary(
                matching_opportunity_count=opp_count,
                sample_opportunity_titles=sample_titles,
                sample_sources=sample_sources,
                coverage_limitation_note=coverage_note,
            )

            # Feasibility rationale
            rationale = self._compose_feasibility_rationale(
                archetype=archetype,
                relationship=relationship,
                readiness=readiness,
                overlap_ratio=overlap_ratio,
                supporting_count=len(supporting_skills),
                missing_count=len(missing_skills),
                opp_count=opp_count,
            )

            role_assessments.append(
                RoleTargetAssessment(
                    role_title=archetype.role_title,
                    canonical_occupation_code=archetype.canonical_occupation_code,
                    relationship=relationship,
                    readiness=readiness,
                    skill_overlap_ratio=round(overlap_ratio, 2),
                    supporting_skills=sorted(supporting_skills),
                    supporting_evidence=unique_citations[:6],
                    critical_gaps=sorted(missing_skills),
                    eligibility_uncertainties=eligibility_uncertainties,
                    opportunity_coverage=opp_coverage,
                    feasibility_rationale=rationale,
                )
            )
            assessed_roles_set.add(_normalize_token(archetype.role_title))

        # Check for user target roles not matching any known archetype
        for custom_target in direct_target_names:
            if _normalize_token(custom_target) not in assessed_roles_set:
                role_assessments.append(
                    RoleTargetAssessment(
                        role_title=custom_target,
                        canonical_occupation_code=None,
                        relationship=TargetRoleRelationship.DIRECT_TARGET,
                        readiness=RoleReadiness.EXPLORATORY,
                        skill_overlap_ratio=0.0,
                        supporting_skills=[],
                        supporting_evidence=[],
                        critical_gaps=["Unmapped occupational taxonomy requirements"],
                        eligibility_uncertainties=["Custom role taxonomy mapping requires calibration"],
                        opportunity_coverage=OpportunityCoverageSummary(
                            matching_opportunity_count=0,
                            coverage_limitation_note="Custom role title has no taxonomy benchmark in current database.",
                        ),
                        feasibility_rationale=(
                            f"'{custom_target}' is an explicit candidate target role, but lacks standardized "
                            "O*NET archetype mapping. Evidence is insufficient to verify transition feasibility."
                        ),
                    )
                )

        # Sort assessments: DIRECT_TARGET first, then ADJACENT_OPTION, then EXPLORATORY_POSSIBILITY
        rel_priority = {
            TargetRoleRelationship.DIRECT_TARGET: 0,
            TargetRoleRelationship.ADJACENT_OPTION: 1,
            TargetRoleRelationship.EXPLORATORY_POSSIBILITY: 2,
        }
        role_assessments.sort(
            key=lambda r: (rel_priority.get(r.relationship, 3), -r.skill_overlap_ratio, r.role_title)
        )

        # 4. Build Career Path Graph
        graph = self.build_career_path_graph(candidate, role_assessments)

        # 5. Extract Opportunity Market Insights
        market_insights = self.extract_opportunity_market_insights(
            opportunities=opportunities,
            assessed_roles=role_assessments,
        )

        # 6. Generate Personalized Development Plan
        development_plan = self.generate_development_plan(
            candidate=candidate,
            role_assessments=role_assessments,
            market_insights=market_insights,
            opportunities=opportunities,
        )

        return CareerPathAssessmentResponse(
            user_id=candidate.user_id,
            assessed_at=datetime.now(timezone.utc),
            role_assessments=role_assessments,
            career_path_graph=graph,
            development_plan=development_plan,
            total_target_roles=sum(
                1 for r in role_assessments if r.relationship == TargetRoleRelationship.DIRECT_TARGET
            ),
            total_adjacent_roles=sum(
                1 for r in role_assessments if r.relationship == TargetRoleRelationship.ADJACENT_OPTION
            ),
            total_exploratory_roles=sum(
                1 for r in role_assessments if r.relationship == TargetRoleRelationship.EXPLORATORY_POSSIBILITY
            ),
        )

    # =========================================================================
    # 2. CAREER PATH GRAPH CONSTRUCTION
    # =========================================================================

    def build_career_path_graph(
        self,
        candidate: CandidateCareerProfile,
        assessments: list[RoleTargetAssessment],
    ) -> CareerPathGraph:
        """Constructs a cycle-safe, evidence-grounded career path transition graph."""
        nodes: list[CareerPathNodeView] = []
        assessment_by_title: dict[str, RoleTargetAssessment] = {}

        for a in assessments:
            node_id = f"node_{_normalize_token(a.role_title)}"
            nodes.append(
                CareerPathNodeView(
                    node_id=node_id,
                    role_title=a.role_title,
                    canonical_occupation_code=a.canonical_occupation_code,
                    relationship=a.relationship,
                    readiness=a.readiness,
                    skill_overlap_ratio=a.skill_overlap_ratio,
                    core_competencies=a.supporting_skills + a.critical_gaps,
                )
            )
            assessment_by_title[a.role_title] = a

        # Identify baseline role: candidate current career path or top-overlap pursuable role
        baseline_title: Optional[str] = None
        if candidate.current_career_path:
            baseline_title = candidate.current_career_path.title
        else:
            # Pick highest overlap pursuable role
            pursuable = [a for a in assessments if a.readiness == RoleReadiness.PURSUABLE_NOW]
            if pursuable:
                baseline_title = pursuable[0].role_title
            elif assessments:
                baseline_title = assessments[0].role_title

        # Generate directed edges between relevant roles
        edges: list[CareerPathTransitionEdge] = []
        seen_pairs: set[tuple[str, str]] = set()

        # Topological ranking to guarantee DAG (no cycles)
        readiness_rank = {
            RoleReadiness.PURSUABLE_NOW: 1,
            RoleReadiness.ATTAINABLE_WITH_DEVELOPMENT: 2,
            RoleReadiness.EXPLORATORY: 3,
        }
        rel_rank = {
            TargetRoleRelationship.DIRECT_TARGET: 1,
            TargetRoleRelationship.ADJACENT_OPTION: 2,
            TargetRoleRelationship.EXPLORATORY_POSSIBILITY: 3,
        }

        def role_order_key(role: RoleTargetAssessment) -> tuple:
            is_baseline = 0 if (baseline_title and role.role_title == baseline_title) else 1
            return (
                is_baseline,
                readiness_rank.get(role.readiness, 2),
                rel_rank.get(role.relationship, 2),
                -role.skill_overlap_ratio,
                role.role_title,
            )

        # For every pair of roles, evaluate transition feasibility
        for src in assessments:
            for tgt in assessments:
                if src.role_title == tgt.role_title:
                    continue

                pair = (src.role_title, tgt.role_title)
                if pair in seen_pairs:
                    continue

                # Enforce strict acyclic topological direction: order(src) must be strictly less than order(tgt)
                if role_order_key(src) >= role_order_key(tgt):
                    continue

                # Check skill overlap between source and target
                src_skills = set(_normalize_token(s) for s in src.supporting_skills)
                tgt_skills_needed = set(_normalize_token(s) for s in tgt.supporting_skills + tgt.critical_gaps)

                transferable = [s for s in src.supporting_skills if _normalize_token(s) in tgt_skills_needed]
                gaps = [s for s in tgt.critical_gaps if _normalize_token(s) not in src_skills]

                # Transition is supported if:
                # 1. Source is baseline role and target is direct target or adjacent option
                # 2. Or there is significant transferable skill overlap (>= 30%)
                is_from_baseline = baseline_title and (src.role_title == baseline_title)
                has_skill_bridge = len(transferable) >= 2 or (tgt.skill_overlap_ratio >= 0.30)

                if is_from_baseline or has_skill_bridge:
                    # Transition type
                    if tgt.relationship == TargetRoleRelationship.DIRECT_TARGET:
                        transition_type = "DIRECT_PROGRESSION"
                    elif tgt.relationship == TargetRoleRelationship.ADJACENT_OPTION:
                        transition_type = "LATERAL_EXPANSION"
                    else:
                        transition_type = "STRETCH_PIVOT"

                    # Feasibility score
                    overlap_factor = tgt.skill_overlap_ratio
                    transfer_factor = (len(transferable) / max(1, len(tgt.critical_gaps) + len(transferable)))
                    feasibility = round(min(1.0, max(0.1, 0.5 * overlap_factor + 0.3 * transfer_factor + 0.2)), 2)

                    effort = "LOW" if feasibility >= 0.70 else ("MEDIUM" if feasibility >= 0.45 else "HIGH")

                    basis = (
                        f"Transition supported by {len(transferable)} transferable skill(s) "
                        f"({', '.join(transferable[:3]) if transferable else 'foundational competencies'}). "
                        f"Requires bridging {len(gaps)} key development gap(s)."
                    )

                    edge = CareerPathTransitionEdge(
                        edge_id=f"edge_{uuid.uuid4().hex[:8]}",
                        source_role=src.role_title,
                        target_role=tgt.role_title,
                        transition_type=transition_type,
                        basis_description=basis,
                        transferable_skills=transferable,
                        development_gaps=gaps[:5],
                        feasibility_score=feasibility,
                        estimated_effort_level=effort,
                    )
                    edges.append(edge)
                    seen_pairs.add(pair)

        # Cycle safety check
        is_cycle_free = self._verify_cycle_free(nodes, edges)

        return CareerPathGraph(
            nodes=nodes,
            edges=edges,
            baseline_role_title=baseline_title,
            is_cycle_free=is_cycle_free,
        )

    # =========================================================================
    # 3. OPPORTUNITY-AWARE MARKET INSIGHTS
    # =========================================================================

    def extract_opportunity_market_insights(
        self,
        opportunities: list[PolymorphicOpportunity],
        assessed_roles: list[RoleTargetAssessment],
    ) -> OpportunityMarketInsight:
        """Derives transparent skill demand signals from discovered job listings and O*NET taxonomy."""
        opp_count = len(opportunities)

        if opp_count == 0:
            data_sufficiency = "NO_DISCOVERED_DATA"
        elif opp_count < 4:
            data_sufficiency = "LIMITED_SAMPLE"
        elif opp_count < 15:
            data_sufficiency = "MODERATE"
        else:
            data_sufficiency = "HIGH"

        sources = sorted(list({_extract_source_name(o) for o in opportunities}))

        # Track skill frequencies
        # Map: skill_key -> { 'name': str, 'mandatory_count': int, 'preferred_count': int, 'titles': set, 'sources': set }
        skill_stats: dict[str, dict] = {}

        for opp in opportunities:
            opp_src = _extract_source_name(opp)
            for req in opp.skill_requirements:
                k = _normalize_token(req.skill_name)
                if k not in skill_stats:
                    skill_stats[k] = {
                        "name": req.skill_name,
                        "mandatory_count": 0,
                        "preferred_count": 0,
                        "titles": set(),
                        "sources": set(),
                    }
                if req.is_mandatory:
                    skill_stats[k]["mandatory_count"] += 1
                else:
                    skill_stats[k]["preferred_count"] += 1
                skill_stats[k]["titles"].add(opp.title)
                skill_stats[k]["sources"].add(opp_src)

        signals: list[OpportunitySkillSignal] = []

        # 1. Explicitly required vs preferred from listings
        for k, stats in skill_stats.items():
            total = stats["mandatory_count"] + stats["preferred_count"]
            if stats["mandatory_count"] > 0:
                sig_type = SkillRequirementImportance.EXPLICITLY_REQUIRED
            elif total >= 2:
                sig_type = SkillRequirementImportance.EMPLOYER_PREFERRED
            else:
                sig_type = SkillRequirementImportance.UNCERTAIN_IMPORTANCE

            signals.append(
                OpportunitySkillSignal(
                    skill_name=stats["name"],
                    signal_type=sig_type,
                    frequency_in_sample=total,
                    supporting_job_titles=sorted(list(stats["titles"]))[:3],
                    supporting_sources=sorted(list(stats["sources"])),
                )
            )

        # 2. Taxonomy inferred skills (from target role archetypes not yet seen in live jobs)
        target_roles = [r for r in assessed_roles if r.relationship == TargetRoleRelationship.DIRECT_TARGET]
        for tr in target_roles:
            for gap_skill in tr.critical_gaps:
                k = _normalize_token(gap_skill)
                if k not in skill_stats:
                    signals.append(
                        OpportunitySkillSignal(
                            skill_name=gap_skill,
                            signal_type=SkillRequirementImportance.TAXONOMY_INFERRED,
                            frequency_in_sample=0,
                            supporting_job_titles=[f"O*NET Archetype: {tr.role_title}"],
                            supporting_sources=["ESCO/O*NET Taxonomy v2024"],
                        )
                    )

        # Sort signals by frequency and importance
        type_rank = {
            SkillRequirementImportance.EXPLICITLY_REQUIRED: 0,
            SkillRequirementImportance.EMPLOYER_PREFERRED: 1,
            SkillRequirementImportance.TAXONOMY_INFERRED: 2,
            SkillRequirementImportance.UNCERTAIN_IMPORTANCE: 3,
        }
        signals.sort(key=lambda s: (type_rank.get(s.signal_type, 4), -s.frequency_in_sample, s.skill_name))

        # Honest limitation disclosure
        if opp_count == 0:
            disclosure = (
                "No live discovered opportunities are currently loaded. Market demand signals are derived "
                "purely from standardized O*NET/ESCO occupational archetypes. Live job verification is recommended."
            )
        else:
            disclosure = (
                f"Market signals are derived from an active sample of {opp_count} discovered opportunity listings "
                f"across sources [{', '.join(sources)}]. This sample reflects current ingestion and does not "
                "represent an exhaustive census of the global labor market."
            )

        return OpportunityMarketInsight(
            total_opportunities_analyzed=opp_count,
            data_sufficiency_level=data_sufficiency,
            sources_represented=sources,
            recurring_skills=signals[:15],
            limitation_disclosure=disclosure,
        )

    # =========================================================================
    # 4. PERSONALIZED DEVELOPMENT PLAN GENERATION
    # =========================================================================

    def generate_development_plan(
        self,
        candidate: CandidateCareerProfile,
        role_assessments: list[RoleTargetAssessment],
        market_insights: OpportunityMarketInsight,
        opportunities: list[PolymorphicOpportunity],
    ) -> PersonalizedDevelopmentPlan:
        """Synthesizes a prioritized, practical development plan with measurable completion criteria."""
        # 1. Run gap analysis
        target_roles = [
            r.role_title for r in role_assessments if r.relationship == TargetRoleRelationship.DIRECT_TARGET
        ]
        gap_resp = self.gap_analyzer.analyze_candidate_gaps(
            candidate=candidate,
            target_roles=target_roles,
            opportunities=opportunities,
        )

        # 2. Candidate experience context
        exp_months = candidate.eligibility_constraints.total_full_time_experience_months
        is_student = candidate.eligibility_constraints.is_currently_enrolled_student

        # Map opportunity frequency for weighting
        opp_freq_map: dict[str, int] = {
            _normalize_token(s.skill_name): s.frequency_in_sample for s in market_insights.recurring_skills
        }
        opp_req_map: dict[str, bool] = {
            _normalize_token(s.skill_name): (s.signal_type == SkillRequirementImportance.EXPLICITLY_REQUIRED)
            for s in market_insights.recurring_skills
        }

        short_term_actions: list[DevelopmentActionItem] = []
        long_term_actions: list[DevelopmentActionItem] = []

        # Track generated action IDs for dependency wiring
        created_actions: list[DevelopmentActionItem] = []

        for idx, gap in enumerate(gap_resp.prioritized_gaps):
            skill_k = _normalize_token(gap.skill_name)
            freq = opp_freq_map.get(skill_k, len(gap.relevant_opportunities))
            is_explicitly_req = opp_req_map.get(skill_k, gap.is_mandatory)

            # Determine horizon:
            # Foundational / critical tools that can be demonstrated quickly are SHORT_TERM.
            # Deep system architecture, large distributed stacks, or multiple dependencies are LONG_TERM.
            is_short_term = (
                gap.importance in (GapImportance.CRITICAL, GapImportance.HIGH)
                and (exp_months <= 24 or is_student or len(short_term_actions) < 3)
            )

            horizon = ActionHorizon.SHORT_TERM if is_short_term else ActionHorizon.LONG_TERM

            # Generate practical demonstration activity and completion criteria
            action_type, activity, criterion, evidence, rationale = self._craft_practical_activity(
                gap=gap,
                candidate=candidate,
                freq=freq,
                is_explicitly_required=is_explicitly_req,
                horizon=horizon,
            )

            # Action dependencies: higher priority action can serve as dependency for later ones
            deps: list[str] = []
            if created_actions and horizon == ActionHorizon.LONG_TERM:
                # Long-term actions depend on top short-term foundational action
                deps.append(created_actions[0].action_id)

            item = DevelopmentActionItem(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                skill_or_capability=gap.skill_name,
                motivating_gap_id=gap.canonical_skill_id,
                motivating_gap_description=gap.why_it_matters,
                target_roles_supported=gap.relevant_target_roles or target_roles,
                supported_opportunities_count=freq,
                action_type=action_type,
                horizon=horizon,
                concrete_activity=activity,
                measurable_completion_criterion=criterion,
                verifiable_evidence_to_produce=evidence,
                priority=gap.importance,
                priority_rationale=rationale,
                dependencies=deps,
                status=ActionProgressStatus.NOT_STARTED,
            )

            created_actions.append(item)
            if horizon == ActionHorizon.SHORT_TERM:
                short_term_actions.append(item)
            else:
                long_term_actions.append(item)

            # Limit total actions to top 6 to prevent cognitive overwhelm
            if len(created_actions) >= 6:
                break

        summary = (
            f"Personalized development plan for candidate {candidate.user_id} targeting "
            f"{', '.join(target_roles[:2]) or 'Software Engineering'}. "
            f"Includes {len(short_term_actions)} immediate short-term demonstrable project action(s) "
            f"and {len(long_term_actions)} strategic capability advancement(s)."
        )

        return PersonalizedDevelopmentPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}",
            user_id=candidate.user_id,
            generated_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            plan_summary=summary,
            short_term_actions=short_term_actions,
            long_term_actions=long_term_actions,
            total_actions=len(created_actions),
            market_insights=market_insights,
            ethical_disclaimer=(
                "Completing development actions provides verifiable evidence of your capabilities but does not "
                "guarantee employment, interview selection, or specific algorithmic ranking improvement."
            ),
        )

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _filter_opportunities_for_role(
        self,
        archetype: RoleArchetype,
        opportunities: list[PolymorphicOpportunity],
    ) -> list[PolymorphicOpportunity]:
        """Matches opportunities to an archetype by occupation code or role title keywords."""
        matched: list[PolymorphicOpportunity] = []
        arch_norm = _normalize_token(archetype.role_title)
        syns_norm = [_normalize_token(s) for s in archetype.synonyms]

        for opp in opportunities:
            if opp.mapped_occupation_code == archetype.canonical_occupation_code:
                matched.append(opp)
                continue

            opp_norm = _normalize_token(opp.title)
            if arch_norm in opp_norm or opp_norm in arch_norm:
                matched.append(opp)
                continue

            for s in syns_norm:
                if s in opp_norm or opp_norm in s:
                    matched.append(opp)
                    break

        return matched

    def _compose_feasibility_rationale(
        self,
        archetype: RoleArchetype,
        relationship: TargetRoleRelationship,
        readiness: RoleReadiness,
        overlap_ratio: float,
        supporting_count: int,
        missing_count: int,
        opp_count: int,
    ) -> str:
        """Constructs an auditable explanation for role feasibility."""
        pct = int(overlap_ratio * 100)
        if readiness == RoleReadiness.PURSUABLE_NOW:
            return (
                f"Candidate demonstrates {pct}% core competency overlap ({supporting_count} verified skills). "
                f"Eligible for immediate target applications subject to posting-specific requirements. "
                f"Discovered {opp_count} active listing(s)."
            )
        elif readiness == RoleReadiness.ATTAINABLE_WITH_DEVELOPMENT:
            return (
                f"Demonstrates solid foundation with {pct}% core skill overlap, but missing {missing_count} "
                f"competencies (e.g. {', '.join(archetype.core_skills[-2:])}). Bridging these gaps via targeted "
                f"portfolio projects makes this role realistically attainable in the short term."
            )
        else:
            return (
                f"Core competency overlap is currently limited ({pct}%). The candidate profile lacks evidence for "
                f"{missing_count} essential competencies required by O*NET {archetype.canonical_occupation_code}. "
                "Recommended as an exploratory long-term path rather than an immediate target."
            )

    def _craft_practical_activity(
        self,
        gap: Any,
        candidate: CandidateCareerProfile,
        freq: int,
        is_explicitly_required: bool,
        horizon: ActionHorizon,
    ) -> tuple[ActionType, str, str, str, str]:
        """Crafts a practical activity, measurable criterion, verifiable evidence, and rationale."""
        skill = gap.skill_name
        exp_months = candidate.eligibility_constraints.total_full_time_experience_months

        # Select action type
        if gap.gap_status == GapStatus.NOT_DEMONSTRATED:
            action_type = ActionType.PORTFOLIO_BUILD if exp_months <= 24 else ActionType.PROJECT_ENHANCEMENT
        elif gap.gap_status == GapStatus.PROFICIENCY_UNCERTAIN:
            action_type = ActionType.EVIDENCE_COLLECTION
        else:
            action_type = ActionType.CONCEPT_STUDY

        # Activity & Completion Criteria definitions
        if action_type == ActionType.PORTFOLIO_BUILD:
            activity = (
                f"Build a standalone, open-source microservice or demonstration repository implementing {skill}. "
                "Structure it with a clean directory layout, automated unit tests, and a README documenting "
                "the architectural design choices, setup instructions, and execution commands."
            )
            criterion = (
                f"Public repository with >= 3 distinct commits, automated test suite with > 80% coverage, "
                f"and verifiable continuous integration build passing."
            )
            evidence = "Public GitHub repository URL with passing test badge and system architecture diagram in README."

        elif action_type == ActionType.PROJECT_ENHANCEMENT:
            activity = (
                f"Extend an existing codebase or portfolio project by integrating {skill}. "
                "Include end-to-end integration tests, structured logging, and benchmark comparison measurements."
            )
            criterion = (
                f"Pull Request or commit diff demonstrating {skill} integration alongside regression tests "
                "and reproducible performance benchmark logs."
            )
            evidence = "Git commit / Pull Request link showing production-quality code diff and automated test suite."

        elif action_type == ActionType.EVIDENCE_COLLECTION:
            activity = (
                f"Gather and corroborate verifiable evidence for {skill} by adding integration benchmarks, "
                "profiling reports, or live deployment endpoints to existing project artifacts."
            )
            criterion = (
                f"Documented execution trace, profiling metrics, or public deployment URL verifying "
                f"operational {skill} execution."
            )
            evidence = "Live demo URL, execution log output, or benchmark report artifact."

        else:
            activity = (
                f"Perform an architectural deep-dive into {skill} operational patterns, failure modes, "
                "and scaling characteristics. Create an Architecture Decision Record (ADR) comparing trade-offs."
            )
            criterion = (
                f"Written Architecture Decision Record (ADR) analyzing at least 2 alternative solutions, "
                "documenting trade-offs, failure scenarios, and production telemetry guidelines."
            )
            evidence = "Markdown Architecture Decision Record (ADR) file committed to repository docs/ directory."

        # Rationale
        if is_explicitly_required:
            rationale = (
                f"Explicitly mandatory requirement across active job listings. Closing this gap directly removes "
                f"hard screening hurdles."
            )
        elif freq >= 2:
            rationale = (
                f"Recurring across {freq} discovered job listings in target role family. Demonstrating verifiable "
                f"capability raises candidate competitive standing."
            )
        else:
            rationale = (
                f"Standard core competency in O*NET occupational taxonomy for target roles. "
                "Provides balanced technical depth."
            )

        return action_type, activity, criterion, evidence, rationale

    def _verify_cycle_free(
        self,
        nodes: list[CareerPathNodeView],
        edges: list[CareerPathTransitionEdge],
    ) -> bool:
        """Verifies using Depth-First Search that the directed graph contains no cycles."""
        adj: dict[str, list[str]] = {n.role_title: [] for n in nodes}
        for e in edges:
            if e.source_role in adj:
                adj[e.source_role].append(e.target_role)

        visited: set[str] = set()
        recursion_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            recursion_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if not dfs(neighbor):
                        return False
                elif neighbor in recursion_stack:
                    # Cycle detected
                    return False
            recursion_stack.remove(node)
            return True

        for n in nodes:
            if n.role_title not in visited:
                if not dfs(n.role_title):
                    return False
        return True

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.modules.discovery.role_mapper import ROLE_ARCHETYPES, RoleArchetype
from app.schemas.explanation import EvidenceCitation
from app.schemas.gap_analysis import (
    ActionType,
    CandidateCareerGapAnalysisResponse,
    CareerGapItem,
    CareerImprovementSuggestion,
    GapImportance,
    GapStatus,
)
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity
from app.schemas.profile import AssessedSkill, CandidateCareerProfile
from app.schemas.ranking import RankedOpportunity

logger = logging.getLogger(__name__)


class CareerGapAnalysisService:
    """Evaluates candidate evidence against target career ambitions and opportunity requirements.

    Distinguishes strictly between:
    1. NOT_DEMONSTRATED: Skill is unevidenced in candidate profile.
    2. PROFICIENCY_UNCERTAIN: Skill has evidence, but proficiency is below requirement or confidence is low.
    3. REQUIREMENT_UNCLEAR: Requirement definition is ambiguous or uncalibrated.
    """

    def __init__(self, archetypes: Optional[Sequence[RoleArchetype]] = None) -> None:
        self.archetypes = archetypes or ROLE_ARCHETYPES
        self._archetype_map = {
            a.role_title.lower(): a for a in self.archetypes
        }

    def analyze_candidate_gaps(
        self,
        candidate: CandidateCareerProfile,
        target_roles: Optional[list[str]] = None,
        opportunities: Optional[list[PolymorphicOpportunity]] = None,
        ranked_recommendations: Optional[list[RankedOpportunity]] = None,
    ) -> CandidateCareerGapAnalysisResponse:
        """Executes transparent, evidence-grounded gap analysis and synthesizes actionable improvements."""
        # 1. Resolve Target Roles to Evaluate
        evaluated_roles: list[str] = []
        if target_roles:
            evaluated_roles = [r.strip() for r in target_roles if r.strip()]
        else:
            evaluated_roles = [p.title for p in candidate.target_career_paths]
            if not evaluated_roles and candidate.current_career_path:
                evaluated_roles = [candidate.current_career_path.title]

        # 2. Extract Opportunities from Ranked Recommendations if provided
        opp_list: list[PolymorphicOpportunity] = []
        if opportunities:
            opp_list.extend(opportunities)
        if ranked_recommendations:
            opp_list.extend([r.opportunity for r in ranked_recommendations])

        # Deduplicate opportunities by opportunity_id
        unique_opps_dict = {o.opportunity_id: o for o in opp_list}
        unique_opps = list(unique_opps_dict.values())

        # 3. Map Candidate Skills for Fast Provenance Lookup
        cand_skill_map: dict[str, AssessedSkill] = {
            s.canonical_skill_id.strip().lower(): s for s in candidate.assessed_skills
        }
        cand_skill_name_map: dict[str, AssessedSkill] = {
            s.skill_name.strip().lower(): s for s in candidate.assessed_skills
        }

        # 4. Collect Requirements from Target Archetypes & Opportunities
        # Map: skill_key -> { 'reqs': list[OpportunitySkillRequirement], 'archetype_mandatory': bool, 'roles': set, 'opp_titles': set }
        skill_catalog: dict[str, dict] = {}

        # 4a. Harvest from Role Archetypes
        for role_name in evaluated_roles:
            matched_archetype = self._find_matching_archetype(role_name)
            if matched_archetype:
                for skill_name in matched_archetype.core_skills:
                    key = skill_name.strip().lower()
                    if key not in skill_catalog:
                        skill_catalog[key] = {
                            "canonical_id": f"archetype:{matched_archetype.canonical_occupation_code}:{key}",
                            "name": skill_name.title(),
                            "is_mandatory": True,
                            "expected_prof": 6.5,
                            "roles": set(),
                            "opp_titles": set(),
                            "is_unclear": False,
                        }
                    skill_catalog[key]["roles"].add(matched_archetype.role_title)

        # 4b. Harvest from Discovered Opportunities
        for opp in unique_opps:
            for req in opp.skill_requirements:
                key = req.skill_name.strip().lower()
                is_unclear = (
                    req.minimum_proficiency_expected is None
                    or req.minimum_proficiency_expected <= 1.0
                )
                if key not in skill_catalog:
                    skill_catalog[key] = {
                        "canonical_id": req.canonical_skill_id,
                        "name": req.skill_name,
                        "is_mandatory": req.is_mandatory,
                        "expected_prof": req.minimum_proficiency_expected or 5.0,
                        "roles": set(),
                        "opp_titles": set(),
                        "is_unclear": is_unclear,
                    }
                else:
                    if req.is_mandatory:
                        skill_catalog[key]["is_mandatory"] = True
                    skill_catalog[key]["expected_prof"] = max(
                        skill_catalog[key]["expected_prof"],
                        req.minimum_proficiency_expected or 5.0,
                    )
                    if is_unclear:
                        skill_catalog[key]["is_unclear"] = True
                skill_catalog[key]["opp_titles"].add(opp.title)

        # 5. Evaluate Gaps Across Catalog
        identified_gaps: list[CareerGapItem] = []

        for key, info in skill_catalog.items():
            canonical_id = info["canonical_id"]
            skill_name = info["name"]
            is_mand = info["is_mandatory"]
            exp_prof = info["expected_prof"]
            roles_list = sorted(list(info["roles"]))
            opps_list = sorted(list(info["opp_titles"]))
            is_unclear = info["is_unclear"]

            # Lookup candidate evidence
            cand_skill = cand_skill_map.get(key) or cand_skill_name_map.get(key)

            if cand_skill is None:
                # Situation 1: Skill is NOT DEMONSTRATED by available evidence
                # Determine importance
                importance = self._calculate_importance(is_mand, len(roles_list), len(opps_list))
                why_matters = (
                    f"Required or valued across {len(roles_list)} target role(s) "
                    f"and {len(opps_list)} active opportunity listing(s). "
                    "Corroborating this skill expands matching eligibility."
                )
                suggested_act = (
                    f"Develop a focused demonstration project or complete hands-on labs with {skill_name} "
                    "to establish initial verifiable provenance."
                )
                identified_gaps.append(
                    CareerGapItem(
                        canonical_skill_id=canonical_id,
                        skill_name=skill_name,
                        gap_status=GapStatus.NOT_DEMONSTRATED,
                        importance=importance,
                        is_mandatory=is_mand,
                        candidate_proficiency=None,
                        expected_proficiency=exp_prof,
                        confidence_score=None,
                        supporting_evidence=[],
                        why_it_matters=why_matters,
                        suggested_action=suggested_act,
                        relevant_target_roles=roles_list,
                        relevant_opportunities=opps_list,
                    )
                )

            elif is_unclear:
                # Situation 3: Job requirement itself is UNCLEAR or lacks explicit proficiency
                citations = [
                    EvidenceCitation(
                        evidence_id=ev.evidence_id,
                        source_type=ev.source_type,
                        source_uri=ev.source_uri,
                        snippet=ev.extracted_snippet,
                        verifiability_weight=ev.verifiability_weight,
                        observed_at=ev.observed_at,
                    )
                    for ev in cand_skill.evidence_records
                ]
                identified_gaps.append(
                    CareerGapItem(
                        canonical_skill_id=canonical_id,
                        skill_name=skill_name,
                        gap_status=GapStatus.REQUIREMENT_UNCLEAR,
                        importance=GapImportance.MEDIUM if is_mand else GapImportance.NICE_TO_HAVE,
                        is_mandatory=is_mand,
                        candidate_proficiency=cand_skill.proficiency_score,
                        expected_proficiency=exp_prof,
                        confidence_score=cand_skill.confidence_score,
                        supporting_evidence=citations,
                        why_it_matters=(
                            f"The proficiency expectation for '{skill_name}' is uncalibrated or unspecified "
                            "in opportunity descriptions, creating potential expectation mismatch."
                        ),
                        suggested_action=(
                            f"Prepare clarifying questions during interview stages regarding team expectations for {skill_name}."
                        ),
                        relevant_target_roles=roles_list,
                        relevant_opportunities=opps_list,
                    )
                )

            elif cand_skill.proficiency_score < exp_prof or cand_skill.confidence_score < 0.65:
                # Situation 2: Skill is DEMONSTRATED but proficiency is UNCERTAIN or below requirement
                citations = [
                    EvidenceCitation(
                        evidence_id=ev.evidence_id,
                        source_type=ev.source_type,
                        source_uri=ev.source_uri,
                        snippet=ev.extracted_snippet,
                        verifiability_weight=ev.verifiability_weight,
                        observed_at=ev.observed_at,
                    )
                    for ev in cand_skill.evidence_records
                ]
                importance = self._calculate_importance(is_mand, len(roles_list), len(opps_list))

                deficit_desc = (
                    f"Proficiency ({cand_skill.proficiency_score:.1f}/10) is below target ({exp_prof:.1f}/10)"
                    if cand_skill.proficiency_score < exp_prof
                    else f"Confidence score ({cand_skill.confidence_score:.2f}) indicates limited independent artifacts"
                )
                why_matters = (
                    f"Skill is evidenced in your profile, but {deficit_desc}. "
                    "Strengthening demonstrable artifacts will improve recommendation fit."
                )
                suggested_act = (
                    f"Enhance existing project artifacts with deeper {skill_name} features, "
                    "benchmarks, or automated tests to corroborate higher proficiency."
                )
                identified_gaps.append(
                    CareerGapItem(
                        canonical_skill_id=canonical_id,
                        skill_name=skill_name,
                        gap_status=GapStatus.PROFICIENCY_UNCERTAIN,
                        importance=importance,
                        is_mandatory=is_mand,
                        candidate_proficiency=cand_skill.proficiency_score,
                        expected_proficiency=exp_prof,
                        confidence_score=cand_skill.confidence_score,
                        supporting_evidence=citations,
                        why_it_matters=why_matters,
                        suggested_action=suggested_act,
                        relevant_target_roles=roles_list,
                        relevant_opportunities=opps_list,
                    )
                )

        # 6. Sort Gaps by Priority Deterministically
        priority_order = {
            GapImportance.CRITICAL: 0,
            GapImportance.HIGH: 1,
            GapImportance.MEDIUM: 2,
            GapImportance.NICE_TO_HAVE: 3,
        }
        status_order = {
            GapStatus.NOT_DEMONSTRATED: 0,
            GapStatus.PROFICIENCY_UNCERTAIN: 1,
            GapStatus.REQUIREMENT_UNCLEAR: 2,
        }
        identified_gaps.sort(
            key=lambda g: (
                priority_order.get(g.importance, 4),
                0 if g.is_mandatory else 1,
                status_order.get(g.gap_status, 3),
                -len(g.relevant_opportunities),
                g.skill_name.lower(),
            )
        )

        # 7. Generate Stage-Proportional Improvement Suggestions
        suggestions = self._synthesize_improvement_suggestions(candidate, identified_gaps, evaluated_roles)

        return CandidateCareerGapAnalysisResponse(
            user_id=candidate.user_id,
            analyzed_at=datetime.now(timezone.utc),
            target_roles_analyzed=evaluated_roles,
            total_opportunities_analyzed=len(unique_opps),
            total_gaps_identified=len(identified_gaps),
            prioritized_gaps=identified_gaps,
            suggested_improvements=suggestions,
        )

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _find_matching_archetype(self, role_title: str) -> Optional[RoleArchetype]:
        """Finds closest role archetype by title or synonyms."""
        norm_title = role_title.strip().lower()
        if norm_title in self._archetype_map:
            return self._archetype_map[norm_title]

        for archetype in self.archetypes:
            if norm_title in archetype.role_title.lower() or archetype.role_title.lower() in norm_title:
                return archetype
            for syn in archetype.synonyms:
                if norm_title in syn.lower() or syn.lower() in norm_title:
                    return archetype

        return None

    def _calculate_importance(self, is_mandatory: bool, role_count: int, opp_count: int) -> GapImportance:
        if is_mandatory and (role_count >= 1 or opp_count >= 2):
            return GapImportance.CRITICAL
        elif is_mandatory or opp_count >= 2:
            return GapImportance.HIGH
        elif role_count >= 1 or opp_count == 1:
            return GapImportance.MEDIUM
        return GapImportance.NICE_TO_HAVE

    def _synthesize_improvement_suggestions(
        self,
        candidate: CandidateCareerProfile,
        gaps: list[CareerGapItem],
        target_roles: list[str],
    ) -> list[CareerImprovementSuggestion]:
        """Generates realistic, stage-appropriate next steps without false promises."""
        suggestions: list[CareerImprovementSuggestion] = []

        # Determine candidate career stage
        total_exp = candidate.eligibility_constraints.total_full_time_experience_months
        if total_exp <= 24:
            stage_label = "Early Career / Junior"
        elif total_exp <= 60:
            stage_label = "Mid-Level Professional"
        else:
            stage_label = "Senior Professional"

        # Group top gaps by status
        not_evidenced_gaps = [g for g in gaps if g.gap_status == GapStatus.NOT_DEMONSTRATED][:4]
        uncertain_gaps = [g for g in gaps if g.gap_status == GapStatus.PROFICIENCY_UNCERTAIN][:4]

        # Suggestion 1: Portfolio demonstration for unevidenced critical skills
        if not_evidenced_gaps:
            top_skills = [g.skill_name for g in not_evidenced_gaps[:2]]
            action_type = ActionType.PORTFOLIO_BUILD if total_exp <= 24 else ActionType.PROJECT_ENHANCEMENT
            desc = (
                f"Build a focused, public GitHub repository demonstrating practical integration of {', '.join(top_skills)}. "
                "Include clean documentation, automated unit tests, and a README highlighting the problem solved. "
                "This creates verifiable, high-weight provenance for your candidate profile."
            )
            suggestions.append(
                CareerImprovementSuggestion(
                    suggestion_id=f"sug_{uuid.uuid4().hex[:8]}",
                    action_type=action_type,
                    title=f"Build Portfolio Artifact for {', '.join(top_skills)}",
                    description=desc,
                    proportional_stage=stage_label,
                    targeted_gaps=top_skills,
                    supported_roles=target_roles,
                )
            )

        # Suggestion 2: Deepening proficiency & evidence on existing skills
        if uncertain_gaps:
            unc_skills = [g.skill_name for g in uncertain_gaps[:2]]
            desc = (
                f"Your profile demonstrates exposure to {', '.join(unc_skills)}, but lacks depth or empirical verification. "
                "Add benchmark measurements, integration tests, or architectural documentation to an existing project "
                "to raise your verifiability weight and proficiency rating."
            )
            suggestions.append(
                CareerImprovementSuggestion(
                    suggestion_id=f"sug_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.EVIDENCE_COLLECTION,
                    title=f"Deepen Empirical Evidence for {', '.join(unc_skills)}",
                    description=desc,
                    proportional_stage=stage_label,
                    targeted_gaps=unc_skills,
                    supported_roles=target_roles,
                )
            )

        # Suggestion 3: Conceptual / Systems Architecture Study
        if len(not_evidenced_gaps) >= 3:
            study_skills = [g.skill_name for g in not_evidenced_gaps[2:4]]
            desc = (
                f"Study core architectural patterns, design trade-offs, and operational paradigms underlying {', '.join(study_skills)}. "
                "Prepare concise summary notes or system design diagrams to discuss during technical screens."
            )
            suggestions.append(
                CareerImprovementSuggestion(
                    suggestion_id=f"sug_{uuid.uuid4().hex[:8]}",
                    action_type=ActionType.CONCEPT_STUDY,
                    title=f"Architectural Deep-Dive on {', '.join(study_skills)}",
                    description=desc,
                    proportional_stage=stage_label,
                    targeted_gaps=study_skills,
                    supported_roles=target_roles,
                )
            )

        return suggestions

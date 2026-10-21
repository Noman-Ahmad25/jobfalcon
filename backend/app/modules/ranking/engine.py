from __future__ import annotations

from datetime import datetime, timezone
import math
import uuid
from typing import Any, Optional

from app.schemas.common import (
    DEGREE_HIERARCHY,
    CareerPathRelationship,
    DegreeLevel,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.eligibility import (
    EligibilityResult,
    EligibilityStatus,
)
from app.schemas.opportunity import (
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CareerPathNode,
)
from app.schemas.ranking import (
    DEFAULT_RANKING_WEIGHTS,
    EARLY_CAREER_WEIGHTS,
    EXPERIENCED_WEIGHTS,
    DimensionScoreBreakdown,
    RankedOpportunity,
    RankingDimension,
    RankingResponse,
    SkillGap,
    SkillMatchEvidence,
)


class CandidateJobRankingEngine:
    """Deterministic, evidence-grounded candidate-job fit scoring and ranking engine.

    Executes multi-dimensional scoring in pure Python deterministic code.
    Maintains strict separation between deterministic eligibility gating and ranking.
    """

    MODEL_VERSION = "jobfalcon-ranking-v1.0-deterministic"

    def __init__(
        self,
        default_weights: Optional[dict[RankingDimension, float]] = None,
    ) -> None:
        self._default_weights = (
            default_weights.copy() if default_weights else DEFAULT_RANKING_WEIGHTS.copy()
        )

    def evaluate_and_rank(
        self,
        candidate_profile: CandidateCareerProfile,
        opportunities: list[PolymorphicOpportunity],
        eligibility_results: Optional[list[EligibilityResult]] = None,
        weight_profile_name: str = "DEFAULT",
        custom_weights: Optional[dict[str, float]] = None,
        top_k: int = 10,
        include_ineligible_in_audit: bool = True,
    ) -> RankingResponse:
        """Evaluates, scores, and ranks opportunities for a given candidate profile."""
        start_time = datetime.now(timezone.utc)
        evaluation_id = str(uuid.uuid4())

        # 1. Resolve weight configuration
        resolved_weights = self._resolve_weights(weight_profile_name, custom_weights)

        # 2. Map eligibility results by opportunity_id
        elig_map: dict[str, EligibilityResult] = {}
        if eligibility_results:
            for er in eligibility_results:
                elig_map[er.opportunity_id] = er

        eligible_candidates: list[tuple[PolymorphicOpportunity, EligibilityResult]] = []
        ineligible_candidates: list[tuple[PolymorphicOpportunity, Optional[EligibilityResult]]] = []

        # 3. Segregate by deterministic eligibility invariant
        for opp in opportunities:
            er = elig_map.get(opp.opportunity_id)
            if er is not None:
                if er.is_eligible:
                    eligible_candidates.append((opp, er))
                else:
                    ineligible_candidates.append((opp, er))
            else:
                # If no explicit eligibility result provided, assume rankable with unverified caveat
                synthetic_er = EligibilityResult(
                    opportunity_id=opp.opportunity_id,
                    user_id=candidate_profile.user_id,
                    status=EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY,
                    is_eligible=True,
                    disqualification_reasons=[],
                    uncertainty_caveats=["UNCERT_ELIGIBILITY_GATE_NOT_PRE_EVALUATED"],
                    constraint_checks={},
                )
                eligible_candidates.append((opp, synthetic_er))

        # 4. Score each eligible opportunity across all 6 dimensions
        scored_recommendations: list[RankedOpportunity] = []
        for opp, er in eligible_candidates:
            ranked_opp = self._score_single_opportunity(
                candidate=candidate_profile,
                opportunity=opp,
                eligibility=er,
                weights=resolved_weights,
            )
            scored_recommendations.append(ranked_opp)

        # 5. Deterministic sorting and tie-breaking:
        # Primary: overall_fit_score (descending, 4 decimal places)
        # Secondary: skill alignment score (descending)
        # Tertiary: completeness score (descending)
        # Quaternary: opportunity_id (alphabetical ascending)
        scored_recommendations.sort(
            key=lambda r: (
                -round(r.overall_fit_score, 4),
                -round(r.dimension_scores[RankingDimension.SKILL_ALIGNMENT].raw_score, 4),
                -round(r.opportunity.completeness_score, 4),
                r.opportunity.opportunity_id,
            )
        )

        # Assign 1-based ranks
        for idx, rec in enumerate(scored_recommendations, start=1):
            rec.rank = idx

        # Apply top_k slicing
        top_recommendations = scored_recommendations[:top_k]

        # 6. Build excluded audit records
        excluded_audit: list[dict[str, Any]] = []
        if include_ineligible_in_audit:
            for opp, er in ineligible_candidates:
                reasons = er.disqualification_reasons if er else ["DISQ_UNSPECIFIED"]
                excluded_audit.append(
                    {
                        "opportunity_id": opp.opportunity_id,
                        "title": opp.title,
                        "company_name": opp.company_name,
                        "eligibility_status": er.status if er else "INELIGIBLE",
                        "disqualification_reasons": reasons,
                        "excluded_from_ranking": True,
                    }
                )

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0

        weights_str_dict = {dim.value: val for dim, val in resolved_weights.items()}

        return RankingResponse(
            evaluation_id=evaluation_id,
            candidate_id=candidate_profile.user_id,
            model_version=self.MODEL_VERSION,
            weight_profile_used=weight_profile_name,
            weights=weights_str_dict,
            total_candidates_evaluated=len(opportunities),
            total_eligible_ranked=len(scored_recommendations),
            total_ineligible_excluded=len(ineligible_candidates),
            ranked_recommendations=top_recommendations,
            excluded_ineligible=excluded_audit,
            execution_metadata={
                "duration_ms": duration_ms,
                "top_k_requested": top_k,
                "total_available_recommendations": len(scored_recommendations),
            },
        )

    # =========================================================================
    # SINGLE OPPORTUNITY SCORING PIPELINE
    # =========================================================================

    def _score_single_opportunity(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
        eligibility: EligibilityResult,
        weights: dict[RankingDimension, float],
    ) -> RankedOpportunity:
        """Scores an individual eligible opportunity across all 6 dimensions."""
        caveats = list(eligibility.uncertainty_caveats)

        # 1. Skill Alignment (S_skill)
        skill_score, matched_skills, missing_skills, skill_caveats = (
            self._compute_skill_alignment(candidate, opportunity)
        )
        caveats.extend(skill_caveats)

        # 2. Career Path / Role Alignment (S_career)
        career_score, career_rationale = self._compute_career_alignment(
            candidate, opportunity
        )

        # 3. Growth Potential (S_growth)
        growth_score, growth_skills, growth_rationale = (
            self._compute_growth_potential(
                candidate, opportunity, skill_score, matched_skills, missing_skills
            )
        )

        # 4. Market Relevance & Quality (S_market)
        market_score, market_rationale = self._compute_market_relevance(opportunity)

        # 5. Preference & Workplace Alignment (S_pref)
        pref_score, pref_rationale = self._compute_preference_fit(
            candidate, opportunity
        )

        # 6. Experience & Qualification Fit (S_qual)
        qual_score, qual_rationale = self._compute_qualification_fit(
            candidate, opportunity
        )

        # Build Dimension Breakdowns
        dims: dict[RankingDimension, DimensionScoreBreakdown] = {
            RankingDimension.SKILL_ALIGNMENT: DimensionScoreBreakdown(
                dimension=RankingDimension.SKILL_ALIGNMENT,
                raw_score=round(skill_score, 4),
                weight=round(weights[RankingDimension.SKILL_ALIGNMENT], 4),
                weighted_score=round(
                    skill_score * weights[RankingDimension.SKILL_ALIGNMENT], 4
                ),
                rationale=(
                    f"Matched {len(matched_skills)} skills with evidence confidence; "
                    f"{len(missing_skills)} unverified requirements."
                ),
                caveats_or_missing_data=skill_caveats,
            ),
            RankingDimension.CAREER_ALIGNMENT: DimensionScoreBreakdown(
                dimension=RankingDimension.CAREER_ALIGNMENT,
                raw_score=round(career_score, 4),
                weight=round(weights[RankingDimension.CAREER_ALIGNMENT], 4),
                weighted_score=round(
                    career_score * weights[RankingDimension.CAREER_ALIGNMENT], 4
                ),
                rationale=career_rationale,
                caveats_or_missing_data=[],
            ),
            RankingDimension.GROWTH_POTENTIAL: DimensionScoreBreakdown(
                dimension=RankingDimension.GROWTH_POTENTIAL,
                raw_score=round(growth_score, 4),
                weight=round(weights[RankingDimension.GROWTH_POTENTIAL], 4),
                weighted_score=round(
                    growth_score * weights[RankingDimension.GROWTH_POTENTIAL], 4
                ),
                rationale=growth_rationale,
                caveats_or_missing_data=[],
            ),
            RankingDimension.MARKET_RELEVANCE: DimensionScoreBreakdown(
                dimension=RankingDimension.MARKET_RELEVANCE,
                raw_score=round(market_score, 4),
                weight=round(weights[RankingDimension.MARKET_RELEVANCE], 4),
                weighted_score=round(
                    market_score * weights[RankingDimension.MARKET_RELEVANCE], 4
                ),
                rationale=market_rationale,
                caveats_or_missing_data=[],
            ),
            RankingDimension.PREFERENCE_FIT: DimensionScoreBreakdown(
                dimension=RankingDimension.PREFERENCE_FIT,
                raw_score=round(pref_score, 4),
                weight=round(weights[RankingDimension.PREFERENCE_FIT], 4),
                weighted_score=round(
                    pref_score * weights[RankingDimension.PREFERENCE_FIT], 4
                ),
                rationale=pref_rationale,
                caveats_or_missing_data=[],
            ),
            RankingDimension.QUALIFICATION_FIT: DimensionScoreBreakdown(
                dimension=RankingDimension.QUALIFICATION_FIT,
                raw_score=round(qual_score, 4),
                weight=round(weights[RankingDimension.QUALIFICATION_FIT], 4),
                weighted_score=round(
                    qual_score * weights[RankingDimension.QUALIFICATION_FIT], 4
                ),
                rationale=qual_rationale,
                caveats_or_missing_data=[],
            ),
        }

        # Calculate Total Weighted Fit Score
        overall_score = sum(d.weighted_score for d in dims.values())
        overall_score = max(0.0, min(1.0, overall_score))

        # Synthesize grounded natural-language explanation
        rationale_text, tradeoffs = self._synthesize_grounded_explanation(
            candidate=candidate,
            opportunity=opportunity,
            dims=dims,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            growth_skills=growth_skills,
            caveats=caveats,
        )

        cluster_id = opportunity.category_specific_attributes.get("cluster_id")
        cluster_size = opportunity.category_specific_attributes.get("cluster_size", 1)

        provenance = {
            "source_url": opportunity.source_url,
            "application_url": opportunity.category_specific_attributes.get(
                "application_url", opportunity.source_url
            ),
            "discovered_at": opportunity.discovered_at.isoformat(),
            "posted_at": opportunity.posted_at.isoformat(),
            "cluster_id": cluster_id,
            "cluster_size": cluster_size,
        }

        return RankedOpportunity(
            rank=1,  # temporary, will be assigned after full sorting
            overall_fit_score=round(overall_score, 4),
            opportunity=opportunity,
            eligibility_status=eligibility.status,
            is_eligible=eligibility.is_eligible,
            eligibility_caveats=sorted(list(set(caveats))),
            dimension_scores=dims,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            growth_skills=growth_skills,
            recommendation_rationale=rationale_text,
            key_tradeoffs_or_risks=tradeoffs,
            provenance_info=provenance,
        )

    # =========================================================================
    # DIMENSION 1: SKILL ALIGNMENT (S_skill)
    # =========================================================================

    def _compute_skill_alignment(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
    ) -> tuple[float, list[SkillMatchEvidence], list[SkillGap], list[str]]:
        """Evaluates verified evidence-backed skills against required and preferred qualifications."""
        requirements = opportunity.skill_requirements
        caveats: list[str] = []

        if not requirements:
            # Opportunity did not list discrete skill requirements
            return (
                0.70,
                [],
                [],
                ["UNCERT_NO_SKILL_REQUIREMENTS_SPECIFIED"],
            )

        # Index candidate skills by canonical_id and lower-cased skill_name
        cand_skill_map: dict[str, AssessedSkill] = {}
        for s in candidate.assessed_skills:
            cand_skill_map[s.canonical_skill_id.strip().lower()] = s
            cand_skill_map[s.skill_name.strip().lower()] = s

        matched_skills: list[SkillMatchEvidence] = []
        missing_skills: list[SkillGap] = []

        total_weight = 0.0
        weighted_match_sum = 0.0

        for req in requirements:
            req_weight = 2.0 if req.is_mandatory else 1.0
            total_weight += req_weight

            # Match lookup
            matched_cand_skill = cand_skill_map.get(
                req.canonical_skill_id.strip().lower()
            ) or cand_skill_map.get(req.skill_name.strip().lower())

            if matched_cand_skill is not None:
                P_u = matched_cand_skill.proficiency_score
                P_req = req.minimum_proficiency_expected
                C_u = matched_cand_skill.confidence_score

                # Proficiency ratio
                prof_ratio = min(1.0, P_u / max(1.0, P_req))
                match_quality = prof_ratio * C_u

                # Surplus bonus if candidate exceeds requirement
                if P_u > P_req:
                    surplus = min(0.10, ((P_u - P_req) / 10.0) * 0.10)
                    match_quality = min(1.0, match_quality + surplus)

                weighted_match_sum += req_weight * match_quality

                # Extract top 2 verbatim evidence snippets
                snippets = [
                    ev.extracted_snippet
                    for ev in matched_cand_skill.evidence_records[:2]
                ]

                matched_skills.append(
                    SkillMatchEvidence(
                        canonical_skill_id=req.canonical_skill_id,
                        skill_name=req.skill_name,
                        candidate_proficiency=P_u,
                        expected_proficiency=P_req,
                        confidence_score=C_u,
                        is_mandatory=req.is_mandatory,
                        evidence_snippets=snippets,
                        match_quality=round(match_quality, 4),
                    )
                )

                # If proficiency is below expected, also record deficit
                if P_u < P_req:
                    missing_skills.append(
                        SkillGap(
                            canonical_skill_id=req.canonical_skill_id,
                            skill_name=req.skill_name,
                            is_mandatory=req.is_mandatory,
                            expected_proficiency=P_req,
                            candidate_proficiency=P_u,
                            gap_type="PROFICIENCY_DEFICIT",
                        )
                    )
            else:
                # Skill not found in candidate profile
                # Missing mandatory is penalized; missing preferred has lower weight
                missing_skills.append(
                    SkillGap(
                        canonical_skill_id=req.canonical_skill_id,
                        skill_name=req.skill_name,
                        is_mandatory=req.is_mandatory,
                        expected_proficiency=req.minimum_proficiency_expected,
                        candidate_proficiency=None,
                        gap_type="MISSING_FROM_PROFILE",
                    )
                )

        raw_skill_score = (
            weighted_match_sum / total_weight if total_weight > 0.0 else 0.70
        )
        return (
            max(0.0, min(1.0, raw_skill_score)),
            matched_skills,
            missing_skills,
            caveats,
        )

    # =========================================================================
    # DIMENSION 2: CAREER PATH & ROLE ALIGNMENT (S_career)
    # =========================================================================

    def _compute_career_alignment(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
    ) -> tuple[float, str]:
        """Evaluates whether the opportunity matches target ambition vs adjacent role."""
        opp_code = opportunity.mapped_occupation_code.strip()
        opp_title_lower = opportunity.title.lower()

        # Check explicit target career paths
        for target in candidate.target_career_paths:
            if target.occupation_code.strip() == opp_code:
                return (
                    1.00,
                    f"Direct taxonomy match with target career ambition: '{target.title}'.",
                )
            if target.title.lower() in opp_title_lower:
                return (
                    0.95,
                    f"Strong title match with target career ambition: '{target.title}'.",
                )

        # Check adjacent career paths
        for adj in candidate.adjacent_career_paths:
            if adj.occupation_code.strip() == opp_code:
                similarity = max(0.60, min(0.95, adj.adjacency_similarity))
                return (
                    similarity,
                    f"Adjacent career path ('{adj.title}') with taxonomy similarity {similarity:.2f}.",
                )
            if adj.title.lower() in opp_title_lower:
                similarity = max(0.60, min(0.90, adj.adjacency_similarity))
                return (
                    similarity,
                    f"Adjacent career path title match ('{adj.title}') with similarity {similarity:.2f}.",
                )

        # Check current baseline role (lateral movement)
        if candidate.current_career_path:
            if candidate.current_career_path.occupation_code.strip() == opp_code:
                return (
                    0.65,
                    f"Lateral role matching current career baseline: '{candidate.current_career_path.title}'.",
                )

        # Fallback: check candidate preferred titles from eligibility constraints
        for target_title in candidate.eligibility_constraints.allowed_opportunity_categories:
            if str(target_title).lower() in opp_title_lower:
                return (0.75, "Partial title match with stated career preferences.")

        return (
            0.25,
            "Role title and occupation code differ from candidate's primary target career paths.",
        )

    # =========================================================================
    # DIMENSION 3: GROWTH POTENTIAL & ZPD (S_growth)
    # =========================================================================

    def _compute_growth_potential(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
        skill_score: float,
        matched_skills: list[SkillMatchEvidence],
        missing_skills: list[SkillGap],
    ) -> tuple[float, list[str], str]:
        """Calculates learning potential in candidate's Zone of Proximal Development."""
        total_reqs = len(opportunity.skill_requirements)
        if total_reqs == 0:
            return 0.50, [], "Growth potential unassessed (no requirements listed)."

        # Growth skills are those in the opportunity that the candidate can develop
        growth_skills = [gap.skill_name for gap in missing_skills]

        # Stretch ratio: fraction of skills candidate does not yet master
        stretch_ratio = len(missing_skills) / float(total_reqs)

        # Optimal ZPD Gaussian response curve around stretch_ratio = 0.30
        # (Candidate possesses ~70% core skills and has 30% learning stretch)
        zpd_peak = 0.30
        sigma = 0.20
        bell_factor = math.exp(-((stretch_ratio - zpd_peak) ** 2) / (2 * (sigma**2)))

        # Mandatory skill foundation check
        mandatory_reqs = [r for r in opportunity.skill_requirements if r.is_mandatory]
        matched_mandatory = [m for m in matched_skills if m.is_mandatory]
        mandatory_coverage = (
            len(matched_mandatory) / len(mandatory_reqs) if mandatory_reqs else 1.0
        )

        if mandatory_coverage < 0.40:
            # Candidate lacks fundamental prerequisite skills; high risk of overwhelm
            growth_score = max(0.15, bell_factor * 0.50)
            rationale = (
                f"High stretch ({stretch_ratio:.0%} new skills), but candidate currently lacks "
                f"core foundational requirements ({mandatory_coverage:.0%} mandatory covered)."
            )
        elif stretch_ratio < 0.10:
            # Near 100% mastery: great skill fit, but limited new learning potential
            growth_score = 0.40
            rationale = (
                "Comfortable mastery of nearly all requirements; provides immediate productivity "
                "with modest growth stretch."
            )
        elif 0.20 <= stretch_ratio <= 0.45:
            # Optimal Zone of Proximal Development
            growth_score = max(0.75, bell_factor)
            rationale = (
                f"Optimal Zone of Proximal Development: solid foundation with {len(missing_skills)} "
                f"expanding competencies ({', '.join(growth_skills[:3])})."
            )
        else:
            # Moderate stretch
            growth_score = max(0.35, bell_factor)
            rationale = (
                f"Noticeable learning curve with {len(missing_skills)} unverified skills to acquire."
            )

        return min(1.0, max(0.10, growth_score)), growth_skills, rationale

    # =========================================================================
    # DIMENSION 4: MARKET RELEVANCE & OPPORTUNITY QUALITY (S_market)
    # =========================================================================

    def _compute_market_relevance(
        self,
        opportunity: PolymorphicOpportunity,
    ) -> tuple[float, str]:
        """Evaluates source trust, domain verification, completeness, and freshness."""
        trust = opportunity.trust_score
        completeness = opportunity.completeness_score
        domain_verified = 1.0 if opportunity.company_domain_verified else 0.60

        # Recency decay: postings within 14 days receive 1.0; decaying over 60 days
        now = datetime.now(timezone.utc)
        age_days = max(
            0.0, (now - opportunity.posted_at).total_seconds() / 86400.0
        )
        recency = max(0.40, math.exp(-age_days / 45.0))

        score = (
            0.40 * trust
            + 0.30 * completeness
            + 0.15 * domain_verified
            + 0.15 * recency
        )

        score = max(0.0, min(1.0, score))
        rationale = (
            f"Source trust: {trust:.2f}, completeness: {completeness:.2f}, "
            f"domain verified: {opportunity.company_domain_verified}, age: {age_days:.0f} days."
        )
        return score, rationale

    # =========================================================================
    # DIMENSION 5: PREFERENCE & WORKPLACE ALIGNMENT (S_pref)
    # =========================================================================

    def _compute_preference_fit(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
    ) -> tuple[float, str]:
        """Evaluates alignment with candidate's soft location, work-mode, and category preferences."""
        constraints = candidate.eligibility_constraints
        rules = opportunity.eligibility_rules

        # Work Mode Alignment
        if rules.work_mode == WorkMode.REMOTE:
            mode_score = 1.00
        elif rules.work_mode in constraints.allowed_work_modes:
            mode_score = 0.90
        else:
            mode_score = 0.40

        # Geographic Location Alignment
        opp_locations = rules.location_city_country
        cand_locations = constraints.preferred_locations

        if rules.work_mode == WorkMode.REMOTE:
            loc_score = 1.00
        elif not cand_locations:
            # Candidate is completely flexible geographically
            loc_score = 0.90
        else:
            # Check for city/country overlap
            match = False
            for c_loc in cand_locations:
                for o_loc in opp_locations:
                    if (
                        c_loc.lower() in o_loc.lower()
                        or o_loc.lower() in c_loc.lower()
                    ):
                        match = True
                        break
                if match:
                    break
            loc_score = 1.00 if match else 0.65

        # Opportunity Category Alignment
        if rules.opportunity_category in constraints.allowed_opportunity_categories:
            cat_score = 1.00
        else:
            cat_score = 0.50

        pref_score = 0.45 * mode_score + 0.40 * loc_score + 0.15 * cat_score
        pref_score = max(0.0, min(1.0, pref_score))

        rationale = (
            f"Work mode ({rules.work_mode}): {mode_score:.2f}; "
            f"Location ({', '.join(opp_locations) or 'Remote'}): {loc_score:.2f}; "
            f"Category ({rules.opportunity_category}): {cat_score:.2f}."
        )
        return pref_score, rationale

    # =========================================================================
    # DIMENSION 6: EXPERIENCE & QUALIFICATION FIT (S_qual)
    # =========================================================================

    def _compute_qualification_fit(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
    ) -> tuple[float, str]:
        """Evaluates experience seniority bounds and academic degree hierarchy alignment."""
        cand_exp = (
            candidate.eligibility_constraints.total_full_time_experience_months
        )
        min_exp = opportunity.eligibility_rules.min_experience_months
        max_exp = opportunity.eligibility_rules.max_experience_months

        # Experience fit
        if cand_exp >= min_exp:
            if max_exp is None or cand_exp <= max_exp:
                exp_score = 1.00
            else:
                # Overqualified / oversenior
                excess = cand_exp - max_exp
                exp_score = max(0.40, 1.0 - (excess / float(max_exp + 12)))
        else:
            # Below minimum (should be caught by eligibility, but handled gracefully)
            exp_score = max(0.20, cand_exp / float(max(1, min_exp)))

        # Degree fit
        cand_degree = candidate.eligibility_constraints.highest_degree_level
        min_degree = opportunity.eligibility_rules.minimum_degree_required

        cand_deg_rank = DEGREE_HIERARCHY.get(cand_degree, 0)
        min_deg_rank = DEGREE_HIERARCHY.get(min_degree, 0)

        if min_deg_rank == 0 or cand_deg_rank == min_deg_rank:
            deg_score = 0.95
        elif cand_deg_rank > min_deg_rank:
            deg_score = 1.00
        else:
            deg_score = max(0.30, cand_deg_rank / float(min_deg_rank))

        qual_score = 0.60 * exp_score + 0.40 * deg_score
        qual_score = max(0.0, min(1.0, qual_score))

        rationale = (
            f"Experience: {cand_exp}mo vs required {min_exp}mo-{max_exp or 'any'}mo (score {exp_score:.2f}); "
            f"Degree: {cand_degree} vs minimum {min_degree} (score {deg_score:.2f})."
        )
        return qual_score, rationale

    # =========================================================================
    # GROUNDED EXPLANATION SYNTHESIS
    # =========================================================================

    def _synthesize_grounded_explanation(
        self,
        candidate: CandidateCareerProfile,
        opportunity: PolymorphicOpportunity,
        dims: dict[RankingDimension, DimensionScoreBreakdown],
        matched_skills: list[SkillMatchEvidence],
        missing_skills: list[SkillGap],
        growth_skills: list[str],
        caveats: list[str],
    ) -> tuple[str, list[str]]:
        """Synthesizes transparent, grounded summary and highlights key tradeoffs."""
        tradeoffs: list[str] = []

        # Find top 2 highest dimension contributors
        sorted_dims = sorted(
            dims.values(), key=lambda d: d.weighted_score, reverse=True
        )
        top_driver = sorted_dims[0].dimension.value.replace("_", " ").title()

        # Skill summary
        top_matched_names = [m.skill_name for m in matched_skills[:3]]
        skills_summary = (
            f"Strong verified match in {', '.join(top_matched_names)}."
            if top_matched_names
            else "Limited skill overlap."
        )

        # Tradeoffs / risks
        if missing_skills:
            missing_names = [g.skill_name for g in missing_skills[:3]]
            tradeoffs.append(
                f"Candidate profile does not corroborate: {', '.join(missing_names)}"
            )

        if caveats:
            for cav in caveats:
                if "DEADLINE" in cav:
                    tradeoffs.append(
                        "Application deadline is rolling or unspecified; early application recommended"
                    )
                elif "LOCATION" in cav:
                    tradeoffs.append(
                        "Location details require verification for hybrid commuting"
                    )

        if not opportunity.company_domain_verified:
            tradeoffs.append(
                "Company email domain has not been independently verified"
            )

        explanation_parts = [
            f"Recommended primarily due to strong {top_driver}.",
            skills_summary,
            dims[RankingDimension.GROWTH_POTENTIAL].rationale,
        ]

        if caveats:
            explanation_parts.append(
                f"Note {len(caveats)} pending verification items."
            )

        explanation_text = " ".join(explanation_parts)
        return explanation_text, tradeoffs

    # =========================================================================
    # WEIGHT PROFILE RESOLUTION
    # =========================================================================

    def _resolve_weights(
        self,
        profile_name: str,
        custom_weights: Optional[dict[str, float]],
    ) -> dict[RankingDimension, float]:
        """Resolves and normalizes weights to sum strictly to 1.00."""
        if custom_weights:
            raw_weights: dict[RankingDimension, float] = {}
            for dim in RankingDimension:
                val = custom_weights.get(dim.value, self._default_weights[dim])
                raw_weights[dim] = max(0.0, float(val))
        elif profile_name == "EARLY_CAREER":
            raw_weights = EARLY_CAREER_WEIGHTS.copy()
        elif profile_name == "EXPERIENCED":
            raw_weights = EXPERIENCED_WEIGHTS.copy()
        else:
            raw_weights = self._default_weights.copy()

        # Normalize to 1.00
        total = sum(raw_weights.values())
        if total <= 0.0:
            return DEFAULT_RANKING_WEIGHTS.copy()

        return {dim: val / total for dim, val in raw_weights.items()}

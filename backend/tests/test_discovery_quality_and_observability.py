from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pytest

from app.modules.discovery.connectors.web_search.classifier import (
    ClassificationResult,
    JobSearchResultClassifier,
    extract_company_from_title,
)
from app.modules.discovery.connectors.web_search.providers import RawSearchResult
from app.modules.orchestration.agent import DiscoveryAgentDecisionMaker
from app.modules.orchestration.graph import AdaptiveDiscoveryGraphBuilder
from app.modules.orchestration.state import AdaptiveDiscoveryGraphState
from app.modules.ranking.engine import CandidateJobRankingEngine
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import (
    DiscoverySearchQuery,
    OpportunityRejectionCode,
    RoleMappingTarget,
)
from app.schemas.evidence import EvidenceRecord, EvidenceSourceType
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.orchestration import (
    CoverageAssessment,
    SearchStrategy,
    TerminationReason,
    WorkflowStage,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)
from app.modules.discovery.connectors.base import create_normalized_opportunity


# =============================================================================
# 1. COLLECTION PAGE AND AGGREGATOR DETECTION
# =============================================================================

def test_collection_page_rejection_by_title():
    """Validates that multi-vacancy lists, aggregator roundups, and directory titles are rejected with COLLECTION_PAGE."""
    query = DiscoverySearchQuery(
        query_id="q1",
        role_title="Python Developer",
        query_string="Python Developer jobs",
        category=OpportunityCategory.FULL_TIME_JOB,
    )

    test_cases = [
        "200 Python Jobs in London (with Salaries)",
        "Top 50 Software Developer Jobs in Europe",
        "Jobs in Middle East - 1500 Openings",
        "Career Opportunities in San Francisco",
        "Browse all Tech Jobs - Global Directory",
        "Hundreds of Python Vacancies across Tech",
    ]

    for title in test_cases:
        raw = RawSearchResult(
            title=title,
            url="https://jobaggregator.org/directory/listings/123",
            snippet="View our directory of open positions and apply to hundreds of roles.",
        )
        res = JobSearchResultClassifier.evaluate(raw, query)
        assert not res.is_job, f"Expected '{title}' to be rejected as collection page"
        assert res.rejection_code == OpportunityRejectionCode.COLLECTION_PAGE, (
            f"Expected COLLECTION_PAGE for '{title}', got {res.rejection_code}"
        )


def test_collection_page_rejection_by_url():
    """Validates that search queries, category filters, and directory URLs are rejected with COLLECTION_PAGE."""
    query = DiscoverySearchQuery(
        query_id="q2",
        role_title="Backend Engineer",
        query_string="Backend Engineer jobs",
        category=OpportunityCategory.FULL_TIME_JOB,
    )

    test_cases = [
        "https://jobs.examplecorp.com/jobs?q=backend+engineer&loc=remote",
        "https://aggregator.net/search?keyword=python&category=software",
        "https://recruitment.com/browse/engineering-roles",
        "https://board.org/jobs-in-california",
        "https://careers.techboard.com/all-jobs",
    ]

    for url in test_cases:
        raw = RawSearchResult(
            title="Backend Engineer",
            url=url,
            snippet="Apply to open backend positions.",
        )
        res = JobSearchResultClassifier.evaluate(raw, query)
        assert not res.is_job, f"Expected URL '{url}' to be rejected as collection page"
        assert res.rejection_code == OpportunityRejectionCode.COLLECTION_PAGE, (
            f"Expected COLLECTION_PAGE for '{url}', got {res.rejection_code}"
        )


def test_individual_job_posting_acceptance():
    """Validates that genuine individual postings on direct ATS domains or career routes are accepted."""
    query = DiscoverySearchQuery(
        query_id="q3",
        role_title="Backend Engineer",
        query_string="Backend Engineer jobs",
        category=OpportunityCategory.FULL_TIME_JOB,
    )

    valid_postings = [
        (
            "Senior Backend Engineer at Acme Corp",
            "https://boards.greenhouse.io/acmecorp/jobs/54321",
            "We are looking for a Senior Backend Engineer to join our distributed platform team.",
        ),
        (
            "Software Engineer - Platform",
            "https://jobs.lever.co/stripe/a1b2c3d4",
            "Build reliable payment rails using Python and Go. Apply directly on our Lever requisition.",
        ),
        (
            "Backend Engineer - Core Services",
            "https://careers.datadoghq.com/posting/98765",
            "Design and maintain telemetry pipelines. Full-time position in New York or Remote.",
        ),
    ]

    for title, url, snippet in valid_postings:
        raw = RawSearchResult(title=title, url=url, snippet=snippet)
        res = JobSearchResultClassifier.evaluate(raw, query)
        assert res.is_job, f"Expected '{title}' ({url}) to be accepted as genuine posting"
        assert res.rejection_code is None


# =============================================================================
# 2. EMPLOYER VS DISCOVERY SOURCE SEPARATION
# =============================================================================

def test_employer_separation_from_job_boards():
    """Validates that job boards (Indeed, LinkedIn, Glassdoor, Monster) are NEVER extracted as the employer."""
    cases = [
        # (title, url, expected_employer)
        ("Senior Python Engineer - Stripe - Indeed", "https://www.indeed.com/viewjob?jk=123", "Stripe"),
        ("Backend Developer at Datadog | LinkedIn", "https://www.linkedin.com/jobs/view/456", "Datadog"),
        ("Staff Engineer at Snowflake - Glassdoor", "https://www.glassdoor.com/job-listing/789", "Snowflake"),
        ("Python Developer - Indeed", "https://www.indeed.com/viewjob?jk=999", "Unstated Employer"),
        ("Software Engineer", "https://www.linkedin.com/jobs/view/111", "Unstated Employer"),
        ("Backend Engineer", "https://careers.google.com/jobs/results/222", "Google"),
    ]

    for title, url, expected_company in cases:
        company = extract_company_from_title(title, url)
        assert company.lower() != "indeed", f"Indeed should never be company name for {title}"
        assert company.lower() != "linkedin", f"LinkedIn should never be company name for {title}"
        assert company.lower() != "glassdoor", f"Glassdoor should never be company name for {title}"
        assert company == expected_company, f"For '{title}' ({url}): expected '{expected_company}', got '{company}'"


# =============================================================================
# 3. SKILL-HEAVY MATCHING & EXPERIENCE MISMATCH RANKING
# =============================================================================

def test_fresh_grad_experience_mismatch_ranking_penalty():
    """Validates the core principle:
    'A demonstrated skill is evidence of capability, not proof of years of professional experience.'
    A fresh graduate with high skill overlap must not rank senior roles (10+ years) above suitable junior roles.
    """
    # Candidate: Fresh Graduate with 0 months experience
    now = datetime.now(timezone.utc)
    ev = EvidenceRecord(
        evidence_id="ev_01",
        source_type=EvidenceSourceType.ACADEMIC_TRANSCRIPT,
        extracted_snippet="Completed course projects and laboratory exercises.",
        observed_at=now,
        verifiability_weight=0.90,
    )

    candidate = CandidateCareerProfile(
        user_id="user_fresh_grad",
        display_name="Taylor NewGrad",
        profile_version=1,
        overall_profile_confidence=0.85,
        target_career_paths=[
            CareerPathNode(
                title="Software Engineer",
                occupation_code="15-1252.00",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled=False,
            requires_visa_sponsorship=False,
            total_full_time_experience_months=0,  # 0 months
        ),
        assessed_skills=[
            AssessedSkill(
                canonical_skill_id="skill_python",
                skill_name="Python",
                proficiency_score=8.5,
                confidence_score=0.90,
                evidence_records=[ev],
            ),
            AssessedSkill(
                canonical_skill_id="skill_sql",
                skill_name="SQL",
                proficiency_score=8.0,
                confidence_score=0.85,
                evidence_records=[ev],
            ),
            AssessedSkill(
                canonical_skill_id="skill_aws",
                skill_name="AWS",
                proficiency_score=7.5,
                confidence_score=0.80,
                evidence_records=[ev],
            ),
            AssessedSkill(
                canonical_skill_id="skill_docker",
                skill_name="Docker",
                proficiency_score=7.0,
                confidence_score=0.80,
                evidence_records=[ev],
            ),
        ],
    )

    future_deadline = datetime(2028, 1, 1, tzinfo=timezone.utc)

    # Opportunity 1: Junior Software Engineer (0 months required, 2 skills match: Python, SQL)
    junior_opp = create_normalized_opportunity(
        title="Junior Software Engineer",
        company_name="Apex Tech",
        description="Entry-level software engineering role for new graduates. Python and SQL foundational work.",
        source_url="https://apex.com/jobs/junior-swe",
        source_system="ats_direct",
        source_job_id="apex_junior_1",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        min_experience_months=0,
        application_deadline=future_deadline,
        skill_requirements=[
            OpportunitySkillRequirement(canonical_skill_id="skill_python", skill_name="Python", is_mandatory=True, minimum_proficiency_expected=6.0),
            OpportunitySkillRequirement(canonical_skill_id="skill_sql", skill_name="SQL", is_mandatory=True, minimum_proficiency_expected=5.0),
        ],
        mapped_occupation_code="15-1252.00",
        is_verified_posting=True,
    )

    # Opportunity 2: Principal / Senior Staff Engineer (120 months = 10 years required, 100% skill match: Python, SQL, AWS, Docker)
    senior_opp = create_normalized_opportunity(
        title="Principal Staff Backend Engineer",
        company_name="MegaScale Corp",
        description="Lead architectural decisions for 10+ years experienced veterans. Requires Python, SQL, AWS, Docker.",
        source_url="https://megascale.com/jobs/staff-architect",
        source_system="ats_direct",
        source_job_id="megascale_staff_1",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        min_experience_months=120,  # 10 years!
        application_deadline=future_deadline,
        skill_requirements=[
            OpportunitySkillRequirement(canonical_skill_id="skill_python", skill_name="Python", is_mandatory=True, minimum_proficiency_expected=8.0),
            OpportunitySkillRequirement(canonical_skill_id="skill_sql", skill_name="SQL", is_mandatory=True, minimum_proficiency_expected=7.0),
            OpportunitySkillRequirement(canonical_skill_id="skill_aws", skill_name="AWS", is_mandatory=True, minimum_proficiency_expected=7.0),
            OpportunitySkillRequirement(canonical_skill_id="skill_docker", skill_name="Docker", is_mandatory=True, minimum_proficiency_expected=7.0),
        ],
        mapped_occupation_code="15-1252.00",
        is_verified_posting=True,
    )

    engine = CandidateJobRankingEngine()
    result = engine.evaluate_and_rank(
        candidate_profile=candidate,
        opportunities=[junior_opp, senior_opp],
    )

    assert len(result.ranked_recommendations) >= 1
    ranked_titles = [r.opportunity.title for r in result.ranked_recommendations]

    # The Junior role MUST rank first for a fresh graduate!
    assert ranked_titles[0] == "Junior Software Engineer", (
        f"Fresh graduate ranking error: Expected 'Junior Software Engineer' to rank #1, but got {ranked_titles}"
    )

    # Check that if Senior role was evaluated, its score was penalized with EXPERIENCE_MISMATCH caveat
    if len(result.ranked_recommendations) > 1:
        senior_ranked = next(r for r in result.ranked_recommendations if "Principal" in r.opportunity.title)
        junior_ranked = next(r for r in result.ranked_recommendations if "Junior" in r.opportunity.title)

        assert junior_ranked.overall_fit_score > senior_ranked.overall_fit_score, (
            f"Junior score ({junior_ranked.overall_fit_score}) must strictly exceed Senior score ({senior_ranked.overall_fit_score})"
        )
        assert any("EXPERIENCE_MISMATCH" in c or "SENIORITY_MISMATCH" in c for c in senior_ranked.eligibility_caveats), (
            f"Expected EXPERIENCE_MISMATCH caveat on senior role, got: {senior_ranked.eligibility_caveats}"
        )


# =============================================================================
# 4. STRICT TOOL BUDGET ACCOUNTING (NEVER EXCEEDS MAX)
# =============================================================================

def test_tool_budget_accounting_and_skipped_queries():
    """Validates that LangGraph discovery worker strictly enforces tool budget and reports accurate telemetry.
    Never produces impossible states like 10/8 calls.
    """
    async def _run():
        builder = AdaptiveDiscoveryGraphBuilder()

        # Create 5 pending queries for 2 connectors (10 potential tool calls)
        queries = [
            DiscoverySearchQuery(
                query_id=f"q_{i}",
                role_title="Software Engineer",
                query_string=f"Software Engineer query {i}",
                category=OpportunityCategory.FULL_TIME_JOB,
            )
            for i in range(5)
        ]

        strategy = SearchStrategy(
            strategy_summary="Test strategy",
            target_role_priorities=["Software Engineer"],
            target_coverage_goal=3,
            selected_connector_ids=["web_search", "ats_career_pages"],
            initial_queries=queries,
        )

        # Set strict budget of 4 tool calls
        state: AdaptiveDiscoveryGraphState = {
            "workflow_id": "test_budget_run",
            "candidate_id": "test_cand",
            "pending_queries": queries,
            "search_strategy": strategy,
            "tool_call_count": 0,
            "max_tool_calls": 4,  # Cap at 4!
            "iteration": 1,
            "max_iterations": 2,
            "executed_query_hashes": [],
        }

        result = await builder.discovery_worker_node(state)

        # Invariant: tool_call_count must be <= max_tool_calls
        assert result["tool_call_count"] <= 4, (
            f"Tool call budget exceeded! Expected <= 4, got {result['tool_call_count']}"
        )

        # Telemetry check: BUDGET_CAP_REACHED event emitted with skipped calls
        events = result["timeline_events"]
        cap_event = next((e for e in events if e.event_type == "BUDGET_CAP_REACHED"), None)
        assert cap_event is not None, "Expected BUDGET_CAP_REACHED event when budget was exhausted"
        assert "skipped" in cap_event.summary.lower()
        assert cap_event.details["tool_call_count"] == 4
        assert cap_event.details["skipped_calls"] > 0

    asyncio.run(_run())


# =============================================================================
# 5. ADAPTIVE DISCOVERY QUALITY SIGNALS
# =============================================================================

def test_adaptive_coverage_decision_quality_signals():
    """Validates that coverage assessment evaluates authentic verified counts and duplicate rate."""
    maker = DiscoveryAgentDecisionMaker()

    candidate = CandidateCareerProfile(
        user_id="user_q",
        display_name="Quality Candidate",
        profile_version=1,
        overall_profile_confidence=0.85,
        target_career_paths=[
            CareerPathNode(
                title="Backend Engineer",
                occupation_code="15-1252.00",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            allowed_work_modes=[WorkMode.REMOTE],
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled=False,
            requires_visa_sponsorship=False,
            total_full_time_experience_months=24,
        ),
        assessed_skills=[],
    )

    strategy = SearchStrategy(
        strategy_summary="Quality discovery plan",
        target_role_priorities=["Backend Engineer"],
        target_coverage_goal=2,
        selected_connector_ids=["web_search"],
        initial_queries=[],
    )

    future_deadline = datetime(2028, 1, 1, tzinfo=timezone.utc)
    verified_opp_1 = create_normalized_opportunity(
        title="Backend Engineer",
        company_name="Acme Corp",
        description="Python backend role.",
        source_url="https://acme.greenhouse.io/jobs/1",
        source_system="ats_direct",
        source_job_id="acme_1",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        application_deadline=future_deadline,
        is_verified_posting=True,
    )
    verified_opp_2 = create_normalized_opportunity(
        title="Backend Engineer",
        company_name="Stripe",
        description="Platform engineering.",
        source_url="https://stripe.lever.co/jobs/2",
        source_system="ats_direct",
        source_job_id="stripe_2",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        application_deadline=future_deadline,
        is_verified_posting=True,
    )

    from app.schemas.eligibility import EligibilityResult, EligibilityStatus
    elig_results = [
        EligibilityResult(opportunity_id=verified_opp_1.opportunity_id, user_id="user_q", status=EligibilityStatus.ELIGIBLE, is_eligible=True),
        EligibilityResult(opportunity_id=verified_opp_2.opportunity_id, user_id="user_q", status=EligibilityStatus.ELIGIBLE, is_eligible=True),
    ]

    assessment, adaptation = maker.assess_coverage_and_decide_adaptation(
        profile=candidate,
        strategy=strategy,
        target_roles=[],
        adjacent_roles=[],
        canonical_opportunities=[verified_opp_1, verified_opp_2],
        eligibility_results=elig_results,
        iteration=1,
        max_iterations=3,
        executed_query_hashes=set(),
    )

    assert assessment.is_coverage_sufficient is True
    assert assessment.recommended_action == "STOP"
    assert assessment.verified_opportunity_count == 2
    assert "verified authentic" in assessment.quality_summary
    assert adaptation is None

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
import pytest

from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
    InMemoryRecommendationRepository,
)
from app.modules.discovery.connectors.ats_career_page import CompanyCareerPageConnector
from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.discovery.connectors.india_jobs import IndiaJobsMCPConnector
from app.modules.discovery.connectors.jobspy import JobSpyMCPConnector
from app.modules.discovery.connectors.parsing_utils import (
    determine_work_mode,
    extract_experience_months,
    extract_skills_from_text,
    strip_html_tags,
)
from app.modules.discovery.connectors.web_search import WebSearchConnector
from app.modules.discovery.role_mapper import map_profile_to_target_roles
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.orchestration.workflow import AdaptiveDiscoveryWorkflow
from app.modules.ranking.engine import CandidateJobRankingEngine
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import (
    ConnectorStatus,
    DiscoverySearchQuery,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import OpportunitySkillRequirement
from app.schemas.orchestration import (
    AdaptiveDiscoveryRequest,
    WorkflowStage,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def sample_senior_profile() -> CandidateCareerProfile:
    """Fixture representing an experienced full-stack / backend software engineer."""
    ev = EvidenceRecord(
        evidence_id="ev-agent-1",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Architected distributed Python FastAPI microservices and PostgreSQL databases handling 25,000 req/min.",
        observed_at="2026-01-10T10:00:00Z",
        verifiability_weight=0.90,
    )

    skills = [
        AssessedSkill(
            canonical_skill_id="esco:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.90,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:fastapi",
            skill_name="FastAPI",
            proficiency_score=8.0,
            confidence_score=0.88,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:postgresql",
            skill_name="PostgreSQL",
            proficiency_score=7.5,
            confidence_score=0.85,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:docker",
            skill_name="Docker",
            proficiency_score=7.0,
            confidence_score=0.80,
            evidence_records=[ev],
        ),
        AssessedSkill(
            canonical_skill_id="esco:typescript",
            skill_name="TypeScript",
            proficiency_score=7.0,
            confidence_score=0.80,
            evidence_records=[ev],
        ),
    ]

    target = CareerPathNode(
        occupation_code="15-1252.00",
        title="Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
        missing_core_skill_ids=[],
    )

    eligibility = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        expected_graduation_date=None,
        total_full_time_experience_months=48,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, US", "Remote"],
    )

    return CandidateCareerProfile(
        user_id="usr-senior-dev-10",
        profile_version=1,
        assessed_skills=skills,
        current_career_path=None,
        target_career_paths=[target],
        adjacent_career_paths=[],
        eligibility_constraints=eligibility,
        overall_profile_confidence=0.92,
    )


# ==============================================================================
# 1. Parsing Utilities Tests
# ==============================================================================


def test_strip_html_tags_removes_scripts_and_noise() -> None:
    noisy_html = """
    <div>
        <script>alert('malicious')</script>
        <style>.job { color: red; }</style>
        <h2>About The Role &amp; Responsibilities</h2>
        <p>We are seeking a <strong>Senior Software Engineer</strong> to join our team.</p>
        <ul>
            <li>Build REST APIs with FastAPI</li>
            <li>Optimize PostgreSQL queries</li>
        </ul>
    </div>
    """
    cleaned = strip_html_tags(noisy_html)
    assert "alert" not in cleaned
    assert "color: red" not in cleaned
    assert "About The Role & Responsibilities" in cleaned
    assert "Senior Software Engineer" in cleaned
    assert "FastAPI" in cleaned
    assert "PostgreSQL" in cleaned


def test_extract_skills_from_text_matches_canonical_variants() -> None:
    text = (
        "Requirements: 4+ years of hands-on experience with Python3 and Postgres. "
        "Must know React.js, Typescript, and Docker. Familiarity with AWS and K8s is a plus."
    )
    skills = extract_skills_from_text(text)
    names = {s.skill_name for s in skills}
    assert "Python" in names
    assert "PostgreSQL" in names
    assert "React" in names
    assert "TypeScript" in names
    assert "Docker" in names
    assert "AWS" in names
    assert "Kubernetes" in names


def test_extract_experience_months_handles_ranges_and_titles() -> None:
    assert extract_experience_months("Requires 3-5 years of engineering experience") == 36
    assert extract_experience_months("At least 5+ years building scalable systems") == 60
    assert extract_experience_months("Requires 2 years experience", title="Software Engineering Intern") == 0
    assert extract_experience_months("Exciting role for an experienced builder", title="Senior Backend Engineer") == 48


def test_determine_work_mode_detects_modes() -> None:
    assert determine_work_mode("Remote - US") == WorkMode.REMOTE
    assert determine_work_mode("London, UK", workplace_type="hybrid") == WorkMode.HYBRID
    assert determine_work_mode("New York, NY", workplace_type="on-site") == WorkMode.ON_SITE


# ==============================================================================
# 2. Connector Health and Honest Status Verification
# ==============================================================================


def test_connector_health_honest_reporting() -> None:
    async def _run() -> None:
        # 1. WebSearch in live mode honestly reports MOCKED_FALLBACK because no SearXNG/Google credentials exist
        web = WebSearchConnector(mock_mode=False)
        web_health = await web.check_health()
        assert web_health.status == ConnectorStatus.MOCKED_FALLBACK
        assert web_health.is_mock_fallback is True
        assert "No external search gateway credentials configured" in web_health.details.get("note", "")

        # 2. India Jobs MCP in live mode honestly reports UNAVAILABLE_MISSING_BINARY
        india = IndiaJobsMCPConnector(mock_mode=False)
        india_health = await india.check_health()
        assert india_health.status == ConnectorStatus.UNAVAILABLE_MISSING_BINARY
        assert india_health.is_mock_fallback is False

        # 3. JobSpy in live mode reports CONNECTED because python-jobspy is installed in venv
        jobspy = JobSpyMCPConnector(mock_mode=False)
        jobspy_health = await jobspy.check_health()
        assert jobspy_health.status == ConnectorStatus.CONNECTED
        assert jobspy_health.is_mock_fallback is False

        # 4. ATS connector in mock mode reports MOCKED_FALLBACK
        ats_mock = CompanyCareerPageConnector(mock_mode=True)
        ats_health = await ats_mock.check_health()
        assert ats_health.status == ConnectorStatus.MOCKED_FALLBACK
        assert ats_health.is_mock_fallback is True

    asyncio.run(_run())


# ==============================================================================
# 3. Real Recorded ATS Payload Normalization
# ==============================================================================


def test_ats_recorded_payload_normalization() -> None:
    """Verifies that actual Greenhouse and Ashby JSON structures parse cleanly into PolymorphicOpportunity."""
    gh_job = {
        "id": 6136160004,
        "title": "Account Executive, Commercial",
        "absolute_url": "https://job-boards.greenhouse.io/vercel/jobs/6136160004",
        "location": {"name": "Hybrid - London"},
        "content": "<p>Vercel is looking for builders. Experience with React and TypeScript is preferred.</p>",
    }

    clean_desc = strip_html_tags(gh_job["content"])
    skills = extract_skills_from_text(clean_desc)
    work_mode = determine_work_mode(gh_job["location"]["name"])

    opp = create_normalized_opportunity(
        title=gh_job["title"],
        company_name="Vercel",
        description=clean_desc,
        source_url=gh_job["absolute_url"],
        source_system="ats_greenhouse",
        source_job_id=str(gh_job["id"]),
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["GB", "US"],
        work_mode=work_mode,
        skill_requirements=skills,
        category_specific_attributes={"is_live_retrieval": True},
    )

    assert opp.opportunity_id is not None
    assert opp.company_name == "Vercel"
    assert opp.source_url.startswith("https://job-boards.greenhouse.io")
    assert opp.eligibility_rules.work_mode == WorkMode.HYBRID
    assert len(opp.minhash_signature_hex) == 64
    assert opp.category_specific_attributes["is_live_retrieval"] is True
    assert any(s.skill_name in ("React", "TypeScript") for s in opp.skill_requirements)


# ==============================================================================
# 4. End-to-End Workflow with Multi-Dimensional Ranking
# ==============================================================================


def test_end_to_end_adaptive_discovery_with_ranking(sample_senior_profile: CandidateCareerProfile) -> None:
    """Executes the full pipeline: Profile -> Role Mapping -> Search -> Dedup -> Eligibility -> Ranking -> Persistence."""
    async def _run() -> None:
        profile_repo = InMemoryCandidateProfileRepository()
        opp_repo = InMemoryOpportunityRepository()
        cluster_repo = InMemoryDuplicateClusterRepository()
        rec_repo = InMemoryRecommendationRepository()

        profile_repo.save(sample_senior_profile)

        workflow = AdaptiveDiscoveryWorkflow(
            opp_repo=opp_repo,
            cluster_repo=cluster_repo,
            profile_repo=profile_repo,
            rec_repo=rec_repo,
        )

        request = AdaptiveDiscoveryRequest(
            user_id=sample_senior_profile.user_id,
            target_coverage_goal=3,
            max_iterations=2,
            enable_live_discovery=False,
            rank_recommendations=True,
            weight_profile_name="EXPERIENCED",
            persist_to_repository=True,
        )

        response = await workflow.run(request)

        # 1. Workflow completed successfully
        assert response.workflow_id.startswith("wf-")
        assert response.candidate_id == sample_senior_profile.user_id
        assert response.total_discovered_raw > 0
        assert response.canonical_count > 0

        # 2. Deterministic Eligibility evaluated
        assert len(response.eligibility_results) == response.canonical_count
        assert len(response.eligible_opportunities) > 0
        assert (response.eligible_count + response.uncertain_count) > 0

        # 3. Multi-Dimensional Recommendations populated
        assert response.recommendations is not None
        recs = response.recommendations
        assert recs.total_eligible_ranked == len(response.eligible_opportunities)
        assert len(recs.ranked_recommendations) > 0

        # 4. Recommendation scores are well-formed and ordered
        top_rec = recs.ranked_recommendations[0]
        assert 0.0 <= top_rec.overall_fit_score <= 1.0
        assert top_rec.rank == 1
        assert "SKILL_ALIGNMENT" in top_rec.dimension_scores
        assert "CAREER_ALIGNMENT" in top_rec.dimension_scores
        assert "GROWTH_POTENTIAL" in top_rec.dimension_scores
        assert "MARKET_RELEVANCE" in top_rec.dimension_scores
        assert "PREFERENCE_FIT" in top_rec.dimension_scores
        assert "QUALIFICATION_FIT" in top_rec.dimension_scores

        # Verify score descending order
        for idx in range(len(recs.ranked_recommendations) - 1):
            assert recs.ranked_recommendations[idx].overall_fit_score >= recs.ranked_recommendations[idx + 1].overall_fit_score

        # 5. Timeline includes RANKING stage
        stages = [event.stage for event in response.timeline_events]
        assert WorkflowStage.INITIALIZING in stages
        assert WorkflowStage.STRATEGY_FORMULATION in stages
        assert WorkflowStage.SEARCHING in stages
        assert WorkflowStage.RANKING in stages
        assert WorkflowStage.FINALIZING in stages
        assert WorkflowStage.COMPLETED in stages

        # 6. Persistence verified
        saved_rec = rec_repo.get_latest_evaluation(sample_senior_profile.user_id)
        assert saved_rec is not None
        assert saved_rec.evaluation_id == recs.evaluation_id

    asyncio.run(_run())


# ==============================================================================
# 5. Real Data Ranking Score Differentiation
# ==============================================================================


def test_real_data_ranking_score_differentiation(sample_senior_profile: CandidateCareerProfile) -> None:
    """Verifies that ranking produces meaningful, differentiated scores across realistic opportunities."""
    now = datetime.now(timezone.utc)

    # Opportunity A: Strong match (Senior Backend, Python, PostgreSQL, Docker)
    opp_a = create_normalized_opportunity(
        title="Senior Backend Software Engineer",
        company_name="Cloud Infrastructure Co",
        description="Looking for Senior Python developer with PostgreSQL and Docker experience. Remote.",
        source_url="https://example.com/jobs/backend-sr",
        source_system="ats_greenhouse",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        min_experience_months=36,
        work_mode=WorkMode.REMOTE,
        skill_requirements=[
            OpportunitySkillRequirement(canonical_skill_id="esco:python", skill_name="Python", is_mandatory=True, minimum_proficiency_expected=7.0),
            OpportunitySkillRequirement(canonical_skill_id="esco:postgresql", skill_name="PostgreSQL", is_mandatory=True, minimum_proficiency_expected=6.5),
            OpportunitySkillRequirement(canonical_skill_id="esco:docker", skill_name="Docker", is_mandatory=False, minimum_proficiency_expected=5.0),
        ],
        mapped_occupation_code="15-1252.00",
        posted_at=now,
    )

    # Opportunity B: Stretch role (Senior ML Engineer with PyTorch, Machine Learning)
    opp_b = create_normalized_opportunity(
        title="Senior Machine Learning Engineer",
        company_name="AI Research Labs",
        description="Build LLM inference pipelines with Python, PyTorch, and CUDA.",
        source_url="https://example.com/jobs/ml-sr",
        source_system="ats_greenhouse",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        min_experience_months=48,
        work_mode=WorkMode.REMOTE,
        skill_requirements=[
            OpportunitySkillRequirement(canonical_skill_id="esco:python", skill_name="Python", is_mandatory=True, minimum_proficiency_expected=8.0),
            OpportunitySkillRequirement(canonical_skill_id="esco:pytorch", skill_name="PyTorch", is_mandatory=True, minimum_proficiency_expected=7.0),
            OpportunitySkillRequirement(canonical_skill_id="esco:machine_learning", skill_name="Machine Learning", is_mandatory=True, minimum_proficiency_expected=7.0),
        ],
        mapped_occupation_code="15-1251.00",
        posted_at=now,
    )

    # Opportunity C: Ineligible role (requires Active Student status for internship)
    opp_c = create_normalized_opportunity(
        title="Software Engineering Summer Intern",
        company_name="Tech Incubator",
        description="Internship for active university students.",
        source_url="https://example.com/jobs/intern-swe",
        source_system="ats_greenhouse",
        category=OpportunityCategory.INTERNSHIP,
        eligible_country_codes=["US"],
        requires_active_student_status=True,
        min_experience_months=0,
        work_mode=WorkMode.REMOTE,
        mapped_occupation_code="15-1252.00",
        posted_at=now,
    )

    engine = CandidateJobRankingEngine()
    eligibility_results = [
        evaluate_eligibility(sample_senior_profile, opp_a),
        evaluate_eligibility(sample_senior_profile, opp_b),
        evaluate_eligibility(sample_senior_profile, opp_c),
    ]

    response = engine.evaluate_and_rank(
        candidate_profile=sample_senior_profile,
        opportunities=[opp_a, opp_b, opp_c],
        eligibility_results=eligibility_results,
        weight_profile_name="EXPERIENCED",
    )

    # Ineligible role C must be strictly excluded from recommendations
    assert response.total_eligible_ranked == 2
    assert response.total_ineligible_excluded == 1
    assert len(response.ranked_recommendations) == 2

    # Opportunity A must score higher than Opportunity B (due to strong skill match)
    rec_a = next(r for r in response.ranked_recommendations if r.opportunity.company_name == "Cloud Infrastructure Co")
    rec_b = next(r for r in response.ranked_recommendations if r.opportunity.company_name == "AI Research Labs")

    assert rec_a.overall_fit_score > rec_b.overall_fit_score
    assert rec_a.dimension_scores["SKILL_ALIGNMENT"].raw_score > rec_b.dimension_scores["SKILL_ALIGNMENT"].raw_score
    # Opportunity B must have a growth explanation identifying missing skills (PyTorch, Machine Learning)
    assert len(rec_b.missing_skills) > 0
    missing_names = {s.skill_name for s in rec_b.missing_skills}
    assert "PyTorch" in missing_names

from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest

from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteMarketReportRepository,
    SQLiteOpportunityRepository,
)
from app.main import app
from app.modules.market.aggregator import (
    compute_sample_confidence_tier,
    filter_opportunities_for_market_scope,
    synthesize_market_report,
)
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.market import (
    MarketResearchReportRecord,
    SampleConfidenceTier,
)
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)


@pytest.fixture
def test_client():
    return TestClient(app)


def make_test_opportunity(
    opp_id: str,
    title: str,
    country: str,
    skills: list[str],
    work_mode: WorkMode = WorkMode.REMOTE,
    min_exp: int = 12,
    company: str = "FalconTech",
) -> PolymorphicOpportunity:
    rules = OpportunityEligibilityRules(
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=[country],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=min_exp,
        work_mode=work_mode,
        location_city_country=[f"City, {country}"],
    )
    skill_reqs = [
        OpportunitySkillRequirement(
            canonical_skill_id=f"esco:skill:{s.lower()}",
            skill_name=s,
            is_mandatory=(idx == 0),  # First skill is mandatory
            source_snippet=f"Requires {s}",
        )
        for idx, s in enumerate(skills)
    ]
    return PolymorphicOpportunity(
        opportunity_id=opp_id,
        minhash_signature_hex="1234567890abcdef",
        title=title,
        company_name=company,
        mapped_occupation_code="2512.1",
        opportunity_category=OpportunityCategory.FULL_TIME_JOB,
        sanitized_summary=f"Job for {title}",
        source_url=f"https://example.com/job/{opp_id}",
        posted_at=datetime.now(timezone.utc),
        completeness_score=0.9,
        trust_score=0.95,
        eligibility_rules=rules,
        skill_requirements=skill_reqs,
    )


# =====================================================================
# 1. CONFIDENCE TIER THRESHOLD TESTS
# =====================================================================


def test_sample_confidence_tier_boundaries():
    assert compute_sample_confidence_tier(0) == SampleConfidenceTier.EMPTY
    assert compute_sample_confidence_tier(1) == SampleConfidenceTier.EMERGING
    assert compute_sample_confidence_tier(4) == SampleConfidenceTier.EMERGING
    assert compute_sample_confidence_tier(5) == SampleConfidenceTier.DIRECTIONAL
    assert compute_sample_confidence_tier(14) == SampleConfidenceTier.DIRECTIONAL
    assert compute_sample_confidence_tier(15) == SampleConfidenceTier.MODERATE
    assert compute_sample_confidence_tier(29) == SampleConfidenceTier.MODERATE
    assert compute_sample_confidence_tier(30) == SampleConfidenceTier.HIGH
    assert compute_sample_confidence_tier(100) == SampleConfidenceTier.HIGH


# =====================================================================
# 2. GEOGRAPHIC AND ROLE FILTERING TESTS (NO US ASSUMPTION)
# =====================================================================


def test_market_filtering_candidate_specific_geography():
    opp_in_1 = make_test_opportunity("opp_in_1", "Backend Engineer", "IN", ["Python", "FastAPI"])
    opp_in_2 = make_test_opportunity("opp_in_2", "Backend Engineer", "IN", ["Python", "Docker"])
    opp_us = make_test_opportunity("opp_us_1", "Backend Engineer", "US", ["Go", "Kubernetes"])
    opp_de = make_test_opportunity("opp_de_1", "Backend Engineer", "DE", ["Java", "Spring"])

    all_opps = [opp_in_1, opp_in_2, opp_us, opp_de]

    # Filter for India
    in_results = filter_opportunities_for_market_scope(all_opps, role_title="Backend Engineer", country_code="IN")
    assert len(in_results) == 2
    assert all("IN" in o.eligibility_rules.eligible_country_codes for o in in_results)

    # Filter for Germany
    de_results = filter_opportunities_for_market_scope(all_opps, role_title="Backend Engineer", country_code="DE")
    assert len(de_results) == 1
    assert de_results[0].opportunity_id == "opp_de_1"


# =====================================================================
# 3. SYNTHESIS AND CORE VS PREFERRED SKILLS
# =====================================================================


def test_market_report_synthesis_and_skill_partition():
    opps = [
        make_test_opportunity(f"opp_{i}", "AI Engineer", "IN", ["Python", "PyTorch", "Docker"], company=f"Employer_{i%3}")
        for i in range(16)  # N=16 -> MODERATE tier
    ]

    report = synthesize_market_report(
        opportunities=opps,
        role_title="AI Engineer",
        country_code="IN",
        career_track="TECHNICAL",
    )

    assert report.sample_size == 16
    assert report.sample_confidence_tier == SampleConfidenceTier.MODERATE
    assert report.country_code == "IN"
    assert report.unique_employers_count == 3
    assert len(report.core_skills) > 0

    # Python was first skill in each opp, so mandatory -> classified as core
    core_names = [s.skill_name for s in report.core_skills]
    assert "Python" in core_names

    # Check work mode distribution
    assert report.work_mode_distribution[WorkMode.REMOTE.value] == 16

    # Check synthesis markdown contains accurate provenance notes
    assert "N=16" in report.synthesis_markdown
    assert "AI Engineer" in report.synthesis_markdown


# =====================================================================
# 4. REPOSITORY PERSISTENCE AND API ENDPOINTS
# =====================================================================


def test_market_report_persistence():
    repo = SQLiteMarketReportRepository()
    opps = [make_test_opportunity(f"opp_c_{i}", "Data Scientist", "CA", ["Python", "SQL"]) for i in range(6)]

    report = synthesize_market_report(opps, role_title="Data Scientist", country_code="CA")
    repo.save_report(report)

    cached = repo.get_report("Data Scientist", "CA")
    assert cached is not None
    assert cached.sample_size == 6
    assert cached.sample_confidence_tier == SampleConfidenceTier.DIRECTIONAL

    recent_reports = repo.list_reports(limit=5)
    assert len(recent_reports) >= 1
    assert any(r.role_title == "Data Scientist" for r in recent_reports)


def test_market_api_endpoint(test_client):
    opp_repo = SQLiteOpportunityRepository()
    for i in range(5):
        opp_repo.save(make_test_opportunity(f"api_opp_{i}_{int(datetime.now().timestamp()*1000)}", "Security Engineer", "GB", ["Python", "Linux"]))

    resp = test_client.get("/api/v1/market/report?role_title=Security+Engineer&country_code=GB&force_refresh=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["role_title"] == "Security Engineer"
    assert data["country_code"] == "GB"
    assert data["sample_size"] >= 5
    assert data["sample_confidence_tier"] in ("DIRECTIONAL", "MODERATE", "HIGH")
    assert "synthesis_markdown" in data

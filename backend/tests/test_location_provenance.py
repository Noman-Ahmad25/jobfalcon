from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryOpportunityRepository,
)
from app.modules.deduplication.service import deduplicate_opportunities
from app.modules.discovery.connectors.ats_career_page import CompanyCareerPageConnector
from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.discovery.connectors.mcp.normalizer import JobSpyMCPNormalizer
from app.modules.discovery.connectors.parsing_utils import (
    format_opportunity_location,
    parse_location_and_work_mode,
)
from app.modules.discovery.connectors.web_search.classifier import (
    normalize_search_result_to_opportunity,
)
from app.modules.discovery.connectors.web_search.connector import WebSearchConnector
from app.modules.discovery.connectors.web_search.providers import RawSearchResult
from app.modules.discovery.role_mapper import generate_discovery_query_plan
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.ingestion.importer import OpportunityImporter
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import DiscoverySearchQuery
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


def _make_candidate_in_satna() -> CandidateCareerProfile:
    """Builds a candidate profile anchored in Satna, Madhya Pradesh, India."""
    ev = EvidenceRecord(
        evidence_id="ev-satna-01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Full stack engineer specializing in Python and React.",
        observed_at="2026-02-01T00:00:00Z",
        verifiability_weight=0.9,
    )
    target_path = CareerPathNode(
        occupation_code="15-1252.00",
        title="Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
        missing_core_skill_ids=[],
    )
    return CandidateCareerProfile(
        user_id="candidate-satna-test",
        profile_version=1,
        display_name="Devendra Sharma",
        headline="Full Stack Engineer",
        location="Satna, Madhya Pradesh, India",
        assessed_skills=[
            AssessedSkill(
                canonical_skill_id="esco:python",
                skill_name="Python",
                proficiency_score=8.5,
                confidence_score=0.95,
                evidence_records=[ev],
            ),
            AssessedSkill(
                canonical_skill_id="esco:fastapi",
                skill_name="FastAPI",
                proficiency_score=8.0,
                confidence_score=0.90,
                evidence_records=[ev],
            ),
        ],
        current_career_path=None,
        target_career_paths=[target_path],
        adjacent_career_paths=[],
        eligibility_constraints=CandidateEligibilityProfile(
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled_student=False,
            requires_visa_sponsorship=False,
            authorized_country_codes=["IN"],
            preferred_locations=["Satna, Madhya Pradesh, India"],
            allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ON_SITE],
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            total_full_time_experience_months=24,
        ),
        overall_profile_confidence=0.90,
    )


# --------------------------------------------------------------------------
# Scenario 1: Candidate is in Satna, Job Listing is in Bengaluru
# --------------------------------------------------------------------------
def test_scenario_1_candidate_satna_job_in_bengaluru():
    """Candidate is in Satna, but job listing specifies Bengaluru.
    Opportunity location MUST be Bengaluru, never candidate's location.
    """
    candidate = _make_candidate_in_satna()
    query = DiscoverySearchQuery(
        query_id="q_test_1",
        role_title="Backend Software Engineer",
        query_string="Backend Software Engineer Python Satna",
        expanded_keywords=["Python", "FastAPI"],
        category=OpportunityCategory.FULL_TIME_JOB,
        work_modes=candidate.eligibility_constraints.allowed_work_modes,
        target_locations=candidate.eligibility_constraints.preferred_locations,
        target_country_codes=["IN"],
        seniority_level="MID",
    )

    # 1. Parsing utility test
    locs, mode = parse_location_and_work_mode(
        raw_location="Bengaluru, Karnataka, India",
        text="Acme Corp is hiring a Backend Engineer in Bengaluru, India.",
        title="Backend Software Engineer",
    )
    assert locs == ["Bengaluru, Karnataka, India"]
    assert "Satna" not in str(locs)
    assert format_opportunity_location(mode, locs) == "Bengaluru, Karnataka, India"

    # 2. Web search classifier test with Bengaluru snippet
    raw_result = RawSearchResult(
        title="Backend Software Engineer - Acme Corp - Bengaluru, India",
        snippet="Join Acme Corp in Bengaluru, India. We are hiring a Backend Engineer with Python and FastAPI experience.",
        url="https://boards.greenhouse.io/acme/jobs/12345",
        engine="searxng",
    )
    opp = normalize_search_result_to_opportunity(raw_result, query)
    assert opp is not None
    assert "Satna" not in opp.eligibility_rules.location_city_country
    assert "Satna" not in opp.display_location
    assert "Bengaluru" in opp.display_location


# --------------------------------------------------------------------------
# Scenario 2: Candidate is in Satna, Listing is Explicitly Remote Across India
# --------------------------------------------------------------------------
def test_scenario_2_candidate_satna_listing_remote_india():
    """Candidate is in Satna, listing is explicitly remote across India.
    Opportunity location MUST display `Remote — India`.
    """
    candidate = _make_candidate_in_satna()
    query = DiscoverySearchQuery(
        query_id="q_test_2",
        role_title="Software Engineer",
        query_string="Software Engineer Remote",
        expanded_keywords=["Python"],
        category=OpportunityCategory.FULL_TIME_JOB,
        work_modes=[WorkMode.REMOTE],
        target_locations=candidate.eligibility_constraints.preferred_locations,
        target_country_codes=["IN"],
        seniority_level="MID",
    )

    # 1. JobSpy MCP normalization of "Remote - India"
    raw_mcp_job = {
        "title": "Software Engineer (Remote)",
        "company": "CloudTech",
        "location": "Remote - India",
        "is_remote": True,
        "description": "We are seeking a Python Engineer. This position is 100% remote within India.",
        "site": "indeed",
    }
    opp = JobSpyMCPNormalizer.normalize_job_record(raw_mcp_job, query)
    assert opp.eligibility_rules.work_mode == WorkMode.REMOTE
    assert opp.eligibility_rules.location_city_country == ["India"]
    assert opp.display_location == "Remote — India"
    assert "Satna" not in opp.display_location


# --------------------------------------------------------------------------
# Scenario 3: Candidate is in Satna, Listing Has No Location Specified
# --------------------------------------------------------------------------
def test_scenario_3_candidate_satna_listing_has_no_location():
    """Candidate is in Satna, listing has no location specified.
    Opportunity location MUST be empty and display `Location not specified`.
    Must NOT fall back to Satna.
    """
    candidate = _make_candidate_in_satna()
    query = DiscoverySearchQuery(
        query_id="q_test_3",
        role_title="Backend Developer",
        query_string="Backend Developer Python Satna",
        expanded_keywords=["Python", "PostgreSQL"],
        category=OpportunityCategory.FULL_TIME_JOB,
        work_modes=candidate.eligibility_constraints.allowed_work_modes,
        target_locations=candidate.eligibility_constraints.preferred_locations,
        target_country_codes=["IN"],
        seniority_level="MID",
    )

    raw_result = RawSearchResult(
        title="Backend Developer Opening",
        snippet="We are seeking an experienced Backend Developer proficient with Python, FastAPI, and PostgreSQL.",
        url="https://jobs.example.com/posting/9999",
        engine="searxng",
    )
    opp = normalize_search_result_to_opportunity(raw_result, query)
    assert opp is not None
    # Verify no location leaked
    assert opp.eligibility_rules.location_city_country == []
    assert "Satna" not in opp.eligibility_rules.location_city_country
    assert opp.display_location == "Location not specified"


# --------------------------------------------------------------------------
# Scenario 4: Query Contains Satna, Returned Listing Has No Location
# --------------------------------------------------------------------------
def test_scenario_4_query_has_satna_listing_has_no_location():
    """Search query contains Satna in target_locations, but listing has no location.
    Opportunity location MUST NOT contain Satna or any query location.
    """
    query = DiscoverySearchQuery(
        query_id="q_satna_query",
        role_title="Full Stack Engineer",
        query_string="Full Stack Engineer Satna",
        expanded_keywords=["Python", "React"],
        category=OpportunityCategory.FULL_TIME_JOB,
        work_modes=[WorkMode.ON_SITE],
        target_locations=["Satna, Madhya Pradesh, India", "Satna"],
        target_country_codes=["IN"],
        seniority_level="MID",
    )

    # Web search
    raw_res = RawSearchResult(
        title="Full Stack Engineer - Tech Innovations",
        snippet="Immediate opening for Full Stack Engineer with Python, React, and PostgreSQL background.",
        url="https://jobs.example.com/apply/888",
        engine="google",
    )
    opp_web = normalize_search_result_to_opportunity(raw_res, query)
    assert opp_web is not None
    assert opp_web.eligibility_rules.location_city_country == []
    assert "Satna" not in opp_web.eligibility_rules.location_city_country
    assert opp_web.display_location == "Location not specified"

    # MCP normalizer with missing location
    raw_job = {
        "title": "Full Stack Engineer",
        "company": "Innovations Corp",
        "location": "",
        "is_remote": False,
        "description": "Building next-gen applications with Python and React.",
        "site": "linkedin",
    }
    opp_mcp = JobSpyMCPNormalizer.normalize_job_record(raw_job, query)
    assert opp_mcp.eligibility_rules.location_city_country == []
    assert "Satna" not in opp_mcp.eligibility_rules.location_city_country
    assert opp_mcp.display_location == "Location not specified"


# --------------------------------------------------------------------------
# Scenario 5: Candidate Location Does Not Overwrite Opportunity on Dedup / Persistence
# --------------------------------------------------------------------------
def test_scenario_5_deduplication_and_persistence_preserve_opportunity_location():
    """Verifies candidate location never overwrites an existing opportunity location
    during MinHash LSH deduplication or repository persistence.
    """
    candidate = _make_candidate_in_satna()
    opp_repo = InMemoryOpportunityRepository()
    cluster_repo = InMemoryDuplicateClusterRepository()

    # Pre-existing opportunity in Bengaluru
    opp = create_normalized_opportunity(
        title="Platform Software Engineer",
        company_name="Zomato Tech",
        description="Core infrastructure team in Bengaluru building high-throughput systems.",
        source_url="https://zomato.careers/jobs/infra-01",
        source_system="ats_greenhouse",
        source_job_id="zomato_01",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["IN"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=12,
        work_mode=WorkMode.HYBRID,
        location_city_country=["Bengaluru, India"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                is_mandatory=True,
                minimum_proficiency_expected=5.0,
            )
        ],
        posted_at=datetime.now(timezone.utc),
    )

    assert opp.display_location == "Bengaluru, India (Hybrid)"
    assert "Satna" not in opp.eligibility_rules.location_city_country

    # Run deduplication
    dedup_result = deduplicate_opportunities([opp])
    assert len(dedup_result.canonical_opportunities) == 1
    canonical_opp = dedup_result.canonical_opportunities[0]
    assert canonical_opp.eligibility_rules.location_city_country == ["Bengaluru, India"]
    assert canonical_opp.display_location == "Bengaluru, India (Hybrid)"
    assert "Satna" not in canonical_opp.display_location

    # Run persistence via OpportunityImporter
    importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)
    persisted = importer.import_opportunities([canonical_opp], source_system="test_pipeline")
    assert persisted.canonical_opportunities == 1

    stored = opp_repo.get(canonical_opp.opportunity_id)
    assert stored is not None
    assert stored.eligibility_rules.location_city_country == ["Bengaluru, India"]
    assert stored.display_location == "Bengaluru, India (Hybrid)"
    assert "Satna" not in stored.eligibility_rules.location_city_country

    # Evaluate eligibility with candidate in Satna:
    # Because role is HYBRID in Bengaluru, candidate in Satna fails or is uncertain on location
    elig_result = evaluate_eligibility(candidate, stored)
    loc_check = elig_result.constraint_checks.get("geographic_location")
    assert loc_check is not None
    # Satna does not match Bengaluru
    assert loc_check.status.value in ("FAILED", "UNCERTAIN")
    # And opportunity location remains Bengaluru!
    assert stored.eligibility_rules.location_city_country == ["Bengaluru, India"]


# --------------------------------------------------------------------------
# Scenario 6: All 5 Canonical Location Normalization Cases
# --------------------------------------------------------------------------
def test_scenario_6_all_five_canonical_location_display_cases():
    """Verifies the 5 canonical normalization behaviors specified in the prompt:
    1. Explicit city/location in listing -> Display that location.
    2. Explicit remote position with specified geographic scope -> Display `Remote — [scope]`.
    3. Explicitly remote without geographic scope -> Display `Remote`.
    4. Hybrid position -> Display actual location and hybrid designation.
    5. Location absent or unverifiable -> Display `Location not specified`.
    """
    # 1. Explicit city/location
    assert format_opportunity_location(WorkMode.ON_SITE, ["Bengaluru, India"]) == "Bengaluru, India"
    assert format_opportunity_location(WorkMode.ON_SITE, ["San Francisco, CA"]) == "San Francisco, CA"
    assert format_opportunity_location(WorkMode.ON_SITE, ["London, UK"]) == "London, UK"

    # 2. Explicit remote position with geographic scope
    assert format_opportunity_location(WorkMode.REMOTE, ["India"]) == "Remote — India"
    assert format_opportunity_location(WorkMode.REMOTE, ["US"]) == "Remote — US"
    assert format_opportunity_location(WorkMode.REMOTE, ["United States"]) == "Remote — United States"
    assert format_opportunity_location(WorkMode.REMOTE, ["EMEA"]) == "Remote — EMEA"
    assert format_opportunity_location(WorkMode.REMOTE, ["Remote - India"]) == "Remote — India"
    assert format_opportunity_location(WorkMode.REMOTE, ["Remote (US only)"]) == "Remote — US"

    # 3. Explicitly remote without geographic scope
    assert format_opportunity_location(WorkMode.REMOTE, []) == "Remote"
    assert format_opportunity_location(WorkMode.REMOTE, ["Remote"]) == "Remote"
    assert format_opportunity_location(WorkMode.REMOTE, ["Worldwide"]) == "Remote"
    assert format_opportunity_location(WorkMode.REMOTE, ["Global"]) == "Remote"

    # 4. Hybrid position
    assert format_opportunity_location(WorkMode.HYBRID, ["Bengaluru, India"]) == "Bengaluru, India (Hybrid)"
    assert format_opportunity_location(WorkMode.HYBRID, ["San Francisco, CA"]) == "San Francisco, CA (Hybrid)"
    assert format_opportunity_location(WorkMode.HYBRID, ["Bengaluru, India (Hybrid)"]) == "Bengaluru, India (Hybrid)"
    assert format_opportunity_location(WorkMode.HYBRID, []) == "Hybrid (Location not specified)"

    # 5. Location absent or unverifiable
    assert format_opportunity_location(WorkMode.ON_SITE, []) == "Location not specified"
    assert format_opportunity_location(WorkMode.ON_SITE, [""]) == "Location not specified"


# --------------------------------------------------------------------------
# Scenario 7: Never Infer "Remote — India" Just Because Candidate is in India
# --------------------------------------------------------------------------
def test_scenario_7_never_infer_remote_india_from_candidate():
    """If listing is remote without geographic scope, but candidate is in India,
    the opportunity location MUST display `Remote`, NOT `Remote — India`.
    """
    candidate = _make_candidate_in_satna()
    query = DiscoverySearchQuery(
        query_id="q_remote_test",
        role_title="Senior Python Engineer",
        query_string="Senior Python Engineer Remote",
        expanded_keywords=["Python"],
        category=OpportunityCategory.FULL_TIME_JOB,
        work_modes=[WorkMode.REMOTE],
        target_locations=candidate.eligibility_constraints.preferred_locations,
        target_country_codes=candidate.eligibility_constraints.authorized_country_codes,
        seniority_level="SENIOR",
    )

    # Raw listing that is simply "Remote" without specifying India
    raw_result = RawSearchResult(
        title="Remote Senior Python Engineer - Global SaaS",
        snippet="We are a fully distributed remote engineering team looking for a Senior Python Engineer.",
        url="https://jobs.example.com/careers/remote-py",
        engine="searxng",
    )
    opp = normalize_search_result_to_opportunity(raw_result, query)
    assert opp is not None
    assert opp.eligibility_rules.work_mode == WorkMode.REMOTE
    # Must NOT infer India as remote scope
    assert opp.eligibility_rules.location_city_country == []
    assert opp.display_location == "Remote"
    assert opp.display_location != "Remote — India"
    assert "Satna" not in opp.display_location


# --------------------------------------------------------------------------
# Scenario 8: Candidate Location Used for Query Expansion, Isolated from Opportunity
# --------------------------------------------------------------------------
def test_scenario_8_candidate_location_query_expansion_isolation():
    """Candidate location is correctly used for query generation and geographic expansion,
    but never leaks into the generated opportunity.
    """
    candidate = _make_candidate_in_satna()
    query_plan = generate_discovery_query_plan(candidate)
    assert len(query_plan.all_queries) > 0

    # Queries correctly contain candidate's preferred location for search targeting
    has_satna_in_query = any("Satna" in q.query_string or "Satna, Madhya Pradesh, India" in q.target_locations for q in query_plan.all_queries)
    assert has_satna_in_query is True

    # But when a connector generates mock/live opportunities, they don't inherit Satna
    ws_connector = WebSearchConnector(mock_mode=True)
    res = ws_connector._generate_mock_opportunities(query_plan.all_queries[0], limit=3)
    for opp in res:
        assert "Satna" not in opp.eligibility_rules.location_city_country
        assert "Satna" not in opp.display_location

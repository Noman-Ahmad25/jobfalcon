from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.discovery.connectors.parsing_utils import (
    extract_experience_months_with_confidence,
)
from app.modules.discovery.connectors.web_search.classifier import (
    BLOCKED_DOMAINS,
    JobSearchResultClassifier,
)
from app.modules.discovery.connectors.web_search.providers import RawSearchResult
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.explanation.explainer import OpportunityExplanationEngine
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.discovery import DiscoverySearchQuery, OpportunityRejectionCode
from app.schemas.eligibility import (
    DISQ_EXPERIENCE_BELOW_MINIMUM,
    EligibilityStatus,
    UNCERT_EXPERIENCE_REQUIREMENT_UNKNOWN,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)


@pytest.fixture
def fresh_grad_candidate() -> CandidateCareerProfile:
    """College graduate with 6 months total experience."""
    now = datetime.now(timezone.utc)
    ev = EvidenceRecord(
        evidence_id="ev_grad_py",
        source_type=EvidenceSourceType.ACADEMIC_TRANSCRIPT,
        extracted_snippet="Completed course projects in Python and relational databases.",
        observed_at=now,
        verifiability_weight=0.90,
    )
    return CandidateCareerProfile(
        user_id="test_fresh_grad_01",
        display_name="Jordan Fresh",
        profile_version=1,
        assessed_skills=[
            AssessedSkill(
                canonical_skill_id="esco:python",
                skill_name="Python",
                proficiency_score=7.0,
                confidence_score=0.85,
                evidence_records=[ev],
            )
        ],
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Software Engineer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            requires_visa_sponsorship=False,
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled_student=False,
            total_full_time_experience_months=6,  # 6 months
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
            preferred_locations=["Remote"],
        ),
        overall_profile_confidence=0.85,
    )


def test_placeholder_domain_rejection() -> None:
    """Verifies that reserved, test, and placeholder domains are rejected with code PLACEHOLDER_DOMAIN."""
    sample_query = DiscoverySearchQuery(
        query_id="q_test_ph",
        role_title="Backend Engineer",
        query_string="Backend Engineer python jobs",
        target_country_codes=["US"],
        category=OpportunityCategory.FULL_TIME_JOB,
    )

    test_urls = [
        "https://jobs.example.com/posting/12345",
        "https://example.org/careers/senior-engineer",
        "https://test.com/jobs/python-developer",
        "http://localhost:8000/careers/backend",
        "http://127.0.0.1:3000/jobs/ml-engineer",
    ]

    for url in test_urls:
        raw = RawSearchResult(
            url=url,
            title="Senior Backend Engineer - Hiring Now",
            snippet="Build scalable distributed microservices in Python with PostgreSQL.",
        )
        eval_res = JobSearchResultClassifier.evaluate(raw, sample_query)
        assert eval_res.is_job is False
        assert eval_res.rejection_code == OpportunityRejectionCode.PLACEHOLDER_DOMAIN
        assert "PLACEHOLDER_DOMAIN" in eval_res.reason


def test_experience_extraction_confidence() -> None:
    """Verifies deterministic confidence detection for experience requirements."""
    # 1. Entry level / intern -> 0 months, confident
    m1, c1 = extract_experience_months_with_confidence("Great entry level software engineer role for new graduates.")
    assert m1 == 0
    assert c1 is True

    # 2. Explicit 10+ years -> 120 months, confident
    m2, c2 = extract_experience_months_with_confidence("Requires at least 10+ years of distributed systems engineering.")
    assert m2 == 120
    assert c2 is True

    # 3. Senior title heuristic -> 48 months, confident
    m3, c3 = extract_experience_months_with_confidence("We are looking for an engineer to lead core infra.", title="Senior Backend Engineer")
    assert m3 == 48
    assert c3 is True

    # 4. Short snippet without experience signal -> 0 months, not confident
    m4, c4 = extract_experience_months_with_confidence("Build REST APIs in Python. Apply now.")
    assert m4 == 0
    assert c4 is False


def test_fresh_graduate_eligibility_for_senior_role(fresh_grad_candidate: CandidateCareerProfile) -> None:
    """Verifies that a role requiring 10+ years is deterministically INELIGIBLE for a fresh graduate."""
    now = datetime.now(timezone.utc)

    # Opportunity 1: Senior Principal Role (120 months required)
    senior_opp = create_normalized_opportunity(
        opportunity_id="opp_senior_10yr",
        category=OpportunityCategory.FULL_TIME_JOB,
        title="Principal Infrastructure Architect",
        company_name="MegaCorp Cloud",
        source_url="https://megacorp.jobs/principal-10yr",
        source_system="greenhouse",
        source_job_id="mc_1001",
        description="Requires 10+ years designing enterprise distributed infrastructure.",
        eligible_country_codes=["US"],
        sponsors_work_visa=True,
        minimum_degree_required=DegreeLevel.BACHELORS,
        min_experience_months=120,  # 10 years
        work_mode=WorkMode.REMOTE,
        location_city_country=["Remote"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=7.0,
                is_mandatory=True,
            )
        ],
        posted_at=now,
    )

    result_senior = evaluate_eligibility(fresh_grad_candidate, senior_opp)
    assert result_senior.is_eligible is False
    assert result_senior.status == EligibilityStatus.INELIGIBLE
    assert DISQ_EXPERIENCE_BELOW_MINIMUM in result_senior.disqualification_reasons

    # Opportunity 2: Early career role (0 months required)
    junior_opp = create_normalized_opportunity(
        opportunity_id="opp_junior_role",
        category=OpportunityCategory.FULL_TIME_JOB,
        title="Associate Software Engineer",
        company_name="NexGen Labs",
        source_url="https://nexgen.jobs/assoc-01",
        source_system="greenhouse",
        source_job_id="ng_2001",
        description="Entry level software engineering position.",
        eligible_country_codes=["US"],
        sponsors_work_visa=True,
        minimum_degree_required=DegreeLevel.BACHELORS,
        min_experience_months=0,
        work_mode=WorkMode.REMOTE,
        location_city_country=["Remote"],
        application_deadline=datetime(2027, 1, 1, tzinfo=timezone.utc),
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=6.0,
                is_mandatory=True,
            )
        ],
        posted_at=now,
    )

    result_junior = evaluate_eligibility(fresh_grad_candidate, junior_opp)
    assert result_junior.is_eligible is True
    assert result_junior.status == EligibilityStatus.ELIGIBLE

    # Opportunity 3: Web-sourced role with unknown experience (sentinel -1)
    unknown_exp_opp = create_normalized_opportunity(
        opportunity_id="opp_unknown_exp",
        category=OpportunityCategory.FULL_TIME_JOB,
        title="Python Developer",
        company_name="TechStart",
        source_url="https://techstart.careers/dev-01",
        source_system="web_search",
        source_job_id="ts_3001",
        description="Python backend developer wanted.",
        eligible_country_codes=["US"],
        sponsors_work_visa=True,
        minimum_degree_required=DegreeLevel.BACHELORS,
        min_experience_months=-1,  # Unknown from web snippet
        work_mode=WorkMode.REMOTE,
        location_city_country=["Remote"],
        posted_at=now,
    )

    result_unknown = evaluate_eligibility(fresh_grad_candidate, unknown_exp_opp)
    assert result_unknown.is_eligible is True
    assert result_unknown.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY
    assert UNCERT_EXPERIENCE_REQUIREMENT_UNKNOWN in result_unknown.uncertainty_caveats


def test_structured_profile_api_lifecycle() -> None:
    """Verifies complete deterministic profile creation, listing, updating, and deletion via API."""
    async def _test() -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            test_uid = f"usr_test_lifecycle_{int(datetime.now().timestamp())}"

            # 1. Create Profile
            payload = {
                "user_id": test_uid,
                "display_name": "Taylor Coder",
                "headline": "Junior Systems Developer",
                "highest_degree_level": "BACHELORS",
                "is_currently_enrolled_student": False,
                "total_full_time_experience_months": 12,
                "authorized_country_codes": ["US"],
                "requires_visa_sponsorship": False,
                "allowed_opportunity_categories": ["FULL_TIME_JOB"],
                "allowed_work_modes": ["REMOTE", "HYBRID"],
                "preferred_locations": ["Remote", "Chicago, IL"],
                "target_role_title": "Systems Software Engineer",
                "target_occupation_code": "15-1252.00",
                "initial_skills": [
                    {
                        "skill_name": "Go",
                        "proficiency_score": 7.5,
                        "evidence_snippet": "Developed concurrent CLI tools in Go.",
                    }
                ],
            }
            res_create = await client.post("/api/v1/profile/create-structured", json=payload)
            assert res_create.status_code == 201
            data = res_create.json()
            assert data["user_id"] == test_uid
            assert data["display_name"] == "Taylor Coder"
            assert len(data["assessed_skills"]) == 1
            assert data["assessed_skills"][0]["skill_name"] == "Go"

            # 2. List Profiles (must contain newly created profile)
            res_list = await client.get("/api/v1/profile/")
            assert res_list.status_code == 200
            summaries = res_list.json()
            assert any(s["user_id"] == test_uid for s in summaries)

            # 3. Retrieve Profile
            res_get = await client.get(f"/api/v1/profile/{test_uid}")
            assert res_get.status_code == 200
            assert res_get.json()["display_name"] == "Taylor Coder"

            # 4. Update Profile
            profile_data = res_get.json()
            profile_data["display_name"] = "Taylor Senior Coder"
            res_put = await client.put(f"/api/v1/profile/{test_uid}", json=profile_data)
            assert res_put.status_code == 200
            assert res_put.json()["display_name"] == "Taylor Senior Coder"

            # 5. Delete Profile
            res_del = await client.delete(f"/api/v1/profile/{test_uid}")
            assert res_del.status_code == 204

            # Verify 404 after deletion
            res_verify = await client.get(f"/api/v1/profile/{test_uid}")
            assert res_verify.status_code == 404

    asyncio.run(_test())


def test_explanation_deduplication_and_what_to_verify(fresh_grad_candidate: CandidateCareerProfile) -> None:
    """Verifies that explanations deduplicate skills and provide actionable what_to_verify items."""
    now = datetime.now(timezone.utc)
    engine = OpportunityExplanationEngine(llm_client=None)

    opp = create_normalized_opportunity(
        opportunity_id="opp_expl_dedup_01",
        category=OpportunityCategory.FULL_TIME_JOB,
        title="Software Engineer",
        company_name="CloudNine Systems",
        source_url="https://cloudnine.test/jobs/swe-01",
        source_system="web_search",
        source_job_id="cn_1001",
        description="Looking for Python engineers.",
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        min_experience_months=0,
        work_mode=WorkMode.REMOTE,
        location_city_country=["Remote"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=6.0,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:docker",
                skill_name="Docker",
                minimum_proficiency_expected=6.0,
                is_mandatory=False,
            ),
        ],
        posted_at=now,
        is_verified_posting=False,
        company_domain_verified=False,
    )

    expl = engine.explain_opportunity(fresh_grad_candidate, opp, use_llm=False)

    # 1. Deduplication check: No skill in both matched and skill_gaps
    matched_names = {m.skill_name for m in expl.matched_requirements}
    gap_names = {g.skill_name for g in expl.skill_gaps}
    assert matched_names.isdisjoint(gap_names)
    assert "Python" in matched_names
    assert "Docker" in gap_names

    # 2. What to verify items
    assert len(expl.what_to_verify) >= 2
    assert any("direct source URL" in v for v in expl.what_to_verify)
    assert any("employer identity" in v for v in expl.what_to_verify)

    # 3. Grounded summary
    assert "Python" in expl.why_matches_summary
    assert "Overall candidate fit score:" in expl.why_matches_summary

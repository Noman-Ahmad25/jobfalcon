from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.modules.deduplication.service import (
    DeduplicationService,
    deduplicate_opportunities,
)
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    PolymorphicOpportunity,
)


@pytest.fixture
def make_opportunity():
    """Factory fixture for creating PolymorphicOpportunity instances for deduplication testing."""
    def _create(
        opp_id: str,
        title: str,
        company: str,
        summary: str,
        source_url: str,
    ) -> PolymorphicOpportunity:
        rules = OpportunityEligibilityRules(
            opportunity_category=OpportunityCategory.FULL_TIME_JOB,
            eligible_country_codes=["US"],
            work_mode=WorkMode.HYBRID,
            location_city_country=["San Francisco, CA"],
        )
        return PolymorphicOpportunity(
            opportunity_id=opp_id,
            minhash_signature_hex="0" * 64,  # Placeholder, will be computed by service
            title=title,
            company_name=company,
            mapped_occupation_code="2512.1",
            eligibility_rules=rules,
            sanitized_summary=summary,
            source_url=source_url,
            posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            completeness_score=0.9,
            trust_score=0.95,
        )
    return _create


def test_matching_titles_alone_do_not_trigger_duplicate_detection(make_opportunity):
    """Opportunities with identical titles but different employers/descriptions are NOT duplicates."""
    service = DeduplicationService(threshold=0.85)

    opp_backend = make_opportunity(
        opp_id="opp-acme-001",
        title="Senior Software Engineer",
        company="Acme Corporation",
        summary="Build distributed cloud backend services using Python, FastAPI, and PostgreSQL. 5 years experience.",
        source_url="https://acme.example.com/jobs/001",
    )
    opp_frontend = make_opportunity(
        opp_id="opp-beta-002",
        title="Senior Software Engineer",
        company="Beta Interactive",
        summary="Develop responsive web applications using React, TypeScript, and Next.js. UI/UX design collaboration.",
        source_url="https://beta.example.com/jobs/002",
    )

    is_dup_1, rec_1 = service.process_opportunity(opp_backend)
    is_dup_2, rec_2 = service.process_opportunity(opp_frontend)

    assert is_dup_1 is False
    assert rec_1 is None
    assert is_dup_2 is False
    assert rec_2 is None

    assert len(service.canonical_opportunities) == 2
    assert "opp-acme-001" in service.canonical_opportunities
    assert "opp-beta-002" in service.canonical_opportunities


def test_syndicated_near_duplicate_grouped_with_provenance_preserved(make_opportunity):
    """Syndicated postings across multiple ATS boards are detected as duplicates without silent deletion."""
    service = DeduplicationService(threshold=0.85)

    base_summary = (
        "Join Apex Systems as a Backend Software Engineer designing and implementing high throughput cloud APIs. "
        "You will be responsible for developing asynchronous REST services using Python, FastAPI, and PostgreSQL, "
        "collaborating with cross-functional engineering teams, and writing comprehensive test suites using pytest. "
        "Candidates should have at least 3 years of professional Python experience, strong knowledge of SQL, "
        "and experience with containerization technologies including Docker and Kubernetes."
    )
    # Posting 1 on Greenhouse
    opp_greenhouse = make_opportunity(
        opp_id="opp-gh-101",
        title="Backend Software Engineer",
        company="Apex Systems",
        summary=base_summary,
        source_url="https://boards.greenhouse.io/apex/jobs/101",
    )
    # Posting 2 on Lever with minor syndication footer
    opp_lever = make_opportunity(
        opp_id="opp-lever-202",
        title="Backend Software Engineer",
        company="Apex Systems",
        summary=f"{base_summary} Equal opportunity employer. Apply via Lever.",
        source_url="https://jobs.lever.co/apex/jobs/202",
    )

    is_dup_1, rec_1 = service.process_opportunity(opp_greenhouse)
    is_dup_2, rec_2 = service.process_opportunity(opp_lever)

    # First is canonical
    assert is_dup_1 is False
    assert rec_1 is None
    assert opp_greenhouse.is_duplicate is False

    # Second is recognized as duplicate
    assert is_dup_2 is True
    assert rec_2 is not None
    assert opp_lever.is_duplicate is True
    assert rec_2.canonical_opportunity_id == "opp-gh-101"
    assert rec_2.duplicate_opportunity_id == "opp-lever-202"
    assert rec_2.source_url == "https://jobs.lever.co/apex/jobs/202"
    assert rec_2.similarity_score >= 0.85

    # Check cluster state: canonical cluster tracks both source URLs
    cluster = service.clusters["opp-gh-101"]
    assert cluster.cluster_size == 2
    assert "https://boards.greenhouse.io/apex/jobs/101" in cluster.all_source_urls
    assert "https://jobs.lever.co/apex/jobs/202" in cluster.all_source_urls
    assert len(cluster.duplicate_records) == 1


def test_deduplicate_batch_execution(make_opportunity):
    """deduplicate_opportunities batch function partitions canonicals and duplicates correctly."""
    summary_1 = (
        "Design distributed data streaming pipelines using Python, Apache Kafka, and ClickHouse. "
        "The Data Platform team is responsible for real-time telemetry processing, maintaining data lakes, "
        "and ensuring low-latency query performance across distributed analytics workloads. "
        "Required qualifications include 3+ years experience with data engineering, strong SQL proficiency, "
        "and practical experience managing Kafka event streams and columnar databases."
    )
    summary_2 = (
        "Lead mobile application engineering for iOS and Android using Swift, Kotlin, and React Native. "
        "You will architect cross-platform mobile interfaces, integrate RESTful backend APIs, and establish "
        "automated mobile release pipelines through GitHub Actions and Fastlane."
    )

    opp_1 = make_opportunity("opp-1", "Data Engineer", "StreamCo", summary_1, "https://stream.co/1")
    # Duplicate of opp_1 with minor syndication footer
    opp_1_dup = make_opportunity(
        "opp-1-dup", "Data Engineer", "StreamCo",
        f"{summary_1} Please submit applications through Ashby career portal.", "https://ashbyhq.com/stream/1"
    )
    opp_2 = make_opportunity("opp-2", "Mobile Lead", "AppCo", summary_2, "https://app.co/2")

    result = deduplicate_opportunities([opp_1, opp_1_dup, opp_2], threshold=0.85)


    assert result.total_evaluated == 3
    assert result.canonical_count == 2
    assert result.duplicate_count == 1

    canonical_ids = {o.opportunity_id for o in result.canonical_opportunities}
    assert canonical_ids == {"opp-1", "opp-2"}

    duplicate_ids = {o.opportunity_id for o in result.duplicate_opportunities}
    assert duplicate_ids == {"opp-1-dup"}

    # MinHash signature hex was generated (length 64)
    for opp in result.canonical_opportunities + result.duplicate_opportunities:
        assert len(opp.minhash_signature_hex) == 64
        assert opp.minhash_signature_hex != "0" * 64

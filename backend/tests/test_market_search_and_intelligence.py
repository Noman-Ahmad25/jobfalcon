from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.discovery.connectors.parsing_utils import (
    extract_skills_from_text,
    format_experience_requirement,
)
from app.schemas.common import OpportunityCategory, WorkMode


# ==============================================================================
# 1. Requirement Extraction & "Unknown is not zero" Tests
# ==============================================================================

def test_extract_skills_distinguishes_mandatory_vs_preferred() -> None:
    text = (
        "Required Qualifications: Hands-on experience with Python and FastAPI. "
        "Must have experience deploying with Docker. "
        "Preferred Qualifications: Knowledge of Kubernetes and Redis is a plus. "
        "Familiarity with GraphQL is advantageous."
    )
    skills = extract_skills_from_text(text)
    skill_map = {s.skill_name: s for s in skills}

    assert "Python" in skill_map
    assert skill_map["Python"].is_mandatory is True

    assert "FastAPI" in skill_map
    assert skill_map["FastAPI"].is_mandatory is True

    assert "Docker" in skill_map
    assert skill_map["Docker"].is_mandatory is True

    assert "Kubernetes" in skill_map
    assert skill_map["Kubernetes"].is_mandatory is False

    assert "Redis" in skill_map
    assert skill_map["Redis"].is_mandatory is False


def test_format_experience_requirement_unknown_is_not_zero() -> None:
    # Sentinel -1 must explicitly format to "Not stated"
    assert format_experience_requirement(-1) == "Not stated"
    # Confirmed 0 months means entry level
    assert format_experience_requirement(0) == "Entry level (no prior experience required)"
    # Positive months formatted to years
    assert format_experience_requirement(24) == "2+ years"
    assert format_experience_requirement(60) == "5+ years"
    assert format_experience_requirement(18) == "18 months"


# ==============================================================================
# 2. Market Search API Tests
# ==============================================================================

@pytest.mark.anyio
async def test_search_opportunities_by_keyword() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Search for Python
        payload = {"query": "Python", "page": 1, "page_size": 10}
        resp = await client.post("/api/v1/opportunities/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "opportunities" in data
        assert data["total"] > 0
        assert len(data["opportunities"]) <= 10
        # Check first match contains Python
        first = data["opportunities"][0]
        text_corp = f"{first['title']} {first['sanitized_summary']} {' '.join(s['skill_name'] for s in first['skill_requirements'])}".lower()
        assert "python" in text_corp


@pytest.mark.anyio
async def test_search_opportunities_with_filters() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Search with remote filter
        payload = {
            "work_mode": WorkMode.REMOTE.value,
            "category": OpportunityCategory.FULL_TIME_JOB.value,
            "page": 1,
            "page_size": 5,
        }
        resp = await client.post("/api/v1/opportunities/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        for opp in data["opportunities"]:
            assert opp["eligibility_rules"]["work_mode"] == WorkMode.REMOTE.value
            assert opp["eligibility_rules"]["opportunity_category"] == OpportunityCategory.FULL_TIME_JOB.value


# ==============================================================================
# 3. Market Intelligence API Tests
# ==============================================================================

@pytest.mark.anyio
async def test_get_market_intelligence_returns_truthful_distributions() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/opportunities/market-intelligence")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_opportunities_analyzed"] > 0
        assert data["unique_employers_count"] > 0
        assert len(data["top_skills"]) > 0

        # Check skill frequency calculation integrity
        total = data["total_opportunities_analyzed"]
        for skill in data["top_skills"]:
            assert skill["count"] > 0
            assert 0.0 <= skill["percentage"] <= 100.0
            expected_pct = round((skill["count"] / total) * 100.0, 1)
            assert skill["percentage"] == expected_pct

        # Check experience distribution keys (Unknown is not zero)
        exp_dist = data["experience_distribution"]
        assert "Not stated" in exp_dist
        assert "Entry level (0-2 yrs)" in exp_dist
        assert "Mid level (2-5 yrs)" in exp_dist
        assert "Senior / Lead (5+ yrs)" in exp_dist

        # Check work mode distribution
        mode_dist = data["work_mode_distribution"]
        assert "REMOTE" in mode_dist
        assert "HYBRID" in mode_dist
        assert "ON_SITE" in mode_dist

        # Check data integrity notice
        assert "Zero speculative trends" in data["data_integrity_notice"]

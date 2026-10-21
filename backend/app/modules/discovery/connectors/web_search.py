from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

from app.modules.discovery.connectors.base import (
    BaseDiscoveryConnector,
    create_normalized_opportunity,
)
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.discovery import (
    ConnectorHealthReport,
    ConnectorStatus,
    DiscoveryConnectorResult,
    DiscoverySearchQuery,
)
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity


class WebSearchConnector(BaseDiscoveryConnector):
    """Discovery connector wrapping broad career web search aggregation (Google Jobs / SearXNG / Bing).

    In air-gapped sandboxes or test suites without live search API keys, operates in a deterministic
    mock fallback mode generating high-fidelity search index listings.
    """

    def __init__(
        self,
        mock_mode: bool = True,
        simulate_error: bool = False,
        artificial_latency_ms: float = 20.0,
    ) -> None:
        self._mock_mode = mock_mode
        self._simulate_error = simulate_error
        self._latency_ms = artificial_latency_ms

    @property
    def connector_id(self) -> str:
        return "web_search"

    @property
    def source_name(self) -> str:
        return "Web Career Search Engine"

    @property
    def connector_type(self) -> str:
        return "WEB_SEARCH_INDEX"

    @property
    def is_mock_fallback(self) -> bool:
        return self._mock_mode

    async def check_health(self) -> ConnectorHealthReport:
        if self._simulate_error:
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.ERROR,
                is_mock_fallback=self.is_mock_fallback,
                details={"error": "Simulated search engine network gateway error"},
            )
        # Search engine aggregator requires live SearXNG host or Google Jobs API key
        return ConnectorHealthReport(
            connector_id=self.connector_id,
            source_name=self.source_name,
            connector_type=self.connector_type,
            status=ConnectorStatus.MOCKED_FALLBACK,
            is_mock_fallback=True,
            details={
                "search_provider": "SearXNG / Google for Jobs Aggregator",
                "rate_limit_per_min": 60,
                "configured": False,
                "note": "No external search gateway credentials configured; running in deterministic simulated mode.",
            },
        )

    async def search(
        self,
        query: DiscoverySearchQuery,
        limit: int = 10,
    ) -> DiscoveryConnectorResult:
        t0 = time.perf_counter()
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

        if self._simulate_error:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return DiscoveryConnectorResult(
                connector_id=self.connector_id,
                source_name=self.source_name,
                query_id=query.query_id,
                status=ConnectorStatus.ERROR,
                opportunities=[],
                raw_count=0,
                latency_ms=elapsed,
                error_message="Search engine connection timeout or HTTP 503 response.",
            )

        opportunities: list[PolymorphicOpportunity] = []
        now = datetime.now(timezone.utc)

        # Synthesize realistic search results based on query terms
        company_pool = ["Acme Cloud Technologies", "Vanguard Media", "DataStream Analytics", "NextGen Solutions"]
        country_codes = query.target_country_codes or ["US"]
        work_mode = query.work_modes[0] if query.work_modes else WorkMode.REMOTE
        category = query.category

        num_results = min(limit, 3)
        for idx in range(num_results):
            company = company_pool[idx % len(company_pool)]
            title = f"{query.role_title}"
            desc = (
                f"We are seeking a talented and driven {query.role_title} to join {company}. "
                f"In this role, you will design, build, and maintain high-performance software systems and APIs. "
                f"You will work closely with cross-functional product and engineering teams to deliver scalable solutions. "
                f"Key requirements include strong hands-on experience with {', '.join(query.expanded_keywords[:3])}, "
                f"writing clean and maintainable code, automated testing, and agile delivery. "
                f"Work environment: {work_mode.value}. We offer competitive compensation, comprehensive health benefits, "
                f"and flexible PTO for our engineering staff."
            )
            source_url = f"https://www.google.com/search?ibp=htl;jobs#fpstate=tldetail&htidocid=web_search_{idx}_{query.query_id}"

            opp = create_normalized_opportunity(
                title=title,
                company_name=company,
                description=desc,
                source_url=source_url,
                source_system="web_search",
                source_job_id=f"ws_{idx}_{query.query_id}",
                category=category,
                eligible_country_codes=country_codes,
                sponsors_work_visa=False,
                minimum_degree_required=DegreeLevel.BACHELORS if category != OpportunityCategory.INTERNSHIP else DegreeLevel.NONE,
                requires_active_student_status=category == OpportunityCategory.INTERNSHIP,
                min_experience_months=0 if "INTERN" in query.seniority_level or "ENTRY" in query.seniority_level else 24,
                work_mode=work_mode,
                location_city_country=[query.target_locations[0]] if query.target_locations else [],
                skill_requirements=[
                    OpportunitySkillRequirement(
                        canonical_skill_id=f"skill_ws_{kw.lower()}",
                        skill_name=kw,
                        is_mandatory=True,
                        minimum_proficiency_expected=5.0,
                    )
                    for kw in query.expanded_keywords[:3]
                ],
                mapped_occupation_code="15-1252.00",
                completeness_score=0.88,
                trust_score=0.82,
                posted_at=now,
            )
            opportunities.append(opp)

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        # Always reports MOCKED_FALLBACK because no live search provider backend is connected
        status = ConnectorStatus.MOCKED_FALLBACK
        return DiscoveryConnectorResult(
            connector_id=self.connector_id,
            source_name=self.source_name,
            query_id=query.query_id,
            status=status,
            opportunities=opportunities,
            raw_count=len(opportunities),
            latency_ms=elapsed,
            error_message=None,
        )

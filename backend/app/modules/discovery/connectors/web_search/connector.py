from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

from app.modules.discovery.connectors.base import (
    BaseDiscoveryConnector,
    create_normalized_opportunity,
)
from app.modules.discovery.connectors.web_search.classifier import (
    JobSearchResultClassifier,
    normalize_search_result_to_opportunity,
)
from app.modules.discovery.connectors.web_search.providers import (
    BaseSearchProvider,
    MockSearchProvider,
    RawSearchResult,
    get_search_provider,
)
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.discovery import (
    ConnectorHealthReport,
    ConnectorStatus,
    DiscoveryConnectorResult,
    DiscoverySearchQuery,
)
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity

logger = logging.getLogger(__name__)


class WebSearchConnector(BaseDiscoveryConnector):
    """Discovery connector interfacing with real web search providers (SearXNG / DuckDuckGo / Custom).

    Features:
    - Real HTTP search query execution via configurable provider (SearXNG, DuckDuckGo, Custom REST).
    - Intelligent job listing classification filtering out tutorials, blogs, and aggregators.
    - Explicit uncertainty tracking (marks unverified search snippets with calibrated trust scores).
    - Retains original source URLs and provenance attribution.
    - Partial failure resilience and transparent connector health reporting (CONNECTED, UNAVAILABLE, MISCONFIGURED, DEGRADED, MOCKED_FALLBACK).
    - Deterministic fallback for air-gapped CI and test environments.
    """

    def __init__(
        self,
        mock_mode: bool = True,
        simulate_error: bool = False,
        artificial_latency_ms: float = 20.0,
        provider: BaseSearchProvider | None = None,
    ) -> None:
        self._mock_mode = mock_mode
        self._simulate_error = simulate_error
        self._latency_ms = artificial_latency_ms
        self._provider = provider

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

    @property
    def provider(self) -> BaseSearchProvider:
        if self._provider is not None:
            return self._provider
        if self._mock_mode:
            return MockSearchProvider(latency_ms=self._latency_ms)
        return get_search_provider(mock_mode=False)

    async def check_health(self) -> ConnectorHealthReport:
        """Inspects connectivity and reports honest operational status."""
        if self._simulate_error:
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.ERROR,
                is_mock_fallback=self.is_mock_fallback,
                details={"error": "Simulated search engine network gateway error"},
            )

        if self._mock_mode:
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.MOCKED_FALLBACK,
                is_mock_fallback=True,
                details={
                    "search_provider": "Deterministic Mock Provider",
                    "mode": "MOCKED_FALLBACK",
                    "configured": True,
                    "note": "Running in deterministic simulated mock mode for tests / offline sandbox.",
                },
            )

        # Live Provider Health Probe
        try:
            health = await self.provider.check_health()
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=health.status,
                is_mock_fallback=False,
                details={
                    "search_provider": health.provider_name,
                    "latency_ms": health.latency_ms,
                    **health.details,
                },
            )
        except Exception as exc:
            logger.error("Web search health check probe failed: %s", exc)
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.UNAVAILABLE,
                is_mock_fallback=False,
                details={"error": f"Provider probe failed: {type(exc).__name__} - {exc!s}"},
            )

    async def search(
        self,
        query: DiscoverySearchQuery,
        limit: int = 10,
    ) -> DiscoveryConnectorResult:
        """Executes search query against configured provider and returns normalized opportunities."""
        t0 = time.perf_counter()

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

        # 1. Deterministic Mock Mode
        if self._mock_mode:
            if self._latency_ms > 0:
                await asyncio.sleep(self._latency_ms / 1000.0)

            opportunities = self._generate_mock_opportunities(query, limit)
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return DiscoveryConnectorResult(
                connector_id=self.connector_id,
                source_name=self.source_name,
                query_id=query.query_id,
                status=ConnectorStatus.MOCKED_FALLBACK,
                opportunities=opportunities,
                raw_count=len(opportunities),
                latency_ms=elapsed,
                error_message=None,
            )

        # 2. Live Provider Execution
        try:
            # Build targeted web query string
            effective_query = self._build_search_query_string(query)
            raw_results: list[RawSearchResult] = await self.provider.search(
                query=effective_query,
                limit=limit,
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.warning("Web search provider '%s' failed for query '%s': %s", self.provider.provider_name, query.query_id, exc)
            return DiscoveryConnectorResult(
                connector_id=self.connector_id,
                source_name=self.source_name,
                query_id=query.query_id,
                status=ConnectorStatus.UNAVAILABLE,
                opportunities=[],
                raw_count=0,
                latency_ms=elapsed,
                error_message=f"Web search provider error: {type(exc).__name__} - {exc!s}",
            )

        # 3. Filter and Classify Job Results
        opportunities: list[PolymorphicOpportunity] = []
        for raw in raw_results:
            is_job, reason = JobSearchResultClassifier.evaluate(raw, query)
            if not is_job:
                logger.debug("Filtered out web search result '%s': %s", raw.title, reason)
                continue

            opp = normalize_search_result_to_opportunity(raw, query)
            opportunities.append(opp)

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        status = ConnectorStatus.CONNECTED if len(opportunities) > 0 else ConnectorStatus.DEGRADED

        return DiscoveryConnectorResult(
            connector_id=self.connector_id,
            source_name=self.source_name,
            query_id=query.query_id,
            status=status,
            opportunities=opportunities,
            raw_count=len(raw_results),
            latency_ms=elapsed,
            error_message=None,
        )

    def _build_search_query_string(self, query: DiscoverySearchQuery) -> str:
        """Constructs a targeted search engine query string emphasizing hiring career pages."""
        tokens = [f'"{query.role_title}"']
        if query.category == OpportunityCategory.INTERNSHIP:
            tokens.append("internship OR intern")
        elif "ENTRY" in query.seniority_level:
            tokens.append("junior OR entry level")

        # Top skills
        if query.expanded_keywords:
            top_tech = " ".join(query.expanded_keywords[:2])
            tokens.append(top_tech)

        if query.work_modes and WorkMode.REMOTE in query.work_modes:
            tokens.append("remote")
        elif query.target_locations:
            tokens.append(f'"{query.target_locations[0]}"')

        # Add career keywords
        tokens.append("(careers OR jobs OR apply)")
        return " ".join(tokens)

    def _generate_mock_opportunities(
        self,
        query: DiscoverySearchQuery,
        limit: int,
    ) -> list[PolymorphicOpportunity]:
        """Generates deterministic mock opportunities for testing."""
        opportunities: list[PolymorphicOpportunity] = []
        now = datetime.now(UTC)
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
            source_url = f"https://jobs.example.com/{company.lower().replace(' ', '-')}/posting-{idx}_{query.query_id}"

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

        return opportunities

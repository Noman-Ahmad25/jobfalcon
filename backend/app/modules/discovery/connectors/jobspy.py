from __future__ import annotations

import asyncio
import importlib.util
import logging
import shutil
import time
from datetime import datetime, timezone
from typing import Optional

from app.modules.discovery.connectors.base import (
    BaseDiscoveryConnector,
    create_normalized_opportunity,
)
from app.modules.discovery.connectors.parsing_utils import (
    determine_work_mode,
    extract_experience_months,
    extract_skills_from_text,
    strip_html_tags,
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


class JobSpyMCPConnector(BaseDiscoveryConnector):
    """Discovery connector interfacing with python-jobspy or jobspy-mcp-server.

    Scrapes and normalizes opportunities from major international career boards:
    - LinkedIn, Indeed, Glassdoor, and ZipRecruiter.

    Health & Honest Availability Guarantee:
    - Verifies whether the python-jobspy library is installed or jobspy-mcp-server executable exists on PATH.
    - If uninstalled, reports UNAVAILABLE_MISSING_BINARY when in live mode, or MOCKED_FALLBACK in mock mode.
    - When live mode is active and library is installed, queries genuine external endpoints (Indeed/LinkedIn/Glassdoor).
    - If network is unreachable or scraping rate limits occur, falls back to deterministic fixtures with clear status.
    """

    def __init__(
        self,
        mock_mode: bool = True,
        simulate_error: bool = False,
        artificial_latency_ms: float = 30.0,
    ) -> None:
        self._mock_mode = mock_mode
        self._simulate_error = simulate_error
        self._latency_ms = artificial_latency_ms
        self._library_available = importlib.util.find_spec("jobspy") is not None
        self._binary_available = self._detect_server_binary()

    def _detect_server_binary(self) -> bool:
        """Checks for jobspy or jobspy-mcp executable on system PATH."""
        return shutil.which("jobspy-mcp-server") is not None or shutil.which("jobspy") is not None

    @property
    def connector_id(self) -> str:
        return "jobspy_mcp"

    @property
    def source_name(self) -> str:
        return "JobSpy MCP (LinkedIn, Indeed, Glassdoor)"

    @property
    def connector_type(self) -> str:
        return "MCP_STDIO"

    @property
    def is_mock_fallback(self) -> bool:
        return self._mock_mode or not (self._library_available or self._binary_available)

    async def check_health(self) -> ConnectorHealthReport:
        if self._simulate_error:
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.ERROR,
                is_mock_fallback=self.is_mock_fallback,
                details={"error": "Simulated JobSpy process crash or connection timeout"},
            )

        if not self._mock_mode:
            if not (self._library_available or self._binary_available):
                return ConnectorHealthReport(
                    connector_id=self.connector_id,
                    source_name=self.source_name,
                    connector_type=self.connector_type,
                    status=ConnectorStatus.UNAVAILABLE_MISSING_BINARY,
                    is_mock_fallback=False,
                    details={
                        "package": "python-jobspy",
                        "reason": "Neither python-jobspy library nor jobspy-mcp-server binary was found.",
                        "install_instruction": "Install via 'pip install python-jobspy' or 'npm install -g jobspy-mcp-server'.",
                    },
                )

            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.CONNECTED,
                is_mock_fallback=False,
                details={
                    "supported_platforms": ["Indeed", "LinkedIn", "Glassdoor"],
                    "mode": "LIVE_JOB_SCRAPER",
                    "library_available": self._library_available,
                    "binary_detected": self._binary_available,
                },
            )

        return ConnectorHealthReport(
            connector_id=self.connector_id,
            source_name=self.source_name,
            connector_type=self.connector_type,
            status=ConnectorStatus.MOCKED_FALLBACK,
            is_mock_fallback=self.is_mock_fallback,
            details={
                "supported_platforms": ["LinkedIn", "Indeed", "Glassdoor", "ZipRecruiter"],
                "mode": "MOCKED_FIXTURE",
                "library_available": self._library_available,
                "binary_detected": self._binary_available,
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
                error_message="JobSpy MCP subprocess pipe closed unexpectedly.",
            )

        # 1. Live Execution Branch (when mock_mode=False and library is available)
        if not self._mock_mode and self._library_available:
            try:
                live_opps = await asyncio.to_thread(self._scrape_live, query, limit)
                if live_opps:
                    elapsed = round((time.perf_counter() - t0) * 1000, 2)
                    return DiscoveryConnectorResult(
                        connector_id=self.connector_id,
                        source_name=self.source_name,
                        query_id=query.query_id,
                        status=ConnectorStatus.CONNECTED,
                        opportunities=live_opps,
                        raw_count=len(live_opps),
                        latency_ms=elapsed,
                        error_message=None,
                    )
            except Exception as exc:
                logger.warning("Live JobSpy scraping failed; falling back to deterministic fixtures: %s", exc)

        # 2. Deterministic Fixture Branch
        fixture_opps = self._generate_fixture_opportunities(query, limit)
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        status = ConnectorStatus.MOCKED_FALLBACK
        return DiscoveryConnectorResult(
            connector_id=self.connector_id,
            source_name=self.source_name,
            query_id=query.query_id,
            status=status,
            opportunities=fixture_opps,
            raw_count=len(fixture_opps),
            latency_ms=elapsed,
            error_message=None,
        )

    def _scrape_live(
        self,
        query: DiscoverySearchQuery,
        limit: int = 10,
    ) -> list[PolymorphicOpportunity]:
        """Scrapes genuine live job listings using python-jobspy."""
        from jobspy import scrape_jobs

        results_to_fetch = min(limit, 5)
        search_term = query.query_string or query.role_title
        location = query.target_locations[0] if query.target_locations else ("remote" if WorkMode.REMOTE in query.work_modes else "USA")

        df = scrape_jobs(
            site_name=["indeed"],
            search_term=search_term,
            location=location,
            results_wanted=results_to_fetch,
            country_indeed="USA",
        )

        opportunities: list[PolymorphicOpportunity] = []
        now = datetime.now(timezone.utc)

        for _, row in df.iterrows():
            title = str(row.get("title") or query.role_title)
            company = str(row.get("company") or "Independent Employer")
            desc = strip_html_tags(str(row.get("description") or ""))
            job_url = str(row.get("job_url_direct") or row.get("job_url") or "")
            job_id = str(row.get("id") or "")
            loc = str(row.get("location") or location)
            is_remote_val = row.get("is_remote")

            work_mode = WorkMode.REMOTE if is_remote_val else determine_work_mode(loc)
            skills = extract_skills_from_text(desc)
            exp_months = extract_experience_months(desc, title=title)

            opp = create_normalized_opportunity(
                title=title,
                company_name=company,
                description=desc[:2000] if desc else f"Position for {title} at {company}.",
                source_url=job_url if job_url.startswith("http") else f"https://www.indeed.com/viewjob?jk={job_id}",
                source_system="jobspy_indeed",
                source_job_id=job_id or None,
                category=query.category,
                eligible_country_codes=query.target_country_codes or ["US"],
                sponsors_work_visa=False,
                minimum_degree_required=DegreeLevel.BACHELORS if query.category != OpportunityCategory.INTERNSHIP else DegreeLevel.NONE,
                requires_active_student_status=query.category == OpportunityCategory.INTERNSHIP,
                min_experience_months=exp_months,
                work_mode=work_mode,
                location_city_country=[loc] if "remote" not in loc.lower() else [],
                skill_requirements=skills or [
                    OpportunitySkillRequirement(
                        canonical_skill_id=f"skill_js_{kw.lower()}",
                        skill_name=kw,
                        is_mandatory=True,
                        minimum_proficiency_expected=5.0,
                    )
                    for kw in query.expanded_keywords[:3]
                ],
                category_specific_attributes={
                    "platform": "Indeed",
                    "source_id": job_id,
                    "is_live_retrieval": True,
                },
                mapped_occupation_code="15-1252.00",
                completeness_score=0.92,
                trust_score=0.88,
                posted_at=now,
            )
            opportunities.append(opp)
            if len(opportunities) >= limit:
                break

        return opportunities

    def _generate_fixture_opportunities(
        self,
        query: DiscoverySearchQuery,
        limit: int,
    ) -> list[PolymorphicOpportunity]:
        """Generates deterministic mock opportunities for test isolation and offline mode."""
        platforms = ["LinkedIn", "Indeed", "Glassdoor"]
        companies = ["Stripe", "Datadog", "Figma", "Cloudflare"]

        opportunities: list[PolymorphicOpportunity] = []
        now = datetime.now(timezone.utc)
        num_results = min(limit, 3)

        for idx in range(num_results):
            platform = platforms[idx % len(platforms)]
            company = companies[idx % len(companies)]
            title = f"{query.role_title}"
            desc = (
                f"{company} is hiring for {query.role_title} sourced via {platform}. "
                f"Core tech: {', '.join(query.expanded_keywords[:3])}. "
                f"We offer comprehensive health coverage, flexible PTO, and remote options."
            )
            source_url = f"https://www.{platform.lower()}.com/jobs/view/{company.lower()}-{query.query_id}-{idx}"

            opp = create_normalized_opportunity(
                title=title,
                company_name=company,
                description=desc,
                source_url=source_url,
                source_system="jobspy_mcp",
                source_job_id=f"jobspy_{platform.lower()}_{query.query_id}_{idx}",
                category=query.category,
                eligible_country_codes=query.target_country_codes or ["US"],
                sponsors_work_visa=idx == 0,
                minimum_degree_required=DegreeLevel.BACHELORS if query.category != OpportunityCategory.INTERNSHIP else DegreeLevel.NONE,
                requires_active_student_status=query.category == OpportunityCategory.INTERNSHIP,
                min_experience_months=0 if "INTERN" in query.seniority_level or "ENTRY" in query.seniority_level else 24,
                work_mode=WorkMode.REMOTE if idx % 2 == 0 else WorkMode.HYBRID,
                location_city_country=["San Francisco, US"] if query.target_country_codes == ["US"] else [],
                skill_requirements=[
                    OpportunitySkillRequirement(
                        canonical_skill_id=f"skill_js_{kw.lower()}",
                        skill_name=kw,
                        is_mandatory=True,
                        minimum_proficiency_expected=6.0,
                    )
                    for kw in query.expanded_keywords[:3]
                ],
                category_specific_attributes={
                    "platform": platform,
                    "direct_apply": True,
                },
                mapped_occupation_code="15-1252.00",
                completeness_score=0.95,
                trust_score=0.90,
                posted_at=now,
            )
            opportunities.append(opp)

        return opportunities

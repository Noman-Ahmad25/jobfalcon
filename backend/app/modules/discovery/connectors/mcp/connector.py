from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import get_settings, resolve_jobspy_country
from app.modules.discovery.connectors.base import (
    BaseDiscoveryConnector,
    create_normalized_opportunity,
)
from app.modules.discovery.connectors.mcp.client import MCPClient
from app.modules.discovery.connectors.mcp.normalizer import JobSpyMCPNormalizer
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
    """Discovery connector interfacing with JobSpy MCP over standard Model Context Protocol (STDIO).

    Retrieves and normalizes career opportunities across:
    - LinkedIn, Indeed, Glassdoor, and ZipRecruiter.

    Health & Honest Availability Guarantee:
    - Truly communicates through the MCP JSON-RPC protocol over stdio.
    - Probes protocol handshake (`initialize`) and discovers advertised tools (`list_tools`).
    - Reports CONNECTED only when real MCP protocol communication succeeded.
    - Reports UNAVAILABLE_MISSING_BINARY if mcp-jobspy executable or module is absent.
    - Reports MOCKED_FALLBACK when explicitly running in mock/test mode.
    - Isolates failures: tool or pipe errors never crash the overall coordinator workflow.
    """

    def __init__(
        self,
        mock_mode: bool = True,
        simulate_error: bool = False,
        artificial_latency_ms: float = 30.0,
        mcp_client: Optional[MCPClient] = None,
        timeout_seconds: Optional[float] = None,
        fetch_details: Optional[bool] = None,
    ) -> None:
        settings = get_settings()
        self._mock_mode = mock_mode
        self._simulate_error = simulate_error
        self._latency_ms = artificial_latency_ms
        self.timeout_seconds = timeout_seconds or settings.MCP_JOBSPY_TIMEOUT_SECONDS
        self._fetch_details = (
            fetch_details if fetch_details is not None else settings.MCP_JOBSPY_FETCH_DETAILS
        )
        self.client = mcp_client or MCPClient(timeout_seconds=self.timeout_seconds)

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
        return self._mock_mode or not self.client.is_binary_available()

    async def check_health(self) -> ConnectorHealthReport:
        """Evaluates live MCP server availability and protocol health."""
        if self._simulate_error:
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=ConnectorStatus.ERROR,
                is_mock_fallback=self.is_mock_fallback,
                details={"error": "Simulated MCP pipe disconnection or crash"},
            )

        if not self._mock_mode:
            conn_info = await self.client.check_health()
            return ConnectorHealthReport(
                connector_id=self.connector_id,
                source_name=self.source_name,
                connector_type=self.connector_type,
                status=conn_info.status,
                is_mock_fallback=False,
                details={
                    "protocol_version": conn_info.protocol_version,
                    "server_name": conn_info.server_name,
                    "server_version": conn_info.server_version,
                    "discovered_tools": conn_info.discovered_tools,
                    "latency_ms": conn_info.latency_ms,
                    **conn_info.details,
                },
            )

        # Mock mode fallback
        return ConnectorHealthReport(
            connector_id=self.connector_id,
            source_name=self.source_name,
            connector_type=self.connector_type,
            status=ConnectorStatus.MOCKED_FALLBACK,
            is_mock_fallback=True,
            details={
                "supported_platforms": ["LinkedIn", "Indeed", "Glassdoor", "ZipRecruiter"],
                "mode": "MOCKED_FIXTURE",
                "binary_detected": self.client.is_binary_available(),
            },
        )

    async def search(
        self,
        query: DiscoverySearchQuery,
        limit: int = 10,
    ) -> DiscoveryConnectorResult:
        """Executes targeted opportunity retrieval via MCP protocol or deterministic mock fixtures."""
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

        # 1. Live MCP Execution Branch
        if not self._mock_mode:
            if not self.client.is_binary_available():
                elapsed = round((time.perf_counter() - t0) * 1000, 2)
                return DiscoveryConnectorResult(
                    connector_id=self.connector_id,
                    source_name=self.source_name,
                    query_id=query.query_id,
                    status=ConnectorStatus.UNAVAILABLE_MISSING_BINARY,
                    opportunities=[],
                    raw_count=0,
                    latency_ms=elapsed,
                    error_message=f"JobSpy MCP binary '{self.client.binary_name}' is not installed in PATH.",
                )

            try:
                live_opps = await self._search_via_mcp(query, limit)
                elapsed = round((time.perf_counter() - t0) * 1000, 2)
                if live_opps:
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
                else:
                    return DiscoveryConnectorResult(
                        connector_id=self.connector_id,
                        source_name=self.source_name,
                        query_id=query.query_id,
                        status=ConnectorStatus.DEGRADED,
                        opportunities=[],
                        raw_count=0,
                        latency_ms=elapsed,
                        error_message="MCP tool 'search_jobs' returned 0 listings for query.",
                    )
            except Exception as exc:
                elapsed = round((time.perf_counter() - t0) * 1000, 2)
                logger.warning("Live MCP search failed: %s", exc)
                return DiscoveryConnectorResult(
                    connector_id=self.connector_id,
                    source_name=self.source_name,
                    query_id=query.query_id,
                    status=ConnectorStatus.ERROR,
                    opportunities=[],
                    raw_count=0,
                    latency_ms=elapsed,
                    error_message=f"Live MCP execution error: {exc!s}",
                )

        # 2. Deterministic Fixture Branch (strictly when mock_mode=True)
        fixture_opps = self._generate_fixture_opportunities(query, limit)
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return DiscoveryConnectorResult(
            connector_id=self.connector_id,
            source_name=self.source_name,
            query_id=query.query_id,
            status=ConnectorStatus.MOCKED_FALLBACK,
            opportunities=fixture_opps,
            raw_count=len(fixture_opps),
            latency_ms=elapsed,
            error_message=None,
        )

    @staticmethod
    def _clean_mcp_search_term(query: DiscoverySearchQuery) -> str:
        """Extracts clean role title and key technologies for ATS/job-board search without boolean noise."""
        base = query.role_title or query.query_string or ""
        # Strip site: operators and excessive quotes/brackets
        base = re.sub(r"site:[^\s)]+", "", base)
        base = re.sub(r'[\"\'\(\)]', " ", base)
        base = re.sub(r"\b(OR|AND|NOT)\b", " ", base)
        base = re.sub(r"\b(hiring|apply|careers)\b", " ", base, flags=re.IGNORECASE)
        cleaned = " ".join(base.split())
        return cleaned or query.role_title or "Software Engineer"

    async def _search_via_mcp(
        self,
        query: DiscoverySearchQuery,
        limit: int,
    ) -> list[PolymorphicOpportunity]:
        """Invokes MCP tool 'search_jobs' and optionally 'get_job_details' through the MCP client."""
        settings = get_settings()
        results_wanted = max(min(limit, 50), min(settings.MCP_JOBSPY_RESULTS_WANTED, 50))
        search_term = self._clean_mcp_search_term(query)
        country_code = resolve_jobspy_country(
            query.target_country_codes, default_fallback=settings.MCP_JOBSPY_COUNTRY
        )
        location = (
            query.target_locations[0]
            if query.target_locations
            else ("remote" if WorkMode.REMOTE in query.work_modes else country_code.upper())
        )
        is_remote = WorkMode.REMOTE in query.work_modes

        tool_args: dict[str, Any] = {
            "search_term": search_term,
            "location": location,
            "site_name": ["indeed"],  # Indeed is fast, reliable, and provides initial descriptions
            "results_wanted": results_wanted,
            "is_remote": is_remote,
            "country_indeed": country_code,
        }

        # Step 1 & 2: Execute search_jobs and get_job_details in a single MCP session
        async with self.client.session() as mcp_session:
            call_result = await mcp_session.call_tool("search_jobs", arguments=tool_args)

            # Parse tool output content
            payload: dict[str, Any] = {}
            for content in call_result.content or []:
                if hasattr(content, "text") and content.text:
                    try:
                        payload = json.loads(content.text)
                        break
                    except Exception:
                        continue

            raw_jobs: list[dict[str, Any]] = payload.get("jobs", [])
            search_id = payload.get("search_id")

            if not raw_jobs:
                return []

            detailed_jobs: list[dict[str, Any]] = raw_jobs
            if self._fetch_details and search_id:
                job_ids = [str(j["id"]) for j in raw_jobs[:5] if j.get("id")]
                if job_ids:
                    try:
                        details_result = await mcp_session.call_tool(
                            "get_job_details",
                            arguments={"search_id": search_id, "job_ids": job_ids},
                        )
                        for content in details_result.content or []:
                            if hasattr(content, "text") and content.text:
                                details_payload = json.loads(content.text)
                                if details_payload.get("jobs"):
                                    detailed_jobs = details_payload["jobs"]
                                break
                    except Exception as exc:
                        logger.info("MCP get_job_details enrichment skipped: %s; using search preview", exc)

        # Step 3: Normalize records into PolymorphicOpportunities
        opportunities: list[PolymorphicOpportunity] = []
        for job_dict in detailed_jobs[:limit]:
            opp = JobSpyMCPNormalizer.normalize_job_record(job_dict, query)
            opportunities.append(opp)

        return opportunities

    def _generate_fixture_opportunities(
        self,
        query: DiscoverySearchQuery,
        limit: int,
    ) -> list[PolymorphicOpportunity]:
        """Generates deterministic mock fixtures for offline testing."""
        platforms = [
            ("Indeed", "https://www.indeed.com/viewjob?jk=indeed_sample_99", "120-140k USD"),
            ("LinkedIn", "https://www.linkedin.com/jobs/view/linkedin_sample_88", "130-150k USD"),
            ("Glassdoor", "https://www.glassdoor.com/job-listing/glassdoor_sample_77", "115-135k USD"),
        ]
        now = datetime.now(timezone.utc)
        opportunities: list[PolymorphicOpportunity] = []
        num_to_gen = min(limit, 3)

        for i in range(num_to_gen):
            plat, base_url, comp = platforms[i % len(platforms)]
            title = f"{query.role_title}"
            company = f"{plat} Featured Tech Corp"
            desc = (
                f"[MCP Tool Result: jobspy/search_jobs - Mock Fixture] "
                f"We are hiring a {title} to build cloud infrastructure and APIs. "
                f"Required skills: {', '.join(query.expanded_keywords[:2])}. "
                f"Compensation: {comp}."
            )
            opp = create_normalized_opportunity(
                title=title,
                company_name=company,
                description=desc,
                source_url=f"{base_url}_{query.query_id}_{i}",
                source_system="jobspy_mcp",
                source_job_id=f"js_mock_{i}_{query.query_id}",
                category=query.category,
                eligible_country_codes=query.target_country_codes or ["US"],
                sponsors_work_visa=False,
                minimum_degree_required=DegreeLevel.BACHELORS if query.category != OpportunityCategory.INTERNSHIP else DegreeLevel.NONE,
                requires_active_student_status=query.category == OpportunityCategory.INTERNSHIP,
                min_experience_months=0 if "INTERN" in query.seniority_level or "ENTRY" in query.seniority_level else 18,
                work_mode=WorkMode.REMOTE if query.work_modes and WorkMode.REMOTE in query.work_modes else WorkMode.HYBRID,
                location_city_country=["San Francisco, CA"] if WorkMode.REMOTE not in query.work_modes else [],
                skill_requirements=[
                    OpportunitySkillRequirement(
                        canonical_skill_id=f"skill_mcp_{kw.lower()}",
                        skill_name=kw,
                        is_mandatory=True,
                        minimum_proficiency_expected=5.5,
                    )
                    for kw in query.expanded_keywords[:3]
                ],
                category_specific_attributes={
                    "platform": plat,
                    "mcp_server": "jobspy",
                    "mcp_tool": "search_jobs",
                },
                mapped_occupation_code="15-1252.00",
                completeness_score=0.88,
                trust_score=0.82,
                posted_at=now,
            )
            opportunities.append(opp)

        return opportunities

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    OpportunityRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteOpportunityRepository,
)
from app.modules.deduplication.service import deduplicate_opportunities
from app.modules.discovery.connectors import (
    BaseDiscoveryConnector,
    get_default_connectors,
)
from app.modules.discovery.role_mapper import generate_discovery_query_plan
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.ingestion.importer import OpportunityImporter
from app.schemas.discovery import (
    ConnectorStatus,
    DiscoveryConnectorReport,
    DiscoveryConnectorResult,
    DiscoveryQueryPlan,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
)
from app.schemas.eligibility import EligibilityResult, EligibilityStatus
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile

logger = logging.getLogger(__name__)


class DiscoveryCoordinator:
    """Orchestrates multi-source career opportunity discovery.

    Responsibilities:
    1. Generates targeted query plans from candidate skill profiles.
    2. Concurrently invokes multi-source connectors (Web Search, India Jobs MCP, JobSpy MCP, ATS Direct).
    3. Guarantees partial failure resilience: exceptions in one connector never discard other results.
    4. Executes early cross-source MinHash LSH deduplication.
    5. Optionally persists opportunities and duplicate linkages via repository interfaces.
    6. Evaluates hard deterministic eligibility constraints on discovered canonical listings.
    """

    def __init__(
        self,
        opp_repo: Optional[OpportunityRepository] = None,
        cluster_repo: Optional[DuplicateClusterRepository] = None,
        profile_repo: Optional[CandidateProfileRepository] = None,
        connectors: Optional[list[BaseDiscoveryConnector]] = None,
    ) -> None:
        self.opp_repo = opp_repo or SQLiteOpportunityRepository()
        self.cluster_repo = cluster_repo or SQLiteDuplicateClusterRepository()
        self.profile_repo = profile_repo or SQLiteCandidateProfileRepository()
        self._connectors = connectors

    async def execute_discovery(
        self,
        request: DiscoveryRunRequest,
    ) -> DiscoveryRunResponse:
        t0 = time.perf_counter()

        # 1. Resolve candidate profile
        profile = request.candidate_profile
        if profile is None and request.user_id:
            profile = self.profile_repo.get(request.user_id)

        if profile is None:
            raise ValueError(
                "Cannot execute discovery: neither a valid 'candidate_profile' was provided "
                "nor was an existing profile found for 'user_id'."
            )

        # 2. Generate deterministic Skill-to-Role Mapping Query Plan
        query_plan = generate_discovery_query_plan(profile)

        # 3. Resolve and configure connectors
        active_connectors = self._resolve_connectors(
            connector_ids=request.connector_ids,
            simulate_failure_connector=request.simulate_failure_connector,
            mock_mode=request.mock_mode,
        )

        # 4. Concurrently invoke connectors across prioritized queries
        connector_results, connector_reports = await self._run_connectors_concurrently(
            connectors=active_connectors,
            query_plan=query_plan,
            max_results_per_connector=request.max_results_per_connector,
        )

        # Aggregate raw opportunities from all successful connector results
        all_discovered: list[PolymorphicOpportunity] = []
        for res in connector_results:
            all_discovered.extend(res.opportunities)

        # 5. Early Cross-Source MinHash LSH Deduplication
        dedup_result = deduplicate_opportunities(
            opportunities=all_discovered,
            threshold=request.deduplication_threshold,
        )

        # 6. Optional Persistence via OpportunityImporter
        if request.persist_to_repository and all_discovered:
            importer = OpportunityImporter(
                opp_repo=self.opp_repo,
                cluster_repo=self.cluster_repo,
            )
            try:
                importer.import_opportunities(
                    opportunities=all_discovered,
                    source_system="multi_source_discovery",
                )
            except Exception as exc:
                logger.error("Failed to persist discovered opportunities: %s", exc, exc_info=True)

        # 7. Evaluate deterministic eligibility on distinct canonical opportunities
        ref_time = datetime.now(timezone.utc)
        eligible_canonical: list[PolymorphicOpportunity] = []
        eligibility_results: list[EligibilityResult] = []
        eligible_count = 0
        uncertain_count = 0
        ineligible_count = 0

        for opp in dedup_result.canonical_opportunities:
            eval_res = evaluate_eligibility(
                candidate=profile,
                opportunity=opp,
                reference_time=ref_time,
            )
            eligibility_results.append(eval_res)

            if eval_res.is_eligible:
                eligible_canonical.append(opp)
                if eval_res.status == EligibilityStatus.ELIGIBLE_WITH_UNCERTAINTY:
                    uncertain_count += 1
                else:
                    eligible_count += 1
            else:
                ineligible_count += 1

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        return DiscoveryRunResponse(
            candidate_id=profile.user_id,
            query_plan=query_plan,
            connector_reports=connector_reports,
            total_discovered=len(all_discovered),
            canonical_count=dedup_result.canonical_count,
            duplicate_count=dedup_result.duplicate_count,
            eligible_count=eligible_count,
            uncertain_count=uncertain_count,
            ineligible_count=ineligible_count,
            canonical_opportunities=dedup_result.canonical_opportunities,
            eligible_opportunities=eligible_canonical,
            duplicate_clusters=dedup_result.clusters,
            duplicate_records=dedup_result.duplicate_records,
            eligibility_results=eligibility_results,
            execution_metadata={
                "duration_ms": elapsed_ms,
                "deduplication_threshold": request.deduplication_threshold,
                "connectors_executed": len(active_connectors),
                "successful_connectors": sum(1 for r in connector_reports if r.status != ConnectorStatus.ERROR),
                "failed_connectors": sum(1 for r in connector_reports if r.status == ConnectorStatus.ERROR),
                "reference_time": ref_time.isoformat(),
            },
        )

    def _resolve_connectors(
        self,
        connector_ids: Optional[list[str]],
        simulate_failure_connector: Optional[str],
        mock_mode: bool = True,
    ) -> list[BaseDiscoveryConnector]:
        """Configures and filters active connectors."""
        if self._connectors is not None:
            base_list = self._connectors
        else:
            base_list = get_default_connectors(
                mock_mode=mock_mode,
                simulate_failure_connector=simulate_failure_connector,
            )

        if not connector_ids:
            return base_list

        allowed = set(connector_ids)
        return [c for c in base_list if c.connector_id in allowed]

    async def _run_connectors_concurrently(
        self,
        connectors: list[BaseDiscoveryConnector],
        query_plan: DiscoveryQueryPlan,
        max_results_per_connector: int,
    ) -> tuple[list[DiscoveryConnectorResult], list[DiscoveryConnectorReport]]:
        """Concurrently queries all connectors with bounded timeout and error shielding.

        Ensures that an exception in any single connector is trapped and logged as
        ConnectorStatus.ERROR while all other results are preserved.
        """
        primary_query = query_plan.all_queries[0]

        async def _invoke_connector(connector: BaseDiscoveryConnector) -> DiscoveryConnectorResult:
            t_start = time.perf_counter()
            try:
                # 5.0 second bounded timeout per connector
                return await asyncio.wait_for(
                    connector.search(primary_query, limit=max_results_per_connector),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                lat = round((time.perf_counter() - t_start) * 1000, 2)
                logger.warning("Connector %s timed out after 5.0s", connector.connector_id)
                return DiscoveryConnectorResult(
                    connector_id=connector.connector_id,
                    source_name=connector.source_name,
                    query_id=primary_query.query_id,
                    status=ConnectorStatus.ERROR,
                    opportunities=[],
                    raw_count=0,
                    latency_ms=lat,
                    error_message="Connector request timed out after 5000ms.",
                )
            except Exception as exc:
                lat = round((time.perf_counter() - t_start) * 1000, 2)
                logger.error("Connector %s raised error: %s", connector.connector_id, exc)
                return DiscoveryConnectorResult(
                    connector_id=connector.connector_id,
                    source_name=connector.source_name,
                    query_id=primary_query.query_id,
                    status=ConnectorStatus.ERROR,
                    opportunities=[],
                    raw_count=0,
                    latency_ms=lat,
                    error_message=f"Connector error: {str(exc)}",
                )

        tasks = [_invoke_connector(c) for c in connectors]
        raw_results = await asyncio.gather(*tasks, return_exceptions=False)

        results: list[DiscoveryConnectorResult] = []
        reports: list[DiscoveryConnectorReport] = []

        for res in raw_results:
            results.append(res)
            reports.append(
                DiscoveryConnectorReport(
                    connector_id=res.connector_id,
                    source_name=res.source_name,
                    status=res.status,
                    raw_count=res.raw_count,
                    latency_ms=res.latency_ms,
                    error_message=res.error_message,
                )
            )

        return results, reports

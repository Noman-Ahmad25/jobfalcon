from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Generic, Optional, Sequence, TypeVar
from pydantic import BaseModel, Field

from app.core.sanitization import sanitize_untrusted_text
from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    OpportunityRepository,
)
from app.modules.deduplication.service import (
    DeduplicationResult,
    deduplicate_opportunities,
)
from app.modules.discovery.connectors import (
    BaseDiscoveryConnector,
    get_default_connectors,
)
from app.modules.discovery.role_mapper import (
    map_profile_to_target_roles,
)
from app.modules.eligibility.engine import evaluate_eligibility
from app.modules.ingestion.importer import IngestionReport, OpportunityImporter
from app.modules.ranking.engine import CandidateJobRankingEngine
from app.schemas.deduplication import OpportunityCluster
from app.schemas.discovery import (
    ConnectorStatus,
    DiscoveryConnectorResult,
    DiscoverySearchQuery,
    RoleMappingTarget,
)
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile
from app.schemas.ranking import RankingResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    """Standardized wrapper for controlled agent tool execution."""

    tool_name: str = Field(..., description="Name of the invoked tool.")
    success: bool = Field(..., description="Whether the tool completed without unhandled exceptions.")
    data: Optional[T] = Field(default=None, description="Output payload on success.")
    error_message: Optional[str] = Field(default=None, description="Error explanation on failure.")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Tool execution duration in milliseconds.")
    provenance: dict[str, Any] = Field(default_factory=dict, description="Execution context and audit data.")


# ==============================================================================
# Tool 1: Candidate Profile Retrieval Tool
# ==============================================================================


class ProfileRetrievalArgs(BaseModel):
    """Arguments for candidate profile retrieval."""

    user_id: str = Field(..., min_length=1, max_length=120, description="Target candidate user identifier.")


class ProfileRetrievalTool:
    """Retrieves validated candidate career profile and evidence from repository."""

    def __init__(self, profile_repo: CandidateProfileRepository) -> None:
        self.profile_repo = profile_repo
        self.tool_name = "profile_retrieval_tool"

    def execute(self, args: ProfileRetrievalArgs) -> ToolResult[CandidateCareerProfile]:
        t0 = time.perf_counter()
        clean_user_id = sanitize_untrusted_text(args.user_id)
        try:
            profile = self.profile_repo.get(clean_user_id)
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            if profile is None:
                return ToolResult(
                    tool_name=self.tool_name,
                    success=False,
                    data=None,
                    error_message=f"Candidate profile '{clean_user_id}' not found in repository.",
                    latency_ms=elapsed,
                    provenance={"user_id": clean_user_id},
                )
            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                data=profile,
                latency_ms=elapsed,
                provenance={"user_id": clean_user_id, "profile_version": profile.profile_version},
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("ProfileRetrievalTool error: %s", exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Profile retrieval failed: {str(exc)}",
                latency_ms=elapsed,
                provenance={"user_id": clean_user_id},
            )


# ==============================================================================
# Tool 2: Role Mapping Tool
# ==============================================================================


class RoleMappingArgs(BaseModel):
    """Arguments for taxonomic skill-to-role mapping."""

    profile: CandidateCareerProfile = Field(..., description="Candidate career profile with assessed skills.")


class RoleMappingTool:
    """Maps candidate skills to canonical O*NET/ESCO role families and generates query templates."""

    def __init__(self) -> None:
        self.tool_name = "role_mapping_tool"

    def execute(self, args: RoleMappingArgs) -> ToolResult[list[RoleMappingTarget]]:
        t0 = time.perf_counter()
        try:
            targets = map_profile_to_target_roles(args.profile)
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                data=targets,
                latency_ms=elapsed,
                provenance={
                    "candidate_id": args.profile.user_id,
                    "target_count": sum(1 for t in targets if t.relationship_type.value == "TARGET"),
                    "adjacent_count": sum(1 for t in targets if t.relationship_type.value == "ADJACENT"),
                },
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("RoleMappingTool error: %s", exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Role mapping failed: {str(exc)}",
                latency_ms=elapsed,
                provenance={"candidate_id": args.profile.user_id},
            )


# ==============================================================================
# Tool 3: Opportunity Search Tool
# ==============================================================================


class OpportunitySearchArgs(BaseModel):
    """Arguments for opportunity source retrieval."""

    connector_id: str = Field(..., description="Identifier of the target connector.")
    query: DiscoverySearchQuery = Field(..., description="Targeted parameterized query.")
    limit: int = Field(default=5, ge=1, le=20, description="Max opportunities to fetch.")


class OpportunitySearchTool:
    """Controlled execution tool for querying discovery connectors with timeouts and error isolation."""

    def __init__(
        self,
        connectors: Optional[list[BaseDiscoveryConnector]] = None,
        mock_mode: bool = True,
        simulate_failure_connector: Optional[str] = None,
    ) -> None:
        self.tool_name = "opportunity_search_tool"
        self._connectors = connectors or get_default_connectors(
            mock_mode=mock_mode,
            simulate_failure_connector=simulate_failure_connector,
        )
        self._connector_map = {c.connector_id: c for c in self._connectors}

    async def execute(self, args: OpportunitySearchArgs) -> ToolResult[DiscoveryConnectorResult]:
        t0 = time.perf_counter()
        cid = args.connector_id
        if cid not in self._connector_map:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Connector '{cid}' is unknown or not configured.",
                latency_ms=elapsed,
                provenance={"connector_id": cid},
            )

        connector = self._connector_map[cid]
        try:
            result = await connector.search(args.query, limit=args.limit)
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            success = result.status != ConnectorStatus.ERROR
            return ToolResult(
                tool_name=self.tool_name,
                success=success,
                data=result,
                error_message=result.error_message if not success else None,
                latency_ms=elapsed,
                provenance={
                    "connector_id": cid,
                    "status": result.status.value,
                    "raw_count": result.raw_count,
                    "query_id": args.query.query_id,
                },
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("OpportunitySearchTool error on %s: %s", cid, exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Connector execution failed: {str(exc)}",
                latency_ms=elapsed,
                provenance={"connector_id": cid},
            )


# ==============================================================================
# Tool 4: Deduplication Tool
# ==============================================================================


class DeduplicationArgs(BaseModel):
    """Arguments for MinHash LSH deduplication."""

    opportunities: list[PolymorphicOpportunity] = Field(..., description="Opportunities to cluster.")
    threshold: float = Field(default=0.85, ge=0.50, le=1.00, description="Jaccard threshold.")


class DeduplicationTool:
    """Clusters cross-source syndicated opportunities using 128-permutation MinHash LSH."""

    def __init__(self) -> None:
        self.tool_name = "deduplication_tool"

    def execute(self, args: DeduplicationArgs) -> ToolResult[DeduplicationResult]:
        t0 = time.perf_counter()
        try:
            result = deduplicate_opportunities(
                opportunities=args.opportunities,
                threshold=args.threshold,
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                data=result,
                latency_ms=elapsed,
                provenance={
                    "total_evaluated": result.total_evaluated,
                    "canonical_count": result.canonical_count,
                    "duplicate_count": result.duplicate_count,
                    "cluster_count": len(result.clusters),
                    "threshold": args.threshold,
                },
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("DeduplicationTool error: %s", exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Deduplication failed: {str(exc)}",
                latency_ms=elapsed,
            )


# ==============================================================================
# Tool 5: Deterministic Eligibility Tool
# ==============================================================================


class DeterministicEligibilityArgs(BaseModel):
    """Arguments for deterministic eligibility evaluation."""

    candidate_profile: CandidateCareerProfile = Field(..., description="Candidate constraints.")
    canonical_opportunities: list[PolymorphicOpportunity] = Field(..., description="List of distinct opportunities.")
    reference_time: Optional[datetime] = Field(default=None, description="Optional baseline evaluation timestamp.")


class DeterministicEligibilityTool:
    """Evaluates candidate constraints against opportunities strictly in pure Python deterministic code."""

    def __init__(self) -> None:
        self.tool_name = "deterministic_eligibility_tool"

    def execute(self, args: DeterministicEligibilityArgs) -> ToolResult[list[EligibilityResult]]:
        t0 = time.perf_counter()
        ref_time = args.reference_time or datetime.now(timezone.utc)
        results: list[EligibilityResult] = []
        try:
            for opp in args.canonical_opportunities:
                eval_res = evaluate_eligibility(
                    candidate=args.candidate_profile,
                    opportunity=opp,
                    reference_time=ref_time,
                )
                results.append(eval_res)

            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            eligible_count = sum(1 for r in results if r.is_eligible)
            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                data=results,
                latency_ms=elapsed,
                provenance={
                    "total_evaluated": len(results),
                    "eligible_count": eligible_count,
                    "ineligible_count": len(results) - eligible_count,
                },
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("DeterministicEligibilityTool error: %s", exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Deterministic eligibility evaluation failed: {str(exc)}",
                latency_ms=elapsed,
            )


# ==============================================================================
# Tool 6: Persistence Tool
# ==============================================================================


class PersistenceArgs(BaseModel):
    """Arguments for saving opportunities and clusters to database."""

    opportunities: list[PolymorphicOpportunity] = Field(..., description="Canonical and duplicate opportunities.")
    clusters: dict[str, OpportunityCluster] = Field(default_factory=dict, description="Duplicate clusters.")


class PersistenceTool:
    """Idempotently saves discovered opportunities and duplicate clusters to repositories."""

    def __init__(
        self,
        opp_repo: OpportunityRepository,
        cluster_repo: DuplicateClusterRepository,
    ) -> None:
        self.tool_name = "persistence_tool"
        self.opp_repo = opp_repo
        self.cluster_repo = cluster_repo
        self.importer = OpportunityImporter(opp_repo=opp_repo, cluster_repo=cluster_repo)

    def execute(self, args: PersistenceArgs) -> ToolResult[IngestionReport]:
        t0 = time.perf_counter()
        try:
            report = self.importer.import_opportunities(
                opportunities=args.opportunities,
                source_system="adaptive_discovery_agent",
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                data=report,
                latency_ms=elapsed,
                provenance={
                    "new_opportunities": report.new_opportunities,
                    "updated_opportunities": report.updated_opportunities,
                    "recorded_duplicate_links": report.recorded_duplicate_links,
                },
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("PersistenceTool error: %s", exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Persistence failed: {str(exc)}",
                latency_ms=elapsed,
            )


# ==============================================================================
# Tool 7: Ranking Tool
# ==============================================================================


class RankingArgs(BaseModel):
    """Arguments for candidate-job ranking and fit scoring."""

    candidate_profile: CandidateCareerProfile = Field(..., description="Target candidate profile.")
    opportunities: list[PolymorphicOpportunity] = Field(..., description="Eligible opportunities to rank.")
    eligibility_results: Optional[list[EligibilityResult]] = Field(default=None, description="Pre-computed eligibility results.")
    weight_profile_name: str = Field(default="DEFAULT", description="Weight profile to apply.")
    custom_weights: Optional[dict[str, float]] = Field(default=None, description="Optional custom weights.")
    top_k: int = Field(default=10, description="Top-K recommendations cutoff.")


class RankingTool:
    """Ranks eligible opportunities using deterministic multi-dimensional fit scoring."""

    def __init__(self, engine: Optional[CandidateJobRankingEngine] = None) -> None:
        self.tool_name = "ranking_tool"
        self.engine = engine or CandidateJobRankingEngine()

    def execute(self, args: RankingArgs) -> ToolResult[RankingResponse]:
        t0 = time.perf_counter()
        try:
            response = self.engine.evaluate_and_rank(
                candidate_profile=args.candidate_profile,
                opportunities=args.opportunities,
                eligibility_results=args.eligibility_results,
                weight_profile_name=args.weight_profile_name,
                custom_weights=args.custom_weights,
                top_k=args.top_k,
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return ToolResult(
                tool_name=self.tool_name,
                success=True,
                data=response,
                latency_ms=elapsed,
                provenance={
                    "total_evaluated": response.total_candidates_evaluated,
                    "total_ranked": response.total_eligible_ranked,
                    "total_excluded": response.total_ineligible_excluded,
                },
            )
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("RankingTool error: %s", exc, exc_info=True)
            return ToolResult(
                tool_name=self.tool_name,
                success=False,
                data=None,
                error_message=f"Ranking failed: {str(exc)}",
                latency_ms=elapsed,
            )


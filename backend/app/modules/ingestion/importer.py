from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.db.repositories.interfaces import (
    DuplicateClusterRepository,
    OpportunityRepository,
)
from app.modules.deduplication.service import DeduplicationService
from app.modules.ingestion.adapter import BaseOpportunityAdapter
from app.schemas.opportunity import PolymorphicOpportunity


@dataclass(frozen=True)
class IngestionReport:
    """Summary metrics of an opportunity ingestion run."""

    total_fetched: int
    new_opportunities: int
    updated_opportunities: int
    expired_opportunities: int
    canonical_opportunities: int
    duplicate_opportunities: int
    recorded_duplicate_links: int


class OpportunityImporter:
    """Ingestion orchestrator managing incoming career opportunities.

    Responsibilities:
    - Ingests feeds from BaseOpportunityAdapter implementations.
    - Runs early deterministic deduplication before database persistence.
    - Handles new, updated, and expired/closed listings.
    - Idempotently persists opportunities and duplicate cluster provenance.
    """

    def __init__(
        self,
        opp_repo: OpportunityRepository,
        cluster_repo: DuplicateClusterRepository,
        dedup_service: Optional[DeduplicationService] = None,
    ) -> None:
        self.opp_repo = opp_repo
        self.cluster_repo = cluster_repo
        self.dedup_service = dedup_service or DeduplicationService(threshold=0.85)

    def import_from_adapter(
        self,
        adapter: BaseOpportunityAdapter,
        reference_time: Optional[datetime] = None,
    ) -> IngestionReport:
        """Imports opportunities directly from an external adapter."""
        opportunities = adapter.fetch_opportunities()
        return self.import_opportunities(
            opportunities=opportunities,
            source_system=adapter.source_name,
            reference_time=reference_time,
        )

    def import_opportunities(
        self,
        opportunities: Sequence[PolymorphicOpportunity],
        source_system: str = "generic",
        reference_time: Optional[datetime] = None,
    ) -> IngestionReport:
        """Ingests and persists a batch of opportunities with deterministic deduplication.

        Guarantees:
        - Deterministic duplicate clustering before saving.
        - Idempotent repeated imports: re-importing identical records causes 0 extra rows or spurious links.
        - Preservation of all original source identifiers, URLs, and timestamps.
        """
        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if not opportunities:
            return IngestionReport(
                total_fetched=0,
                new_opportunities=0,
                updated_opportunities=0,
                expired_opportunities=0,
                canonical_opportunities=0,
                duplicate_opportunities=0,
                recorded_duplicate_links=0,
            )

        # 1. Early deterministic deduplication across the batch
        dedup_result = self.dedup_service.deduplicate_batch(opportunities)

        new_count = 0
        updated_count = 0
        expired_count = 0

        # Combine both canonical and duplicate opportunities for persistence
        all_processed: list[PolymorphicOpportunity] = (
            dedup_result.canonical_opportunities + dedup_result.duplicate_opportunities
        )

        for opp in all_processed:
            # Check expiration / closed status
            is_expired = False
            deadline = opp.eligibility_rules.application_deadline
            if deadline is not None:
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                if deadline < now:
                    is_expired = True

            if opp.category_specific_attributes.get("is_closed") is True:
                is_expired = True

            if is_expired:
                expired_count += 1

            source_job_id = opp.category_specific_attributes.get("source_job_id")

            # Check existing listing
            existing = self.opp_repo.get(opp.opportunity_id)
            if existing is None and source_job_id:
                existing = self.opp_repo.get_by_source(source_system, source_job_id)

            if existing is not None:
                # Check if listing changed
                has_changed = (
                    existing.title != opp.title
                    or existing.sanitized_summary != opp.sanitized_summary
                    or existing.minhash_signature_hex != opp.minhash_signature_hex
                    or existing.category_specific_attributes != opp.category_specific_attributes
                )
                if has_changed:
                    updated_count += 1
                # Persist updated state
                self.opp_repo.save(opp, source_system=source_system, source_job_id=source_job_id)
            else:
                new_count += 1
                self.opp_repo.save(opp, source_system=source_system, source_job_id=source_job_id)

        # 2. Persist duplicate clusters and linkage records
        recorded_links = 0
        for cluster in dedup_result.clusters.values():
            if cluster.duplicate_records:
                self.cluster_repo.save_cluster(cluster)
                recorded_links += len(cluster.duplicate_records)

        return IngestionReport(
            total_fetched=len(opportunities),
            new_opportunities=new_count,
            updated_opportunities=updated_count,
            expired_opportunities=expired_count,
            canonical_opportunities=dedup_result.canonical_count,
            duplicate_opportunities=dedup_result.duplicate_count,
            recorded_duplicate_links=recorded_links,
        )

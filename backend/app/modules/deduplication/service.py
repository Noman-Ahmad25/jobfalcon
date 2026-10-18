from __future__ import annotations

import uuid
from typing import Optional, Sequence

from app.modules.deduplication.lsh import MinHashLSHIndex
from app.modules.deduplication.minhash import (
    MinHashSignatureGenerator,
    _DEFAULT_GENERATOR,
)
from app.modules.deduplication.normalization import build_opportunity_comparison_text
from app.schemas.deduplication import (
    DeduplicationResult,
    DuplicateRecord,
    OpportunityCluster,
)
from app.schemas.opportunity import PolymorphicOpportunity


class DeduplicationService:
    """Service governing near-duplicate opportunity detection, clustering, and provenance preservation.

    Guarantees:
    - Never deletes or irreversibly merges distinct listings.
    - Retains all source URLs, original identifiers, and metadata.
    - Avoids matching on titles alone by comparing composite normalized content.
    - Bounded sub-linear indexing via 128-permutation MinHash and LSH.
    """

    def __init__(
        self,
        threshold: float = 0.85,
        num_perm: int = 128,
        num_bands: int = 16,
        generator: Optional[MinHashSignatureGenerator] = None,
    ) -> None:
        self.threshold = threshold
        self.generator = generator or _DEFAULT_GENERATOR
        self.index = MinHashLSHIndex(
            threshold=threshold,
            num_perm=num_perm,
            num_bands=num_bands,
        )
        self.canonical_opportunities: dict[str, PolymorphicOpportunity] = {}
        self.clusters: dict[str, OpportunityCluster] = {}

    def process_opportunity(
        self, opportunity: PolymorphicOpportunity
    ) -> tuple[bool, Optional[DuplicateRecord]]:
        """Processes an individual opportunity, updating its MinHash digest and checking for near-duplicates.

        Returns:
            tuple[bool, Optional[DuplicateRecord]]: (is_duplicate, duplicate_record_if_matched)
        """
        # Construct composite text to avoid superficial title-only matches
        comparison_text = build_opportunity_comparison_text(
            title=opportunity.title,
            company_name=opportunity.company_name,
            description_summary=opportunity.sanitized_summary,
        )

        # Generate 128-permutation signature and deterministic 64-char hex digest
        sig, hex_digest = self.generator.generate_from_text(comparison_text, k=3)
        opportunity.minhash_signature_hex = hex_digest

        # Query LSH index for near-duplicate candidates meeting threshold
        matches = self.index.query(sig, min_similarity=self.threshold)

        if matches:
            # Match detected: select highest similarity canonical parent
            canonical_id, similarity = matches[0]
            record = DuplicateRecord(
                duplicate_id=f"dup-{uuid.uuid4().hex[:12]}",
                canonical_opportunity_id=canonical_id,
                duplicate_opportunity_id=opportunity.opportunity_id,
                similarity_score=round(similarity, 4),
                similarity_method="MINHASH_ESTIMATE",
                source_url=str(opportunity.source_url),
                reasons=[f"MINHASH_JACCARD_SIMILARITY_EXCEEDS_{int(self.threshold*100)}PCT"],
            )

            opportunity.is_duplicate = True

            # Update canonical cluster metadata
            if canonical_id in self.clusters:
                cluster = self.clusters[canonical_id]
                cluster.duplicate_records.append(record)
                if str(opportunity.source_url) not in cluster.all_source_urls:
                    cluster.all_source_urls.append(str(opportunity.source_url))
                cluster.cluster_size = 1 + len(cluster.duplicate_records)

            return True, record

        # No match: this listing is canonical
        opportunity.is_duplicate = False
        self.index.insert(
            key=opportunity.opportunity_id,
            signature=sig,
            metadata={"title": opportunity.title, "company": opportunity.company_name},
        )
        self.canonical_opportunities[opportunity.opportunity_id] = opportunity

        # Initialize cluster
        self.clusters[opportunity.opportunity_id] = OpportunityCluster(
            canonical_opportunity=opportunity,
            duplicate_records=[],
            all_source_urls=[str(opportunity.source_url)],
            cluster_size=1,
        )

        return False, None

    def deduplicate_batch(
        self, opportunities: Sequence[PolymorphicOpportunity]
    ) -> DeduplicationResult:
        """Processes a batch of opportunity listings, returning canonical and duplicate sets with full provenance."""
        canonical_list: list[PolymorphicOpportunity] = []
        duplicate_list: list[PolymorphicOpportunity] = []
        duplicate_records: list[DuplicateRecord] = []

        for opp in opportunities:
            # Create isolated copy to avoid unexpected side effects if caller re-uses objects
            opp_copy = opp.model_copy(deep=True)
            is_dup, record = self.process_opportunity(opp_copy)

            if is_dup and record is not None:
                duplicate_list.append(opp_copy)
                duplicate_records.append(record)
            else:
                canonical_list.append(opp_copy)

        return DeduplicationResult(
            canonical_opportunities=canonical_list,
            duplicate_opportunities=duplicate_list,
            duplicate_records=duplicate_records,
            clusters=dict(self.clusters),
            total_evaluated=len(opportunities),
            canonical_count=len(canonical_list),
            duplicate_count=len(duplicate_list),
        )


def deduplicate_opportunities(
    opportunities: Sequence[PolymorphicOpportunity],
    threshold: float = 0.85,
) -> DeduplicationResult:
    """Convenience functional interface for batch deduplicating opportunities."""
    service = DeduplicationService(threshold=threshold)
    return service.deduplicate_batch(opportunities)

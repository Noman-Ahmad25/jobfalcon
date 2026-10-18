from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    EligibilityAuditRepository,
    OpportunityRepository,
)
from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile


class InMemoryCandidateProfileRepository(CandidateProfileRepository):
    """In-memory dictionary-backed repository for CandidateCareerProfile."""

    def __init__(self) -> None:
        self._storage: Dict[str, CandidateCareerProfile] = {}

    def get(self, user_id: str) -> Optional[CandidateCareerProfile]:
        profile = self._storage.get(user_id)
        if profile is None:
            return None
        # Return a copy to ensure caller mutations don't alter stored state
        return CandidateCareerProfile.model_validate(profile.model_dump())

    def save(self, profile: CandidateCareerProfile) -> None:
        self._storage[profile.user_id] = CandidateCareerProfile.model_validate(
            profile.model_dump()
        )

    def delete(self, user_id: str) -> bool:
        if user_id in self._storage:
            del self._storage[user_id]
            return True
        return False

    def list_all(self) -> List[CandidateCareerProfile]:
        return [
            CandidateCareerProfile.model_validate(p.model_dump())
            for p in self._storage.values()
        ]

    def clear(self) -> None:
        self._storage.clear()


class InMemoryOpportunityRepository(OpportunityRepository):
    """In-memory dictionary-backed repository for PolymorphicOpportunity."""

    def __init__(self) -> None:
        self._storage: Dict[str, PolymorphicOpportunity] = {}
        self._source_index: Dict[Tuple[str, str], str] = {}
        self._active_status: Dict[str, bool] = {}

    def get(self, opportunity_id: str) -> Optional[PolymorphicOpportunity]:
        opp = self._storage.get(opportunity_id)
        if opp is None:
            return None
        return PolymorphicOpportunity.model_validate(opp.model_dump())

    def get_by_source(
        self, source_system: str, source_job_id: str
    ) -> Optional[PolymorphicOpportunity]:
        opp_id = self._source_index.get((source_system, source_job_id))
        if opp_id is None:
            return None
        return self.get(opp_id)

    def save(
        self,
        opportunity: PolymorphicOpportunity,
        source_system: str = "generic",
        source_job_id: Optional[str] = None,
    ) -> None:
        opp_copy = PolymorphicOpportunity.model_validate(opportunity.model_dump())
        self._storage[opp_copy.opportunity_id] = opp_copy
        self._active_status[opp_copy.opportunity_id] = True

        effective_source_job_id = (
            source_job_id or opp_copy.category_specific_attributes.get("source_job_id")
        )
        if effective_source_job_id:
            self._source_index[(source_system, effective_source_job_id)] = opp_copy.opportunity_id

    def save_batch(
        self,
        opportunities: Sequence[PolymorphicOpportunity],
        source_system: str = "generic",
    ) -> None:
        for opp in opportunities:
            self.save(opp, source_system=source_system)

    def mark_inactive(self, opportunity_id: str) -> None:
        if opportunity_id in self._storage:
            self._active_status[opportunity_id] = False

    def list_all(self, active_only: bool = True) -> List[PolymorphicOpportunity]:
        results: List[PolymorphicOpportunity] = []
        for opp_id, opp in self._storage.items():
            if not active_only or self._active_status.get(opp_id, True):
                results.append(PolymorphicOpportunity.model_validate(opp.model_dump()))
        return results

    def count(self, active_only: bool = True) -> int:
        if not active_only:
            return len(self._storage)
        return sum(1 for is_act in self._active_status.values() if is_act)

    def clear(self) -> None:
        self._storage.clear()
        self._source_index.clear()
        self._active_status.clear()


class InMemoryDuplicateClusterRepository(DuplicateClusterRepository):
    """In-memory dictionary-backed repository for OpportunityCluster and DuplicateRecord."""

    def __init__(self, opp_repo: Optional[OpportunityRepository] = None) -> None:
        self.opp_repo = opp_repo or InMemoryOpportunityRepository()
        self._clusters: Dict[str, OpportunityCluster] = {}
        self._duplicate_records: Dict[str, List[DuplicateRecord]] = {}

    def get_cluster(self, canonical_opportunity_id: str) -> Optional[OpportunityCluster]:
        cluster = self._clusters.get(canonical_opportunity_id)
        if cluster is None:
            return None
        return OpportunityCluster.model_validate(cluster.model_dump())

    def save_cluster(self, cluster: OpportunityCluster) -> None:
        cluster_copy = OpportunityCluster.model_validate(cluster.model_dump())
        self._clusters[cluster_copy.canonical_opportunity.opportunity_id] = cluster_copy
        self._duplicate_records[cluster_copy.canonical_opportunity.opportunity_id] = [
            DuplicateRecord.model_validate(r.model_dump())
            for r in cluster_copy.duplicate_records
        ]

    def record_duplicate(self, record: DuplicateRecord) -> None:
        rec_copy = DuplicateRecord.model_validate(record.model_dump())
        canon_id = rec_copy.canonical_opportunity_id

        if canon_id not in self._duplicate_records:
            self._duplicate_records[canon_id] = []

        existing = [
            r
            for r in self._duplicate_records[canon_id]
            if r.duplicate_id == rec_copy.duplicate_id
        ]
        if not existing:
            self._duplicate_records[canon_id].append(rec_copy)

        canonical_opp = self.opp_repo.get(canon_id)
        if canonical_opp:
            all_urls = [str(canonical_opp.source_url)]
            for r in self._duplicate_records[canon_id]:
                if r.source_url not in all_urls:
                    all_urls.append(r.source_url)

            cluster = OpportunityCluster(
                canonical_opportunity=canonical_opp,
                duplicate_records=self._duplicate_records[canon_id],
                all_source_urls=all_urls,
                cluster_size=1 + len(self._duplicate_records[canon_id]),
            )
            self._clusters[canon_id] = cluster

    def list_clusters(self) -> List[OpportunityCluster]:
        return [
            OpportunityCluster.model_validate(c.model_dump())
            for c in self._clusters.values()
        ]

    def clear(self) -> None:
        self._clusters.clear()
        self._duplicate_records.clear()


class InMemoryEligibilityAuditRepository(EligibilityAuditRepository):
    """In-memory dictionary-backed repository for EligibilityResult audits."""

    def __init__(self) -> None:
        self._audits: List[EligibilityResult] = []

    def save_audit(self, result: EligibilityResult) -> None:
        self._audits.append(EligibilityResult.model_validate(result.model_dump()))

    def get_latest_audit(
        self, opportunity_id: str, user_id: str
    ) -> Optional[EligibilityResult]:
        matching = [
            a
            for a in self._audits
            if a.opportunity_id == opportunity_id and a.user_id == user_id
        ]
        if not matching:
            return None
        matching.sort(key=lambda a: a.evaluated_at, reverse=True)
        return EligibilityResult.model_validate(matching[0].model_dump())

    def list_audits_for_user(self, user_id: str) -> List[EligibilityResult]:
        matching = [a for a in self._audits if a.user_id == user_id]
        matching.sort(key=lambda a: a.evaluated_at, reverse=True)
        return [EligibilityResult.model_validate(a.model_dump()) for a in matching]

    def prune_older_than(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        initial_len = len(self._audits)
        self._audits = [a for a in self._audits if a.evaluated_at >= cutoff]
        return initial_len - len(self._audits)

    def clear(self) -> None:
        self._audits.clear()

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from app.db.repositories.interfaces import (
    CandidateActionRepository,
    CandidateProfileRepository,
    CareerMemoryRepository,
    DiscoveryRunRepository,
    DuplicateClusterRepository,
    EligibilityAuditRepository,
    MarketReportRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.schemas.action import (
    ActionType,
    CandidateActionsSummary,
    CandidateOpportunityActionRecord,
)
from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import EligibilityResult
from app.schemas.market import MarketResearchReportRecord
from app.schemas.memory import (
    CandidateCareerMemoryItem,
    MemoryType,
    ProvenanceLevel,
)
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.orchestration import DiscoveryRun, DiscoveryRunStatus
from app.schemas.profile import CandidateCareerProfile
from app.schemas.ranking import RankingResponse


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


class InMemoryRecommendationRepository(RecommendationRepository):
    """In-memory dictionary-backed repository for RankingResponse evaluations."""

    def __init__(self) -> None:
        self._evaluations: List[RankingResponse] = []

    def save_evaluation(self, response: RankingResponse) -> None:
        self._evaluations.append(
            RankingResponse.model_validate(response.model_dump())
        )

    def get_latest_evaluation(self, user_id: str) -> Optional[RankingResponse]:
        matching = [e for e in self._evaluations if e.candidate_id == user_id]
        if not matching:
            return None
        matching.sort(key=lambda e: e.evaluation_timestamp, reverse=True)
        return RankingResponse.model_validate(matching[0].model_dump())

    def list_evaluations_for_user(self, user_id: str) -> List[RankingResponse]:
        matching = [e for e in self._evaluations if e.candidate_id == user_id]
        matching.sort(key=lambda e: e.evaluation_timestamp, reverse=True)
        return [RankingResponse.model_validate(e.model_dump()) for e in matching]

    def clear(self) -> None:
        self._evaluations.clear()


class InMemoryDiscoveryRunRepository(DiscoveryRunRepository):
    """In-memory dictionary-backed repository for DiscoveryRun lifecycle states."""

    TERMINAL_STATUSES = {
        DiscoveryRunStatus.COMPLETED,
        DiscoveryRunStatus.FAILED,
        DiscoveryRunStatus.CANCELLED,
        DiscoveryRunStatus.PARTIALLY_COMPLETED,
    }

    def __init__(self) -> None:
        self._runs: Dict[str, DiscoveryRun] = {}

    def save(self, run: DiscoveryRun) -> None:
        self._runs[run.run_id] = DiscoveryRun.model_validate(run.model_dump())

    def get(self, run_id: str) -> Optional[DiscoveryRun]:
        run = self._runs.get(run_id)
        if run is None:
            return None
        return DiscoveryRun.model_validate(run.model_dump())

    def get_latest_for_candidate(self, candidate_id: str) -> Optional[DiscoveryRun]:
        matching = [r for r in self._runs.values() if r.candidate_id == candidate_id]
        if not matching:
            return None
        matching.sort(key=lambda r: r.created_at, reverse=True)
        return DiscoveryRun.model_validate(matching[0].model_dump())

    def list_for_candidate(self, candidate_id: str, limit: int = 10) -> List[DiscoveryRun]:
        matching = [r for r in self._runs.values() if r.candidate_id == candidate_id]
        matching.sort(key=lambda r: r.created_at, reverse=True)
        return [DiscoveryRun.model_validate(r.model_dump()) for r in matching[:limit]]

    def get_active_run_for_candidate(self, candidate_id: str) -> Optional[DiscoveryRun]:
        matching = [
            r for r in self._runs.values()
            if r.candidate_id == candidate_id and r.status not in self.TERMINAL_STATUSES
        ]
        if not matching:
            return None
        matching.sort(key=lambda r: r.created_at, reverse=True)
        return DiscoveryRun.model_validate(matching[0].model_dump())

    def clear(self) -> None:
        self._runs.clear()


class InMemoryCandidateActionRepository(CandidateActionRepository):
    """In-memory event-sourced repository for candidate opportunity interaction transitions."""

    def __init__(self) -> None:
        self._actions: list[CandidateOpportunityActionRecord] = []

    def record_action(self, action: CandidateOpportunityActionRecord) -> None:
        self._actions.append(CandidateOpportunityActionRecord.model_validate(action.model_dump()))

    def get_latest_actions(self, user_id: str) -> dict[str, CandidateOpportunityActionRecord]:
        user_actions = [a for a in self._actions if a.user_id == user_id]
        # Sort chronologically ascending so later ones override
        user_actions.sort(key=lambda a: a.created_at)
        latest: dict[str, CandidateOpportunityActionRecord] = {}
        for a in user_actions:
            latest[a.opportunity_id] = CandidateOpportunityActionRecord.model_validate(a.model_dump())
        return latest

    def get_actions_summary(self, user_id: str) -> CandidateActionsSummary:
        latest = self.get_latest_actions(user_id)
        saved = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.SAVED]
        applied = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.APPLIED]
        dismissed = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.DISMISSED]
        overridden = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.SOFT_OVERRIDDEN]
        user_total = sum(1 for a in self._actions if a.user_id == user_id)

        return CandidateActionsSummary(
            user_id=user_id,
            saved_opportunity_ids=saved,
            applied_opportunity_ids=applied,
            dismissed_opportunity_ids=dismissed,
            soft_overridden_opportunity_ids=overridden,
            latest_actions_by_opp={opp_id: r.action_type for opp_id, r in latest.items()},
            total_actions_recorded=user_total,
        )

    def get_action_history(
        self, user_id: str, opportunity_id: Optional[str] = None, limit: int = 100
    ) -> list[CandidateOpportunityActionRecord]:
        matching = [
            a for a in self._actions
            if a.user_id == user_id and (opportunity_id is None or a.opportunity_id == opportunity_id)
        ]
        matching.sort(key=lambda a: a.created_at, reverse=True)
        return [CandidateOpportunityActionRecord.model_validate(a.model_dump()) for a in matching[:limit]]

    def get_overridden_opportunity_ids(self, user_id: str) -> list[str]:
        latest = self.get_latest_actions(user_id)
        return [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.SOFT_OVERRIDDEN]

    def clear(self) -> None:
        self._actions.clear()


class InMemoryCareerMemoryRepository(CareerMemoryRepository):
    """In-memory repository preserving versioned candidate career understanding."""

    def __init__(self) -> None:
        self._memories: dict[str, CandidateCareerMemoryItem] = {}

    def add_memory(self, memory: CandidateCareerMemoryItem) -> None:
        self._memories[memory.memory_id] = CandidateCareerMemoryItem.model_validate(memory.model_dump())

    def get_memory(self, memory_id: str) -> Optional[CandidateCareerMemoryItem]:
        item = self._memories.get(memory_id)
        if not item:
            return None
        return CandidateCareerMemoryItem.model_validate(item.model_dump())

    def update_memory(
        self,
        user_id: str,
        current_memory_id: str,
        new_statement: str,
        change_reason: str,
        provenance_level: Optional[ProvenanceLevel] = None,
        confidence_score: Optional[float] = None,
    ) -> CandidateCareerMemoryItem:
        current = self._memories.get(current_memory_id)
        if not current or current.user_id != user_id:
            raise ValueError(f"Memory item '{current_memory_id}' not found for user '{user_id}'.")

        now = datetime.now(timezone.utc)
        new_id = f"mem_{uuid.uuid4().hex[:12]}"
        new_version = current.version + 1
        prov = provenance_level or current.provenance_level
        conf = confidence_score if confidence_score is not None else current.confidence_score

        # Supersede current
        current_dump = current.model_dump()
        current_dump["is_active"] = False
        current_dump["superseded_by"] = new_id
        current_dump["effective_to"] = now
        self._memories[current_memory_id] = CandidateCareerMemoryItem.model_validate(current_dump)

        # Create new version
        new_item = CandidateCareerMemoryItem(
            memory_id=new_id,
            user_id=user_id,
            memory_type=current.memory_type,
            statement=new_statement,
            provenance_level=prov,
            source_context=current.source_context,
            confidence_score=conf,
            version=new_version,
            superseded_by=None,
            change_reason=change_reason,
            is_active=True,
            effective_from=now,
            effective_to=None,
            created_at=now,
        )
        self._memories[new_id] = new_item
        return CandidateCareerMemoryItem.model_validate(new_item.model_dump())

    def deactivate_memory(self, user_id: str, memory_id: str, reason: str) -> bool:
        current = self._memories.get(memory_id)
        if not current or current.user_id != user_id or not current.is_active:
            return False

        now = datetime.now(timezone.utc)
        d = current.model_dump()
        d["is_active"] = False
        d["change_reason"] = reason
        d["effective_to"] = now
        self._memories[memory_id] = CandidateCareerMemoryItem.model_validate(d)
        return True

    def list_active_memories(
        self, user_id: str, memory_type: Optional[MemoryType] = None
    ) -> list[CandidateCareerMemoryItem]:
        matching = [
            m for m in self._memories.values()
            if m.user_id == user_id and m.is_active and (memory_type is None or m.memory_type == memory_type)
        ]
        matching.sort(key=lambda m: m.created_at, reverse=True)
        return [CandidateCareerMemoryItem.model_validate(m.model_dump()) for m in matching]

    def get_memory_history(self, user_id: str, memory_id: str) -> list[CandidateCareerMemoryItem]:
        target = self._memories.get(memory_id)
        if not target or target.user_id != user_id:
            return []

        matching = [
            m for m in self._memories.values()
            if m.user_id == user_id and m.memory_type == target.memory_type
        ]
        matching.sort(key=lambda m: m.version)
        return [CandidateCareerMemoryItem.model_validate(m.model_dump()) for m in matching]

    def list_all_memories_for_candidate(
        self, user_id: str, include_inactive: bool = False
    ) -> list[CandidateCareerMemoryItem]:
        matching = [
            m for m in self._memories.values()
            if m.user_id == user_id and (include_inactive or m.is_active)
        ]
        matching.sort(key=lambda m: (m.version, m.created_at), reverse=True)
        return [CandidateCareerMemoryItem.model_validate(m.model_dump()) for m in matching]

    def clear(self) -> None:
        self._memories.clear()


class InMemoryMarketReportRepository(MarketReportRepository):
    """In-memory dictionary-backed repository for MarketResearchReportRecord."""

    def __init__(self) -> None:
        self._reports: dict[str, MarketResearchReportRecord] = {}

    def save_report(self, report: MarketResearchReportRecord) -> None:
        self._reports[report.report_id] = MarketResearchReportRecord.model_validate(report.model_dump())

    def get_report(
        self, role_title: str, country_code: str, max_age_hours: int = 48
    ) -> Optional[MarketResearchReportRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        matching = [
            r for r in self._reports.values()
            if r.role_title.strip().lower() == role_title.strip().lower()
            and r.country_code.strip().lower() == country_code.strip().lower()
            and r.generated_at >= cutoff
        ]
        if not matching:
            return None
        matching.sort(key=lambda r: r.generated_at, reverse=True)
        return MarketResearchReportRecord.model_validate(matching[0].model_dump())

    def list_reports(self, limit: int = 20) -> list[MarketResearchReportRecord]:
        items = list(self._reports.values())
        items.sort(key=lambda r: r.generated_at, reverse=True)
        return [MarketResearchReportRecord.model_validate(r.model_dump()) for r in items[:limit]]

    def clear(self) -> None:
        self._reports.clear()





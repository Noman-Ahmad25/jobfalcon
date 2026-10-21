from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile
from app.schemas.ranking import RankingResponse


class CandidateProfileRepository(ABC):
    """Abstract port for candidate career profile persistence."""

    @abstractmethod
    def get(self, user_id: str) -> Optional[CandidateCareerProfile]:
        """Retrieves a candidate profile by user_id."""
        raise NotImplementedError

    @abstractmethod
    def save(self, profile: CandidateCareerProfile) -> None:
        """Persists or updates a candidate profile with its skills and evidence records."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """Deletes a candidate profile and associated skills/evidence."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[CandidateCareerProfile]:
        """Lists all registered candidate profiles."""
        raise NotImplementedError


class OpportunityRepository(ABC):
    """Abstract port for career opportunity listings persistence."""

    @abstractmethod
    def get(self, opportunity_id: str) -> Optional[PolymorphicOpportunity]:
        """Retrieves an opportunity by primary opportunity_id."""
        raise NotImplementedError

    @abstractmethod
    def get_by_source(
        self, source_system: str, source_job_id: str
    ) -> Optional[PolymorphicOpportunity]:
        """Retrieves an opportunity by source board identifier (e.g. ('greenhouse', '12345'))."""
        raise NotImplementedError

    @abstractmethod
    def save(
        self,
        opportunity: PolymorphicOpportunity,
        source_system: str = "generic",
        source_job_id: Optional[str] = None,
    ) -> None:
        """Persists or updates an opportunity listing with source provenance."""
        raise NotImplementedError

    @abstractmethod
    def save_batch(
        self,
        opportunities: Sequence[PolymorphicOpportunity],
        source_system: str = "generic",
    ) -> None:
        """Persists a batch of opportunity listings inside a transaction."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self, active_only: bool = True) -> list[PolymorphicOpportunity]:
        """Lists stored opportunities with optional filtering for active listings."""
        raise NotImplementedError

    @abstractmethod
    def count(self, active_only: bool = True) -> int:
        """Returns the total number of stored opportunities."""
        raise NotImplementedError


class DuplicateClusterRepository(ABC):
    """Abstract port for near-duplicate opportunity clusters and provenance."""

    @abstractmethod
    def get_cluster(self, canonical_opportunity_id: str) -> Optional[OpportunityCluster]:
        """Retrieves an opportunity cluster and its duplicate member records."""
        raise NotImplementedError

    @abstractmethod
    def save_cluster(self, cluster: OpportunityCluster) -> None:
        """Persists or updates a duplicate cluster and its member records."""
        raise NotImplementedError

    @abstractmethod
    def record_duplicate(self, record: DuplicateRecord) -> None:
        """Records a new duplicate linkage event to a canonical parent."""
        raise NotImplementedError

    @abstractmethod
    def list_clusters(self) -> list[OpportunityCluster]:
        """Lists all recorded duplicate clusters."""
        raise NotImplementedError


class EligibilityAuditRepository(ABC):
    """Abstract port for deterministic eligibility evaluation audit logs."""

    @abstractmethod
    def save_audit(self, result: EligibilityResult) -> None:
        """Persists a deterministic eligibility evaluation result."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_audit(
        self, opportunity_id: str, user_id: str
    ) -> Optional[EligibilityResult]:
        """Retrieves the most recent evaluation result for a candidate/opportunity pair."""
        raise NotImplementedError

    @abstractmethod
    def list_audits_for_user(self, user_id: str) -> list[EligibilityResult]:
        """Lists all evaluation audits for a specific candidate."""
        raise NotImplementedError

    @abstractmethod
    def prune_older_than(self, days: int) -> int:
        """Prunes historical evaluation audit logs older than the specified retention window."""
        raise NotImplementedError


class RecommendationRepository(ABC):
    """Abstract port for recommendation evaluations and score breakdowns."""

    @abstractmethod
    def save_evaluation(self, response: RankingResponse) -> None:
        """Persists a full ranking evaluation run."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_evaluation(self, user_id: str) -> Optional[RankingResponse]:
        """Retrieves the latest ranking evaluation for a candidate."""
        raise NotImplementedError

    @abstractmethod
    def list_evaluations_for_user(self, user_id: str) -> list[RankingResponse]:
        """Lists historical ranking evaluations for a candidate."""
        raise NotImplementedError


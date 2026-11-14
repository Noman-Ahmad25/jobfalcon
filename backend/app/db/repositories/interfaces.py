from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from app.schemas.action import (
    ActionType,
    CandidateActionsSummary,
    CandidateOpportunityActionRecord,
)
from app.schemas.career_path import (
    ActionProgressStatus,
    CareerPathAssessmentResponse,
    DevelopmentActionItem,
    PersonalizedDevelopmentPlan,
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
from app.schemas.orchestration import DiscoveryRun
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


class CareerPathRepository(ABC):
    """Abstract port for career path assessments and personalized development plan persistence."""

    @abstractmethod
    def save_assessment(self, response: CareerPathAssessmentResponse) -> None:
        """Persists a complete career path assessment."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_assessment(self, user_id: str) -> Optional[CareerPathAssessmentResponse]:
        """Retrieves the most recent career path assessment for a candidate."""
        raise NotImplementedError

    @abstractmethod
    def save_development_plan(self, plan: PersonalizedDevelopmentPlan) -> None:
        """Persists or updates a personalized development plan."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_development_plan(self, user_id: str) -> Optional[PersonalizedDevelopmentPlan]:
        """Retrieves the latest development plan for a candidate."""
        raise NotImplementedError

    @abstractmethod
    def update_action_progress(
        self,
        user_id: str,
        action_id: str,
        status: ActionProgressStatus,
        artifact_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[DevelopmentActionItem]:
        """Updates the status and artifact provenance for a specific development action."""
        raise NotImplementedError


class DiscoveryRunRepository(ABC):
    """Abstract port for persistent discovery run states and lifecycle telemetry."""

    @abstractmethod
    def save(self, run: DiscoveryRun) -> None:
        """Persists or updates a discovery run."""
        raise NotImplementedError

    @abstractmethod
    def get(self, run_id: str) -> Optional[DiscoveryRun]:
        """Retrieves a discovery run by its run_id."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_for_candidate(self, candidate_id: str) -> Optional[DiscoveryRun]:
        """Retrieves the most recent discovery run for a candidate."""
        raise NotImplementedError

    @abstractmethod
    def list_for_candidate(self, candidate_id: str, limit: int = 10) -> list[DiscoveryRun]:
        """Lists historical discovery runs for a candidate."""
        raise NotImplementedError

    @abstractmethod
    def get_active_run_for_candidate(self, candidate_id: str) -> Optional[DiscoveryRun]:
        """Retrieves any currently executing (non-terminal) discovery run for a candidate."""
        raise NotImplementedError


class CandidateActionRepository(ABC):
    """Abstract port for candidate opportunity interaction tracking and history."""

    @abstractmethod
    def record_action(self, action: CandidateOpportunityActionRecord) -> None:
        """Records an immutable opportunity action transition event."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_actions(self, user_id: str) -> dict[str, CandidateOpportunityActionRecord]:
        """Returns map of opportunity_id to latest action record for user."""
        raise NotImplementedError

    @abstractmethod
    def get_actions_summary(self, user_id: str) -> CandidateActionsSummary:
        """Returns consolidated interaction summary (saved, applied, dismissed, soft-overridden)."""
        raise NotImplementedError

    @abstractmethod
    def get_action_history(
        self, user_id: str, opportunity_id: Optional[str] = None, limit: int = 100
    ) -> list[CandidateOpportunityActionRecord]:
        """Retrieves event-sourced action transition audit trail."""
        raise NotImplementedError

    @abstractmethod
    def get_overridden_opportunity_ids(self, user_id: str) -> list[str]:
        """Returns list of opportunity IDs currently soft-overridden by the candidate."""
        raise NotImplementedError


class CareerMemoryRepository(ABC):
    """Abstract port for persistent versioned candidate career memory."""

    @abstractmethod
    def add_memory(self, memory: CandidateCareerMemoryItem) -> None:
        """Persists a new versioned career memory fact."""
        raise NotImplementedError

    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[CandidateCareerMemoryItem]:
        """Retrieves a specific memory item by memory_id."""
        raise NotImplementedError

    @abstractmethod
    def update_memory(
        self,
        user_id: str,
        current_memory_id: str,
        new_statement: str,
        change_reason: str,
        provenance_level: Optional[ProvenanceLevel] = None,
        confidence_score: Optional[float] = None,
    ) -> CandidateCareerMemoryItem:
        """Supersedes existing memory fact with version increment and links history."""
        raise NotImplementedError

    @abstractmethod
    def deactivate_memory(self, user_id: str, memory_id: str, reason: str) -> bool:
        """Deactivates/archives an active memory fact."""
        raise NotImplementedError

    @abstractmethod
    def list_active_memories(
        self, user_id: str, memory_type: Optional[MemoryType] = None
    ) -> list[CandidateCareerMemoryItem]:
        """Retrieves currently active memory facts for a candidate."""
        raise NotImplementedError

    @abstractmethod
    def get_memory_history(self, user_id: str, memory_id: str) -> list[CandidateCareerMemoryItem]:
        """Retrieves full version audit history for a memory lineage."""
        raise NotImplementedError

    @abstractmethod
    def list_all_memories_for_candidate(
        self, user_id: str, include_inactive: bool = False
    ) -> list[CandidateCareerMemoryItem]:
        """Lists all memory items for a candidate."""
        raise NotImplementedError


class MarketReportRepository(ABC):
    """Abstract port for cached market intelligence research reports."""

    @abstractmethod
    def save_report(self, report: MarketResearchReportRecord) -> None:
        """Persists or updates a market research report."""
        raise NotImplementedError

    @abstractmethod
    def get_report(
        self, role_title: str, country_code: str, max_age_hours: int = 48
    ) -> Optional[MarketResearchReportRecord]:
        """Retrieves an active cached market report for a role and geography."""
        raise NotImplementedError

    @abstractmethod
    def list_reports(self, limit: int = 20) -> list[MarketResearchReportRecord]:
        """Lists recently generated market research reports."""
        raise NotImplementedError






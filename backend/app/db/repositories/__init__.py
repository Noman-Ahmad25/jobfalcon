from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryEligibilityAuditRepository,
    InMemoryOpportunityRepository,
    InMemoryRecommendationRepository,
)
from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    EligibilityAuditRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteEligibilityAuditRepository,
    SQLiteOpportunityRepository,
    SQLiteRecommendationRepository,
)

__all__ = [
    "CandidateProfileRepository",
    "OpportunityRepository",
    "DuplicateClusterRepository",
    "EligibilityAuditRepository",
    "RecommendationRepository",
    "SQLiteCandidateProfileRepository",
    "SQLiteOpportunityRepository",
    "SQLiteDuplicateClusterRepository",
    "SQLiteEligibilityAuditRepository",
    "SQLiteRecommendationRepository",
    "InMemoryCandidateProfileRepository",
    "InMemoryOpportunityRepository",
    "InMemoryDuplicateClusterRepository",
    "InMemoryEligibilityAuditRepository",
    "InMemoryRecommendationRepository",
]

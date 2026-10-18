from app.db.repositories.in_memory import (
    InMemoryCandidateProfileRepository,
    InMemoryDuplicateClusterRepository,
    InMemoryEligibilityAuditRepository,
    InMemoryOpportunityRepository,
)
from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    DuplicateClusterRepository,
    EligibilityAuditRepository,
    OpportunityRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteDuplicateClusterRepository,
    SQLiteEligibilityAuditRepository,
    SQLiteOpportunityRepository,
)

__all__ = [
    "CandidateProfileRepository",
    "OpportunityRepository",
    "DuplicateClusterRepository",
    "EligibilityAuditRepository",
    "SQLiteCandidateProfileRepository",
    "SQLiteOpportunityRepository",
    "SQLiteDuplicateClusterRepository",
    "SQLiteEligibilityAuditRepository",
    "InMemoryCandidateProfileRepository",
    "InMemoryOpportunityRepository",
    "InMemoryDuplicateClusterRepository",
    "InMemoryEligibilityAuditRepository",
]

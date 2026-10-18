from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.schemas.opportunity import PolymorphicOpportunity


class BaseOpportunityAdapter(ABC):
    """Abstract interface for external career opportunity data sources.

    Adapters ingest raw ATS feeds, job boards, or fixtures, normalize the fields,
    compute MinHash signatures when necessary, and output domain-validated
    PolymorphicOpportunity instances.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Machine-readable source system identifier (e.g. 'greenhouse', 'lever', 'fixture')."""
        raise NotImplementedError

    @abstractmethod
    def fetch_opportunities(self) -> Sequence[PolymorphicOpportunity]:
        """Fetches and transforms records into validated PolymorphicOpportunity instances."""
        raise NotImplementedError

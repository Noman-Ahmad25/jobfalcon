from app.modules.ingestion.adapter import BaseOpportunityAdapter
from app.modules.ingestion.fixture_adapter import JSONFixtureOpportunityAdapter
from app.modules.ingestion.importer import IngestionReport, OpportunityImporter

__all__ = [
    "BaseOpportunityAdapter",
    "JSONFixtureOpportunityAdapter",
    "OpportunityImporter",
    "IngestionReport",
]

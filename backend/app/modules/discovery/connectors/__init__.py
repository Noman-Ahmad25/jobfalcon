from __future__ import annotations

from typing import Optional

from app.modules.discovery.connectors.ats_career_page import CompanyCareerPageConnector
from app.modules.discovery.connectors.base import (
    BaseDiscoveryConnector,
    create_normalized_opportunity,
)
from app.modules.discovery.connectors.india_jobs import IndiaJobsMCPConnector
from app.modules.discovery.connectors.jobspy import JobSpyMCPConnector
from app.modules.discovery.connectors.web_search import WebSearchConnector


def get_default_connectors(
    mock_mode: bool = True,
    simulate_failure_connector: Optional[str] = None,
) -> list[BaseDiscoveryConnector]:
    """Instantiates the 4 discovery connectors with optional fault injection for testing resilience."""
    connectors: list[BaseDiscoveryConnector] = [
        WebSearchConnector(
            mock_mode=mock_mode,
            simulate_error=(simulate_failure_connector == "web_search"),
        ),
        IndiaJobsMCPConnector(
            mock_mode=mock_mode,
            simulate_error=(simulate_failure_connector == "india_jobs_mcp"),
        ),
        JobSpyMCPConnector(
            mock_mode=mock_mode,
            simulate_error=(simulate_failure_connector == "jobspy_mcp"),
        ),
        CompanyCareerPageConnector(
            mock_mode=mock_mode,
            simulate_error=(simulate_failure_connector == "ats_career_pages"),
        ),
    ]
    return connectors


__all__ = [
    "BaseDiscoveryConnector",
    "create_normalized_opportunity",
    "WebSearchConnector",
    "IndiaJobsMCPConnector",
    "JobSpyMCPConnector",
    "CompanyCareerPageConnector",
    "get_default_connectors",
]

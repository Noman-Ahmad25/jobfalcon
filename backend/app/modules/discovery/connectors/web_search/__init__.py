"""Web Search Discovery Integration package for JobFalcon."""

from app.modules.discovery.connectors.web_search.classifier import (
    JobSearchResultClassifier,
    extract_company_from_title,
    normalize_search_result_to_opportunity,
)
from app.modules.discovery.connectors.web_search.connector import WebSearchConnector
from app.modules.discovery.connectors.web_search.providers import (
    BaseSearchProvider,
    CustomJSONSearchProvider,
    DuckDuckGoSearchProvider,
    MockSearchProvider,
    ProviderHealth,
    RawSearchResult,
    SearXNGSearchProvider,
    get_search_provider,
)

__all__ = [
    "BaseSearchProvider",
    "CustomJSONSearchProvider",
    "DuckDuckGoSearchProvider",
    "JobSearchResultClassifier",
    "MockSearchProvider",
    "ProviderHealth",
    "RawSearchResult",
    "SearXNGSearchProvider",
    "WebSearchConnector",
    "extract_company_from_title",
    "get_search_provider",
    "normalize_search_result_to_opportunity",
]

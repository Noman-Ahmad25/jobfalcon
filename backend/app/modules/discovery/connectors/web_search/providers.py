from __future__ import annotations

import asyncio
import logging
import time
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.discovery import ConnectorStatus

logger = logging.getLogger(__name__)


class RawSearchResult(BaseModel):
    """Raw, un-normalized search result from an external search engine."""

    url: str = Field(..., description="Canonical destination URL.")
    title: str = Field(..., description="Result title as reported by search engine.")
    snippet: str = Field(default="", description="Snippet or text summary.")
    engine: str | None = Field(default=None, description="Backend search engine (e.g. google, bing, duckduckgo).")
    published_date: datetime | None = Field(default=None, description="Publication timestamp if available.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional provider-specific metadata.")


class ProviderHealth(BaseModel):
    """Health diagnostic for a web search provider."""

    status: ConnectorStatus = Field(..., description="Operational status.")
    provider_name: str = Field(..., description="Identifier name of the provider.")
    latency_ms: float = Field(default=0.0, description="Response latency in milliseconds.")
    details: dict[str, Any] = Field(default_factory=dict, description="Safe diagnostics (no secrets).")


class BaseSearchProvider(ABC):
    """Abstract interface for external web search engine integrations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'searxng', 'duckduckgo', 'custom', 'mock')."""
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[RawSearchResult]:
        """Executes a search query and returns raw search results."""
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Checks connectivity and returns operational health status."""
        raise NotImplementedError


# =============================================================================
# 1. SearXNG Provider (Self-Hosted / Open-Source Meta-Search)
# =============================================================================

class SearXNGSearchProvider(BaseSearchProvider):
    """Integrates with self-hosted or managed SearXNG meta-search instances.

    SearXNG provides structured JSON output at `/search?q={query}&format=json`.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (settings.SEARXNG_BASE_URL if base_url is None else base_url).rstrip("/")
        self.api_key = api_key or settings.WEB_SEARCH_API_KEY
        self.timeout_seconds = timeout_seconds or settings.WEB_SEARCH_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "searxng"

    async def check_health(self) -> ProviderHealth:
        t0 = time.perf_counter()
        if not self.base_url or not (self.base_url.startswith("http://") or self.base_url.startswith("https://")):
            return ProviderHealth(
                status=ConnectorStatus.MISCONFIGURED,
                provider_name=self.provider_name,
                latency_ms=0.0,
                details={
                    "error": "Invalid or missing SEARXNG_BASE_URL configuration.",
                    "configured_url": self.base_url or "<empty>",
                },
            )

        headers: dict[str, str] = {
            "User-Agent": "JobFalcon/1.0 (Career Discovery Engine)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        probe_url = f"{self.base_url}/search"
        params = {"q": "software engineer job", "format": "json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(probe_url, params=params, headers=headers)
                latency = round((time.perf_counter() - t0) * 1000, 2)

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        result_count = len(data.get("results", []))
                        return ProviderHealth(
                            status=ConnectorStatus.CONNECTED,
                            provider_name=self.provider_name,
                            latency_ms=latency,
                            details={
                                "base_url": self.base_url,
                                "probe_results": result_count,
                                "unresponsive_engines": data.get("unresponsive_engines", []),
                            },
                        )
                    except Exception as json_err:
                        return ProviderHealth(
                            status=ConnectorStatus.DEGRADED,
                            provider_name=self.provider_name,
                            latency_ms=latency,
                            details={
                                "error": f"SearXNG instance returned non-JSON response: {json_err}",
                                "status_code": resp.status_code,
                            },
                        )
                elif resp.status_code == 429:
                    return ProviderHealth(
                        status=ConnectorStatus.RATE_LIMITED,
                        provider_name=self.provider_name,
                        latency_ms=latency,
                        details={"status_code": 429, "error": "Search provider rate limit exceeded."},
                    )
                else:
                    return ProviderHealth(
                        status=ConnectorStatus.UNAVAILABLE,
                        provider_name=self.provider_name,
                        latency_ms=latency,
                        details={"status_code": resp.status_code, "error": f"SearXNG returned HTTP {resp.status_code}"},
                    )

        except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return ProviderHealth(
                status=ConnectorStatus.UNAVAILABLE,
                provider_name=self.provider_name,
                latency_ms=latency,
                details={
                    "error": f"Could not connect to SearXNG at {self.base_url}: {type(conn_err).__name__}",
                    "suggestion": "Start a local SearXNG container (e.g. docker run -d -p 8080:8080 searxng/searxng) or configure DUCKDUCKGO provider.",
                },
            )
        except Exception as exc:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return ProviderHealth(
                status=ConnectorStatus.ERROR,
                provider_name=self.provider_name,
                latency_ms=latency,
                details={"error": f"Search health probe error: {type(exc).__name__} - {exc!s}"},
            )

    async def search(self, query: str, limit: int = 10) -> list[RawSearchResult]:
        headers: dict[str, str] = {
            "User-Agent": "JobFalcon/1.0 (Career Discovery Engine)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning("SearXNG search returned HTTP %d for query %s", resp.status_code, query)
                return []

            data = resp.json()
            raw_items = data.get("results", [])
            results: list[RawSearchResult] = []

            for item in raw_items[:limit]:
                dest_url = item.get("url", "").strip()
                title = item.get("title", "").strip()
                content = item.get("content", "").strip()
                engine = item.get("engine", "searxng")

                if dest_url and title:
                    results.append(
                        RawSearchResult(
                            url=dest_url,
                            title=title,
                            snippet=content,
                            engine=engine,
                            metadata={"score": item.get("score")},
                        )
                    )

            return results


# =============================================================================
# 2. DuckDuckGo Provider (Public Web Search, Zero API Key Required)
# =============================================================================

class DuckDuckGoSearchProvider(BaseSearchProvider):
    """Direct public web search using DuckDuckGo HTML endpoint.

    Requires zero API keys and zero local container setup.
    Parses real search-result titles, clean URLs, and snippets.
    """

    def __init__(self, timeout_seconds: float | None = None) -> None:
        settings = get_settings()
        self.timeout_seconds = timeout_seconds or settings.WEB_SEARCH_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "duckduckgo"

    async def check_health(self) -> ProviderHealth:
        t0 = time.perf_counter()
        try:
            # Execute quick live search test
            results = await self.search(query="site:greenhouse.io python engineer", limit=2)
            latency = round((time.perf_counter() - t0) * 1000, 2)
            if len(results) > 0:
                return ProviderHealth(
                    status=ConnectorStatus.CONNECTED,
                    provider_name=self.provider_name,
                    latency_ms=latency,
                    details={
                        "endpoint": "https://lite.duckduckgo.com/lite/",
                        "test_result_count": len(results),
                        "sample_url": results[0].url if results else None,
                    },
                )
            else:
                return ProviderHealth(
                    status=ConnectorStatus.DEGRADED,
                    provider_name=self.provider_name,
                    latency_ms=latency,
                    details={"error": "Probe returned 0 results."},
                )
        except Exception as exc:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return ProviderHealth(
                status=ConnectorStatus.UNAVAILABLE,
                provider_name=self.provider_name,
                latency_ms=latency,
                details={"error": f"DuckDuckGo probe error: {type(exc).__name__} - {exc!s}"},
            )

    async def search(self, query: str, limit: int = 10) -> list[RawSearchResult]:
        # Run in threadpool for robust sync requests handling
        return await asyncio.to_thread(self._sync_search, query, limit)

    def _sync_search(self, query: str, limit: int) -> list[RawSearchResult]:
        import requests
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("beautifulsoup4 not installed; cannot parse HTML search results.")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # 1. Primary: DuckDuckGo Lite endpoint (clean HTML, highly reliable without JavaScript)
        try:
            resp = requests.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": query},
                headers=headers,
                timeout=int(self.timeout_seconds),
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.select(".result-link")
                snippets = soup.select(".result-snippet")
                results: list[RawSearchResult] = []

                for idx, link_elem in enumerate(links):
                    raw_href = link_elem.get("href", "")
                    if "uddg=" in raw_href:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        clean_url = parsed_qs.get("uddg", [raw_href])[0]
                    else:
                        clean_url = raw_href

                    if not clean_url or clean_url.startswith("/") or "duckduckgo.com" in clean_url:
                        continue

                    title = link_elem.get_text().strip()
                    snippet = snippets[idx].get_text().strip() if idx < len(snippets) else ""

                    results.append(
                        RawSearchResult(
                            url=clean_url,
                            title=title,
                            snippet=snippet,
                            engine="duckduckgo_lite",
                        )
                    )
                    if len(results) >= limit:
                        break

                if results:
                    return results
        except Exception as exc:
            logger.warning("DuckDuckGo lite endpoint error: %s; falling back to html endpoint", exc)

        # 2. Fallback: DuckDuckGo HTML endpoint
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=int(self.timeout_seconds),
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for item in soup.select(".result"):
                    title_elem = item.select_one(".result__title a")
                    snippet_elem = item.select_one(".result__snippet")
                    if not title_elem:
                        continue

                    raw_href = title_elem.get("href", "")
                    if "uddg=" in raw_href:
                        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        clean_url = parsed_qs.get("uddg", [raw_href])[0]
                    else:
                        clean_url = raw_href

                    if not clean_url or clean_url.startswith("/") or "duckduckgo.com" in clean_url:
                        continue

                    title = title_elem.get_text().strip()
                    snippet = snippet_elem.get_text().strip() if snippet_elem else ""

                    results.append(
                        RawSearchResult(
                            url=clean_url,
                            title=title,
                            snippet=snippet,
                            engine="duckduckgo_html",
                        )
                    )
                    if len(results) >= limit:
                        break

                return results
        except Exception as exc:
            logger.warning("DuckDuckGo HTML endpoint error: %s", exc)

        return []


# =============================================================================
# 3. Custom JSON REST Provider
# =============================================================================

class CustomJSONSearchProvider(BaseSearchProvider):
    """Integrates with any custom REST search service accepting `?q={query}` and returning JSON."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 6.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "custom"

    async def check_health(self) -> ProviderHealth:
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(self.endpoint_url, params={"q": "ping"})
                latency = round((time.perf_counter() - t0) * 1000, 2)
                status = ConnectorStatus.CONNECTED if resp.status_code == 200 else ConnectorStatus.UNAVAILABLE
                return ProviderHealth(
                    status=status,
                    provider_name=self.provider_name,
                    latency_ms=latency,
                    details={"status_code": resp.status_code, "url": self.endpoint_url},
                )
        except Exception as exc:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return ProviderHealth(
                status=ConnectorStatus.UNAVAILABLE,
                provider_name=self.provider_name,
                latency_ms=latency,
                details={"error": str(exc)},
            )

    async def search(self, query: str, limit: int = 10) -> list[RawSearchResult]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(self.endpoint_url, params={"q": query, "limit": limit}, headers=headers)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data if isinstance(data, list) else data.get("results", [])
            results = []
            for item in items[:limit]:
                url = item.get("url")
                title = item.get("title")
                snippet = item.get("snippet", "")
                if url and title:
                    results.append(RawSearchResult(url=url, title=title, snippet=snippet, engine="custom"))
            return results


# =============================================================================
# 4. Mock Search Provider (Deterministic Offline Testing)
# =============================================================================

class MockSearchProvider(BaseSearchProvider):
    """Deterministic mock provider for air-gapped CI test suites."""

    def __init__(self, simulate_failure: bool = False, latency_ms: float = 15.0) -> None:
        self.simulate_failure = simulate_failure
        self.latency_ms = latency_ms

    @property
    def provider_name(self) -> str:
        return "mock"

    async def check_health(self) -> ProviderHealth:
        if self.simulate_failure:
            return ProviderHealth(
                status=ConnectorStatus.ERROR,
                provider_name=self.provider_name,
                latency_ms=self.latency_ms,
                details={"error": "Simulated mock provider failure"},
            )
        return ProviderHealth(
            status=ConnectorStatus.MOCKED_FALLBACK,
            provider_name=self.provider_name,
            latency_ms=self.latency_ms,
            details={"mode": "deterministic_mock_fixtures"},
        )

    async def search(self, query: str, limit: int = 10) -> list[RawSearchResult]:
        if self.simulate_failure:
            raise ConnectionError("Mock search provider simulated network drop.")

        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

        # Generate realistic deterministic results matching query terms
        companies = ["ScaleGrid Cloud", "Apex Analytics", "Beacon Distributed Systems", "Nova Health"]
        results: list[RawSearchResult] = []
        for i in range(min(limit, 3)):
            comp = companies[i % len(companies)]
            results.append(
                RawSearchResult(
                    url=f"https://jobs.example.com/{comp.lower().replace(' ', '-')}/posting-{i+100}",
                    title=f"Senior Software Engineer ({query}) at {comp}",
                    snippet=f"Seeking a talented engineer with expertise in {query}. Design resilient backend microservices and databases.",
                    engine="mock",
                )
            )
        return results


# =============================================================================
# Provider Factory
# =============================================================================

def get_search_provider(
    provider_name: str | None = None,
    mock_mode: bool = False,
) -> BaseSearchProvider:
    """Instantiates search provider based on settings or explicit specification."""
    if mock_mode:
        return MockSearchProvider()

    settings = get_settings()
    p_name = (provider_name or settings.WEB_SEARCH_PROVIDER).lower().strip()

    if p_name == "duckduckgo":
        return DuckDuckGoSearchProvider(timeout_seconds=settings.WEB_SEARCH_TIMEOUT_SECONDS)
    elif p_name == "searxng":
        return SearXNGSearchProvider(
            base_url=settings.SEARXNG_BASE_URL,
            api_key=settings.WEB_SEARCH_API_KEY or None,
            timeout_seconds=settings.WEB_SEARCH_TIMEOUT_SECONDS,
        )
    elif p_name == "custom":
        return CustomJSONSearchProvider(
            endpoint_url=settings.SEARXNG_BASE_URL,
            api_key=settings.WEB_SEARCH_API_KEY or None,
            timeout_seconds=settings.WEB_SEARCH_TIMEOUT_SECONDS,
        )
    elif p_name == "mock":
        return MockSearchProvider()
    else:
        # Default to SearXNG with fallback
        return SearXNGSearchProvider()

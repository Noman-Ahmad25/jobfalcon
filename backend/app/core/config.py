from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Metadata
    PROJECT_NAME: str = "JobFalcon API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="development, testing, production")
    DEBUG: bool = Field(default=False)

    # API Routing
    API_V1_PREFIX: str = "/api/v1"

    # Server Bind Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Persistence Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./jobfalcon_dev.db",
        description="Database connection URL (e.g., sqlite:///./jobfalcon_dev.db or postgresql://...)",
    )

    # LLM / AI Gateway Configuration
    LLM_PROVIDER: str = Field(
        default="mock",
        description="Model provider: 'mock' (offline testing), 'litellm', 'ollama', or 'openai'",
    )
    LLM_API_KEY: str = Field(
        default="",
        description="API key for LLM gateway or provider (optional for local/mock)",
    )
    LLM_BASE_URL: str = Field(
        default="http://localhost:4000/v1",
        description="OpenAI-compatible base URL (e.g., http://localhost:4000/v1 for LiteLLM or http://localhost:11434/v1 for Ollama)",
    )
    LLM_MODEL: str = Field(
        default="qwen2.5:14b-instruct",
        description="Model identifier (e.g., qwen2.5:14b-instruct or gpt-4o-mini)",
    )
    LLM_TIMEOUT_SECONDS: float = Field(
        default=120.0,
        description="Client timeout for model inference calls in seconds",
    )
    LLM_MAX_RETRIES: int = Field(
        default=1,
        description="Maximum retry attempts on transient model gateway errors",
    )

    # Candidate Profiling Limits
    PROFILING_MAX_INPUT_CHARS: int = Field(
        default=25000,
        description="Maximum combined character length for candidate input materials",
    )

    # Web Search Configuration (Milestone 13)
    WEB_SEARCH_PROVIDER: str = Field(
        default="searxng",
        description="Search provider: 'searxng', 'custom', or 'mock'",
    )
    SEARXNG_BASE_URL: str = Field(
        default="http://localhost:8080",
        description="Base URL for SearXNG instance (e.g., http://localhost:8080 or public host)",
    )
    WEB_SEARCH_API_KEY: str = Field(
        default="",
        description="Optional API key / authentication token for search provider",
    )
    WEB_SEARCH_TIMEOUT_SECONDS: float = Field(
        default=6.0,
        description="Client timeout for search HTTP requests in seconds",
    )
    WEB_SEARCH_MAX_RESULTS: int = Field(
        default=10,
        description="Maximum search results requested per query",
    )
    WEB_SEARCH_ENRICH_DESTINATIONS: bool = Field(
        default=False,
        description="Whether to perform shallow verification/enrichment on destination URLs",
    )

    # Model Context Protocol (MCP) Configuration (Milestone 14)
    MCP_JOBSPY_COMMAND: str = Field(
        default="mcp-jobspy",
        description="Executable command or binary path for the JobSpy MCP server (e.g. 'mcp-jobspy')",
    )
    MCP_JOBSPY_TIMEOUT_SECONDS: float = Field(
        default=12.0,
        description="Client timeout for MCP stdio tool calls in seconds",
    )
    MCP_JOBSPY_RESULTS_WANTED: int = Field(
        default=5,
        description="Number of opportunity results requested per job board during MCP tool execution",
    )
    MCP_JOBSPY_FETCH_DETAILS: bool = Field(
        default=True,
        description="Whether to invoke MCP get_job_details tool to enrich full descriptions and direct URLs",
    )
    MCP_JOBSPY_COUNTRY: str = Field(
        default="usa",
        description="Default target country for JobSpy MCP scrapers (e.g., 'usa', 'uk', 'canada')",
    )

    # Adaptive Discovery & Orchestration Budget Configuration
    DISCOVERY_EXECUTION_MODE: str = Field(
        default="local",
        description="Discovery environment profile: 'local' (generous exploration budgets, zero LLM billing constraints) or 'hosted' (strict quota & concurrency boundaries)",
    )
    DISCOVERY_MAX_ITERATIONS: int = Field(
        default=6,
        description="Default maximum search-evaluate-adapt loop iterations (6 for local, 3 for hosted)",
    )
    DISCOVERY_MAX_TOOL_CALLS: int = Field(
        default=30,
        description="Default maximum external search tool calls (0 = unlimited). In local mode defaults to 30; in hosted defaults to 10.",
    )
    DISCOVERY_MAX_CALLS_PER_CONNECTOR: int = Field(
        default=15,
        description="Upper bound on tool calls dispatched to any single connector in a workflow run",
    )
    DISCOVERY_MAX_CONCURRENT_CONNECTOR_CALLS: int = Field(
        default=3,
        description="Maximum concurrent search tool calls across connectors",
    )
    DISCOVERY_PER_TOOL_TIMEOUT_SECONDS: float = Field(
        default=20.0,
        description="Default timeout in seconds for individual connector search invocations",
    )
    DISCOVERY_WORKFLOW_TIMEOUT_SECONDS: float = Field(
        default=120.0,
        description="Overall workflow execution timeout in seconds before safely concluding with partial results",
    )
    DISCOVERY_RETRY_LIMIT: int = Field(
        default=2,
        description="Maximum retry count per failed connector call before marking provider degraded",
    )

    # Demo Data Seeding
    SEED_DEMO_DATA: bool = Field(
        default=False,
        description="If True, seeds demo candidate profiles and opportunities on startup. Disable in real local-user mode.",
    )

    # CORS Settings
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"


    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_local_discovery_mode(self) -> bool:
        return self.DISCOVERY_EXECUTION_MODE.lower().strip() == "local"

    def get_effective_max_iterations(self, requested: Optional[int] = None) -> int:
        if requested is not None and requested > 0:
            if not self.is_local_discovery_mode:
                return min(requested, 3)
            return requested
        return self.DISCOVERY_MAX_ITERATIONS if self.is_local_discovery_mode else 3

    def get_effective_max_tool_calls(self, requested: Optional[int] = None) -> int:
        """Resolves tool call budget. 0 represents unlimited."""
        if requested is not None:
            if not self.is_local_discovery_mode and (requested == 0 or requested > 10):
                return 10
            return requested
        return self.DISCOVERY_MAX_TOOL_CALLS if self.is_local_discovery_mode else 10


COUNTRY_CODE_TO_JOBSPY: dict[str, str] = {
    "IN": "india",
    "IND": "india",
    "US": "usa",
    "USA": "usa",
    "UK": "uk",
    "GB": "uk",
    "GBR": "uk",
    "CA": "canada",
    "CAN": "canada",
    "DE": "germany",
    "DEU": "germany",
    "FR": "france",
    "FRA": "france",
    "AU": "australia",
    "AUS": "australia",
    "SG": "singapore",
    "SGP": "singapore",
}


def resolve_jobspy_country(
    target_country_codes: Optional[list[str]] = None,
    default_fallback: str = "usa",
) -> str:
    """Deterministically maps ISO country codes to JobSpy country domains."""
    if target_country_codes:
        for code in target_country_codes:
            normalized = code.upper().strip()
            if normalized in COUNTRY_CODE_TO_JOBSPY:
                return COUNTRY_CODE_TO_JOBSPY[normalized]
    return default_fallback


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton instance."""
    return Settings()

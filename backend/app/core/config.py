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
        default=30.0,
        description="Client timeout for model inference calls in seconds",
    )
    LLM_MAX_RETRIES: int = Field(
        default=2,
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

    # CORS Settings
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"


    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton instance."""
    return Settings()

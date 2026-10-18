from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.common import CareerPathRelationship, OpportunityCategory, WorkMode
from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import EligibilityResult
from app.schemas.opportunity import PolymorphicOpportunity
from app.schemas.profile import CandidateCareerProfile


class ConnectorStatus(str, Enum):
    """Operational status of an external opportunity discovery connector."""

    CONNECTED = "CONNECTED"
    MOCKED_FALLBACK = "MOCKED_FALLBACK"
    UNAVAILABLE_MISSING_BINARY = "UNAVAILABLE_MISSING_BINARY"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"


class DiscoverySearchQuery(BaseModel):
    """Concrete parameterized search query generated from candidate skills and constraints."""

    query_id: str = Field(
        ...,
        description="Deterministic identifier for this search query.",
    )
    role_title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Canonical role title targeted by this query.",
    )
    query_string: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Optimized search query string formatted for keyword or search engine retrieval.",
    )
    expanded_keywords: list[str] = Field(
        default_factory=list,
        description="Synonyms, skill keywords, and technology terms associated with this query.",
    )
    category: OpportunityCategory = Field(
        ...,
        description="Target opportunity category (e.g., INTERNSHIP, FULL_TIME_JOB).",
    )
    work_modes: list[WorkMode] = Field(
        default_factory=list,
        description="Permitted work modes (REMOTE, HYBRID, ON_SITE).",
    )
    target_locations: list[str] = Field(
        default_factory=list,
        description="Target cities or regions for this query.",
    )
    target_country_codes: list[str] = Field(
        default_factory=list,
        description="ISO-3166-1 alpha-2 country codes where the candidate is authorized.",
    )
    seniority_level: str = Field(
        default="ENTRY_LEVEL",
        description="Calibrated seniority level (e.g., INTERN, ENTRY_LEVEL, MID_LEVEL, SENIOR).",
    )
    relationship_type: CareerPathRelationship = Field(
        default=CareerPathRelationship.TARGET,
        description="Whether this query originates from an explicit TARGET or inferred ADJACENT role.",
    )

    @field_validator("query_string", "role_title", mode="before")
    @classmethod
    def _sanitize_query_strings(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class RoleMappingTarget(BaseModel):
    """Target or adjacent career trajectory derived from candidate profile and skills."""

    role_title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Standardized occupation or role title.",
    )
    canonical_occupation_code: str = Field(
        ...,
        description="Canonical O*NET (e.g. '15-1252.00') or ESCO code.",
    )
    relationship_type: CareerPathRelationship = Field(
        ...,
        description="TARGET for explicit candidate preference; ADJACENT for skill-inferred path.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Taxonomic or skill overlap confidence score.",
    )
    matched_skill_names: list[str] = Field(
        default_factory=list,
        description="Candidate skills matching this role's core competencies.",
    )
    missing_skill_names: list[str] = Field(
        default_factory=list,
        description="Known core skills for this role that candidate currently lacks.",
    )
    queries: list[DiscoverySearchQuery] = Field(
        default_factory=list,
        description="Specific parameterized search queries generated for this role.",
    )

    @field_validator("role_title", mode="before")
    @classmethod
    def _sanitize_role_title(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class DiscoveryQueryPlan(BaseModel):
    """Structured plan mapping candidate competencies to multi-source discovery queries."""

    candidate_id: str = Field(
        ...,
        description="Unique identifier of the candidate.",
    )
    target_roles: list[RoleMappingTarget] = Field(
        ...,
        min_length=1,
        description="Role mappings with matched skills and generated queries.",
    )
    all_queries: list[DiscoverySearchQuery] = Field(
        ...,
        min_length=1,
        description="Flattened, prioritized list of all queries to execute across discovery connectors.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of query plan creation.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostics, taxonomy coverage, and generation parameters.",
    )


class ConnectorHealthReport(BaseModel):
    """Telemetry report describing the health and capability of a discovery connector."""

    connector_id: str = Field(
        ...,
        description="Unique identifier of the connector (e.g., 'india_jobs_mcp').",
    )
    source_name: str = Field(
        ...,
        description="Human-readable connector name.",
    )
    connector_type: str = Field(
        ...,
        description="Transport type (e.g. 'MCP_STDIO', 'MCP_HTTP', 'WEB_SCRAPER', 'ATS_API').",
    )
    status: ConnectorStatus = Field(
        ...,
        description="Current operational status.",
    )
    is_mock_fallback: bool = Field(
        ...,
        description="True if connector is running in simulated or fixture mode rather than live external network.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic details, binary presence, or failure explanation.",
    )
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the health evaluation.",
    )


class DiscoveryConnectorResult(BaseModel):
    """Raw result emitted by a single discovery connector invocation."""

    connector_id: str = Field(
        ...,
        description="Identifier of the emitting connector.",
    )
    source_name: str = Field(
        ...,
        description="Human-readable name of the opportunity source.",
    )
    query_id: str = Field(
        ...,
        description="Search query ID that produced these results.",
    )
    status: ConnectorStatus = Field(
        ...,
        description="Connector execution status.",
    )
    opportunities: list[PolymorphicOpportunity] = Field(
        default_factory=list,
        description="Normalized and sanitized opportunities retrieved.",
    )
    raw_count: int = Field(
        default=0,
        ge=0,
        description="Total items returned before deduplication.",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Connector execution time in milliseconds.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error detail if execution encountered a failure.",
    )
    trust_level: str = Field(
        default="untrusted_external_data",
        description="Data provenance trust classification.",
    )


class DiscoveryConnectorReport(BaseModel):
    """Aggregated status telemetry for a connector in a discovery run."""

    connector_id: str
    source_name: str
    status: ConnectorStatus
    raw_count: int
    latency_ms: float
    error_message: Optional[str] = None


class DiscoveryRunRequest(BaseModel):
    """Payload requesting an end-to-end multi-source discovery execution."""

    candidate_profile: Optional[CandidateCareerProfile] = Field(
        default=None,
        description="Full candidate career profile. If omitted, user_id will be loaded from repository.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier to load profile from repository if candidate_profile is omitted.",
    )
    connector_ids: Optional[list[str]] = Field(
        default=None,
        description="Optional whitelist of connector IDs to execute. None executes all available.",
    )
    max_results_per_connector: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Upper bound of opportunities each connector should yield per query.",
    )
    deduplication_threshold: float = Field(
        default=0.85,
        ge=0.50,
        le=1.00,
        description="Jaccard similarity threshold for MinHash LSH deduplication.",
    )
    simulate_failure_connector: Optional[str] = Field(
        default=None,
        description="Optional connector ID to artificially simulate a partial failure for testing resilience.",
    )
    persist_to_repository: bool = Field(
        default=True,
        description="Whether to persist discovered listings and clusters into the database.",
    )


class DiscoveryRunResponse(BaseModel):
    """End-to-end multi-source discovery execution response."""

    candidate_id: str
    query_plan: DiscoveryQueryPlan
    connector_reports: list[DiscoveryConnectorReport]
    total_discovered: int
    canonical_count: int
    duplicate_count: int
    eligible_count: int
    uncertain_count: int
    ineligible_count: int
    canonical_opportunities: list[PolymorphicOpportunity]
    eligible_opportunities: list[PolymorphicOpportunity]
    duplicate_clusters: dict[str, OpportunityCluster]
    duplicate_records: list[DuplicateRecord]
    eligibility_results: list[EligibilityResult]
    execution_metadata: dict[str, Any]

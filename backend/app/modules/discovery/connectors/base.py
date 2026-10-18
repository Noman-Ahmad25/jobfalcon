from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.sanitization import sanitize_untrusted_text
from app.modules.deduplication.minhash import compute_minhash_signature
from app.modules.deduplication.normalization import build_opportunity_comparison_text
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.discovery import (
    ConnectorHealthReport,
    ConnectorStatus,
    DiscoveryConnectorResult,
    DiscoverySearchQuery,
)
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)


def create_normalized_opportunity(
    title: str,
    company_name: str,
    description: str,
    source_url: str,
    source_system: str,
    source_job_id: Optional[str] = None,
    category: OpportunityCategory = OpportunityCategory.FULL_TIME_JOB,
    eligible_country_codes: Optional[list[str]] = None,
    sponsors_work_visa: bool = False,
    minimum_degree_required: DegreeLevel = DegreeLevel.NONE,
    requires_active_student_status: bool = False,
    min_experience_months: int = 0,
    max_experience_months: Optional[int] = None,
    work_mode: WorkMode = WorkMode.REMOTE,
    location_city_country: Optional[list[str]] = None,
    application_deadline: Optional[datetime] = None,
    skill_requirements: Optional[list[OpportunitySkillRequirement]] = None,
    category_specific_attributes: Optional[dict[str, Any]] = None,
    mapped_occupation_code: str = "15-1252.00",
    completeness_score: float = 0.90,
    trust_score: float = 0.85,
    posted_at: Optional[datetime] = None,
    opportunity_id: Optional[str] = None,
) -> PolymorphicOpportunity:
    """Helper to construct a validated, sanitized PolymorphicOpportunity with MinHash signature.

    Ensures:
    1. Input text is strictly sanitized against prompt injection directives.
    2. Deterministic 128-permutation MinHash signature is computed over normalized text.
    3. Proper source provenance metadata is recorded.
    """
    clean_title = sanitize_untrusted_text(title)
    clean_company = sanitize_untrusted_text(company_name)
    clean_desc = sanitize_untrusted_text(description)[:2400]

    comparison_text = build_opportunity_comparison_text(
        title=clean_title,
        company_name=clean_company,
        description_summary=clean_desc,
    )
    _, hex_digest = compute_minhash_signature(comparison_text)

    opp_id = opportunity_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    post_time = posted_at or now

    attributes = dict(category_specific_attributes or {})
    attributes["source_system"] = source_system
    if source_job_id:
        attributes["source_job_id"] = source_job_id

    eligibility = OpportunityEligibilityRules(
        opportunity_category=category,
        eligible_country_codes=eligible_country_codes or ["US"],
        sponsors_work_visa=sponsors_work_visa,
        minimum_degree_required=minimum_degree_required,
        requires_active_student_status=requires_active_student_status,
        min_experience_months=min_experience_months,
        max_experience_months=max_experience_months,
        work_mode=work_mode,
        location_city_country=location_city_country or [],
        application_deadline=application_deadline,
    )

    return PolymorphicOpportunity(
        opportunity_id=opp_id,
        minhash_signature_hex=hex_digest,
        title=clean_title,
        company_name=clean_company,
        company_domain_verified=trust_score >= 0.80,
        mapped_occupation_code=mapped_occupation_code,
        eligibility_rules=eligibility,
        skill_requirements=skill_requirements or [],
        category_specific_attributes=attributes,
        sanitized_summary=clean_desc,
        source_url=source_url,
        posted_at=post_time,
        discovered_at=now,
        completeness_score=completeness_score,
        trust_score=trust_score,
        is_duplicate=False,
    )


class BaseDiscoveryConnector(ABC):
    """Abstract interface for external multi-source career opportunity connectors.

    Guarantees:
    - Independent connector lifecycle and health checks.
    - Honest capability and status reporting (never pretending uninstalled MCPs are live).
    - Sanitization of all returned external listings into PolymorphicOpportunity contracts.
    """

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Machine-readable unique connector identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable display name for this opportunity source."""
        raise NotImplementedError

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Transport/integration classification (e.g., 'MCP_STDIO', 'WEB_SEARCH', 'ATS_API')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_mock_fallback(self) -> bool:
        """True if the connector is operating in offline simulated mode."""
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> ConnectorHealthReport:
        """Verifies connector availability, network connectivity, or binary presence."""
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: DiscoverySearchQuery,
        limit: int = 10,
    ) -> DiscoveryConnectorResult:
        """Executes targeted opportunity retrieval for the provided query."""
        raise NotImplementedError

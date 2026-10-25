from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import UTC, datetime

from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.discovery.connectors.parsing_utils import (
    determine_work_mode,
    extract_experience_months,
    extract_skills_from_text,
    strip_html_tags,
)
from app.modules.discovery.connectors.web_search.providers import RawSearchResult
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.discovery import DiscoverySearchQuery
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity

logger = logging.getLogger(__name__)

# Known direct ATS domains indicating high trust direct career postings
KNOWN_ATS_DOMAINS: set[str] = {
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "workable.com",
    "bamboohr.com",
    "recruitee.com",
    "jobvite.com",
    "taleo.net",
    "icims.com",
}

# Positive URL / path indicators
JOB_URL_PATTERNS = re.compile(
    r"(/jobs?/|/careers?/|/posting/|/requisition/|/apply/|/positions?/|/open-roles/|/vacancy/)",
    re.IGNORECASE,
)

# Positive title keywords
JOB_TITLE_KEYWORDS = re.compile(
    r"\b(engineer|developer|scientist|architect|analyst|intern|internship|specialist|manager|lead|consultant|programmer|designer)\b",
    re.IGNORECASE,
)

# Negative keywords indicating articles, guides, courses, or aggregations
NEGATIVE_PATTERNS = re.compile(
    r"\b(how to become|top \d+|interview questions|salary guide|salary in|course|tutorial|bootcamp|cheat sheet|resume template|forum|discussion|reddit\.com|quora\.com|wikipedia\.org|coursera\.org|udemy\.com|edx\.org|medium\.com)\b",
    re.IGNORECASE,
)


class JobSearchResultClassifier:
    """Classifies raw search results to separate authentic job postings from general web content."""

    @classmethod
    def evaluate(cls, result: RawSearchResult, query: DiscoverySearchQuery | None = None) -> tuple[bool, str]:
        """Returns (is_job_listing, reason_string)."""
        url_lower = result.url.lower()
        title_lower = result.title.lower()
        combined_text = f"{url_lower} {title_lower} {result.snippet.lower()}"

        # 1. Negative filtering: Reject obvious non-job informational pages
        neg_match = NEGATIVE_PATTERNS.search(combined_text)
        if neg_match:
            return False, f"Filtered as informational / non-job content (matched '{neg_match.group(0)}')"

        # 2. Strong Positive Signal A: Direct ATS domain in URL
        parsed_url = urllib.parse.urlparse(result.url)
        netloc = parsed_url.netloc.lower()
        for ats_domain in KNOWN_ATS_DOMAINS:
            if ats_domain in netloc:
                return True, f"Verified direct ATS domain: {ats_domain}"

        # 3. Strong Positive Signal B: Career / job path in URL
        if JOB_URL_PATTERNS.search(parsed_url.path):
            return True, "URL path contains explicit career/job requisition routing"

        # 4. Strong Positive Signal C: Title contains explicit hiring terms
        if "hiring" in title_lower or "job application" in title_lower or "open position" in title_lower:
            return True, "Title contains explicit job application / hiring phrasing"

        # 5. Role Keyword match in title
        if JOB_TITLE_KEYWORDS.search(title_lower):
            # Check if title or snippet matches query role title
            if query and (query.role_title.lower() in title_lower or query.role_title.lower() in result.snippet.lower()):
                return True, "Role title and technology match target query"
            return True, "Title contains standard professional job title"

        return False, "Insufficient job posting indicators in URL and metadata"


def extract_company_from_title(title: str, url: str) -> str:
    """Deterministically extracts hiring company name from search result title or URL domain."""
    cleaned = strip_html_tags(title)

    # Patterns like: "Senior Backend Engineer at Acme Corp"
    if " at " in cleaned:
        parts = cleaned.split(" at ")
        candidate = parts[-1].split("|")[0].split(" - ")[0].split("·")[0].strip()
        if candidate and len(candidate) <= 60:
            return candidate

    # Patterns like: "Acme Corp - Senior Backend Engineer"
    if " - " in cleaned:
        parts = cleaned.split(" - ")
        if len(parts) >= 2:
            # Check if first part looks like company
            if len(parts[0].strip()) <= 40 and not JOB_TITLE_KEYWORDS.search(parts[0]):
                return parts[0].strip()
            # Or last part
            if len(parts[-1].strip()) <= 40 and not JOB_TITLE_KEYWORDS.search(parts[-1]):
                return parts[-1].strip()

    # Patterns like: "Acme Corp is hiring..."
    if " is hiring " in cleaned.lower():
        idx = cleaned.lower().index(" is hiring ")
        return cleaned[:idx].strip()

    # Fallback to domain name: careers.acmecorp.com -> Acme Corp
    parsed = urllib.parse.urlparse(url)
    domain_parts = parsed.netloc.replace("www.", "").split(".")
    if len(domain_parts) >= 2:
        name = domain_parts[0]
        if name in ("jobs", "careers", "boards", "job-boards") and len(domain_parts) >= 3:
            name = domain_parts[1]
        return name.replace("-", " ").title()

    return "Unknown Employer"


def normalize_search_result_to_opportunity(
    result: RawSearchResult,
    query: DiscoverySearchQuery,
) -> PolymorphicOpportunity:
    """Converts a raw search result into an auditable PolymorphicOpportunity.

    Maintains explicit uncertainty:
    - Sets is_verified_posting = False.
    - Annotates sanitized summary with [Search Index Result] provenance.
    - Preserves clean original source URL.
    """
    clean_title = strip_html_tags(result.title).split("|")[0].split(" - ")[0].strip()
    if not clean_title or len(clean_title) < 3:
        clean_title = query.role_title

    company = extract_company_from_title(result.title, result.url)

    # Sanitized description with explicit unverified search provenance header
    clean_snippet = strip_html_tags(result.snippet).strip()
    if not clean_snippet:
        clean_snippet = f"Career opportunity listing for {clean_title} at {company}. View direct posting for full requirements."

    sanitized_summary = (
        f"[Search Index Result - Unverified Requisition] {clean_snippet}"
    )

    # Extract skills from snippet
    extracted_skills = extract_skills_from_text(f"{clean_title} {clean_snippet}")
    if not extracted_skills and query.expanded_keywords:
        # Fall back to top query keywords
        extracted_skills = [
            OpportunitySkillRequirement(
                canonical_skill_id=f"skill_ws_{kw.lower()}",
                skill_name=kw,
                is_mandatory=True,
                minimum_proficiency_expected=5.0,
            )
            for kw in query.expanded_keywords[:3]
        ]

    # Work mode & experience
    work_mode = determine_work_mode(f"{clean_title} {clean_snippet}")
    if work_mode == WorkMode.ON_SITE and query.work_modes:
        work_mode = query.work_modes[0]

    min_exp = extract_experience_months(clean_snippet, title=clean_title)
    if "INTERN" in query.seniority_level or query.category == OpportunityCategory.INTERNSHIP:
        min_exp = 0

    # Trust score is higher if hosted on recognized ATS domain
    is_direct_ats = any(ats in result.url.lower() for ats in KNOWN_ATS_DOMAINS)
    trust_score = 0.82 if is_direct_ats else 0.68

    country_codes = query.target_country_codes or ["US"]
    category = query.category

    return create_normalized_opportunity(
        title=clean_title,
        company_name=company,
        description=sanitized_summary,
        source_url=result.url,
        source_system="web_search",
        source_job_id=f"ws_{abs(hash(result.url))}",
        category=category,
        eligible_country_codes=country_codes,
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS if category != OpportunityCategory.INTERNSHIP else DegreeLevel.NONE,
        requires_active_student_status=category == OpportunityCategory.INTERNSHIP,
        min_experience_months=min_exp,
        work_mode=work_mode,
        location_city_country=query.target_locations or [],
        skill_requirements=extracted_skills,
        mapped_occupation_code="15-1252.00",
        completeness_score=0.75,
        trust_score=trust_score,
        posted_at=result.published_date or datetime.now(UTC),
    )

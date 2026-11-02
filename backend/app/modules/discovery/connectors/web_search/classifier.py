from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import UTC, datetime
from typing import Optional

from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.discovery.connectors.parsing_utils import (
    determine_work_mode,
    extract_experience_months_with_confidence,
    extract_skills_from_text,
    strip_html_tags,
)
from app.modules.discovery.connectors.web_search.providers import RawSearchResult
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.discovery import DiscoverySearchQuery, OpportunityRejectionCode
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

# Reserved/placeholder/test domains that must never appear in real results
BLOCKED_DOMAINS: frozenset[str] = frozenset({
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "invalid",
    "placeholder.com",
    "jobs.example.com",
    "careers.example.com",
    "acme.com",  # classic fictional company domain
    "foo.com",
    "bar.com",
    "baz.com",
})

# Known job boards, aggregators, and career search engines.
# These must NEVER be assigned as the hiring company_name.
KNOWN_JOB_BOARDS: frozenset[str] = frozenset({
    "indeed",
    "glassdoor",
    "linkedin",
    "monster",
    "ziprecruiter",
    "dice",
    "simplyhired",
    "careerbuilder",
    "naukri",
    "foundit",
    "reed",
    "totaljobs",
    "builtin",
    "wellfound",
    "angellist",
    "upwork",
    "freelancer",
    "fiverr",
    "flexjobs",
    "snagajob",
    "jobrapido",
    "jooble",
    "adzuna",
    "salary",
    "comparably",
    "payscale",
    "themuse",
    "hired",
})

# Positive URL / path indicators for genuine individual requisitions
JOB_URL_PATTERNS = re.compile(
    r"(/jobs?/|/careers?/|/posting/|/requisition/|/apply/|/positions?/|/open-roles/|/vacancy/)",
    re.IGNORECASE,
)

# Collection, aggregator, and search result page URL patterns (to be rejected with COLLECTION_PAGE)
COLLECTION_URL_PATTERNS = re.compile(
    r"("
    r"[?&](q|query|k|keywords|keyword|search|searchTerm|title|what|where)=|"
    r"/(jobs-in-|jobs-near-|search/|browse/|categories/|directory/|category/|explore/)|"
    r"/(all-jobs|open-positions/?$|careers/?$|jobs/?$)"
    r")",
    re.IGNORECASE,
)

# Collection, aggregator, and multi-vacancy title patterns (to be rejected with COLLECTION_PAGE)
COLLECTION_TITLE_PATTERNS = re.compile(
    r"("
    r"\b(\d{2,}|hundreds of|dozens of|\d+k\+?)\s+.*?\b(jobs|vacancies|openings|positions|opportunities)\b|"
    r"\b(top|best|latest)\s+\d+\s+.*?\b(jobs|careers|openings|positions)\b|"
    r"^(jobs|vacancies|openings|careers)\s+in\b|"
    r"^career opportunities in\b|"
    r"\b(job board|job search engine|job directory|job portal)\b|"
    r"\b(browse all|view all|explore all)\s+(jobs|openings|positions)\b"
    r")",
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


class ClassificationResult(tuple):
    """Result tuple supporting both 2-element unpack `(is_job, reason)` and property access."""

    is_job: bool
    reason: str
    rejection_code: Optional[OpportunityRejectionCode]

    def __new__(
        cls,
        is_job: bool,
        reason: str,
        rejection_code: Optional[OpportunityRejectionCode] = None,
    ):
        inst = super().__new__(cls, (is_job, reason))
        inst.is_job = is_job
        inst.reason = reason
        inst.rejection_code = rejection_code
        return inst


class JobSearchResultClassifier:
    """Classifies raw search results to separate authentic individual vacancies from collection/aggregator pages."""

    @classmethod
    def evaluate(
        cls,
        result: RawSearchResult,
        query: DiscoverySearchQuery | None = None,
    ) -> ClassificationResult:
        """Returns ClassificationResult with (is_job, reason) and rejection_code attribute.

        rejection_code is None when is_job is True (accepted).
        When is_job is False, rejection_code carries a structured enum value
        suitable for telemetry aggregation in the discovery run.
        """
        # 0. Validate URL protocol and address
        parsed_url = urllib.parse.urlparse(result.url)
        if not parsed_url.scheme or parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            return ClassificationResult(
                False,
                "INVALID_URL: Search result URL must be a valid http/https address",
                OpportunityRejectionCode.INVALID_URL,
            )

        netloc = parsed_url.netloc.lower()
        domain = netloc.split(":")[0]
        for blocked in BLOCKED_DOMAINS:
            if domain == blocked or domain.endswith("." + blocked):
                return ClassificationResult(
                    False,
                    f"PLACEHOLDER_DOMAIN: Reserved or fictional domain detected ({blocked})",
                    OpportunityRejectionCode.PLACEHOLDER_DOMAIN,
                )

        # 1. Collection Page & Aggregator Search Result Filtering
        if COLLECTION_URL_PATTERNS.search(result.url):
            return ClassificationResult(
                False,
                f"COLLECTION_PAGE: Filtered as collection/search aggregator URL: {result.url}",
                OpportunityRejectionCode.COLLECTION_PAGE,
            )

        coll_match = COLLECTION_TITLE_PATTERNS.search(result.title)
        if coll_match:
            return ClassificationResult(
                False,
                f"COLLECTION_PAGE: Title indicates collection or listing directory ('{coll_match.group(0)}')",
                OpportunityRejectionCode.COLLECTION_PAGE,
            )

        url_lower = result.url.lower()
        title_lower = result.title.lower()
        combined_text = f"{url_lower} {title_lower} {result.snippet.lower()}"

        # 2. Negative filtering: Reject obvious non-job informational pages
        neg_match = NEGATIVE_PATTERNS.search(combined_text)
        if neg_match:
            return ClassificationResult(
                False,
                f"Filtered as informational / non-job content (matched '{neg_match.group(0)}')",
                OpportunityRejectionCode.INFORMATIONAL_CONTENT,
            )

        # 3. Strong Positive Signal A: Direct ATS domain in URL with specific requisition path
        for ats_domain in KNOWN_ATS_DOMAINS:
            if ats_domain in netloc:
                return ClassificationResult(True, f"Verified direct ATS domain: {ats_domain}")

        # 4. Strong Positive Signal B: Career / job requisition path in URL
        if JOB_URL_PATTERNS.search(parsed_url.path):
            return ClassificationResult(True, "URL path contains explicit career/job requisition routing")

        # 5. Strong Positive Signal C: Title contains explicit hiring terms
        if "hiring" in title_lower or "job application" in title_lower or "open position" in title_lower:
            return ClassificationResult(True, "Title contains explicit job application / hiring phrasing")

        # 6. Role Keyword match in title
        if JOB_TITLE_KEYWORDS.search(title_lower):
            # Check if title or snippet matches query role title
            if query and (query.role_title.lower() in title_lower or query.role_title.lower() in result.snippet.lower()):
                return ClassificationResult(True, "Role title and technology match target query")
            return ClassificationResult(True, "Title contains standard professional job title")

        return ClassificationResult(
            False,
            "Insufficient job posting indicators in URL and metadata",
            OpportunityRejectionCode.INSUFFICIENT_INDICATORS,
        )


def extract_company_from_title(title: str, url: str) -> str:
    """Deterministically extracts hiring company name from search result title or URL domain.

    Guarantees:
    - Never extracts job boards or aggregators (Indeed, LinkedIn, Glassdoor, etc.) as the employer.
    - Accurately parses 'at [Company]', '[Company] - [Title]', or '[Title] - [Company] - [Platform]'.
    - Returns 'Unstated Employer' if the hiring organization cannot be cleanly separated.
    """
    cleaned = strip_html_tags(title)

    def _is_job_board(text: str) -> bool:
        t_clean = re.sub(r"[^a-zA-Z0-9]", "", text.lower())
        return any(board in t_clean for board in KNOWN_JOB_BOARDS)

    # Patterns like: "Senior Backend Engineer at Acme Corp" or "Python Dev at Acme Corp | LinkedIn"
    if " at " in cleaned:
        parts = cleaned.split(" at ")
        subparts = re.split(r"[\-|\|·]", parts[-1])
        for sub in subparts:
            cand = sub.strip()
            if cand and len(cand) <= 60 and not _is_job_board(cand) and not JOB_TITLE_KEYWORDS.search(cand):
                return cand

    # Patterns with delimiters: "Acme Corp - Senior Backend Engineer" or "Senior Backend Engineer - Acme Corp - Indeed"
    delims = [" - ", " | ", " · "]
    for delim in delims:
        if delim in cleaned:
            parts = [p.strip() for p in cleaned.split(delim) if p.strip()]
            valid_company_candidates = [
                p for p in parts
                if len(p) <= 50 and not _is_job_board(p) and not JOB_TITLE_KEYWORDS.search(p)
            ]
            if valid_company_candidates:
                return valid_company_candidates[0]

    # Patterns like: "Acme Corp is hiring..."
    if " is hiring " in cleaned.lower():
        idx = cleaned.lower().index(" is hiring ")
        cand = cleaned[:idx].strip()
        if cand and not _is_job_board(cand):
            return cand

    # Fallback to domain name: careers.acmecorp.com -> Acme Corp
    parsed = urllib.parse.urlparse(url)
    domain_parts = parsed.netloc.replace("www.", "").split(".")
    if len(domain_parts) >= 2:
        name = domain_parts[0]
        if name in ("jobs", "careers", "boards", "job-boards") and len(domain_parts) >= 3:
            name = domain_parts[1]

        # If the domain itself is a job board (e.g. indeed.com, linkedin.com, glassdoor.com)
        if _is_job_board(name):
            return "Unstated Employer"

        clean_name = name.replace("-", " ").title()
        if len(clean_name) <= 40:
            return clean_name

    return "Unstated Employer"


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

    min_exp, exp_confident = extract_experience_months_with_confidence(clean_snippet, title=clean_title)
    if "INTERN" in query.seniority_level or query.category == OpportunityCategory.INTERNSHIP:
        # Internship/intern queries always require 0 experience — override any extracted value.
        min_exp = 0
    elif not exp_confident:
        # No deterministic experience signal was found in the short web snippet.
        # Use -1 as sentinel so the eligibility engine can flag UNCERTAIN instead of
        # incorrectly treating this as a 0-months-required (entry-level) opportunity.
        min_exp = -1

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
        is_verified_posting=False,
    )

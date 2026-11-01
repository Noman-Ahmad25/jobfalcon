from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.sanitization import sanitize_untrusted_text
from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.discovery.connectors.parsing_utils import (
    determine_work_mode,
    extract_experience_months,
    extract_skills_from_text,
    strip_html_tags,
)
from app.schemas.common import DegreeLevel, OpportunityCategory, WorkMode
from app.schemas.discovery import DiscoverySearchQuery
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity

logger = logging.getLogger(__name__)

# Known direct ATS domains that increase source trust score
TRUSTED_ATS_DOMAINS = (
    "greenhouse.io",
    "grnh.se",
    "lever.co",
    "ashbyhq.com",
    "workday.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "jobvite.com",
    "icims.com",
)


class JobSpyMCPNormalizer:
    """Normalizes raw MCP tool outputs into validated, injection-resistant PolymorphicOpportunities."""

    @classmethod
    def normalize_job_record(
        cls,
        raw_job: dict[str, Any],
        query: DiscoverySearchQuery,
    ) -> PolymorphicOpportunity:
        """Transforms a raw job record from MCP tool output into an auditable PolymorphicOpportunity."""
        # 1. Title & Company Sanitization
        raw_title = str(raw_job.get("title") or query.role_title)
        raw_company = str(raw_job.get("company") or "Independent Employer")

        clean_title = sanitize_untrusted_text(strip_html_tags(raw_title))
        clean_company = sanitize_untrusted_text(strip_html_tags(raw_company))

        # 2. Destination URL & Source System
        site_name = str(raw_job.get("site") or "indeed").lower()
        direct_url = raw_job.get("job_url_direct") or raw_job.get("job_url") or ""
        job_id = str(raw_job.get("id") or "")

        # Fallback URL if direct link is empty
        if direct_url and str(direct_url).startswith("http"):
            source_url = str(direct_url)
        elif job_id:
            source_url = f"https://www.{site_name}.com/viewjob?jk={job_id}"
        else:
            source_url = f"https://www.{site_name}.com/jobs?q={clean_title.replace(' ', '+')}"

        # 3. Description & Provenance Sanitization
        raw_desc = str(raw_job.get("description") or "")
        clean_desc = strip_html_tags(raw_desc).strip()
        if not clean_desc:
            clean_desc = (
                f"Position for {clean_title} at {clean_company}. "
                f"Sourced via JobSpy MCP from {site_name.capitalize()}. "
                f"Review direct listing for complete details."
            )

        sanitized_summary = (
            f"[MCP Tool Result: jobspy/search_jobs - Unverified Requisition] {clean_desc[:2200]}"
        )

        # 4. Location & Work Mode
        loc_str = str(raw_job.get("location") or "")
        is_remote_flag = bool(raw_job.get("is_remote"))
        work_mode = WorkMode.REMOTE if is_remote_flag else determine_work_mode(loc_str)

        # Align with candidate query preference if applicable
        if work_mode == WorkMode.ON_SITE and query.work_modes:
            if WorkMode.REMOTE in query.work_modes and "remote" in loc_str.lower():
                work_mode = WorkMode.REMOTE

        # 5. Skill Extraction
        extracted_skills = extract_skills_from_text(f"{clean_title} {clean_desc}")
        if not extracted_skills and query.expanded_keywords:
            extracted_skills = [
                OpportunitySkillRequirement(
                    canonical_skill_id=f"skill_mcp_{kw.lower()}",
                    skill_name=kw,
                    is_mandatory=True,
                    minimum_proficiency_expected=5.0,
                )
                for kw in query.expanded_keywords[:3]
            ]

        # 6. Experience & Category
        exp_months = extract_experience_months(clean_desc, title=clean_title)
        category = query.category
        if "intern" in clean_title.lower() or "internship" in str(raw_job.get("job_type", "")).lower():
            category = OpportunityCategory.INTERNSHIP
            exp_months = 0

        # 7. Trust & Completeness Scoring
        is_direct_ats = any(domain in source_url.lower() for domain in TRUSTED_ATS_DOMAINS)
        trust_score = 0.85 if is_direct_ats else 0.78
        completeness_score = 0.85 if len(clean_desc) > 300 else 0.75

        # 8. Category-specific Attributes
        attributes: dict[str, Any] = {
            "platform": site_name.capitalize(),
            "source_id": job_id,
            "mcp_server": "jobspy",
            "mcp_tool": "search_jobs",
        }
        if raw_job.get("min_amount"):
            attributes["min_amount"] = raw_job.get("min_amount")
        if raw_job.get("max_amount"):
            attributes["max_amount"] = raw_job.get("max_amount")
        if raw_job.get("currency"):
            attributes["currency"] = raw_job.get("currency")
        if raw_job.get("interval"):
            attributes["interval"] = raw_job.get("interval")

        # 9. Date Posted
        posted_at = datetime.now(timezone.utc)
        if raw_job.get("date_posted"):
            try:
                date_val = raw_job.get("date_posted")
                if isinstance(date_val, datetime):
                    posted_at = date_val if date_val.tzinfo else date_val.replace(tzinfo=timezone.utc)
                elif isinstance(date_val, str):
                    posted_at = datetime.fromisoformat(date_val)
                    if not posted_at.tzinfo:
                        posted_at = posted_at.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        location_list = [loc_str] if loc_str and "remote" not in loc_str.lower() else []

        return create_normalized_opportunity(
            title=clean_title,
            company_name=clean_company,
            description=sanitized_summary,
            source_url=source_url,
            source_system="jobspy_mcp",
            source_job_id=f"mcp_{site_name}_{job_id or abs(hash(source_url))}",
            category=category,
            eligible_country_codes=query.target_country_codes or ["US"],
            sponsors_work_visa=False,
            minimum_degree_required=DegreeLevel.BACHELORS if category != OpportunityCategory.INTERNSHIP else DegreeLevel.NONE,
            requires_active_student_status=category == OpportunityCategory.INTERNSHIP,
            min_experience_months=exp_months,
            work_mode=work_mode,
            location_city_country=location_list,
            skill_requirements=extracted_skills,
            mapped_occupation_code="15-1252.00",
            completeness_score=completeness_score,
            trust_score=trust_score,
            posted_at=posted_at,
            category_specific_attributes=attributes,
        )

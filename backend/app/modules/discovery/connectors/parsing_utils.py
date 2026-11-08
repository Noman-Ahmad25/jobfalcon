from __future__ import annotations

import html
import re
from typing import Optional

from app.schemas.common import WorkMode
from app.schemas.opportunity import OpportunitySkillRequirement

# Canonical skills and common variations for deterministic skill extraction
SKILL_TAXONOMY_DICTIONARY: dict[str, tuple[str, ...]] = {
    "Python": ("python", "python3", "py"),
    "TypeScript": ("typescript", "ts"),
    "JavaScript": ("javascript", "js", "ecmascript"),
    "React": ("react", "react.js", "reactjs"),
    "Next.js": ("next.js", "nextjs", "next js"),
    "Vue": ("vue", "vue.js", "vuejs"),
    "Node.js": ("node.js", "nodejs", "node"),
    "Go": ("golang", "go"),
    "Java": ("java", "jvm"),
    "C++": ("c++", "cpp"),
    "Rust": ("rust", "rustlang"),
    "FastAPI": ("fastapi",),
    "Django": ("django",),
    "Flask": ("flask",),
    "SQL": ("sql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Redis": ("redis",),
    "GraphQL": ("graphql",),
    "REST API": ("rest api", "restful api", "rest apis", "restful apis"),
    "Docker": ("docker", "containerization"),
    "Kubernetes": ("kubernetes", "k8s"),
    "AWS": ("aws", "amazon web services"),
    "GCP": ("gcp", "google cloud platform"),
    "Azure": ("azure", "microsoft azure"),
    "Git": ("git", "github", "gitlab"),
    "CI/CD": ("ci/cd", "continuous integration", "github actions"),
    "Microservices": ("microservices", "microservice architecture"),
    "Distributed Systems": ("distributed systems", "distributed computing"),
    "Tailwind": ("tailwind", "tailwind css", "tailwindcss"),
    "PyTorch": ("pytorch",),
    "TensorFlow": ("tensorflow",),
    "Machine Learning": ("machine learning", "deep learning"),
    "LLM": ("llm", "large language models", "prompt engineering"),
}


def strip_html_tags(html_text: str) -> str:
    """Strips HTML tags, decodes entities, and normalizes whitespace."""
    if not html_text:
        return ""
    text = html.unescape(html_text)
    # Remove script and style elements
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse multiple whitespace characters into single space
    return re.sub(r"\s+", " ", text).strip()


PREFERRED_QUALIFICATION_CUES: tuple[str, ...] = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "is a plus",
    "a plus",
    "bonus",
    "good to have",
    "optional",
    "desired",
    "advantageous",
)


def extract_skills_from_text(
    text: str,
    max_skills: int = 8,
) -> list[OpportunitySkillRequirement]:
    """Deterministically extracts canonical skill requirements from normalized job text.

    Distinguishes mandatory requirements from preferred/nice-to-have qualifications
    based on section headings and local sentence/clause context cues.
    """
    if not text:
        return []

    lowered = text.lower()
    extracted: list[OpportunitySkillRequirement] = []

    # Check for dedicated preferred qualifications section
    preferred_section_start = -1
    for heading in ("preferred qualifications", "preferred skills", "nice to have", "nice-to-have", "desired skills", "bonus points"):
        idx = lowered.find(heading)
        if idx != -1:
            preferred_section_start = idx
            break

    for canonical_name, variants in SKILL_TAXONOMY_DICTIONARY.items():
        for variant in variants:
            pattern = r"(?:\b|_)" + re.escape(variant) + r"(?:\b|_)"
            match = re.search(pattern, lowered)
            if match:
                is_preferred = False
                pos = match.start()

                # 1. Check if located inside an explicit preferred section
                if preferred_section_start != -1 and pos > preferred_section_start:
                    is_preferred = True
                else:
                    # 2. Check local sentence/clause (delimited by periods or linebreaks)
                    clause_start = max(lowered.rfind(".", 0, pos), lowered.rfind("\n", 0, pos), 0)
                    clause_end = len(lowered)
                    next_period = lowered.find(".", match.end())
                    next_nl = lowered.find("\n", match.end())
                    if next_period != -1 and (next_nl == -1 or next_period < next_nl):
                        clause_end = next_period
                    elif next_nl != -1:
                        clause_end = next_nl

                    clause = lowered[clause_start:clause_end]
                    is_preferred = any(cue in clause for cue in PREFERRED_QUALIFICATION_CUES)

                clean_id = f"skill_{canonical_name.lower().replace('.', '').replace(' ', '_').replace('+', 'p')}"
                extracted.append(
                    OpportunitySkillRequirement(
                        canonical_skill_id=clean_id,
                        skill_name=canonical_name,
                        is_mandatory=not is_preferred,
                        minimum_proficiency_expected=5.0,
                    )
                )
                break
        if len(extracted) >= max_skills:
            break

    return extracted


def format_experience_requirement(months: int) -> str:
    """Returns human-readable experience string obeying 'Unknown is not zero'.

    If months < 0, explicitly returns 'Not stated' rather than converting to 0.
    """
    if months < 0:
        return "Not stated"
    if months == 0:
        return "Entry level (no prior experience required)"
    years = months // 12
    rem = months % 12
    if rem == 0:
        return f"{years}+ year{'s' if years != 1 else ''}"
    return f"{months} months"


def extract_experience_months_with_confidence(
    text: str,
    title: str = "",
    default_months: int = 0,
) -> tuple[int, bool]:
    """Returns (months, is_confident).

    is_confident=True means experience was explicitly stated OR strongly implied by a
    seniority keyword in the title — a deterministic signal was found.
    is_confident=False means no deterministic signal was found in the available text;
    the caller should treat the requirement as UNCERTAIN rather than defaulting to 0.
    """
    full_text = f"{title} {text}".lower()

    # Entry-level indicators: confident at 0 months required
    if any(k in full_text for k in ("intern", "internship", "entry level", "entry-level", "junior", "associate", "new grad", "new-grad", "graduate")):
        return 0, True

    # Explicit year patterns: e.g., "5+ years", "3-5 years", "at least 4 years"
    matches = re.findall(r"(\d+)\+?\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)\b", full_text)
    if matches:
        years_found = [int(m[0]) for m in matches if m[0].isdigit() and 1 <= int(m[0]) <= 25]
        if years_found:
            return min(years_found) * 12, True

    # Title seniority heuristics: deterministic signals from job title keywords
    title_lower = title.lower()
    if any(k in title_lower for k in ("principal", "director", "architect")):
        return 96, True   # ~8 years
    if any(k in title_lower for k in ("staff", "lead")):
        return 72, True   # ~6 years
    if "senior" in title_lower or "sr." in title_lower:
        return 48, True   # ~4 years

    # No deterministic signal found — caller should treat as UNCERTAIN
    return default_months, False


def extract_experience_months(
    text: str,
    title: str = "",
    default_months: int = 0,
) -> int:
    """Extracts minimum experience requirements in months from title and description.

    Thin backward-compatible wrapper around extract_experience_months_with_confidence.
    Discards the confidence flag; use extract_experience_months_with_confidence directly
    when the caller needs to distinguish 'confirmed 0' from 'unknown'.
    """
    months, _ = extract_experience_months_with_confidence(text, title, default_months)
    return months


def determine_work_mode(
    location_str: str = "",
    workplace_type: str = "",
) -> WorkMode:
    """Determines work mode from location text or ATS workplace type."""
    combined = f"{location_str} {workplace_type}".lower()
    if "hybrid" in combined:
        return WorkMode.HYBRID
    if "remote" in combined:
        return WorkMode.REMOTE
    return WorkMode.ON_SITE


KNOWN_TECH_CITIES: tuple[str, ...] = (
    "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi", "Gurgaon", "Gurugram",
    "Noida", "Chennai", "Kolkata", "Ahmedabad", "San Francisco", "San Jose", "Sunnyvale",
    "Mountain View", "Palo Alto", "Seattle", "Redmond", "Bellevue", "New York", "Austin",
    "Boston", "Cambridge", "Chicago", "Denver", "Boulder", "Los Angeles", "San Diego",
    "London", "Dublin", "Berlin", "Munich", "Amsterdam", "Paris", "Zurich", "Toronto",
    "Vancouver", "Montreal", "Singapore", "Tokyo", "Sydney", "Melbourne",
)

REMOTE_SCOPE_CUES: tuple[str, ...] = (
    "India", "United States", "US", "USA", "North America", "EMEA", "APAC", "LATAM",
    "Europe", "UK", "United Kingdom", "Canada", "Germany", "Australia", "Global", "Worldwide",
)


def format_opportunity_location(
    work_mode: WorkMode | str,
    locations: Optional[list[str]] = None,
) -> str:
    """Formats opportunity location according to JobFalcon canonical rules:
    - Explicit city/location in the listing -> Display that location.
    - Explicit remote position with a specified geographic scope -> Display `Remote — [scope]`.
    - Explicitly remote without geographic scope -> Display `Remote`.
    - Hybrid position -> Display the actual location and hybrid designation.
    - Location absent or unverifiable -> Display `Location not specified`.
    """
    mode_str = work_mode.value if isinstance(work_mode, WorkMode) else str(work_mode or "").upper()
    valid_locs = [loc.strip() for loc in (locations or []) if loc and loc.strip()]

    # Case: REMOTE
    if mode_str == "REMOTE":
        if not valid_locs:
            return "Remote"

        raw_scope = valid_locs[0]
        lower_scope = raw_scope.lower()
        if lower_scope in ("remote", "anywhere", "worldwide", "global", "flexible"):
            return "Remote"

        # Strip any redundant "Remote -", "Remote —", "Remote in", "Remote (India)", etc.
        clean_scope = re.sub(r"^remote\s*(?:[-—–:,]|\bin\b|\bwithin\b)?\s*[\(\[]?", "", raw_scope, flags=re.IGNORECASE).strip()
        clean_scope = re.sub(r"[\)\]]+$", "", clean_scope).strip()
        clean_scope = re.sub(r"\bonly\b", "", clean_scope, flags=re.IGNORECASE).strip()
        if not clean_scope or clean_scope.lower() in ("remote", "anywhere", "worldwide", "global", "flexible"):
            return "Remote"

        return f"Remote — {clean_scope}"

    # Case: HYBRID
    if mode_str == "HYBRID":
        if not valid_locs:
            return "Hybrid (Location not specified)"

        raw_loc = ", ".join(valid_locs)
        clean_loc = re.sub(r"\(?hybrid\)?", "", raw_loc, flags=re.IGNORECASE).strip(" -—–,")
        if not clean_loc:
            return "Hybrid (Location not specified)"
        return f"{clean_loc} (Hybrid)"

    # Case: ON_SITE or UNSPECIFIED
    if not valid_locs:
        return "Location not specified"

    return ", ".join(valid_locs)


def _extract_city_from_text(text: str) -> str:
    """Extracts explicit city/location mention from text."""
    if not text:
        return ""

    # Check for "Location: <city, country>" pattern
    m_loc = re.search(
        r"(?:location|office|based in)\s*:\s*([A-Za-z\s,\.-]+?)(?:\.|\n|;|\band\b|Full[- ]time|Part[- ]time|Competitive|Salary|Benefits|Apply|View|\Z)",
        text,
        re.IGNORECASE,
    )
    if m_loc:
        cand = m_loc.group(1).strip(" -—–,")
        if cand and len(cand) <= 60 and cand.lower() not in ("remote", "hybrid", "unspecified", "various", "flexible"):
            return cand

    # Check for "in <City>, <Country/State>"
    m_in = re.search(
        r"\bin\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?,\s*(?:[A-Z]{2}|[A-Z][a-zA-Z]+))\b",
        text,
    )
    if m_in:
        return m_in.group(1).strip()

    # Search for known tech cities
    for city in KNOWN_TECH_CITIES:
        pattern = r"\b" + re.escape(city) + r"(?:,\s*([A-Za-z\s]+))?\b"
        m_city = re.search(pattern, text)
        if m_city:
            if m_city.group(1):
                country_state = m_city.group(1).strip()
                if len(country_state) < 30 and "\n" not in country_state:
                    return f"{city}, {country_state}"
            return city

    return ""


def parse_location_and_work_mode(
    raw_location: Optional[str] = None,
    text: str = "",
    title: str = "",
    workplace_type: str = "",
    is_remote: Optional[bool] = None,
) -> tuple[list[str], WorkMode]:
    """Deterministically parses location list and WorkMode from opportunity metadata and text.

    Guarantees:
    - Never populates opportunity location from candidate preferences or query parameters.
    - Extracts explicit remote scopes (e.g. 'Remote - India' -> ['India'], WorkMode.REMOTE).
    - Preserves explicit city/region locations for on-site and hybrid roles.
    - Returns empty location list when location is absent or unverifiable.
    """
    combined_meta = f"{raw_location or ''} {workplace_type} {title}".strip()
    full_text = f"{combined_meta} {text}"
    full_lower = full_text.lower()

    # 1. Determine WorkMode
    is_hybrid_mode = (
        "hybrid" in workplace_type.lower()
        or (bool(raw_location) and "hybrid" in str(raw_location).lower())
        or "(hybrid)" in title.lower()
        or bool(re.search(r"\bhybrid\b", full_lower))
    )

    is_remote_mode = (
        is_remote is True
        or "remote" in workplace_type.lower()
        or (bool(raw_location) and "remote" in str(raw_location).lower())
        or bool(re.search(r"\b(?:remote|work from home|wfh|telecommute)\b", full_lower))
    )

    if is_hybrid_mode:
        work_mode = WorkMode.HYBRID
    elif is_remote_mode:
        work_mode = WorkMode.REMOTE
    else:
        work_mode = WorkMode.ON_SITE

    # 2. Extract Location / Scope
    # Case A: REMOTE
    if work_mode == WorkMode.REMOTE:
        scope: Optional[str] = None
        # Check raw_location first
        if raw_location:
            m = re.search(
                r"remote\s*(?:[-—–:,]|\bin\b|\bwithin\b|\bfor\b)?\s*[\(\[]?([^()\]\n]+)[\)\]]?",
                raw_location,
                re.IGNORECASE,
            )
            if m:
                cand_scope = m.group(1).strip(" -—–,")
                cand_scope = re.sub(r"\bonly\b", "", cand_scope, flags=re.IGNORECASE).strip()
                if cand_scope and cand_scope.lower() not in ("remote", "work", "job", "position", "anywhere", "worldwide", "global", "flexible"):
                    scope = cand_scope
            elif raw_location.lower() not in ("remote", "fully remote", "100% remote", "remote work", "work from home"):
                scope = raw_location.strip()

        # If no scope yet, check title & text for explicit remote scope cues
        if not scope:
            m = re.search(
                r"remote\s*(?:[-—–:,]|\bin\b|\bwithin\b)\s*[\(\[]?([A-Za-z\s]+?)(?:[\)\]]|\bonly\b|\beligible\b|\bbased\b|\.|\n|$)",
                f"{title} {text}",
                re.IGNORECASE,
            )
            if m:
                cand_scope = m.group(1).strip()
                cand_scope = re.sub(r"\bonly\b", "", cand_scope, flags=re.IGNORECASE).strip()
                if any(cand_scope.lower() == sc.lower() for sc in REMOTE_SCOPE_CUES):
                    scope = cand_scope

        if scope and scope.lower() not in ("remote", "work", "job", "position", "anywhere", "worldwide", "global", "flexible"):
            return [scope], WorkMode.REMOTE
        return [], WorkMode.REMOTE

    # Case B: HYBRID
    if work_mode == WorkMode.HYBRID:
        loc_str = ""
        if raw_location:
            loc_str = re.sub(r"\(?hybrid\)?", "", raw_location, flags=re.IGNORECASE).strip(" -—–,")
        if not loc_str:
            loc_str = _extract_city_from_text(f"{title} {text}")
        if loc_str:
            return [loc_str], WorkMode.HYBRID
        return [], WorkMode.HYBRID

    # Case C: ON_SITE
    loc_str = ""
    if raw_location:
        cleaned = raw_location.strip()
        if cleaned.lower() not in ("unspecified", "not specified", "various", "n/a", "multiple locations", "unknown", "remote", "hybrid"):
            loc_str = cleaned
    if not loc_str:
        loc_str = _extract_city_from_text(f"{title} {text}")
    if loc_str:
        return [loc_str], WorkMode.ON_SITE

    return [], WorkMode.ON_SITE

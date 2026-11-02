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
    if "remote" in combined:
        return WorkMode.REMOTE
    if "hybrid" in combined:
        return WorkMode.HYBRID
    return WorkMode.ON_SITE

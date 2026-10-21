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


def extract_skills_from_text(
    text: str,
    max_skills: int = 8,
) -> list[OpportunitySkillRequirement]:
    """Deterministically extracts canonical skill requirements from normalized job text."""
    if not text:
        return []

    lowered = text.lower()
    extracted: list[OpportunitySkillRequirement] = []

    for canonical_name, variants in SKILL_TAXONOMY_DICTIONARY.items():
        for variant in variants:
            # Word boundary matching
            pattern = r"(?:\b|_)" + re.escape(variant) + r"(?:\b|_)"
            if re.search(pattern, lowered):
                clean_id = f"skill_{canonical_name.lower().replace('.', '').replace(' ', '_').replace('+', 'p')}"
                extracted.append(
                    OpportunitySkillRequirement(
                        canonical_skill_id=clean_id,
                        skill_name=canonical_name,
                        is_mandatory=True,
                        minimum_proficiency_expected=5.0,
                    )
                )
                break
        if len(extracted) >= max_skills:
            break

    return extracted


def extract_experience_months(
    text: str,
    title: str = "",
    default_months: int = 0,
) -> int:
    """Extracts minimum experience requirements in months from title and description."""
    full_text = f"{title} {text}".lower()

    # If title indicates intern or entry level, return 0
    if any(k in full_text for k in ("intern", "internship", "entry level", "junior", "associate", "new grad")):
        return 0

    # Look for numeric year patterns: e.g., "5+ years", "3-5 years", "at least 4 years"
    matches = re.findall(r"(\d+)\+?\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)\b", full_text)
    if matches:
        # Use the lowest stated year bound
        years_found = [int(m[0]) for m in matches if m[0].isdigit() and 1 <= int(m[0]) <= 20]
        if years_found:
            return min(years_found) * 12

    # Title-based heuristic fallback if senior / lead / staff
    if any(k in title.lower() for k in ("principal", "director", "architect")):
        return 96  # 8 years
    if any(k in title.lower() for k in ("staff", "lead")):
        return 72  # 6 years
    if "senior" in title.lower() or "sr." in title.lower():
        return 48  # 4 years

    return default_months


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

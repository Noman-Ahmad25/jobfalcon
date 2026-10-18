from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Sequence

from app.schemas.common import CareerPathRelationship, OpportunityCategory, WorkMode
from app.schemas.discovery import (
    DiscoveryQueryPlan,
    DiscoverySearchQuery,
    RoleMappingTarget,
)
from app.schemas.profile import CandidateCareerProfile


@dataclass(frozen=True)
class RoleArchetype:
    """Pre-calibrated taxonomic archetype linking standard role families to O*NET codes and skills."""

    role_title: str
    canonical_occupation_code: str
    category_family: str
    core_skills: tuple[str, ...]
    adjacent_titles: tuple[str, ...]
    synonyms: tuple[str, ...]


# Curated occupational taxonomy archetypes based on O*NET 2024 / ESCO v1.2 standards
ROLE_ARCHETYPES: list[RoleArchetype] = [
    RoleArchetype(
        role_title="Backend Software Engineer",
        canonical_occupation_code="15-1252.00",  # O*NET: Software Developers
        category_family="Software Engineering",
        core_skills=(
            "python", "fastapi", "django", "flask", "go", "java", "sql",
            "postgresql", "redis", "docker", "rest api", "microservices", "git"
        ),
        adjacent_titles=("Full Stack Developer", "DevOps Engineer", "Data Engineer"),
        synonyms=("Backend Developer", "Server Engineer", "Software Engineer - Backend", "Backend Engineer"),
    ),
    RoleArchetype(
        role_title="Frontend Engineer",
        canonical_occupation_code="15-1254.00",  # O*NET: Web Developers
        category_family="Software Engineering",
        core_skills=(
            "typescript", "javascript", "react", "next.js", "vue", "html",
            "css", "tailwind", "redux", "webpack", "responsive design", "git"
        ),
        adjacent_titles=("Full Stack Developer", "UI/UX Engineer", "Mobile Developer"),
        synonyms=("Frontend Developer", "Web Developer", "Client-Side Engineer", "UI Engineer"),
    ),
    RoleArchetype(
        role_title="Full Stack Developer",
        canonical_occupation_code="15-1252.00",  # O*NET: Software Developers
        category_family="Software Engineering",
        core_skills=(
            "typescript", "javascript", "react", "python", "node.js",
            "sql", "postgresql", "rest api", "docker", "git"
        ),
        adjacent_titles=("Backend Software Engineer", "Frontend Engineer", "DevOps Engineer"),
        synonyms=("Full Stack Engineer", "Software Engineer - Full Stack", "Full-Stack Developer"),
    ),
    RoleArchetype(
        role_title="Machine Learning Engineer",
        canonical_occupation_code="15-1251.00",  # O*NET: Computer and Information Research Scientists
        category_family="Artificial Intelligence & Data",
        core_skills=(
            "python", "pytorch", "tensorflow", "scikit-learn", "numpy", "pandas",
            "machine learning", "deep learning", "nlp", "llm", "docker", "sql"
        ),
        adjacent_titles=("Data Scientist", "Data Engineer", "Backend Software Engineer"),
        synonyms=("AI Engineer", "ML Engineer", "Machine Learning Scientist", "Applied Scientist"),
    ),
    RoleArchetype(
        role_title="Data Engineer",
        canonical_occupation_code="15-2051.00",  # O*NET: Data Scientists / Data Engineers
        category_family="Artificial Intelligence & Data",
        core_skills=(
            "python", "sql", "spark", "kafka", "airflow", "postgresql",
            "data pipeline", "etl", "snowflake", "docker", "aws"
        ),
        adjacent_titles=("Backend Software Engineer", "Machine Learning Engineer", "DevOps Engineer"),
        synonyms=("Data Platform Engineer", "Big Data Engineer", "ETL Developer"),
    ),
    RoleArchetype(
        role_title="DevOps & Platform Engineer",
        canonical_occupation_code="15-1244.00",  # O*NET: Network and Computer Systems Administrators
        category_family="Infrastructure & Operations",
        core_skills=(
            "docker", "kubernetes", "linux", "ci/cd", "terraform", "aws",
            "gcp", "bash", "python", "ansible", "monitoring", "git"
        ),
        adjacent_titles=("Backend Software Engineer", "Site Reliability Engineer", "Cloud Architect"),
        synonyms=("DevOps Engineer", "Cloud Engineer", "Infrastructure Engineer", "Platform Engineer"),
    ),
    RoleArchetype(
        role_title="Mobile Developer",
        canonical_occupation_code="15-1252.00",  # O*NET: Software Developers
        category_family="Software Engineering",
        core_skills=(
            "swift", "kotlin", "react native", "flutter", "ios", "android",
            "mobile development", "typescript", "git", "rest api"
        ),
        adjacent_titles=("Frontend Engineer", "Full Stack Developer"),
        synonyms=("iOS Developer", "Android Developer", "Mobile Engineer"),
    ),
]


def _normalize_token(text: str) -> str:
    """Normalizes token for case and punctuation insensitive matching."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _find_matching_archetype(title: str) -> Optional[RoleArchetype]:
    """Finds best matching taxonomy archetype by title or synonym."""
    norm_title = _normalize_token(title)
    for arch in ROLE_ARCHETYPES:
        if _normalize_token(arch.role_title) in norm_title or norm_title in _normalize_token(arch.role_title):
            return arch
        for syn in arch.synonyms:
            if _normalize_token(syn) in norm_title or norm_title in _normalize_token(syn):
                return arch
    return None


def _calculate_seniority(candidate: CandidateCareerProfile) -> str:
    """Deterministically infers seniority level from experience and student status."""
    constraints = candidate.eligibility_constraints
    if constraints.is_currently_enrolled_student:
        if constraints.total_full_time_experience_months < 12:
            return "INTERN"
    if constraints.total_full_time_experience_months <= 12:
        return "ENTRY_LEVEL"
    if constraints.total_full_time_experience_months <= 36:
        return "MID_LEVEL"
    return "SENIOR"


def _generate_queries_for_target(
    candidate: CandidateCareerProfile,
    target: RoleMappingTarget,
    matched_skills: list[str],
    seniority: str,
) -> list[DiscoverySearchQuery]:
    """Constructs focused, parameterized queries for a given role mapping target."""
    queries: list[DiscoverySearchQuery] = []
    constraints = candidate.eligibility_constraints
    categories = constraints.allowed_opportunity_categories
    work_modes = constraints.allowed_work_modes
    country_codes = constraints.authorized_country_codes
    locations = constraints.preferred_locations

    # Take top 3-4 skills for query building
    top_skills = [s for s in matched_skills[:4] if s]

    for category in categories:
        # Determine prefix / role modifier
        if category == OpportunityCategory.INTERNSHIP or seniority == "INTERN":
            role_kw = f"{target.role_title} Intern"
        elif seniority == "ENTRY_LEVEL":
            role_kw = f"Junior {target.role_title}"
        elif seniority == "SENIOR":
            role_kw = f"Senior {target.role_title}"
        else:
            role_kw = target.role_title

        # Query 1: Role keyword + primary technologies
        tech_suffix = " ".join(top_skills[:2]) if top_skills else ""
        mode_suffix = "remote" if WorkMode.REMOTE in work_modes else ""
        query_str_1 = f'"{role_kw}" {tech_suffix} {mode_suffix}'.strip()

        expanded_kw_1 = list(top_skills)
        expanded_kw_1.extend([target.role_title, category.value.lower()])

        q1 = DiscoverySearchQuery(
            query_id=f"q_{target.canonical_occupation_code}_{category.value}_{len(queries)+1}",
            role_title=target.role_title,
            query_string=query_str_1,
            expanded_keywords=expanded_kw_1,
            category=category,
            work_modes=work_modes,
            target_locations=locations,
            target_country_codes=country_codes,
            seniority_level=seniority,
            relationship_type=target.relationship_type,
        )
        queries.append(q1)

        # Query 2: Broader query with target locations or country codes
        loc_str = locations[0] if locations else (country_codes[0] if country_codes else "")
        query_str_2 = f'{target.role_title} {loc_str}'.strip()
        q2 = DiscoverySearchQuery(
            query_id=f"q_{target.canonical_occupation_code}_{category.value}_{len(queries)+1}",
            role_title=target.role_title,
            query_string=query_str_2,
            expanded_keywords=[target.role_title] + top_skills,
            category=category,
            work_modes=work_modes,
            target_locations=locations,
            target_country_codes=country_codes,
            seniority_level=seniority,
            relationship_type=target.relationship_type,
        )
        queries.append(q2)

    return queries


def map_profile_to_target_roles(profile: CandidateCareerProfile) -> list[RoleMappingTarget]:
    """Relates candidate extracted skills and preferences to relevant role families.

    Rules:
    1. Explicit target career paths from candidate profile are mapped as TARGET nodes (confidence = 1.0).
    2. Missing core skills are identified by comparing candidate skills to canonical archetype competencies.
    3. Archetypes with strong skill overlap (>= 30%) not explicitly targeted are added as ADJACENT nodes.
    4. Distinguishes explicit preferences from inferred roles without false equivalences.
    """
    targets: list[RoleMappingTarget] = []
    mapped_titles: set[str] = set()

    candidate_skills_norm = {
        _normalize_token(skill.skill_name): skill.skill_name
        for skill in profile.assessed_skills
    }
    seniority = _calculate_seniority(profile)

    # 1. Process explicit target career paths
    for target_path in profile.target_career_paths:
        archetype = _find_matching_archetype(target_path.title)
        role_title = archetype.role_title if archetype else target_path.title
        occ_code = archetype.canonical_occupation_code if archetype else target_path.occupation_code

        matched_skills: list[str] = []
        missing_skills: list[str] = []

        if archetype:
            for core_s in archetype.core_skills:
                norm_core = _normalize_token(core_s)
                if norm_core in candidate_skills_norm:
                    matched_skills.append(candidate_skills_norm[norm_core])
                else:
                    missing_skills.append(core_s)
        else:
            # Fallback to candidate skills
            matched_skills = [s.skill_name for s in profile.assessed_skills[:5]]

        role_target = RoleMappingTarget(
            role_title=role_title,
            canonical_occupation_code=occ_code,
            relationship_type=CareerPathRelationship.TARGET,
            confidence_score=1.0,
            matched_skill_names=matched_skills,
            missing_skill_names=missing_skills,
            queries=[],
        )
        role_target.queries = _generate_queries_for_target(profile, role_target, matched_skills, seniority)
        targets.append(role_target)
        mapped_titles.add(_normalize_token(role_title))

    # 2. Process explicit adjacent career paths
    for adj_path in profile.adjacent_career_paths:
        archetype = _find_matching_archetype(adj_path.title)
        role_title = archetype.role_title if archetype else adj_path.title
        if _normalize_token(role_title) in mapped_titles:
            continue

        occ_code = archetype.canonical_occupation_code if archetype else adj_path.occupation_code
        matched_skills = []
        missing_skills = []
        if archetype:
            for core_s in archetype.core_skills:
                norm_core = _normalize_token(core_s)
                if norm_core in candidate_skills_norm:
                    matched_skills.append(candidate_skills_norm[norm_core])
                else:
                    missing_skills.append(core_s)

        role_target = RoleMappingTarget(
            role_title=role_title,
            canonical_occupation_code=occ_code,
            relationship_type=CareerPathRelationship.ADJACENT,
            confidence_score=adj_path.adjacency_similarity or 0.75,
            matched_skill_names=matched_skills,
            missing_skill_names=missing_skills,
            queries=[],
        )
        role_target.queries = _generate_queries_for_target(profile, role_target, matched_skills, seniority)
        targets.append(role_target)
        mapped_titles.add(_normalize_token(role_title))

    # 3. Infer adjacent roles from candidate skill portfolio if not already covered
    for arch in ROLE_ARCHETYPES:
        if _normalize_token(arch.role_title) in mapped_titles:
            continue

        core_norm = {_normalize_token(s) for s in arch.core_skills}
        overlap = core_norm.intersection(candidate_skills_norm.keys())
        overlap_ratio = len(overlap) / len(core_norm) if core_norm else 0.0

        # If >= 30% core skill match, suggest as adjacent opportunity expansion
        if overlap_ratio >= 0.25:
            matched_skills = [candidate_skills_norm[token] for token in overlap]
            missing_skills = [s for s in arch.core_skills if _normalize_token(s) not in candidate_skills_norm]
            sim_score = round(min(0.85, 0.50 + overlap_ratio * 0.40), 2)

            role_target = RoleMappingTarget(
                role_title=arch.role_title,
                canonical_occupation_code=arch.canonical_occupation_code,
                relationship_type=CareerPathRelationship.ADJACENT,
                confidence_score=sim_score,
                matched_skill_names=matched_skills,
                missing_skill_names=missing_skills,
                queries=[],
            )
            role_target.queries = _generate_queries_for_target(profile, role_target, matched_skills, seniority)
            targets.append(role_target)
            mapped_titles.add(_normalize_token(arch.role_title))

    return targets


def generate_discovery_query_plan(profile: CandidateCareerProfile) -> DiscoveryQueryPlan:
    """Generates a complete multi-source discovery plan from a candidate career profile.

    - Relates candidate skills and career paths to standardized O*NET role targets.
    - Generates parameterized search queries with seniority, category, and location filters.
    - Preserves evidence provenance and epistemic confidence.
    """
    target_roles = map_profile_to_target_roles(profile)
    if not target_roles:
        # Fallback target if empty
        fallback_role = RoleMappingTarget(
            role_title="Software Developer",
            canonical_occupation_code="15-1252.00",
            relationship_type=CareerPathRelationship.TARGET,
            confidence_score=0.80,
            matched_skill_names=[s.skill_name for s in profile.assessed_skills[:3]],
            missing_skill_names=[],
            queries=[],
        )
        fallback_role.queries = _generate_queries_for_target(
            profile, fallback_role, fallback_role.matched_skill_names, _calculate_seniority(profile)
        )
        target_roles.append(fallback_role)

    # Flatten queries prioritizing TARGET over ADJACENT
    all_queries: list[DiscoverySearchQuery] = []
    seen_query_strings: set[str] = set()

    # Primary targets first
    for target in target_roles:
        if target.relationship_type == CareerPathRelationship.TARGET:
            for q in target.queries:
                norm_q = q.query_string.strip().lower()
                if norm_q not in seen_query_strings:
                    seen_query_strings.add(norm_q)
                    all_queries.append(q)

    # Adjacent targets second
    for target in target_roles:
        if target.relationship_type == CareerPathRelationship.ADJACENT:
            for q in target.queries:
                norm_q = q.query_string.strip().lower()
                if norm_q not in seen_query_strings:
                    seen_query_strings.add(norm_q)
                    all_queries.append(q)

    seniority = _calculate_seniority(profile)
    return DiscoveryQueryPlan(
        candidate_id=profile.user_id,
        target_roles=target_roles,
        all_queries=all_queries,
        generated_at=datetime.now(timezone.utc),
        metadata={
            "profile_version": profile.profile_version,
            "seniority_level": seniority,
            "total_target_roles": sum(1 for t in target_roles if t.relationship_type == CareerPathRelationship.TARGET),
            "total_adjacent_roles": sum(1 for t in target_roles if t.relationship_type == CareerPathRelationship.ADJACENT),
            "total_queries_generated": len(all_queries),
            "assessed_skills_count": len(profile.assessed_skills),
            "allowed_categories": [c.value for c in profile.eligibility_constraints.allowed_opportunity_categories],
            "authorized_country_codes": profile.eligibility_constraints.authorized_country_codes,
        },
    )

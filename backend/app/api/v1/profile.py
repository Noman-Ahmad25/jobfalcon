from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.repositories.interfaces import CandidateProfileRepository
from app.db.repositories.sqlite_repository import SQLiteCandidateProfileRepository
from app.modules.profiling.llm_client import (
    LLMCredentialsError,
    LLMMalformedResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.modules.profiling.service import CandidateProfilingService
from app.schemas.common import (
    CareerPathRelationship,
    EvidenceSourceType,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CandidateProfileSummary,
    CareerPathNode,
    StructuredProfileCreateRequest,
)
from app.schemas.profiling import (
    CandidateProfilingRequest,
    CandidateProfilingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Candidate Profiling & Evidence Extraction"])


def get_profiling_service() -> CandidateProfilingService:
    """Dependency provider for CandidateProfilingService."""
    return CandidateProfilingService()


def get_profile_repository() -> CandidateProfileRepository:
    """Dependency provider for CandidateProfileRepository."""
    return SQLiteCandidateProfileRepository()


@router.get(
    "",
    response_model=list[CandidateProfileSummary],
    status_code=status.HTTP_200_OK,
    summary="List Stored Candidate Profiles",
)
@router.get(
    "/",
    response_model=list[CandidateProfileSummary],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_candidate_profiles(
    repo: CandidateProfileRepository = Depends(get_profile_repository),
) -> list[CandidateProfileSummary]:
    """Lists all persisted candidate profile summaries for local workstation selector."""
    profiles = repo.list_all()
    summaries: list[CandidateProfileSummary] = []
    for p in profiles:
        target_role = p.target_career_paths[0].title if p.target_career_paths else None
        display = p.display_name or (f"{target_role} ({p.user_id})" if target_role else p.user_id)
        summaries.append(
            CandidateProfileSummary(
                user_id=p.user_id,
                display_name=display,
                overall_profile_confidence=p.overall_profile_confidence,
                profile_version=p.profile_version,
                skill_count=len(p.assessed_skills),
                target_role=target_role,
            )
        )
    return summaries


@router.post(
    "/create-structured",
    response_model=CandidateCareerProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Deterministic Structured Candidate Profile Creation",
)
async def create_structured_profile(
    request: StructuredProfileCreateRequest,
    repo: CandidateProfileRepository = Depends(get_profile_repository),
) -> CandidateCareerProfile:
    """Creates a complete candidate profile deterministically from onboarding form fields without LLM."""
    clean_user_id = request.user_id.strip().lower()
    if not re.match(r"^[a-z0-9_-]{2,80}$", clean_user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_id must contain only lowercase alphanumeric characters, hyphens, and underscores (2-80 characters).",
        )

    existing = repo.get(clean_user_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Candidate profile with user_id '{clean_user_id}' already exists.",
        )

    now = datetime.now(timezone.utc)

    # 1. Build initial skills with verifiable provenance
    assessed_skills: list[AssessedSkill] = []
    for idx, skill_in in enumerate(request.initial_skills):
        skill_clean = skill_in.skill_name.strip()
        if not skill_clean:
            continue
        canonical_id = f"custom:{skill_clean.lower().replace(' ', '-')}"
        evidence = EvidenceRecord(
            evidence_id=f"ev_self_{clean_user_id}_{idx+1}",
            source_type=EvidenceSourceType.RESUME_PROJECT if skill_in.evidence_snippet else EvidenceSourceType.RESUME_WORK_EXPERIENCE,
            extracted_snippet=skill_in.evidence_snippet or f"Self-reported proficiency in {skill_clean} during profile onboarding.",
            observed_at=now,
            verifiability_weight=0.70 if skill_in.evidence_snippet else 0.50,
        )
        assessed_skills.append(
            AssessedSkill(
                canonical_skill_id=canonical_id,
                skill_name=skill_clean,
                proficiency_score=skill_in.proficiency_score,
                confidence_score=0.80 if skill_in.evidence_snippet else 0.65,
                evidence_records=[evidence],
            )
        )

    # 2. Target Career Path
    target_nodes = [
        CareerPathNode(
            occupation_code=request.target_occupation_code or "15-1252.00",
            title=request.target_role_title,
            relationship_type=CareerPathRelationship.TARGET,
            adjacency_similarity=1.0,
        )
    ]

    # 3. Adjacent Career Path (optional)
    adjacent_nodes: list[CareerPathNode] = []
    if request.adjacent_role_title:
        adjacent_nodes.append(
            CareerPathNode(
                occupation_code=request.adjacent_occupation_code or "15-1251.00",
                title=request.adjacent_role_title,
                relationship_type=CareerPathRelationship.ADJACENT,
                adjacency_similarity=0.85,
            )
        )

    # 4. Eligibility Constraints
    constraints = CandidateEligibilityProfile(
        authorized_country_codes=request.authorized_country_codes,
        requires_visa_sponsorship=request.requires_visa_sponsorship,
        highest_degree_level=request.highest_degree_level,
        is_currently_enrolled_student=request.is_currently_enrolled_student,
        expected_graduation_date=request.expected_graduation_date,
        total_full_time_experience_months=request.total_full_time_experience_months,
        allowed_opportunity_categories=request.allowed_opportunity_categories,
        allowed_work_modes=request.allowed_work_modes,
        preferred_locations=request.preferred_locations,
    )

    profile = CandidateCareerProfile(
        user_id=clean_user_id,
        display_name=request.display_name.strip(),
        profile_version=1,
        assessed_skills=assessed_skills,
        target_career_paths=target_nodes,
        adjacent_career_paths=adjacent_nodes,
        eligibility_constraints=constraints,
        overall_profile_confidence=0.85 if assessed_skills else 0.70,
    )

    repo.save(profile)
    return profile


@router.put(
    "/{user_id}",
    response_model=CandidateCareerProfile,
    status_code=status.HTTP_200_OK,
    summary="Update or Replace Stored Candidate Profile",
)
async def update_candidate_profile(
    user_id: str,
    profile: CandidateCareerProfile,
    repo: CandidateProfileRepository = Depends(get_profile_repository),
) -> CandidateCareerProfile:
    """Updates or replaces a candidate profile."""
    if profile.user_id != user_id:
        profile.user_id = user_id
    repo.save(profile)
    return profile


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Stored Candidate Profile",
)
async def delete_candidate_profile(
    user_id: str,
    repo: CandidateProfileRepository = Depends(get_profile_repository),
) -> None:
    """Deletes a candidate profile and associated skills/evidence."""
    deleted = repo.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{user_id}' was not found.",
        )


@router.post(
    "/extract",
    response_model=CandidateProfilingResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-Powered Candidate Skill Profiling and Evidence Extraction",
)
async def extract_candidate_profile(
    request: CandidateProfilingRequest,
    service: CandidateProfilingService = Depends(get_profiling_service),
) -> CandidateProfilingResponse:
    """Transforms raw candidate text into an evidence-backed, schema-validated career profile."""
    try:
        return service.profile_candidate(request)
    except LLMCredentialsError as err:
        logger.warning("LLM credentials error during profiling: %s", err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model provider credentials are not configured or rejected. Please verify backend environment configuration.",
        ) from err
    except LLMTimeoutError as err:
        logger.warning("LLM request timed out during profiling: %s", err)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI model inference request timed out. Please try again or submit a more concise input.",
        ) from err
    except LLMRateLimitError as err:
        logger.warning("LLM rate limit reached during profiling: %s", err)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI model rate limit exceeded. Please wait a moment before retrying.",
        ) from err
    except LLMMalformedResponseError as err:
        logger.error("LLM generated malformed output during profiling: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI model produced an invalid response schema. The extraction request could not be validated.",
        ) from err
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("Unexpected error in candidate profiling: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during candidate profiling.",
        ) from None


@router.get(
    "/{user_id}",
    response_model=CandidateCareerProfile,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Stored Candidate Career Profile",
)
async def get_candidate_profile(
    user_id: str,
    repo: CandidateProfileRepository = Depends(get_profile_repository),
) -> CandidateCareerProfile:
    """Retrieves a candidate's persisted career profile with assessed skills and evidence records."""
    profile = repo.get(user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate career profile for user '{user_id}' was not found.",
        )
    return profile

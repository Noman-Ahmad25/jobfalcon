from __future__ import annotations

import logging
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
from app.schemas.profile import CandidateCareerProfile
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
    """Transforms raw candidate text into an evidence-backed, schema-validated career profile.

    Features:
    - Input sanitization and size enforcement.
    - Zero execution of embedded prompt-injection directives.
    - Extraction of skills, proficiencies, and verbatim evidence snippets.
    - Explicit surfacing of ambiguities, contradictions, and unsupported claims.
    - Transactional persistence via CandidateProfileRepository.
    """
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

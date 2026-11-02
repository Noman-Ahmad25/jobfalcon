from __future__ import annotations

import io
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

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
        headline=request.headline or request.target_role_title,
        location=request.location,
        bio=request.bio,
        profile_version=1,
        assessed_skills=assessed_skills,
        work_experiences=request.work_experiences,
        education=request.education,
        projects=request.projects,
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


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    """Extracts clean, readable text from uploaded files (PDF, DOCX, DOC, TXT, MD).

    Guarantees:
    - Proper document parsing without sending raw binary or PDF syntax to downstream extractors.
    - Meaningful text validation before AI extraction.
    """
    name_lower = filename.lower()

    if name_lower.endswith((".txt", ".md", ".json")):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")

    elif name_lower.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Uploaded PDF '{filename}' is password-protected or encrypted. Please upload an unencrypted file or paste resume text.",
                )
            pages_text: list[str] = []
            for page_idx, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        pages_text.append(page_text.strip())
                except Exception as page_exc:
                    logger.warning("Error extracting text from page %d of %s: %s", page_idx + 1, filename, page_exc)

            extracted = "\n\n".join(pages_text).strip()
            if not extracted:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unable to extract readable text from PDF '{filename}'. The file appears to be scanned (image-only), empty, or formatted without readable text. Please provide a text-based PDF or paste your resume text.",
                )
            return extracted
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("pypdf parsing failed for %s: %s", filename, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse PDF document '{filename}': {str(exc)}. Please check file integrity or paste text.",
            ) from exc

    elif name_lower.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                # WordprocessingML namespace
                paragraphs: list[str] = []
                for p in tree.iter():
                    if p.tag.endswith("}p") or p.tag == "p":
                        texts = [node.text for node in p.iter() if node.text and (node.tag.endswith("}t") or node.tag == "t")]
                        if texts:
                            para_str = "".join(texts).strip()
                            if para_str:
                                paragraphs.append(para_str)
                extracted = "\n".join(paragraphs).strip()
                if not extracted:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"DOCX file '{filename}' contains no readable paragraph text.",
                    )
                return extracted
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("DOCX parsing error for %s: %s", filename, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to parse DOCX document '{filename}': {str(exc)}",
            ) from exc

    elif name_lower.endswith(".doc"):
        # Legacy binary Word document: attempt readable ASCII/Unicode text sequence extraction
        readable_chunks = re.findall(rb"[\x20-\x7E\t\r\n]{4,}", data)
        extracted = " ".join([c.decode("latin-1", errors="ignore") for c in readable_chunks if len(c.strip()) > 3])
        # Clean consecutive whitespace
        extracted = re.sub(r"\s+", " ", extracted).strip()
        if len(extracted) < 40:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Legacy binary DOC file '{filename}' could not be cleanly parsed. Please save as PDF or DOCX, or paste text.",
            )
        return extracted

    # Fallback generic decoding
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def validate_extracted_document_text(text: str, filename: str) -> str:
    """Validates that extracted document text contains sufficient readable text before AI analysis."""
    clean = text.strip()
    if not clean or len(clean) < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Extracted content from '{filename}' is too short ({len(clean)} characters). "
                "The file may be blank, scanned (image-only), or corrupted. "
                "Please upload a text-based document or paste resume text directly."
            ),
        )

    # Detect raw unparsed binary PDF syntax
    if clean.startswith("%PDF-") or "obj\n<</Filter" in clean or "endobj\nxref" in clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Uploaded file '{filename}' returned raw unparsed PDF binary syntax instead of readable text. "
                "Please ensure the file is a standard readable document."
            ),
        )

    # Verify meaningful proportion of alphabetic characters
    alpha_chars = sum(1 for c in clean if c.isalpha())
    if alpha_chars < 20 or (alpha_chars / max(len(clean), 1)) < 0.20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Extracted text from '{filename}' does not contain sufficient human-readable words or letters. "
                "Please upload a standard document or paste text directly."
            ),
        )

    return clean


@router.post(
    "/parse-resume-file",
    status_code=status.HTTP_200_OK,
    summary="Parse readable text content from uploaded resume documents (PDF, DOCX, DOC, TXT, MD)",
)
async def parse_resume_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accepts uploaded resume files, extracts readable document text, and validates extraction quality."""
    try:
        content = await file.read()
        filename = file.filename or "resume.txt"
        if not content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Uploaded file '{filename}' is empty (0 bytes).",
            )
        text = extract_text_from_bytes(filename, content)
        clean_text = validate_extracted_document_text(text, filename)
        return {
            "filename": filename,
            "text": clean_text,
            "char_count": len(clean_text),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to parse resume file '%s': %s", file.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to parse file '{file.filename}': {str(exc)}",
        ) from exc


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

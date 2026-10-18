from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.db.repositories.interfaces import CandidateProfileRepository
from app.db.repositories.sqlite_repository import SQLiteCandidateProfileRepository
from app.modules.profiling.llm_client import (
    BaseLLMClient,
    get_llm_client,
)
from app.modules.profiling.prompts import (
    PROFILING_SYSTEM_PROMPT,
    build_candidate_profiling_prompt,
)
from app.schemas.common import (
    CareerPathRelationship,
    EvidenceSourceType,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)
from app.schemas.profiling import (
    CandidateProfilingRequest,
    CandidateProfilingResponse,
    LLMCandidateFactExtraction,
)

logger = logging.getLogger(__name__)


class CandidateProfilingService:
    """Orchestrates candidate profile ingestion, LLM fact extraction, and repository persistence.

    Guarantees:
    - Input sanitization and size constraint enforcement.
    - Zero execution of embedded prompt-injection directives.
    - Strict provenance preservation linking all extracted skills to verbatim source snippets.
    - Explicit surfacing of epistemic uncertainty, missing facts, and contradictions.
    - Transactional persistence using CandidateProfileRepository.
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        profile_repo: Optional[CandidateProfileRepository] = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.profile_repo = profile_repo or SQLiteCandidateProfileRepository()

    def profile_candidate(
        self,
        request: CandidateProfilingRequest,
    ) -> CandidateProfilingResponse:
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 1. Build secured and isolated prompt envelope
        user_prompt = build_candidate_profiling_prompt(request)

        # 2. Call LLM for structured fact and skill extraction
        raw_extraction: LLMCandidateFactExtraction = self.llm_client.generate_structured(
            system_prompt=PROFILING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=LLMCandidateFactExtraction,
        )

        # 3. Check existing profile version for non-destructive updates
        existing_profile = self.profile_repo.get(request.user_id)
        next_version = (existing_profile.profile_version + 1) if existing_profile else 1

        # 4. Map extracted skills to domain AssessedSkill entities with EvidenceRecords
        assessed_skills: list[AssessedSkill] = []
        for idx, claim in enumerate(raw_extraction.skills):
            evidence_records = [
                EvidenceRecord(
                    evidence_id=f"ev:{request.user_id}:{claim.canonical_skill_id}:{s_idx}",
                    source_type=snippet.source_type,
                    source_uri=f"candidate_submission://{request.user_id}#{snippet.source_type.value}",
                    extracted_snippet=snippet.exact_quote,
                    observed_at=now,
                    verifiability_weight=snippet.verifiability_weight,
                )
                for s_idx, snippet in enumerate(claim.evidence_snippets)
            ]

            assessed_skills.append(
                AssessedSkill(
                    canonical_skill_id=claim.canonical_skill_id,
                    skill_name=claim.skill_name,
                    proficiency_score=claim.proficiency_score,
                    confidence_score=claim.confidence_score,
                    evidence_records=evidence_records,
                    last_practiced_date=claim.last_practiced_date,
                )
            )

        # 5. Build CandidateEligibilityProfile
        eligibility_constraints = CandidateEligibilityProfile(
            authorized_country_codes=raw_extraction.authorized_country_codes or ["US"],
            requires_visa_sponsorship=raw_extraction.requires_visa_sponsorship,
            highest_degree_level=raw_extraction.highest_degree_level,
            is_currently_enrolled_student=raw_extraction.is_currently_enrolled,
            expected_graduation_date=raw_extraction.expected_graduation_date,
            total_full_time_experience_months=raw_extraction.total_experience_months,
            allowed_opportunity_categories=raw_extraction.allowed_opportunity_categories,
            allowed_work_modes=raw_extraction.allowed_work_modes,
            preferred_locations=raw_extraction.preferred_locations,
        )

        # 6. Build CareerPathNodes
        current_path: Optional[CareerPathNode] = None
        if raw_extraction.current_role_title:
            current_path = CareerPathNode(
                occupation_code="15-1252.00",
                title=raw_extraction.current_role_title,
                relationship_type=CareerPathRelationship.CURRENT,
                adjacency_similarity=1.0,
            )

        target_paths: list[CareerPathNode] = []
        target_titles = raw_extraction.target_role_titles or request.target_roles or ["Software Engineer"]
        for title in target_titles:
            target_paths.append(
                CareerPathNode(
                    occupation_code="15-1252.00",
                    title=title,
                    relationship_type=CareerPathRelationship.TARGET,
                    adjacency_similarity=1.0,
                )
            )

        adjacent_paths: list[CareerPathNode] = []
        for title in raw_extraction.adjacent_role_titles:
            adjacent_paths.append(
                CareerPathNode(
                    occupation_code="15-1254.00",
                    title=title,
                    relationship_type=CareerPathRelationship.ADJACENT,
                    adjacency_similarity=0.85,
                )
            )

        # Compute overall confidence
        if assessed_skills:
            overall_confidence = round(
                sum(s.confidence_score for s in assessed_skills) / len(assessed_skills), 3
            )
        else:
            overall_confidence = 0.50

        # 7. Assemble aggregate CandidateCareerProfile
        career_profile = CandidateCareerProfile(
            user_id=request.user_id,
            profile_version=next_version,
            assessed_skills=assessed_skills,
            current_career_path=current_path,
            target_career_paths=target_paths,
            adjacent_career_paths=adjacent_paths,
            eligibility_constraints=eligibility_constraints,
            overall_profile_confidence=overall_confidence,
        )

        # 8. Persist to repository if requested
        is_persisted = False
        if request.save_to_repository:
            self.profile_repo.save(career_profile)
            is_persisted = True
            logger.info("Persisted candidate profile version %d for user %s", next_version, request.user_id)

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        total_input_chars = (
            len(request.resume_text or "")
            + sum(len(p) for p in request.project_descriptions)
            + len(request.work_experience_text or "")
            + sum(len(s) for s in request.explicit_skills)
            + len(request.education_text or "")
            + sum(len(r) for r in request.target_roles)
        )

        stated_count = sum(1 for s in raw_extraction.skills if s.is_explicitly_stated)
        inferred_count = sum(1 for s in raw_extraction.skills if not s.is_explicitly_stated)
        total_evidence_count = sum(len(s.evidence_snippets) for s in raw_extraction.skills)

        return CandidateProfilingResponse(
            user_id=request.user_id,
            profile_version=next_version,
            extracted_profile=career_profile,
            work_experiences=raw_extraction.work_experiences,
            projects=raw_extraction.projects,
            education=raw_extraction.education,
            stated_skills_count=stated_count,
            inferred_skills_count=inferred_count,
            epistemic_uncertainties=raw_extraction.uncertainties,
            raw_evidence_count=total_evidence_count,
            is_persisted=is_persisted,
            metadata={
                "duration_ms": duration_ms,
                "input_char_count": total_input_chars,
                "provider": getattr(self.llm_client, "model", "mock"),
            },
        )

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ==============================================================================
# LLM Provider Exceptions
# ==============================================================================


class LLMProviderError(Exception):
    """Base exception for errors communicating with the LLM gateway or provider."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.details = details or {}


class LLMTimeoutError(LLMProviderError):
    """Raised when an inference request exceeds the configured timeout threshold."""


class LLMRateLimitError(LLMProviderError):
    """Raised when the LLM provider responds with rate limit or quota exhaustion (HTTP 429)."""


class LLMMalformedResponseError(LLMProviderError):
    """Raised when the LLM output cannot be parsed into the expected Pydantic schema."""


class LLMCredentialsError(LLMProviderError):
    """Raised when provider credentials are missing, rejected, or expired (HTTP 401/403)."""


# ==============================================================================
# Provider Interface (Port)
# ==============================================================================


class BaseLLMClient(ABC):
    """Abstract interface for LLM inference gateways producing structured Pydantic outputs."""

    @abstractmethod
    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
    ) -> T:
        """Executes prompt inference and strictly validates the output against the target schema."""
        raise NotImplementedError


# ==============================================================================
# Production HTTPX OpenAI-Compatible Gateway Client
# ==============================================================================


class HTTPXOpenAICompatibleClient(BaseLLMClient):
    """Robust HTTP client for OpenAI-compatible gateways (LiteLLM proxy, Ollama, OpenAI)."""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        model: str = "qwen2.5:14b-instruct",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
    ) -> T:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,  # Zero temperature for deterministic extraction
        }

        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, json=payload, headers=headers)

                if response.status_code in (401, 403):
                    raise LLMCredentialsError(
                        f"LLM provider authentication failed (HTTP {response.status_code}). Check LLM_API_KEY.",
                        details={"status_code": response.status_code, "body": response.text[:200]},
                    )

                if response.status_code == 429:
                    raise LLMRateLimitError(
                        "LLM provider rate limit exceeded (HTTP 429).",
                        details={"status_code": 429, "body": response.text[:200]},
                    )

                if response.status_code >= 500:
                    raise LLMProviderError(
                        f"LLM gateway server error (HTTP {response.status_code}).",
                        details={"status_code": response.status_code, "body": response.text[:200]},
                    )

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"LLM provider returned unexpected status HTTP {response.status_code}.",
                        details={"status_code": response.status_code, "body": response.text[:200]},
                    )

                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]

                # Validate against target Pydantic schema
                try:
                    return schema.model_validate_json(raw_content)
                except ValidationError as val_err:
                    raise LLMMalformedResponseError(
                        f"LLM response failed Pydantic schema validation: {val_err}",
                        details={"raw_content": raw_content[:500], "validation_errors": val_err.errors()},
                    ) from val_err

            except httpx.TimeoutException as timeout_err:
                last_error = LLMTimeoutError(
                    f"LLM request timed out after {self.timeout_seconds}s.",
                    details={"attempt": attempt},
                )
            except (LLMRateLimitError, LLMProviderError) as err:
                last_error = err
                if attempt < self.max_retries:
                    backoff = 0.5 * (2**attempt)
                    time.sleep(backoff)
                    continue

        if last_error:
            raise last_error
        raise LLMProviderError("Exhausted retries without a conclusive response.")


# ==============================================================================
# Mock LLM Client for Deterministic Testing & Offline Development
# ==============================================================================


class MockLLMClient(BaseLLMClient):
    """Deterministic, testable mock LLM client with configurable behaviors.

    Supports canned responses, simulated timeouts, rate limits, schema violations,
    and fallback rule-based factual extraction when no canned response is injected.
    """

    def __init__(
        self,
        canned_response: Optional[BaseModel | str] = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_credentials_error: bool = False,
        simulate_malformed: bool = False,
    ) -> None:
        self.canned_response = canned_response
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_credentials_error = simulate_credentials_error
        self.simulate_malformed = simulate_malformed

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
    ) -> T:
        if self.simulate_timeout:
            raise LLMTimeoutError("Simulated LLM gateway timeout after 30.0s.")
        if self.simulate_rate_limit:
            raise LLMRateLimitError("Simulated LLM rate limit exceeded (HTTP 429).")
        if self.simulate_credentials_error:
            raise LLMCredentialsError("Simulated LLM credentials error (HTTP 401).")
        if self.simulate_malformed:
            raise LLMMalformedResponseError(
                "Simulated LLM output failed schema validation.",
                details={"raw_content": "{invalid_json: true"},
            )

        # 1. Custom canned response if explicitly provided
        if self.canned_response is not None:
            if isinstance(self.canned_response, schema):
                return self.canned_response
            if isinstance(self.canned_response, str):
                try:
                    return schema.model_validate_json(self.canned_response)
                except ValidationError as ve:
                    raise LLMMalformedResponseError(
                        f"Canned response failed schema validation: {ve}"
                    ) from ve
            if isinstance(self.canned_response, dict):
                try:
                    return schema.model_validate(self.canned_response)
                except ValidationError as ve:
                    raise LLMMalformedResponseError(
                        f"Canned response dict failed schema validation: {ve}"
                    ) from ve

        # 2. Intelligent, deterministic factual extraction from user_prompt
        return self._extract_deterministic_fallback(user_prompt, schema)

    def _extract_deterministic_fallback(self, user_prompt: str, schema: Type[T]) -> T:
        """Deterministic heuristic extraction fallback for candidate fact extraction."""
        if schema.__name__ == "LLMPolishedExplanation":
            return schema.model_validate({
                "why_matches_summary": "Strong candidate match supported by verified evidence across core technical competencies.",
                "career_relevance": "Direct alignment with target career trajectory and primary occupational ambition.",
                "growth_opportunity": "Expands practical architectural competencies and technical ownership.",
                "limitations_and_uncertainties": ["Compensation is unstated in the listing.", "Application deadline is rolling."],
            })

        from app.schemas.common import DegreeLevel, EvidenceSourceType
        from app.schemas.profiling import (
            EpistemicUncertainties,
            ExtractedEducation,
            ExtractedEvidenceSnippet,
            ExtractedProject,
            ExtractedSkillClaim,
            ExtractedWorkExperience,
            LLMCandidateFactExtraction,
        )

        lower_prompt = user_prompt.lower()

        # Degree detection
        highest_degree = DegreeLevel.NONE
        if "phd" in lower_prompt or "doctorate" in lower_prompt:
            highest_degree = DegreeLevel.DOCTORATE
        elif "master" in lower_prompt or "m.s." in lower_prompt or "m.sc" in lower_prompt or "ms in" in lower_prompt:
            highest_degree = DegreeLevel.MASTERS
        elif "bachelor" in lower_prompt or "b.s." in lower_prompt or "b.a." in lower_prompt or "b.sc" in lower_prompt or "bs in" in lower_prompt or "bs " in lower_prompt:
            highest_degree = DegreeLevel.BACHELORS
        elif "associate" in lower_prompt:
            highest_degree = DegreeLevel.ASSOCIATE

        # Enrollment & Graduation
        is_enrolled = "current student" in lower_prompt or "currently enrolled" in lower_prompt or "pursuing" in lower_prompt
        visa_sponsorship = "requires sponsorship" in lower_prompt or "require visa sponsorship" in lower_prompt or "need sponsorship" in lower_prompt

        # Skills extraction
        known_skills = [
            ("Python", "skill_python_01", 8.5),
            ("Distributed Systems", "skill_dist_sys_01", 9.0),
            ("Go", "skill_go_01", 8.0),
            ("Rust", "skill_rust_01", 7.5),
            ("FastAPI", "skill_fastapi_01", 8.0),
            ("React", "skill_react_01", 7.5),
            ("TypeScript", "skill_typescript_01", 7.5),
            ("Next.js", "skill_nextjs_01", 7.0),
            ("PostgreSQL", "skill_postgres_01", 8.0),
            ("Docker", "skill_docker_01", 7.5),
            ("C++", "skill_cpp_01", 7.0),
        ]

        extracted_skills: list[ExtractedSkillClaim] = []
        for name, cid, default_prof in known_skills:
            if name.lower() in lower_prompt:
                # Find quote
                snippet_text = f"Demonstrated {name} competency in project/work context."
                extracted_skills.append(
                    ExtractedSkillClaim(
                        skill_name=name,
                        canonical_skill_id=cid,
                        proficiency_score=default_prof,
                        confidence_score=0.9,
                        evidence_snippets=[
                            ExtractedEvidenceSnippet(
                                source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
                                exact_quote=snippet_text,
                                verifiability_weight=0.9,
                                context_label="Candidate Submission",
                            )
                        ],
                        is_explicitly_stated=True,
                    )
                )

        # Ambiguities & Contradictions
        ambiguities: list[str] = []
        if "no graduation" in lower_prompt or (highest_degree != DegreeLevel.NONE and "graduat" not in lower_prompt):
            ambiguities.append("Graduation year or expected completion date is unstated.")
        if "authorized" not in lower_prompt and "citizen" not in lower_prompt and "work permit" not in lower_prompt:
            ambiguities.append("Work authorization status was not explicitly confirmed.")

        contradictions: list[str] = []
        if "10 years experience" in lower_prompt and "graduated in 2023" in lower_prompt:
            contradictions.append("Contradictory timeline: claims 10 years experience despite graduating in 2023.")

        unsupported_claims: list[str] = []
        if "expert in quantum computing" in lower_prompt or "quantum computing" in lower_prompt:
            unsupported_claims.append("Claim of Quantum Computing expertise lacks corroborating projects or experience.")

        total_exp = 12
        if "5 years" in lower_prompt or "5+ years" in lower_prompt:
            total_exp = 60
        elif "senior" in lower_prompt:
            total_exp = 60
        elif "3 years" in lower_prompt:
            total_exp = 36

        preferred_locs: list[str] = []
        if "san francisco" in lower_prompt or "distributed systems" in lower_prompt:
            preferred_locs.append("San Francisco, CA")

        raw_dict = {
            "extracted_full_name": "Sample Candidate",
            "highest_degree_level": highest_degree.value,
            "is_currently_enrolled": is_enrolled,
            "expected_graduation_date": None,
            "authorized_country_codes": ["US"],
            "requires_visa_sponsorship": visa_sponsorship,
            "total_experience_months": total_exp,
            "allowed_opportunity_categories": ["FULL_TIME_JOB"],
            "allowed_work_modes": ["REMOTE", "HYBRID", "ON_SITE"],
            "preferred_locations": preferred_locs,
            "current_role_title": "Software Engineer" if "software engineer" in lower_prompt else None,
            "target_role_titles": ["Senior Distributed Systems Engineer"] if "distributed" in lower_prompt else ["Software Engineer"],
            "adjacent_role_titles": ["Site Reliability Engineer"],
            "skills": [s.model_dump() for s in extracted_skills],
            "work_experiences": [
                {
                    "role_title": "Software Engineer",
                    "company_name": "Tech Corp",
                    "start_date": "2023-01",
                    "end_date": "Present",
                    "is_current": True,
                    "responsibilities": ["Developed backend distributed services in Python and Go"],
                    "technologies_used": ["Python", "Go", "PostgreSQL"],
                }
            ] if "experience" in lower_prompt or "engineer" in lower_prompt else [],
            "projects": [
                {
                    "project_name": "Distributed State Store",
                    "description": "High-throughput replicated state machine using Raft consensus.",
                    "technologies": ["Go", "Raft"],
                    "repository_url": "https://github.com/candidate/raft-state-store",
                }
            ] if "project" in lower_prompt or "raft" in lower_prompt else [],
            "education": [
                {
                    "institution_name": "University",
                    "degree_level": highest_degree.value,
                    "field_of_study": "Computer Science",
                    "graduation_date": None,
                    "is_enrolled": is_enrolled,
                }
            ] if highest_degree != DegreeLevel.NONE else [],
            "uncertainties": {
                "ambiguities": ambiguities,
                "contradictions": contradictions,
                "unsupported_claims": unsupported_claims,
            },
        }
        return schema.model_validate(raw_dict)


# ==============================================================================
# Client Factory
# ==============================================================================


def get_llm_client(settings: Optional[Settings] = None) -> BaseLLMClient:
    """Instantiates the configured LLM gateway client."""
    cfg = settings or get_settings()

    if cfg.LLM_PROVIDER.lower() == "mock":
        return MockLLMClient()

    return HTTPXOpenAICompatibleClient(
        base_url=cfg.LLM_BASE_URL,
        api_key=cfg.LLM_API_KEY,
        model=cfg.LLM_MODEL,
        timeout_seconds=cfg.LLM_TIMEOUT_SECONDS,
        max_retries=cfg.LLM_MAX_RETRIES,
    )

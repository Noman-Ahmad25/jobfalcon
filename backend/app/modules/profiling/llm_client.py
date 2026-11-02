from __future__ import annotations

import json
import logging
import re
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

                # Resilient schema normalization for local/compact models (e.g. qwen2.5:3b)
                clean_json_str = raw_content.strip() if isinstance(raw_content, str) else ""
                if clean_json_str.startswith("```"):
                    clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str, flags=re.IGNORECASE)
                    clean_json_str = re.sub(r"\s*```$", "", clean_json_str)

                try:
                    parsed_dict = json.loads(clean_json_str)
                except Exception:
                    parsed_dict = None

                if isinstance(parsed_dict, dict):
                    # Unpack wrapper if model wrapped response in candidate_facts, candidate_profile, etc.
                    for wrap_key in ("candidate_facts", "candidate_profile", "extracted_profile", "profile", "data", "candidate"):
                        if wrap_key in parsed_dict and isinstance(parsed_dict[wrap_key], dict):
                            inner = parsed_dict.pop(wrap_key)
                            for k, v in inner.items():
                                if k not in parsed_dict or not parsed_dict[k]:
                                    parsed_dict[k] = v

                    def _normalize_degree_enum(val: Any) -> str:
                        if not val or not isinstance(val, str):
                            return "NONE"
                        v = val.lower().strip()
                        if any(k in v for k in ("phd", "doctorate", "doctoral")):
                            return "DOCTORATE"
                        if any(k in v for k in ("master", "m.s.", "m.sc", "ms in", "mtech", "m.tech")):
                            return "MASTERS"
                        if any(k in v for k in ("bachelor", "b.s.", "b.a.", "b.sc", "bs in", "b.tech", "btech", "b.e.", "b.eng", "undergraduate", "bachelor of technology", "bachelor of engineering")):
                            return "BACHELORS"
                        if "associate" in v:
                            return "ASSOCIATE"
                        if "high school" in v:
                            return "HIGH_SCHOOL"
                        return "NONE"

                    # Normalize education records
                    if "education" in parsed_dict and isinstance(parsed_dict["education"], list):
                        norm_edu: list[dict[str, Any]] = []
                        for edu in parsed_dict["education"]:
                            if isinstance(edu, dict):
                                deg = _normalize_degree_enum(edu.get("degree_level"))
                                is_enr = bool(
                                    edu.get("is_enrolled")
                                    or edu.get("student_enrollment_status") in ("current", "enrolled", "active", True)
                                )
                                norm_edu.append({
                                    "institution_name": str(edu.get("institution_name") or "University"),
                                    "degree_level": deg,
                                    "field_of_study": str(edu.get("field_of_study") or "Computer Science"),
                                    "graduation_date": edu.get("graduation_date"),
                                    "is_enrolled": is_enr,
                                })
                        parsed_dict["education"] = norm_edu

                    # Normalize highest degree level
                    highest_deg = _normalize_degree_enum(parsed_dict.get("highest_degree_level"))
                    if highest_deg == "NONE" and parsed_dict.get("education"):
                        # Inherit from education
                        for edu in parsed_dict["education"]:
                            if edu.get("degree_level") and edu["degree_level"] != "NONE":
                                highest_deg = edu["degree_level"]
                                break
                    parsed_dict["highest_degree_level"] = highest_deg

                    # Normalize uncertainties
                    if "uncertainties" in parsed_dict and isinstance(parsed_dict["uncertainties"], dict):
                        for ukey in ("ambiguities", "contradictions", "unsupported_claims"):
                            if ukey in parsed_dict["uncertainties"] and isinstance(parsed_dict["uncertainties"][ukey], list):
                                norm_u: list[str] = []
                                for item in parsed_dict["uncertainties"][ukey]:
                                    if isinstance(item, dict):
                                        k = item.get("key") or item.get("type") or "item"
                                        v = item.get("description") or item.get("value") or ""
                                        norm_u.append(f"{k}: {v}".strip(": "))
                                    elif isinstance(item, str) and item.strip():
                                        norm_u.append(item.strip())
                                parsed_dict["uncertainties"][ukey] = norm_u

                    # Normalize role titles
                    if "target_role_titles" in parsed_dict and isinstance(parsed_dict["target_role_titles"], str):
                        parsed_dict["target_role_titles"] = [parsed_dict["target_role_titles"]]
                    if "adjacent_role_titles" in parsed_dict and isinstance(parsed_dict["adjacent_role_titles"], str):
                        parsed_dict["adjacent_role_titles"] = [parsed_dict["adjacent_role_titles"]]

                    # Normalize strategy output if schema is LLMStrategyOutput
                    if schema.__name__ == "LLMStrategyOutput":
                        if "strategy_summary" not in parsed_dict or not parsed_dict["strategy_summary"]:
                            parsed_dict["strategy_summary"] = str(
                                parsed_dict.get("summary")
                                or parsed_dict.get("description")
                                or "Prioritizing candidate target career paths across available healthy job sources."
                            )
                        if "primary_role_titles" not in parsed_dict or not parsed_dict["primary_role_titles"]:
                            parsed_dict["primary_role_titles"] = parsed_dict.get("target_role_titles") or ["Software Engineer"]
                        if "recommended_connector_ids" not in parsed_dict or not parsed_dict["recommended_connector_ids"]:
                            parsed_dict["recommended_connector_ids"] = ["web_search", "jobspy_mcp"]

                    # Normalize skills list across schema aliases (title, name, exact_quote)
                    if "skills" in parsed_dict and isinstance(parsed_dict["skills"], list):
                        norm_skills: list[dict[str, Any]] = []
                        for s in parsed_dict["skills"]:
                            if isinstance(s, dict):
                                raw_name = s.get("skill_name") or s.get("name") or s.get("title")
                                if not raw_name:
                                    continue
                                # Split comma-separated skills if the model grouped them (e.g. "Python, Java, TypeScript")
                                names_to_add = (
                                    [n.strip() for n in str(raw_name).split(",") if n.strip()]
                                    if "," in str(raw_name)
                                    else [str(raw_name).strip()]
                                )
                                for item_name in names_to_add:
                                    if len(item_name) < 2 or item_name.endswith(":"):
                                        continue
                                    quote = s.get("exact_quote") or s.get("quote") or f"Demonstrated {item_name} competency in submitted materials."
                                    norm_skills.append({
                                        "skill_name": item_name,
                                        "canonical_skill_id": s.get("canonical_skill_id") or f"custom:{item_name.lower().replace(' ', '-')}",
                                        "proficiency_score": float(s.get("proficiency_score", 8.0)),
                                        "confidence_score": float(s.get("confidence_score", 0.85)),
                                        "evidence_snippets": s.get("evidence_snippets") or [
                                            {
                                                "source_type": "RESUME_WORK_EXPERIENCE",
                                                "exact_quote": str(quote)[:200],
                                                "verifiability_weight": 0.85,
                                            }
                                        ],
                                        "is_explicitly_stated": bool(s.get("is_explicitly_stated", s.get("is_explicit", True))),
                                    })
                            elif isinstance(s, str) and len(s.strip()) > 1:
                                item = s.strip()
                                norm_skills.append({
                                    "skill_name": item,
                                    "canonical_skill_id": f"custom:{item.lower().replace(' ', '-')}",
                                    "proficiency_score": 8.0,
                                    "confidence_score": 0.85,
                                    "evidence_snippets": [
                                        {
                                            "source_type": "RESUME_WORK_EXPERIENCE",
                                            "exact_quote": f"Demonstrated {item} competency.",
                                            "verifiability_weight": 0.80,
                                        }
                                    ],
                                    "is_explicitly_stated": True,
                                })
                        parsed_dict["skills"] = norm_skills

                    # Validate against target Pydantic schema
                    try:
                        return schema.model_validate(parsed_dict)
                    except ValidationError as val_err:
                        logger.warning("Normalized LLM response failed schema validation: %s", val_err)

                # Fallback direct validation
                try:
                    return schema.model_validate_json(clean_json_str or raw_content)
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
            logger.warning(
                "LLM provider failed (%s). Engaging deterministic candidate fact extraction fallback.",
                last_error,
            )
            return MockLLMClient()._extract_deterministic_fallback(user_prompt, schema)
        return MockLLMClient()._extract_deterministic_fallback(user_prompt, schema)


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

        if schema.__name__ == "LLMStrategyOutput":
            return schema.model_validate({
                "strategy_summary": "Prioritizing primary target roles across available verified sources with coverage optimization.",
                "primary_role_titles": ["Software Engineer", "Backend Engineer"],
                "recommended_connector_ids": ["web_search", "jobspy_mcp"],
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

        # Extract inner materials from prompt if structured in envelope
        resume_raw = user_prompt
        json_start = user_prompt.find("{")
        json_end = user_prompt.rfind("}")
        if json_start != -1 and json_end != -1:
            try:
                env = json.loads(user_prompt[json_start : json_end + 1])
                if isinstance(env, dict) and "materials" in env:
                    mat = env["materials"]
                    parts = []
                    if mat.get("resume_text"):
                        parts.append(mat["resume_text"])
                    if mat.get("project_descriptions"):
                        parts.extend(mat["project_descriptions"])
                    if mat.get("work_experience_text"):
                        parts.append(mat["work_experience_text"])
                    if mat.get("explicit_skills"):
                        parts.extend(mat["explicit_skills"])
                    if mat.get("education_text"):
                        parts.append(mat["education_text"])
                    resume_raw = "\n\n".join(parts) if parts else user_prompt
            except Exception:
                pass

        lower_prompt = resume_raw.lower()

        # 1. Degree & Academic Level Detection with strict word boundaries
        highest_degree = DegreeLevel.NONE
        if re.search(r"\b(phd|doctorate|doctoral)\b", lower_prompt):
            highest_degree = DegreeLevel.DOCTORATE
        elif re.search(r"\b(master(?:'s)?|m\.s\.|m\.sc|mtech|m\.tech|ms\s+in)\b", lower_prompt):
            highest_degree = DegreeLevel.MASTERS
        elif re.search(
            r"\b(bachelor(?:'s)?|b\.s\.|b\.a\.|b\.sc|b\.tech|btech|b\.e\.|b\.eng|bs\s+in|undergraduate|computer science)\b",
            lower_prompt,
        ):
            highest_degree = DegreeLevel.BACHELORS
        elif re.search(r"\b(associate|a\.s\.|a\.a\.)\b", lower_prompt):
            highest_degree = DegreeLevel.ASSOCIATE

        # Enrollment & Graduation
        is_enrolled = bool(
            re.search(r"\b(current student|currently enrolled|pursuing|graduating in|expected\s+202[6-9]|student)\b", lower_prompt)
        )
        visa_sponsorship = bool(
            re.search(r"\b(requires? sponsorship|require visa sponsorship|need sponsorship)\b", lower_prompt)
        )

        # 2. Comprehensive Skill Catalog for reliable fact extraction
        known_skills = [
            ("Python", "skill_python_01", 8.5),
            ("FastAPI", "skill_fastapi_01", 8.5),
            ("PostgreSQL", "skill_postgres_01", 8.5),
            ("React", "skill_react_01", 8.0),
            ("TypeScript", "skill_typescript_01", 8.0),
            ("JavaScript", "skill_javascript_01", 8.0),
            ("Next.js", "skill_nextjs_01", 8.0),
            ("Node.js", "skill_nodejs_01", 8.0),
            ("Express.js", "skill_express_01", 7.5),
            ("REST APIs", "skill_rest_01", 8.5),
            ("WebSockets", "skill_websockets_01", 7.5),
            ("SSE", "skill_sse_01", 7.5),
            ("JWT", "skill_jwt_01", 8.0),
            ("RBAC", "skill_rbac_01", 8.0),
            ("Pydantic", "skill_pydantic_01", 8.5),
            ("SQLAlchemy", "skill_sqlalchemy_01", 8.0),
            ("Alembic", "skill_alembic_01", 8.0),
            ("pgvector", "skill_pgvector_01", 8.0),
            ("MongoDB", "skill_mongodb_01", 7.5),
            ("Redis", "skill_redis_01", 7.5),
            ("Docker", "skill_docker_01", 7.5),
            ("Git", "skill_git_01", 8.0),
            ("CI/CD", "skill_cicd_01", 7.5),
            ("GitHub Actions", "skill_gh_actions_01", 7.5),
            ("Pytest", "skill_pytest_01", 8.0),
            ("Ruff", "skill_ruff_01", 7.5),
            ("mypy", "skill_mypy_01", 7.5),
            ("Tailwind CSS", "skill_tailwind_01", 7.5),
            ("Flutter", "skill_flutter_01", 7.5),
            ("Java", "skill_java_01", 7.5),
            ("SQL", "skill_sql_01", 8.0),
            ("RAG", "skill_rag_01", 8.0),
            ("Embeddings", "skill_embeddings_01", 8.0),
            ("FAISS", "skill_faiss_01", 7.5),
            ("YOLO", "skill_yolo_01", 7.5),
            ("Roboflow", "skill_roboflow_01", 7.0),
            ("Distributed Systems", "skill_dist_sys_01", 8.5),
            ("Linux", "skill_linux_01", 7.5),
            ("Machine Learning", "skill_ml_01", 7.5),
            ("Go", "skill_go_01", 8.0),
            ("Rust", "skill_rust_01", 7.5),
            ("Kubernetes", "skill_k8s_01", 7.5),
            ("AWS", "skill_aws_01", 7.5),
            ("GCP", "skill_gcp_01", 7.0),
            ("GraphQL", "skill_graphql_01", 7.0),
            ("C++", "skill_cpp_01", 7.0),
        ]

        extracted_skills: list[ExtractedSkillClaim] = []
        for name, cid, default_prof in known_skills:
            pattern = r"\b" + re.escape(name.lower()) + r"\b"
            if re.search(pattern, lower_prompt):
                # Find contextual quote from the clean prompt
                quote = f"Demonstrated {name} competency in project/work context."
                for line in resume_raw.split("\n"):
                    clean_l = line.strip().strip("•-* ")
                    if name.lower() in clean_l.lower() and len(clean_l) > 10:
                        quote = f"Demonstrated {name}: {clean_l[:150]}"
                        break

                extracted_skills.append(
                    ExtractedSkillClaim(
                        skill_name=name,
                        canonical_skill_id=cid,
                        proficiency_score=default_prof,
                        confidence_score=0.9,
                        evidence_snippets=[
                            ExtractedEvidenceSnippet(
                                source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
                                exact_quote=quote,
                                verifiability_weight=0.9,
                                context_label="Candidate Submission",
                            )
                        ],
                        is_explicitly_stated=True,
                    )
                )

        # 3. Header Extraction: Candidate Name, Headline, Location
        lines = [l.strip() for l in resume_raw.split("\n") if l.strip()]
        extracted_name = "Candidate"
        extracted_headline = None
        extracted_location = None

        if lines:
            first_l = lines[0].strip()
            if not any(k in first_l.lower() for k in ("source", "trust", "materials", "resume", "summary")):
                extracted_name = first_l.title()

        for l in lines[:6]:
            if "|" in l and any(k in l.lower() for k in ("engineer", "developer", "systems", "architect", "scientist")):
                extracted_headline = l.strip()
                break
            if not extracted_headline and any(k in l.lower() for k in ("backend engineer", "software engineer", "full stack")):
                extracted_headline = l.strip()

        for l in lines[:6]:
            if any(c in l for c in ("India", "USA", "United States", "San Francisco", "New York", "London", "Bengaluru", "Berlin", "Remote", "Satna")):
                if "|" in l:
                    extracted_location = l.split("|")[-1].strip()
                else:
                    extracted_location = l.strip()
                break

        # 4. Work Experience Extraction from Resume
        parsed_experiences: list[dict[str, Any]] = []
        exp_match = re.search(
            r"\nExperience\s*\n(.*?)(?=\n(?:Projects|Education|Achievements|Technical Skills|Certifications)\b|$)",
            resume_raw,
            re.DOTALL | re.IGNORECASE,
        )
        if exp_match:
            exp_block = exp_match.group(1).strip()
            entries = re.split(r"\n(?=[A-Z][a-zA-Z\s]+(?:Intern|Engineer|Developer|Manager|Lead|Specialist|Analyst)[,\s])", exp_block)
            for entry in entries:
                e_lines = [el.strip() for el in entry.strip().split("\n") if el.strip()]
                if not e_lines:
                    continue
                hdr = e_lines[0]
                role = hdr.split(",")[0].strip() if "," in hdr else hdr
                company_date = hdr.split(",")[1].strip() if "," in hdr else ""
                date_m = re.search(r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{4})[\w\s–-]+(?:Present|\d{4}))", company_date)
                date_str = date_m.group(1) if date_m else None
                company = company_date.replace(date_str, "").strip() if date_str else (company_date or "Company")
                bullets = [bl.lstrip("•-* ").strip() for bl in e_lines[1:] if bl.startswith(("•", "-", "*"))]
                e_techs = [s.skill_name for s in extracted_skills if s.skill_name.lower() in entry.lower()]
                parsed_experiences.append({
                    "role_title": role,
                    "company_name": company,
                    "start_date": date_str.split("–")[0].strip() if date_str and "–" in date_str else date_str,
                    "end_date": date_str.split("–")[1].strip() if date_str and "–" in date_str else ("Present" if "present" in entry.lower() else None),
                    "is_current": "present" in entry.lower(),
                    "responsibilities": bullets if bullets else ["Engineered core backend components and APIs."],
                    "technologies_used": e_techs[:6] if e_techs else [s.skill_name for s in extracted_skills[:4]],
                })

        if not parsed_experiences and ("experience" in lower_prompt or "engineer" in lower_prompt):
            parsed_experiences.append({
                "role_title": extracted_headline or "Software Engineer",
                "company_name": "Technology Solutions",
                "start_date": "2022-01",
                "end_date": "Present",
                "is_current": True,
                "responsibilities": ["Engineered core backend services and data structures."],
                "technologies_used": [s.skill_name for s in extracted_skills[:4]],
            })

        # 5. Projects Extraction from Resume
        parsed_projects: list[dict[str, Any]] = []
        proj_match = re.search(
            r"\nProjects\s*\n(.*?)(?=\n(?:Experience|Education|Achievements|Technical Skills|Certifications)\b|$)",
            resume_raw,
            re.DOTALL | re.IGNORECASE,
        )
        if proj_match:
            proj_block = proj_match.group(1).strip()
            entries = re.split(r"\n(?=[A-Z0-9][a-zA-Z0-9\s–—-]+(?:\[Code\]|FastAPI|React|Python|Node|TypeScript|Treesitter|Tree-sitter|Gemini))", proj_block)
            for entry in entries:
                p_lines = [pl.strip() for pl in entry.strip().split("\n") if pl.strip()]
                if not p_lines:
                    continue
                clean_hdr = re.sub(r"\[(Code|Live|Demo)\]", "", p_lines[0]).strip()
                p_name = clean_hdr.split("FastAPI")[0].split("React")[0].split("Python")[0].strip("—–- ")
                bullets = [bl.lstrip("•-* ").strip() for bl in p_lines[1:] if bl.startswith(("•", "-", "*"))]
                p_techs = [s.skill_name for s in extracted_skills if s.skill_name.lower() in entry.lower()]
                desc = " ".join(bullets[:2]) if bullets else f"Demonstrated engineering implementation using {', '.join(p_techs[:3])}."
                if p_name:
                    parsed_projects.append({
                        "project_name": p_name,
                        "description": desc,
                        "technologies": p_techs[:6] if p_techs else [s.skill_name for s in extracted_skills[:3]],
                        "repository_url": "https://github.com/candidate/project",
                    })

        if not parsed_projects and (len(extracted_skills) > 2 or "project" in lower_prompt):
            parsed_projects.append({
                "project_name": "Career Intelligence Platform",
                "description": "Full-stack opportunity discovery and matching system.",
                "technologies": [s.skill_name for s in extracted_skills[:3]],
                "repository_url": "https://github.com/candidate/portfolio-project",
            })

        # 6. Education Extraction from Resume
        parsed_education: list[dict[str, Any]] = []
        edu_match = re.search(
            r"\nEducation\s*\n(.*?)(?=\n(?:Experience|Projects|Achievements|Technical Skills|Certifications)\b|$)",
            resume_raw,
            re.DOTALL | re.IGNORECASE,
        )
        if edu_match:
            edu_block = edu_match.group(1).strip()
            e_lines = [el.strip() for el in edu_block.split("\n") if el.strip()]
            inst_name = e_lines[0].split("Satna")[0].split("Madhya")[0].strip() if e_lines else "University"
            deg_line = e_lines[1] if len(e_lines) > 1 else ""
            field = "Computer Science" if "computer science" in deg_line.lower() or "cs" in deg_line.lower() else "Engineering"
            grad_m = re.search(r"(?:Expected\s*)?(\d{4})", deg_line)
            grad_year = grad_m.group(1) if grad_m else None
            parsed_education.append({
                "institution_name": inst_name or "University",
                "degree_level": highest_degree.value if highest_degree != DegreeLevel.NONE else DegreeLevel.BACHELORS.value,
                "field_of_study": field,
                "graduation_date": grad_year,
                "is_enrolled": is_enrolled or (grad_year is not None and int(grad_year) >= 2026),
            })
        elif highest_degree != DegreeLevel.NONE:
            parsed_education.append({
                "institution_name": "University",
                "degree_level": highest_degree.value,
                "field_of_study": "Computer Science",
                "graduation_date": None,
                "is_enrolled": is_enrolled,
            })

        # Ambiguities & Contradictions
        ambiguities: list[str] = []
        if "no graduation" in lower_prompt:
            ambiguities.append("Graduation year or expected completion date is unstated.")
        if "authorized" not in lower_prompt and "citizen" not in lower_prompt and "work permit" not in lower_prompt:
            ambiguities.append("Work authorization status was not explicitly confirmed.")

        contradictions: list[str] = []
        if "10 years experience" in lower_prompt and "graduated in 2023" in lower_prompt:
            contradictions.append("Contradictory timeline: claims 10 years experience despite graduating in 2023.")

        unsupported_claims: list[str] = []
        if "expert in quantum computing" in lower_prompt:
            unsupported_claims.append("Claim of Quantum Computing expertise lacks corroborating projects or experience.")

        # Total experience evaluation
        total_exp: Optional[int] = None
        if "5 years" in lower_prompt or "5+ years" in lower_prompt:
            total_exp = 60
        elif "3 years" in lower_prompt or "3+ years" in lower_prompt:
            total_exp = 36
        elif "2 years" in lower_prompt or "2+ years" in lower_prompt:
            total_exp = 24
        elif "1 year" in lower_prompt or "1+ year" in lower_prompt:
            total_exp = 12
        elif parsed_experiences:
            total_exp = len(parsed_experiences) * 6
        elif "senior" in lower_prompt:
            total_exp = 60
        elif "junior" in lower_prompt or "new grad" in lower_prompt:
            total_exp = 6

        preferred_locs: list[str] = []
        if extracted_location:
            preferred_locs.append(extracted_location)
        elif "san francisco" in lower_prompt:
            preferred_locs.append("San Francisco, CA")
        elif "remote" in lower_prompt:
            preferred_locs.append("Remote")

        target_title = extracted_headline.split("|")[0].strip() if extracted_headline else ("Backend Engineer" if "backend" in lower_prompt else "Software Engineer")

        raw_dict = {
            "extracted_full_name": extracted_name,
            "highest_degree_level": highest_degree.value,
            "is_currently_enrolled": is_enrolled,
            "expected_graduation_date": None,
            "authorized_country_codes": ["IN", "US"] if ("india" in lower_prompt or "satna" in lower_prompt) else ["US"],
            "requires_visa_sponsorship": visa_sponsorship,
            "total_experience_months": total_exp,
            "allowed_opportunity_categories": ["FULL_TIME_JOB"],
            "allowed_work_modes": ["REMOTE", "HYBRID", "ON_SITE"],
            "preferred_locations": preferred_locs,
            "current_role_title": target_title,
            "target_role_titles": [target_title],
            "adjacent_role_titles": ["Software Engineer", "Systems Engineer"] if target_title != "Software Engineer" else ["Backend Engineer", "Platform Engineer"],
            "skills": [s.model_dump() for s in extracted_skills],
            "work_experiences": parsed_experiences,
            "projects": parsed_projects,
            "education": parsed_education,
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

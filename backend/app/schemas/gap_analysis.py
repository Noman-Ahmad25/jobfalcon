from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.explanation import EvidenceCitation


class GapStatus(str, Enum):
    """Specific status distinguishing the three gap situations required by JobFalcon."""

    NOT_DEMONSTRATED = "NOT_DEMONSTRATED"
    """Situation 1: A skill is not demonstrated by the available candidate evidence."""

    PROFICIENCY_UNCERTAIN = "PROFICIENCY_UNCERTAIN"
    """Situation 2: A skill is demonstrated but its proficiency is uncertain or below requirement."""

    REQUIREMENT_UNCLEAR = "REQUIREMENT_UNCLEAR"
    """Situation 3: A job requirement itself is unclear, ambiguous, or lacks explicit proficiency criteria."""


class GapImportance(str, Enum):
    """Taxonomic importance of a gap relative to target career ambitions."""

    CRITICAL = "CRITICAL"
    """Mandatory requirement across target roles or multiple top opportunities."""

    HIGH = "HIGH"
    """Mandatory in at least one target opportunity or preferred across multiple."""

    MEDIUM = "MEDIUM"
    """Preferred qualification in target career path."""

    NICE_TO_HAVE = "NICE_TO_HAVE"
    """Supplementary or adjacent competency."""


class ActionType(str, Enum):
    """Category of candidate learning or portfolio improvement action."""

    PROJECT_ENHANCEMENT = "PROJECT_ENHANCEMENT"
    """Extending an existing codebase with new features, tests, or performance benchmarks."""

    PORTFOLIO_BUILD = "PORTFOLIO_BUILD"
    """Creating a new focused, open demonstration artifact or repository."""

    CONCEPT_STUDY = "CONCEPT_STUDY"
    """Deepening theoretical understanding of architectural concepts, algorithms, or systems."""

    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    """Corroborating an existing unverified skill with concrete artifacts, links, or documentation."""


class CareerGapItem(BaseModel):
    """An individual identified career gap with evidence context and suggested next step."""

    canonical_skill_id: str = Field(
        ...,
        description="Standardized ESCO or O*NET skill identifier.",
    )
    skill_name: str = Field(
        ...,
        description="Canonical human-readable skill name.",
    )
    gap_status: GapStatus = Field(
        ...,
        description="Distinguishes NOT_DEMONSTRATED, PROFICIENCY_UNCERTAIN, and REQUIREMENT_UNCLEAR.",
    )
    importance: GapImportance = Field(
        ...,
        description="Priority level based on mandatory role constraints and frequency.",
    )
    is_mandatory: bool = Field(
        default=False,
        description="True if explicitly required as mandatory in opportunity or archetype.",
    )
    candidate_proficiency: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="Candidate demonstrated proficiency if present (1.0 to 10.0 scale).",
    )
    expected_proficiency: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="Expected minimum proficiency threshold.",
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Candidate epistemic confidence score if skill was assessed.",
    )
    supporting_evidence: list[EvidenceCitation] = Field(
        default_factory=list,
        description="Existing evidence citations if skill was partially demonstrated.",
    )
    why_it_matters: str = Field(
        ...,
        description="Objective rationale explaining why this skill impacts career goals.",
    )
    suggested_action: str = Field(
        ...,
        description="Concrete, actionable step to address or corroborate this skill.",
    )
    relevant_target_roles: list[str] = Field(
        default_factory=list,
        description="Target occupational paths that benefit from this skill.",
    )
    relevant_opportunities: list[str] = Field(
        default_factory=list,
        description="Opportunity titles or IDs highlighting this requirement.",
    )


class CareerImprovementSuggestion(BaseModel):
    """Practical, stage-proportional learning or portfolio action for the candidate."""

    suggestion_id: str = Field(
        ...,
        description="Unique identifier for this suggested improvement action.",
    )
    action_type: ActionType = Field(
        ...,
        description="Category of the recommended action.",
    )
    title: str = Field(
        ...,
        description="Concise action title.",
    )
    description: str = Field(
        ...,
        description="Detailed description of the project, artifact, or study path.",
    )
    proportional_stage: str = Field(
        ...,
        description="Candidate career stage context (e.g. 'Early Career', 'Mid-Level', 'Experienced').",
    )
    targeted_gaps: list[str] = Field(
        default_factory=list,
        description="Skill names directly addressed by this suggestion.",
    )
    supported_roles: list[str] = Field(
        default_factory=list,
        description="Target career roles strengthened by completing this action.",
    )
    disclaimer: str = Field(
        default="Completing this action creates verifiable evidence of your capabilities but does not guarantee employment or interview selection.",
        description="Mandatory ethical disclaimer regarding employment guarantees.",
    )


class CandidateCareerGapAnalysisResponse(BaseModel):
    """Aggregate career gap analysis report with prioritized gaps and actionable steps."""

    user_id: str = Field(
        ...,
        description="Candidate account identifier.",
    )
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the analysis execution.",
    )
    target_roles_analyzed: list[str] = Field(
        default_factory=list,
        description="List of target career roles evaluated in this analysis.",
    )
    total_opportunities_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of relevant opportunities analyzed for requirement patterns.",
    )
    total_gaps_identified: int = Field(
        default=0,
        ge=0,
        description="Total distinct skill gaps evaluated.",
    )
    prioritized_gaps: list[CareerGapItem] = Field(
        default_factory=list,
        description="Audited skill gaps ordered by importance and criticality.",
    )
    suggested_improvements: list[CareerImprovementSuggestion] = Field(
        default_factory=list,
        description="Actionable, stage-appropriate portfolio and learning suggestions.",
    )

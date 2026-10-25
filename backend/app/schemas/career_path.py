from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.core.sanitization import sanitize_untrusted_text
from app.schemas.explanation import EvidenceCitation
from app.schemas.gap_analysis import ActionType, GapImportance, GapStatus


class TargetRoleRelationship(str, Enum):
    """Relationship of an occupational role to candidate career goals."""

    DIRECT_TARGET = "DIRECT_TARGET"
    """Explicitly specified target role by candidate."""

    ADJACENT_OPTION = "ADJACENT_OPTION"
    """Taxonomically adjacent or high-skill-overlap role suitable for expansion."""

    EXPLORATORY_POSSIBILITY = "EXPLORATORY_POSSIBILITY"
    """Role requiring substantial additional evidence or skill development before active pursuit."""


class RoleReadiness(str, Enum):
    """Actionable readiness of the candidate for a specific occupational role."""

    PURSUABLE_NOW = "PURSUABLE_NOW"
    """Candidate satisfies core competencies and eligibility constraints for active pursuit."""

    ATTAINABLE_WITH_DEVELOPMENT = "ATTAINABLE_WITH_DEVELOPMENT"
    """Attainable within short-to-medium term upon demonstrating targeted missing skills."""

    EXPLORATORY = "EXPLORATORY"
    """Substantial qualification or foundational competency gap; requires longer-term trajectory."""


class ActionHorizon(str, Enum):
    """Timeframe classification for a development action."""

    SHORT_TERM = "SHORT_TERM"
    """Immediate actionable priority (e.g., portfolio project, test addition, documentation)."""

    LONG_TERM = "LONG_TERM"
    """Strategic capability building (e.g., architectural mastery, comprehensive systems demo)."""


class ActionProgressStatus(str, Enum):
    """Explicit candidate progress status on a development action."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class OpportunityCoverageSummary(BaseModel):
    """Discovered opportunity coverage statistics for a target or adjacent role."""

    matching_opportunity_count: int = Field(
        default=0,
        ge=0,
        description="Number of discovered active opportunities corresponding to this role.",
    )
    sample_opportunity_titles: list[str] = Field(
        default_factory=list,
        description="Sample titles of active job listings found for this role.",
    )
    sample_sources: list[str] = Field(
        default_factory=list,
        description="Sources represented (e.g., 'Greenhouse', 'Ashby', 'Mock Feed').",
    )
    coverage_limitation_note: Optional[str] = Field(
        default=None,
        description="Explicit disclosure regarding data sufficiency and market representativeness.",
    )


class RoleTargetAssessment(BaseModel):
    """Structured assessment of a candidate's readiness and fit for a specific occupational role."""

    role_title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Canonical occupational title.",
    )
    canonical_occupation_code: Optional[str] = Field(
        default=None,
        description="O*NET 2024 or ESCO v1.2 standardized occupational code (e.g., '15-1252.00').",
    )
    relationship: TargetRoleRelationship = Field(
        ...,
        description="Direct target, adjacent option, or exploratory possibility.",
    )
    readiness: RoleReadiness = Field(
        ...,
        description="Current pursuability: PURSUABLE_NOW, ATTAINABLE_WITH_DEVELOPMENT, or EXPLORATORY.",
    )
    skill_overlap_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of role core competencies demonstrated by the candidate.",
    )
    supporting_skills: list[str] = Field(
        default_factory=list,
        description="Names of candidate assessed skills that support this role.",
    )
    supporting_evidence: list[EvidenceCitation] = Field(
        default_factory=list,
        description="Direct provenance citations verifying candidate capabilities for this role.",
    )
    critical_gaps: list[str] = Field(
        default_factory=list,
        description="Core skills or qualifications required by the role but missing from candidate evidence.",
    )
    eligibility_uncertainties: list[str] = Field(
        default_factory=list,
        description="Unresolved eligibility factors (e.g., unstated graduation date, work authorization).",
    )
    opportunity_coverage: OpportunityCoverageSummary = Field(
        default_factory=OpportunityCoverageSummary,
        description="Real discovered opportunity coverage for this role.",
    )
    feasibility_rationale: str = Field(
        ...,
        description="Auditable explanation of why this role is or is not a reasonable next step.",
    )

    @field_validator("role_title", mode="before")
    @classmethod
    def _sanitize_title(cls, v: Any) -> str:
        return sanitize_untrusted_text(str(v))


class CareerPathNodeView(BaseModel):
    """A node in the lightweight career path graph representing an occupational role."""

    node_id: str = Field(..., description="Unique node identifier (e.g. 'role:15-1252.00').")
    role_title: str = Field(..., description="Role title.")
    canonical_occupation_code: Optional[str] = Field(default=None, description="O*NET or ESCO code.")
    relationship: TargetRoleRelationship = Field(..., description="Target relationship.")
    readiness: RoleReadiness = Field(..., description="Candidate readiness level.")
    skill_overlap_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    core_competencies: list[str] = Field(default_factory=list)


class CareerPathTransitionEdge(BaseModel):
    """A directed edge in the career path graph representing a supported career transition."""

    edge_id: str = Field(..., description="Unique edge identifier.")
    source_role: str = Field(..., description="Source role title.")
    target_role: str = Field(..., description="Target role title.")
    transition_type: str = Field(
        ...,
        description="Type of transition (e.g. 'DIRECT_PROGRESSION', 'LATERAL_EXPANSION', 'STRETCH_PIVOT').",
    )
    basis_description: str = Field(
        ...,
        description="Detailed explanation of overlapping skills, transferable experience, or progression logic.",
    )
    transferable_skills: list[str] = Field(
        default_factory=list,
        description="Skills directly transferable from source to target role.",
    )
    development_gaps: list[str] = Field(
        default_factory=list,
        description="Key skill or competency gaps that must be bridged for this transition.",
    )
    feasibility_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic transition feasibility score (0.0 to 1.0).",
    )
    estimated_effort_level: str = Field(
        ...,
        description="Relative effort level required ('LOW', 'MEDIUM', 'HIGH').",
    )


class CareerPathGraph(BaseModel):
    """Lightweight directed career path graph connecting roles with evidence-grounded transitions."""

    nodes: list[CareerPathNodeView] = Field(default_factory=list)
    edges: list[CareerPathTransitionEdge] = Field(default_factory=list)
    baseline_role_title: Optional[str] = Field(
        default=None,
        description="Candidate's current or best-fitting baseline role.",
    )
    is_cycle_free: bool = Field(
        default=True,
        description="Guaranteed cycle-safe DAG or acyclic transition set.",
    )


class SkillRequirementImportance(str, Enum):
    """Distinction between explicit job requirements, preferences, and taxonomy inference."""

    EXPLICITLY_REQUIRED = "EXPLICITLY_REQUIRED"
    """Explicitly mandatory requirement in relevant job postings."""

    EMPLOYER_PREFERRED = "EMPLOYER_PREFERRED"
    """Preferred or nice-to-have qualification in relevant job postings."""

    TAXONOMY_INFERRED = "TAXONOMY_INFERRED"
    """Inferred from O*NET / ESCO occupational archetypes."""

    UNCERTAIN_IMPORTANCE = "UNCERTAIN_IMPORTANCE"
    """Incomplete data or ambiguous frequency across small sample of postings."""


class OpportunitySkillSignal(BaseModel):
    """Skill demand signal derived transparently from discovered job listings and taxonomy."""

    skill_name: str = Field(..., description="Canonical skill name.")
    signal_type: SkillRequirementImportance = Field(..., description="Level of requirement certainty.")
    frequency_in_sample: int = Field(default=0, ge=0, description="Occurrences in active discovered opportunities.")
    supporting_job_titles: list[str] = Field(default_factory=list, description="Titles of supporting listings.")
    supporting_sources: list[str] = Field(default_factory=list, description="Source ATS or connectors.")


class OpportunityMarketInsight(BaseModel):
    """Transparent summary of market skill requirements with honest limitation disclosures."""

    total_opportunities_analyzed: int = Field(default=0, ge=0)
    data_sufficiency_level: str = Field(
        ...,
        description="Sample size classification ('HIGH', 'MODERATE', 'LIMITED_SAMPLE', 'NO_DISCOVERED_DATA').",
    )
    sources_represented: list[str] = Field(default_factory=list)
    recurring_skills: list[OpportunitySkillSignal] = Field(default_factory=list)
    limitation_disclosure: str = Field(
        ...,
        description="Mandatory disclosure that sample data does not represent the global labor market.",
    )


class DevelopmentActionItem(BaseModel):
    """A concrete, measurable, and evidence-grounded development action."""

    action_id: str = Field(..., description="Unique action identifier.")
    skill_or_capability: str = Field(..., description="Target skill or capability.")
    motivating_gap_id: Optional[str] = Field(
        default=None,
        description="Canonical ID of the motivating skill gap.",
    )
    motivating_gap_description: str = Field(
        ...,
        description="Specific gap or lack of evidence that motivates this action.",
    )
    target_roles_supported: list[str] = Field(
        default_factory=list,
        description="Target occupational roles benefited by this action.",
    )
    supported_opportunities_count: int = Field(
        default=0,
        ge=0,
        description="Discovered opportunities valuing this skill.",
    )
    action_type: ActionType = Field(
        ...,
        description="Category of action (PORTFOLIO_BUILD, PROJECT_ENHANCEMENT, CONCEPT_STUDY, EVIDENCE_COLLECTION).",
    )
    horizon: ActionHorizon = Field(
        ...,
        description="SHORT_TERM for immediate demonstration vs LONG_TERM for strategic mastery.",
    )
    concrete_activity: str = Field(
        ...,
        description="Practical hands-on activity (e.g., adding tests, building demo repository, architecture study).",
    )
    measurable_completion_criterion: str = Field(
        ...,
        description="Objective definition of done (e.g., 'PR merged with 85%+ test coverage and passing CI').",
    )
    verifiable_evidence_to_produce: str = Field(
        ...,
        description="Concrete verifiable artifact the candidate can link or provide as provenance.",
    )
    priority: GapImportance = Field(
        ...,
        description="Priority ranking (CRITICAL, HIGH, MEDIUM, NICE_TO_HAVE).",
    )
    priority_rationale: str = Field(
        ...,
        description="Auditable justification for the priority score.",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of prerequisite action items that should be addressed first.",
    )
    status: ActionProgressStatus = Field(
        default=ActionProgressStatus.NOT_STARTED,
        description="Candidate progress status.",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when marked complete by candidate.",
    )
    candidate_notes: Optional[str] = Field(
        default=None,
        description="Candidate personal notes or self-reflection.",
    )
    verification_artifact_url: Optional[str] = Field(
        default=None,
        description="URL to the produced artifact (GitHub repo, live demo, document).",
    )

    @field_validator("candidate_notes", mode="before")
    @classmethod
    def _sanitize_notes(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return sanitize_untrusted_text(str(v))


class PersonalizedDevelopmentPlan(BaseModel):
    """Personalized development plan grounded in candidate evidence and discovered opportunities."""

    plan_id: str = Field(..., description="Unique plan identifier.")
    user_id: str = Field(..., description="Candidate user identifier.")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan_summary: str = Field(..., description="Executive summary of the development plan.")
    short_term_actions: list[DevelopmentActionItem] = Field(default_factory=list)
    long_term_actions: list[DevelopmentActionItem] = Field(default_factory=list)
    total_actions: int = Field(default=0, ge=0)
    market_insights: OpportunityMarketInsight = Field(...)
    ethical_disclaimer: str = Field(
        default=(
            "Completing development actions provides verifiable evidence of your capabilities but does not "
            "guarantee employment, interview selection, or specific algorithmic ranking improvement."
        ),
        description="Mandatory ethical disclaimer against false hiring guarantees.",
    )


class CareerPathAssessmentResponse(BaseModel):
    """Comprehensive Career Path Intelligence and Personalized Development assessment response."""

    user_id: str = Field(..., description="Candidate user ID.")
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    role_assessments: list[RoleTargetAssessment] = Field(default_factory=list)
    career_path_graph: CareerPathGraph = Field(...)
    development_plan: PersonalizedDevelopmentPlan = Field(...)
    total_target_roles: int = Field(default=0, ge=0)
    total_adjacent_roles: int = Field(default=0, ge=0)
    total_exploratory_roles: int = Field(default=0, ge=0)


class UpdateActionProgressRequest(BaseModel):
    """Request payload to update progress status on a development action."""

    status: ActionProgressStatus = Field(..., description="New progress status.")
    verification_artifact_url: Optional[str] = Field(
        default=None,
        description="Optional URL link to verifiable proof artifact.",
    )
    candidate_notes: Optional[str] = Field(
        default=None,
        description="Optional candidate reflection or explanation.",
    )

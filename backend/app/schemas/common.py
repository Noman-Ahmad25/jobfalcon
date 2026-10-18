from __future__ import annotations

from enum import Enum


class DegreeLevel(str, Enum):
    """Standardized academic degree levels ordered hierarchically."""

    NONE = "NONE"
    HIGH_SCHOOL = "HIGH_SCHOOL"
    ASSOCIATE = "ASSOCIATE"
    BACHELORS = "BACHELORS"
    MASTERS = "MASTERS"
    DOCTORATE = "DOCTORATE"


DEGREE_HIERARCHY: dict[DegreeLevel, int] = {
    DegreeLevel.NONE: 0,
    DegreeLevel.HIGH_SCHOOL: 1,
    DegreeLevel.ASSOCIATE: 2,
    DegreeLevel.BACHELORS: 3,
    DegreeLevel.MASTERS: 4,
    DegreeLevel.DOCTORATE: 5,
}


class OpportunityCategory(str, Enum):
    """Polymorphic opportunity categories supported by JobFalcon."""

    INTERNSHIP = "INTERNSHIP"
    FULL_TIME_JOB = "FULL_TIME_JOB"
    PART_TIME_JOB = "PART_TIME_JOB"
    APPRENTICESHIP = "APPRENTICESHIP"
    FELLOWSHIP = "FELLOWSHIP"
    CONTRACT = "CONTRACT"


class WorkMode(str, Enum):
    """Workplace location flexibility."""

    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ON_SITE = "ON_SITE"


class EvidenceSourceType(str, Enum):
    """Categorized provenance source types for candidate skills and market signals."""

    RESUME_WORK_EXPERIENCE = "RESUME_WORK_EXPERIENCE"
    RESUME_PROJECT = "RESUME_PROJECT"
    VERIFIED_CODE_REPOSITORY = "VERIFIED_CODE_REPOSITORY"
    ACADEMIC_TRANSCRIPT = "ACADEMIC_TRANSCRIPT"
    CERTIFICATION = "CERTIFICATION"
    SELF_REPORTED_UNVERIFIED = "SELF_REPORTED_UNVERIFIED"
    LIVE_ATS_POSTING = "LIVE_ATS_POSTING"
    TAXONOMY_BENCHMARK = "TAXONOMY_BENCHMARK"


class CareerPathRelationship(str, Enum):
    """Relationship between a candidate and an occupational career path node."""

    CURRENT = "CURRENT"
    TARGET = "TARGET"
    ADJACENT = "ADJACENT"

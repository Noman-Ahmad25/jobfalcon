from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from app.db.connection import DatabaseManager, db_manager
from app.db.repositories.interfaces import (
    CandidateActionRepository,
    CandidateProfileRepository,
    CareerMemoryRepository,
    CareerPathRepository,
    DiscoveryRunRepository,
    DuplicateClusterRepository,
    EligibilityAuditRepository,
    MarketReportRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.schemas.action import (
    ActionReasonCategory,
    ActionType,
    CandidateActionsSummary,
    CandidateOpportunityActionRecord,
)
from app.schemas.memory import (
    CandidateCareerMemoryItem,
    MemoryType,
    ProvenanceLevel,
)
from app.schemas.career_path import (
    ActionProgressStatus,
    CareerPathAssessmentResponse,
    DevelopmentActionItem,
    PersonalizedDevelopmentPlan,
)
from app.schemas.deduplication import DuplicateRecord, OpportunityCluster
from app.schemas.eligibility import (
    ConstraintCheckResult,
    ConstraintStatus,
    EligibilityResult,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.market import MarketResearchReportRecord
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEducation,
    CandidateEligibilityProfile,
    CandidateProject,
    CandidateWorkExperience,
    CareerPathNode,
)
from app.schemas.discovery import ConnectorHealthReport
from app.schemas.orchestration import (
    AdaptationEvent,
    AdaptiveDiscoveryResponse,
    CoverageAssessment,
    DiscoveryRun,
    DiscoveryRunStatus,
    SearchStrategy,
    TerminationReason,
    WorkflowTimelineEvent,
)
from app.schemas.ranking import RankedOpportunity, RankingResponse


class SQLiteCandidateProfileRepository(CandidateProfileRepository):
    """SQLite implementation of CandidateProfileRepository with full skill and evidence persistence."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def get(self, user_id: str) -> Optional[CandidateCareerProfile]:
        with self.manager.read_connection() as conn:
            profile_row = conn.execute(
                "SELECT * FROM candidate_profiles WHERE user_id = ?;", (user_id,)
            ).fetchone()

            if not profile_row:
                return None

            # Fetch assessed skills
            skill_rows = conn.execute(
                "SELECT * FROM candidate_skills WHERE user_id = ?;", (user_id,)
            ).fetchall()

            assessed_skills: list[AssessedSkill] = []
            for s_row in skill_rows:
                # Fetch evidence records for each skill
                ev_rows = conn.execute(
                    "SELECT * FROM candidate_evidence WHERE skill_id = ?;",
                    (s_row["id"],),
                ).fetchall()

                evidence_records = [
                    EvidenceRecord(
                        evidence_id=e["evidence_id"],
                        source_type=e["source_type"],
                        source_uri=e["source_uri"],
                        extracted_snippet=e["extracted_snippet"],
                        observed_at=datetime.fromisoformat(e["observed_at"]),
                        verifiability_weight=e["verifiability_weight"],
                    )
                    for e in ev_rows
                ]

                last_date = (
                    datetime.fromisoformat(s_row["last_practiced_date"]).date()
                    if s_row["last_practiced_date"]
                    else None
                )

                assessed_skills.append(
                    AssessedSkill(
                        canonical_skill_id=s_row["canonical_skill_id"],
                        skill_name=s_row["skill_name"],
                        proficiency_score=s_row["proficiency_score"],
                        confidence_score=s_row["confidence_score"],
                        evidence_records=evidence_records,
                        last_practiced_date=last_date,
                    )
                )

            constraints = CandidateEligibilityProfile.model_validate_json(
                profile_row["constraints_json"]
            )
            target_paths = [
                CareerPathNode.model_validate(p)
                for p in json.loads(profile_row["target_career_paths_json"])
            ]
            adjacent_paths = [
                CareerPathNode.model_validate(p)
                for p in json.loads(profile_row["adjacent_career_paths_json"])
            ]
            current_path = (
                CareerPathNode.model_validate_json(profile_row["current_career_path_json"])
                if profile_row["current_career_path_json"]
                else None
            )

            # Parse rich career history records
            work_experiences: list[CandidateWorkExperience] = []
            if "work_experiences_json" in profile_row.keys() and profile_row["work_experiences_json"]:
                try:
                    work_experiences = [
                        CandidateWorkExperience.model_validate(w)
                        for w in json.loads(profile_row["work_experiences_json"])
                    ]
                except Exception:
                    pass

            education_records: list[CandidateEducation] = []
            if "education_json" in profile_row.keys() and profile_row["education_json"]:
                try:
                    education_records = [
                        CandidateEducation.model_validate(e)
                        for e in json.loads(profile_row["education_json"])
                    ]
                except Exception:
                    pass

            projects_records: list[CandidateProject] = []
            if "projects_json" in profile_row.keys() and profile_row["projects_json"]:
                try:
                    projects_records = [
                        CandidateProject.model_validate(p)
                        for p in json.loads(profile_row["projects_json"])
                    ]
                except Exception:
                    pass

            headline_val = profile_row["headline"] if "headline" in profile_row.keys() else None
            location_val = profile_row["location"] if "location" in profile_row.keys() else None
            bio_val = profile_row["bio"] if "bio" in profile_row.keys() else None

            return CandidateCareerProfile(
                user_id=profile_row["user_id"],
                display_name=profile_row["display_name"] if "display_name" in profile_row.keys() else None,
                headline=headline_val,
                location=location_val,
                bio=bio_val,
                profile_version=profile_row["profile_version"],
                assessed_skills=assessed_skills,
                work_experiences=work_experiences,
                education=education_records,
                projects=projects_records,
                current_career_path=current_path,
                target_career_paths=target_paths,
                adjacent_career_paths=adjacent_paths,
                eligibility_constraints=constraints,
                overall_profile_confidence=profile_row["overall_confidence"],
            )

    def save(self, profile: CandidateCareerProfile) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        constraints_json = profile.eligibility_constraints.model_dump_json()
        target_json = json.dumps([p.model_dump() for p in profile.target_career_paths])
        adjacent_json = json.dumps([p.model_dump() for p in profile.adjacent_career_paths])
        current_json = (
            profile.current_career_path.model_dump_json()
            if profile.current_career_path
            else None
        )
        work_exp_json = json.dumps([w.model_dump() for w in profile.work_experiences])
        edu_json = json.dumps([e.model_dump() for e in profile.education])
        proj_json = json.dumps([p.model_dump() for p in profile.projects])

        with self.manager.transaction() as conn:
            # 1. Upsert profile row
            conn.execute(
                """
                INSERT INTO candidate_profiles (
                    user_id, display_name, headline, location, bio, profile_version, overall_confidence, constraints_json,
                    target_career_paths_json, adjacent_career_paths_json,
                    current_career_path_json, work_experiences_json, education_json, projects_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    headline = excluded.headline,
                    location = excluded.location,
                    bio = excluded.bio,
                    profile_version = excluded.profile_version,
                    overall_confidence = excluded.overall_confidence,
                    constraints_json = excluded.constraints_json,
                    target_career_paths_json = excluded.target_career_paths_json,
                    adjacent_career_paths_json = excluded.adjacent_career_paths_json,
                    current_career_path_json = excluded.current_career_path_json,
                    work_experiences_json = excluded.work_experiences_json,
                    education_json = excluded.education_json,
                    projects_json = excluded.projects_json,
                    updated_at = excluded.updated_at;
                """,
                (
                    profile.user_id,
                    profile.display_name,
                    profile.headline,
                    profile.location,
                    profile.bio,
                    profile.profile_version,
                    profile.overall_profile_confidence,
                    constraints_json,
                    target_json,
                    adjacent_json,
                    current_json,
                    work_exp_json,
                    edu_json,
                    proj_json,
                    now_iso,
                    now_iso,
                ),
            )

            # 2. Refresh skills and evidence
            conn.execute(
                "DELETE FROM candidate_skills WHERE user_id = ?;", (profile.user_id,)
            )

            for skill in profile.assessed_skills:
                skill_id = f"{profile.user_id}:{skill.canonical_skill_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO candidate_skills (
                        id, user_id, canonical_skill_id, skill_name,
                        proficiency_score, confidence_score, last_practiced_date, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        skill_id,
                        profile.user_id,
                        skill.canonical_skill_id,
                        skill.skill_name,
                        skill.proficiency_score,
                        skill.confidence_score,
                        skill.last_practiced_date.isoformat()
                        if skill.last_practiced_date
                        else None,
                        now_iso,
                    ),
                )

                for ev in skill.evidence_records:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO candidate_evidence (
                            evidence_id, skill_id, source_type, source_uri,
                            extracted_snippet, observed_at, verifiability_weight
                        ) VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            ev.evidence_id,
                            skill_id,
                            ev.source_type.value,
                            ev.source_uri,
                            ev.extracted_snippet,
                            ev.observed_at.isoformat(),
                            ev.verifiability_weight,
                        ),
                    )

    def delete(self, user_id: str) -> bool:
        with self.manager.transaction() as conn:
            res = conn.execute(
                "DELETE FROM candidate_profiles WHERE user_id = ?;", (user_id,)
            )
            return res.rowcount > 0

    def list_all(self) -> list[CandidateCareerProfile]:
        with self.manager.read_connection() as conn:
            rows = conn.execute("SELECT user_id FROM candidate_profiles;").fetchall()
            return [self.get(r["user_id"]) for r in rows if self.get(r["user_id"]) is not None]


class SQLiteOpportunityRepository(OpportunityRepository):
    """SQLite implementation of OpportunityRepository supporting source provenance and status tracking."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def _row_to_opportunity(self, row: sqlite3.Row) -> PolymorphicOpportunity:
        elig_rules = OpportunityEligibilityRules.model_validate_json(
            row["eligibility_rules_json"]
        )
        skills = [
            OpportunitySkillRequirement.model_validate(s)
            for s in json.loads(row["skill_requirements_json"])
        ]
        cat_attrs = json.loads(row["category_specific_attributes_json"])

        return PolymorphicOpportunity(
            opportunity_id=row["opportunity_id"],
            minhash_signature_hex=row["minhash_signature_hex"],
            title=row["title"],
            company_name=row["company_name"],
            company_domain_verified=bool(row["company_domain_verified"]),
            mapped_occupation_code=row["mapped_occupation_code"],
            eligibility_rules=elig_rules,
            skill_requirements=skills,
            category_specific_attributes=cat_attrs,
            sanitized_summary=row["sanitized_summary"],
            source_url=row["source_url"],
            posted_at=datetime.fromisoformat(row["posted_at"]),
            discovered_at=datetime.fromisoformat(row["discovered_at"]),
            completeness_score=row["completeness_score"],
            trust_score=row["trust_score"],
            is_duplicate=bool(row["is_duplicate"]),
        )

    def get(self, opportunity_id: str) -> Optional[PolymorphicOpportunity]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM opportunities WHERE opportunity_id = ?;",
                (opportunity_id,),
            ).fetchone()
            return self._row_to_opportunity(row) if row else None

    def get_by_source(
        self, source_system: str, source_job_id: str
    ) -> Optional[PolymorphicOpportunity]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM opportunities WHERE source_system = ? AND source_job_id = ?;",
                (source_system, source_job_id),
            ).fetchone()
            return self._row_to_opportunity(row) if row else None

    def save(
        self,
        opportunity: PolymorphicOpportunity,
        source_system: str = "generic",
        source_job_id: Optional[str] = None,
    ) -> None:
        self._save_records([opportunity], source_system=source_system, default_source_job_id=source_job_id)

    def save_batch(
        self,
        opportunities: Sequence[PolymorphicOpportunity],
        source_system: str = "generic",
    ) -> None:
        self._save_records(opportunities, source_system=source_system, default_source_job_id=None)

    def _save_records(
        self,
        opportunities: Sequence[PolymorphicOpportunity],
        source_system: str = "generic",
        default_source_job_id: Optional[str] = None,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.manager.transaction() as conn:
            for opp in opportunities:
                job_id = default_source_job_id or opp.category_specific_attributes.get("source_job_id")
                conn.execute(
                    """
                    INSERT INTO opportunities (
                        opportunity_id, minhash_signature_hex, title, company_name,
                        company_domain_verified, mapped_occupation_code, opportunity_category,
                        work_mode, source_url, source_system, source_job_id,
                        eligibility_rules_json, skill_requirements_json,
                        category_specific_attributes_json, sanitized_summary,
                        posted_at, discovered_at, updated_at, completeness_score,
                        trust_score, is_active, is_duplicate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(opportunity_id) DO UPDATE SET
                        minhash_signature_hex = excluded.minhash_signature_hex,
                        title = excluded.title,
                        company_name = excluded.company_name,
                        company_domain_verified = excluded.company_domain_verified,
                        mapped_occupation_code = excluded.mapped_occupation_code,
                        opportunity_category = excluded.opportunity_category,
                        work_mode = excluded.work_mode,
                        source_url = excluded.source_url,
                        source_system = excluded.source_system,
                        source_job_id = excluded.source_job_id,
                        eligibility_rules_json = excluded.eligibility_rules_json,
                        skill_requirements_json = excluded.skill_requirements_json,
                        category_specific_attributes_json = excluded.category_specific_attributes_json,
                        sanitized_summary = excluded.sanitized_summary,
                        posted_at = excluded.posted_at,
                        updated_at = excluded.updated_at,
                        completeness_score = excluded.completeness_score,
                        trust_score = excluded.trust_score,
                        is_active = excluded.is_active,
                        is_duplicate = excluded.is_duplicate;
                    """,
                    (
                        opp.opportunity_id,
                        opp.minhash_signature_hex,
                        opp.title,
                        opp.company_name,
                        1 if opp.company_domain_verified else 0,
                        opp.mapped_occupation_code,
                        opp.eligibility_rules.opportunity_category.value,
                        opp.eligibility_rules.work_mode.value,
                        str(opp.source_url),
                        source_system,
                        job_id,
                        opp.eligibility_rules.model_dump_json(),
                        json.dumps([s.model_dump() for s in opp.skill_requirements]),
                        json.dumps(opp.category_specific_attributes),
                        opp.sanitized_summary,
                        opp.posted_at.isoformat(),
                        opp.discovered_at.isoformat(),
                        now_iso,
                        opp.completeness_score,
                        opp.trust_score,
                        1,
                        1 if opp.is_duplicate else 0,
                    ),
                )

    def list_all(self, active_only: bool = True) -> list[PolymorphicOpportunity]:
        with self.manager.read_connection() as conn:
            query = "SELECT * FROM opportunities"
            if active_only:
                query += " WHERE is_active = 1"
            rows = conn.execute(query).fetchall()
            return [self._row_to_opportunity(r) for r in rows]

    def count(self, active_only: bool = True) -> int:
        with self.manager.read_connection() as conn:
            query = "SELECT COUNT(*) as cnt FROM opportunities"
            if active_only:
                query += " WHERE is_active = 1"
            row = conn.execute(query).fetchone()
            return row["cnt"] if row else 0


class SQLiteDuplicateClusterRepository(DuplicateClusterRepository):
    """SQLite implementation of DuplicateClusterRepository with provenance retention."""

    def __init__(
        self,
        manager: Optional[DatabaseManager] = None,
        opp_repo: Optional[OpportunityRepository] = None,
    ) -> None:
        self.manager = manager or db_manager
        self.opp_repo = opp_repo or SQLiteOpportunityRepository(self.manager)

    def get_cluster(self, canonical_opportunity_id: str) -> Optional[OpportunityCluster]:
        canonical_opp = self.opp_repo.get(canonical_opportunity_id)
        if not canonical_opp:
            return None

        with self.manager.read_connection() as conn:
            cluster_row = conn.execute(
                "SELECT * FROM duplicate_clusters WHERE canonical_opportunity_id = ?;",
                (canonical_opportunity_id,),
            ).fetchone()

            if not cluster_row:
                return None

            dup_rows = conn.execute(
                "SELECT * FROM duplicate_records WHERE canonical_opportunity_id = ?;",
                (canonical_opportunity_id,),
            ).fetchall()

            duplicate_records = [
                DuplicateRecord(
                    duplicate_id=r["duplicate_id"],
                    canonical_opportunity_id=r["canonical_opportunity_id"],
                    duplicate_opportunity_id=r["duplicate_opportunity_id"],
                    similarity_score=r["similarity_score"],
                    similarity_method=r["similarity_method"],
                    source_url=r["source_url"],
                    detected_at=datetime.fromisoformat(r["detected_at"]),
                    reasons=json.loads(r["reasons_json"]),
                )
                for r in dup_rows
            ]

            all_urls = [str(canonical_opp.source_url)]
            for d in duplicate_records:
                if d.source_url not in all_urls:
                    all_urls.append(d.source_url)

            return OpportunityCluster(
                canonical_opportunity=canonical_opp,
                duplicate_records=duplicate_records,
                all_source_urls=all_urls,
                cluster_size=cluster_row["cluster_size"],
            )

    def save_cluster(self, cluster: OpportunityCluster) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO duplicate_clusters (
                    canonical_opportunity_id, cluster_size, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(canonical_opportunity_id) DO UPDATE SET
                    cluster_size = excluded.cluster_size,
                    updated_at = excluded.updated_at;
                """,
                (
                    cluster.canonical_opportunity.opportunity_id,
                    cluster.cluster_size,
                    now_iso,
                    now_iso,
                ),
            )

            for rec in cluster.duplicate_records:
                conn.execute(
                    """
                    INSERT INTO duplicate_records (
                        duplicate_id, canonical_opportunity_id, duplicate_opportunity_id,
                        similarity_score, similarity_method, source_url, detected_at, reasons_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(duplicate_id) DO UPDATE SET
                        similarity_score = excluded.similarity_score;
                    """,
                    (
                        rec.duplicate_id,
                        rec.canonical_opportunity_id,
                        rec.duplicate_opportunity_id,
                        rec.similarity_score,
                        rec.similarity_method,
                        rec.source_url,
                        rec.detected_at.isoformat(),
                        json.dumps(rec.reasons),
                    ),
                )

    def record_duplicate(self, record: DuplicateRecord) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.manager.transaction() as conn:
            # 1. Upsert cluster entry
            conn.execute(
                """
                INSERT INTO duplicate_clusters (canonical_opportunity_id, cluster_size, created_at, updated_at)
                VALUES (?, 2, ?, ?)
                ON CONFLICT(canonical_opportunity_id) DO UPDATE SET
                    cluster_size = cluster_size + 1,
                    updated_at = excluded.updated_at;
                """,
                (record.canonical_opportunity_id, now_iso, now_iso),
            )

            # 2. Insert duplicate linkage record
            conn.execute(
                """
                INSERT INTO duplicate_records (
                    duplicate_id, canonical_opportunity_id, duplicate_opportunity_id,
                    similarity_score, similarity_method, source_url, detected_at, reasons_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(duplicate_id) DO UPDATE SET
                    similarity_score = excluded.similarity_score;
                """,
                (
                    record.duplicate_id,
                    record.canonical_opportunity_id,
                    record.duplicate_opportunity_id,
                    record.similarity_score,
                    record.similarity_method,
                    record.source_url,
                    record.detected_at.isoformat(),
                    json.dumps(record.reasons),
                ),
            )

    def list_clusters(self) -> list[OpportunityCluster]:
        with self.manager.read_connection() as conn:
            rows = conn.execute(
                "SELECT canonical_opportunity_id FROM duplicate_clusters;"
            ).fetchall()
            return [
                self.get_cluster(r["canonical_opportunity_id"])
                for r in rows
                if self.get_cluster(r["canonical_opportunity_id"]) is not None
            ]


class SQLiteEligibilityAuditRepository(EligibilityAuditRepository):
    """SQLite implementation of EligibilityAuditRepository enforcing the 30-90 day retention policy."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def save_audit(self, result: EligibilityResult) -> None:
        with self.manager.transaction() as conn:
            audit_id = f"audit:{result.user_id}:{result.opportunity_id}:{int(result.evaluated_at.timestamp())}"
            conn.execute(
                """
                INSERT INTO eligibility_audits (
                    audit_id, opportunity_id, user_id, status, is_eligible,
                    disqualification_reasons_json, uncertainty_caveats_json,
                    constraint_checks_json, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_id,
                    result.opportunity_id,
                    result.user_id,
                    result.status.value,
                    1 if result.is_eligible else 0,
                    json.dumps(result.disqualification_reasons),
                    json.dumps(result.uncertainty_caveats),
                    json.dumps(
                        {k: v.model_dump() for k, v in result.constraint_checks.items()}
                    ),
                    result.evaluated_at.isoformat(),
                ),
            )

    def get_latest_audit(
        self, opportunity_id: str, user_id: str
    ) -> Optional[EligibilityResult]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM eligibility_audits
                WHERE opportunity_id = ? AND user_id = ?
                ORDER BY evaluated_at DESC LIMIT 1;
                """,
                (opportunity_id, user_id),
            ).fetchone()

            if not row:
                return None

            raw_checks = json.loads(row["constraint_checks_json"])
            checks = {
                k: ConstraintCheckResult.model_validate(v) for k, v in raw_checks.items()
            }
            hard_disqs = [c.rule_code for c in checks.values() if (c.status == ConstraintStatus.FAILED and not c.is_soft_failure) or c.is_vacancy_unavailable]
            soft_disqs = [c.rule_code for c in checks.values() if c.status == ConstraintStatus.FAILED and c.is_soft_failure]
            is_vac_exp = any(c.is_vacancy_unavailable for c in checks.values())
            is_soft_inel = len(soft_disqs) > 0 and len(hard_disqs) == 0 and not is_vac_exp

            return EligibilityResult(
                opportunity_id=row["opportunity_id"],
                user_id=row["user_id"],
                status=EligibilityStatus(row["status"]),
                is_eligible=bool(row["is_eligible"]),
                disqualification_reasons=json.loads(row["disqualification_reasons_json"]),
                hard_disqualifications=hard_disqs,
                soft_disqualifications=soft_disqs,
                is_vacancy_expired=is_vac_exp,
                is_soft_ineligible=is_soft_inel,
                uncertainty_caveats=json.loads(row["uncertainty_caveats_json"]),
                constraint_checks=checks,
                evaluated_at=datetime.fromisoformat(row["evaluated_at"]),
            )

    def list_audits_for_user(self, user_id: str) -> list[EligibilityResult]:
        with self.manager.read_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM eligibility_audits
                WHERE user_id = ?
                ORDER BY evaluated_at DESC;
                """,
                (user_id,),
            ).fetchall()

            results: list[EligibilityResult] = []
            for row in rows:
                raw_checks = json.loads(row["constraint_checks_json"])
                checks = {
                    k: ConstraintCheckResult.model_validate(v) for k, v in raw_checks.items()
                }
                hard_disqs = [c.rule_code for c in checks.values() if (c.status == ConstraintStatus.FAILED and not c.is_soft_failure) or c.is_vacancy_unavailable]
                soft_disqs = [c.rule_code for c in checks.values() if c.status == ConstraintStatus.FAILED and c.is_soft_failure]
                is_vac_exp = any(c.is_vacancy_unavailable for c in checks.values())
                is_soft_inel = len(soft_disqs) > 0 and len(hard_disqs) == 0 and not is_vac_exp

                results.append(
                    EligibilityResult(
                        opportunity_id=row["opportunity_id"],
                        user_id=row["user_id"],
                        status=EligibilityStatus(row["status"]),
                        is_eligible=bool(row["is_eligible"]),
                        disqualification_reasons=json.loads(row["disqualification_reasons_json"]),
                        hard_disqualifications=hard_disqs,
                        soft_disqualifications=soft_disqs,
                        is_vacancy_expired=is_vac_exp,
                        is_soft_ineligible=is_soft_inel,
                        uncertainty_caveats=json.loads(row["uncertainty_caveats_json"]),
                        constraint_checks=checks,
                        evaluated_at=datetime.fromisoformat(row["evaluated_at"]),
                    )
                )
            return results

    def prune_older_than(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.manager.transaction() as conn:
            res = conn.execute(
                "DELETE FROM eligibility_audits WHERE evaluated_at < ?;", (cutoff,)
            )
            return res.rowcount


class SQLiteRecommendationRepository(RecommendationRepository):
    """SQLite implementation of RecommendationRepository for candidate ranking evaluations."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def save_evaluation(self, response: RankingResponse) -> None:
        ranked_json = json.dumps([r.model_dump(mode="json") for r in response.ranked_recommendations])
        excluded_json = json.dumps(response.excluded_ineligible)
        weights_json = json.dumps(response.weights)

        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO recommendation_evaluations (
                    evaluation_id,
                    candidate_id,
                    model_version,
                    weight_profile,
                    weights_json,
                    total_evaluated,
                    total_ranked,
                    total_excluded,
                    ranked_recommendations_json,
                    excluded_ineligible_json,
                    evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    response.evaluation_id,
                    response.candidate_id,
                    response.model_version,
                    response.weight_profile_used,
                    weights_json,
                    response.total_candidates_evaluated,
                    response.total_eligible_ranked,
                    response.total_ineligible_excluded,
                    ranked_json,
                    excluded_json,
                    response.evaluation_timestamp.isoformat(),
                ),
            )

    def get_latest_evaluation(self, user_id: str) -> Optional[RankingResponse]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM recommendation_evaluations
                WHERE candidate_id = ?
                ORDER BY evaluated_at DESC
                LIMIT 1;
                """,
                (user_id,),
            ).fetchone()

            if not row:
                return None

            return self._row_to_response(row)

    def list_evaluations_for_user(self, user_id: str) -> list[RankingResponse]:
        with self.manager.read_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM recommendation_evaluations
                WHERE candidate_id = ?
                ORDER BY evaluated_at DESC;
                """,
                (user_id,),
            ).fetchall()

            return [self._row_to_response(r) for r in rows]

    def _row_to_response(self, row: Any) -> RankingResponse:
        raw_ranked = json.loads(row["ranked_recommendations_json"])
        ranked_recs = [RankedOpportunity.model_validate(r) for r in raw_ranked]
        excluded = json.loads(row["excluded_ineligible_json"])
        weights = json.loads(row["weights_json"])

        return RankingResponse(
            evaluation_id=row["evaluation_id"],
            candidate_id=row["candidate_id"],
            model_version=row["model_version"],
            weight_profile_used=row["weight_profile"],
            weights=weights,
            total_candidates_evaluated=row["total_evaluated"],
            total_eligible_ranked=row["total_ranked"],
            total_ineligible_excluded=row["total_excluded"],
            ranked_recommendations=ranked_recs,
            excluded_ineligible=excluded,
            evaluation_timestamp=datetime.fromisoformat(row["evaluated_at"]),
            execution_metadata={},
        )


class SQLiteCareerPathRepository(CareerPathRepository):
    """SQLite implementation of CareerPathRepository for assessments, plans, and action tracking."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def save_assessment(self, response: CareerPathAssessmentResponse) -> None:
        assessment_json = response.model_dump_json()
        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO career_path_assessments (
                    id, user_id, assessment_json, assessed_at
                ) VALUES (?, ?, ?, ?);
                """,
                (
                    f"cpa_{response.user_id}_{int(response.assessed_at.timestamp())}",
                    response.user_id,
                    assessment_json,
                    response.assessed_at.isoformat(),
                ),
            )

    def get_latest_assessment(self, user_id: str) -> Optional[CareerPathAssessmentResponse]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM career_path_assessments
                WHERE user_id = ?
                ORDER BY assessed_at DESC
                LIMIT 1;
                """,
                (user_id,),
            ).fetchone()

            if not row:
                return None

            return CareerPathAssessmentResponse.model_validate_json(row["assessment_json"])

    def save_development_plan(self, plan: PersonalizedDevelopmentPlan) -> None:
        plan_json = plan.model_dump_json()
        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO development_plans (
                    plan_id, user_id, plan_json, generated_at, updated_at
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    plan.plan_id,
                    plan.user_id,
                    plan_json,
                    plan.generated_at.isoformat(),
                    plan.updated_at.isoformat(),
                ),
            )

            # Also sync progress table for individual actions
            for action in plan.short_term_actions + plan.long_term_actions:
                completed_str = action.completed_at.isoformat() if action.completed_at else None
                conn.execute(
                    """
                    INSERT OR REPLACE INTO development_action_progress (
                        action_id, user_id, plan_id, status, artifact_url, candidate_notes, completed_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        action.action_id,
                        plan.user_id,
                        plan.plan_id,
                        action.status.value,
                        action.verification_artifact_url,
                        action.candidate_notes,
                        completed_str,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )

    def get_latest_development_plan(self, user_id: str) -> Optional[PersonalizedDevelopmentPlan]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM development_plans
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 1;
                """,
                (user_id,),
            ).fetchone()

            if not row:
                return None

            plan = PersonalizedDevelopmentPlan.model_validate_json(row["plan_json"])

            # Merge live progress states from development_action_progress
            progress_rows = conn.execute(
                """
                SELECT * FROM development_action_progress
                WHERE user_id = ? AND plan_id = ?;
                """,
                (user_id, plan.plan_id),
            ).fetchall()

            progress_map = {r["action_id"]: r for r in progress_rows}

            for act in plan.short_term_actions + plan.long_term_actions:
                if act.action_id in progress_map:
                    pr = progress_map[act.action_id]
                    act.status = ActionProgressStatus(pr["status"])
                    act.verification_artifact_url = pr["artifact_url"]
                    act.candidate_notes = pr["candidate_notes"]
                    if pr["completed_at"]:
                        act.completed_at = datetime.fromisoformat(pr["completed_at"])

            return plan

    def update_action_progress(
        self,
        user_id: str,
        action_id: str,
        status: ActionProgressStatus,
        artifact_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[DevelopmentActionItem]:
        plan = self.get_latest_development_plan(user_id)
        if not plan:
            return None

        # Find the action item in plan
        target_action: Optional[DevelopmentActionItem] = None
        for act in plan.short_term_actions + plan.long_term_actions:
            if act.action_id == action_id:
                target_action = act
                break

        if not target_action:
            return None

        target_action.status = status
        now_utc = datetime.now(timezone.utc)
        if status == ActionProgressStatus.COMPLETED:
            target_action.completed_at = now_utc
        elif status == ActionProgressStatus.NOT_STARTED:
            target_action.completed_at = None

        if artifact_url is not None:
            target_action.verification_artifact_url = artifact_url
        if notes is not None:
            target_action.candidate_notes = notes

        plan.updated_at = now_utc
        self.save_development_plan(plan)
        return target_action


class SQLiteDiscoveryRunRepository(DiscoveryRunRepository):
    """SQLite implementation of DiscoveryRunRepository for durable workflow persistence."""

    TERMINAL_STATUSES = {
        DiscoveryRunStatus.COMPLETED,
        DiscoveryRunStatus.FAILED,
        DiscoveryRunStatus.CANCELLED,
        DiscoveryRunStatus.PARTIALLY_COMPLETED,
    }

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def save(self, run: DiscoveryRun) -> None:
        """Persists or updates a discovery run idempotently."""
        conn_health_json = json.dumps([h.model_dump(mode="json") for h in run.connector_health])
        events_json = json.dumps([e.model_dump(mode="json") for e in run.timeline_events])
        adapt_json = json.dumps([a.model_dump(mode="json") for a in run.adaptation_history])
        strat_json = run.search_strategy.model_dump_json() if run.search_strategy else None
        cov_json = run.coverage_assessment.model_dump_json() if run.coverage_assessment else None
        canon_ids_json = json.dumps(run.canonical_opportunity_ids)
        elig_ids_json = json.dumps(run.eligible_opportunity_ids)
        resp_json = run.response.model_dump_json() if run.response else None

        sql = """
            INSERT INTO discovery_runs (
                run_id, candidate_id, status, termination_reason,
                started_at, completed_at, iterations_completed, total_tool_calls,
                target_coverage_goal, connector_health_json, timeline_events_json,
                adaptation_history_json, search_strategy_json, coverage_assessment_json,
                total_discovered_raw, canonical_count, duplicate_count,
                eligible_count, uncertain_count, ineligible_count,
                canonical_opportunity_ids_json, eligible_opportunity_ids_json,
                response_json, error_message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status = excluded.status,
                termination_reason = excluded.termination_reason,
                completed_at = excluded.completed_at,
                iterations_completed = excluded.iterations_completed,
                total_tool_calls = excluded.total_tool_calls,
                target_coverage_goal = excluded.target_coverage_goal,
                connector_health_json = excluded.connector_health_json,
                timeline_events_json = excluded.timeline_events_json,
                adaptation_history_json = excluded.adaptation_history_json,
                search_strategy_json = excluded.search_strategy_json,
                coverage_assessment_json = excluded.coverage_assessment_json,
                total_discovered_raw = excluded.total_discovered_raw,
                canonical_count = excluded.canonical_count,
                duplicate_count = excluded.duplicate_count,
                eligible_count = excluded.eligible_count,
                uncertain_count = excluded.uncertain_count,
                ineligible_count = excluded.ineligible_count,
                canonical_opportunity_ids_json = excluded.canonical_opportunity_ids_json,
                eligible_opportunity_ids_json = excluded.eligible_opportunity_ids_json,
                response_json = excluded.response_json,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at;
        """

        now_str = datetime.now(timezone.utc).isoformat()
        with self.manager.transaction() as conn:
            conn.execute(
                sql,
                (
                    run.run_id,
                    run.candidate_id,
                    run.status.value,
                    run.termination_reason.value if run.termination_reason else None,
                    run.started_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.iterations_completed,
                    run.total_tool_calls,
                    run.target_coverage_goal,
                    conn_health_json,
                    events_json,
                    adapt_json,
                    strat_json,
                    cov_json,
                    run.total_discovered_raw,
                    run.canonical_count,
                    run.duplicate_count,
                    run.eligible_count,
                    run.uncertain_count,
                    run.ineligible_count,
                    canon_ids_json,
                    elig_ids_json,
                    resp_json,
                    run.error_message,
                    run.created_at.isoformat() if run.created_at else now_str,
                    now_str,
                ),
            )

    def _row_to_run(self, row: sqlite3.Row) -> DiscoveryRun:
        response = (
            AdaptiveDiscoveryResponse.model_validate_json(row["response_json"])
            if row["response_json"]
            else None
        )
        connector_health = [
            ConnectorHealthReport.model_validate(h)
            for h in json.loads(row["connector_health_json"] or "[]")
        ]
        timeline_events = [
            WorkflowTimelineEvent.model_validate(e)
            for e in json.loads(row["timeline_events_json"] or "[]")
        ]
        adaptation_history = [
            AdaptationEvent.model_validate(a)
            for a in json.loads(row["adaptation_history_json"] or "[]")
        ]
        search_strategy = (
            SearchStrategy.model_validate_json(row["search_strategy_json"])
            if row["search_strategy_json"]
            else None
        )
        coverage_assessment = (
            CoverageAssessment.model_validate_json(row["coverage_assessment_json"])
            if row["coverage_assessment_json"]
            else None
        )
        term_reason = (
            TerminationReason(row["termination_reason"])
            if row["termination_reason"]
            else None
        )

        return DiscoveryRun(
            run_id=row["run_id"],
            candidate_id=row["candidate_id"],
            status=DiscoveryRunStatus(row["status"]),
            termination_reason=term_reason,
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            iterations_completed=row["iterations_completed"],
            total_tool_calls=row["total_tool_calls"],
            target_coverage_goal=row["target_coverage_goal"],
            connector_health=connector_health,
            timeline_events=timeline_events,
            adaptation_history=adaptation_history,
            search_strategy=search_strategy,
            coverage_assessment=coverage_assessment,
            total_discovered_raw=row["total_discovered_raw"],
            canonical_count=row["canonical_count"],
            duplicate_count=row["duplicate_count"],
            eligible_count=row["eligible_count"],
            uncertain_count=row["uncertain_count"],
            ineligible_count=row["ineligible_count"],
            canonical_opportunity_ids=json.loads(row["canonical_opportunity_ids_json"] or "[]"),
            eligible_opportunity_ids=json.loads(row["eligible_opportunity_ids_json"] or "[]"),
            search_outcomes=response.search_outcomes if response else [],
            search_calls_by_source=response.search_calls_by_source if response else {},
            rejections_by_code=response.rejections_by_code if response else {},
            sources_queried=response.sources_queried if response else [],
            verified_opportunity_count=response.verified_opportunity_count if response else 0,
            response=response,
            error_message=row["error_message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def get(self, run_id: str) -> Optional[DiscoveryRun]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM discovery_runs WHERE run_id = ?;", (run_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    def get_latest_for_candidate(self, candidate_id: str) -> Optional[DiscoveryRun]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM discovery_runs WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1;",
                (candidate_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    def list_for_candidate(self, candidate_id: str, limit: int = 10) -> list[DiscoveryRun]:
        with self.manager.read_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM discovery_runs WHERE candidate_id = ? ORDER BY created_at DESC LIMIT ?;",
                (candidate_id, limit),
            ).fetchall()
            return [self._row_to_run(r) for r in rows]

    def get_active_run_for_candidate(self, candidate_id: str) -> Optional[DiscoveryRun]:
        terminal_values = tuple(s.value for s in self.TERMINAL_STATUSES)
        placeholders = ",".join("?" for _ in terminal_values)
        query = f"""
            SELECT * FROM discovery_runs
            WHERE candidate_id = ? AND status NOT IN ({placeholders})
            ORDER BY created_at DESC LIMIT 1;
        """
        with self.manager.read_connection() as conn:
            row = conn.execute(query, (candidate_id, *terminal_values)).fetchone()
            if not row:
                return None
            return self._row_to_run(row)


class SQLiteCandidateActionRepository(CandidateActionRepository):
    """SQLite implementation of CandidateActionRepository tracking immutable interaction transitions."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def record_action(self, action: CandidateOpportunityActionRecord) -> None:
        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO candidate_opportunity_actions (
                    id, user_id, opportunity_id, action_type, previous_state,
                    reason_category, user_notes, soft_override_rationale, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    action.id,
                    action.user_id,
                    action.opportunity_id,
                    action.action_type.value,
                    action.previous_state,
                    action.reason_category.value if action.reason_category else None,
                    action.user_notes,
                    action.soft_override_rationale,
                    action.created_at.isoformat(),
                ),
            )

    def get_latest_actions(self, user_id: str) -> dict[str, CandidateOpportunityActionRecord]:
        """Returns map of opportunity_id to latest action record for user."""
        query = """
            SELECT a.* FROM candidate_opportunity_actions a
            INNER JOIN (
                SELECT opportunity_id, MAX(created_at) as max_created
                FROM candidate_opportunity_actions
                WHERE user_id = ?
                GROUP BY opportunity_id
            ) latest ON a.opportunity_id = latest.opportunity_id AND a.created_at = latest.max_created
            WHERE a.user_id = ?;
        """
        with self.manager.read_connection() as conn:
            rows = conn.execute(query, (user_id, user_id)).fetchall()
            result: dict[str, CandidateOpportunityActionRecord] = {}
            for r in rows:
                rec = self._row_to_record(r)
                result[rec.opportunity_id] = rec
            return result

    def get_actions_summary(self, user_id: str) -> CandidateActionsSummary:
        latest = self.get_latest_actions(user_id)
        saved = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.SAVED]
        applied = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.APPLIED]
        dismissed = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.DISMISSED]
        overridden = [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.SOFT_OVERRIDDEN]

        with self.manager.read_connection() as conn:
            cnt_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM candidate_opportunity_actions WHERE user_id = ?;", (user_id,)
            ).fetchone()
            total_count = cnt_row["cnt"] if cnt_row else 0

        return CandidateActionsSummary(
            user_id=user_id,
            saved_opportunity_ids=saved,
            applied_opportunity_ids=applied,
            dismissed_opportunity_ids=dismissed,
            soft_overridden_opportunity_ids=overridden,
            latest_actions_by_opp={opp_id: r.action_type for opp_id, r in latest.items()},
            total_actions_recorded=total_count,
        )

    def get_action_history(
        self, user_id: str, opportunity_id: Optional[str] = None, limit: int = 100
    ) -> list[CandidateOpportunityActionRecord]:
        with self.manager.read_connection() as conn:
            if opportunity_id:
                rows = conn.execute(
                    """
                    SELECT * FROM candidate_opportunity_actions
                    WHERE user_id = ? AND opportunity_id = ?
                    ORDER BY created_at DESC LIMIT ?;
                    """,
                    (user_id, opportunity_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM candidate_opportunity_actions
                    WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT ?;
                    """,
                    (user_id, limit),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]

    def get_overridden_opportunity_ids(self, user_id: str) -> list[str]:
        latest = self.get_latest_actions(user_id)
        return [opp_id for opp_id, r in latest.items() if r.action_type == ActionType.SOFT_OVERRIDDEN]

    @staticmethod
    def _row_to_record(row: Any) -> CandidateOpportunityActionRecord:
        created_at = row["created_at"]
        if isinstance(created_at, str):
            dt = datetime.fromisoformat(created_at)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)

        reason_val = row["reason_category"]
        reason_cat = ActionReasonCategory(reason_val) if reason_val else None

        return CandidateOpportunityActionRecord(
            id=row["id"],
            user_id=row["user_id"],
            opportunity_id=row["opportunity_id"],
            action_type=ActionType(row["action_type"]),
            previous_state=row["previous_state"],
            reason_category=reason_cat,
            user_notes=row["user_notes"],
            soft_override_rationale=row["soft_override_rationale"],
            created_at=dt,
        )


class SQLiteCareerMemoryRepository(CareerMemoryRepository):
    """SQLite implementation of CareerMemoryRepository preserving versioned candidate understanding."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def add_memory(self, memory: CandidateCareerMemoryItem) -> None:
        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO candidate_career_memory (
                    memory_id, user_id, memory_type, statement, provenance_level,
                    source_context, confidence_score, version, superseded_by,
                    change_reason, is_active, effective_from, effective_to, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    memory.memory_id,
                    memory.user_id,
                    memory.memory_type.value,
                    memory.statement,
                    memory.provenance_level.value,
                    memory.source_context,
                    memory.confidence_score,
                    memory.version,
                    memory.superseded_by,
                    memory.change_reason,
                    1 if memory.is_active else 0,
                    memory.effective_from.isoformat(),
                    memory.effective_to.isoformat() if memory.effective_to else None,
                    memory.created_at.isoformat(),
                ),
            )

    def get_memory(self, memory_id: str) -> Optional[CandidateCareerMemoryItem]:
        with self.manager.read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM candidate_career_memory WHERE memory_id = ?;", (memory_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_item(row)

    def update_memory(
        self,
        user_id: str,
        current_memory_id: str,
        new_statement: str,
        change_reason: str,
        provenance_level: Optional[ProvenanceLevel] = None,
        confidence_score: Optional[float] = None,
    ) -> CandidateCareerMemoryItem:
        now = datetime.now(timezone.utc)
        with self.manager.transaction() as conn:
            current_row = conn.execute(
                "SELECT * FROM candidate_career_memory WHERE memory_id = ? AND user_id = ?;",
                (current_memory_id, user_id),
            ).fetchone()
            if not current_row:
                raise ValueError(f"Memory item '{current_memory_id}' not found for user '{user_id}'.")

            current_item = self._row_to_item(current_row)
            new_id = f"mem_{uuid.uuid4().hex[:12]}"
            new_version = current_item.version + 1
            prov = provenance_level or current_item.provenance_level
            conf = confidence_score if confidence_score is not None else current_item.confidence_score

            # 1. Insert new version first so foreign key check for superseded_by succeeds
            new_item = CandidateCareerMemoryItem(
                memory_id=new_id,
                user_id=user_id,
                memory_type=current_item.memory_type,
                statement=new_statement,
                provenance_level=prov,
                source_context=current_item.source_context,
                confidence_score=conf,
                version=new_version,
                superseded_by=None,
                change_reason=change_reason,
                is_active=True,
                effective_from=now,
                effective_to=None,
                created_at=now,
            )

            conn.execute(
                """
                INSERT INTO candidate_career_memory (
                    memory_id, user_id, memory_type, statement, provenance_level,
                    source_context, confidence_score, version, superseded_by,
                    change_reason, is_active, effective_from, effective_to, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    new_item.memory_id,
                    new_item.user_id,
                    new_item.memory_type.value,
                    new_item.statement,
                    new_item.provenance_level.value,
                    new_item.source_context,
                    new_item.confidence_score,
                    new_item.version,
                    new_item.superseded_by,
                    new_item.change_reason,
                    1,
                    new_item.effective_from.isoformat(),
                    None,
                    new_item.created_at.isoformat(),
                ),
            )

            # 2. Supersede and archive previous version referencing newly inserted version
            conn.execute(
                """
                UPDATE candidate_career_memory
                SET is_active = 0, superseded_by = ?, effective_to = ?
                WHERE memory_id = ?;
                """,
                (new_id, now.isoformat(), current_memory_id),
            )

            return new_item

    def deactivate_memory(self, user_id: str, memory_id: str, reason: str) -> bool:
        now = datetime.now(timezone.utc)
        with self.manager.transaction() as conn:
            res = conn.execute(
                """
                UPDATE candidate_career_memory
                SET is_active = 0, change_reason = ?, effective_to = ?
                WHERE memory_id = ? AND user_id = ? AND is_active = 1;
                """,
                (reason, now.isoformat(), memory_id, user_id),
            )
            return res.rowcount > 0

    def list_active_memories(
        self, user_id: str, memory_type: Optional[MemoryType] = None
    ) -> list[CandidateCareerMemoryItem]:
        with self.manager.read_connection() as conn:
            if memory_type:
                rows = conn.execute(
                    """
                    SELECT * FROM candidate_career_memory
                    WHERE user_id = ? AND is_active = 1 AND memory_type = ?
                    ORDER BY created_at DESC;
                    """,
                    (user_id, memory_type.value),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM candidate_career_memory
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC;
                    """,
                    (user_id,),
                ).fetchall()
            return [self._row_to_item(r) for r in rows]

    def get_memory_history(self, user_id: str, memory_id: str) -> list[CandidateCareerMemoryItem]:
        with self.manager.read_connection() as conn:
            target = conn.execute(
                "SELECT * FROM candidate_career_memory WHERE memory_id = ? AND user_id = ?;",
                (memory_id, user_id),
            ).fetchone()
            if not target:
                return []

            rows = conn.execute(
                "SELECT * FROM candidate_career_memory WHERE user_id = ? AND memory_type = ? ORDER BY version ASC;",
                (user_id, target["memory_type"]),
            ).fetchall()
            return [self._row_to_item(r) for r in rows]

    def list_all_memories_for_candidate(
        self, user_id: str, include_inactive: bool = False
    ) -> list[CandidateCareerMemoryItem]:
        with self.manager.read_connection() as conn:
            if include_inactive:
                rows = conn.execute(
                    "SELECT * FROM candidate_career_memory WHERE user_id = ? ORDER BY version DESC, created_at DESC;",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM candidate_career_memory WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC;",
                    (user_id,),
                ).fetchall()
            return [self._row_to_item(r) for r in rows]

    @staticmethod
    def _row_to_item(row: Any) -> CandidateCareerMemoryItem:
        def _parse_dt(v: Any) -> Optional[datetime]:
            if not v:
                return None
            if isinstance(v, str):
                dt = datetime.fromisoformat(v)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            return None

        eff_from = _parse_dt(row["effective_from"]) or datetime.now(timezone.utc)
        eff_to = _parse_dt(row["effective_to"])
        created_at = _parse_dt(row["created_at"]) or datetime.now(timezone.utc)

        return CandidateCareerMemoryItem(
            memory_id=row["memory_id"],
            user_id=row["user_id"],
            memory_type=MemoryType(row["memory_type"]),
            statement=row["statement"],
            provenance_level=ProvenanceLevel(row["provenance_level"]),
            source_context=row["source_context"],
            confidence_score=float(row["confidence_score"]),
            version=int(row["version"]),
            superseded_by=row["superseded_by"],
            change_reason=row["change_reason"],
            is_active=bool(row["is_active"]),
            effective_from=eff_from,
            effective_to=eff_to,
            created_at=created_at,
        )


class SQLiteMarketReportRepository(MarketReportRepository):
    """SQLite implementation of MarketReportRepository for grounded intelligence caching."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or db_manager

    def save_report(self, report: MarketResearchReportRecord) -> None:
        now = datetime.now(timezone.utc)
        expires_at = report.expires_at or (now + timedelta(hours=48))
        with self.manager.transaction() as conn:
            conn.execute(
                """
                INSERT INTO market_research_reports (
                    report_id, role_title, country_code, mapped_occupation_code,
                    career_track, sample_size, confidence_score, sample_confidence_tier,
                    report_data_json, llm_synthesis_json, generated_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                    sample_size = excluded.sample_size,
                    confidence_score = excluded.confidence_score,
                    sample_confidence_tier = excluded.sample_confidence_tier,
                    report_data_json = excluded.report_data_json,
                    llm_synthesis_json = excluded.llm_synthesis_json,
                    generated_at = excluded.generated_at,
                    expires_at = excluded.expires_at;
                """,
                (
                    report.report_id,
                    report.role_title,
                    report.country_code,
                    report.mapped_occupation_code or "",
                    report.career_track,
                    report.sample_size,
                    report.confidence_score,
                    report.sample_confidence_tier.value,
                    report.model_dump_json(),
                    report.synthesis_markdown,
                    report.generated_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def get_report(
        self, role_title: str, country_code: str, max_age_hours: int = 48
    ) -> Optional[MarketResearchReportRecord]:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
        with self.manager.read_connection() as conn:
            row = conn.execute(
                """
                SELECT report_data_json FROM market_research_reports
                WHERE LOWER(role_title) = LOWER(?)
                  AND LOWER(country_code) = LOWER(?)
                  AND generated_at >= ?
                ORDER BY generated_at DESC
                LIMIT 1;
                """,
                (role_title.strip(), country_code.strip(), cutoff),
            ).fetchone()

            if not row:
                return None
            return MarketResearchReportRecord.model_validate_json(row["report_data_json"])

    def list_reports(self, limit: int = 20) -> list[MarketResearchReportRecord]:
        with self.manager.read_connection() as conn:
            rows = conn.execute(
                """
                SELECT report_data_json FROM market_research_reports
                ORDER BY generated_at DESC
                LIMIT ?;
                """,
                (limit,),
            ).fetchall()
            return [
                MarketResearchReportRecord.model_validate_json(r["report_data_json"])
                for r in rows
            ]





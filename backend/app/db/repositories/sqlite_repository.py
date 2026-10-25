from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from app.db.connection import DatabaseManager, db_manager
from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    CareerPathRepository,
    DuplicateClusterRepository,
    EligibilityAuditRepository,
    OpportunityRepository,
    RecommendationRepository,
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
    EligibilityResult,
    EligibilityStatus,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import (
    OpportunityEligibilityRules,
    OpportunitySkillRequirement,
    PolymorphicOpportunity,
)
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
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

            return CandidateCareerProfile(
                user_id=profile_row["user_id"],
                profile_version=profile_row["profile_version"],
                assessed_skills=assessed_skills,
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

        with self.manager.transaction() as conn:
            # 1. Upsert profile row
            conn.execute(
                """
                INSERT INTO candidate_profiles (
                    user_id, profile_version, overall_confidence, constraints_json,
                    target_career_paths_json, adjacent_career_paths_json,
                    current_career_path_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_version = excluded.profile_version,
                    overall_confidence = excluded.overall_confidence,
                    constraints_json = excluded.constraints_json,
                    target_career_paths_json = excluded.target_career_paths_json,
                    adjacent_career_paths_json = excluded.adjacent_career_paths_json,
                    current_career_path_json = excluded.current_career_path_json,
                    updated_at = excluded.updated_at;
                """,
                (
                    profile.user_id,
                    profile.profile_version,
                    profile.overall_profile_confidence,
                    constraints_json,
                    target_json,
                    adjacent_json,
                    current_json,
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

            return EligibilityResult(
                opportunity_id=row["opportunity_id"],
                user_id=row["user_id"],
                status=EligibilityStatus(row["status"]),
                is_eligible=bool(row["is_eligible"]),
                disqualification_reasons=json.loads(row["disqualification_reasons_json"]),
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
                results.append(
                    EligibilityResult(
                        opportunity_id=row["opportunity_id"],
                        user_id=row["user_id"],
                        status=EligibilityStatus(row["status"]),
                        is_eligible=bool(row["is_eligible"]),
                        disqualification_reasons=json.loads(row["disqualification_reasons_json"]),
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



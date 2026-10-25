from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.db.repositories.interfaces import (
    CandidateProfileRepository,
    CareerPathRepository,
    OpportunityRepository,
    RecommendationRepository,
)
from app.db.repositories.sqlite_repository import (
    SQLiteCandidateProfileRepository,
    SQLiteCareerPathRepository,
    SQLiteOpportunityRepository,
    SQLiteRecommendationRepository,
)
from app.modules.career_path.service import CareerPathIntelligenceService
from app.modules.discovery.connectors.base import create_normalized_opportunity
from app.modules.ranking.engine import CandidateJobRankingEngine
from app.schemas.common import (
    CareerPathRelationship,
    DegreeLevel,
    EvidenceSourceType,
    OpportunityCategory,
    WorkMode,
)
from app.schemas.evidence import EvidenceRecord
from app.schemas.opportunity import OpportunitySkillRequirement, PolymorphicOpportunity
from app.schemas.profile import (
    AssessedSkill,
    CandidateCareerProfile,
    CandidateEligibilityProfile,
    CareerPathNode,
)

logger = logging.getLogger(__name__)


def build_seed_candidates() -> list[CandidateCareerProfile]:
    """Constructs realistic demo candidate profiles used across JobFalcon frontend demos."""
    now = datetime.now(timezone.utc)

    # 1. Maya Chen - Junior Backend Engineer (maya-chen-junior)
    ev_m_py = EvidenceRecord(
        evidence_id="ev_maya_jr_py",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Built asynchronous REST APIs in Python using FastAPI, Pydantic, and PostgreSQL.",
        observed_at=now,
        verifiability_weight=0.90,
    )
    ev_m_fastapi = EvidenceRecord(
        evidence_id="ev_maya_jr_fastapi",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Architected REST endpoints in FastAPI handling 5,000 req/sec.",
        observed_at=now,
        verifiability_weight=0.90,
    )
    ev_m_pg = EvidenceRecord(
        evidence_id="ev_maya_jr_pg",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Designed relational schemas and wrote indexed queries in PostgreSQL.",
        observed_at=now,
        verifiability_weight=0.88,
    )
    ev_m_docker = EvidenceRecord(
        evidence_id="ev_maya_jr_docker",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Containerized microservices using Docker and implemented CI/CD pipelines.",
        observed_at=now,
        verifiability_weight=0.80,
    )
    ev_m_ts = EvidenceRecord(
        evidence_id="ev_maya_jr_ts",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Built dashboard developer portal using TypeScript and React.",
        observed_at=now,
        verifiability_weight=0.75,
    )

    maya_skills = [
        AssessedSkill(
            canonical_skill_id="esco:python",
            skill_name="Python",
            proficiency_score=8.5,
            confidence_score=0.92,
            evidence_records=[ev_m_py],
        ),
        AssessedSkill(
            canonical_skill_id="esco:fastapi",
            skill_name="FastAPI",
            proficiency_score=8.0,
            confidence_score=0.90,
            evidence_records=[ev_m_fastapi],
        ),
        AssessedSkill(
            canonical_skill_id="esco:postgresql",
            skill_name="PostgreSQL",
            proficiency_score=7.5,
            confidence_score=0.85,
            evidence_records=[ev_m_pg],
        ),
        AssessedSkill(
            canonical_skill_id="esco:docker",
            skill_name="Docker",
            proficiency_score=7.0,
            confidence_score=0.80,
            evidence_records=[ev_m_docker],
        ),
        AssessedSkill(
            canonical_skill_id="esco:typescript",
            skill_name="TypeScript",
            proficiency_score=6.0,
            confidence_score=0.75,
            evidence_records=[ev_m_ts],
        ),
    ]

    maya_target = CareerPathNode(
        occupation_code="15-1252.00",
        title="Backend Software Engineer",
        relationship_type=CareerPathRelationship.TARGET,
        adjacency_similarity=1.0,
    )
    maya_adjacent = CareerPathNode(
        occupation_code="15-1252.00",
        title="Full Stack Developer",
        relationship_type=CareerPathRelationship.ADJACENT,
        adjacency_similarity=0.80,
    )
    maya_constraints = CandidateEligibilityProfile(
        authorized_country_codes=["US"],
        requires_visa_sponsorship=False,
        highest_degree_level=DegreeLevel.BACHELORS,
        is_currently_enrolled_student=False,
        total_full_time_experience_months=18,
        allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
        allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID],
        preferred_locations=["San Francisco, CA"],
    )

    cand_maya_junior = CandidateCareerProfile(
        user_id="maya-chen-junior",
        profile_version=1,
        assessed_skills=maya_skills,
        current_career_path=None,
        target_career_paths=[maya_target],
        adjacent_career_paths=[maya_adjacent],
        eligibility_constraints=maya_constraints,
        overall_profile_confidence=0.92,
    )

    # 2. Maya Chen (usr_cand_backend_01 - used in CareerPathIntelligenceDemo)
    ev_mb1 = EvidenceRecord(
        evidence_id="ev_maya_be_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Built asynchronous REST APIs in Python using FastAPI, Pydantic, and PostgreSQL.",
        observed_at=now,
        verifiability_weight=0.90,
    )
    ev_mb2 = EvidenceRecord(
        evidence_id="ev_maya_be_02",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Designed relational schemas and wrote indexed queries in PostgreSQL handling 5,000 req/sec.",
        observed_at=now,
        verifiability_weight=0.88,
    )
    ev_mb3 = EvidenceRecord(
        evidence_id="ev_maya_be_03",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Wrote complex SQL migrations and optimized index access paths.",
        observed_at=now,
        verifiability_weight=0.85,
    )

    cand_maya_backend_01 = CandidateCareerProfile(
        user_id="usr_cand_backend_01",
        profile_version=1,
        assessed_skills=[
            AssessedSkill(
                canonical_skill_id="esco:python",
                skill_name="Python",
                proficiency_score=8.0,
                confidence_score=0.90,
                evidence_records=[ev_mb1],
            ),
            AssessedSkill(
                canonical_skill_id="esco:postgresql",
                skill_name="PostgreSQL",
                proficiency_score=7.5,
                confidence_score=0.85,
                evidence_records=[ev_mb2],
            ),
            AssessedSkill(
                canonical_skill_id="esco:sql",
                skill_name="SQL",
                proficiency_score=8.0,
                confidence_score=0.85,
                evidence_records=[ev_mb3],
            ),
        ],
        current_career_path=CareerPathNode(
            occupation_code="15-1252.00",
            title="Software Developer",
            relationship_type=CareerPathRelationship.CURRENT,
            adjacency_similarity=1.0,
        ),
        target_career_paths=[maya_target],
        adjacent_career_paths=[maya_adjacent],
        eligibility_constraints=maya_constraints,
        overall_profile_confidence=0.92,
    )

    # 3. Rohan Sharma / Liam Patel - Student (usr_cand_student_02)
    ev_stud_py = EvidenceRecord(
        evidence_id="ev_stud_py_01",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Coursework project developing data analysis scripts in Python using pandas.",
        observed_at=now,
        verifiability_weight=0.65,
    )
    ev_stud_ml = EvidenceRecord(
        evidence_id="ev_stud_ml_01",
        source_type=EvidenceSourceType.RESUME_PROJECT,
        extracted_snippet="Coursework project training neural networks in PyTorch for computer vision tasks.",
        observed_at=now,
        verifiability_weight=0.65,
    )

    cand_student = CandidateCareerProfile(
        user_id="usr_cand_student_02",
        profile_version=1,
        assessed_skills=[
            AssessedSkill(
                canonical_skill_id="esco:python",
                skill_name="Python",
                proficiency_score=6.0,
                confidence_score=0.65,
                evidence_records=[ev_stud_py],
            ),
            AssessedSkill(
                canonical_skill_id="esco:machine-learning",
                skill_name="Machine Learning",
                proficiency_score=5.5,
                confidence_score=0.60,
                evidence_records=[ev_stud_ml],
            ),
        ],
        current_career_path=None,
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Machine Learning Engineer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        adjacent_career_paths=[
            CareerPathNode(
                occupation_code="15-1251.00",
                title="Data Scientist",
                relationship_type=CareerPathRelationship.ADJACENT,
                adjacency_similarity=0.75,
            )
        ],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            requires_visa_sponsorship=True,
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled_student=True,
            graduation_date=None,  # Missing graduation window represents uncertainty
            total_full_time_experience_months=0,
            allowed_opportunity_categories=[
                OpportunityCategory.INTERNSHIP,
                OpportunityCategory.FULL_TIME_JOB,
            ],
            allowed_work_modes=[WorkMode.REMOTE, WorkMode.HYBRID, WorkMode.ON_SITE],
            preferred_locations=[],
        ),
        overall_profile_confidence=0.68,
    )

    # 4. Alex Rivera - Full Stack Engineer (alex-rivera-fullstack)
    ev_alex_ts = EvidenceRecord(
        evidence_id="ev_alex_ts_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Engineered production TypeScript micro-frontends and backend services.",
        observed_at=now,
        verifiability_weight=0.88,
    )
    ev_alex_react = EvidenceRecord(
        evidence_id="ev_alex_react_01",
        source_type=EvidenceSourceType.RESUME_WORK_EXPERIENCE,
        extracted_snippet="Engineered production React components and customer-facing web apps with Tailwind CSS.",
        observed_at=now,
        verifiability_weight=0.88,
    )
    cand_alex = CandidateCareerProfile(
        user_id="alex-rivera-fullstack",
        profile_version=1,
        assessed_skills=[
            AssessedSkill(
                canonical_skill_id="esco:typescript",
                skill_name="TypeScript",
                proficiency_score=8.5,
                confidence_score=0.88,
                evidence_records=[ev_alex_ts],
            ),
            AssessedSkill(
                canonical_skill_id="esco:react",
                skill_name="React",
                proficiency_score=8.0,
                confidence_score=0.85,
                evidence_records=[ev_alex_react],
            ),
        ],
        current_career_path=None,
        target_career_paths=[
            CareerPathNode(
                occupation_code="15-1252.00",
                title="Full Stack Developer",
                relationship_type=CareerPathRelationship.TARGET,
                adjacency_similarity=1.0,
            )
        ],
        adjacent_career_paths=[],
        eligibility_constraints=CandidateEligibilityProfile(
            authorized_country_codes=["US"],
            requires_visa_sponsorship=False,
            highest_degree_level=DegreeLevel.BACHELORS,
            is_currently_enrolled_student=False,
            total_full_time_experience_months=48,
            allowed_opportunity_categories=[OpportunityCategory.FULL_TIME_JOB],
            allowed_work_modes=[WorkMode.REMOTE],
            preferred_locations=[],
        ),
        overall_profile_confidence=0.88,
    )

    return [cand_maya_junior, cand_maya_backend_01, cand_student, cand_alex]


def build_seed_opportunities() -> list[PolymorphicOpportunity]:
    """Constructs realistic benchmark opportunities matching frontend demonstration IDs."""
    opps: list[PolymorphicOpportunity] = []

    # 1. opp-b-1 (Standard sample opportunity expected by CareerExplanationAndGapAnalysis)
    opp_b1 = create_normalized_opportunity(
        opportunity_id="opp-b-1",
        title="Junior Backend Software Engineer",
        company_name="CloudScale Systems",
        description="Design high-performance asynchronous REST APIs in Python using FastAPI, Pydantic, and PostgreSQL for remote teams.",
        source_url="https://job-boards.greenhouse.io/cloudscale/jobs/10101",
        source_system="greenhouse",
        source_job_id="cs_be_101",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=12,
        work_mode=WorkMode.REMOTE,
        location_city_country=["San Francisco, CA"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=7.0,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:fastapi",
                skill_name="FastAPI",
                minimum_proficiency_expected=6.5,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:postgresql",
                skill_name="PostgreSQL",
                minimum_proficiency_expected=6.0,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:docker",
                skill_name="Docker",
                minimum_proficiency_expected=5.0,
                is_mandatory=False,
            ),
        ],
        mapped_occupation_code="15-1252.00",
        completeness_score=0.95,
        trust_score=0.90,
    )
    opps.append(opp_b1)

    # 2. opp-ideal-backend
    opp_ideal = create_normalized_opportunity(
        opportunity_id="opp-ideal-backend",
        title="Junior Backend Engineer (Python / FastAPI)",
        company_name="CloudScale Systems",
        description="Build scalable microservices and relational database schemas with Python, FastAPI, and PostgreSQL.",
        source_url="https://job-boards.greenhouse.io/cloudscale/jobs/10202",
        source_system="greenhouse",
        source_job_id="cs_be_102",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=12,
        work_mode=WorkMode.REMOTE,
        location_city_country=["San Francisco, CA"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=7.0,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:fastapi",
                skill_name="FastAPI",
                minimum_proficiency_expected=6.5,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:postgresql",
                skill_name="PostgreSQL",
                minimum_proficiency_expected=6.0,
                is_mandatory=True,
            ),
        ],
        mapped_occupation_code="15-1252.00",
        completeness_score=0.95,
        trust_score=0.92,
    )
    opps.append(opp_ideal)

    # 3. opp-growth-backend
    opp_growth = create_normalized_opportunity(
        opportunity_id="opp-growth-backend",
        title="Backend Systems Engineer",
        company_name="Apex Data Labs",
        description="Design distributed backend microservices in Python and Rust with Docker, Kubernetes, and Kafka.",
        source_url="https://jobs.ashbyhq.com/apex/jobs/20101",
        source_system="ashby",
        source_job_id="apex_be_201",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=18,
        work_mode=WorkMode.HYBRID,
        location_city_country=["New York, NY"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=8.0,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:docker",
                skill_name="Docker",
                minimum_proficiency_expected=6.5,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:kubernetes",
                skill_name="Kubernetes",
                minimum_proficiency_expected=6.0,
                is_mandatory=False,
            ),
        ],
        mapped_occupation_code="15-1252.00",
        completeness_score=0.92,
        trust_score=0.88,
    )
    opps.append(opp_growth)

    # 4. opp-adjacent-data-eng
    opp_adjacent = create_normalized_opportunity(
        opportunity_id="opp-adjacent-data-eng",
        title="Junior Data Platform Engineer",
        company_name="Quantico Metrics",
        description="Maintain data pipelines, SQL ETL flows, and data warehouse tables in PostgreSQL and Python.",
        source_url="https://job-boards.greenhouse.io/quantico/jobs/30101",
        source_system="greenhouse",
        source_job_id="qm_data_301",
        category=OpportunityCategory.FULL_TIME_JOB,
        eligible_country_codes=["US"],
        sponsors_work_visa=False,
        minimum_degree_required=DegreeLevel.BACHELORS,
        requires_active_student_status=False,
        min_experience_months=12,
        work_mode=WorkMode.REMOTE,
        location_city_country=["Chicago, IL"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=7.0,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:postgresql",
                skill_name="PostgreSQL",
                minimum_proficiency_expected=7.0,
                is_mandatory=True,
            ),
        ],
        mapped_occupation_code="15-1251.00",
        completeness_score=0.88,
        trust_score=0.85,
    )
    opps.append(opp_adjacent)

    # 5. opp-ml-intern (For students)
    opp_ml_intern = create_normalized_opportunity(
        opportunity_id="opp-ml-intern",
        title="Machine Learning Engineering Intern",
        company_name="DeepVision AI",
        description="Summer internship developing machine learning pipelines in Python with PyTorch and computer vision.",
        source_url="https://job-boards.greenhouse.io/deepvision/jobs/40101",
        source_system="greenhouse",
        source_job_id="dv_ml_401",
        category=OpportunityCategory.INTERNSHIP,
        eligible_country_codes=["US"],
        sponsors_work_visa=True,
        minimum_degree_required=DegreeLevel.NONE,
        requires_active_student_status=True,
        min_experience_months=0,
        work_mode=WorkMode.REMOTE,
        location_city_country=["Seattle, WA"],
        skill_requirements=[
            OpportunitySkillRequirement(
                canonical_skill_id="esco:python",
                skill_name="Python",
                minimum_proficiency_expected=5.5,
                is_mandatory=True,
            ),
            OpportunitySkillRequirement(
                canonical_skill_id="esco:machine-learning",
                skill_name="Machine Learning",
                minimum_proficiency_expected=5.0,
                is_mandatory=True,
            ),
        ],
        mapped_occupation_code="15-1252.00",
        completeness_score=0.90,
        trust_score=0.88,
    )
    opps.append(opp_ml_intern)

    return opps


def seed_demo_data(
    profile_repo: Optional[CandidateProfileRepository] = None,
    opp_repo: Optional[OpportunityRepository] = None,
    rec_repo: Optional[RecommendationRepository] = None,
    career_repo: Optional[CareerPathRepository] = None,
) -> None:
    """Idempotently seeds demo candidates, opportunities, and evaluations into SQLite database."""
    p_repo = profile_repo or SQLiteCandidateProfileRepository()
    o_repo = opp_repo or SQLiteOpportunityRepository()
    r_repo = rec_repo or SQLiteRecommendationRepository()
    c_repo = career_repo or SQLiteCareerPathRepository()

    ranking_engine = CandidateJobRankingEngine()
    career_service = CareerPathIntelligenceService()

    # 1. Seed Opportunities
    opportunities = build_seed_opportunities()
    for opp in opportunities:
        existing = o_repo.get(opp.opportunity_id)
        if not existing:
            o_repo.save(opp)
            logger.info("Seeded demo opportunity: %s (%s)", opp.opportunity_id, opp.title)

    all_opps = o_repo.list_all(active_only=True)

    # 2. Seed Candidates & Pre-Compute Evaluations
    candidates = build_seed_candidates()
    for cand in candidates:
        existing_cand = p_repo.get(cand.user_id)
        if not existing_cand:
            p_repo.save(cand)
            logger.info("Seeded demo candidate profile: %s", cand.user_id)

        # Pre-compute and save initial ranking evaluation if not present
        latest_eval = r_repo.get_latest_evaluation(cand.user_id)
        if not latest_eval or not latest_eval.ranked_recommendations:
            eval_resp = ranking_engine.evaluate_and_rank(cand, all_opps)
            r_repo.save_evaluation(eval_resp)
            logger.info(
                "Pre-computed ranking evaluation for candidate %s: %d recommendations",
                cand.user_id,
                len(eval_resp.ranked_recommendations),
            )

        # Pre-compute and save initial career path assessment if not present
        existing_assessment = c_repo.get_latest_assessment(cand.user_id)
        if not existing_assessment:
            assessment = career_service.assess_candidate_career_paths(
                candidate=cand,
                discovered_opportunities=all_opps,
            )
            c_repo.save_assessment(assessment)
            c_repo.save_development_plan(assessment.development_plan)
            logger.info("Pre-computed career path assessment for candidate %s", cand.user_id)

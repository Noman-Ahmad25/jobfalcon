-- =====================================================================
-- JobFalcon Relational Schema Migration 001 (PostgreSQL 16 Implementation)
-- Matches core persistence architecture: Profiles, Opportunities, Provenance, Audits
-- =====================================================================

-- 1. Candidate Career Profiles
CREATE TABLE IF NOT EXISTS candidate_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    profile_version INTEGER NOT NULL DEFAULT 1,
    overall_confidence DOUBLE PRECISION NOT NULL,
    constraints_json JSONB NOT NULL,
    target_career_paths_json JSONB NOT NULL,
    adjacent_career_paths_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    current_career_path_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Candidate Assessed Skills
CREATE TABLE IF NOT EXISTS candidate_skills (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES candidate_profiles(user_id) ON DELETE CASCADE,
    canonical_skill_id VARCHAR(255) NOT NULL,
    skill_name VARCHAR(150) NOT NULL,
    proficiency_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    last_practiced_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_candidate_skills_user_id ON candidate_skills(user_id);
CREATE INDEX IF NOT EXISTS ix_candidate_skills_canonical ON candidate_skills(canonical_skill_id);

-- 3. Skill Evidence Records (Grounding Provenance)
CREATE TABLE IF NOT EXISTS candidate_evidence (
    evidence_id VARCHAR(255) PRIMARY KEY,
    skill_id VARCHAR(255) NOT NULL REFERENCES candidate_skills(id) ON DELETE CASCADE,
    source_type VARCHAR(100) NOT NULL,
    source_uri TEXT,
    extracted_snippet TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verifiability_weight DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candidate_evidence_skill_id ON candidate_evidence(skill_id);

-- 4. Polymorphic Opportunities
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id VARCHAR(255) PRIMARY KEY,
    minhash_signature_hex CHAR(64) NOT NULL,
    title VARCHAR(200) NOT NULL,
    company_name VARCHAR(150) NOT NULL,
    company_domain_verified BOOLEAN NOT NULL DEFAULT FALSE,
    mapped_occupation_code VARCHAR(100) NOT NULL,
    opportunity_category VARCHAR(50) NOT NULL,
    work_mode VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    source_system VARCHAR(50) NOT NULL DEFAULT 'generic',
    source_job_id VARCHAR(255),
    eligibility_rules_json JSONB NOT NULL,
    skill_requirements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    category_specific_attributes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    sanitized_summary TEXT NOT NULL,
    posted_at TIMESTAMPTZ NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completeness_score DOUBLE PRECISION NOT NULL,
    trust_score DOUBLE PRECISION NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_opportunities_minhash ON opportunities(minhash_signature_hex);
CREATE INDEX IF NOT EXISTS ix_opportunities_source ON opportunities(source_system, source_job_id);
CREATE INDEX IF NOT EXISTS ix_opportunities_category ON opportunities(opportunity_category);
CREATE INDEX IF NOT EXISTS ix_opportunities_occupation ON opportunities(mapped_occupation_code);

-- 5. Duplicate Clusters (Syndicated Opportunity Groups)
CREATE TABLE IF NOT EXISTS duplicate_clusters (
    canonical_opportunity_id VARCHAR(255) PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    cluster_size INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Duplicate Linkage Records (Provenance Preservation)
CREATE TABLE IF NOT EXISTS duplicate_records (
    duplicate_id VARCHAR(255) PRIMARY KEY,
    canonical_opportunity_id VARCHAR(255) NOT NULL REFERENCES duplicate_clusters(canonical_opportunity_id) ON DELETE CASCADE,
    duplicate_opportunity_id VARCHAR(255) NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    similarity_score DOUBLE PRECISION NOT NULL,
    similarity_method VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_duplicate_records_canonical ON duplicate_records(canonical_opportunity_id);

-- 7. Deterministic Eligibility Audits (Lifecycle / Retention Window)
CREATE TABLE IF NOT EXISTS eligibility_audits (
    audit_id VARCHAR(255) PRIMARY KEY,
    opportunity_id VARCHAR(255) NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    is_eligible BOOLEAN NOT NULL,
    disqualification_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncertainty_caveats_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    constraint_checks_json JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_eligibility_audits_user_opp ON eligibility_audits(user_id, opportunity_id);
CREATE INDEX IF NOT EXISTS ix_eligibility_audits_evaluated_at ON eligibility_audits(evaluated_at);

-- 8. Candidate Recommendations & Ranking Evaluations
CREATE TABLE IF NOT EXISTS recommendation_evaluations (
    evaluation_id VARCHAR(255) PRIMARY KEY,
    candidate_id VARCHAR(255) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    weight_profile VARCHAR(100) NOT NULL,
    weights_json JSONB NOT NULL,
    total_evaluated INTEGER NOT NULL,
    total_ranked INTEGER NOT NULL,
    total_excluded INTEGER NOT NULL,
    ranked_recommendations_json JSONB NOT NULL,
    excluded_ineligible_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_recommendation_evaluations_candidate ON recommendation_evaluations(candidate_id, evaluated_at);

-- 9. Career Path Assessments
CREATE TABLE IF NOT EXISTS career_path_assessments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    assessment_json JSONB NOT NULL,
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_career_path_assessments_user ON career_path_assessments(user_id, assessed_at);

-- 10. Personalized Development Plans
CREATE TABLE IF NOT EXISTS development_plans (
    plan_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_development_plans_user ON development_plans(user_id, updated_at);

-- 11. Development Action Progress
CREATE TABLE IF NOT EXISTS development_action_progress (
    action_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    status TEXT NOT NULL,
    artifact_url TEXT,
    candidate_notes TEXT,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_development_action_progress_user ON development_action_progress(user_id, plan_id);



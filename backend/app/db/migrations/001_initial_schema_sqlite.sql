-- =====================================================================
-- JobFalcon Relational Schema Migration 001 (SQLite Implementation)
-- Matches core domain entities: Profiles, Opportunities, Provenance, Audits
-- =====================================================================

PRAGMA foreign_keys = ON;

-- 1. Candidate Career Profiles
CREATE TABLE IF NOT EXISTS candidate_profiles (
    user_id TEXT PRIMARY KEY,
    profile_version INTEGER NOT NULL DEFAULT 1,
    overall_confidence REAL NOT NULL,
    constraints_json TEXT NOT NULL,
    target_career_paths_json TEXT NOT NULL,
    adjacent_career_paths_json TEXT NOT NULL DEFAULT '[]',
    current_career_path_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Candidate Assessed Skills
CREATE TABLE IF NOT EXISTS candidate_skills (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES candidate_profiles(user_id) ON DELETE CASCADE,
    canonical_skill_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    proficiency_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    last_practiced_date TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candidate_skills_user_id ON candidate_skills(user_id);
CREATE INDEX IF NOT EXISTS ix_candidate_skills_canonical ON candidate_skills(canonical_skill_id);

-- 3. Skill Evidence Records (Grounding Provenance)
CREATE TABLE IF NOT EXISTS candidate_evidence (
    evidence_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL REFERENCES candidate_skills(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_uri TEXT,
    extracted_snippet TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    verifiability_weight REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candidate_evidence_skill_id ON candidate_evidence(skill_id);

-- 4. Polymorphic Opportunities
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    minhash_signature_hex TEXT NOT NULL,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    company_domain_verified INTEGER NOT NULL DEFAULT 0,
    mapped_occupation_code TEXT NOT NULL,
    opportunity_category TEXT NOT NULL,
    work_mode TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_system TEXT NOT NULL DEFAULT 'generic',
    source_job_id TEXT,
    eligibility_rules_json TEXT NOT NULL,
    skill_requirements_json TEXT NOT NULL DEFAULT '[]',
    category_specific_attributes_json TEXT NOT NULL DEFAULT '{}',
    sanitized_summary TEXT NOT NULL,
    posted_at TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completeness_score REAL NOT NULL,
    trust_score REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_duplicate INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_opportunities_minhash ON opportunities(minhash_signature_hex);
CREATE INDEX IF NOT EXISTS ix_opportunities_source ON opportunities(source_system, source_job_id);
CREATE INDEX IF NOT EXISTS ix_opportunities_category ON opportunities(opportunity_category);
CREATE INDEX IF NOT EXISTS ix_opportunities_occupation ON opportunities(mapped_occupation_code);

-- 5. Duplicate Clusters (Syndicated Opportunity Groups)
CREATE TABLE IF NOT EXISTS duplicate_clusters (
    canonical_opportunity_id TEXT PRIMARY KEY REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    cluster_size INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 6. Duplicate Linkage Records (Provenance Preservation)
CREATE TABLE IF NOT EXISTS duplicate_records (
    duplicate_id TEXT PRIMARY KEY,
    canonical_opportunity_id TEXT NOT NULL REFERENCES duplicate_clusters(canonical_opportunity_id) ON DELETE CASCADE,
    duplicate_opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    similarity_score REAL NOT NULL,
    similarity_method TEXT NOT NULL,
    source_url TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    reasons_json TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS ix_duplicate_records_canonical ON duplicate_records(canonical_opportunity_id);

-- 7. Deterministic Eligibility Audits (Lifecycle / Retention Window)
CREATE TABLE IF NOT EXISTS eligibility_audits (
    audit_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    is_eligible INTEGER NOT NULL,
    disqualification_reasons_json TEXT NOT NULL DEFAULT '[]',
    uncertainty_caveats_json TEXT NOT NULL DEFAULT '[]',
    constraint_checks_json TEXT NOT NULL,
    evaluated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_eligibility_audits_user_opp ON eligibility_audits(user_id, opportunity_id);
CREATE INDEX IF NOT EXISTS ix_eligibility_audits_evaluated_at ON eligibility_audits(evaluated_at);

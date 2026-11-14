-- Migration 004: Candidate Opportunity Actions, Versioned Career Memory, and Market Research Reports

-- 1. Candidate Opportunity Action Ledger (Preserves Historical State Transitions)
CREATE TABLE IF NOT EXISTS candidate_opportunity_actions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES candidate_profiles(user_id) ON DELETE CASCADE,
    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    previous_state TEXT,
    reason_category TEXT,
    user_notes TEXT,
    soft_override_rationale TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candidate_actions_user ON candidate_opportunity_actions(user_id, opportunity_id, created_at);
CREATE INDEX IF NOT EXISTS ix_candidate_actions_type ON candidate_opportunity_actions(user_id, action_type);

-- 2. Candidate Career Memory with Version History & Superseded Facts
CREATE TABLE IF NOT EXISTS candidate_career_memory (
    memory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES candidate_profiles(user_id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    statement TEXT NOT NULL,
    provenance_level TEXT NOT NULL,
    source_context TEXT,
    confidence_score REAL NOT NULL DEFAULT 1.0,
    version INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT REFERENCES candidate_career_memory(memory_id),
    change_reason TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_candidate_memory_active ON candidate_career_memory(user_id, is_active);
CREATE INDEX IF NOT EXISTS ix_candidate_memory_history ON candidate_career_memory(user_id, memory_type, version);

-- 3. Cached Market Research Reports (Candidate-Specific Scope, No Hard US Assumption)
CREATE TABLE IF NOT EXISTS market_research_reports (
    report_id TEXT PRIMARY KEY,
    role_title TEXT NOT NULL,
    country_code TEXT NOT NULL,
    mapped_occupation_code TEXT NOT NULL,
    career_track TEXT NOT NULL DEFAULT 'TECHNICAL',
    sample_size INTEGER NOT NULL,
    confidence_score REAL NOT NULL,
    sample_confidence_tier TEXT NOT NULL,
    report_data_json TEXT NOT NULL,
    llm_synthesis_json TEXT,
    generated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_market_reports_lookup ON market_research_reports(role_title, country_code, expires_at);

-- =====================================================================
-- JobFalcon Schema Migration 002: Add display_name to candidate_profiles
-- Idempotent: SQLite will raise an error if the column already exists;
-- this is handled gracefully by the DatabaseManager._apply_migrations()
-- method using executescript with error recovery.
-- =====================================================================

ALTER TABLE candidate_profiles ADD COLUMN display_name TEXT;

-- Migration 003: Add rich career history columns to candidate_profiles
ALTER TABLE candidate_profiles ADD COLUMN work_experiences_json TEXT DEFAULT '[]';
ALTER TABLE candidate_profiles ADD COLUMN education_json TEXT DEFAULT '[]';
ALTER TABLE candidate_profiles ADD COLUMN projects_json TEXT DEFAULT '[]';
ALTER TABLE candidate_profiles ADD COLUMN headline TEXT;
ALTER TABLE candidate_profiles ADD COLUMN location TEXT;
ALTER TABLE candidate_profiles ADD COLUMN bio TEXT;

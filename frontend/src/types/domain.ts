/**
 * Domain types mirroring backend Pydantic v2 schemas for JobFalcon.
 */

export type OpportunityCategory =
  | 'INTERNSHIP'
  | 'FULL_TIME_JOB'
  | 'PART_TIME_JOB'
  | 'APPRENTICESHIP'
  | 'FELLOWSHIP'
  | 'CONTRACT';

export type WorkMode = 'REMOTE' | 'HYBRID' | 'ON_SITE';

export type DegreeLevel =
  | 'NONE'
  | 'HIGH_SCHOOL'
  | 'ASSOCIATE'
  | 'BACHELORS'
  | 'MASTERS'
  | 'DOCTORATE';

export type EvidenceSourceType =
  | 'RESUME_WORK_EXPERIENCE'
  | 'RESUME_PROJECT'
  | 'VERIFIED_CODE_REPOSITORY'
  | 'ACADEMIC_TRANSCRIPT'
  | 'CERTIFICATION'
  | 'SELF_REPORTED_UNVERIFIED'
  | 'LIVE_ATS_POSTING'
  | 'TAXONOMY_BENCHMARK';

export type CareerPathRelationship = 'CURRENT' | 'TARGET' | 'ADJACENT';

export interface EvidenceRecord {
  evidence_id: string;
  source_type: EvidenceSourceType;
  source_uri?: string | null;
  extracted_snippet: string;
  observed_at: string;
  verifiability_weight: number;
}

export interface AssessedSkill {
  canonical_skill_id: string;
  skill_name: string;
  proficiency_score: number;
  confidence_score: number;
  evidence_records: EvidenceRecord[];
  last_practiced_date?: string | null;
}

export interface CareerPathNode {
  occupation_code: string;
  title: string;
  relationship_type: CareerPathRelationship;
  adjacency_similarity: number;
  missing_core_skill_ids: string[];
}

export interface CandidateEligibilityProfile {
  authorized_country_codes: string[];
  requires_visa_sponsorship: boolean;
  highest_degree_level: DegreeLevel;
  is_currently_enrolled_student: boolean;
  expected_graduation_date?: string | null;
  total_full_time_experience_months: number;
  allowed_opportunity_categories: OpportunityCategory[];
  allowed_work_modes: WorkMode[];
  preferred_locations: string[];
}

export interface CandidateCareerProfile {
  user_id: string;
  profile_version: number;
  assessed_skills: AssessedSkill[];
  current_career_path?: CareerPathNode | null;
  target_career_paths: CareerPathNode[];
  adjacent_career_paths: CareerPathNode[];
  eligibility_constraints: CandidateEligibilityProfile;
  overall_profile_confidence: number;
}

export interface OpportunityEligibilityRules {
  opportunity_category: OpportunityCategory;
  eligible_country_codes: string[];
  sponsors_work_visa: boolean;
  minimum_degree_required: DegreeLevel;
  requires_active_student_status: boolean;
  allowed_graduation_window_start?: string | null;
  allowed_graduation_window_end?: string | null;
  min_experience_months: number;
  max_experience_months?: number | null;
  work_mode: WorkMode;
  location_city_country: string[];
  application_deadline?: string | null;
}

export interface OpportunitySkillRequirement {
  canonical_skill_id: string;
  skill_name: string;
  is_mandatory: boolean;
  minimum_proficiency_expected: number;
}

export interface PolymorphicOpportunity {
  opportunity_id: string;
  minhash_signature_hex: string;
  title: string;
  company_name: string;
  company_domain_verified: boolean;
  mapped_occupation_code: string;
  eligibility_rules: OpportunityEligibilityRules;
  skill_requirements: OpportunitySkillRequirement[];
  category_specific_attributes: Record<string, unknown>;
  sanitized_summary: string;
  source_url: string;
  posted_at: string;
  discovered_at: string;
  completeness_score: number;
  trust_score: number;
  is_duplicate: boolean;
}

export type EligibilityStatus =
  | 'ELIGIBLE'
  | 'ELIGIBLE_WITH_UNCERTAINTY'
  | 'INELIGIBLE';

export type ConstraintStatus = 'PASSED' | 'FAILED' | 'UNCERTAIN' | 'WAIVED';

export interface ConstraintCheckResult {
  constraint_name: string;
  status: ConstraintStatus;
  rule_code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface EligibilityResult {
  opportunity_id: string;
  user_id: string;
  status: EligibilityStatus;
  is_eligible: boolean;
  disqualification_reasons: string[];
  uncertainty_caveats: string[];
  constraint_checks: Record<string, ConstraintCheckResult>;
  evaluated_at: string;
}

export interface DuplicateRecord {
  duplicate_id: string;
  canonical_opportunity_id: string;
  duplicate_opportunity_id: string;
  similarity_score: number;
  similarity_method: 'EXACT_SHINGLE_JACCARD' | 'MINHASH_ESTIMATE';
  source_url: string;
  detected_at: string;
  reasons: string[];
}

export interface OpportunityCluster {
  canonical_opportunity: PolymorphicOpportunity;
  duplicate_records: DuplicateRecord[];
  all_source_urls: string[];
  cluster_size: number;
}

export interface DeduplicationResult {
  canonical_opportunities: PolymorphicOpportunity[];
  duplicate_opportunities: PolymorphicOpportunity[];
  duplicate_records: DuplicateRecord[];
  clusters: Record<string, OpportunityCluster>;
  total_evaluated: number;
  canonical_count: number;
  duplicate_count: number;
}

export interface PipelineEvaluationRequest {
  candidate_profile: CandidateCareerProfile;
  opportunities?: PolymorphicOpportunity[];
  deduplication_threshold?: number;
  reference_time?: string | null;
}

export interface PipelineEvaluationResponse {
  candidate_id: string;
  total_submitted: number;
  canonical_count: number;
  duplicate_count: number;
  eligible_canonical_count: number;
  uncertain_canonical_count: number;
  ineligible_canonical_count: number;
  canonical_opportunities: PolymorphicOpportunity[];
  eligible_opportunities: PolymorphicOpportunity[];
  duplicate_records: DuplicateRecord[];
  clusters: Record<string, OpportunityCluster>;
  eligibility_results: EligibilityResult[];
  execution_metadata: Record<string, unknown>;
}

export interface CandidateProfilingRequest {
  user_id: string;
  resume_text?: string | null;
  project_descriptions?: string[];
  work_experience_text?: string | null;
  explicit_skills?: string[];
  education_text?: string | null;
  target_roles?: string[];
  save_to_repository?: boolean;
}

export interface ExtractedEvidenceSnippet {
  source_type: EvidenceSourceType;
  exact_quote: string;
  verifiability_weight: number;
  context_label?: string | null;
}

export interface ExtractedSkillClaim {
  skill_name: string;
  canonical_skill_id: string;
  proficiency_score: number;
  confidence_score: number;
  evidence_snippets: ExtractedEvidenceSnippet[];
  is_explicitly_stated: boolean;
  last_practiced_date?: string | null;
}

export interface ExtractedWorkExperience {
  role_title: string;
  company_name: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current: boolean;
  responsibilities: string[];
  technologies_used: string[];
}

export interface ExtractedProject {
  project_name: string;
  description: string;
  technologies: string[];
  repository_url?: string | null;
}

export interface ExtractedEducation {
  institution_name: string;
  degree_level: DegreeLevel;
  field_of_study?: string | null;
  graduation_date?: string | null;
  is_enrolled: boolean;
}

export interface EpistemicUncertainties {
  ambiguities: string[];
  contradictions: string[];
  unsupported_claims: string[];
}

export interface CandidateProfilingResponse {
  user_id: string;
  profile_version: number;
  extracted_profile: CandidateCareerProfile;
  work_experiences: ExtractedWorkExperience[];
  projects: ExtractedProject[];
  education: ExtractedEducation[];
  stated_skills_count: number;
  inferred_skills_count: number;
  epistemic_uncertainties: EpistemicUncertainties;
  raw_evidence_count: number;
  is_persisted: boolean;
  metadata: {
    duration_ms: number;
    input_char_count: number;
    provider: string;
    [key: string]: unknown;
  };
}

export type ConnectorStatus =
  | 'CONNECTED'
  | 'MOCKED_FALLBACK'
  | 'UNAVAILABLE_MISSING_BINARY'
  | 'RATE_LIMITED'
  | 'ERROR';

export interface DiscoverySearchQuery {
  query_id: string;
  role_title: string;
  query_string: string;
  expanded_keywords: string[];
  category: OpportunityCategory;
  work_modes: WorkMode[];
  target_locations: string[];
  target_country_codes: string[];
  seniority_level: string;
  relationship_type: CareerPathRelationship;
}

export interface RoleMappingTarget {
  role_title: string;
  canonical_occupation_code: string;
  relationship_type: CareerPathRelationship;
  confidence_score: number;
  matched_skill_names: string[];
  missing_skill_names: string[];
  queries: DiscoverySearchQuery[];
}

export interface DiscoveryQueryPlan {
  candidate_id: string;
  target_roles: RoleMappingTarget[];
  all_queries: DiscoverySearchQuery[];
  generated_at: string;
  metadata: Record<string, unknown>;
}

export interface ConnectorHealthReport {
  connector_id: string;
  source_name: string;
  connector_type: string;
  status: ConnectorStatus;
  is_mock_fallback: boolean;
  details: Record<string, unknown>;
  last_checked: string;
}

export interface DiscoveryConnectorReport {
  connector_id: string;
  source_name: string;
  status: ConnectorStatus;
  raw_count: number;
  latency_ms: number;
  error_message?: string | null;
}

export interface DiscoveryRunRequest {
  candidate_profile?: CandidateCareerProfile | null;
  user_id?: string | null;
  connector_ids?: string[] | null;
  max_results_per_connector?: number;
  deduplication_threshold?: number;
  simulate_failure_connector?: string | null;
  persist_to_repository?: boolean;
}

export interface DiscoveryRunResponse {
  candidate_id: string;
  query_plan: DiscoveryQueryPlan;
  connector_reports: DiscoveryConnectorReport[];
  total_discovered: number;
  canonical_count: number;
  duplicate_count: number;
  eligible_count: number;
  uncertain_count: number;
  ineligible_count: number;
  canonical_opportunities: PolymorphicOpportunity[];
  eligible_opportunities: PolymorphicOpportunity[];
  duplicate_clusters: Record<string, OpportunityCluster>;
  duplicate_records: DuplicateRecord[];
  eligibility_results: EligibilityResult[];
  execution_metadata: Record<string, unknown>;
}




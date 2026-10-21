'use client';

import React, { useState } from 'react';
import {
  CandidateCareerProfile,
  CareerPathRelationship,
  DegreeLevel,
  EvidenceSourceType,
  OpportunityCategory,
  PolymorphicOpportunity,
  RankingDimension,
  RankingRequest,
  RankingResponse,
  WorkMode,
} from '@/types/domain';
import { evaluateAndRankOpportunities } from '@/lib/api';

const SAMPLE_CANDIDATES: Record<string, { label: string; description: string; profile: CandidateCareerProfile }> = {
  maya: {
    label: 'Maya Chen — Junior Backend Engineer (US)',
    description: '18 months experience, US Citizen, Bachelors CS. Verified skills: Python 8.5, FastAPI 8.0, PostgreSQL 7.5, Docker 6.5. Target: Backend Software Engineer.',
    profile: {
      user_id: 'maya-chen-junior',
      profile_version: 1,
      assessed_skills: [
        {
          canonical_skill_id: 'esco:python',
          skill_name: 'Python',
          proficiency_score: 8.5,
          confidence_score: 0.92,
          evidence_records: [
            {
              evidence_id: 'ev-m-1',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Built async microservices in Python with FastAPI and PostgreSQL.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.90,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:fastapi',
          skill_name: 'FastAPI',
          proficiency_score: 8.0,
          confidence_score: 0.90,
          evidence_records: [
            {
              evidence_id: 'ev-m-2',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Architected REST endpoints handling 5,000 req/sec.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.90,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:postgresql',
          skill_name: 'PostgreSQL',
          proficiency_score: 7.5,
          confidence_score: 0.85,
          evidence_records: [
            {
              evidence_id: 'ev-m-3',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Designed relational schemas and indexed queries.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:docker',
          skill_name: 'Docker',
          proficiency_score: 6.5,
          confidence_score: 0.80,
          evidence_records: [
            {
              evidence_id: 'ev-m-4',
              source_type: 'RESUME_PROJECT' as EvidenceSourceType,
              extracted_snippet: 'Containerized microservices for local deployment.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.80,
            },
          ],
        },
      ],
      target_career_paths: [
        {
          occupation_code: '15-1252.00',
          title: 'Backend Software Engineer',
          relationship_type: 'TARGET' as CareerPathRelationship,
          adjacency_similarity: 1.0,
          missing_core_skill_ids: [],
        },
      ],
      adjacent_career_paths: [
        {
          occupation_code: '15-1251.00',
          title: 'Data Platform Engineer',
          relationship_type: 'ADJACENT' as CareerPathRelationship,
          adjacency_similarity: 0.80,
          missing_core_skill_ids: ['esco:apache-spark'],
        },
      ],
      eligibility_constraints: {
        authorized_country_codes: ['US'],
        requires_visa_sponsorship: false,
        highest_degree_level: 'BACHELORS' as DegreeLevel,
        is_currently_enrolled_student: false,
        expected_graduation_date: null,
        total_full_time_experience_months: 18,
        allowed_opportunity_categories: ['FULL_TIME_JOB' as OpportunityCategory],
        allowed_work_modes: ['REMOTE' as WorkMode, 'HYBRID' as WorkMode],
        preferred_locations: ['San Francisco, US'],
      },
      overall_profile_confidence: 0.88,
    },
  },
  priyansh: {
    label: 'Priyansh Sharma — Student Intern (India)',
    description: 'B.Tech pre-final year, India Authorized. Python 7.5, PyTorch 7.0, SQL 6.8. Target: Software Developer / ML Intern.',
    profile: {
      user_id: 'priyansh-student-in',
      profile_version: 1,
      assessed_skills: [
        {
          canonical_skill_id: 'esco:python',
          skill_name: 'Python',
          proficiency_score: 7.5,
          confidence_score: 0.85,
          evidence_records: [
            {
              evidence_id: 'ev-p-1',
              source_type: 'RESUME_PROJECT' as EvidenceSourceType,
              extracted_snippet: 'Developed full stack testing toolkit in Python.',
              observed_at: '2026-02-01T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:react',
          skill_name: 'React',
          proficiency_score: 7.0,
          confidence_score: 0.80,
          evidence_records: [
            {
              evidence_id: 'ev-p-2',
              source_type: 'RESUME_PROJECT' as EvidenceSourceType,
              extracted_snippet: 'Constructed responsive event portal in React.',
              observed_at: '2026-02-01T00:00:00Z',
              verifiability_weight: 0.80,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:sql',
          skill_name: 'SQL',
          proficiency_score: 6.8,
          confidence_score: 0.78,
          evidence_records: [
            {
              evidence_id: 'ev-p-3',
              source_type: 'ACADEMIC_TRANSCRIPT' as EvidenceSourceType,
              extracted_snippet: 'Database Management Systems coursework (Grade: A).',
              observed_at: '2025-11-15T00:00:00Z',
              verifiability_weight: 0.78,
            },
          ],
        },
      ],
      target_career_paths: [
        {
          occupation_code: '15-1252.00',
          title: 'Software Developer',
          relationship_type: 'TARGET' as CareerPathRelationship,
          adjacency_similarity: 1.0,
          missing_core_skill_ids: [],
        },
      ],
      adjacent_career_paths: [],
      eligibility_constraints: {
        authorized_country_codes: ['IN'],
        requires_visa_sponsorship: false,
        highest_degree_level: 'HIGH_SCHOOL' as DegreeLevel,
        is_currently_enrolled_student: true,
        expected_graduation_date: '2026-06-30',
        total_full_time_experience_months: 0,
        allowed_opportunity_categories: [
          'INTERNSHIP' as OpportunityCategory,
          'FULL_TIME_JOB' as OpportunityCategory,
        ],
        allowed_work_modes: ['REMOTE' as WorkMode, 'HYBRID' as WorkMode, 'ON_SITE' as WorkMode],
        preferred_locations: ['Bengaluru, India', 'Pune, India'],
      },
      overall_profile_confidence: 0.82,
    },
  },
};

const SAMPLE_OPPORTUNITIES: PolymorphicOpportunity[] = [
  {
    opportunity_id: 'opp-ideal-backend',
    minhash_signature_hex: 'a1b2c3d4e5f60718' + 'a1b2c3d4e5f60718',
    title: 'Junior Backend Engineer (Python / FastAPI)',
    company_name: 'CloudScale Systems',
    company_domain_verified: true,
    mapped_occupation_code: '15-1252.00',
    eligibility_rules: {
      opportunity_category: 'FULL_TIME_JOB' as OpportunityCategory,
      eligible_country_codes: ['US'],
      sponsors_work_visa: false,
      minimum_degree_required: 'BACHELORS' as DegreeLevel,
      requires_active_student_status: false,
      min_experience_months: 12,
      max_experience_months: 36,
      work_mode: 'REMOTE' as WorkMode,
      location_city_country: ['San Francisco, US'],
      application_deadline: '2026-11-30T23:59:59Z',
    },
    skill_requirements: [
      {
        canonical_skill_id: 'esco:python',
        skill_name: 'Python',
        is_mandatory: true,
        minimum_proficiency_expected: 7.0,
      },
      {
        canonical_skill_id: 'esco:fastapi',
        skill_name: 'FastAPI',
        is_mandatory: true,
        minimum_proficiency_expected: 7.0,
      },
      {
        canonical_skill_id: 'esco:postgresql',
        skill_name: 'PostgreSQL',
        is_mandatory: false,
        minimum_proficiency_expected: 6.5,
      },
    ],
    category_specific_attributes: {
      compensation_range: '$95,000 - $115,000',
    },
    sanitized_summary: 'Seeking junior backend engineer to build scalable REST services using Python and FastAPI.',
    source_url: 'https://boards.greenhouse.io/cloudscale/jobs/101',
    posted_at: '2026-10-15T00:00:00Z',
    discovered_at: '2026-10-21T00:00:00Z',
    completeness_score: 0.95,
    trust_score: 0.90,
    is_duplicate: false,
  },
  {
    opportunity_id: 'opp-growth-backend',
    minhash_signature_hex: 'b2c3d4e5f6071829' + 'b2c3d4e5f6071829',
    title: 'Backend Systems Engineer',
    company_name: 'Apex Data Labs',
    company_domain_verified: true,
    mapped_occupation_code: '15-1252.00',
    eligibility_rules: {
      opportunity_category: 'FULL_TIME_JOB' as OpportunityCategory,
      eligible_country_codes: ['US'],
      sponsors_work_visa: false,
      minimum_degree_required: 'BACHELORS' as DegreeLevel,
      requires_active_student_status: false,
      min_experience_months: 12,
      max_experience_months: 48,
      work_mode: 'HYBRID' as WorkMode,
      location_city_country: ['San Francisco, US'],
      application_deadline: '2026-12-15T23:59:59Z',
    },
    skill_requirements: [
      {
        canonical_skill_id: 'esco:python',
        skill_name: 'Python',
        is_mandatory: true,
        minimum_proficiency_expected: 7.5,
      },
      {
        canonical_skill_id: 'esco:docker',
        skill_name: 'Docker',
        is_mandatory: true,
        minimum_proficiency_expected: 6.0,
      },
      {
        canonical_skill_id: 'esco:kubernetes',
        skill_name: 'Kubernetes',
        is_mandatory: false,
        minimum_proficiency_expected: 5.5,
      },
      {
        canonical_skill_id: 'esco:redis',
        skill_name: 'Redis',
        is_mandatory: false,
        minimum_proficiency_expected: 5.5,
      },
    ],
    category_specific_attributes: {
      compensation_range: '$100,000 - $125,000',
    },
    sanitized_summary: 'Grow your distributed systems engineering skills with Python, Docker, Redis, and Kubernetes orchestration.',
    source_url: 'https://jobs.lever.co/apexdata/202',
    posted_at: '2026-10-18T00:00:00Z',
    discovered_at: '2026-10-21T00:00:00Z',
    completeness_score: 0.92,
    trust_score: 0.88,
    is_duplicate: false,
  },
  {
    opportunity_id: 'opp-adjacent-data-eng',
    minhash_signature_hex: 'c3d4e5f60718293a' + 'c3d4e5f60718293a',
    title: 'Junior Data Platform Engineer',
    company_name: 'Quantico Metrics',
    company_domain_verified: true,
    mapped_occupation_code: '15-1251.00',
    eligibility_rules: {
      opportunity_category: 'FULL_TIME_JOB' as OpportunityCategory,
      eligible_country_codes: ['US'],
      sponsors_work_visa: false,
      minimum_degree_required: 'BACHELORS' as DegreeLevel,
      requires_active_student_status: false,
      min_experience_months: 6,
      max_experience_months: 36,
      work_mode: 'REMOTE' as WorkMode,
      location_city_country: ['San Francisco, US'],
      application_deadline: '2026-12-01T23:59:59Z',
    },
    skill_requirements: [
      {
        canonical_skill_id: 'esco:python',
        skill_name: 'Python',
        is_mandatory: true,
        minimum_proficiency_expected: 7.0,
      },
      {
        canonical_skill_id: 'esco:postgresql',
        skill_name: 'PostgreSQL',
        is_mandatory: true,
        minimum_proficiency_expected: 7.0,
      },
      {
        canonical_skill_id: 'esco:apache-spark',
        skill_name: 'Apache Spark',
        is_mandatory: false,
        minimum_proficiency_expected: 5.0,
      },
    ],
    category_specific_attributes: {
      compensation_range: '$90,000 - $110,000',
    },
    sanitized_summary: 'Adjacent career opportunity building automated ETL data pipelines in Python and relational warehouses.',
    source_url: 'https://jobs.ashbyhq.com/quanticometrics/303',
    posted_at: '2026-10-12T00:00:00Z',
    discovered_at: '2026-10-21T00:00:00Z',
    completeness_score: 0.88,
    trust_score: 0.85,
    is_duplicate: false,
  },
  {
    opportunity_id: 'opp-uncertain-rolling',
    minhash_signature_hex: 'd4e5f60718293a4b' + 'd4e5f60718293a4b',
    title: 'Python API Developer (Rolling Admissions)',
    company_name: 'FinTech Stream',
    company_domain_verified: false,
    mapped_occupation_code: '15-1252.00',
    eligibility_rules: {
      opportunity_category: 'FULL_TIME_JOB' as OpportunityCategory,
      eligible_country_codes: ['US'],
      sponsors_work_visa: false,
      minimum_degree_required: 'BACHELORS' as DegreeLevel,
      requires_active_student_status: false,
      min_experience_months: 12,
      work_mode: 'REMOTE' as WorkMode,
      location_city_country: ['Remote, US'],
      application_deadline: null, // Rolling deadline
    },
    skill_requirements: [
      {
        canonical_skill_id: 'esco:python',
        skill_name: 'Python',
        is_mandatory: true,
        minimum_proficiency_expected: 7.0,
      },
      {
        canonical_skill_id: 'esco:fastapi',
        skill_name: 'FastAPI',
        is_mandatory: true,
        minimum_proficiency_expected: 6.5,
      },
    ],
    category_specific_attributes: {},
    sanitized_summary: 'Fast-moving fintech startup looking for API developers. Rolling recruitment process.',
    source_url: 'https://example.com/jobs/fintech/404',
    posted_at: '2026-10-19T00:00:00Z',
    discovered_at: '2026-10-21T00:00:00Z',
    completeness_score: 0.70,
    trust_score: 0.72,
    is_duplicate: false,
  },
  {
    opportunity_id: 'opp-ineligible-foreign-visa',
    minhash_signature_hex: 'e5f60718293a4b5c' + 'e5f60718293a4b5c',
    title: 'Python Backend Developer (UK On-site, No Visa)',
    company_name: 'London Tech Works',
    company_domain_verified: true,
    mapped_occupation_code: '15-1252.00',
    eligibility_rules: {
      opportunity_category: 'FULL_TIME_JOB' as OpportunityCategory,
      eligible_country_codes: ['GB'],
      sponsors_work_visa: false, // Strict violation for US candidate!
      minimum_degree_required: 'BACHELORS' as DegreeLevel,
      requires_active_student_status: false,
      min_experience_months: 12,
      work_mode: 'ON_SITE' as WorkMode,
      location_city_country: ['London, UK'],
      application_deadline: '2026-11-20T00:00:00Z',
    },
    skill_requirements: [
      {
        canonical_skill_id: 'esco:python',
        skill_name: 'Python',
        is_mandatory: true,
        minimum_proficiency_expected: 8.0,
      },
      {
        canonical_skill_id: 'esco:fastapi',
        skill_name: 'FastAPI',
        is_mandatory: true,
        minimum_proficiency_expected: 7.5,
      },
    ],
    category_specific_attributes: {},
    sanitized_summary: 'On-site London software engineer role. Must possess existing British right to work.',
    source_url: 'https://example.co.uk/jobs/505',
    posted_at: '2026-10-15T00:00:00Z',
    discovered_at: '2026-10-21T00:00:00Z',
    completeness_score: 0.90,
    trust_score: 0.92,
    is_duplicate: false,
  },
];

export function RecommendationDemo() {
  const [selectedCandidate, setSelectedCandidate] = useState<string>('maya');
  const [weightProfile, setWeightProfile] = useState<string>('DEFAULT');
  const [topK, setTopK] = useState<number>(5);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [response, setResponse] = useState<RankingResponse | null>(null);
  const [expandedOpportunityId, setExpandedOpportunityId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'ranked' | 'breakdown' | 'excluded'>('ranked');

  const currentCandidate = SAMPLE_CANDIDATES[selectedCandidate];

  async function handleEvaluateAndRank() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const payload: RankingRequest = {
        candidate_profile: currentCandidate.profile,
        user_id: currentCandidate.profile.user_id,
        opportunities: SAMPLE_OPPORTUNITIES,
        weight_profile_name: weightProfile,
        include_ineligible_in_audit: true,
        top_k: topK,
      };

      const res = await evaluateAndRankOpportunities(payload);
      setResponse(res);
      if (res.ranked_recommendations.length > 0) {
        setExpandedOpportunityId(res.ranked_recommendations[0].opportunity.opportunity_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Ranking evaluation failed';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }

  function getDimensionLabel(dim: RankingDimension): string {
    switch (dim) {
      case 'SKILL_ALIGNMENT':
        return 'Skill Alignment (S_skill)';
      case 'CAREER_ALIGNMENT':
        return 'Career Path Fit (S_career)';
      case 'GROWTH_POTENTIAL':
        return 'Growth Potential (S_growth)';
      case 'MARKET_RELEVANCE':
        return 'Market Credibility (S_market)';
      case 'PREFERENCE_FIT':
        return 'Preference Fit (S_pref)';
      case 'QUALIFICATION_FIT':
        return 'Experience & Degree (S_qual)';
    }
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden text-zinc-900">
      {/* Header Banner */}
      <div className="bg-zinc-900 text-white p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Milestone 9
              </span>
              <span className="text-xs text-zinc-400">Evidence-Grounded Candidate–Job Fit Scoring</span>
            </div>
            <h3 className="text-xl font-bold tracking-tight mt-1 text-white">
              Multi-Dimensional Recommendation Engine
            </h3>
            <p className="text-xs text-zinc-300 mt-1 max-w-2xl">
              Calculates personalized candidate–job recommendations across 6 explicit dimensions.
              Hard eligibility is strictly preserved: disqualified opportunities are quarantined from recommendations
              regardless of skill scores.
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium border border-zinc-700 bg-zinc-800 text-zinc-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Deterministic Primacy
            </span>
          </div>
        </div>
      </div>

      <div className="p-6 sm:p-8 space-y-8">
        {/* Error Banner */}
        {errorMessage && (
          <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-start gap-3">
            <span className="font-bold text-rose-600">Error:</span>
            <div className="flex-1 leading-relaxed">{errorMessage}</div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-500 hover:text-rose-700 font-bold ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {/* Section 1: Candidate Profile & Weight Profile Selection */}
        <div className="space-y-4">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
            1. Select Candidate Profile & Scoring Weights Configuration
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(SAMPLE_CANDIDATES).map(([key, item]) => {
              const isSelected = selectedCandidate === key;
              return (
                <div
                  key={key}
                  onClick={() => setSelectedCandidate(key)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    isSelected
                      ? 'border-emerald-600 bg-emerald-50/30 ring-1 ring-emerald-600'
                      : 'border-zinc-200 bg-white hover:border-zinc-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-900">{item.label}</span>
                    {isSelected && (
                      <span className="text-[10px] uppercase font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-600 mt-1.5 leading-relaxed">{item.description}</p>
                </div>
              );
            })}
          </div>

          <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <label htmlFor="weightProfileSelect" className="text-xs font-semibold text-zinc-700">Weight Profile:</label>
              <select
                id="weightProfileSelect"
                value={weightProfile}
                onChange={(e) => setWeightProfile(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs text-zinc-900 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                <option value="DEFAULT">Default Baseline (Skill 30%, Career 20%, Growth 20%, Market 12%, Pref 10%, Qual 8%)</option>
                <option value="EARLY_CAREER">Early Career Profile (Growth 28%, Skill 25%, Career 20%, Market 12%, Pref 10%, Qual 5%)</option>
                <option value="EXPERIENCED">Experienced Lateral (Skill 35%, Career 20%, Growth 15%, Market 10%, Pref 10%, Qual 10%)</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-zinc-600">Top Recommendations:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="px-2 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs font-mono text-zinc-900"
              >
                <option value={3}>Top 3</option>
                <option value={5}>Top 5</option>
                <option value={10}>Top 10</option>
              </select>
            </div>

            <button
              onClick={handleEvaluateAndRank}
              disabled={isLoading}
              className="px-5 py-2.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm disabled:opacity-50 flex items-center gap-2 self-start sm:self-auto"
            >
              {isLoading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Computing Multi-Dimensional Scores...</span>
                </>
              ) : (
                <>
                  <span>★</span>
                  <span>Calculate Candidate Fit & Order Recommendations</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {response && (
          <div className="space-y-6 pt-4 border-t border-zinc-200">
            {/* Top Summary Banner */}
            <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-4">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border-b border-zinc-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-zinc-900">Ranking Evaluation Run</span>
                    <span className="text-xs font-mono text-zinc-400">
                      ID: {response.evaluation_id.slice(0, 16)}...
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-zinc-500">Candidate: {response.candidate_id}</span>
                    <span className="text-zinc-300">•</span>
                    <span className="text-xs text-zinc-500">Model: {response.model_version}</span>
                    <span className="text-zinc-300">•</span>
                    <span className="text-xs text-zinc-500">Profile: {response.weight_profile_used}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500">Eligible Ranked:</span>
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {response.total_eligible_ranked} Qualified
                  </span>
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
                    {response.total_ineligible_excluded} Disqualified
                  </span>
                </div>
              </div>

              {/* Weight Visualizer */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                  Active Dimension Weights (Sum = 100%)
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                  {Object.entries(response.weights).map(([dim, wt]) => (
                    <div key={dim} className="p-2 rounded-lg bg-zinc-50 border border-zinc-200 text-center text-xs">
                      <div className="text-[10px] uppercase font-semibold text-zinc-500 truncate">
                        {dim.replace('_ALIGNMENT', '').replace('_FIT', '').replace('_RELEVANCE', '')}
                      </div>
                      <div className="text-sm font-bold text-zinc-800 mt-0.5">
                        {Math.round(wt * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="border-b border-zinc-200 flex items-center gap-4 text-xs font-semibold">
              <button
                onClick={() => setActiveTab('ranked')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'ranked'
                    ? 'border-emerald-600 text-emerald-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Top Recommendations ({response.ranked_recommendations.length})
              </button>
              <button
                onClick={() => setActiveTab('breakdown')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'breakdown'
                    ? 'border-emerald-600 text-emerald-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Comparative Dimension Scores
              </button>
              <button
                onClick={() => setActiveTab('excluded')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'excluded'
                    ? 'border-emerald-600 text-emerald-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Excluded Disqualified Listings ({response.excluded_ineligible.length})
              </button>
            </div>

            {/* Tab 1: Top Recommendations */}
            {activeTab === 'ranked' && (
              <div className="space-y-4">
                {response.ranked_recommendations.length === 0 ? (
                  <div className="p-8 text-center rounded-xl border border-dashed border-zinc-300 text-xs text-zinc-500">
                    No eligible opportunities passed deterministic qualification checks.
                  </div>
                ) : (
                  response.ranked_recommendations.map((rec) => {
                    const isExpanded = expandedOpportunityId === rec.opportunity.opportunity_id;
                    const fitPercent = Math.round(rec.overall_fit_score * 100);

                    return (
                      <div
                        key={rec.opportunity.opportunity_id}
                        className={`p-5 rounded-xl border transition ${
                          rec.rank === 1
                            ? 'border-emerald-500/40 bg-white shadow-sm ring-1 ring-emerald-500/20'
                            : 'border-zinc-200 bg-white'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-emerald-100/60 text-emerald-800 font-bold text-xs flex items-center justify-center shrink-0">
                              #{rec.rank}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-zinc-900">{rec.opportunity.title}</h4>
                                <span
                                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                    rec.eligibility_status === 'ELIGIBLE'
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                      : 'bg-sky-50 text-sky-700 border-sky-200'
                                  }`}
                                >
                                  {rec.eligibility_status}
                                </span>
                              </div>
                              <div className="text-xs text-zinc-600 mt-0.5">
                                <span className="font-semibold text-zinc-800">{rec.opportunity.company_name}</span> •{' '}
                                {rec.opportunity.eligibility_rules.location_city_country.join(', ')} ({rec.opportunity.eligibility_rules.work_mode})
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 self-start sm:self-auto">
                            <div className="text-right">
                              <div className="text-xl font-extrabold text-emerald-700">{fitPercent}%</div>
                              <div className="text-[10px] text-zinc-400 font-medium">Candidate Fit</div>
                            </div>
                            <button
                              onClick={() =>
                                setExpandedOpportunityId(isExpanded ? null : rec.opportunity.opportunity_id)
                              }
                              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-100 hover:bg-zinc-200 text-zinc-700 transition"
                            >
                              {isExpanded ? 'Hide Details' : 'View Breakdown'}
                            </button>
                          </div>
                        </div>

                        {/* Grounded Recommendation Rationale */}
                        <div className="mt-3 p-3 rounded-lg bg-emerald-50/30 border border-emerald-100 text-xs text-zinc-700 leading-relaxed font-sans">
                          <span className="font-semibold text-emerald-900">Why Recommended: </span>
                          {rec.recommendation_rationale}
                        </div>

                        {/* Matched Skills with Evidence Snippets */}
                        <div className="mt-3 space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                            Verified Skills Grounded in Candidate Evidence
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {rec.matched_skills.map((m, idx) => (
                              <div
                                key={idx}
                                className="px-2.5 py-1 rounded-lg bg-zinc-50 border border-zinc-200 text-xs flex items-center gap-1.5"
                              >
                                <span className="font-semibold text-zinc-800">{m.skill_name}</span>
                                <span className="text-[10px] font-mono text-emerald-700 font-bold">
                                  {m.candidate_proficiency.toFixed(1)}/10
                                </span>
                                {m.evidence_snippets.length > 0 && (
                                  <span className="text-[10px] text-zinc-400" title={m.evidence_snippets[0]}>
                                    (Verified)
                                  </span>
                                )}
                              </div>
                            ))}
                            {rec.missing_skills.map((gap, idx) => (
                              <div
                                key={idx}
                                className="px-2.5 py-1 rounded-lg bg-amber-50/50 border border-amber-200 text-xs flex items-center gap-1.5 text-amber-800"
                              >
                                <span>{gap.skill_name}</span>
                                <span className="text-[10px] font-mono font-medium">
                                  ({gap.is_mandatory ? 'Missing Required' : 'Unverified Preferred'})
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Expandable 6-Dimension Audit Breakdown */}
                        {isExpanded && (
                          <div className="mt-4 pt-4 border-t border-zinc-100 space-y-4">
                            <span className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                              Detailed 6-Dimension Score Audit
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                              {Object.entries(rec.dimension_scores).map(([dim, score]) => (
                                <div key={dim} className="p-3 rounded-lg border border-zinc-200 bg-zinc-50/50 space-y-1">
                                  <div className="flex items-center justify-between font-semibold">
                                    <span className="text-zinc-800">{getDimensionLabel(dim as RankingDimension)}</span>
                                    <span className="font-mono text-emerald-700 font-bold">
                                      {Math.round(score.raw_score * 100)}% (wt: {Math.round(score.weight * 100)}%)
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-zinc-600 leading-normal">{score.rationale}</p>
                                </div>
                              ))}
                            </div>

                            {/* Tradeoffs and Caveats */}
                            {rec.key_tradeoffs_or_risks.length > 0 && (
                              <div className="p-3 rounded-lg bg-amber-50/40 border border-amber-200 text-xs text-amber-800 space-y-1">
                                <span className="font-bold text-amber-900">Considerations & Verification Caveats:</span>
                                <ul className="list-disc list-inside space-y-0.5 pl-1 text-[11px]">
                                  {rec.key_tradeoffs_or_risks.map((t, idx) => (
                                    <li key={idx}>{t}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Source and Application Links */}
                            <div className="flex items-center justify-between text-xs pt-1">
                              <span className="text-[10px] font-mono text-zinc-400">
                                Mapped Code: {rec.opportunity.mapped_occupation_code}
                              </span>
                              <div className="flex items-center gap-3">
                                <a
                                  href={rec.opportunity.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-emerald-700 hover:text-emerald-900 font-semibold underline"
                                >
                                  View Source Listing ↗
                                </a>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Tab 2: Comparative Dimension Scores */}
            {activeTab === 'breakdown' && (
              <div className="p-4 rounded-xl border border-zinc-200 bg-white space-y-4">
                <div className="text-xs text-zinc-500">
                  Compare how each recommended role scored across the 6 dimensions to understand ranking differentiation.
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-zinc-200 text-zinc-400 font-semibold uppercase text-[10px]">
                        <th className="py-2.5 px-3">Opportunity</th>
                        <th className="py-2.5 px-3 text-right">Overall Fit</th>
                        <th className="py-2.5 px-3 text-right">Skill (30%)</th>
                        <th className="py-2.5 px-3 text-right">Career (20%)</th>
                        <th className="py-2.5 px-3 text-right">Growth (20%)</th>
                        <th className="py-2.5 px-3 text-right">Market (12%)</th>
                        <th className="py-2.5 px-3 text-right">Pref (10%)</th>
                        <th className="py-2.5 px-3 text-right">Qual (8%)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 font-mono">
                      {response.ranked_recommendations.map((rec) => (
                        <tr key={rec.opportunity.opportunity_id} className="hover:bg-zinc-50">
                          <td className="py-2.5 px-3 font-sans font-medium text-zinc-800">
                            #{rec.rank} {rec.opportunity.title}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-emerald-700">
                            {Math.round(rec.overall_fit_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-600">
                            {Math.round(rec.dimension_scores.SKILL_ALIGNMENT.raw_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-600">
                            {Math.round(rec.dimension_scores.CAREER_ALIGNMENT.raw_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-600">
                            {Math.round(rec.dimension_scores.GROWTH_POTENTIAL.raw_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-600">
                            {Math.round(rec.dimension_scores.MARKET_RELEVANCE.raw_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-600">
                            {Math.round(rec.dimension_scores.PREFERENCE_FIT.raw_score * 100)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-zinc-600">
                            {Math.round(rec.dimension_scores.QUALIFICATION_FIT.raw_score * 100)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tab 3: Excluded Disqualified Listings */}
            {activeTab === 'excluded' && (
              <div className="p-4 rounded-xl border border-zinc-200 bg-white space-y-4">
                <div className="text-xs text-zinc-500">
                  Authoritative Determinism Invariant: Disqualified opportunities are quarantined from recommendations
                  regardless of semantic skill overlap.
                </div>
                {response.excluded_ineligible.length === 0 ? (
                  <div className="p-6 text-center text-xs text-zinc-400">
                    No opportunities were disqualified by hard eligibility rules.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {response.excluded_ineligible.map((item, idx) => (
                      <div key={idx} className="p-3.5 rounded-lg border border-rose-200 bg-rose-50/20 text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-zinc-900">{item.title as string}</span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200">
                            DISQUALIFIED
                          </span>
                        </div>
                        <div className="text-zinc-600">
                          Company: <span className="font-medium text-zinc-800">{item.company_name as string}</span>
                        </div>
                        <div className="text-[11px] text-rose-700 font-mono">
                          Hard Rule Violations: {(item.disqualification_reasons as string[]).join(', ')}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

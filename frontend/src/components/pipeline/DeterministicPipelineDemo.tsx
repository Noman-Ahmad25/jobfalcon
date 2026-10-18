'use client';

import React, { useState } from 'react';
import { evaluateOpportunitiesPipeline, ApiError } from '@/lib/api';
import {
  PipelineEvaluationRequest,
  PipelineEvaluationResponse,
} from '@/types/domain';

const SYNTHETIC_DEMO_REQUEST: PipelineEvaluationRequest = {
  candidate_profile: {
    user_id: 'usr-demo-001',
    profile_version: 1,
    assessed_skills: [
      {
        canonical_skill_id: 'esco:skill:python',
        skill_name: 'Python',
        proficiency_score: 8.0,
        confidence_score: 0.92,
        evidence_records: [
          {
            evidence_id: 'ev-demo-01',
            source_type: 'RESUME_WORK_EXPERIENCE',
            extracted_snippet: 'Built high-throughput FastAPI microservices and PostgreSQL schemas.',
            observed_at: '2026-01-15T00:00:00Z',
            verifiability_weight: 0.95,
          },
        ],
      },
    ],
    target_career_paths: [
      {
        occupation_code: '2512.1',
        title: 'Backend Software Engineer',
        relationship_type: 'TARGET',
        adjacency_similarity: 1.0,
        missing_core_skill_ids: ['esco:skill:kubernetes'],
      },
    ],
    adjacent_career_paths: [],
    eligibility_constraints: {
      authorized_country_codes: ['US'],
      requires_visa_sponsorship: false,
      highest_degree_level: 'BACHELORS',
      is_currently_enrolled_student: false,
      expected_graduation_date: '2024-05-15',
      total_full_time_experience_months: 24,
      allowed_opportunity_categories: ['FULL_TIME_JOB'],
      allowed_work_modes: ['HYBRID', 'REMOTE'],
      preferred_locations: ['San Francisco, CA'],
    },
    overall_profile_confidence: 0.92,
  },
  opportunities: [
    {
      opportunity_id: 'opp-gh-101',
      minhash_signature_hex: '0'.repeat(64),
      title: 'Backend Software Engineer',
      company_name: 'Apex Systems',
      company_domain_verified: true,
      mapped_occupation_code: '2512.1',
      eligibility_rules: {
        opportunity_category: 'FULL_TIME_JOB',
        eligible_country_codes: ['US'],
        sponsors_work_visa: false,
        minimum_degree_required: 'BACHELORS',
        requires_active_student_status: false,
        min_experience_months: 12,
        work_mode: 'HYBRID',
        location_city_country: ['San Francisco, CA'],
        application_deadline: '2027-01-01T00:00:00Z',
      },
      skill_requirements: [
        {
          canonical_skill_id: 'esco:skill:python',
          skill_name: 'Python',
          is_mandatory: true,
          minimum_proficiency_expected: 7.0,
        },
      ],
      category_specific_attributes: {},
      sanitized_summary:
        'Apex Systems is hiring a Backend Software Engineer to design, implement, and maintain scalable cloud services. In this role, you will work with cross-functional teams of frontend engineers and product managers to deliver high-performance microservices and RESTful APIs using Python, FastAPI, and PostgreSQL.',
      source_url: 'https://boards.greenhouse.io/apex/jobs/101',
      posted_at: '2026-01-01T00:00:00Z',
      discovered_at: '2026-10-18T00:00:00Z',
      completeness_score: 0.95,
      trust_score: 0.98,
      is_duplicate: false,
    },
    {
      opportunity_id: 'opp-lever-202',
      minhash_signature_hex: '0'.repeat(64),
      title: 'Backend Software Engineer',
      company_name: 'Apex Systems',
      company_domain_verified: true,
      mapped_occupation_code: '2512.1',
      eligibility_rules: {
        opportunity_category: 'FULL_TIME_JOB',
        eligible_country_codes: ['US'],
        sponsors_work_visa: false,
        minimum_degree_required: 'BACHELORS',
        requires_active_student_status: false,
        min_experience_months: 12,
        work_mode: 'HYBRID',
        location_city_country: ['San Francisco, CA'],
        application_deadline: '2027-01-01T00:00:00Z',
      },
      skill_requirements: [],
      category_specific_attributes: {},
      sanitized_summary:
        'Apex Systems is hiring a Backend Software Engineer to design, implement, and maintain scalable cloud services. In this role, you will work with cross-functional teams of frontend engineers and product managers to deliver high-performance microservices and RESTful APIs using Python, FastAPI, and PostgreSQL. Apply via Lever ATS career portal.',
      source_url: 'https://jobs.lever.co/apex/jobs/202',
      posted_at: '2026-01-01T00:00:00Z',
      discovered_at: '2026-10-18T00:00:00Z',
      completeness_score: 0.92,
      trust_score: 0.95,
      is_duplicate: false,
    },
    {
      opportunity_id: 'opp-robotics-303',
      minhash_signature_hex: '0'.repeat(64),
      title: 'Principal Autonomous Systems Scientist',
      company_name: 'Berlin Robotics AG',
      company_domain_verified: true,
      mapped_occupation_code: '2166.1',
      eligibility_rules: {
        opportunity_category: 'FULL_TIME_JOB',
        eligible_country_codes: ['DE'],
        sponsors_work_visa: false,
        minimum_degree_required: 'DOCTORATE',
        requires_active_student_status: false,
        min_experience_months: 60,
        work_mode: 'ON_SITE',
        location_city_country: ['Berlin, Germany'],
        application_deadline: '2026-12-31T00:00:00Z',
      },
      skill_requirements: [],
      category_specific_attributes: {},
      sanitized_summary:
        'Lead fundamental algorithmic research for autonomous robotics manipulation. Candidates must possess a Ph.D. in Robotics or Control Theory and be authorized to work in Germany.',
      source_url: 'https://berlinrobotics.example.de/jobs/303',
      posted_at: '2026-01-01T00:00:00Z',
      discovered_at: '2026-10-18T00:00:00Z',
      completeness_score: 0.90,
      trust_score: 0.90,
      is_duplicate: false,
    },
  ],
  deduplication_threshold: 0.85,
};

export function DeterministicPipelineDemo() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PipelineEvaluationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await evaluateOpportunitiesPipeline(SYNTHETIC_DEMO_REQUEST);
      setResult(response);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to execute pipeline demo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-base font-semibold text-zinc-900">
            Deterministic Pipeline Integration Demo
          </h3>
          <p className="text-xs text-zinc-500 mt-1">
            Evaluates synthetic candidate profile against 3 opportunities: 1 canonical eligible role, 1 syndicated Lever duplicate, and 1 ineligible role.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRunDemo}
          disabled={loading}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-xs font-medium rounded-lg text-white bg-zinc-900 hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-900 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Evaluating Pipeline...' : 'Run Deterministic Pipeline'}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
          <p className="font-semibold">Pipeline Error:</p>
          <p className="mt-0.5">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-6 pt-2">
          {/* Summary Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-center">
              <span className="block text-xs text-zinc-500 font-medium">Submitted</span>
              <span className="text-lg font-bold text-zinc-900">{result.total_submitted}</span>
            </div>
            <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-center">
              <span className="block text-xs text-zinc-500 font-medium">Canonical (Distinct)</span>
              <span className="text-lg font-bold text-zinc-900">{result.canonical_count}</span>
            </div>
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-center">
              <span className="block text-xs text-amber-700 font-medium">Duplicates Clustered</span>
              <span className="text-lg font-bold text-amber-900">{result.duplicate_count}</span>
            </div>
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-center">
              <span className="block text-xs text-emerald-700 font-medium">Eligible Canonical</span>
              <span className="text-lg font-bold text-emerald-900">{result.eligible_canonical_count}</span>
            </div>
          </div>

          {/* Near-Duplicate Clustering Breakdown */}
          {result.duplicate_records.length > 0 && (
            <div className="p-4 rounded-lg bg-zinc-50 border border-zinc-200 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-600">
                MinHash LSH Near-Duplicate Clusters (Non-Destructive)
              </h4>
              <div className="space-y-2">
                {result.duplicate_records.map((rec) => (
                  <div
                    key={rec.duplicate_id}
                    className="p-3 rounded bg-white border border-zinc-200 text-xs text-zinc-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                  >
                    <div>
                      <span className="font-semibold text-zinc-900">{rec.duplicate_opportunity_id}</span>
                      <span className="text-zinc-500"> clustered under </span>
                      <span className="font-semibold text-zinc-900">{rec.canonical_opportunity_id}</span>
                      <div className="text-[11px] text-zinc-500 truncate max-w-md mt-0.5">
                        Source URL: <a href={rec.source_url} target="_blank" rel="noopener noreferrer" className="underline">{rec.source_url}</a>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800">
                        Similarity: {(rec.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Deterministic Eligibility Audit */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-600">
              Deterministic Eligibility Evaluation
            </h4>
            <div className="overflow-x-auto border border-zinc-200 rounded-lg">
              <table className="min-w-full divide-y divide-zinc-200 text-left text-xs">
                <thead className="bg-zinc-50 font-semibold text-zinc-700">
                  <tr>
                    <th scope="col" className="px-3.5 py-2.5">Opportunity</th>
                    <th scope="col" className="px-3.5 py-2.5">Status</th>
                    <th scope="col" className="px-3.5 py-2.5">Verdict / Disqualification</th>
                    <th scope="col" className="px-3.5 py-2.5">Caveats / Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 bg-white">
                  {result.eligibility_results.map((elig) => (
                    <tr key={elig.opportunity_id} className="hover:bg-zinc-50/50">
                      <td className="px-3.5 py-3 font-mono text-zinc-900 font-medium">
                        {elig.opportunity_id}
                      </td>
                      <td className="px-3.5 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${
                            elig.status === 'ELIGIBLE'
                              ? 'bg-emerald-100 text-emerald-800'
                              : elig.status === 'ELIGIBLE_WITH_UNCERTAINTY'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {elig.status}
                        </span>
                      </td>
                      <td className="px-3.5 py-3 text-zinc-600">
                        {elig.disqualification_reasons.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {elig.disqualification_reasons.map((reason) => (
                              <span key={reason} className="font-mono text-[10px] text-rose-700 bg-rose-50 px-1 py-0.5 rounded">
                                {reason}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-emerald-700 font-medium">Passed all hard gates</span>
                        )}
                      </td>
                      <td className="px-3.5 py-3 text-zinc-500 text-[11px]">
                        {elig.uncertainty_caveats.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {elig.uncertainty_caveats.map((caveat) => (
                              <span key={caveat} className="font-mono text-[10px] text-amber-800 bg-amber-50 px-1 py-0.5 rounded">
                                {caveat}
                              </span>
                            ))}
                          </div>
                        ) : (
                          'None'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

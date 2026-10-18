'use client';

import React, { useEffect, useState } from 'react';
import {
  CandidateCareerProfile,
  ConnectorHealthReport,
  DiscoveryQueryPlan,
  DiscoveryRunResponse,
  OpportunityCategory,
  WorkMode,
  DegreeLevel,
  EvidenceSourceType,
  CareerPathRelationship,
} from '@/types/domain';
import {
  generateDiscoveryPlan,
  getDiscoveryConnectors,
  runDiscovery,
} from '@/lib/api';

// Pre-configured candidate profiles for quick interactive testing
const SAMPLE_CANDIDATES: Record<string, { label: string; description: string; profile: CandidateCareerProfile }> = {
  maya: {
    label: 'Maya Chen — Junior Backend Engineer (US)',
    description: '18 months experience, strong Python, FastAPI, PostgreSQL, Docker skills. Target: Backend Engineer. Authorized: US.',
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
          proficiency_score: 7.0,
          confidence_score: 0.80,
          evidence_records: [
            {
              evidence_id: 'ev-m-4',
              source_type: 'RESUME_PROJECT' as EvidenceSourceType,
              extracted_snippet: 'Containerized microservices for Kubernetes deployment.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.80,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:typescript',
          skill_name: 'TypeScript',
          proficiency_score: 6.0,
          confidence_score: 0.75,
          evidence_records: [
            {
              evidence_id: 'ev-m-5',
              source_type: 'RESUME_PROJECT' as EvidenceSourceType,
              extracted_snippet: 'Built developer portal dashboard in React & TypeScript.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.75,
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
      adjacent_career_paths: [],
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
    description: 'Enrolled B.Tech student graduating 2026. Python, React, SQL. Target: Software Engineering Intern. Authorized: IN.',
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
              extracted_snippet: 'Developed full stack automated testing toolkit in Python.',
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
              extracted_snippet: 'Constructed responsive student event portal with React & Tailwind.',
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
              extracted_snippet: 'Relational Database Management coursework (Grade: A).',
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

export function DiscoveryDemo() {
  const [selectedKey, setSelectedKey] = useState<string>('maya');
  const [connectors, setConnectors] = useState<ConnectorHealthReport[]>([]);
  const [queryPlan, setQueryPlan] = useState<DiscoveryQueryPlan | null>(null);
  const [discoveryResponse, setDiscoveryResponse] = useState<DiscoveryRunResponse | null>(null);

  const [simulateFailure, setSimulateFailure] = useState<string>('none');
  const [dedupThreshold, setDedupThreshold] = useState<number>(0.85);

  const [loadingConnectors, setLoadingConnectors] = useState<boolean>(false);
  const [planningLoading, setPlanningLoading] = useState<boolean>(false);
  const [discoveryLoading, setDiscoveryLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const currentProfile = SAMPLE_CANDIDATES[selectedKey].profile;

  // Load connector health on mount
  useEffect(() => {
    refreshConnectors();
  }, []);

  async function refreshConnectors() {
    setLoadingConnectors(true);
    try {
      const data = await getDiscoveryConnectors();
      setConnectors(data);
    } catch (err: unknown) {
      console.error('Failed to load discovery connectors:', err);
    } finally {
      setLoadingConnectors(false);
    }
  }

  async function handleGeneratePlan() {
    setPlanningLoading(true);
    setErrorMessage(null);
    try {
      const plan = await generateDiscoveryPlan({ candidate_profile: currentProfile });
      setQueryPlan(plan);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate query plan';
      setErrorMessage(msg);
    } finally {
      setPlanningLoading(false);
    }
  }

  async function handleRunDiscovery() {
    setDiscoveryLoading(true);
    setErrorMessage(null);
    try {
      const failureParam = simulateFailure === 'none' ? null : simulateFailure;
      const res = await runDiscovery({
        candidate_profile: currentProfile,
        max_results_per_connector: 3,
        deduplication_threshold: dedupThreshold,
        simulate_failure_connector: failureParam,
        persist_to_repository: true,
      });
      setDiscoveryResponse(res);
      if (!queryPlan) {
        setQueryPlan(res.query_plan);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Discovery run failed';
      setErrorMessage(msg);
    } finally {
      setDiscoveryLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden text-zinc-900">
      {/* Header Banner */}
      <div className="bg-zinc-900 text-white p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Milestone 7
              </span>
              <span className="text-xs text-zinc-400">Multi-Source Discovery & Role Mapping</span>
            </div>
            <h3 className="text-xl font-bold tracking-tight mt-1 text-white">
              Skill-to-Role Mapping & Discovery Coordinator
            </h3>
            <p className="text-xs text-zinc-300 mt-1 max-w-2xl">
              Maps candidate skills to O*NET taxonomy families, queries 4 independent sources
              with partial failure resilience, runs early MinHash LSH deduplication, and feeds results into the
              deterministic eligibility engine.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={refreshConnectors}
              disabled={loadingConnectors}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition"
            >
              {loadingConnectors ? 'Checking...' : 'Refresh Health'}
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 sm:p-8 space-y-8">
        {/* Error notification */}
        {errorMessage && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs">
            <span className="font-semibold">Error:</span> {errorMessage}
          </div>
        )}

        {/* Section 1: Candidate Selection */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
            1. Select Candidate Profile For Discovery
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(SAMPLE_CANDIDATES).map(([key, item]) => {
              const isSelected = selectedKey === key;
              return (
                <div
                  key={key}
                  onClick={() => {
                    setSelectedKey(key);
                    setQueryPlan(null);
                    setDiscoveryResponse(null);
                  }}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    isSelected
                      ? 'border-indigo-600 bg-indigo-50/30 shadow-sm'
                      : 'border-zinc-200 bg-zinc-50/50 hover:border-zinc-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-900">{item.label}</span>
                    {isSelected && (
                      <span className="text-[10px] uppercase font-bold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-600 mt-1.5 leading-relaxed">{item.description}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 2: Multi-Source Connector Health Status */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              2. Discovery Connectors & Transport Health
            </label>
            <span className="text-[11px] text-zinc-400">
              Honest status reporting (never claiming uninstalled tools are live)
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {connectors.map((c) => {
              const isMock = c.is_mock_fallback;
              let badgeColor = 'bg-zinc-100 text-zinc-700 border-zinc-200';
              if (c.status === 'CONNECTED') {
                badgeColor = 'bg-emerald-50 text-emerald-700 border-emerald-200';
              } else if (c.status === 'MOCKED_FALLBACK') {
                badgeColor = 'bg-sky-50 text-sky-700 border-sky-200';
              } else if (c.status === 'UNAVAILABLE_MISSING_BINARY') {
                badgeColor = 'bg-amber-50 text-amber-700 border-amber-200';
              } else if (c.status === 'ERROR') {
                badgeColor = 'bg-rose-50 text-rose-700 border-rose-200';
              }

              return (
                <div key={c.connector_id} className="p-4 rounded-xl border border-zinc-200 bg-white space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400">
                      {c.connector_type}
                    </span>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badgeColor}`}>
                      {c.status}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-zinc-900 leading-tight">{c.source_name}</h4>
                  <p className="text-[11px] text-zinc-500">
                    {isMock ? 'Deterministic offline adapter' : 'Live network transport active'}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 3: Skill-to-Role Mapping Action & Query Plan */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
              3. Skill-to-Role Mapping & Query Planning
            </label>
            <button
              onClick={handleGeneratePlan}
              disabled={planningLoading}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white transition shadow-sm disabled:opacity-50"
            >
              {planningLoading ? 'Mapping Roles...' : 'Generate Query Plan'}
            </button>
          </div>

          {queryPlan && (
            <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/50 space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-200 pb-3">
                <span className="text-xs font-bold text-zinc-900">
                  Taxonomy Mappings ({queryPlan.target_roles.length} Roles, {queryPlan.all_queries.length} Queries)
                </span>
                <span className="text-xs font-mono text-zinc-500">
                  Candidate ID: {queryPlan.candidate_id}
                </span>
              </div>

              {/* Roles mapped */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {queryPlan.target_roles.map((target, idx) => (
                  <div key={idx} className="p-4 rounded-lg bg-white border border-zinc-200 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-zinc-900">{target.role_title}</span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          target.relationship_type === 'TARGET'
                            ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {target.relationship_type} ({Math.round(target.confidence_score * 100)}%)
                      </span>
                    </div>

                    <div className="text-[11px] font-mono text-zinc-500">
                      O*NET Code: {target.canonical_occupation_code}
                    </div>

                    {/* Matched skills */}
                    <div>
                      <div className="text-[10px] font-medium text-zinc-500 uppercase">Matched Core Skills</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {target.matched_skill_names.map((s, sIdx) => (
                          <span
                            key={sIdx}
                            className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-medium"
                          >
                            ✓ {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Missing skills */}
                    {target.missing_skill_names.length > 0 && (
                      <div>
                        <div className="text-[10px] font-medium text-zinc-500 uppercase">Missing Role Competencies</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {target.missing_skill_names.slice(0, 4).map((s, sIdx) => (
                            <span
                              key={sIdx}
                              className="px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200 text-[10px]"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Sample Generated Search Queries */}
              <div>
                <div className="text-xs font-semibold text-zinc-700 mb-2">Generated Parameterized Queries:</div>
                <div className="space-y-1.5 font-mono text-xs">
                  {queryPlan.all_queries.slice(0, 3).map((q, qIdx) => (
                    <div key={qIdx} className="p-2.5 rounded bg-white border border-zinc-200 flex items-center justify-between">
                      <span className="text-zinc-800">{q.query_string}</span>
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600 text-[10px]">
                          {q.category}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 text-[10px]">
                          {q.seniority_level}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 4: Discovery Run Execution & Partial Failure Simulation */}
        <div className="space-y-4 border-t border-zinc-200 pt-6">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
            4. Execute Multi-Source Discovery
          </label>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-xl border border-zinc-200 bg-zinc-50/50">
            <div className="space-y-2">
              <div className="text-xs font-bold text-zinc-900">Resilience & Partial Failure Simulation</div>
              <p className="text-xs text-zinc-600 max-w-xl">
                Test connector error shielding: Even if one connector throws an exception or times out,
                the Discovery Coordinator traps it and delivers results from the remaining connectors.
              </p>

              <div className="flex flex-wrap items-center gap-3 pt-1">
                <label className="text-xs font-medium text-zinc-700">Simulate Failure:</label>
                <select
                  value={simulateFailure}
                  onChange={(e) => setSimulateFailure(e.target.value)}
                  className="px-3 py-1.5 rounded-lg border border-zinc-300 text-xs bg-white text-zinc-800"
                >
                  <option value="none">None (All 4 Healthy)</option>
                  <option value="web_search">Web Search Error (Simulate HTTP 503)</option>
                  <option value="india_jobs_mcp">India Jobs MCP Error (Simulate Crash)</option>
                  <option value="jobspy_mcp">JobSpy MCP Error (Simulate Timeout)</option>
                  <option value="ats_career_pages">ATS Career Page Error (Simulate Gateway Error)</option>
                </select>

                <label className="text-xs font-medium text-zinc-700 ml-2">MinHash Dedup Threshold:</label>
                <input
                  type="number"
                  step="0.05"
                  min="0.5"
                  max="1.0"
                  value={dedupThreshold}
                  onChange={(e) => setDedupThreshold(parseFloat(e.target.value))}
                  className="w-16 px-2 py-1 rounded border border-zinc-300 text-xs bg-white text-zinc-800"
                />
              </div>
            </div>

            <button
              onClick={handleRunDiscovery}
              disabled={discoveryLoading}
              className="px-6 py-3 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white transition shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 self-start sm:self-auto"
            >
              {discoveryLoading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Discovering Opportunities...</span>
                </>
              ) : (
                <span>Run Discovery Coordinator</span>
              )}
            </button>
          </div>
        </div>

        {/* Section 5: Discovery Results Telemetry & Normalized Listings */}
        {discoveryResponse && (
          <div className="space-y-6 border-t border-zinc-200 pt-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                5. Discovery Run Results & Telemetry
              </label>
              <span className="text-xs font-mono text-zinc-500">
                Execution time: {String(discoveryResponse.execution_metadata.duration_ms)} ms
              </span>
            </div>

            {/* KPI metric summary cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="p-4 rounded-xl border border-zinc-200 bg-white">
                <div className="text-[10px] font-bold text-zinc-500 uppercase">Total Fetched</div>
                <div className="text-xl font-bold text-zinc-900 mt-1">{discoveryResponse.total_discovered}</div>
              </div>

              <div className="p-4 rounded-xl border border-zinc-200 bg-white">
                <div className="text-[10px] font-bold text-zinc-500 uppercase">Canonical Roles</div>
                <div className="text-xl font-bold text-indigo-600 mt-1">{discoveryResponse.canonical_count}</div>
              </div>

              <div className="p-4 rounded-xl border border-zinc-200 bg-white">
                <div className="text-[10px] font-bold text-zinc-500 uppercase">Duplicates Clustered</div>
                <div className="text-xl font-bold text-amber-600 mt-1">{discoveryResponse.duplicate_count}</div>
              </div>

              <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40">
                <div className="text-[10px] font-bold text-emerald-800 uppercase">Eligible Roles</div>
                <div className="text-xl font-bold text-emerald-700 mt-1">{discoveryResponse.eligible_count}</div>
              </div>

              <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/40">
                <div className="text-[10px] font-bold text-amber-800 uppercase">Eligible w/ Caveats</div>
                <div className="text-xl font-bold text-amber-700 mt-1">{discoveryResponse.uncertain_count}</div>
              </div>

              <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/40">
                <div className="text-[10px] font-bold text-rose-800 uppercase">Ineligible Roles</div>
                <div className="text-xl font-bold text-rose-700 mt-1">{discoveryResponse.ineligible_count}</div>
              </div>
            </div>

            {/* Connector execution breakdown */}
            <div className="space-y-2">
              <div className="text-xs font-semibold text-zinc-700">Connector Execution Status:</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {discoveryResponse.connector_reports.map((report) => (
                  <div
                    key={report.connector_id}
                    className={`p-3 rounded-lg border text-xs space-y-1 ${
                      report.status === 'ERROR'
                        ? 'border-rose-300 bg-rose-50 text-rose-900'
                        : 'border-zinc-200 bg-white text-zinc-800'
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold">
                      <span>{report.source_name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-mono">
                        {report.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-zinc-500 flex justify-between">
                      <span>Items: {report.raw_count}</span>
                      <span>Latency: {report.latency_ms} ms</span>
                    </div>
                    {report.error_message && (
                      <div className="text-[10px] text-rose-700 pt-1 border-t border-rose-200">
                        {report.error_message}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Opportunities List */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-zinc-700">
                Discovered Opportunities & Deterministic Eligibility Verification:
              </div>

              <div className="space-y-3">
                {discoveryResponse.canonical_opportunities.map((opp) => {
                  const evalResult = discoveryResponse.eligibility_results.find(
                    (r) => r.opportunity_id === opp.opportunity_id
                  );
                  const cluster = discoveryResponse.duplicate_clusters[opp.opportunity_id];
                  const hasDuplicates = cluster && cluster.duplicate_records.length > 0;

                  return (
                    <div
                      key={opp.opportunity_id}
                      className="p-5 rounded-xl border border-zinc-200 bg-white space-y-3 shadow-xs hover:border-zinc-300 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-zinc-900">{opp.title}</h4>
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-zinc-100 text-zinc-700">
                              {opp.company_name}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500 mt-1">
                            <span>{opp.eligibility_rules.opportunity_category}</span>
                            <span>•</span>
                            <span>{opp.eligibility_rules.work_mode}</span>
                            <span>•</span>
                            <span>
                              {opp.eligibility_rules.location_city_country.join(', ') ||
                                opp.eligibility_rules.eligible_country_codes.join(', ')}
                            </span>
                            <span>•</span>
                            <span className="font-mono text-indigo-600">
                              Source: {opp.category_specific_attributes.source_system as string}
                            </span>
                          </div>
                        </div>

                        {/* Eligibility Status Pill */}
                        <div>
                          {evalResult?.is_eligible ? (
                            evalResult.status === 'ELIGIBLE_WITH_UNCERTAINTY' ? (
                              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                                Eligible (With Caveats)
                              </span>
                            ) : (
                              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                                100% Eligible
                              </span>
                            )
                          ) : (
                            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                              Disqualified
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Description summary */}
                      <p className="text-xs text-zinc-600 leading-relaxed">
                        {opp.sanitized_summary}
                      </p>

                      {/* Near-duplicate cluster alert */}
                      {hasDuplicates && (
                        <div className="p-3 rounded-lg bg-indigo-50/60 border border-indigo-200 text-xs space-y-1">
                          <div className="font-bold text-indigo-900 flex items-center gap-1.5">
                            <span>🔄 MinHash LSH Clustered Syndicated Near-Duplicate:</span>
                            <span className="text-[11px] font-normal text-indigo-700">
                              Detected across {cluster.all_source_urls.length} independent sources without data loss.
                            </span>
                          </div>
                          <div className="text-[11px] text-indigo-800 font-mono space-y-0.5 pt-1">
                            {cluster.duplicate_records.map((dup, dIdx) => (
                              <div key={dIdx} className="truncate">
                                • {dup.source_url} (Similarity: {Math.round(dup.similarity_score * 100)}%)
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Disqualification / Uncertainty Reasons */}
                      {evalResult && !evalResult.is_eligible && (
                        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800">
                          <span className="font-semibold">Deterministic Disqualification: </span>
                          {evalResult.disqualification_reasons.join(', ')}
                        </div>
                      )}

                      {evalResult && evalResult.uncertainty_caveats.length > 0 && (
                        <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800">
                          <span className="font-semibold">Caveats Preserved: </span>
                          {evalResult.uncertainty_caveats.join(', ')}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

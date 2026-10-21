'use client';

import React, { useState } from 'react';
import {
  AdaptiveDiscoveryRequest,
  AdaptiveDiscoveryResponse,
  CandidateCareerProfile,
  CareerPathRelationship,
  ConstraintCheckResult,
  DegreeLevel,
  EvidenceSourceType,
  OpportunityCategory,
  RankedOpportunity,
  RankingDimension,
  WorkMode,
} from '@/types/domain';
import { runAdaptiveDiscovery } from '@/lib/api';

const SAMPLE_PROFILES: Record<string, { label: string; description: string; profile: CandidateCareerProfile }> = {
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
        total_full_time_experience_months: 18,
        allowed_opportunity_categories: ['FULL_TIME_JOB' as OpportunityCategory],
        allowed_work_modes: ['REMOTE' as WorkMode, 'HYBRID' as WorkMode],
        preferred_locations: ['San Francisco, US', 'Remote'],
      },
      overall_profile_confidence: 0.88,
    },
  },
  alex: {
    label: 'Alex Rivera — Senior Full Stack Engineer (US & Remote)',
    description: '48 months experience, advanced TypeScript, React, Python, PostgreSQL, AWS, Microservices.',
    profile: {
      user_id: 'alex-rivera-senior',
      profile_version: 1,
      assessed_skills: [
        {
          canonical_skill_id: 'esco:typescript',
          skill_name: 'TypeScript',
          proficiency_score: 9.0,
          confidence_score: 0.95,
          evidence_records: [
            {
              evidence_id: 'ev-a-1',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Led frontend architecture across 4 engineering pods in React/TypeScript.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.95,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:react',
          skill_name: 'React',
          proficiency_score: 8.8,
          confidence_score: 0.92,
          evidence_records: [
            {
              evidence_id: 'ev-a-2',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Built real-time collaborative workspace interface.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.90,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:python',
          skill_name: 'Python',
          proficiency_score: 8.2,
          confidence_score: 0.88,
          evidence_records: [
            {
              evidence_id: 'ev-a-3',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Built ETL pipelines and FastAPI endpoints.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.88,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:postgresql',
          skill_name: 'PostgreSQL',
          proficiency_score: 8.0,
          confidence_score: 0.86,
          evidence_records: [
            {
              evidence_id: 'ev-a-4',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Designed high-concurrency relational schema.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:docker',
          skill_name: 'Docker',
          proficiency_score: 7.8,
          confidence_score: 0.82,
          evidence_records: [
            {
              evidence_id: 'ev-a-5',
              source_type: 'RESUME_PROJECT' as EvidenceSourceType,
              extracted_snippet: 'Containerized CI/CD builds with GitHub Actions.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.80,
            },
          ],
        },
      ],
      target_career_paths: [
        {
          occupation_code: '15-1254.00',
          title: 'Frontend Engineer',
          relationship_type: 'TARGET' as CareerPathRelationship,
          adjacency_similarity: 1.0,
          missing_core_skill_ids: [],
        },
        {
          occupation_code: '15-1252.00',
          title: 'Backend Software Engineer',
          relationship_type: 'TARGET' as CareerPathRelationship,
          adjacency_similarity: 0.95,
          missing_core_skill_ids: [],
        },
      ],
      adjacent_career_paths: [],
      eligibility_constraints: {
        authorized_country_codes: ['US'],
        requires_visa_sponsorship: false,
        highest_degree_level: 'BACHELORS' as DegreeLevel,
        is_currently_enrolled_student: false,
        total_full_time_experience_months: 48,
        allowed_opportunity_categories: ['FULL_TIME_JOB' as OpportunityCategory],
        allowed_work_modes: ['REMOTE' as WorkMode, 'HYBRID' as WorkMode, 'ON_SITE' as WorkMode],
        preferred_locations: ['Remote', 'San Francisco, US'],
      },
      overall_profile_confidence: 0.92,
    },
  },
  priya: {
    label: 'Priya Sharma — Student Software Engineer (India)',
    description: 'Final-year student, Java, Python, SQL, REST APIs. Authorized: IN. Looking for Internships & Entry roles.',
    profile: {
      user_id: 'priya-sharma-student',
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
              extracted_snippet: 'Developed backend API in Flask for college portal.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.80,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:java',
          skill_name: 'Java',
          proficiency_score: 7.8,
          confidence_score: 0.85,
          evidence_records: [
            {
              evidence_id: 'ev-p-2',
              source_type: 'RESUME_WORK_EXPERIENCE' as EvidenceSourceType,
              extracted_snippet: 'Completed 6-month software internship building Spring Boot microservices.',
              observed_at: '2026-01-10T00:00:00Z',
              verifiability_weight: 0.85,
            },
          ],
        },
        {
          canonical_skill_id: 'esco:sql',
          skill_name: 'SQL',
          proficiency_score: 7.0,
          confidence_score: 0.80,
          evidence_records: [
            {
              evidence_id: 'ev-p-3',
              source_type: 'CERTIFICATION' as EvidenceSourceType,
              extracted_snippet: 'Certified Database Developer with MySQL and PostgreSQL.',
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
      adjacent_career_paths: [],
      eligibility_constraints: {
        authorized_country_codes: ['IN'],
        requires_visa_sponsorship: false,
        highest_degree_level: 'BACHELORS' as DegreeLevel,
        is_currently_enrolled_student: true,
        expected_graduation_date: '2026-06-30',
        total_full_time_experience_months: 6,
        allowed_opportunity_categories: ['INTERNSHIP' as OpportunityCategory, 'FULL_TIME_JOB' as OpportunityCategory],
        allowed_work_modes: ['HYBRID' as WorkMode, 'REMOTE' as WorkMode, 'ON_SITE' as WorkMode],
        preferred_locations: ['Bengaluru, India', 'Pune, India', 'Remote'],
      },
      overall_profile_confidence: 0.82,
    },
  },
};

export function AdaptiveDiscoveryDemo() {
  const [selectedCandidate, setSelectedCandidate] = useState<string>('alex');
  const [targetCoverageGoal, setTargetCoverageGoal] = useState<number>(3);
  const [maxIterations, setMaxIterations] = useState<number>(2);
  const [maxToolCalls, setMaxToolCalls] = useState<number>(12);
  const [simulateFailure, setSimulateFailure] = useState<string>('none');
  const [forceGap, setForceGap] = useState<boolean>(false);
  const [enableLiveDiscovery, setEnableLiveDiscovery] = useState<boolean>(true);
  const [rankRecommendations, setRankRecommendations] = useState<boolean>(true);
  const [weightProfile, setWeightProfile] = useState<string>('DEFAULT');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [response, setResponse] = useState<AdaptiveDiscoveryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'recommendations' | 'timeline' | 'adaptations' | 'opportunities' | 'connectors'>('recommendations');
  const [expandedEventIdx, setExpandedEventIdx] = useState<number | null>(null);

  const candidateData = SAMPLE_PROFILES[selectedCandidate];

  async function handleRunWorkflow() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const payload: AdaptiveDiscoveryRequest = {
        candidate_profile: candidateData.profile,
        user_id: candidateData.profile.user_id,
        target_coverage_goal: Number(targetCoverageGoal),
        max_iterations: Number(maxIterations),
        max_tool_calls: Number(maxToolCalls),
        deduplication_threshold: 0.85,
        simulate_failure_connector: simulateFailure === 'none' ? null : simulateFailure,
        force_adaptive_gap_for_testing: forceGap,
        persist_to_repository: true,
        enable_live_discovery: enableLiveDiscovery,
        rank_recommendations: rankRecommendations,
        weight_profile_name: weightProfile,
      };

      const res = await runAdaptiveDiscovery(payload);
      setResponse(res);
      if (res.recommendations && res.recommendations.ranked_recommendations?.length > 0) {
        setActiveTab('recommendations');
      } else if (res.adaptation_history && res.adaptation_history.length > 0) {
        setActiveTab('adaptations');
      } else {
        setActiveTab('timeline');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Orchestration workflow execution failed';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }

  function getTerminationBadgeClass(reason?: string) {
    switch (reason) {
      case 'COVERAGE_SATISFIED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'MAX_ITERATIONS_REACHED':
      case 'BUDGET_EXHAUSTED':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'ALL_SOURCES_EXHAUSTED':
      case 'ABORTED_ERROR':
      case 'FAILED':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-zinc-100 text-zinc-700 border-zinc-200';
    }
  }

  const eligibilityMap = React.useMemo(() => {
    if (!response?.eligibility_results) return new Map();
    return new Map(response.eligibility_results.map((r) => [r.opportunity_id, r]));
  }, [response]);

  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-sm overflow-hidden text-zinc-900">
      {/* Header Banner */}
      <div className="bg-zinc-900 text-white p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Milestone 10
              </span>
              <span className="text-xs text-zinc-400">End-to-End Career Intelligence & Live Discovery Validation</span>
            </div>
            <h3 className="text-xl font-bold tracking-tight mt-1 text-white">
              End-to-End Career Intelligence & Live Discovery System
            </h3>
            <p className="text-xs text-zinc-300 mt-1 max-w-3xl leading-relaxed">
              Unified agentic pipeline executing from candidate evidence profiling to multi-source discovery (Greenhouse, Ashby, JobSpy/Indeed),
              deterministic MinHash deduplication, hard eligibility gating, and 6-dimensional candidate-job fit ranking with honest source transparency.
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium border border-zinc-700 bg-zinc-800 text-zinc-300">
              <span className={`w-2 h-2 rounded-full ${enableLiveDiscovery ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
              {enableLiveDiscovery ? 'Live External Mode' : 'Deterministic Fixture Mode'}
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
              className="text-rose-500 hover:text-rose-700 text-xs font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Configuration Console */}
        <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/50 space-y-5">
          <div className="flex items-center justify-between border-b border-zinc-200 pb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700">
              Pipeline Execution Controls
            </h4>
            <span className="text-xs font-mono text-zinc-500">
              Candidate: {candidateData.label.split(' — ')[0]}
            </span>
          </div>

          {/* Candidate Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-700">Select Candidate Career Profile</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {Object.entries(SAMPLE_PROFILES).map(([key, data]) => {
                const isSelected = selectedCandidate === key;
                return (
                  <button
                    key={key}
                    onClick={() => setSelectedCandidate(key)}
                    className={`p-3 rounded-lg border text-left transition ${
                      isSelected
                        ? 'border-violet-600 bg-violet-50/50 ring-1 ring-violet-600 text-zinc-900'
                        : 'border-zinc-200 bg-white hover:border-zinc-300 text-zinc-700'
                    }`}
                  >
                    <div className="font-bold text-xs">{data.label}</div>
                    <div className="text-[11px] text-zinc-500 mt-1 line-clamp-2 leading-relaxed">
                      {data.description}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Milestone 10 Mode & Ranking Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
            <div className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50/40 space-y-1">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="liveDiscoveryToggle"
                  checked={enableLiveDiscovery}
                  onChange={(e) => setEnableLiveDiscovery(e.target.checked)}
                  className="h-4 w-4 rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500"
                />
                <label htmlFor="liveDiscoveryToggle" className="text-xs font-bold text-emerald-900 cursor-pointer">
                  Query Live External APIs & Scrapers
                </label>
              </div>
              <p className="text-[10px] text-emerald-800 leading-relaxed pl-6">
                Queries Greenhouse, Ashby, and Indeed live. Falling back gracefully if offline.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-violet-200 bg-violet-50/40 space-y-1">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="rankRecsToggle"
                  checked={rankRecommendations}
                  onChange={(e) => setRankRecommendations(e.target.checked)}
                  className="h-4 w-4 rounded border-zinc-300 text-violet-600 focus:ring-violet-500"
                />
                <label htmlFor="rankRecsToggle" className="text-xs font-bold text-violet-900 cursor-pointer">
                  Run 6-D Fit Scoring & Ranking
                </label>
              </div>
              <p className="text-[10px] text-violet-800 leading-relaxed pl-6">
                Applies multi-dimensional evidence fit math to compute personalized recommendations.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-zinc-200 bg-white space-y-1">
              <label className="text-[11px] font-bold text-zinc-700">Ranking Weight Profile</label>
              <select
                value={weightProfile}
                onChange={(e) => setWeightProfile(e.target.value)}
                className="w-full px-2.5 py-1 rounded-md border border-zinc-200 bg-zinc-50 text-xs text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              >
                <option value="DEFAULT">DEFAULT (30/20/20/12/10/8)</option>
                <option value="EARLY_CAREER">EARLY_CAREER (25/20/28/12/10/5)</option>
                <option value="EXPERIENCED">EXPERIENCED (35/20/15/10/10/10)</option>
              </select>
              <p className="text-[10px] text-zinc-400">Calibrated scoring weights</p>
            </div>
          </div>

          {/* Loop Guard Parameters */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-1">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-700">Coverage Goal</label>
              <input
                type="number"
                min={1}
                max={10}
                value={targetCoverageGoal}
                onChange={(e) => setTargetCoverageGoal(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs font-mono text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <span className="text-[10px] text-zinc-400">Target count</span>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-700">Max Iterations</label>
              <input
                type="number"
                min={1}
                max={5}
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs font-mono text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <span className="text-[10px] text-zinc-400">Loop budget</span>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-700">Max Tool Calls</label>
              <input
                type="number"
                min={4}
                max={20}
                value={maxToolCalls}
                onChange={(e) => setMaxToolCalls(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs font-mono text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <span className="text-[10px] text-zinc-400">Cost guard</span>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-700">Simulate Failure</label>
              <select
                value={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              >
                <option value="none">None (All Healthy)</option>
                <option value="web_search">Web Search Error</option>
                <option value="india_jobs_mcp">India Jobs MCP Error</option>
                <option value="jobspy_mcp">JobSpy MCP Error</option>
                <option value="ats_career_pages">ATS Career Pages Error</option>
              </select>
              <span className="text-[10px] text-zinc-400">Resilience test</span>
            </div>

            <div className="space-y-1 flex flex-col justify-between">
              <div>
                <label className="text-[11px] font-semibold text-zinc-700">Adaptive Shift</label>
                <div className="flex items-center gap-2 mt-2">
                  <input
                    type="checkbox"
                    id="forceGapToggle"
                    checked={forceGap}
                    onChange={(e) => setForceGap(e.target.checked)}
                    className="h-4 w-4 rounded border-zinc-300 text-violet-600 focus:ring-violet-500"
                  />
                  <label htmlFor="forceGapToggle" className="text-xs text-zinc-700 font-medium cursor-pointer">
                    Force Gap
                  </label>
                </div>
              </div>
              <span className="text-[10px] text-zinc-400">Test adaptation</span>
            </div>
          </div>

          <div className="flex items-center justify-end pt-2">
            <button
              onClick={handleRunWorkflow}
              disabled={isLoading}
              className="px-6 py-2.5 rounded-lg text-xs font-bold bg-violet-600 hover:bg-violet-700 text-white transition shadow-sm disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Executing End-to-End Career Intelligence Pipeline...</span>
                </>
              ) : (
                <>
                  <span>▶</span>
                  <span>Execute End-to-End Career Intelligence</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {response && (
          <div className="space-y-6 pt-4 border-t border-zinc-200">
            {/* Top Summary & Termination Bar */}
            <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-4">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border-b border-zinc-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-zinc-900">Workflow Execution</span>
                    <span className="text-xs font-mono text-zinc-400">
                      ID: {response.workflow_id.slice(0, 16)}...
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-zinc-500 font-medium">Termination Reason:</span>
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${getTerminationBadgeClass(response.termination_reason)}`}>
                      {response.termination_reason}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono">
                  <div className="px-3 py-1.5 rounded-lg bg-zinc-50 border border-zinc-200 text-zinc-700">
                    <span className="text-zinc-400 font-sans text-[11px]">Iterations: </span>
                    <span className="font-bold">{response.iterations_completed}</span>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-zinc-50 border border-zinc-200 text-zinc-700">
                    <span className="text-zinc-400 font-sans text-[11px]">Tool Calls: </span>
                    <span className="font-bold">{response.total_tool_calls}</span>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-zinc-50 border border-zinc-200 text-zinc-700">
                    <span className="text-zinc-400 font-sans text-[11px]">Duration: </span>
                    <span className="font-bold">{response.execution_metadata.duration_ms as number}ms</span>
                  </div>
                </div>
              </div>

              {/* Key Metrics Counter Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Raw Discovered</div>
                  <div className="text-lg font-bold text-zinc-900 mt-0.5">{response.total_discovered_raw}</div>
                  <div className="text-[10px] text-zinc-400">Across all sources</div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Canonical Unique</div>
                  <div className="text-lg font-bold text-violet-700 mt-0.5">{response.canonical_count}</div>
                  <div className="text-[10px] text-zinc-400">MinHash LSH deduplicated</div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Duplication Rate</div>
                  <div className="text-lg font-bold text-amber-700 mt-0.5">
                    {response.total_discovered_raw > 0
                      ? `${Math.round((response.duplicate_count / response.total_discovered_raw) * 100)}%`
                      : '0%'}
                  </div>
                  <div className="text-[10px] text-zinc-400">{response.duplicate_count} syndicated postings</div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Eligible Qualified</div>
                  <div className="text-lg font-bold text-emerald-700 mt-0.5">
                    {response.eligible_count + response.uncertain_count}
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    {response.eligible_count} clean / {response.uncertain_count} caveats
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Ranked Recs</div>
                  <div className="text-lg font-bold text-indigo-700 mt-0.5">
                    {response.recommendations?.total_eligible_ranked ?? 0}
                  </div>
                  <div className="text-[10px] text-zinc-400">
                    Top fit: {response.recommendations?.ranked_recommendations?.[0] ? `${(response.recommendations.ranked_recommendations[0].overall_fit_score * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="border-b border-zinc-200 flex items-center gap-4 text-xs font-semibold overflow-x-auto">
              {response.recommendations && (
                <button
                  onClick={() => setActiveTab('recommendations')}
                  className={`pb-2.5 transition border-b-2 flex items-center gap-1.5 ${
                    activeTab === 'recommendations'
                      ? 'border-violet-600 text-violet-700 font-bold'
                      : 'border-transparent text-zinc-500 hover:text-zinc-800'
                  }`}
                >
                  <span>Ranked Recommendations</span>
                  <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-violet-100 text-violet-800 font-mono">
                    {response.recommendations.ranked_recommendations?.length ?? 0}
                  </span>
                </button>
              )}
              <button
                onClick={() => setActiveTab('timeline')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'timeline'
                    ? 'border-violet-600 text-violet-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Workflow Timeline ({response.timeline_events.length})
              </button>
              <button
                onClick={() => setActiveTab('opportunities')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'opportunities'
                    ? 'border-violet-600 text-violet-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Canonical Opportunities ({response.canonical_opportunities.length})
              </button>
              <button
                onClick={() => setActiveTab('adaptations')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'adaptations'
                    ? 'border-violet-600 text-violet-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Adaptive Shifts ({response.adaptation_history.length})
              </button>
              <button
                onClick={() => setActiveTab('connectors')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'connectors'
                    ? 'border-violet-600 text-violet-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Source Connectors ({response.connector_health.length})
              </button>
            </div>

            {/* Tab 0: Ranked Recommendations (Milestone 10 Core) */}
            {activeTab === 'recommendations' && response.recommendations && (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-zinc-600 bg-zinc-50 p-3 rounded-lg border border-zinc-200">
                  <div>
                    <span className="font-semibold text-zinc-900">Ranking Profile: </span>
                    <span className="font-mono">{response.recommendations.weight_profile_used}</span>
                    <span className="mx-2">•</span>
                    <span>Evaluated: {response.recommendations.total_candidates_evaluated}</span>
                    <span className="mx-2">•</span>
                    <span className="text-emerald-700 font-semibold">Ranked: {response.recommendations.total_eligible_ranked}</span>
                    <span className="mx-2">•</span>
                    <span className="text-rose-700 font-semibold">Ineligible Excluded: {response.recommendations.total_ineligible_excluded}</span>
                  </div>
                  <div className="text-[11px] text-zinc-500 font-mono">
                    Evaluation ID: {response.recommendations.evaluation_id.slice(0, 14)}...
                  </div>
                </div>

                <div className="space-y-4">
                  {response.recommendations.ranked_recommendations.map((rec: RankedOpportunity) => {
                    const opp = rec.opportunity;
                    const isLive = opp.category_specific_attributes?.is_live_retrieval === true;
                    const dimScores = rec.dimension_scores as Record<RankingDimension, { raw_score: number; weight: number }>;

                    return (
                      <div
                        key={opp.opportunity_id}
                        className="p-5 rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 transition shadow-sm space-y-4"
                      >
                        {/* Header: Rank + Title + Company + Live Badge */}
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                          <div className="flex items-center gap-3">
                            <span className="w-8 h-8 rounded-lg bg-zinc-900 text-white font-bold text-xs flex items-center justify-center font-mono">
                              #{rec.rank}
                            </span>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-zinc-900">{opp.title}</h4>
                                {isLive ? (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                    Live External Listing
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-100 text-zinc-600 border border-zinc-200">
                                    Simulated Fixture
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-zinc-600 mt-0.5 flex items-center gap-2">
                                <span className="font-semibold text-zinc-800">{opp.company_name}</span>
                                <span>•</span>
                                <span>{opp.eligibility_rules.work_mode}</span>
                                <span>•</span>
                                <span className="font-mono text-[11px]">
                                  {opp.category_specific_attributes?.source_system as string || 'ats'}
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 self-end sm:self-center">
                            <div className="text-right">
                              <div className="text-xs font-mono text-zinc-400 uppercase">Fit Score</div>
                              <div className="text-lg font-bold text-violet-700 font-mono">
                                {(rec.overall_fit_score * 100).toFixed(1)}%
                              </div>
                            </div>
                            {opp.source_url && (
                              <a
                                href={opp.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-violet-600 hover:bg-violet-700 text-white transition flex items-center gap-1 shadow-sm"
                              >
                                <span>Apply / View</span>
                                <span>↗</span>
                              </a>
                            )}
                          </div>
                        </div>

                        {/* 6-Dimension Score Breakdown */}
                        <div className="p-3.5 rounded-lg bg-zinc-50 border border-zinc-200 space-y-2">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                            Multi-Dimensional Score Breakdown
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                            {([
                              ['SKILL_ALIGNMENT', 'Skill Fit'],
                              ['CAREER_ALIGNMENT', 'Career Alignment'],
                              ['GROWTH_POTENTIAL', 'Growth Potential'],
                              ['MARKET_RELEVANCE', 'Market Match'],
                              ['PREFERENCE_FIT', 'Preferences'],
                              ['QUALIFICATION_FIT', 'Qualifications'],
                            ] as [RankingDimension, string][]).map(([dimKey, dimLabel]) => {
                              const scoreObj = dimScores?.[dimKey];
                              const rawScore = scoreObj ? scoreObj.raw_score : 0;
                              return (
                                <div key={dimKey} className="p-2 rounded bg-white border border-zinc-200 text-center">
                                  <div className="text-[9px] uppercase font-bold text-zinc-400 truncate">{dimLabel}</div>
                                  <div className="text-xs font-bold text-zinc-800 font-mono mt-0.5">
                                    {(rawScore * 100).toFixed(0)}%
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Matched Skills & Growth Skills */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                          <div className="p-3 rounded-lg border border-emerald-100 bg-emerald-50/30 space-y-1.5">
                            <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">
                              Verified Matched Skills ({rec.matched_skills.length})
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {rec.matched_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-100/70 text-emerald-800 border border-emerald-200"
                                >
                                  {s.skill_name}
                                </span>
                              ))}
                              {rec.matched_skills.length === 0 && (
                                <span className="text-[11px] text-zinc-400 italic">No direct keyword overlap</span>
                              )}
                            </div>
                          </div>

                          <div className="p-3 rounded-lg border border-indigo-100 bg-indigo-50/30 space-y-1.5">
                            <span className="text-[10px] font-bold text-indigo-800 uppercase tracking-wider">
                              Growth & Missing Competencies ({rec.missing_skills.length})
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {rec.missing_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-100/70 text-indigo-800 border border-indigo-200"
                                >
                                  {s.skill_name}
                                </span>
                              ))}
                              {rec.missing_skills.length === 0 && (
                                <span className="text-[11px] text-zinc-400 italic">Prerequisites fully satisfied</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Recommendation Rationale */}
                        {rec.recommendation_rationale && (
                          <div className="text-xs text-zinc-600 leading-relaxed bg-zinc-50/60 p-3 rounded-lg border border-zinc-100">
                            <span className="font-semibold text-zinc-800">Recommendation Rationale: </span>
                            {rec.recommendation_rationale}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 1: Workflow Timeline */}
            {activeTab === 'timeline' && (
              <div className="space-y-3">
                <div className="text-xs text-zinc-500">
                  Chronological event log of all actions, tool calls, and state transitions emitted by the agent coordinator.
                </div>
                <div className="space-y-2">
                  {response.timeline_events.map((evt, idx) => {
                    const isExpanded = expandedEventIdx === idx;
                    return (
                      <div
                        key={idx}
                        className="p-3.5 rounded-lg border text-xs transition bg-white border-zinc-200 hover:border-zinc-300"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1.5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] text-zinc-400">
                              {new Date(evt.timestamp).toLocaleTimeString()}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                              evt.stage === 'RANKING' ? 'bg-violet-100 text-violet-800' : 'bg-zinc-100 text-zinc-700'
                            }`}>
                              {evt.stage}
                            </span>
                            <span className="font-bold text-zinc-900">{evt.event_type}</span>
                          </div>
                          {Object.keys(evt.details || {}).length > 0 && (
                            <button
                              onClick={() => setExpandedEventIdx(isExpanded ? null : idx)}
                              className="text-[11px] text-violet-600 hover:text-violet-800 font-medium self-end sm:self-auto"
                            >
                              {isExpanded ? 'Hide Payload' : 'Inspect Payload'}
                            </button>
                          )}
                        </div>

                        <div className="text-zinc-600 mt-1.5 leading-relaxed">{evt.summary}</div>

                        {isExpanded && (
                          <div className="mt-2.5 p-3 rounded bg-zinc-900 text-zinc-200 font-mono text-[11px] overflow-x-auto">
                            <pre>{JSON.stringify(evt.details, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 2: Canonical Opportunities & Deduplication */}
            {activeTab === 'opportunities' && (
              <div className="space-y-4">
                <div className="text-xs text-zinc-500">
                  Deduplicated canonical opportunities after MinHash LSH evaluation and deterministic eligibility evaluation.
                </div>

                <div className="space-y-3">
                  {response.canonical_opportunities.map((opp) => {
                    const elig = eligibilityMap.get(opp.opportunity_id);
                    const cluster = response.duplicate_clusters[opp.opportunity_id];
                    const clusterSize = cluster ? cluster.cluster_size : 1;
                    const isLive = opp.category_specific_attributes?.is_live_retrieval === true;

                    return (
                      <div
                        key={opp.opportunity_id}
                        className="p-4 rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 transition space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-xs font-bold text-zinc-900">{opp.title}</h4>
                              {isLive ? (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  Live External
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-zinc-100 text-zinc-600">
                                  Simulated
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-zinc-500 mt-0.5">
                              {opp.company_name} • {opp.eligibility_rules.work_mode}
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 self-start sm:self-auto">
                            {clusterSize > 1 && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-violet-50 text-violet-700 border border-violet-200">
                                Clustered ({clusterSize} syndicated)
                              </span>
                            )}
                            {opp.source_url && (
                              <a
                                href={opp.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs font-semibold text-violet-600 hover:text-violet-800 underline"
                              >
                                Source ↗
                              </a>
                            )}
                          </div>
                        </div>

                        <p className="text-xs text-zinc-600 leading-relaxed line-clamp-2">
                          {opp.sanitized_summary}
                        </p>

                        {/* Deterministic Audit Breakdown */}
                        {elig && (
                          <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-[11px] space-y-1.5">
                            <div className="flex items-center justify-between text-zinc-500 font-semibold text-[10px] uppercase">
                              <span>Deterministic Eligibility Rules Audit</span>
                              <span className="font-mono">
                                {elig.status}
                              </span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[10px]">
                              {Object.entries(elig.constraint_checks || {}).map(([key, rawCheck]) => {
                                const check = rawCheck as ConstraintCheckResult;
                                return (
                                  <div key={key}>
                                    <span className="text-zinc-400">{key}: </span>
                                    <span className={`font-semibold ${
                                      check.status === 'PASSED' ? 'text-emerald-700' : check.status === 'UNCERTAIN' ? 'text-sky-700' : 'text-rose-700'
                                    }`}>
                                      {check.status}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 3: Adaptive Shifts */}
            {activeTab === 'adaptations' && (
              <div className="space-y-4">
                <div className="text-xs text-zinc-500">
                  Adaptive decisions made by the agent to overcome coverage deficiencies or zero-result search queries.
                </div>

                {response.adaptation_history.length === 0 ? (
                  <div className="p-6 rounded-xl border border-dashed border-zinc-200 text-center text-xs text-zinc-400">
                    No adaptive shifts required — initial search strategy satisfied target coverage goals directly.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {response.adaptation_history.map((adapt, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-zinc-200 bg-white space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                            {adapt.adaptation_type}
                          </span>
                          <span className="text-[11px] font-mono text-zinc-400">Shift #{idx + 1}</span>
                        </div>
                        <div className="text-xs font-bold text-zinc-800">{adapt.action_summary}</div>
                        <div className="text-xs text-zinc-500">
                          Identified Gap: <span className="text-zinc-700">{adapt.identified_gap}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Connector Health & Honesty */}
            {activeTab === 'connectors' && (
              <div className="space-y-4">
                <div className="text-xs text-zinc-500">
                  Operational status, transport details, and honest availability reporting for all discovery adapters.
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {response.connector_health.map((ch) => {
                    const isConnected = ch.status === 'CONNECTED';
                    const isMock = ch.status === 'MOCKED_FALLBACK';
                    const isMissing = ch.status === 'UNAVAILABLE_MISSING_BINARY';

                    return (
                      <div key={ch.connector_id} className="p-4 rounded-xl border border-zinc-200 bg-white space-y-2.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-zinc-900">{ch.source_name}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            isConnected
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : isMock
                              ? 'bg-sky-50 text-sky-700 border-sky-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}>
                            {ch.status}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-600">
                          Connector ID: <span className="font-mono text-zinc-800">{ch.connector_id}</span>
                        </div>
                        <div className="text-xs text-zinc-600">
                          Transport Type: <span className="font-mono text-zinc-800">{ch.connector_type}</span>
                        </div>
                        <div className="text-[11px] text-zinc-500">
                          Execution Mode:{' '}
                          <span className={isConnected ? 'text-emerald-700 font-semibold' : isMissing ? 'text-amber-700 font-semibold' : 'text-zinc-700'}>
                            {isConnected ? '🟢 Live Network Transport Verified' : isMissing ? '⚠️ Missing Binary / Prerequisite' : '⚪ Offline Simulated Fixtures'}
                          </span>
                        </div>
                        {ch.details && Object.keys(ch.details).length > 0 && (
                          <div className="text-[10px] text-zinc-600 bg-zinc-50 p-2.5 rounded font-mono border border-zinc-100 overflow-x-auto">
                            <pre>{JSON.stringify(ch.details, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

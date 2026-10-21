'use client';

import React, { useState } from 'react';
import {
  AdaptiveDiscoveryRequest,
  AdaptiveDiscoveryResponse,
  CandidateCareerProfile,
  CareerPathRelationship,
  DegreeLevel,
  EvidenceSourceType,
  OpportunityCategory,
  ConstraintCheckResult,
  WorkflowStage,
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

const STAGES: { id: WorkflowStage; label: string }[] = [
  { id: 'INITIALIZING', label: 'Init' },
  { id: 'STRATEGY_FORMULATION', label: 'Strategy' },
  { id: 'SEARCHING', label: 'Searching' },
  { id: 'EVALUATING', label: 'Evaluating' },
  { id: 'GAP_ANALYSIS', label: 'Gap Analysis' },
  { id: 'ADAPTING', label: 'Adapting' },
  { id: 'FINALIZING', label: 'Finalizing' },
  { id: 'COMPLETED', label: 'Completed' },
];

export function AdaptiveDiscoveryDemo() {
  const [selectedCandidate, setSelectedCandidate] = useState<string>('maya');
  const [targetCoverageGoal, setTargetCoverageGoal] = useState<number>(3);
  const [maxIterations, setMaxIterations] = useState<number>(3);
  const [maxToolCalls, setMaxToolCalls] = useState<number>(10);
  const [simulateFailure, setSimulateFailure] = useState<string>('none');
  const [forceGap, setForceGap] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [response, setResponse] = useState<AdaptiveDiscoveryResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'timeline' | 'adaptations' | 'opportunities' | 'connectors'>('timeline');
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
      };

      const res = await runAdaptiveDiscovery(payload);
      setResponse(res);
      if (res.adaptation_history && res.adaptation_history.length > 0) {
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

  // Map opportunity_id to eligibility result for quick lookup
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
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-violet-500/20 text-violet-300 border border-violet-500/30">
                Milestone 8
              </span>
              <span className="text-xs text-zinc-400">Agent Orchestration & Adaptive Discovery</span>
            </div>
            <h3 className="text-xl font-bold tracking-tight mt-1 text-white">
              Autonomous Adaptive Discovery Coordinator
            </h3>
            <p className="text-xs text-zinc-300 mt-1 max-w-2xl">
              An LLM-driven agent formulates search strategies, executes controlled tools, inspects result
              freshness & coverage, autonomously adapts queries/roles when gaps occur, and subjects all findings
              to deterministic deduplication and eligibility gating.
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium border border-zinc-700 bg-zinc-800 text-zinc-300">
              <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
              Bounded State Machine
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

        {/* Section 1: Candidate Selection & Parameters */}
        <div className="space-y-4">
          <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">
            1. Select Candidate Profile & Orchestration Limits
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(SAMPLE_PROFILES).map(([key, item]) => {
              const isSelected = selectedCandidate === key;
              return (
                <div
                  key={key}
                  onClick={() => setSelectedCandidate(key)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    isSelected
                      ? 'border-violet-600 bg-violet-50/30 ring-1 ring-violet-600'
                      : 'border-zinc-200 bg-white hover:border-zinc-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-900">{item.label}</span>
                    {isSelected && (
                      <span className="text-[10px] uppercase font-bold text-violet-700 bg-violet-100 px-2 py-0.5 rounded">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-600 mt-1.5 leading-relaxed">{item.description}</p>
                </div>
              );
            })}
          </div>

          {/* Workflow Parameters Grid */}
          <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50/50 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-700">Target Coverage Goal</label>
              <input
                type="number"
                min={1}
                max={10}
                value={targetCoverageGoal}
                onChange={(e) => setTargetCoverageGoal(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs font-mono text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <span className="text-[10px] text-zinc-400">Stop when met</span>
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
              <span className="text-[10px] text-zinc-400">Loop budget guard</span>
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
              <span className="text-[10px] text-zinc-400">Cost limit guard</span>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-700">Simulate Source Failure</label>
              <select
                value={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-zinc-200 bg-white text-xs text-zinc-900 focus:outline-none focus:ring-1 focus:ring-violet-500"
              >
                <option value="none">None (All Available)</option>
                <option value="web_search">Web Search Error</option>
                <option value="india_jobs_mcp">India Jobs MCP Error</option>
                <option value="jobspy_mcp">JobSpy MCP Error</option>
                <option value="ats_career_pages">ATS Career Pages Error</option>
              </select>
              <span className="text-[10px] text-zinc-400">Resilience test</span>
            </div>

            <div className="space-y-1 flex flex-col justify-between">
              <div>
                <label className="text-[11px] font-semibold text-zinc-700">Adaptive Decision Trigger</label>
                <div className="flex items-center gap-2 mt-2">
                  <input
                    type="checkbox"
                    id="forceGapToggle"
                    checked={forceGap}
                    onChange={(e) => setForceGap(e.target.checked)}
                    className="h-4 w-4 rounded border-zinc-300 text-violet-600 focus:ring-violet-500"
                  />
                  <label htmlFor="forceGapToggle" className="text-xs text-zinc-700 font-medium cursor-pointer">
                    Force Initial Gap
                  </label>
                </div>
              </div>
              <span className="text-[10px] text-zinc-400">Forces agent into query/role adaptation</span>
            </div>
          </div>

          <div className="flex items-center justify-end pt-2">
            <button
              onClick={handleRunWorkflow}
              disabled={isLoading}
              className="px-5 py-2.5 rounded-lg text-xs font-bold bg-violet-600 hover:bg-violet-700 text-white transition shadow-sm disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Agent Reasoning & Orchestrating...</span>
                </>
              ) : (
                <>
                  <span>▶</span>
                  <span>Execute Adaptive Discovery Workflow</span>
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
                    <span className="text-xs text-zinc-500">Candidate: {response.candidate_id}</span>
                    <span className="text-zinc-300">•</span>
                    <span className="text-xs text-zinc-500">
                      Duration: {Number(response.execution_metadata?.duration_ms || 0).toFixed(1)}ms
                    </span>
                    <span className="text-zinc-300">•</span>
                    <span className="text-xs text-zinc-500">Iterations: {response.iterations_completed}</span>
                    <span className="text-zinc-300">•</span>
                    <span className="text-xs text-zinc-500">Tool Calls: {response.total_tool_calls}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500">Status:</span>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${getTerminationBadgeClass(response.termination_reason)}`}>
                    {response.termination_reason}
                  </span>
                </div>
              </div>

              {/* Progress Stepper */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                  <span>Workflow Execution Stepper</span>
                  <span className="font-mono text-zinc-400">Completed: {response.termination_reason}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-1.5">
                  {STAGES.map((s, idx) => (
                    <div
                      key={idx}
                      className="px-2 py-1.5 rounded-lg border text-center transition bg-violet-50 border-violet-200 text-violet-800 font-bold"
                    >
                      <div className="text-[10px] font-mono text-violet-500">{idx + 1}</div>
                      <div className="text-[11px] truncate">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Key Metrics Counter Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Raw Retrieved</div>
                  <div className="text-lg font-bold text-zinc-900 mt-0.5">{response.total_discovered_raw}</div>
                  <div className="text-[10px] text-zinc-400">Across all sources</div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Canonical Unique</div>
                  <div className="text-lg font-bold text-violet-700 mt-0.5">{response.canonical_count}</div>
                  <div className="text-[10px] text-zinc-400">MinHash LSH deduplicated</div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Eligible Canonical</div>
                  <div className="text-lg font-bold text-emerald-700 mt-0.5">{response.eligible_count}</div>
                  <div className="text-[10px] text-zinc-400">Deterministic gate passed</div>
                </div>

                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] uppercase font-bold text-zinc-500">Adaptation Events</div>
                  <div className="text-lg font-bold text-indigo-700 mt-0.5">{response.adaptation_history.length}</div>
                  <div className="text-[10px] text-zinc-400">Search strategy shifts</div>
                </div>
              </div>
            </div>

            {/* Strategy Card */}
            {response.search_strategy && (
              <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/50 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-zinc-700">
                    Formulated Search Strategy
                  </span>
                  <span className="text-[11px] font-mono text-zinc-500">
                    Goal: {response.search_strategy.target_coverage_goal} eligible listings
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-white border border-zinc-200 text-xs text-zinc-700 leading-relaxed font-sans">
                  <span className="font-semibold text-zinc-900">Agent Rationale: </span>
                  {response.search_strategy.strategy_summary}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-white border border-zinc-200 space-y-1">
                    <span className="text-[11px] font-bold text-zinc-500 uppercase">Target Role Priorities</span>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {response.search_strategy.target_role_priorities.map((r, i) => (
                        <span key={i} className="px-2 py-0.5 rounded text-[11px] font-medium bg-zinc-100 text-zinc-800">
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-white border border-zinc-200 space-y-1">
                    <span className="text-[11px] font-bold text-zinc-500 uppercase">Selected Connectors</span>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {response.search_strategy.selected_connector_ids.map((c, i) => (
                        <span key={i} className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-violet-50 text-violet-700 border border-violet-200">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Tabs */}
            <div className="border-b border-zinc-200 flex items-center gap-4 text-xs font-semibold">
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
                onClick={() => setActiveTab('adaptations')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'adaptations'
                    ? 'border-violet-600 text-violet-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Adaptive Decisions & Gaps ({response.adaptation_history.length})
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
                onClick={() => setActiveTab('connectors')}
                className={`pb-2.5 transition border-b-2 ${
                  activeTab === 'connectors'
                    ? 'border-violet-600 text-violet-700 font-bold'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Connector Health ({response.connector_health.length})
              </button>
            </div>

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
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-zinc-100 text-zinc-700">
                              {evt.stage}
                            </span>
                            <span className="font-bold text-zinc-900">{evt.event_type}</span>
                          </div>
                          {Object.keys(evt.details || {}).length > 0 && (
                            <button
                              onClick={() => setExpandedEventIdx(isExpanded ? null : idx)}
                              className="text-[11px] text-violet-600 hover:text-violet-800 font-medium self-start sm:self-auto"
                            >
                              {isExpanded ? 'Hide Payload' : 'View Payload'}
                            </button>
                          )}
                        </div>
                        <p className="text-zinc-600 mt-1 leading-relaxed">{evt.summary}</p>
                        {isExpanded && (
                          <pre className="mt-2.5 p-3 rounded bg-zinc-900 text-zinc-100 text-[10px] font-mono overflow-x-auto">
                            {JSON.stringify(evt.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 2: Adaptive Decisions & Gaps */}
            {activeTab === 'adaptations' && (
              <div className="space-y-4">
                <div className="text-xs text-zinc-500">
                  When discovery results fail coverage goals or encounter zero results, the agent shifts its search strategy.
                </div>

                {response.adaptation_history.length === 0 ? (
                  <div className="p-8 text-center rounded-xl border border-dashed border-zinc-300 text-xs text-zinc-500">
                    No adaptations were required. Initial queries satisfied the coverage goal of {response.search_strategy?.target_coverage_goal} listings in Iteration 1.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {response.adaptation_history.map((ad, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-indigo-200 bg-indigo-50/20 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-indigo-100 pb-2.5">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-600 text-white">
                              Shift #{idx + 1} (Iter {ad.iteration})
                            </span>
                            <span className="text-xs font-bold text-zinc-900">{ad.adaptation_type}</span>
                          </div>
                          <span className="text-[11px] font-mono text-indigo-700 bg-indigo-100/60 px-2 py-0.5 rounded">
                            Gap: {ad.identified_gap}
                          </span>
                        </div>

                        <div className="text-xs text-zinc-700 leading-relaxed">
                          <span className="font-semibold text-zinc-900">Agent Action: </span>
                          {ad.action_summary}
                        </div>

                        <div className="p-3 rounded-lg bg-white border border-indigo-100 text-[11px] font-mono text-zinc-800 space-y-1">
                          <div className="text-[10px] uppercase font-bold text-zinc-400 font-sans">
                            New Query Formulated
                          </div>
                          <div className="text-xs font-semibold text-zinc-900">
                            Query: &quot;{ad.new_query.query_string}&quot;
                          </div>
                          <div className="text-[10px] text-zinc-500">
                            Target Role: {ad.new_query.role_title} • Target Connectors: {ad.target_connector_ids.join(', ')}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Final Coverage Assessment */}
                {response.coverage_assessment && (
                  <div className="p-4 rounded-xl border border-zinc-200 bg-white space-y-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-zinc-900 uppercase tracking-wider text-[11px]">
                        Final Coverage Assessment
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          response.coverage_assessment.is_coverage_sufficient
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {response.coverage_assessment.is_coverage_sufficient ? 'Coverage Met' : 'Coverage Incomplete'}
                      </span>
                    </div>

                    <div className="text-zinc-600">
                      Total Eligible Canonical: <span className="font-bold text-zinc-900">{response.coverage_assessment.total_eligible_canonical}</span>
                    </div>

                    {Object.keys(response.coverage_assessment.target_role_coverage).length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase text-zinc-400">Coverage by Role</span>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(response.coverage_assessment.target_role_coverage).map(([role, count]) => (
                            <span key={role} className="px-2 py-1 rounded bg-zinc-50 border border-zinc-200 font-mono text-[11px]">
                              {role}: {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {response.coverage_assessment.identified_gaps.length > 0 && (
                      <div className="text-amber-700 font-medium">
                        Identified Gaps: {response.coverage_assessment.identified_gaps.join('; ')}
                      </div>
                    )}

                    <div className="text-zinc-500 text-[11px]">
                      Recommended Directive: <span className="font-mono text-zinc-800 font-bold">{response.coverage_assessment.recommended_action}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Canonical Opportunities & Deterministic Eligibility */}
            {activeTab === 'opportunities' && (
              <div className="space-y-4">
                <div className="text-xs text-zinc-500">
                  Every discovered opportunity is deduplicated via MinHash LSH and evaluated through the deterministic
                  Python eligibility gate (zero LLM evaluation).
                </div>

                {response.canonical_opportunities.length === 0 ? (
                  <div className="p-8 text-center rounded-xl border border-dashed border-zinc-300 text-xs text-zinc-500">
                    No canonical opportunities discovered. Check connector configurations or simulated failure flags.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-4">
                    {response.canonical_opportunities.map((opp) => {
                      const elig = eligibilityMap.get(opp.opportunity_id);
                      const eligStatus = elig ? elig.status : (opp.is_duplicate ? 'DUPLICATE' : 'PENDING');
                      let badgeClass = 'bg-zinc-100 text-zinc-700 border-zinc-200';
                      if (eligStatus === 'ELIGIBLE') {
                        badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                      } else if (eligStatus === 'ELIGIBLE_WITH_UNCERTAINTY') {
                        badgeClass = 'bg-sky-50 text-sky-700 border-sky-200';
                      } else if (eligStatus === 'INELIGIBLE') {
                        badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
                      }

                      // Check if canonical master in cluster
                      const cluster = response.duplicate_clusters[opp.opportunity_id];
                      const clusterSize = cluster ? cluster.cluster_size : 1;

                      return (
                        <div key={opp.opportunity_id} className="p-4 rounded-xl border border-zinc-200 bg-white space-y-3">
                          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-zinc-900">{opp.title}</h4>
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                                  {eligStatus}
                                </span>
                              </div>
                              <div className="text-xs text-zinc-600 mt-0.5">
                                <span className="font-semibold text-zinc-800">{opp.company_name}</span> • {opp.eligibility_rules.location_city_country.join(', ')} ({opp.eligibility_rules.work_mode})
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5 self-start sm:self-auto">
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-zinc-100 text-zinc-600">
                                {opp.mapped_occupation_code}
                              </span>
                              {clusterSize > 1 && (
                                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-violet-50 text-violet-700 border border-violet-200">
                                  Canonical Master ({clusterSize} obs)
                                </span>
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
                                <span className="font-mono">Result: {elig.is_eligible ? 'QUALIFIED' : 'UNQUALIFIED'}</span>
                              </div>
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[10px]">
                                {Object.entries(elig.constraint_checks || {}).map(([key, rawCheck]) => {
                                  const check = rawCheck as ConstraintCheckResult;
                                  return (
                                    <div key={key}>
                                      <span className="text-zinc-400">{key}: </span>
                                      <span className={`font-semibold ${check.status === 'PASSED' ? 'text-emerald-700' : check.status === 'UNCERTAIN' ? 'text-sky-700' : 'text-rose-700'}`}>
                                        {check.status}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                              {elig.uncertainty_caveats && elig.uncertainty_caveats.length > 0 && (
                                <div className="text-[10px] text-sky-700 pt-0.5">
                                  Caveat: {elig.uncertainty_caveats.join('; ')}
                                </div>
                              )}
                              {elig.disqualification_reasons && elig.disqualification_reasons.length > 0 && (
                                <div className="text-[10px] text-rose-700 pt-0.5">
                                  Reason: {elig.disqualification_reasons.join('; ')}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Provenance & Links */}
                          <div className="flex items-center justify-between text-[11px] pt-1">
                            <span className="font-mono text-zinc-400 text-[10px]">
                              ID: {opp.opportunity_id.slice(0, 16)}...
                            </span>
                            <div className="flex items-center gap-3">
                              {opp.source_url && (
                                <a
                                  href={opp.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-violet-600 hover:text-violet-800 font-medium underline"
                                >
                                  Source Listing ↗
                                </a>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Connector Health Breakdown */}
            {activeTab === 'connectors' && (
              <div className="space-y-4">
                <div className="text-xs text-zinc-500">
                  Operational status and transport details of all configured discovery source adapters.
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {response.connector_health.map((ch) => (
                    <div key={ch.connector_id} className="p-4 rounded-xl border border-zinc-200 bg-white space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-zinc-900">{ch.source_name}</span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                          ch.status === 'CONNECTED'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : ch.status === 'MOCKED_FALLBACK'
                            ? 'bg-sky-50 text-sky-700 border-sky-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}>
                          {ch.status}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-600">
                        Type: <span className="font-mono text-zinc-800">{ch.connector_type}</span>
                      </div>
                      <div className="text-[11px] text-zinc-500">
                        Transport: {ch.is_mock_fallback ? 'Offline Safe Adapter' : 'Live Transport Active'}
                      </div>
                      {typeof ch.details?.error_message === 'string' && (
                        <div className="text-[10px] text-rose-600 bg-rose-50 p-2 rounded">
                          {ch.details.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

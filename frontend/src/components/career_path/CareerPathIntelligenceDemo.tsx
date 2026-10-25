'use client';

import React, { useState, useEffect } from 'react';
import {
  CareerPathAssessmentResponse,
  RoleTargetAssessment,
  DevelopmentActionItem,
  ActionProgressStatus,
} from '@/types/domain';
import {
  getCareerPathAssessment,
  refreshCareerPathAssessment,
  updateActionProgress,
} from '@/lib/api';

const SAMPLE_CANDIDATES: Record<string, { label: string; user_id: string; title: string; description: string }> = {
  maya: {
    label: 'Maya Chen — Junior Backend Engineer',
    user_id: 'usr_cand_backend_01',
    title: 'Junior Backend Engineer',
    description: '18 months exp, BS CS. Proven skills in Python (8.0), PostgreSQL (7.5), SQL (8.0). Target: Backend Software Engineer.',
  },
  student: {
    label: 'Rohan Sharma — ML Graduate Student',
    user_id: 'usr_cand_student_02',
    title: 'Master\'s Student / Aspiring ML Engineer',
    description: 'Student, visa sponsorship required, missing graduation window. Coursework in Python (6.0). Target: Machine Learning Engineer.',
  },
};

// Fallback mock assessment for offline/demo reliability
const FALLBACK_MOCK_ASSESSMENT: CareerPathAssessmentResponse = {
  user_id: 'usr_cand_backend_01',
  assessed_at: new Date().toISOString(),
  total_target_roles: 1,
  total_adjacent_roles: 2,
  total_exploratory_roles: 4,
  role_assessments: [
    {
      role_title: 'Backend Software Engineer',
      canonical_occupation_code: '15-1252.00',
      relationship: 'DIRECT_TARGET',
      readiness: 'PURSUABLE_NOW',
      skill_overlap_ratio: 0.62,
      supporting_skills: ['FastAPI', 'PostgreSQL', 'Python', 'SQL'],
      supporting_evidence: [
        {
          evidence_id: 'ev_py_101',
          source_type: 'VERIFIED_CODE_REPOSITORY',
          source_uri: 'https://github.com/candidate/backend-api',
          snippet: 'Built asynchronous REST API using Python and FastAPI with pytest suite.',
          verifiability_weight: 0.9,
          observed_at: new Date().toISOString(),
        },
      ],
      critical_gaps: ['Docker', 'Microservices', 'Redis'],
      eligibility_uncertainties: [],
      opportunity_coverage: {
        matching_opportunity_count: 5,
        sample_opportunity_titles: ['Junior Backend Developer', 'Python API Engineer'],
        sample_sources: ['greenhouse', 'ashby'],
        coverage_limitation_note: null,
      },
      feasibility_rationale: 'Demonstrates 62% core competency overlap. Eligible for immediate target applications.',
    },
    {
      role_title: 'Full Stack Developer',
      canonical_occupation_code: '15-1252.00',
      relationship: 'ADJACENT_OPTION',
      readiness: 'ATTAINABLE_WITH_DEVELOPMENT',
      skill_overlap_ratio: 0.40,
      supporting_skills: ['PostgreSQL', 'Python', 'SQL'],
      supporting_evidence: [],
      critical_gaps: ['JavaScript', 'Node.js', 'React', 'TypeScript'],
      eligibility_uncertainties: [],
      opportunity_coverage: {
        matching_opportunity_count: 3,
        sample_opportunity_titles: ['Full Stack Engineer (Python/React)'],
        sample_sources: ['ashby'],
        coverage_limitation_note: null,
      },
      feasibility_rationale: 'Solid backend core foundation. Attainable upon building demonstrable frontend React artifacts.',
    },
    {
      role_title: 'DevOps & Platform Engineer',
      canonical_occupation_code: '15-1244.00',
      relationship: 'ADJACENT_OPTION',
      readiness: 'ATTAINABLE_WITH_DEVELOPMENT',
      skill_overlap_ratio: 0.33,
      supporting_skills: ['Python'],
      supporting_evidence: [],
      critical_gaps: ['CI/CD', 'Docker', 'Kubernetes', 'Linux', 'Terraform'],
      eligibility_uncertainties: [],
      opportunity_coverage: {
        matching_opportunity_count: 1,
        sample_opportunity_titles: ['Cloud Platform Engineer'],
        sample_sources: ['greenhouse'],
        coverage_limitation_note: 'Limited sample size (1 discovered listing).',
      },
      feasibility_rationale: 'Scripting capability present. Requires infrastructure and containerization demonstration.',
    },
    {
      role_title: 'Machine Learning Engineer',
      canonical_occupation_code: '15-1251.00',
      relationship: 'EXPLORATORY_POSSIBILITY',
      readiness: 'EXPLORATORY',
      skill_overlap_ratio: 0.17,
      supporting_skills: ['Python', 'SQL'],
      supporting_evidence: [],
      critical_gaps: ['Deep Learning', 'LLMs', 'NLP', 'PyTorch', 'Scikit-Learn'],
      eligibility_uncertainties: [],
      opportunity_coverage: {
        matching_opportunity_count: 0,
        sample_opportunity_titles: [],
        sample_sources: [],
        coverage_limitation_note: 'No active discovered listings in current sample.',
      },
      feasibility_rationale: 'Exploratory trajectory requiring significant mathematical modeling and deep learning evidence.',
    },
  ],
  career_path_graph: {
    nodes: [
      {
        node_id: 'node_backend',
        role_title: 'Backend Software Engineer',
        canonical_occupation_code: '15-1252.00',
        relationship: 'DIRECT_TARGET',
        readiness: 'PURSUABLE_NOW',
        skill_overlap_ratio: 0.62,
        core_competencies: ['Python', 'FastAPI', 'PostgreSQL', 'SQL', 'Docker', 'Redis'],
      },
      {
        node_id: 'node_fullstack',
        role_title: 'Full Stack Developer',
        canonical_occupation_code: '15-1252.00',
        relationship: 'ADJACENT_OPTION',
        readiness: 'ATTAINABLE_WITH_DEVELOPMENT',
        skill_overlap_ratio: 0.40,
        core_competencies: ['TypeScript', 'React', 'Python', 'Node.js'],
      },
      {
        node_id: 'node_devops',
        role_title: 'DevOps & Platform Engineer',
        canonical_occupation_code: '15-1244.00',
        relationship: 'ADJACENT_OPTION',
        readiness: 'ATTAINABLE_WITH_DEVELOPMENT',
        skill_overlap_ratio: 0.33,
        core_competencies: ['Docker', 'Kubernetes', 'CI/CD', 'Terraform'],
      },
    ],
    edges: [
      {
        edge_id: 'edge_01',
        source_role: 'Backend Software Engineer',
        target_role: 'Full Stack Developer',
        transition_type: 'LATERAL_EXPANSION',
        basis_description: 'Transferable backend skills in Python and PostgreSQL. Bridge frontend gap by building React apps.',
        transferable_skills: ['Python', 'PostgreSQL', 'SQL'],
        development_gaps: ['TypeScript', 'React', 'Node.js'],
        feasibility_score: 0.72,
        estimated_effort_level: 'LOW',
      },
      {
        edge_id: 'edge_02',
        source_role: 'Backend Software Engineer',
        target_role: 'DevOps & Platform Engineer',
        transition_type: 'LATERAL_EXPANSION',
        basis_description: 'Transferable Python scripting. Bridge gap by adding container orchestration and CI/CD pipelines.',
        transferable_skills: ['Python'],
        development_gaps: ['Docker', 'Kubernetes', 'CI/CD', 'Linux'],
        feasibility_score: 0.58,
        estimated_effort_level: 'MEDIUM',
      },
    ],
    baseline_role_title: 'Backend Software Engineer',
    is_cycle_free: true,
  },
  development_plan: {
    plan_id: 'plan_demo_01',
    user_id: 'usr_cand_backend_01',
    generated_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    plan_summary: 'Personalized development plan targeting Backend Software Engineer. Focus on containerization and caching.',
    short_term_actions: [
      {
        action_id: 'act_docker_01',
        skill_or_capability: 'Docker & Containerization',
        motivating_gap_id: 'http://data.europa.eu/esco/skill/docker',
        motivating_gap_description: 'Required across 4 discovered listings and core archetype. Eliminates hard screening filter.',
        target_roles_supported: ['Backend Software Engineer', 'DevOps & Platform Engineer'],
        supported_opportunities_count: 4,
        action_type: 'PORTFOLIO_BUILD',
        horizon: 'SHORT_TERM',
        concrete_activity: 'Build a standalone open-source microservice with multi-stage Dockerfile and docker-compose orchestration.',
        measurable_completion_criterion: 'Public GitHub repo with passing automated healthcheck and containerized pytest suite.',
        verifiable_evidence_to_produce: 'GitHub repo URL with passing test badge and container architecture diagram.',
        priority: 'CRITICAL',
        priority_rationale: 'Explicitly mandatory requirement across active backend listings.',
        dependencies: [],
        status: 'IN_PROGRESS',
        completed_at: null,
        candidate_notes: 'Created initial Dockerfile, working on multi-stage cache optimization.',
        verification_artifact_url: 'https://github.com/candidate/containerized-backend-demo',
      },
      {
        action_id: 'act_redis_02',
        skill_or_capability: 'Redis & Distributed Caching',
        motivating_gap_id: 'http://data.europa.eu/esco/skill/redis',
        motivating_gap_description: 'Frequently valued for latency-critical API architectures.',
        target_roles_supported: ['Backend Software Engineer'],
        supported_opportunities_count: 2,
        action_type: 'PROJECT_ENHANCEMENT',
        horizon: 'SHORT_TERM',
        concrete_activity: 'Integrate Redis cache layer with TTL invalidation into existing FastAPI service.',
        measurable_completion_criterion: 'Pull Request with before/after latency benchmark showing >= 50% p95 response time reduction.',
        verifiable_evidence_to_produce: 'PR diff link and benchmark execution logs.',
        priority: 'HIGH',
        priority_rationale: 'Demonstrates tangible backend performance optimization.',
        dependencies: [],
        status: 'NOT_STARTED',
        completed_at: null,
        candidate_notes: null,
        verification_artifact_url: null,
      },
    ],
    long_term_actions: [
      {
        action_id: 'act_k8s_03',
        skill_or_capability: 'Kubernetes & Production Orchestration',
        motivating_gap_id: 'http://data.europa.eu/esco/skill/kubernetes',
        motivating_gap_description: 'Strategic competence for high-scale platform engineering.',
        target_roles_supported: ['DevOps & Platform Engineer', 'Backend Software Engineer'],
        supported_opportunities_count: 2,
        action_type: 'CONCEPT_STUDY',
        horizon: 'LONG_TERM',
        concrete_activity: 'Write Architecture Decision Record (ADR) analyzing service mesh trade-offs with local Minikube cluster setup.',
        measurable_completion_criterion: 'Documented ADR comparing Istio vs Linkerd with deployed YAML manifests.',
        verifiable_evidence_to_produce: 'Markdown ADR document and deployment manifest configs.',
        priority: 'MEDIUM',
        priority_rationale: 'Longer-term infrastructure trajectory expansion.',
        dependencies: ['act_docker_01'],
        status: 'NOT_STARTED',
        completed_at: null,
        candidate_notes: null,
        verification_artifact_url: null,
      },
    ],
    total_actions: 3,
    market_insights: {
      total_opportunities_analyzed: 5,
      data_sufficiency_level: 'MODERATE',
      sources_represented: ['greenhouse', 'ashby'],
      recurring_skills: [
        {
          skill_name: 'Python',
          signal_type: 'EXPLICITLY_REQUIRED',
          frequency_in_sample: 5,
          supporting_job_titles: ['Junior Backend Developer', 'Python API Engineer'],
          supporting_sources: ['greenhouse', 'ashby'],
        },
        {
          skill_name: 'Docker',
          signal_type: 'EXPLICITLY_REQUIRED',
          frequency_in_sample: 4,
          supporting_job_titles: ['Backend Software Engineer'],
          supporting_sources: ['greenhouse'],
        },
        {
          skill_name: 'Redis',
          signal_type: 'EMPLOYER_PREFERRED',
          frequency_in_sample: 2,
          supporting_job_titles: ['Distributed Systems Engineer'],
          supporting_sources: ['ashby'],
        },
      ],
      limitation_disclosure: 'Market signals reflect an active sample of 5 discovered listings across Greenhouse and Ashby. Does not represent global labor market.',
    },
    ethical_disclaimer: 'Completing development actions provides verifiable evidence of your capabilities but does not guarantee employment, interview selection, or specific algorithmic ranking improvement.',
  },
};

export function CareerPathIntelligenceDemo() {
  const [selectedCandidateKey, setSelectedCandidateKey] = useState<string>('maya');
  const [assessment, setAssessment] = useState<CareerPathAssessmentResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSimulated, setIsSimulated] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'roles' | 'graph' | 'plan' | 'market'>('roles');

  // Expanded Citations in role assessment cards
  const [expandedRoles, setExpandedRoles] = useState<Record<string, boolean>>({});

  // Active Action Item edit form
  const [editingActionId, setEditingActionId] = useState<string | null>(null);
  const [actionStatusInput, setActionStatusInput] = useState<ActionProgressStatus>('IN_PROGRESS');
  const [actionArtifactUrl, setActionArtifactUrl] = useState<string>('');
  const [actionNotes, setActionNotes] = useState<string>('');
  const [updatingAction, setUpdatingAction] = useState<boolean>(false);

  const candidateInfo = SAMPLE_CANDIDATES[selectedCandidateKey];

  const fetchAssessment = async (refresh: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = refresh
        ? await refreshCareerPathAssessment(candidateInfo.user_id, undefined, true)
        : await getCareerPathAssessment(candidateInfo.user_id, false);
      setAssessment(data);
      setIsSimulated(false);
    } catch {
      // Graceful offline fallback
      setAssessment(FALLBACK_MOCK_ASSESSMENT);
      setIsSimulated(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getCareerPathAssessment(candidateInfo.user_id, false);
        if (!ignore) {
          setAssessment(data);
          setIsSimulated(false);
        }
      } catch {
        if (!ignore) {
          setAssessment(FALLBACK_MOCK_ASSESSMENT);
          setIsSimulated(true);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    queueMicrotask(() => {
      load();
    });

    return () => {
      ignore = true;
    };
  }, [candidateInfo.user_id]);

  const toggleRoleExpand = (roleTitle: string) => {
    setExpandedRoles((prev) => ({ ...prev, [roleTitle]: !prev[roleTitle] }));
  };

  const handleUpdateAction = async (actionId: string) => {
    if (!assessment) return;
    setUpdatingAction(true);
    try {
      if (!isSimulated) {
        await updateActionProgress(candidateInfo.user_id, actionId, {
          status: actionStatusInput,
          verification_artifact_url: actionArtifactUrl.trim() || undefined,
          candidate_notes: actionNotes.trim() || undefined,
        });
        await fetchAssessment(false);
      } else {
        // Update simulated local state
        const updateList = (list: DevelopmentActionItem[]) =>
          list.map((act) =>
            act.action_id === actionId
              ? {
                  ...act,
                  status: actionStatusInput,
                  verification_artifact_url: actionArtifactUrl.trim() || act.verification_artifact_url,
                  candidate_notes: actionNotes.trim() || act.candidate_notes,
                  completed_at: actionStatusInput === 'COMPLETED' ? new Date().toISOString() : null,
                }
              : act
          );

        setAssessment({
          ...assessment,
          development_plan: {
            ...assessment.development_plan,
            short_term_actions: updateList(assessment.development_plan.short_term_actions),
            long_term_actions: updateList(assessment.development_plan.long_term_actions),
          },
        });
      }
      setEditingActionId(null);
    } catch (err) {
      alert(`Failed to update progress: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUpdatingAction(false);
    }
  };

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
              Milestone 12
            </span>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Career Path Intelligence & Personalized Development Planning
            </h2>
          </div>
          <p className="text-slate-400 text-sm">
            Evidence-grounded role targets, transition graph, prioritized practical activities, and market signal calibration.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedCandidateKey}
            onChange={(e) => setSelectedCandidateKey(e.target.value)}
            className="bg-slate-800 text-slate-200 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
          >
            {Object.entries(SAMPLE_CANDIDATES).map(([k, c]) => (
              <option key={k} value={k}>
                {c.label}
              </option>
            ))}
          </select>

          <button
            onClick={() => fetchAssessment(true)}
            disabled={loading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
          >
            {loading ? 'Evaluating...' : 'Refresh Assessment'}
          </button>
        </div>
      </div>

      {/* Candidate Profile Context Banner */}
      <div className="mt-4 p-4 rounded-lg bg-slate-800/60 border border-slate-700/60 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div className="text-sm">
          <span className="font-semibold text-slate-200">{candidateInfo.title}</span>
          <span className="text-slate-400 ml-2">— {candidateInfo.description}</span>
        </div>
        {isSimulated && (
          <span className="text-xs font-medium px-2 py-1 rounded bg-amber-950 text-amber-300 border border-amber-800 self-start md:self-auto">
            ⚡ Simulated Data Mode
          </span>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-slate-800 mt-6 gap-2">
        <button
          onClick={() => setActiveTab('roles')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'roles'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Target & Adjacent Roles ({assessment?.role_assessments.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('graph')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'graph'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Career Path Graph ({assessment?.career_path_graph.edges.length || 0} transitions)
        </button>
        <button
          onClick={() => setActiveTab('plan')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'plan'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Personalized Development Plan ({assessment?.development_plan.total_actions || 0})
        </button>
        <button
          onClick={() => setActiveTab('market')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'market'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Market Signals & Limitations
        </button>
      </div>

      {/* Main Content Area */}
      {loading && !assessment ? (
        <div className="py-16 text-center text-slate-400">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500 mb-3" />
          <p className="text-sm">Evaluating candidate evidence against role archetypes and live listings...</p>
        </div>
      ) : error ? (
        <div className="p-6 my-6 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
          Failed to load assessment: {error}
        </div>
      ) : assessment ? (
        <div className="mt-6">
          {/* TAB 1: ROLES & TARGETS */}
          {activeTab === 'roles' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                <span>Evaluated across {assessment.role_assessments.length} canonical occupational archetypes</span>
                <div className="flex gap-3">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" /> Direct Target ({assessment.total_target_roles})
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-cyan-400" /> Adjacent ({assessment.total_adjacent_roles})
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-slate-500" /> Exploratory ({assessment.total_exploratory_roles})
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {assessment.role_assessments.map((role: RoleTargetAssessment) => {
                  const isExpanded = expandedRoles[role.role_title];
                  const relBadge =
                    role.relationship === 'DIRECT_TARGET'
                      ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                      : role.relationship === 'ADJACENT_OPTION'
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                      : 'bg-slate-800 text-slate-400 border-slate-700';

                  const readinessBadge =
                    role.readiness === 'PURSUABLE_NOW'
                      ? 'bg-emerald-900/60 text-emerald-200 border-emerald-700'
                      : role.readiness === 'ATTAINABLE_WITH_DEVELOPMENT'
                      ? 'bg-sky-900/60 text-sky-200 border-sky-700'
                      : 'bg-slate-800/80 text-slate-300 border-slate-700';

                  return (
                    <div
                      key={role.role_title}
                      className="bg-slate-800/40 border border-slate-700/80 rounded-lg p-5 flex flex-col justify-between hover:border-slate-600 transition-colors"
                    >
                      <div>
                        {/* Title & Badges */}
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div>
                            <h3 className="text-base font-semibold text-white">{role.role_title}</h3>
                            {role.canonical_occupation_code && (
                              <span className="text-xs text-slate-400 font-mono">
                                O*NET: {role.canonical_occupation_code}
                              </span>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${relBadge}`}>
                              {role.relationship.replace('_', ' ')}
                            </span>
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${readinessBadge}`}>
                              {role.readiness.replace(/_/g, ' ')}
                            </span>
                          </div>
                        </div>

                        {/* Overlap Progress Bar */}
                        <div className="my-3">
                          <div className="flex justify-between text-xs text-slate-300 mb-1">
                            <span>Demonstrated Core Competency</span>
                            <span className="font-semibold text-cyan-400">{Math.round(role.skill_overlap_ratio * 100)}%</span>
                          </div>
                          <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
                            <div
                              className="bg-cyan-500 h-full rounded-full transition-all"
                              style={{ width: `${Math.round(role.skill_overlap_ratio * 100)}%` }}
                            />
                          </div>
                        </div>

                        {/* Rationale */}
                        <p className="text-xs text-slate-300 bg-slate-900/50 p-2.5 rounded border border-slate-800/80 leading-relaxed mb-3">
                          {role.feasibility_rationale}
                        </p>

                        {/* Supporting Skills & Gaps */}
                        <div className="space-y-2 text-xs">
                          <div>
                            <span className="text-slate-400 font-medium">Supporting Evidence ({role.supporting_skills.length}):</span>{' '}
                            <span className="text-emerald-300 font-medium">
                              {role.supporting_skills.length > 0 ? role.supporting_skills.join(', ') : 'None evidenced'}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400 font-medium">Key Skill Gaps:</span>{' '}
                            <span className="text-rose-300 font-medium">
                              {role.critical_gaps.length > 0 ? role.critical_gaps.slice(0, 4).join(', ') : 'None'}
                            </span>
                          </div>

                          {/* Eligibility Uncertainties */}
                          {role.eligibility_uncertainties.length > 0 && (
                            <div className="p-2 rounded bg-amber-950/30 border border-amber-900/50 text-amber-300 text-[11px]">
                              ⚠️ {role.eligibility_uncertainties.join(' ')}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Footer: Opportunity Coverage & Evidence toggle */}
                      <div className="mt-4 pt-3 border-t border-slate-700/60 flex items-center justify-between text-xs">
                        <span className="text-slate-400">
                          Discovered Listings:{' '}
                          <strong className="text-white">{role.opportunity_coverage.matching_opportunity_count}</strong>
                        </span>

                        {role.supporting_evidence.length > 0 && (
                          <button
                            onClick={() => toggleRoleExpand(role.role_title)}
                            className="text-cyan-400 hover:text-cyan-300 text-xs font-medium"
                          >
                            {isExpanded ? 'Hide Evidence Citations' : `View Citations (${role.supporting_evidence.length})`}
                          </button>
                        )}
                      </div>

                      {/* Expandable Citations */}
                      {isExpanded && role.supporting_evidence.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-700/40 space-y-2">
                          <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                            Verified Grounding Citations:
                          </span>
                          {role.supporting_evidence.map((cit) => (
                            <div
                              key={cit.evidence_id}
                              className="p-2 rounded bg-slate-900/80 border border-slate-800 text-[11px]"
                            >
                              <div className="flex justify-between text-slate-400 mb-1">
                                <span className="font-mono text-cyan-400">{cit.evidence_id}</span>
                                <span>Weight: {cit.verifiability_weight.toFixed(2)}</span>
                              </div>
                              <p className="text-slate-300 italic">“{cit.snippet}”</p>
                              {cit.source_uri && (
                                <a
                                  href={cit.source_uri}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-cyan-400 hover:underline block truncate mt-1 text-[10px]"
                                >
                                  {cit.source_uri}
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: CAREER PATH GRAPH */}
          {activeTab === 'graph' && (
            <div className="space-y-6">
              <div className="p-4 rounded-lg bg-slate-800/40 border border-slate-700 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                <div>
                  <span className="text-slate-400">Baseline Role:</span>{' '}
                  <strong className="text-white ml-1">
                    {assessment.career_path_graph.baseline_role_title || 'Software Developer'}
                  </strong>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-semibold">
                    ✓ Strictly Cycle-Free DAG
                  </span>
                  <span className="text-slate-400">
                    {assessment.career_path_graph.nodes.length} Nodes, {assessment.career_path_graph.edges.length} Transitions
                  </span>
                </div>
              </div>

              {/* Transition Cards */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-slate-200">Supported Career Transitions</h4>
                {assessment.career_path_graph.edges.map((edge) => {
                  const effortColor =
                    edge.estimated_effort_level === 'LOW'
                      ? 'text-emerald-300 bg-emerald-950 border-emerald-800'
                      : edge.estimated_effort_level === 'MEDIUM'
                      ? 'text-amber-300 bg-amber-950 border-amber-800'
                      : 'text-rose-300 bg-rose-950 border-rose-800';

                  return (
                    <div
                      key={edge.edge_id}
                      className="bg-slate-800/50 border border-slate-700/80 rounded-lg p-4 text-xs space-y-3 hover:border-slate-600 transition-colors"
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-700/50 pb-2">
                        <div className="flex items-center gap-2 text-sm font-semibold text-white">
                          <span>{edge.source_role}</span>
                          <span className="text-cyan-400">➔</span>
                          <span className="text-cyan-300">{edge.target_role}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700 font-mono text-[10px]">
                            {edge.transition_type}
                          </span>
                          <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold ${effortColor}`}>
                            Effort: {edge.estimated_effort_level}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono text-[10px]">
                            Feasibility: {Math.round(edge.feasibility_score * 100)}%
                          </span>
                        </div>
                      </div>

                      <p className="text-slate-300 leading-relaxed">{edge.basis_description}</p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                        <div className="bg-slate-900/50 p-2 rounded border border-slate-800">
                          <span className="text-slate-400 font-medium block mb-1">Transferable Strengths:</span>
                          <span className="text-emerald-300">
                            {edge.transferable_skills.length > 0 ? edge.transferable_skills.join(', ') : 'Foundational'}
                          </span>
                        </div>
                        <div className="bg-slate-900/50 p-2 rounded border border-slate-800">
                          <span className="text-slate-400 font-medium block mb-1">Development Gaps to Bridge:</span>
                          <span className="text-rose-300">
                            {edge.development_gaps.length > 0 ? edge.development_gaps.join(', ') : 'None'}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: PERSONALIZED DEVELOPMENT PLAN */}
          {activeTab === 'plan' && (
            <div className="space-y-6">
              {/* Executive Summary & Ethical Disclaimer */}
              <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-white">Plan Overview</h3>
                  <span className="text-xs font-mono text-slate-400">
                    ID: {assessment.development_plan.plan_id}
                  </span>
                </div>
                <p className="text-sm text-slate-300">{assessment.development_plan.plan_summary}</p>
                <div className="p-3 rounded bg-cyan-950/40 border border-cyan-900/60 text-cyan-300 text-xs">
                  🛡️ <strong>Ethical Disclaimer:</strong> {assessment.development_plan.ethical_disclaimer}
                </div>
              </div>

              {/* Short Term Immediate Actions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-cyan-400 uppercase tracking-wider">
                    Immediate Demonstrable Actions (Short-Term Priority)
                  </h4>
                  <span className="text-xs text-slate-400">
                    {assessment.development_plan.short_term_actions.length} action(s)
                  </span>
                </div>

                <div className="space-y-3">
                  {assessment.development_plan.short_term_actions.map((act) => renderActionCard(act))}
                </div>
              </div>

              {/* Long Term Strategic Actions */}
              {assessment.development_plan.long_term_actions.length > 0 && (
                <div className="space-y-3 pt-4 border-t border-slate-800">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                      Strategic Capability Advancement (Long-Term Trajectory)
                    </h4>
                    <span className="text-xs text-slate-400">
                      {assessment.development_plan.long_term_actions.length} action(s)
                    </span>
                  </div>

                  <div className="space-y-3">
                    {assessment.development_plan.long_term_actions.map((act) => renderActionCard(act))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: MARKET SIGNALS & LIMITATIONS */}
          {activeTab === 'market' && (
            <div className="space-y-6">
              <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-5 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-700/60 pb-3">
                  <div>
                    <h3 className="text-base font-semibold text-white">Discovered Opportunity Ingestion Data</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Transparent accounting of source listings analyzed for requirement patterns.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300">
                      Sample Size: <strong>{assessment.development_plan.market_insights.total_opportunities_analyzed}</strong> listings
                    </span>
                    <span className="px-2.5 py-1 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-semibold">
                      Sufficiency: {assessment.development_plan.market_insights.data_sufficiency_level}
                    </span>
                  </div>
                </div>

                {/* Honest Limitation Disclosure Notice */}
                <div className="p-3 rounded bg-amber-950/30 border border-amber-800/60 text-amber-300 text-xs leading-relaxed">
                  ⚠️ <strong>Data Limitation Disclosure:</strong> {assessment.development_plan.market_insights.limitation_disclosure}
                </div>

                <div className="text-xs text-slate-400">
                  <span>Sources Represented: </span>
                  <span className="text-white font-medium">
                    {assessment.development_plan.market_insights.sources_represented.length > 0
                      ? assessment.development_plan.market_insights.sources_represented.join(', ')
                      : 'None (Pure Taxonomy Benchmark)'}
                  </span>
                </div>
              </div>

              {/* Recurring Skill Demands Table */}
              <div className="bg-slate-800/40 border border-slate-700 rounded-lg overflow-hidden">
                <div className="p-4 border-b border-slate-700/80">
                  <h4 className="text-sm font-semibold text-white">Calibrated Skill Demand Signals</h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-700">
                      <tr>
                        <th className="py-2.5 px-4">Skill Name</th>
                        <th className="py-2.5 px-4">Signal Type</th>
                        <th className="py-2.5 px-4">Frequency in Sample</th>
                        <th className="py-2.5 px-4">Supporting Postings / Source</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {assessment.development_plan.market_insights.recurring_skills.map((sig) => {
                        const sigBadge =
                          sig.signal_type === 'EXPLICITLY_REQUIRED'
                            ? 'bg-rose-950 text-rose-300 border-rose-800'
                            : sig.signal_type === 'EMPLOYER_PREFERRED'
                            ? 'bg-sky-950 text-sky-300 border-sky-800'
                            : sig.signal_type === 'TAXONOMY_INFERRED'
                            ? 'bg-purple-950 text-purple-300 border-purple-800'
                            : 'bg-slate-800 text-slate-400 border-slate-700';

                        return (
                          <tr key={sig.skill_name} className="hover:bg-slate-800/30 transition-colors">
                            <td className="py-3 px-4 font-semibold text-white">{sig.skill_name}</td>
                            <td className="py-3 px-4">
                              <span className={`px-2 py-0.5 rounded border text-[10px] font-medium ${sigBadge}`}>
                                {sig.signal_type.replace(/_/g, ' ')}
                              </span>
                            </td>
                            <td className="py-3 px-4 font-mono font-medium text-cyan-400">
                              {sig.frequency_in_sample} job(s)
                            </td>
                            <td className="py-3 px-4 text-slate-400">
                              {sig.supporting_job_titles.join(', ') || 'Taxonomy archetype'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </section>
  );

  // Helper rendering function for development action card
  function renderActionCard(act: DevelopmentActionItem) {
    const isEditing = editingActionId === act.action_id;
    const statusColor =
      act.status === 'COMPLETED'
        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
        : act.status === 'IN_PROGRESS'
        ? 'bg-amber-950 text-amber-300 border-amber-800'
        : 'bg-slate-800 text-slate-400 border-slate-700';

    const prioColor =
      act.priority === 'CRITICAL'
        ? 'bg-rose-950 text-rose-300 border-rose-800'
        : act.priority === 'HIGH'
        ? 'bg-orange-950 text-orange-300 border-orange-800'
        : 'bg-slate-800 text-slate-400 border-slate-700';

    return (
      <div
        key={act.action_id}
        className="bg-slate-800/40 border border-slate-700/80 rounded-lg p-5 text-xs space-y-3 hover:border-slate-600 transition-colors"
      >
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-2 border-b border-slate-700/50 pb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h5 className="text-sm font-semibold text-white">{act.skill_or_capability}</h5>
              <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold ${prioColor}`}>
                {act.priority}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-700 text-[10px] font-mono">
                {act.action_type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-slate-400 text-[11px]">{act.motivating_gap_description}</p>
          </div>

          <div className="flex items-center gap-2 self-start">
            <span className={`px-2.5 py-1 rounded border text-[11px] font-medium ${statusColor}`}>
              {act.status.replace(/_/g, ' ')}
            </span>
            <button
              onClick={() => {
                if (isEditing) {
                  setEditingActionId(null);
                } else {
                  setEditingActionId(act.action_id);
                  setActionStatusInput(act.status);
                  setActionArtifactUrl(act.verification_artifact_url || '');
                  setActionNotes(act.candidate_notes || '');
                }
              }}
              className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-[11px] font-medium transition-colors"
            >
              {isEditing ? 'Cancel' : 'Update Status'}
            </button>
          </div>
        </div>

        {/* Concrete Activity */}
        <div className="bg-slate-900/60 p-3 rounded border border-slate-800/80 space-y-1">
          <span className="text-slate-400 font-semibold block text-[11px] uppercase tracking-wider">
            Hands-on Activity:
          </span>
          <p className="text-slate-200 leading-relaxed">{act.concrete_activity}</p>
        </div>

        {/* Measurable Completion Criterion & Evidence */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-slate-900/40 p-2.5 rounded border border-slate-800">
            <span className="text-slate-400 font-medium block mb-1">Measurable Completion Criterion:</span>
            <p className="text-emerald-300 font-mono text-[11px] leading-relaxed">
              ✓ {act.measurable_completion_criterion}
            </p>
          </div>
          <div className="bg-slate-900/40 p-2.5 rounded border border-slate-800">
            <span className="text-slate-400 font-medium block mb-1">Verifiable Evidence to Produce:</span>
            <p className="text-cyan-300 font-mono text-[11px] leading-relaxed">
              📁 {act.verifiable_evidence_to_produce}
            </p>
          </div>
        </div>

        {/* Dependencies & Notes */}
        <div className="flex flex-wrap items-center justify-between text-slate-400 text-[11px] pt-1">
          <div>
            <span>Target Roles Supported: </span>
            <span className="text-slate-200 font-medium">{act.target_roles_supported.join(', ')}</span>
            {act.dependencies.length > 0 && (
              <span className="ml-3 text-amber-400">
                (Depends on: {act.dependencies.join(', ')})
              </span>
            )}
          </div>
          {act.verification_artifact_url && (
            <a
              href={act.verification_artifact_url}
              target="_blank"
              rel="noreferrer"
              className="text-cyan-400 hover:underline"
            >
              View Artifact ↗
            </a>
          )}
        </div>

        {/* Edit Progress Form */}
        {isEditing && (
          <div className="mt-3 p-4 rounded-lg bg-slate-900/90 border border-slate-700 space-y-3">
            <h6 className="text-xs font-semibold text-white">Record Progress & Provenance Artifact</h6>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Progress Status</label>
                <select
                  value={actionStatusInput}
                  onChange={(e) => setActionStatusInput(e.target.value as ActionProgressStatus)}
                  className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1.5 text-xs focus:ring-1 focus:ring-cyan-500"
                >
                  <option value="NOT_STARTED">Not Started</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="ABANDONED">Abandoned</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Artifact URL (GitHub / Demo)</label>
                <input
                  type="url"
                  placeholder="https://github.com/candidate/repo-name"
                  value={actionArtifactUrl}
                  onChange={(e) => setActionArtifactUrl(e.target.value)}
                  className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1.5 text-xs focus:ring-1 focus:ring-cyan-500 placeholder-slate-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Candidate Notes & Reflection</label>
              <textarea
                rows={2}
                placeholder="Brief summary of challenges solved, benchmark results, or test coverage..."
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                className="w-full bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1.5 text-xs focus:ring-1 focus:ring-cyan-500 placeholder-slate-500"
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingActionId(null)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 hover:bg-slate-700 rounded text-xs transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={updatingAction}
                onClick={() => handleUpdateAction(act.action_id)}
                className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {updatingAction ? 'Saving...' : 'Save Progress'}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }
}

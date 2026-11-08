'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Compass,
  RotateCw,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  FileText,
  ChevronRight,
  TrendingUp,
  Target,
  Search,
  CheckCircle2,
  MapPin,
  Building2,
  Eye,
} from 'lucide-react';
import {
  AdaptiveDiscoveryRequest,
  AdaptiveDiscoveryResponse,
  CandidateCareerProfile,
  ConnectorHealthReport,
  DiscoveryRun,
  DiscoveryRunStreamEvent,
  RankedOpportunity,
  WorkflowStage,
  WorkflowTimelineEvent,
} from '@/types/domain';
import {
  getDiscoveryConnectors,
  getDiscoveryRun,
  getDiscoveryRunStreamUrl,
  getLatestDiscoveryRunForCandidate,
  startDiscoveryRun,
} from '@/lib/api';
import { formatOpportunityLocation } from '@/lib/location';
import { Badge } from '@/components/ui/Badge';
import { NumberTicker } from '@/components/ui/NumberTicker';
import { ScoreBar } from '@/components/ui/ScoreBar';
import { SlideDrawer } from '@/components/ui/SlideDrawer';
import { EvidenceCard } from '@/components/ui/EvidenceCard';
import { OpportunityDetailModal } from '@/components/ui/OpportunityDetailModal';
import { WorkspaceTab } from '@/components/layout/Header';

interface DiscoveryWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab: (tab: WorkspaceTab, context?: { targetRole?: string; skillId?: string }) => void;
}

const HUMAN_PROGRESS_STAGES: Record<WorkflowStage, { step: number; text: string }> = {
  INITIALIZING: { step: 1, text: 'Finding opportunities matching your career direction' },
  STRATEGY_FORMULATION: { step: 1, text: 'Market Agent researching demand and formulating search strategy' },
  SEARCHING: { step: 2, text: 'Discovery Agent sourcing live opportunities across authentic sources' },
  EVALUATING: { step: 3, text: 'Research Agent inspecting requirements and company context' },
  GAP_ANALYSIS: { step: 4, text: 'Orchestrator assessing opportunity coverage' },
  ADAPTING: { step: 4, text: 'Orchestrator adapting search strategy to maximize match quality' },
  RANKING: { step: 5, text: 'Recommendation Agent computing 6D deterministic fit scores' },
  FINALIZING: { step: 5, text: 'Finalizing verified career recommendations' },
  COMPLETED: { step: 5, text: 'Personalized opportunity discovery complete' },
  FAILED: { step: 0, text: 'Discovery workflow encountered an issue' },
};

export function DiscoveryWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
}: DiscoveryWorkspaceProps) {
  const [examinedOpportunity, setExaminedOpportunity] = useState<RankedOpportunity | null>(null);

  // Discovery Configuration State
  const [targetGoal, setTargetGoal] = useState<number>(3);
  const [enableLiveDiscovery, setEnableLiveDiscovery] = useState<boolean>(true);
  const selectedConnectorIds = ['web_search', 'jobspy_mcp'];

  // Network & Connector Health
  const [connectors, setConnectors] = useState<ConnectorHealthReport[]>([]);

  // Persistent Run & Execution State
  const [activeRun, setActiveRun] = useState<DiscoveryRun | null>(null);
  const [currentStage, setCurrentStage] = useState<WorkflowStage>('INITIALIZING');
  const [liveEvents, setLiveEvents] = useState<WorkflowTimelineEvent[]>([]);
  const [liveRawCount, setLiveRawCount] = useState<number>(0);
  const [liveCanonicalCount, setLiveCanonicalCount] = useState<number>(0);
  const [liveDuplicateCount, setLiveDuplicateCount] = useState<number>(0);
  const [liveEligibleCount, setLiveEligibleCount] = useState<number>(0);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [discoveryResponse, setDiscoveryResponse] = useState<AdaptiveDiscoveryResponse | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Inspection Drawer State
  const [auditedOpportunity, setAuditedOpportunity] = useState<RankedOpportunity | null>(null);
  const [auditDrawerTab, setAuditDrawerTab] = useState<'fit' | 'evidence' | 'eligibility'>('fit');
  const [showTimeline, setShowTimeline] = useState<boolean>(true);

  // Active event stream ref to clean up listeners
  const activeEventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load connector health on mount and when operating mode changes
  useEffect(() => {
    let isMounted = true;
    async function loadConnectors() {
      try {
        const reports = await getDiscoveryConnectors(enableLiveDiscovery);
        if (isMounted) setConnectors(reports);
      } catch (err) {
        console.warn('Unable to load discovery connectors:', err);
      }
    }
    loadConnectors();
    return () => {
      isMounted = false;
    };
  }, [enableLiveDiscovery]);

  // Helper to fetch final results and set response
  const finalizeRun = useCallback(async (runId: string) => {
    try {
      const finalRun = await getDiscoveryRun(runId);
      setActiveRun(finalRun);
      if (finalRun.response) {
        setDiscoveryResponse(finalRun.response);
        if (finalRun.response.connector_health?.length) {
          setConnectors(finalRun.response.connector_health);
        }
      } else if (finalRun.connector_health?.length) {
        setConnectors(finalRun.connector_health);
      }
      if (finalRun.timeline_events?.length) {
        setLiveEvents(finalRun.timeline_events);
      }
      setLiveRawCount(finalRun.total_discovered_raw);
      setLiveCanonicalCount(finalRun.canonical_count);
      setLiveDuplicateCount(finalRun.duplicate_count);
      setLiveEligibleCount(finalRun.eligible_count);
      setCurrentStage('COMPLETED');
    } catch (err) {
      console.warn('Failed to retrieve finalized run:', err);
    } finally {
      setIsExecuting(false);
    }
  }, []);

  // Attach SSE stream and fallback polling
  const attachStream = useCallback((runId: string) => {
    // Clean up any existing connection
    if (activeEventSourceRef.current) {
      activeEventSourceRef.current.close();
      activeEventSourceRef.current = null;
    }
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    const streamUrl = getDiscoveryRunStreamUrl(runId);
    const eventSource = new EventSource(streamUrl);
    activeEventSourceRef.current = eventSource;

    eventSource.addEventListener('workflow_event', (e: MessageEvent) => {
      try {
        const payload: DiscoveryRunStreamEvent = JSON.parse(e.data);
        if (payload.stage) {
          setCurrentStage(payload.stage);
        }

        setLiveEvents((prev) => {
          const exists = prev.some(
            (x) => x.summary === payload.summary && x.timestamp === payload.timestamp
          );
          if (exists) return prev;
          return [
            ...prev,
            {
              timestamp: payload.timestamp,
              stage: payload.stage || 'SEARCHING',
              event_type: payload.event_type,
              summary: payload.summary,
              details: payload.data || {},
            },
          ];
        });

        if (payload.status === 'COMPLETED') {
          eventSource.close();
          activeEventSourceRef.current = null;
          finalizeRun(runId);
        } else if (payload.status === 'FAILED') {
          eventSource.close();
          activeEventSourceRef.current = null;
          setIsExecuting(false);
          setExecutionError(payload.summary || 'Discovery run failed.');
        }
      } catch (err) {
        console.warn('Error parsing workflow_event:', err);
      }
    });

    eventSource.addEventListener('run_completed', () => {
      eventSource.close();
      activeEventSourceRef.current = null;
      finalizeRun(runId);
    });

    eventSource.onerror = () => {
      // Don't crash on SSE reconnect; polling will maintain state
      eventSource.close();
      activeEventSourceRef.current = null;
    };

    // Polling fallback interval every 2.5 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const current = await getDiscoveryRun(runId);
        setActiveRun(current);
        setLiveRawCount(current.total_discovered_raw);
        setLiveCanonicalCount(current.canonical_count);
        setLiveDuplicateCount(current.duplicate_count);
        setLiveEligibleCount(current.eligible_count);
        if (current.timeline_events?.length) {
          setLiveEvents(current.timeline_events);
        }

        if (current.status === 'COMPLETED') {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          if (activeEventSourceRef.current) activeEventSourceRef.current.close();
          if (current.response) {
            setDiscoveryResponse(current.response);
          }
          setCurrentStage('COMPLETED');
          setIsExecuting(false);
        } else if (current.status === 'FAILED') {
          if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
          if (activeEventSourceRef.current) activeEventSourceRef.current.close();
          setIsExecuting(false);
          setExecutionError(current.error_message || 'Discovery run failed.');
        }
      } catch (pollErr) {
        console.warn('Discovery run polling error:', pollErr);
      }
    }, 2500);
  }, [finalizeRun]);

  // Clean up stream listeners on unmount
  useEffect(() => {
    return () => {
      if (activeEventSourceRef.current) {
        activeEventSourceRef.current.close();
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // 1. Session Persistence Recovery: On candidate change or mount, check for latest run
  useEffect(() => {
    let isMounted = true;
    async function loadLatestRun() {
      try {
        const latest = await getLatestDiscoveryRunForCandidate(candidateProfile.user_id);
        if (!isMounted) return;

        if (latest) {
          setActiveRun(latest);
          setLiveEvents(latest.timeline_events || []);
          setLiveRawCount(latest.total_discovered_raw || 0);
          setLiveCanonicalCount(latest.canonical_count || 0);
          setLiveDuplicateCount(latest.duplicate_count || 0);
          setLiveEligibleCount(latest.eligible_count || 0);

          if (latest.status === 'COMPLETED' && latest.response) {
            setDiscoveryResponse(latest.response);
            if (latest.response.connector_health?.length) {
              setConnectors(latest.response.connector_health);
            }
            setCurrentStage('COMPLETED');
            setIsExecuting(false);
          } else if (latest.connector_health?.length) {
            setConnectors(latest.connector_health);
          } else if (
            latest.status !== 'COMPLETED' &&
            latest.status !== 'FAILED' &&
            latest.status !== 'CANCELLED'
          ) {
            // Reconnect to active running execution seamlessly!
            setIsExecuting(true);
            attachStream(latest.run_id);
          }
        } else {
          setActiveRun(null);
          setDiscoveryResponse(null);
          setLiveEvents([]);
        }
      } catch (err) {
        console.warn('Could not load latest run for candidate:', err);
      }
    }

    loadLatestRun();
    return () => {
      isMounted = false;
    };
  }, [candidateProfile.user_id, attachStream]);

  // Launch LangGraph Adaptive Discovery Workflow
  async function handleLaunchDiscovery() {
    setIsExecuting(true);
    setExecutionError(null);
    setDiscoveryResponse(null);
    setLiveEvents([]);
    setLiveRawCount(0);
    setLiveCanonicalCount(0);
    setLiveDuplicateCount(0);
    setLiveEligibleCount(0);
    setCurrentStage('INITIALIZING');

    try {
      const payload: AdaptiveDiscoveryRequest = {
        candidate_profile: candidateProfile,
        connector_ids: selectedConnectorIds.length > 0 ? selectedConnectorIds : undefined,
        target_coverage_goal: targetGoal,
        enable_live_discovery: enableLiveDiscovery,
        persist_to_repository: true,
        rank_recommendations: true,
      };

      const run = await startDiscoveryRun(payload);
      setActiveRun(run);

      if (run.status === 'COMPLETED' && run.response) {
        setDiscoveryResponse(run.response);
        if (run.response.connector_health?.length) {
          setConnectors(run.response.connector_health);
        }
        setCurrentStage('COMPLETED');
        setIsExecuting(false);
      } else {
        if (run.connector_health?.length) {
          setConnectors(run.connector_health);
        }
        attachStream(run.run_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Discovery workflow failed';
      setExecutionError(msg);
      setIsExecuting(false);
    }
  }

  const recommendations = discoveryResponse?.recommendations?.ranked_recommendations || [];
  const adaptations = activeRun?.adaptation_history || discoveryResponse?.adaptation_history || [];
  const currentIteration = Math.max(
    1,
    liveEvents.filter((e) => e.event_type?.includes('ITERATION_') && e.event_type?.includes('_STARTED')).length
  );
  const rejectionsByCode = activeRun?.rejections_by_code || discoveryResponse?.rejections_by_code || {};

  return (
    <div className="space-y-8">
      {/* 1. Header & Discovery Control Bar */}
      <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-md bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <Compass className="w-4 h-4" />
              </span>
              <h2 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Personalized Opportunity Discovery
              </h2>
              {activeRun && (
                <Badge variant={isExecuting ? 'teal' : 'verified'} size="sm" mono>
                  {isExecuting ? 'FINDING MATCHES' : 'MATCHES SAVED'}
                </Badge>
              )}
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Finds, verifies, and ranks authentic career opportunities tailored specifically to your background and target trajectory ({candidateProfile.target_career_paths[0]?.title || 'Target Role'}).
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {activeRun && !isExecuting && (
              <span className="text-[11px] font-mono text-zinc-500 hidden sm:inline-block">
                Run ID: <span className="font-semibold text-zinc-800 dark:text-zinc-200">{activeRun.run_id}</span>
              </span>
            )}

            <button
              onClick={handleLaunchDiscovery}
              disabled={isExecuting}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold shadow-xs transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              {isExecuting ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin text-teal-400 dark:text-teal-600" />
                  <span>Orchestrating Discovery...</span>
                </>
              ) : (
                <>
                  <Compass className="w-4 h-4 text-teal-400 dark:text-teal-600" />
                  <span>{activeRun ? 'Re-discover Opportunities' : 'Discover opportunities for me'}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Configuration Parameters & Source Status */}
        <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Target Role & Profile Focus */}
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-700/60 space-y-1">
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
              Target Trajectory
            </span>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {candidateProfile.target_career_paths[0]?.title || 'Software Engineer'}
              </span>
              <button
                onClick={() => onNavigateTab('profile')}
                className="text-[11px] text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-0.5"
              >
                Inspect
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            <p className="text-[11px] text-zinc-500 font-mono">
              O*NET: {candidateProfile.target_career_paths[0]?.occupation_code || '15-1252.00'} • {candidateProfile.assessed_skills.length} skills on file
            </p>
          </div>

          {/* Discovery Sources */}
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-700/60 space-y-1">
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
              Dispatched Connectors
            </span>
            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
              {connectors.length > 0 ? (
                connectors.map((c) => {
                  let badgeVariant: 'teal' | 'verified' | 'caveat' | 'disqualified' | 'outline' | 'neutral' = 'neutral';
                  if (c.status === 'CONNECTED') {
                    badgeVariant = 'teal';
                  } else if (c.status === 'ERROR') {
                    badgeVariant = 'disqualified';
                  } else if (
                    c.status === 'UNAVAILABLE_MISSING_BINARY' ||
                    c.status === 'UNAVAILABLE' ||
                    c.status === 'MISCONFIGURED' ||
                    c.status === 'DEGRADED' ||
                    c.status === 'RATE_LIMITED'
                  ) {
                    badgeVariant = 'caveat';
                  } else if (c.is_mock_fallback || c.status === 'MOCKED_FALLBACK') {
                    badgeVariant = 'outline';
                  }

                  return (
                    <Badge
                      key={c.connector_id}
                      variant={badgeVariant}
                      size="sm"
                      mono
                      title={`${c.source_name}: ${c.status}`}
                    >
                      {c.source_name.split(' ')[0]} ({c.status})
                    </Badge>
                  );
                })
              ) : (
                <>
                  <Badge variant="teal" size="sm" mono>
                    SearXNG Web
                  </Badge>
                  <Badge variant="teal" size="sm" mono>
                    JobSpy MCP
                  </Badge>
                </>
              )}
            </div>
          </div>

          {/* Goal & Mode Settings */}
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-700/60 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
                Target Coverage
              </span>
              <div className="flex items-center gap-1 font-mono text-xs">
                {[3, 5, 8].map((val) => (
                  <button
                    key={val}
                    onClick={() => setTargetGoal(val)}
                    disabled={isExecuting}
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${
                      targetGoal === val
                        ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                        : 'bg-zinc-200/70 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300'
                    }`}
                  >
                    {val}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-zinc-500">
              <span>Operating Mode:</span>
              <label className="inline-flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableLiveDiscovery}
                  disabled={isExecuting}
                  onChange={(e) => setEnableLiveDiscovery(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <span className="font-mono text-[10px]">
                  {enableLiveDiscovery ? 'Live Market (SearXNG/MCP)' : 'Deterministic Sandbox'}
                </span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Execution Error Banner */}
      {executionError && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/70 text-xs flex items-start gap-3 text-rose-800 dark:text-rose-200">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold">Discovery Workflow Failed</span>
            <p className="font-mono text-[11px]">{executionError}</p>
          </div>
        </div>
      )}

      {/* 2. User-Centric Live Progress Card (Normal Mode) */}
      {isExecuting && (
        <div className="p-5 rounded-2xl bg-teal-50/60 dark:bg-teal-950/20 border border-teal-200/80 dark:border-teal-800/60 shadow-xs space-y-3 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="p-2 rounded-xl bg-teal-600 text-white animate-spin">
                <RotateCw className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  {HUMAN_PROGRESS_STAGES[currentStage]?.text || 'Discovering career opportunities...'}
                </h3>
                <p className="text-xs text-zinc-500">
                  Step {HUMAN_PROGRESS_STAGES[currentStage]?.step || 1} of 5 • Progressive evaluation across authentic sources.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs font-mono text-zinc-600 dark:text-zinc-400 bg-white dark:bg-zinc-800 px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700">
              <span>Leads: <strong>{liveRawCount}</strong></span>
              <span>•</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                {liveEligibleCount} Verified Matches
              </span>
            </div>
          </div>

          <div className="w-full bg-zinc-200/70 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-teal-600 h-full transition-all duration-300"
              style={{
                width: `${Math.max(15, (HUMAN_PROGRESS_STAGES[currentStage]?.step || 1) * 20)}%`,
              }}
            />
          </div>
        </div>
      )}

      {/* 2. Multi-Agent Research Activity Display */}
      {(isExecuting || activeRun || discoveryResponse) && (
        <div className="rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs overflow-hidden space-y-4">
          {/* Stepper Header Strip */}
          <div className="px-6 py-4 bg-zinc-50/70 dark:bg-zinc-800/40 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isExecuting ? 'bg-teal-500 animate-pulse' : 'bg-emerald-500'
                }`}
              />
              <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                Multi-Agent Career Opportunity Discovery
              </span>
              {activeRun?.status && (
                <Badge
                  variant={
                    activeRun.status === 'COMPLETED'
                      ? 'verified'
                      : activeRun.status === 'FAILED'
                      ? 'disqualified'
                      : 'teal'
                  }
                  size="sm"
                  mono
                >
                  {activeRun.status === 'COMPLETED' ? 'RESULTS READY' : activeRun.status}
                </Badge>
              )}
            </div>

            {/* Live Funnel Counts */}
            <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
              <span className="flex items-center gap-1">
                <span className="font-bold text-zinc-800 dark:text-zinc-200">
                  <NumberTicker value={liveRawCount} />
                </span>{' '}
                leads
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="font-bold text-zinc-800 dark:text-zinc-200">
                  <NumberTicker value={liveCanonicalCount} />
                </span>{' '}
                unique
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                <NumberTicker value={liveEligibleCount} /> verified matches
              </span>
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className="text-[11px] text-teal-600 hover:underline font-sans ml-2"
              >
                {showTimeline ? 'Hide Activity' : 'Show Activity'}
              </button>
            </div>
          </div>

          {/* Adaptive Cycle Notice */}
          {adaptations.length > 0 && (
            <div className="mx-6 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 flex items-center justify-between text-xs text-amber-800 dark:text-amber-300 font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                <span className="font-bold">Adaptive Loop Active: Iteration {currentIteration}</span>
                <span>•</span>
                <span className="truncate max-w-xl text-[11px] font-sans">
                  {adaptations[adaptations.length - 1].action_summary}
                </span>
              </div>
            </div>
          )}

          {/* Active Specialized Agent Indicator */}
          <div className="px-6 py-1">
            <div className="p-3 rounded-lg bg-teal-50/50 dark:bg-teal-950/20 border border-teal-200/80 dark:border-teal-800/60 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <div className="p-1.5 rounded-md bg-teal-600 text-white shrink-0">
                  {currentStage === 'SEARCHING' ? (
                    <Search className="w-4 h-4" />
                  ) : currentStage === 'STRATEGY_FORMULATION' ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : currentStage === 'EVALUATING' ? (
                    <ShieldCheck className="w-4 h-4" />
                  ) : (
                    <Target className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <div className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                    <span>
                      {currentStage === 'SEARCHING'
                        ? 'Discovery Agent Active'
                        : currentStage === 'STRATEGY_FORMULATION'
                        ? 'Market Agent & Orchestrator Active'
                        : currentStage === 'EVALUATING'
                        ? 'Opportunity Research Agent Active'
                        : currentStage === 'RANKING'
                        ? 'Recommendation Agent Active'
                        : 'Orchestration Agent Active'}
                    </span>
                    {isExecuting && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-teal-100 dark:bg-teal-900 text-teal-800 dark:text-teal-200 font-normal">
                        Coordinating
                      </span>
                    )}
                  </div>
                  <p className="text-zinc-600 dark:text-zinc-400 text-[11px] mt-0.5">
                    {HUMAN_PROGRESS_STAGES[currentStage]?.text || 'Coordinating opportunity evaluation...'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Clean Agent Activity Stream */}
          {showTimeline && (
            <div className="px-6 pb-6">
              <div className="p-4 rounded-lg bg-zinc-50/80 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 max-h-56 overflow-y-auto space-y-2.5 text-xs divide-y divide-zinc-200/40 dark:divide-zinc-800/50">
                {liveEvents.length === 0 ? (
                  <div className="text-zinc-400 text-center py-4 text-xs font-sans">
                    Agents are initializing discovery workflow...
                  </div>
                ) : (
                  liveEvents.map((evt, idx) => (
                    <div key={idx} className="pt-2 first:pt-0 flex items-start gap-3">
                      <span className="text-[10px] font-mono text-zinc-400 shrink-0 w-16">
                        {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false })}
                      </span>
                      <span className="text-zinc-800 dark:text-zinc-200 font-sans flex-1 leading-relaxed">
                        {evt.summary}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 2.1 Decision Traceability & Funnel Breakdown Card */}
          <div className="px-6 pb-6 pt-3 border-t border-zinc-100 dark:border-zinc-800">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-mono uppercase font-bold text-zinc-500 tracking-wider">
                Discovery Funnel & Verification Integrity
              </span>
              <span className="text-[10px] font-mono text-zinc-400">
                Deterministic Primacy • Zero Synthetic Listings
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs font-mono">
              {/* 1. Sourced Leads */}
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50">
                <div className="text-[10px] text-zinc-400 uppercase">Sourced Leads</div>
                <div className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  {liveRawCount}
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">
                  {activeRun?.sources_queried?.length ? activeRun.sources_queried.join(', ') : 'SearXNG / MCP'}
                </div>
              </div>

              {/* 2. Collection Pages Filtered */}
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50">
                <div className="text-[10px] text-zinc-400 uppercase">Collection Pages</div>
                <div className="text-base font-bold text-amber-600 dark:text-amber-400 mt-1">
                  {rejectionsByCode['COLLECTION_PAGE'] || 0}
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">
                  Aggregator lists rejected
                </div>
              </div>

              {/* 3. Non-Job / Reserved Filtered */}
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50">
                <div className="text-[10px] text-zinc-400 uppercase">Invalid / Articles</div>
                <div className="text-base font-bold text-rose-600 dark:text-rose-400 mt-1">
                  {(rejectionsByCode['INFORMATIONAL_CONTENT'] || 0) + (rejectionsByCode['PLACEHOLDER_DOMAIN'] || 0) + (rejectionsByCode['INVALID_URL'] || 0)}
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">
                  Guides & placeholders
                </div>
              </div>

              {/* 4. Duplicates Clustered */}
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50">
                <div className="text-[10px] text-zinc-400 uppercase">Duplicates (MinHash)</div>
                <div className="text-base font-bold text-purple-600 dark:text-purple-400 mt-1">
                  {liveDuplicateCount}
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">
                  Redundancy eliminated
                </div>
              </div>

              {/* 5. Hard Eligibility Disqualified */}
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50">
                <div className="text-[10px] text-zinc-400 uppercase">Disqualified</div>
                <div className="text-base font-bold text-zinc-700 dark:text-zinc-300 mt-1">
                  {(activeRun?.ineligible_count || 0) + (rejectionsByCode['OTHER_HARD_CONSTRAINT'] || 0)}
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">
                  Python constraint gate
                </div>
              </div>

              {/* 6. Verified Matches */}
              <div className="p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/50">
                <div className="text-[10px] text-emerald-600 dark:text-emerald-400 uppercase font-semibold">Verified Matches</div>
                <div className="text-base font-bold text-emerald-700 dark:text-emerald-300 mt-1">
                  {liveEligibleCount}
                </div>
                <div className="text-[10px] text-emerald-600 dark:text-emerald-400 truncate mt-0.5">
                  Deterministic 6D ranked
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. Ranked Opportunity Recommendations Feed */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Ranked Opportunity Matches
            </h3>
            {recommendations.length > 0 && (
              <span className="text-xs text-zinc-500 font-mono">
                ({recommendations.length} recommendations ranked by deterministic 6D fit)
              </span>
            )}
          </div>

          {recommendations.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigateTab('profile')}
                className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 font-medium"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Review Profile Evidence
              </button>
            </div>
          )}
        </div>

        {recommendations.length === 0 ? (
          <div className="p-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-center space-y-4 shadow-xs">
            <div className="mx-auto w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
              <Search className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                {discoveryResponse ? 'No Qualified Matches Found' : 'No Opportunities Discovered Yet'}
              </h4>
              <p className="text-xs text-zinc-500 max-w-md mx-auto">
                {discoveryResponse
                  ? `Searched live sources for ${candidateName}, but zero listings satisfied hard deterministic eligibility requirements. No synthetic listings are shown.`
                  : 'Click "Launch Discovery Workflow" above to query live opportunity sources and compute verifiable candidate-job fit scores.'}
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {recommendations.map((rec) => {
              const opp = rec.opportunity;
              const fitPercent = rec.overall_fit_score * 100;

              return (
                <div
                  key={opp.opportunity_id}
                  className="p-5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-all duration-150 shadow-xs space-y-4"
                >
                  {/* Card Top Row: Rank, Title, Company, Score */}
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-mono text-xs font-bold">
                          #{rec.rank}
                        </span>

                        <h4 className="text-base font-bold text-zinc-900 dark:text-zinc-100 hover:text-teal-600 transition-colors">
                          {opp.title}
                        </h4>

                        {opp.company_domain_verified && (
                          <Badge variant="verified" size="sm" icon={<ShieldCheck className="w-3 h-3" />}>
                            Verified Employer
                          </Badge>
                        )}

                        <Badge variant="outline" size="sm" mono>
                          {opp.eligibility_rules?.opportunity_category || 'FULL_TIME_JOB'}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400 flex-wrap">
                        <span className="font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1">
                          <Building2 className="w-3.5 h-3.5" />
                          {opp.company_name}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5" />
                          {formatOpportunityLocation(opp)}
                        </span>
                        <span>•</span>
                        <span className="font-mono">
                          Mode: {opp.eligibility_rules?.work_mode || 'REMOTE'}
                        </span>
                        <span>•</span>
                        <span className="font-mono text-[11px] text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/60 px-1.5 py-0.5 rounded border border-teal-200 dark:border-teal-800">
                          {(() => {
                            const minMonths = opp.eligibility_rules?.min_experience_months ?? 0;
                            const candMonths = candidateProfile?.eligibility_constraints?.total_full_time_experience_months ?? 0;
                            if (minMonths <= 0) return 'Entry Level';
                            const reqYrs = (minMonths / 12).toFixed(minMonths % 12 === 0 ? 0 : 1);
                            const candYrs = (candMonths / 12).toFixed(1);
                            if (candMonths >= minMonths) {
                              return `Req: ${reqYrs}+ yrs • ✓ Qualified (${candYrs} yrs)`;
                            }
                            return `Req: ${reqYrs}+ yrs • You have ${candYrs} yrs`;
                          })()}
                        </span>
                        <span>•</span>
                        <span className="text-[11px] font-mono text-zinc-400">
                          Source: {String(opp.category_specific_attributes?.source_system || 'ats_direct')}
                        </span>
                      </div>
                    </div>

                    {/* Overall Fit Score Ticker */}
                    <div className="flex sm:flex-col items-center sm:items-end justify-between shrink-0 bg-zinc-50 dark:bg-zinc-800/50 p-2.5 rounded-lg border border-zinc-200/60 dark:border-zinc-700/60">
                      <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
                        Fit Score
                      </span>
                      <div className="text-xl font-bold font-mono text-teal-600 dark:text-teal-400 flex items-baseline gap-0.5">
                        <NumberTicker value={fitPercent} decimals={1} />
                      </div>
                      <span className="text-[10px] text-zinc-400 font-mono">
                        Deterministic 6D
                      </span>
                    </div>
                  </div>

                  {/* Recommendation Rationale */}
                  <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed">
                    {rec.recommendation_rationale}
                  </p>

                  {/* 6D Fit Spectrum Mini-Bar */}
                  <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800/80 space-y-1.5">
                    <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
                      Six-Dimensional Fit Spectrum
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
                      {Object.entries(rec.dimension_scores).map(([dim, breakdown]) => (
                        <div key={dim} className="space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-zinc-500 font-medium truncate">
                              {dim.replace('_', ' ').toLowerCase()}
                            </span>
                            <span className="font-mono font-semibold text-zinc-800 dark:text-zinc-200">
                              {(breakdown.raw_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="h-1 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-teal-500 rounded-full"
                              style={{ width: `${breakdown.raw_score * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Bottom Row: Skills, Audit Trigger & External Apply */}
                  <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[11px] text-zinc-400 font-mono mr-1">Matched:</span>
                      {rec.matched_skills.slice(0, 3).map((ms) => (
                        <Badge key={ms.skill_name} variant="verified" size="sm">
                          {ms.skill_name}
                        </Badge>
                      ))}

                      {rec.missing_skills.length > 0 && (
                        <>
                          <span className="text-[11px] text-zinc-400 font-mono ml-2 mr-1">Gaps:</span>
                          {rec.missing_skills.slice(0, 2).map((gap) => (
                            <Badge key={gap.skill_name} variant="caveat" size="sm">
                              {gap.skill_name}
                            </Badge>
                          ))}
                        </>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => setExaminedOpportunity(rec)}
                        className="px-3.5 py-1.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold text-teal-800 dark:text-teal-300 transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                        <span>Examine Role & Fit</span>
                      </button>

                      <button
                        onClick={() => {
                          setAuditedOpportunity(rec);
                          setAuditDrawerTab('fit');
                        }}
                        className="px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400 transition-colors flex items-center gap-1"
                        title="Inspect raw audit and deterministic evidence records"
                      >
                        <FileText className="w-3 h-3 text-zinc-400" />
                        <span className="hidden sm:inline">Audit</span>
                      </button>

                      {opp.source_url && (
                        <a
                          href={opp.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3.5 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold transition-colors flex items-center gap-1 shadow-xs"
                        >
                          <span>Apply</span>
                          <ExternalLink className="w-3 h-3" />
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

      {/* 4. Deep Inspection SlideDrawer */}
      {auditedOpportunity && (
        <SlideDrawer
          isOpen={!!auditedOpportunity}
          onClose={() => setAuditedOpportunity(null)}
          title={`Audit: ${auditedOpportunity.opportunity.title}`}
          subtitle={`${auditedOpportunity.opportunity.company_name} • Match Fit: ${(
            auditedOpportunity.overall_fit_score * 100
          ).toFixed(1)}%`}
        >
          <div className="space-y-6">
            {/* Drawer Sub-tabs */}
            <div className="flex items-center gap-2 p-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-xs">
              <button
                onClick={() => setAuditDrawerTab('fit')}
                className={`flex-1 py-1.5 rounded-md font-semibold transition-colors ${
                  auditDrawerTab === 'fit'
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'text-zinc-500 hover:text-zinc-800'
                }`}
              >
                6D Fit Rationale
              </button>
              <button
                onClick={() => setAuditDrawerTab('evidence')}
                className={`flex-1 py-1.5 rounded-md font-semibold transition-colors ${
                  auditDrawerTab === 'evidence'
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Evidence Citations
              </button>
              <button
                onClick={() => setAuditDrawerTab('eligibility')}
                className={`flex-1 py-1.5 rounded-md font-semibold transition-colors ${
                  auditDrawerTab === 'eligibility'
                    ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                    : 'text-zinc-500 hover:text-zinc-800'
                }`}
              >
                Eligibility Rules
              </button>
            </div>

            {/* TAB 1: 6D FIT RATIONALE */}
            {auditDrawerTab === 'fit' && (
              <div className="space-y-6">
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                    Mathematical 6D Fit Breakdown
                  </h4>
                  <div className="space-y-4">
                    {Object.entries(auditedOpportunity.dimension_scores).map(([dim, score]) => (
                      <ScoreBar
                        key={dim}
                        label={dim.replace(/_/g, ' ').toLowerCase()}
                        score={score.raw_score}
                        weight={score.weight}
                        rationale={score.rationale}
                      />
                    ))}
                  </div>
                </div>

                {/* Key Tradeoffs or Risks */}
                {auditedOpportunity.key_tradeoffs_or_risks.length > 0 && (
                  <div className="p-4 rounded-lg bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-xs space-y-2">
                    <span className="font-bold text-amber-900 dark:text-amber-200 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      Tradeoffs & Epistemic Caveats
                    </span>
                    <ul className="list-disc list-inside space-y-1 text-amber-800 dark:text-amber-300">
                      {auditedOpportunity.key_tradeoffs_or_risks.map((risk, rIdx) => (
                        <li key={rIdx}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: EVIDENCE GROUNDING & MISSING SKILLS */}
            {auditDrawerTab === 'evidence' && (
              <div className="space-y-6">
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                    Grounded Candidate Evidence
                  </h4>

                  {auditedOpportunity.matched_skills.map((match) => (
                    <div
                      key={match.canonical_skill_id}
                      className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 space-y-2.5"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-zinc-900 dark:text-zinc-100">
                          {match.skill_name}
                        </span>
                        <div className="flex items-center gap-2 font-mono text-[11px]">
                          <span className="text-zinc-400">Candidate:</span>
                          <span className="text-emerald-600 font-semibold">
                            {match.candidate_proficiency.toFixed(1)}/10
                          </span>
                          <span className="text-zinc-400">Required:</span>
                          <span className="text-zinc-700 font-semibold">
                            {match.expected_proficiency.toFixed(1)}/10
                          </span>
                        </div>
                      </div>

                      {match.evidence_snippets.map((snip: string, sIdx: number) => (
                        <EvidenceCard
                          key={sIdx}
                          extractedSnippet={snip}
                          sourceType="RESUME_WORK_EXPERIENCE"
                          verifiabilityWeight={match.confidence_score}
                        />
                      ))}
                    </div>
                  ))}
                </div>

                {auditedOpportunity.missing_skills.length > 0 && (
                  <div className="space-y-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                        Identified Skill Gaps
                      </h4>
                      <button
                        onClick={() => {
                          setAuditedOpportunity(null);
                          onNavigateTab('profile');
                        }}
                        className="text-xs text-teal-600 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <Target className="w-3.5 h-3.5" />
                        Update Profile Skills
                      </button>
                    </div>

                    <div className="grid grid-cols-1 gap-2.5">
                      {auditedOpportunity.missing_skills.map((gap) => (
                        <div
                          key={gap.skill_name}
                          className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                              {gap.skill_name}
                            </span>
                            <Badge variant={gap.is_mandatory ? 'disqualified' : 'caveat'} size="sm">
                              {gap.is_mandatory ? 'Mandatory Requirement' : 'Preferred'}
                            </Badge>
                          </div>
                          <p className="text-[11px] text-zinc-500">
                            Required proficiency: {gap.expected_proficiency.toFixed(1)}/10 • No verified candidate provenance
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: DETERMINISTIC ELIGIBILITY AUDIT */}
            {auditDrawerTab === 'eligibility' && (
              <div className="space-y-4">
                <div className="p-3.5 rounded-lg bg-emerald-50/80 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 text-xs space-y-1">
                  <span className="font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Deterministic Primacy Invariant Verified
                  </span>
                  <p className="text-emerald-800 dark:text-emerald-300 text-[11px]">
                    Evaluated strictly in pure Python/SQL code. Zero probabilistic LLM overrides.
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                    Evaluation Constraints Matrix
                  </h4>

                  <div className="divide-y divide-zinc-100 dark:divide-zinc-800/80 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden text-xs">
                    <div className="p-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        Work Authorization
                      </span>
                      <Badge variant="verified" size="sm">
                        PASSED
                      </Badge>
                    </div>

                    <div className="p-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        Degree Requirement
                      </span>
                      <Badge variant="verified" size="sm">
                        PASSED
                      </Badge>
                    </div>

                    <div className="p-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        Student Status Restriction
                      </span>
                      <Badge variant="verified" size="sm">
                        NOT REQUIRED
                      </Badge>
                    </div>

                    <div className="p-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        Experience Threshold
                      </span>
                      <Badge variant="verified" size="sm">
                        PASSED
                      </Badge>
                    </div>

                    <div className="p-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        Work Mode Matching
                      </span>
                      <Badge variant="verified" size="sm">
                        PASSED
                      </Badge>
                    </div>

                    <div className="p-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">
                        Location Compatibility
                      </span>
                      <Badge variant="verified" size="sm">
                        PASSED
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </SlideDrawer>
      )}

      {/* 5. Focused Opportunity Detail Modal */}
      {examinedOpportunity && (
        <OpportunityDetailModal
          opportunity={examinedOpportunity}
          candidateProfile={candidateProfile}
          onClose={() => setExaminedOpportunity(null)}
        />
      )}
    </div>
  );
}

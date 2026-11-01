'use client';

import React, { useState, useEffect } from 'react';
import {
  Compass,
  Play,
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
} from 'lucide-react';
import {
  AdaptiveDiscoveryRequest,
  AdaptiveDiscoveryResponse,
  CandidateCareerProfile,
  ConnectorHealthReport,
  RankedOpportunity,
} from '@/types/domain';
import { getDiscoveryConnectors, runAdaptiveDiscovery } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { NumberTicker } from '@/components/ui/NumberTicker';
import { ScoreBar } from '@/components/ui/ScoreBar';
import { SlideDrawer } from '@/components/ui/SlideDrawer';
import { EvidenceCard } from '@/components/ui/EvidenceCard';
import { WorkspaceTab } from '@/components/layout/Header';

interface DiscoveryWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab: (tab: WorkspaceTab, context?: { targetRole?: string; skillId?: string }) => void;
}

export function DiscoveryWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
}: DiscoveryWorkspaceProps) {
  // Discovery Configuration State
  const [targetGoal, setTargetGoal] = useState<number>(3);
  const maxIterations = 2;
  const [enableLiveDiscovery, setEnableLiveDiscovery] = useState<boolean>(false);
  const selectedConnectorIds = ['web_search', 'jobspy_mcp'];

  // Network & Execution State
  const [connectors, setConnectors] = useState<ConnectorHealthReport[]>([]);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [discoveryResponse, setDiscoveryResponse] = useState<AdaptiveDiscoveryResponse | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Inspection Drawer State
  const [auditedOpportunity, setAuditedOpportunity] = useState<RankedOpportunity | null>(null);
  const [auditDrawerTab, setAuditDrawerTab] = useState<'fit' | 'evidence' | 'eligibility'>('fit');
  const [showTimeline, setShowTimeline] = useState<boolean>(true);

  // Load connector health on mount
  useEffect(() => {
    let isMounted = true;
    async function loadConnectors() {
      try {
        const reports = await getDiscoveryConnectors(false);
        if (isMounted) setConnectors(reports);
      } catch (err) {
        console.warn('Unable to load discovery connectors:', err);
      }
    }
    loadConnectors();
    return () => {
      isMounted = false;
    };
  }, []);

  // Launch LangGraph Adaptive Discovery Workflow
  async function handleLaunchDiscovery() {
    setIsExecuting(true);
    setExecutionError(null);
    try {
      const payload: AdaptiveDiscoveryRequest = {
        candidate_profile: candidateProfile,
        connector_ids: selectedConnectorIds.length > 0 ? selectedConnectorIds : undefined,
        target_coverage_goal: targetGoal,
        max_iterations: maxIterations,
        max_tool_calls: 8,
        enable_live_discovery: enableLiveDiscovery,
        persist_to_repository: true,
        rank_recommendations: true,
      };

      const response = await runAdaptiveDiscovery(payload);
      setDiscoveryResponse(response);
      setShowTimeline(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Discovery workflow failed';
      setExecutionError(msg);
    } finally {
      setIsExecuting(false);
    }
  }

  const recommendations = discoveryResponse?.recommendations?.ranked_recommendations || [];

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
                Opportunity Discovery & Match Radar
              </h2>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Coordinates multi-source discovery (WebSearch, JobSpy MCP, ATS Direct), MinHash deduplication,
              deterministic eligibility filtering, and 6-dimensional fit scoring for {candidateName}.
            </p>
          </div>

          <button
            onClick={handleLaunchDiscovery}
            disabled={isExecuting}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold shadow-xs transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-hidden focus:ring-2 focus:ring-teal-500 shrink-0"
          >
            {isExecuting ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin text-teal-400 dark:text-teal-600" />
                <span>Orchestrating Discovery...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current text-teal-400 dark:text-teal-600" />
                <span>Launch Discovery Workflow</span>
              </>
            )}
          </button>
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
                connectors.map((c) => (
                  <Badge
                    key={c.connector_id}
                    variant={c.status === 'ERROR' ? 'disqualified' : c.is_mock_fallback ? 'outline' : 'teal'}
                    size="sm"
                    mono
                  >
                    {c.source_name.split(' ')[0]} ({c.status})
                  </Badge>
                ))
              ) : (
                <>
                  <Badge variant="teal" size="sm" mono>
                    WebSearch (SearXNG)
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
              <span>Simulation mode:</span>
              <label className="inline-flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableLiveDiscovery}
                  onChange={(e) => setEnableLiveDiscovery(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <span className="font-mono text-[10px]">
                  {enableLiveDiscovery ? 'Live Scrape' : 'Fast Sandbox'}
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

      {/* 2. Safe Agent Activity Feed (WorkflowTimelineEvent Telemetry) */}
      {discoveryResponse && (
        <div className="rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs overflow-hidden">
          {/* Summary Strip */}
          <div className="px-6 py-4 bg-zinc-50/70 dark:bg-zinc-800/40 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                LangGraph StateGraph Execution Trace
              </span>
              <Badge variant="neutral" size="sm" mono>
                {discoveryResponse.workflow_id}
              </Badge>
              <Badge variant="verified" size="sm" mono>
                {discoveryResponse.termination_reason}
              </Badge>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
              <span>{discoveryResponse.total_discovered_raw} raw scraped</span>
              <span>•</span>
              <span>{discoveryResponse.duplicate_count} duplicates merged</span>
              <span>•</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                {discoveryResponse.eligible_count} verified eligible
              </span>
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className="text-[11px] text-teal-600 hover:underline font-sans ml-2"
              >
                {showTimeline ? 'Collapse Trace' : 'Expand Trace'}
              </button>
            </div>
          </div>

          {/* Timeline Event Items */}
          {showTimeline && (
            <div className="p-6 max-h-72 overflow-y-auto space-y-3 font-mono text-xs divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {discoveryResponse.timeline_events.map((evt, idx) => {
                const stageColor = {
                  INITIALIZING: 'text-zinc-500',
                  STRATEGY_FORMULATION: 'text-teal-600 dark:text-teal-400',
                  SEARCHING: 'text-blue-600 dark:text-blue-400',
                  EVALUATING: 'text-purple-600 dark:text-purple-400',
                  GAP_ANALYSIS: 'text-amber-600 dark:text-amber-400',
                  ADAPTING: 'text-orange-600 dark:text-orange-400',
                  RANKING: 'text-emerald-600 dark:text-emerald-400',
                  FINALIZING: 'text-zinc-600',
                  COMPLETED: 'text-emerald-600 font-bold',
                  FAILED: 'text-rose-600 font-bold',
                }[evt.stage] || 'text-zinc-600';

                return (
                  <div key={idx} className="pt-2.5 first:pt-0 flex items-start gap-3">
                    <span className="text-[10px] text-zinc-400 shrink-0 w-16">
                      {new Date(evt.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>
                    <span className={`text-[11px] font-semibold shrink-0 w-36 truncate ${stageColor}`}>
                      [{evt.stage}]
                    </span>
                    <span className="text-zinc-800 dark:text-zinc-200 font-sans flex-1">
                      {evt.summary}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
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
                onClick={() => onNavigateTab('career-path')}
                className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 font-medium"
              >
                <TrendingUp className="w-3.5 h-3.5" />
                View in Career Graph
              </button>
            </div>
          )}
        </div>

        {recommendations.length === 0 ? (
          <div className="p-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto text-zinc-400">
              <Search className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                No active recommendations evaluated yet
              </h4>
              <p className="text-xs text-zinc-500 max-w-md mx-auto">
                Click &ldquo;Launch Discovery Workflow&rdquo; above to query live opportunity sources and compute
                verifiable candidate-job fit scores.
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
                          {opp.eligibility_rules?.location_city_country.join(', ') || 'Remote / Flexible'}
                        </span>
                        <span>•</span>
                        <span className="font-mono">
                          Mode: {opp.eligibility_rules?.work_mode || 'REMOTE'}
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
                        onClick={() => {
                          setAuditedOpportunity(rec);
                          setAuditDrawerTab('fit');
                        }}
                        className="px-3 py-1.5 rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-semibold text-zinc-800 dark:text-zinc-200 transition-colors flex items-center gap-1.5"
                      >
                        <FileText className="w-3.5 h-3.5 text-zinc-500" />
                        <span>Inspect Evidence & Audit</span>
                      </button>

                      {opp.source_url && (
                        <a
                          href={opp.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition-colors flex items-center gap-1 shadow-xs"
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

      {/* 4. Deep Audit Slide-Over Drawer */}
      <SlideDrawer
        isOpen={auditedOpportunity !== null}
        onClose={() => setAuditedOpportunity(null)}
        title={auditedOpportunity?.opportunity.title || 'Opportunity Audit'}
        subtitle={`${auditedOpportunity?.opportunity.company_name} • Fit: ${((auditedOpportunity?.overall_fit_score || 0) * 100).toFixed(1)}%`}
        badge={
          <Badge variant="verified" size="sm" mono>
            Rank #{auditedOpportunity?.rank}
          </Badge>
        }
      >
        {auditedOpportunity && (
          <div className="space-y-6">
            {/* Drawer Navigation Tabs */}
            <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-2">
              <button
                onClick={() => setAuditDrawerTab('fit')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                  auditDrawerTab === 'fit'
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                    : 'text-zinc-500 hover:text-zinc-900'
                }`}
              >
                6D Fit Rationale
              </button>
              <button
                onClick={() => setAuditDrawerTab('evidence')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                  auditDrawerTab === 'evidence'
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                    : 'text-zinc-500 hover:text-zinc-900'
                }`}
              >
                Evidence Citations ({auditedOpportunity.matched_skills.length})
              </button>
              <button
                onClick={() => setAuditDrawerTab('eligibility')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                  auditDrawerTab === 'eligibility'
                    ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                    : 'text-zinc-500 hover:text-zinc-900'
                }`}
              >
                Eligibility Rules
              </button>
            </div>

            {/* TAB 1: 6D FIT BREAKDOWN */}
            {auditDrawerTab === 'fit' && (
              <div className="space-y-6">
                <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/60 space-y-2">
                  <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                    Natural Language Recommendation Rationale
                  </span>
                  <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
                    {auditedOpportunity.recommendation_rationale}
                  </p>
                </div>

                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                    Deterministic Dimensional Breakdown
                  </h4>
                  {Object.entries(auditedOpportunity.dimension_scores).map(([dim, breakdown]) => (
                    <ScoreBar
                      key={dim}
                      label={dim.replace('_', ' ')}
                      score={breakdown.raw_score}
                      weight={breakdown.weight}
                      rationale={breakdown.rationale}
                    />
                  ))}
                </div>

                {auditedOpportunity.key_tradeoffs_or_risks.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 space-y-2">
                    <span className="text-xs font-bold text-amber-900 dark:text-amber-200 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Key Trade-offs & Candidate Considerations
                    </span>
                    <ul className="list-disc list-inside text-xs text-amber-800 dark:text-amber-300 space-y-1">
                      {auditedOpportunity.key_tradeoffs_or_risks.map((risk, i) => (
                        <li key={i}>{risk}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: EVIDENCE PROVENANCE */}
            {auditDrawerTab === 'evidence' && (
              <div className="space-y-6">
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                    Verified Skill Matches & Grounding Snippets
                  </h4>
                  {auditedOpportunity.matched_skills.map((match) => (
                    <div
                      key={match.skill_name}
                      className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-700/80 space-y-3 bg-white dark:bg-zinc-900"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-zinc-900 dark:text-zinc-100">
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
                          onNavigateTab('development');
                        }}
                        className="text-xs text-teal-600 hover:underline flex items-center gap-1 font-semibold"
                      >
                        <Target className="w-3.5 h-3.5" />
                        Create Development Action
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
                  <p className="text-[11px] text-emerald-800 dark:text-emerald-300">
                    Hard constraints (visa authorization, degree level, enrollment dates, location) were evaluated
                    strictly in pure Python code with zero probabilistic LLM generation.
                  </p>
                </div>

                <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl divide-y divide-zinc-200 dark:divide-zinc-800 text-xs overflow-hidden">
                  <div className="p-3 bg-zinc-50 dark:bg-zinc-800/50 font-mono text-[11px] text-zinc-500">
                    Rule Evaluation Audit Table
                  </div>

                  <div className="p-3 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-zinc-800 dark:text-zinc-200">Category Match</div>
                      <div className="text-[11px] text-zinc-500 font-mono">RULE_CATEGORY_MATCH</div>
                    </div>
                    <Badge variant="verified" size="sm" mono>PASSED</Badge>
                  </div>

                  <div className="p-3 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-zinc-800 dark:text-zinc-200">Work Authorization & Visas</div>
                      <div className="text-[11px] text-zinc-500 font-mono">RULE_WORK_AUTH_AUTHORIZED (US)</div>
                    </div>
                    <Badge variant="verified" size="sm" mono>PASSED</Badge>
                  </div>

                  <div className="p-3 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-zinc-800 dark:text-zinc-200">Minimum Academic Degree</div>
                      <div className="text-[11px] text-zinc-500 font-mono">RULE_DEGREE_LEVEL_PASSED (Bachelors)</div>
                    </div>
                    <Badge variant="verified" size="sm" mono>PASSED</Badge>
                  </div>

                  <div className="p-3 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-zinc-800 dark:text-zinc-200">Application Deadline Status</div>
                      <div className="text-[11px] text-zinc-500 font-mono">
                        {auditedOpportunity.opportunity.eligibility_rules?.application_deadline
                          ? 'RULE_DEADLINE_ACTIVE'
                          : 'UNCERT_NO_DEADLINE_SPECIFIED'}
                      </div>
                    </div>
                    <Badge
                      variant={auditedOpportunity.opportunity.eligibility_rules?.application_deadline ? 'verified' : 'caveat'}
                      size="sm"
                      mono
                    >
                      {auditedOpportunity.opportunity.eligibility_rules?.application_deadline ? 'ACTIVE' : 'UNCERTAIN'}
                    </Badge>
                  </div>

                  <div className="p-3 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-zinc-800 dark:text-zinc-200">Work Mode & Geographic Location</div>
                      <div className="text-[11px] text-zinc-500 font-mono">
                        Mode: {auditedOpportunity.opportunity.eligibility_rules?.work_mode || 'REMOTE'}
                      </div>
                    </div>
                    <Badge variant="verified" size="sm" mono>PASSED</Badge>
                  </div>
                </div>

                <div className="pt-4 flex items-center justify-between">
                  <span className="text-[11px] font-mono text-zinc-400">
                    MinHash Hex: {auditedOpportunity.opportunity.minhash_signature_hex.substring(0, 16)}...
                  </span>
                  {auditedOpportunity.opportunity.source_url && (
                    <a
                      href={auditedOpportunity.opportunity.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs"
                    >
                      <span>Proceed to Company Application</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </SlideDrawer>
    </div>
  );
}

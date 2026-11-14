'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  Bookmark,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Brain,
  RotateCw,
  ChevronRight,
  TrendingUp,
  FileText,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  CandidateOpportunityActionRecord,
  CandidateActionsSummary,
  CandidateCareerMemoryItem,
  ActionType,
  ActionReasonCategory,
} from '@/types/domain';
import {
  getCandidateActionsSummary,
  getCandidateActionHistory,
  getCandidateMemories,
  getMemoryLineage,
} from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { WorkspaceTab } from '@/components/layout/Header';

interface ActivityWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab: (tab: WorkspaceTab) => void;
}

type ActivityTab = 'ledger' | 'memory' | 'feedback';

const REASON_LABELS: Record<ActionReasonCategory, string> = {
  SALARY: 'Salary / Compensation',
  LOCATION: 'Geographic Commute / Location',
  ROLE_MISMATCH: 'Role / Seniority Mismatch',
  COMPANY_PREFERENCE: 'Company / Industry Preference',
  EXPERIENCE_OVERRIDE: 'Overrode Experience Shortfall',
  COMMUTE_OVERRIDE: 'Overrode Location Constraint',
  QUALIFICATION_OVERRIDE: 'Overrode Qualification Requirement',
  GENERAL: 'General Assessment',
};

export function ActivityWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
}: ActivityWorkspaceProps) {
  const [activeTab, setActiveTab] = useState<ActivityTab>('ledger');
  const [actionSummary, setActionSummary] = useState<CandidateActionsSummary | null>(null);
  const [actionHistory, setActionHistory] = useState<CandidateOpportunityActionRecord[]>([]);
  const [memories, setMemories] = useState<CandidateCareerMemoryItem[]>([]);
  const [selectedActionFilter, setSelectedActionFilter] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const userId = candidateProfile.user_id;

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [summary, history, mems] = await Promise.all([
        getCandidateActionsSummary(userId).catch(() => null),
        getCandidateActionHistory(userId, undefined, 200).catch(() => []),
        getCandidateMemories(userId, undefined, true).catch(() => []),
      ]);
      setActionSummary(summary);
      setActionHistory(history);
      setMemories(mems);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load candidate activity history.');
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const handleRefresh = async () => {
    setIsLoading(true);
    await loadData();
  };

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const [summary, history, mems] = await Promise.all([
          getCandidateActionsSummary(userId).catch(() => null),
          getCandidateActionHistory(userId, undefined, 200).catch(() => []),
          getCandidateMemories(userId, undefined, true).catch(() => []),
        ]);
        if (!ignore) {
          setActionSummary(summary);
          setActionHistory(history);
          setMemories(mems);
        }
      } catch (err) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : 'Failed to load candidate activity history.');
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [userId]);

  // Filtered action items
  const filteredActions = actionHistory.filter((item) => {
    if (selectedActionFilter === 'ALL') return true;
    return item.action_type === selectedActionFilter;
  });

  return (
    <div className="space-y-6">
      {/* 1. Header & Statistical Overview */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80 shrink-0">
                <History className="w-4 h-4" />
              </span>
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Activity & Interaction Intelligence
              </h1>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl">
              Persistent historical audit of all opportunity actions, decision rationale, soft overrides, and evolving career understanding for <span className="font-semibold text-zinc-800 dark:text-zinc-200">{candidateName}</span>.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-xs font-semibold text-zinc-700 dark:text-zinc-300 transition-colors cursor-pointer w-full sm:w-auto min-h-[38px] sm:min-h-0"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-teal-600' : ''}`} />
              <span>Refresh History</span>
            </button>
          </div>
        </div>

        {/* Aggregate KPI Counter Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-4 border-t border-zinc-100 dark:border-zinc-800/80 text-xs">
          {/* Saved */}
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50 space-y-1">
            <div className="flex items-center gap-1.5 text-zinc-400 text-[11px] font-mono">
              <Bookmark className="w-3.5 h-3.5 text-blue-500" />
              <span>SAVED</span>
            </div>
            <div className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {actionSummary?.saved_opportunity_ids?.length || 0}
            </div>
          </div>

          {/* Applied */}
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50 space-y-1">
            <div className="flex items-center gap-1.5 text-zinc-400 text-[11px] font-mono">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              <span>APPLIED</span>
            </div>
            <div className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {actionSummary?.applied_opportunity_ids?.length || 0}
            </div>
          </div>

          {/* Dismissed */}
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50 space-y-1">
            <div className="flex items-center gap-1.5 text-zinc-400 text-[11px] font-mono">
              <XCircle className="w-3.5 h-3.5 text-zinc-400" />
              <span>DISMISSED</span>
            </div>
            <div className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {actionSummary?.dismissed_opportunity_ids?.length || 0}
            </div>
          </div>

          {/* Soft Overrides */}
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50 space-y-1">
            <div className="flex items-center gap-1.5 text-zinc-400 text-[11px] font-mono">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-500" />
              <span>OVERRIDDEN</span>
            </div>
            <div className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {actionSummary?.soft_overridden_opportunity_ids?.length || 0}
            </div>
          </div>

          {/* Career Facts */}
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50 space-y-1 col-span-2 sm:col-span-1">
            <div className="flex items-center gap-1.5 text-zinc-400 text-[11px] font-mono">
              <Brain className="w-3.5 h-3.5 text-teal-500" />
              <span>MEMORY FACTS</span>
            </div>
            <div className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {memories.filter((m) => m.is_active).length}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Workspace Navigation Bar */}
      <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-2 overflow-x-auto no-scrollbar flex-nowrap sm:flex-wrap">
        <button
          onClick={() => setActiveTab('ledger')}
          className={`flex items-center gap-2 px-3.5 py-2 sm:py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 whitespace-nowrap min-h-[38px] ${
            activeTab === 'ledger'
              ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-xs'
              : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
          }`}
        >
          <Bookmark className="w-3.5 h-3.5" />
          <span>Opportunity Ledger ({actionHistory.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('memory')}
          className={`flex items-center gap-2 px-3.5 py-2 sm:py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 whitespace-nowrap min-h-[38px] ${
            activeTab === 'memory'
              ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-xs'
              : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
          }`}
        >
          <Brain className="w-3.5 h-3.5" />
          <span>Career Memory Evolution ({memories.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('feedback')}
          className={`flex items-center gap-2 px-3.5 py-2 sm:py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 whitespace-nowrap min-h-[38px] ${
            activeTab === 'feedback'
              ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 shadow-xs'
              : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
          }`}
        >
          <TrendingUp className="w-3.5 h-3.5" />
          <span>Feedback Signals & Guardrails</span>
        </button>
      </div>

      {/* 3. Tab Contents */}

      {/* TAB A: Opportunity Action Ledger */}
      {activeTab === 'ledger' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar flex-nowrap sm:flex-wrap pb-1">
              <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider mr-1 shrink-0">Filter:</span>
              {['ALL', 'SAVED', 'APPLIED', 'DISMISSED', 'SOFT_OVERRIDDEN'].map((filterKey) => (
                <button
                  key={filterKey}
                  onClick={() => setSelectedActionFilter(filterKey)}
                  className={`px-2.5 py-1.5 sm:py-1 rounded-md text-[11px] font-semibold transition-all cursor-pointer shrink-0 whitespace-nowrap min-h-[34px] sm:min-h-0 ${
                    selectedActionFilter === filterKey
                      ? 'bg-teal-600 text-white shadow-2xs'
                      : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900'
                  }`}
                >
                  {filterKey.replace('_', ' ')}
                </button>
              ))}
            </div>
            <span className="text-[11px] font-mono text-zinc-500 shrink-0">
              Showing {filteredActions.length} transition events
            </span>
          </div>

          {filteredActions.length === 0 ? (
            <div className="p-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-center space-y-3">
              <div className="mx-auto w-10 h-10 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-400">
                <Bookmark className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                No Opportunity Actions Recorded Yet
              </h4>
              <p className="text-xs text-zinc-500 max-w-md mx-auto">
                As you save, apply, dismiss, or override soft rejections on opportunities in the Discovery workspace, each transition will be event-sourced and cataloged here.
              </p>
              <button
                onClick={() => onNavigateTab('discover')}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer shadow-xs"
              >
                Go to Discovery Workspace
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredActions.map((action) => {
                const isOverride = action.action_type === 'SOFT_OVERRIDDEN';
                const isDismiss = action.action_type === 'DISMISSED';
                const isApply = action.action_type === 'APPLIED';
                const isSave = action.action_type === 'SAVED';

                return (
                  <div
                    key={action.id}
                    className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        {isSave && <Badge variant="teal" size="sm">SAVED</Badge>}
                        {isApply && <Badge variant="verified" size="sm">APPLIED</Badge>}
                        {isDismiss && <Badge variant="outline" size="sm">DISMISSED</Badge>}
                        {isOverride && <Badge variant="caveat" size="sm">SOFT OVERRIDE</Badge>}

                        <span className="font-mono text-xs font-bold text-zinc-800 dark:text-zinc-200">
                          {action.opportunity_id}
                        </span>

                        {action.previous_state && (
                          <span className="text-[11px] font-mono text-zinc-400">
                            (transitioned from <span className="font-semibold">{action.previous_state}</span>)
                          </span>
                        )}
                      </div>

                      <span className="text-[11px] font-mono text-zinc-400 shrink-0">
                        {new Date(action.created_at).toLocaleString()}
                      </span>
                    </div>

                    {/* Reason Category */}
                    {action.reason_category && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-zinc-500 font-mono text-[11px]">Reason Category:</span>
                        <span className="font-medium text-zinc-700 dark:text-zinc-300">
                          {REASON_LABELS[action.reason_category] || action.reason_category}
                        </span>
                      </div>
                    )}

                    {/* Override Rationale */}
                    {action.soft_override_rationale && (
                      <div className="p-2.5 rounded-lg bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-800/50 text-xs space-y-1">
                        <div className="font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
                          <span>Candidate Soft-Rejection Override Rationale</span>
                        </div>
                        <p className="text-amber-900 dark:text-amber-200 font-sans leading-relaxed">
                          &ldquo;{action.soft_override_rationale}&rdquo;
                        </p>
                      </div>
                    )}

                    {/* Candidate Notes */}
                    {action.user_notes && (
                      <div className="text-xs text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/40 p-2.5 rounded-lg border border-zinc-200/50 dark:border-zinc-700/50">
                        <span className="font-mono text-[10px] text-zinc-400 uppercase block mb-0.5">Notes:</span>
                        <span>{action.user_notes}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB B: Career Memory Evolution */}
      {activeTab === 'memory' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-teal-50/40 dark:bg-teal-950/20 border border-teal-200/70 dark:border-teal-800/60 text-xs space-y-1">
            <span className="font-bold text-teal-800 dark:text-teal-300 flex items-center gap-1.5">
              <Brain className="w-4 h-4 text-teal-600" />
              <span>Epistemic Memory & Provenance Lineage</span>
            </span>
            <p className="text-teal-900 dark:text-teal-200 leading-relaxed">
              JobFalcon maintains immutable version history for candidate career goals and preference shifts. When a fact changes, the previous version is archived with explicit timestamps, change reasons, and superseded lineage.
            </p>
          </div>

          {memories.length === 0 ? (
            <div className="p-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-center space-y-3">
              <Brain className="w-8 h-8 text-zinc-400 mx-auto" />
              <h4 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                No Career Memory Facts Recorded
              </h4>
              <p className="text-xs text-zinc-500 max-w-md mx-auto">
                Career memory records goals, domain shifts, and explicit preference evolutions. You can add career memories in your Career Profile workspace.
              </p>
              <button
                onClick={() => onNavigateTab('career')}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer shadow-xs"
              >
                Go to Career Profile
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {memories.map((mem) => (
                <div
                  key={mem.memory_id}
                  className={`p-4 rounded-xl border transition-all ${
                    mem.is_active
                      ? 'bg-white dark:bg-zinc-900 border-zinc-200/90 dark:border-zinc-800 shadow-xs'
                      : 'bg-zinc-50/60 dark:bg-zinc-900/40 border-zinc-200/50 dark:border-zinc-800/40 opacity-75'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700">
                        v{mem.version}
                      </span>
                      <Badge variant={mem.is_active ? 'verified' : 'neutral'} size="sm">
                        {mem.is_active ? 'ACTIVE' : 'SUPERSEDED'}
                      </Badge>
                      <Badge variant="outline" size="sm" mono>
                        {mem.memory_type}
                      </Badge>
                      <Badge variant="teal" size="sm">
                        {mem.provenance_level}
                      </Badge>
                    </div>

                    <span className="text-[11px] font-mono text-zinc-400">
                      Effective: {new Date(mem.effective_from).toLocaleDateString()}
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mt-2 font-sans">
                    {mem.statement}
                  </p>

                  {/* Change Reason if updated/superseded */}
                  {mem.change_reason && (
                    <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-800/40 p-2 rounded-lg border border-zinc-200/50 dark:border-zinc-700/50 space-y-0.5">
                      <span className="font-mono text-[10px] text-zinc-400 uppercase">Change Reason:</span>
                      <p className="font-sans italic">&ldquo;{mem.change_reason}&rdquo;</p>
                    </div>
                  )}

                  {mem.superseded_by && (
                    <div className="mt-2 text-[11px] font-mono text-zinc-400 flex items-center gap-1">
                      <span>Superseded by fact:</span>
                      <span className="font-bold text-zinc-600 dark:text-zinc-300">{mem.superseded_by}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB C: Feedback Signals & Guardrails */}
      {activeTab === 'feedback' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 space-y-2 text-xs">
            <h4 className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-teal-600" />
              <span>Reason-Aware Feedback Guardrails</span>
            </h4>
            <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
              In accordance with JobFalcon&apos;s core invariants, candidate dismissals are categorized by root cause. Dismissals caused by geographic commute or compensation never penalize the underlying role title or technical company profile.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-2">
              <span className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5 text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Geographic & Salary Isolation</span>
              </span>
              <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                When you dismiss a position due to <span className="font-semibold text-zinc-800 dark:text-zinc-200">Location</span> or <span className="font-semibold text-zinc-800 dark:text-zinc-200">Salary</span>, the system notes the constraint mismatch without reducing your relevance scores for that engineering discipline.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-2">
              <span className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5 text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Immutable Eligibility Audits</span>
              </span>
              <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed">
                When you override a soft eligibility rejection (such as experience shortfall), the underlying deterministic audit log remains intact and immutable for scientific evaluation. The recommendation engine honors your override while preserving epistemic honesty.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

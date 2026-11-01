'use client';

import React, { useState, useEffect } from 'react';
import {
  Target,
  CheckCircle2,
  GitPullRequest,
  ShieldCheck,
  Compass,
} from 'lucide-react';
import {
  type ActionProgressStatus,
  CandidateCareerGapAnalysisResponse,
  CandidateCareerProfile,
  DevelopmentActionItem,
  PersonalizedDevelopmentPlan,
  UpdateActionProgressRequest,
} from '@/types/domain';
import {
  getDevelopmentPlan,
  runCareerGapAnalysis,
  updateActionProgress,
} from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { WorkspaceTab } from '@/components/layout/Header';

interface DevelopmentWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab: (tab: WorkspaceTab) => void;
}

export function DevelopmentWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
}: DevelopmentWorkspaceProps) {
  const [horizonFilter, setHorizonFilter] = useState<'ALL' | 'SHORT_TERM' | 'LONG_TERM'>('ALL');
  const [plan, setPlan] = useState<PersonalizedDevelopmentPlan | null>(null);
  const [gapAnalysis, setGapAnalysis] = useState<CandidateCareerGapAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionUpdatingId, setActionUpdatingId] = useState<string | null>(null);
  const [editingArtifactActionId, setEditingArtifactActionId] = useState<string | null>(null);
  const [artifactUrl, setArtifactUrl] = useState<string>('');
  const [candidateNotes, setCandidateNotes] = useState<string>('');
  const [notificationMsg, setNotificationMsg] = useState<string | null>(null);

  // Load plan and gap analysis on mount
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setIsLoading(true);
      try {
        const [planRes, gapRes] = await Promise.allSettled([
          getDevelopmentPlan(candidateProfile.user_id),
          runCareerGapAnalysis(candidateProfile.user_id),
        ]);

        if (isMounted) {
          if (planRes.status === 'fulfilled') setPlan(planRes.value);
          if (gapRes.status === 'fulfilled') setGapAnalysis(gapRes.value);
        }
      } catch (err) {
        console.warn('Error loading development workspace data:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [candidateProfile.user_id]);

  // Handle action status and artifact update
  async function handleUpdateStatus(action: DevelopmentActionItem, newStatus: ActionProgressStatus) {
    setActionUpdatingId(action.action_id);
    try {
      const req: UpdateActionProgressRequest = {
        status: newStatus,
        verification_artifact_url: action.verification_artifact_url,
        candidate_notes: action.candidate_notes,
      };

      const updated = await updateActionProgress(candidateProfile.user_id, action.action_id, req);

      // Update local state smoothly
      if (plan) {
        const updateList = (list: DevelopmentActionItem[]) =>
          list.map((item) => (item.action_id === action.action_id ? updated : item));

        setPlan({
          ...plan,
          short_term_actions: updateList(plan.short_term_actions),
          long_term_actions: updateList(plan.long_term_actions),
        });
      }

      setNotificationMsg(`Updated status for "${action.skill_or_capability}" to ${newStatus}.`);
      setTimeout(() => setNotificationMsg(null), 3000);
    } catch (err: unknown) {
      setNotificationMsg(err instanceof Error ? err.message : 'Failed to update action');
    } finally {
      setActionUpdatingId(null);
    }
  }

  // Handle saving artifact URL and candidate reflection notes
  async function handleSaveArtifact(action: DevelopmentActionItem) {
    setActionUpdatingId(action.action_id);
    try {
      const req: UpdateActionProgressRequest = {
        status: 'COMPLETED',
        verification_artifact_url: artifactUrl.trim() || undefined,
        candidate_notes: candidateNotes.trim() || undefined,
      };

      const updated = await updateActionProgress(candidateProfile.user_id, action.action_id, req);

      if (plan) {
        const updateList = (list: DevelopmentActionItem[]) =>
          list.map((item) => (item.action_id === action.action_id ? updated : item));

        setPlan({
          ...plan,
          short_term_actions: updateList(plan.short_term_actions),
          long_term_actions: updateList(plan.long_term_actions),
        });
      }

      setEditingArtifactActionId(null);
      setArtifactUrl('');
      setCandidateNotes('');
      setNotificationMsg(`Action completed and verified with artifact provenance.`);
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err: unknown) {
      setNotificationMsg(err instanceof Error ? err.message : 'Failed to save artifact');
    } finally {
      setActionUpdatingId(null);
    }
  }

  const allActions = [
    ...(plan?.short_term_actions || []),
    ...(plan?.long_term_actions || []),
  ];

  const filteredActions = allActions.filter((a) => {
    if (horizonFilter === 'SHORT_TERM') return a.horizon === 'SHORT_TERM';
    if (horizonFilter === 'LONG_TERM') return a.horizon === 'LONG_TERM';
    return true;
  });

  const completedCount = allActions.filter((a) => a.status === 'COMPLETED').length;

  return (
    <div className="space-y-8">
      {/* 1. Header & Strategy Summary */}
      <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-md bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <Target className="w-4 h-4" />
              </span>
              <h2 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Personalized Development & Gap Analysis
              </h2>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Grounds developmental priorities in real discovered opportunity demand and identified skill gaps
              for {candidateName}. Completing actions produces verifiable evidence to strengthen candidate fit.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigateTab('discover')}
              className="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Compass className="w-3.5 h-3.5 text-teal-400 dark:text-teal-600" />
              <span>Test Fit in Discovery</span>
            </button>
          </div>
        </div>

        {/* Ethical Disclaimer Callout */}
        <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-700/60 text-xs flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0" />
          <p className="text-zinc-700 dark:text-zinc-300">
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">Ethical Commitment:</span>{' '}
            {plan?.ethical_disclaimer ||
              'Completing development actions provides verifiable evidence of capabilities but does not guarantee employment or specific algorithmic ranking.'}
          </p>
        </div>

        {/* Action Completion Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Total Actions</span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{allActions.length}</span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Completed</span>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {completedCount} / {allActions.length}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Short-Term</span>
            <span className="text-sm font-bold text-teal-600 dark:text-teal-400">
              {plan?.short_term_actions.length || 0}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Long-Term</span>
            <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
              {plan?.long_term_actions.length || 0}
            </span>
          </div>
        </div>
      </div>

      {notificationMsg && (
        <div className="p-3.5 rounded-lg bg-teal-50 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 text-xs text-teal-800 dark:text-teal-200 flex items-center justify-between">
          <span>{notificationMsg}</span>
        </div>
      )}

      {/* 2. Prioritized Skill Gap Queue (NOT_DEMONSTRATED vs PROFICIENCY_UNCERTAIN) */}
      {gapAnalysis && gapAnalysis.prioritized_gaps.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Identified Skill Gaps ({gapAnalysis.prioritized_gaps.length})
            </h3>
            <span className="text-xs text-zinc-500 font-mono">
              Categorized by epistemic certainty
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {gapAnalysis.prioritized_gaps.map((gap) => (
              <div
                key={gap.canonical_skill_id}
                className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-2.5 shadow-xs text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-zinc-900 dark:text-zinc-100">
                    {gap.skill_name}
                  </span>
                  <Badge
                    variant={gap.gap_status === 'NOT_DEMONSTRATED' ? 'caveat' : 'teal'}
                    size="sm"
                    mono
                  >
                    {gap.gap_status}
                  </Badge>
                </div>

                <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed text-[11px]">
                  {gap.why_it_matters}
                </p>

                <div className="p-2 rounded bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-100 dark:border-zinc-700/60 text-[11px] text-zinc-700 dark:text-zinc-300">
                  <span className="font-semibold text-teal-600">Action: </span>
                  {gap.suggested_action}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Action Queue & Verification Artifact Tracking */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
            Concrete Development Actions
          </h3>

          <SegmentedControl
            options={[
              { id: 'ALL', label: 'All Horizons', count: allActions.length },
              { id: 'SHORT_TERM', label: 'Short-Term', count: plan?.short_term_actions.length || 0 },
              { id: 'LONG_TERM', label: 'Long-Term', count: plan?.long_term_actions.length || 0 },
            ]}
            value={horizonFilter}
            onChange={setHorizonFilter}
            size="sm"
          />
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-zinc-500 font-mono">
            Loading personalized development plan...
          </div>
        ) : filteredActions.length === 0 ? (
          <div className="p-12 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-center text-xs text-zinc-500">
            No action items match the active horizon filter.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filteredActions.map((action) => {
              const isCompleted = action.status === 'COMPLETED';
              const isEditing = editingArtifactActionId === action.action_id;

              return (
                <div
                  key={action.action_id}
                  className={`p-5 rounded-xl border transition-all duration-150 space-y-4 shadow-xs ${
                    isCompleted
                      ? 'bg-emerald-50/20 dark:bg-emerald-950/10 border-emerald-200 dark:border-emerald-800/60'
                      : 'bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                          {action.skill_or_capability}
                        </span>
                        <Badge
                          variant={action.horizon === 'SHORT_TERM' ? 'teal' : 'neutral'}
                          size="sm"
                          mono
                        >
                          {action.horizon}
                        </Badge>
                        <Badge
                          variant={action.priority === 'CRITICAL' ? 'disqualified' : 'caveat'}
                          size="sm"
                        >
                          {action.priority}
                        </Badge>
                      </div>

                      <p className="text-xs text-zinc-600 dark:text-zinc-300">
                        {action.motivating_gap_description}
                      </p>
                    </div>

                    {/* Status Toggle Buttons */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => handleUpdateStatus(action, 'NOT_STARTED')}
                        disabled={actionUpdatingId === action.action_id}
                        className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors ${
                          action.status === 'NOT_STARTED'
                            ? 'bg-zinc-800 text-white dark:bg-zinc-200 dark:text-zinc-900'
                            : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200'
                        }`}
                      >
                        Not Started
                      </button>

                      <button
                        onClick={() => handleUpdateStatus(action, 'IN_PROGRESS')}
                        disabled={actionUpdatingId === action.action_id}
                        className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors ${
                          action.status === 'IN_PROGRESS'
                            ? 'bg-amber-600 text-white'
                            : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200'
                        }`}
                      >
                        In Progress
                      </button>

                      <button
                        onClick={() => {
                          setEditingArtifactActionId(action.action_id);
                          setArtifactUrl(action.verification_artifact_url || '');
                          setCandidateNotes(action.candidate_notes || '');
                        }}
                        disabled={actionUpdatingId === action.action_id}
                        className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors flex items-center gap-1 ${
                          isCompleted
                            ? 'bg-emerald-600 text-white'
                            : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200'
                        }`}
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Completed</span>
                      </button>
                    </div>
                  </div>

                  {/* Concrete Activity & Completion Criterion */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/60 space-y-1">
                      <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
                        Concrete Activity
                      </span>
                      <p className="text-zinc-800 dark:text-zinc-200">{action.concrete_activity}</p>
                    </div>

                    <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/60 space-y-1">
                      <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
                        Measurable Completion Criterion
                      </span>
                      <p className="text-zinc-800 dark:text-zinc-200">
                        {action.measurable_completion_criterion}
                      </p>
                    </div>
                  </div>

                  {/* Proof Artifact Display or Editor */}
                  {isEditing ? (
                    <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/70 border border-zinc-300 dark:border-zinc-700 space-y-3 text-xs">
                      <span className="font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                        <GitPullRequest className="w-3.5 h-3.5 text-teal-600" />
                        Record Proof Artifact & Mark Completed
                      </span>

                      <div className="space-y-1">
                        <label className="text-[11px] text-zinc-500 font-mono">
                          Artifact Provenance URL (GitHub PR, Live Demo, Repo Link):
                        </label>
                        <input
                          type="url"
                          value={artifactUrl}
                          onChange={(e) => setArtifactUrl(e.target.value)}
                          placeholder="https://github.com/username/project/pull/12"
                          className="w-full p-2 rounded bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 font-mono text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-[11px] text-zinc-500 font-mono">
                          Self-Reflection or Implementation Notes (Optional):
                        </label>
                        <input
                          type="text"
                          value={candidateNotes}
                          onChange={(e) => setCandidateNotes(e.target.value)}
                          placeholder="e.g., Implemented Redis pub/sub queue with 95% test coverage."
                          className="w-full p-2 rounded bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                        />
                      </div>

                      <div className="flex items-center justify-end gap-2 pt-1">
                        <button
                          onClick={() => setEditingArtifactActionId(null)}
                          className="px-3 py-1.5 rounded text-xs text-zinc-500 hover:text-zinc-700 font-mono"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveArtifact(action)}
                          className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs"
                        >
                          Save & Mark Complete
                        </button>
                      </div>
                    </div>
                  ) : action.verification_artifact_url ? (
                    <div className="flex items-center justify-between text-xs p-2.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 font-mono">
                      <div className="flex items-center gap-2 truncate">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span className="text-zinc-500">Artifact:</span>
                        <a
                          href={action.verification_artifact_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-teal-600 dark:text-teal-400 hover:underline truncate"
                        >
                          {action.verification_artifact_url}
                        </a>
                      </div>
                      <button
                        onClick={() => {
                          setEditingArtifactActionId(action.action_id);
                          setArtifactUrl(action.verification_artifact_url || '');
                          setCandidateNotes(action.candidate_notes || '');
                        }}
                        className="text-[11px] text-zinc-400 hover:text-zinc-600 shrink-0 ml-3"
                      >
                        Edit
                      </button>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

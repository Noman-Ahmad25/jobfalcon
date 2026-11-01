'use client';

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Compass,
  ArrowRight,
  ShieldCheck,
  RotateCw,
  Sparkles,
  Network,
} from 'lucide-react';
import {
  CareerPathAssessmentResponse,
  CandidateCareerProfile,
} from '@/types/domain';
import { getCareerPathAssessment, refreshCareerPathAssessment } from '@/lib/api';
import { Badge, BadgeVariant } from '@/components/ui/Badge';
import { WorkspaceTab } from '@/components/layout/Header';

interface CareerPathWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab: (tab: WorkspaceTab, context?: { targetRole?: string }) => void;
}

export function CareerPathWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
}: CareerPathWorkspaceProps) {
  const [assessment, setAssessment] = useState<CareerPathAssessmentResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  // Load career path assessment on mount
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setIsLoading(true);
      try {
        const res = await getCareerPathAssessment(candidateProfile.user_id, false);
        if (isMounted) {
          setAssessment(res);
          if (res.role_assessments.length > 0) {
            setSelectedRole(res.role_assessments[0].role_title);
          }
        }
      } catch (err) {
        console.warn('Unable to load career path assessment:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, [candidateProfile.user_id]);

  async function handleRefresh() {
    setIsRefreshing(true);
    try {
      const res = await refreshCareerPathAssessment(candidateProfile.user_id);
      setAssessment(res);
    } catch (err) {
      console.warn('Failed to refresh assessment:', err);
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* 1. Header & Career Trajectory Summary */}
      <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-md bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <TrendingUp className="w-4 h-4" />
              </span>
              <h2 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Career Path Intelligence & Market Signals
              </h2>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Analyzes realistic career progression, skill overlap ratios, and market demand signals
              grounded in discovered opportunities for {candidateName}.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="px-3.5 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-semibold text-zinc-800 dark:text-zinc-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Refresh Graph</span>
            </button>

            <button
              onClick={() => onNavigateTab('discover')}
              className="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Compass className="w-3.5 h-3.5 text-teal-400 dark:text-teal-600" />
              <span>Find Matches for Trajectory</span>
            </button>
          </div>
        </div>

        {/* Essential Guarantee */}
        <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-700/60 text-xs flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-teal-600 shrink-0" />
            <span className="text-zinc-700 dark:text-zinc-300">
              Taxonomy Grounded: All role adjacencies use verified O*NET / ESCO occupational mappings.
            </span>
          </div>

          <Badge variant="verified" size="sm" mono>
            CYCLE-SAFE DAG
          </Badge>
        </div>

        {/* Roles Metric Strip */}
        <div className="grid grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Target Roles</span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              {assessment?.total_target_roles || candidateProfile.target_career_paths.length}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Adjacent Trajectories</span>
            <span className="text-sm font-bold text-teal-600 dark:text-teal-400">
              {assessment?.total_adjacent_roles || candidateProfile.adjacent_career_paths.length}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Exploratory</span>
            <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
              {assessment?.total_exploratory_roles || 0}
            </span>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-zinc-500 font-mono">
          Analyzing career path intelligence and market signals...
        </div>
      ) : (
        <>
          {/* 2. Target vs Adjacent Role Readiness Cards */}
          <div className="space-y-4">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
              Evaluated Occupational Roles ({assessment?.role_assessments.length || 0})
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {assessment?.role_assessments.map((role) => {
                const isSelected = selectedRole === role.role_title;
                const overlapPercent = (role.skill_overlap_ratio * 100).toFixed(0);

                const readinessBadge: BadgeVariant =
                  role.readiness === 'PURSUABLE_NOW'
                    ? 'verified'
                    : role.readiness === 'ATTAINABLE_WITH_DEVELOPMENT'
                    ? 'teal'
                    : 'neutral';

                return (
                  <div
                    key={role.role_title}
                    onClick={() => setSelectedRole(role.role_title)}
                    className={`p-5 rounded-xl border cursor-pointer transition-all duration-150 space-y-4 shadow-xs ${
                      isSelected
                        ? 'bg-white dark:bg-zinc-900 border-teal-500 ring-2 ring-teal-500/20 shadow-md'
                        : 'bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                            {role.role_title}
                          </h4>
                          <Badge variant={readinessBadge} size="sm" mono>
                            {role.readiness.replace(/_/g, ' ')}
                          </Badge>
                        </div>
                        {role.canonical_occupation_code && (
                          <span className="text-[11px] font-mono text-zinc-400">
                            O*NET: {role.canonical_occupation_code}
                          </span>
                        )}
                      </div>

                      <div className="text-right shrink-0">
                        <span className="text-sm font-bold font-mono text-teal-600 dark:text-teal-400">
                          {overlapPercent}%
                        </span>
                        <span className="text-[10px] text-zinc-400 font-mono block">
                          Skill Overlap
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed">
                      {role.feasibility_rationale}
                    </p>

                    {/* Supporting Skills Badges */}
                    <div className="space-y-1.5 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                      <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
                        Supporting Skills
                      </span>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {role.supporting_skills.map((c: string) => (
                          <Badge key={c} variant="outline" size="sm">
                            {c}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    {/* Opportunity Coverage Badge */}
                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pt-1">
                      <span>Discovered Postings:</span>
                      <span className="font-bold text-zinc-800 dark:text-zinc-200">
                        {role.opportunity_coverage.matching_opportunity_count} active listing(s)
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 3. Cycle-Safe Career Transition Graph (DAG) */}
          {assessment?.career_path_graph && (
            <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                    <Network className="w-4 h-4 text-teal-600" />
                    Career Transition Graph (Cycle-Free DAG)
                  </h3>
                  <p className="text-xs text-zinc-500">
                    Directed progression paths connecting candidate baseline to target ambitions.
                  </p>
                </div>
                <Badge variant="verified" size="sm" mono>
                  CYCLE-SAFE
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {assessment.career_path_graph.edges.map((edge) => (
                  <div
                    key={edge.edge_id}
                    className="p-4 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/60 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-bold text-zinc-900 dark:text-zinc-100">
                        <span>{edge.source_role}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                        <span className="text-teal-700 dark:text-teal-300">{edge.target_role}</span>
                      </div>
                      <Badge variant="outline" size="sm" mono>
                        {edge.transition_type}
                      </Badge>
                    </div>

                    <p className="text-zinc-600 dark:text-zinc-400 text-[11px] leading-relaxed">
                      {edge.basis_description}
                    </p>

                    {edge.development_gaps.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        <span className="text-[10px] text-zinc-400 font-mono">Bridging Skills:</span>
                        {edge.development_gaps.map((bs: string) => (
                          <Badge key={bs} variant="caveat" size="sm">
                            {bs}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. Discovered Market Skill Signals */}
          {assessment?.development_plan.market_insights && (
            <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-teal-600" />
                    Discovered Market Demand Signals
                  </h3>
                  <p className="text-xs text-zinc-500">
                    Real skill demand patterns extracted from discovered opportunities across WebSearch, MCP, and ATS feeds.
                  </p>
                </div>
                <Badge variant="teal" size="sm" mono>
                  SAMPLE: {assessment.development_plan.market_insights.total_opportunities_analyzed} LISTINGS
                </Badge>
              </div>

              {/* Mandatory Limitation Disclosure */}
              <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/50 text-[11px] text-zinc-600 dark:text-zinc-400">
                <span className="font-semibold text-zinc-800 dark:text-zinc-200">Limitation Disclosure: </span>
                {assessment.development_plan.market_insights.limitation_disclosure}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {assessment.development_plan.market_insights.recurring_skills.map((sig) => (
                  <div
                    key={sig.skill_name}
                    className="p-3.5 rounded-lg bg-zinc-50/70 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/60 space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">
                        {sig.skill_name}
                      </span>
                      <Badge
                        variant={sig.signal_type === 'EXPLICITLY_REQUIRED' ? 'verified' : 'teal'}
                        size="sm"
                        mono
                      >
                        {sig.signal_type}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500">
                      <span>Frequency in Sample:</span>
                      <span className="font-bold text-zinc-800 dark:text-zinc-200">
                        {sig.frequency_in_sample} occurrence(s)
                      </span>
                    </div>

                    {sig.supporting_job_titles.length > 0 && (
                      <p className="text-[10px] text-zinc-400 truncate">
                        Postings: {sig.supporting_job_titles.join(', ')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  Layers,
  Clock,
  ShieldCheck,
  RotateCw,
  MapPin,
  Briefcase,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  MarketIntelligenceResponse,
  MarketSkillDemand,
} from '@/types/domain';
import { getMarketIntelligence } from '@/lib/api';

interface MarketIntelligenceWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
}

export function MarketIntelligenceWorkspace({
  candidateProfile,
  candidateName,
}: MarketIntelligenceWorkspaceProps) {
  const targetRoleTitle = candidateProfile.target_career_paths[0]?.title || '';
  const [scopeToTargetRole, setScopeToTargetRole] = useState<boolean>(false);
  const [intelligence, setIntelligence] = useState<MarketIntelligenceResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIntelligence = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await getMarketIntelligence({
        target_role: scopeToTargetRole && targetRoleTitle ? targetRoleTitle : undefined,
      });
      setIntelligence(resp);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch market intelligence';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [scopeToTargetRole, targetRoleTitle]);

  useEffect(() => {
    let isCancelled = false;
    async function load() {
      try {
        const resp = await getMarketIntelligence({
          target_role: scopeToTargetRole && targetRoleTitle ? targetRoleTitle : undefined,
        });
        if (!isCancelled) {
          setIntelligence(resp);
          setIsLoading(false);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : 'Failed to fetch market intelligence';
          setError(msg);
          setIsLoading(false);
        }
      }
    }
    load();
    return () => {
      isCancelled = true;
    };
  }, [scopeToTargetRole, targetRoleTitle]);

  const candidateSkillsSet = new Set(
    candidateProfile.assessed_skills.map((s) => s.skill_name.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header & Empirical Scope Banner */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <BarChart3 className="w-4 h-4" />
              </span>
              <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Market Intelligence & Demand Analytics
              </h1>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl">
              Empirical market intelligence for {candidateName} grounded strictly in analyzed vacancies. Understand what skills and technologies employers are actually requesting right now.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setScopeToTargetRole(!scopeToTargetRole)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                scopeToTargetRole
                  ? 'bg-teal-50 dark:bg-teal-950/60 border-teal-300 dark:border-teal-700 text-teal-800 dark:text-teal-300'
                  : 'bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100'
              }`}
            >
              {scopeToTargetRole ? `Scoped: ${targetRoleTitle}` : 'Scope: All Discovered Opportunities'}
            </button>

            <button
              onClick={fetchIntelligence}
              disabled={isLoading}
              className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors"
              title="Refresh intelligence"
            >
              <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Dataset Scope Cards */}
        {intelligence && (
          <div className="pt-2 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
              <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">
                Analyzed Opportunities
              </span>
              <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                {intelligence.total_opportunities_analyzed}
              </div>
              <p className="text-[11px] text-zinc-500">Distinct canonical postings verified</p>
            </div>

            <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
              <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">
                Unique Employers
              </span>
              <div className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                {intelligence.unique_employers_count}
              </div>
              <p className="text-[11px] text-zinc-500">Hiring organizations represented</p>
            </div>

            <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
              <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-teal-600" />
                Data Integrity Guarantee
              </span>
              <div className="text-xs font-medium text-zinc-800 dark:text-zinc-200 leading-snug">
                100% Empirical Distributions
              </div>
              <p className="text-[11px] text-zinc-500">Zero speculative trends or hallucinated arrows</p>
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="p-16 text-center space-y-3">
          <RotateCw className="w-6 h-6 animate-spin text-teal-600 mx-auto" />
          <p className="text-xs text-zinc-500 font-mono">Aggregating market intelligence...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300">
          {error}
        </div>
      ) : !intelligence || intelligence.total_opportunities_analyzed === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 space-y-3">
          <Briefcase className="w-8 h-8 text-zinc-400 mx-auto" />
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            No Opportunities Available for Analysis
          </h3>
          <p className="text-xs text-zinc-500 max-w-md mx-auto">
            Run a Personalized Discovery session or Market Search to ingest and index authentic opportunities in this workspace.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Top Requested Skills Section */}
          <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                  Most Requested Skills & Competencies
                </h2>
                <p className="text-xs text-zinc-500">
                  Exact frequency of technical and professional skills requested across {intelligence.total_opportunities_analyzed} analyzed opportunities.
                </p>
              </div>
              <span className="text-xs font-mono text-zinc-500 hidden sm:inline">
                Highlighted = on your profile
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              {intelligence.top_skills.slice(0, 16).map((skill: MarketSkillDemand) => {
                const isOnProfile = candidateSkillsSet.has(skill.skill_name.toLowerCase());

                return (
                  <div
                    key={skill.skill_name}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isOnProfile
                        ? 'bg-teal-50/40 dark:bg-teal-950/20 border-teal-200 dark:border-teal-800/60'
                        : 'bg-zinc-50/80 dark:bg-zinc-800/30 border-zinc-200/70 dark:border-zinc-700/60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                          {skill.skill_name}
                        </span>
                        {isOnProfile && (
                          <span className="text-[10px] font-mono text-teal-700 dark:text-teal-400 bg-teal-100 dark:bg-teal-900/60 px-1.5 py-0.2 rounded-md">
                            Your Skill
                          </span>
                        )}
                      </div>

                      <div className="text-right">
                        <span className="text-xs font-bold font-mono text-zinc-900 dark:text-zinc-100">
                          {skill.percentage}%
                        </span>
                        <span className="text-[11px] font-mono text-zinc-500 ml-1">
                          ({skill.count} of {intelligence.total_opportunities_analyzed})
                        </span>
                      </div>
                    </div>

                    {/* Frequency Progress Bar */}
                    <div className="w-full h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          isOnProfile ? 'bg-teal-600 dark:bg-teal-400' : 'bg-zinc-500 dark:bg-zinc-400'
                        }`}
                        style={{ width: `${Math.min(100, skill.percentage)}%` }}
                      />
                    </div>

                    {/* Breakdown of Mandatory vs Preferred */}
                    <div className="flex items-center justify-between pt-1.5 text-[10px] text-zinc-500 font-mono">
                      <span>Mandatory in {skill.is_mandatory_count} listings</span>
                      <span>Preferred in {skill.is_preferred_count} listings</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Technology Stacks & Distributions Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top Technology Stacks / Combinations */}
            <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
              <div>
                <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-zinc-500" />
                  <span>Common Technology Combinations</span>
                </h3>
                <p className="text-xs text-zinc-500 pt-0.5">
                  Technologies frequently requested together in the same opportunity listing.
                </p>
              </div>

              {intelligence.top_skill_combinations.length === 0 ? (
                <p className="text-xs text-zinc-400 italic">No multi-skill combinations observed yet.</p>
              ) : (
                <div className="space-y-2.5">
                  {intelligence.top_skill_combinations.map((combo, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        {combo.skills.map((s) => (
                          <span
                            key={s}
                            className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-700 font-medium text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-600 text-[11px]"
                          >
                            {s}
                          </span>
                        ))}
                      </div>

                      <div className="text-right shrink-0">
                        <span className="font-mono font-semibold text-zinc-800 dark:text-zinc-200">
                          {combo.co_occurrence_count} listings
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Experience & Work Mode Distributions */}
            <div className="space-y-6">
              {/* Experience Distribution (Strict Unknown is not zero) */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
                <div>
                  <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-zinc-500" />
                    <span>Experience Expectations</span>
                  </h3>
                  <p className="text-[11px] text-zinc-500 pt-0.5">
                    Truthful representation: unstated experience requirements are labeled explicitly as &quot;Not stated&quot;.
                  </p>
                </div>

                <div className="space-y-2">
                  {Object.entries(intelligence.experience_distribution).map(([tier, count]) => {
                    const pct = intelligence.total_opportunities_analyzed > 0
                      ? Math.round((count / intelligence.total_opportunities_analyzed) * 100)
                      : 0;

                    return (
                      <div key={tier} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-zinc-700 dark:text-zinc-300 font-medium">{tier}</span>
                          <span className="font-mono font-semibold text-zinc-900 dark:text-zinc-100">
                            {count} ({pct}%)
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-teal-500 rounded-full"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Work Arrangement Distribution */}
              <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
                <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-zinc-500" />
                  <span>Work Arrangement Breakdown</span>
                </h3>

                <div className="grid grid-cols-3 gap-3 text-center">
                  {Object.entries(intelligence.work_mode_distribution).map(([mode, count]) => {
                    const pct = intelligence.total_opportunities_analyzed > 0
                      ? Math.round((count / intelligence.total_opportunities_analyzed) * 100)
                      : 0;

                    return (
                      <div
                        key={mode}
                        className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1"
                      >
                        <span className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">
                          {mode.replace('_', ' ')}
                        </span>
                        <div className="text-base font-bold text-zinc-900 dark:text-zinc-100">{pct}%</div>
                        <span className="text-[10px] text-zinc-400 font-mono">{count} roles</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

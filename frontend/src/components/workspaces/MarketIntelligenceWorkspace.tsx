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
  TrendingUp,
  CheckCircle2,
  AlertCircle,
  Building2,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  MarketResearchReportRecord,
  MarketSkillDemand,
  SampleConfidenceTier,
} from '@/types/domain';
import { getMarketResearchReport } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { WorkspaceTab } from '@/components/layout/Header';
import { formatWorkMode } from '@/lib/formatters';

interface MarketIntelligenceWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab?: (tab: WorkspaceTab) => void;
}

const TIER_BADGES: Record<
  SampleConfidenceTier,
  { label: string; variant: 'teal' | 'verified' | 'caveat' | 'neutral' | 'outline'; hint: string }
> = {
  HIGH: {
    label: 'HIGH CONFIDENCE (N ≥ 30)',
    variant: 'verified',
    hint: 'Statistically strong empirical sample providing reliable market signals.',
  },
  MODERATE: {
    label: 'MODERATE CONFIDENCE (N ≥ 15)',
    variant: 'teal',
    hint: 'Substantial empirical sample providing dependable directional guidance.',
  },
  DIRECTIONAL: {
    label: 'DIRECTIONAL SIGNAL (5 ≤ N < 15)',
    variant: 'caveat',
    hint: 'Early directional indicators. Valid empirical trends, limited volume.',
  },
  EMERGING: {
    label: 'EMERGING SIGNAL (1 ≤ N < 5)',
    variant: 'outline',
    hint: 'Emerging observations. Limited opportunity count in this specific scope.',
  },
  EMPTY: {
    label: 'NO POSTINGS (N = 0)',
    variant: 'neutral',
    hint: 'No verified opportunity listings found for this specific query scope.',
  },
};

export function MarketIntelligenceWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
}: MarketIntelligenceWorkspaceProps) {
  const defaultRole =
    candidateProfile.target_career_paths[0]?.title ||
    candidateProfile.headline ||
    'Software Engineer';

  const defaultCountry =
    candidateProfile.eligibility_constraints?.authorized_country_codes?.[0] || 'US';

  const [roleTitle, setRoleTitle] = useState<string>(defaultRole);
  const [countryCode, setCountryCode] = useState<string>(defaultCountry);
  const [careerTrack, setCareerTrack] = useState<string>('TECHNICAL');
  const [report, setReport] = useState<MarketResearchReportRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const candidateSkillsSet = new Set(
    candidateProfile.assessed_skills.map((s) => s.skill_name.toLowerCase().trim())
  );

  const fetchReport = useCallback(
    async (forceRefresh: boolean = false) => {
      setIsLoading(true);
      setError(null);
      try {
        const resp = await getMarketResearchReport({
          roleTitle: roleTitle.trim() || defaultRole,
          countryCode: countryCode.trim() || defaultCountry,
          careerTrack,
          userId: candidateProfile.user_id,
          forceRefresh,
        });
        setReport(resp);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to fetch market report';
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [roleTitle, countryCode, careerTrack, candidateProfile.user_id, defaultRole, defaultCountry]
  );

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const resp = await getMarketResearchReport({
          roleTitle: roleTitle.trim() || defaultRole,
          countryCode: countryCode.trim() || defaultCountry,
          careerTrack,
          userId: candidateProfile.user_id,
          forceRefresh: false,
        });
        if (!ignore) setReport(resp);
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : 'Failed to fetch market report';
          setError(msg);
        }
      } finally {
        if (!ignore) setIsLoading(false);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [roleTitle, countryCode, careerTrack, candidateProfile.user_id, defaultRole, defaultCountry]);

  const currentTier = report?.sample_confidence_tier || 'EMPTY';
  const tierConfig = TIER_BADGES[currentTier] || TIER_BADGES.EMPTY;

  return (
    <div className="space-y-6">
      {/* 1. Header & Scope Selector */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80 shrink-0">
                <BarChart3 className="w-4 h-4" />
              </span>
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Grounded Market Intelligence
              </h1>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl">
              Empirical market intelligence tailored to <span className="font-semibold text-zinc-800 dark:text-zinc-200">{candidateName}</span>&apos;s trajectory. Analyzes real vacancies across employers without speculative or hallucinated trends.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchReport(true)}
              disabled={isLoading}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-xs font-semibold text-zinc-700 dark:text-zinc-300 transition-colors cursor-pointer w-full sm:w-auto min-h-[38px] sm:min-h-0"
              title="Re-aggregate market statistics"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-teal-600' : ''}`} />
              <span>Regenerate Report</span>
            </button>
          </div>
        </div>

        {/* Scope Controls Strip (Candidate-Specific Geography & Career Track) */}
        <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800/80 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          {/* Target Role Input */}
          <div className="space-y-1">
            <label className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
              Role Focus
            </label>
            <input
              type="text"
              value={roleTitle}
              onChange={(e) => setRoleTitle(e.target.value)}
              placeholder="e.g. Backend Software Engineer"
              className="w-full px-3 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-base sm:text-xs text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          {/* Country Scope (Candidate-Specific) */}
          <div className="space-y-1">
            <label className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
              Geographic Region (Country Code)
            </label>
            <input
              type="text"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
              placeholder="e.g. IN, US, GB, DE, CA"
              maxLength={4}
              className="w-full px-3 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-base sm:text-xs font-mono uppercase text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            />
          </div>

          {/* Career Track Type */}
          <div className="space-y-1">
            <label className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
              Career Track
            </label>
            <select
              value={careerTrack}
              onChange={(e) => setCareerTrack(e.target.value)}
              className="w-full px-3 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-base sm:text-xs text-zinc-900 dark:text-zinc-100 focus:outline-hidden focus:ring-2 focus:ring-teal-500"
            >
              <option value="TECHNICAL">Technical & Engineering</option>
              <option value="NON_TECHNICAL">Non-Technical & Operations</option>
              <option value="HYBRID">Hybrid & Product</option>
            </select>
          </div>
        </div>
      </div>

      {/* 2. Statistical Metric Strip & Confidence Tier */}
      {report && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          {/* Sample Size & Confidence Tier */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-zinc-400 uppercase">Sample Size</span>
              <Badge variant={tierConfig.variant} size="sm">
                {tierConfig.label}
              </Badge>
            </div>
            <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              N = {report.sample_size}
            </div>
            <p className="text-[11px] text-zinc-500 leading-snug">{tierConfig.hint}</p>
          </div>

          {/* Unique Employers */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-1.5">
            <span className="text-[10px] font-mono text-zinc-400 uppercase block">Employer Diversity</span>
            <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              {report.unique_employers_count}
            </div>
            <p className="text-[11px] text-zinc-500 leading-snug">Hiring companies represented in dataset</p>
          </div>

          {/* Remote / Hybrid Share */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-1.5">
            <span className="text-[10px] font-mono text-zinc-400 uppercase block">Remote / Hybrid Share</span>
            <div className="text-2xl font-bold font-mono text-teal-600 dark:text-teal-400">
              {report.sample_size > 0
                ? `${Math.round(
                    (((report.work_mode_distribution?.REMOTE || 0) +
                      (report.work_mode_distribution?.HYBRID || 0)) /
                      report.sample_size) *
                      100
                  )}%`
                : '0%'}
            </div>
            <p className="text-[11px] text-zinc-500 leading-snug">Roles offering workplace flexibility</p>
          </div>

          {/* Core Competencies Identified */}
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-1.5">
            <span className="text-[10px] font-mono text-zinc-400 uppercase block">Core Competencies</span>
            <div className="text-2xl font-bold font-mono text-zinc-900 dark:text-zinc-100">
              {report.core_skills?.length || 0}
            </div>
            <p className="text-[11px] text-zinc-500 leading-snug">Distinct mandatory technical requirements</p>
          </div>
        </div>
      )}

      {/* 3. Core vs Preferred Skills Grid */}
      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Core Skills (Mandatory / Essential) */}
          <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Core Technical Requirements
                </h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-400 uppercase">
                {report.core_skills.length} skills identified
              </span>
            </div>
            <p className="text-xs text-zinc-500">
              Skills explicitly designated as mandatory requirements or present across ≥40% of postings.
            </p>

            {report.core_skills.length === 0 ? (
              <div className="text-xs text-zinc-400 py-6 text-center">
                No core requirements extracted for this sample scope.
              </div>
            ) : (
              <div className="space-y-3">
                {report.core_skills.slice(0, 10).map((skill) => {
                  const hasSkill = candidateSkillsSet.has(skill.skill_name.toLowerCase().trim());
                  return (
                    <div key={skill.skill_name} className="space-y-1">
                      <div className="flex items-center justify-between text-xs gap-2">
                        <div className="flex items-center gap-1.5 min-w-0 flex-1">
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200 truncate">
                            {skill.skill_name}
                          </span>
                          {hasSkill ? (
                            <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-200 dark:border-emerald-800 flex items-center gap-0.5 shrink-0">
                              <CheckCircle2 className="w-2.5 h-2.5" />
                              On Profile
                            </span>
                          ) : (
                            <span className="text-[10px] font-mono text-zinc-400 shrink-0">
                              (Skill Gap)
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-500 shrink-0">
                          <span className="hidden sm:inline">{skill.count} postings</span>
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                            {skill.percentage}%
                          </span>
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            hasSkill ? 'bg-teal-500' : 'bg-amber-500'
                          }`}
                          style={{ width: `${Math.min(100, skill.percentage)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Preferred / Advantageous Skills */}
          <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Preferred & Advantageous Competencies
                </h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-400 uppercase">
                {report.preferred_skills.length} skills identified
              </span>
            </div>
            <p className="text-xs text-zinc-500">
              Frequently requested secondary technologies and differentiating qualifications.
            </p>

            {report.preferred_skills.length === 0 ? (
              <div className="text-xs text-zinc-400 py-6 text-center">
                No preferred skills extracted for this sample scope.
              </div>
            ) : (
              <div className="space-y-3">
                {report.preferred_skills.slice(0, 10).map((skill) => {
                  const hasSkill = candidateSkillsSet.has(skill.skill_name.toLowerCase().trim());
                  return (
                    <div key={skill.skill_name} className="space-y-1">
                      <div className="flex items-center justify-between text-xs gap-2">
                        <div className="flex items-center gap-1.5 min-w-0 flex-1">
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200 truncate">
                            {skill.skill_name}
                          </span>
                          {hasSkill && (
                            <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-200 dark:border-emerald-800 shrink-0">
                              ✓ Verified
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-500 shrink-0">
                          <span className="hidden sm:inline">{skill.count} postings</span>
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                            {skill.percentage}%
                          </span>
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${Math.min(100, skill.percentage)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. Co-occurring Stacks & Workplace Distributions */}
      {report && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Workplace Arrangements */}
          <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-3">
            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider block">
              Workplace Arrangements
            </span>
            <div className="space-y-2 text-xs">
              {['REMOTE', 'HYBRID', 'ON_SITE'].map((mode) => {
                const count = report.work_mode_distribution?.[mode] || 0;
                const pct = report.sample_size > 0 ? Math.round((count / report.sample_size) * 100) : 0;
                return (
                  <div key={mode} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-zinc-600 dark:text-zinc-300 font-medium">{formatWorkMode(mode)}</span>
                      <span className="font-mono text-zinc-500">{count} ({pct}%)</span>
                    </div>
                    <div className="h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full bg-teal-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Experience Spread */}
          <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-3">
            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider block">
              Experience Expectations
            </span>
            <div className="space-y-2 text-xs">
              {Object.entries(report.experience_distribution || {}).map(([tier, count]) => {
                const pct = report.sample_size > 0 ? Math.round((count / report.sample_size) * 100) : 0;
                return (
                  <div key={tier} className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-zinc-600 dark:text-zinc-300 font-medium truncate">{tier}</span>
                      <span className="font-mono text-zinc-500">{count} ({pct}%)</span>
                    </div>
                    <div className="h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Top Technology Combinations */}
          <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-3">
            <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider block">
              Frequently Paired Stacks
            </span>
            {report.top_skill_combinations?.length === 0 ? (
              <p className="text-xs text-zinc-400 py-3">No pairwise co-occurrences found.</p>
            ) : (
              <div className="space-y-2 text-xs">
                {report.top_skill_combinations.slice(0, 5).map((combo, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 flex items-center justify-between"
                  >
                    <span className="font-medium text-zinc-800 dark:text-zinc-200 truncate pr-2">
                      {combo.skills.join(' + ')}
                    </span>
                    <span className="font-mono text-[11px] text-zinc-500 shrink-0">
                      {combo.co_occurrence_count} jobs
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. Empirical Synthesis Narrative */}
      {report && report.synthesis_markdown && (
        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-600" />
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Empirical Market Synthesis
            </h3>
          </div>
          <div className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed font-sans prose prose-zinc dark:prose-invert max-w-none">
            {report.synthesis_markdown.split('\n\n').map((para, i) => (
              <p key={i} className="mb-2 last:mb-0">
                {para}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

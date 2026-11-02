'use client';

import React from 'react';
import {
  X,
  ExternalLink,
  Building2,
  MapPin,
  CheckCircle2,
  HelpCircle,
  AlertCircle,
  Clock,
  Sparkles,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  OpportunitySkillRequirement,
  PolymorphicOpportunity,
  RankedOpportunity,
} from '@/types/domain';
import { Badge } from '@/components/ui/Badge';
import { ScoreBar } from '@/components/ui/ScoreBar';

interface OpportunityDetailModalProps {
  opportunity: PolymorphicOpportunity | RankedOpportunity | null;
  candidateProfile?: CandidateCareerProfile | null;
  onClose: () => void;
}

export function OpportunityDetailModal({
  opportunity,
  candidateProfile,
  onClose,
}: OpportunityDetailModalProps) {
  if (!opportunity) return null;

  const isRanked = 'overall_fit_score' in opportunity;
  const opp: PolymorphicOpportunity = isRanked
    ? (opportunity as RankedOpportunity).opportunity
    : (opportunity as PolymorphicOpportunity);
  const ranked = isRanked ? (opportunity as RankedOpportunity) : null;

  // Candidate skills map
  const candidateSkills = new Map(
    candidateProfile?.assessed_skills.map((s) => [s.skill_name.toLowerCase(), s]) || []
  );

  // Requirements categorization
  const demonstratedMatches: OpportunitySkillRequirement[] = [];
  const notDemonstrated: OpportunitySkillRequirement[] = [];
  const preferredSkills: OpportunitySkillRequirement[] = [];

  for (const req of opp.skill_requirements) {
    if (!req.is_mandatory) {
      preferredSkills.push(req);
    } else if (candidateSkills.has(req.skill_name.toLowerCase())) {
      demonstratedMatches.push(req);
    } else {
      notDemonstrated.push(req);
    }
  }

  // Experience requirement evaluation
  const minExpMonths = opp.eligibility_rules.min_experience_months;
  const candidateExpMonths = candidateProfile?.eligibility_constraints.total_full_time_experience_months ?? 0;

  let expDescription = '';
  if (minExpMonths < 0) {
    expDescription = 'Not stated by employer. No explicit minimum experience requirement was detected.';
  } else if (minExpMonths === 0) {
    expDescription = 'Entry level. No prior full-time experience is required for this role.';
  } else {
    const years = minExpMonths / 12;
    const candYears = (candidateExpMonths / 12).toFixed(1);
    if (candidateExpMonths >= minExpMonths) {
      expDescription = `Requests ${years}+ years. Your profile demonstrates ${candYears} years of verified experience (Fully qualified).`;
    } else {
      const deficit = ((minExpMonths - candidateExpMonths) / 12).toFixed(1);
      expDescription = `Requests ${years}+ years. Your profile demonstrates ${candYears} years (${deficit} year stretch). Demonstrated skills provide evidence of capability.`;
    }
  }

  // Source attribution
  const originSource: string =
    typeof opp.category_specific_attributes?.source_system === 'string'
      ? opp.category_specific_attributes.source_system
      : 'Web Search';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="relative w-full max-w-3xl max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-6 border-b border-zinc-200 dark:border-zinc-800 flex items-start justify-between gap-4 bg-zinc-50/50 dark:bg-zinc-900/50">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800/80 px-2 py-0.5 rounded-md">
                {opp.eligibility_rules.opportunity_category.replace(/_/g, ' ')}
              </span>
              <Badge variant="verified" size="sm" mono>
                {opp.eligibility_rules.work_mode}
              </Badge>
              {isRanked && (
                <span className="text-xs font-mono font-bold text-zinc-900 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-md">
                  Fit Score: {Math.round(ranked!.overall_fit_score * 100)}%
                </span>
              )}
            </div>

            <h2 className="text-xl sm:text-2xl font-bold text-zinc-900 dark:text-zinc-100 tracking-tight leading-snug">
              {opp.title}
            </h2>

            <div className="flex items-center gap-3 text-xs text-zinc-600 dark:text-zinc-400 flex-wrap pt-1">
              <div className="flex items-center gap-1 font-medium text-zinc-900 dark:text-zinc-200">
                <Building2 className="w-3.5 h-3.5 text-zinc-500" />
                <span>{opp.company_name}</span>
                {opp.company_domain_verified && (
                  <span className="text-[10px] text-teal-600 dark:text-teal-400 font-mono">
                    (Verified Employer)
                  </span>
                )}
              </div>

              <span>•</span>

              <div className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                <span>
                  {opp.eligibility_rules.location_city_country.length > 0
                    ? opp.eligibility_rules.location_city_country.join(', ')
                    : 'Remote / Unrestricted'}
                </span>
              </div>

              <span>•</span>

              <div className="flex items-center gap-1 text-zinc-500 font-mono text-[11px]">
                <span>Source:</span>
                <span className="font-semibold text-zinc-700 dark:text-zinc-300 capitalize">{originSource}</span>
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Why Recommended / Executive Summary */}
          {ranked?.recommendation_rationale && (
            <div className="p-4 rounded-xl bg-teal-50/50 dark:bg-teal-950/20 border border-teal-200/60 dark:border-teal-900/40 space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-teal-800 dark:text-teal-300">
                <Sparkles className="w-4 h-4 text-teal-600" />
                <span>Why This Fits Your Profile</span>
              </div>
              <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
                {ranked.recommendation_rationale}
              </p>
            </div>
          )}

          {/* Fit Dimensions Breakdown (if ranked) */}
          {ranked && ranked.dimension_scores && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                Multi-Dimensional Fit Assessment
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
                  <span className="text-[10px] text-zinc-500 font-mono">Market Relevance</span>
                  <ScoreBar score={ranked.dimension_scores.MARKET_RELEVANCE?.raw_score ?? 0} label="Relevance" />
                </div>
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
                  <span className="text-[10px] text-zinc-500 font-mono">Skill Alignment</span>
                  <ScoreBar score={ranked.dimension_scores.SKILL_ALIGNMENT?.raw_score ?? 0} label="Skills" />
                </div>
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
                  <span className="text-[10px] text-zinc-500 font-mono">Qualification Fit</span>
                  <ScoreBar score={ranked.dimension_scores.QUALIFICATION_FIT?.raw_score ?? 0} label="Quals" />
                </div>
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
                  <span className="text-[10px] text-zinc-500 font-mono">Career Alignment</span>
                  <ScoreBar score={ranked.dimension_scores.CAREER_ALIGNMENT?.raw_score ?? 0} label="Trajectory" />
                </div>
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
                  <span className="text-[10px] text-zinc-500 font-mono">Growth Potential</span>
                  <ScoreBar score={ranked.dimension_scores.GROWTH_POTENTIAL?.raw_score ?? 0} label="Growth" />
                </div>
                <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/60 dark:border-zinc-700/60 space-y-1">
                  <span className="text-[10px] text-zinc-500 font-mono">Preference Fit</span>
                  <ScoreBar score={ranked.dimension_scores.PREFERENCE_FIT?.raw_score ?? 0} label="Preferences" />
                </div>
              </div>
            </div>
          )}

          {/* Experience & Seniority Grounding */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-zinc-500" />
              <span>Experience & Seniority Requirement</span>
            </h3>
            <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/70 text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
              {expDescription}
            </div>
          </div>

          {/* Requirements Analysis */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
              Requirements Analysis
            </h3>

            {/* Demonstrated Matches */}
            {demonstratedMatches.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Demonstrated Competencies ({demonstratedMatches.length})
                </span>
                <div className="flex flex-wrap gap-2">
                  {demonstratedMatches.map((req) => (
                    <span
                      key={req.canonical_skill_id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs font-medium text-emerald-800 dark:text-emerald-300"
                    >
                      <span>{req.skill_name}</span>
                      <span className="text-[10px] opacity-75 font-mono">Matched</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Not Demonstrated */}
            {notDemonstrated.length > 0 && (
              <div className="space-y-2 pt-1">
                <span className="text-xs font-medium text-amber-700 dark:text-amber-400 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Not Yet Evidenced on Profile ({notDemonstrated.length})
                </span>
                <p className="text-[11px] text-zinc-500 italic">
                  Note: Missing profile evidence is capability unevidenced, not proof that you lack the skill.
                </p>
                <div className="flex flex-wrap gap-2">
                  {notDemonstrated.map((req) => (
                    <span
                      key={req.canonical_skill_id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-xs font-medium text-amber-800 dark:text-amber-300"
                    >
                      <span>{req.skill_name}</span>
                      <span className="text-[10px] opacity-75 font-mono">Needs Evidence</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Preferred / Nice-to-have Skills */}
            {preferredSkills.length > 0 && (
              <div className="space-y-2 pt-1">
                <span className="text-xs font-medium text-blue-700 dark:text-blue-400 flex items-center gap-1">
                  <HelpCircle className="w-3.5 h-3.5" />
                  Preferred / Advantageous Skills ({preferredSkills.length})
                </span>
                <div className="flex flex-wrap gap-2">
                  {preferredSkills.map((req) => (
                    <span
                      key={req.canonical_skill_id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-xs font-medium text-blue-800 dark:text-blue-300"
                    >
                      <span>{req.skill_name}</span>
                      <span className="text-[10px] opacity-75 font-mono">Preferred</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sanitized Job Description */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
              Job Description Summary
            </h3>
            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed max-h-56 overflow-y-auto whitespace-pre-wrap font-sans">
              {opp.sanitized_summary}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 px-6 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 flex items-center justify-between gap-4">
          <div className="text-[11px] font-mono text-zinc-500 truncate">
            ID: <span className="font-semibold">{opp.opportunity_id}</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-medium text-zinc-700 dark:text-zinc-300 transition-colors"
            >
              Close
            </button>

            <a
              href={opp.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <span>Apply on {originSource}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import {
  CandidateCareerGapAnalysisResponse,
  OpportunityExplanation,
  GapStatus,
} from '@/types/domain';
import {
  getLatestExplanations,
  runCareerGapAnalysis,
  getOpportunityExplanation,
} from '@/lib/api';

// Sample Candidate Profiles for Interactive Demonstration
const SAMPLE_CANDIDATES: Record<string, { label: string; user_id: string; description: string }> = {
  maya: {
    label: 'Maya Chen — Junior Backend Engineer (US)',
    user_id: 'maya-chen-junior',
    description: '18 mo. exp, US Citizen, BS in CS. Verified skills in Python (8.5), PostgreSQL (7.5); emerging in Docker (4.0). Target: Backend Software Engineer.',
  },
  alex: {
    label: 'Alex Rivera — Full Stack Engineer (US)',
    user_id: 'alex-rivera-fullstack',
    description: '4 years exp. Verified in TypeScript (8.5), React (8.0), Node.js (7.5); lacks Go / Kubernetes evidence. Target: Full Stack Developer.',
  },
};

export function CareerExplanationAndGapAnalysis() {
  const [selectedCandidateKey, setSelectedCandidateKey] = useState<string>('maya');
  const [activeTab, setActiveTab] = useState<'explanations' | 'gap_analysis'>('explanations');
  const [useLlm, setUseLlm] = useState<boolean>(true);

  // Explanation State
  const [explanations, setExplanations] = useState<OpportunityExplanation[]>([]);
  const [selectedExpl, setSelectedExpl] = useState<OpportunityExplanation | null>(null);
  const [loadingExpl, setLoadingExpl] = useState<boolean>(false);
  const [explError, setExplError] = useState<string | null>(null);

  // Gap Analysis State
  const [gapReport, setGapReport] = useState<CandidateCareerGapAnalysisResponse | null>(null);
  const [loadingGaps, setLoadingGaps] = useState<boolean>(false);
  const [gapError, setGapError] = useState<string | null>(null);
  const [gapFilter, setGapFilter] = useState<string>('ALL');

  // Expanded Citation IDs in UI
  const [expandedCitationKeys, setExpandedCitationKeys] = useState<Record<string, boolean>>({});

  const toggleCitation = (key: string) => {
    setExpandedCitationKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const candidate = SAMPLE_CANDIDATES[selectedCandidateKey];

  // Load explanations on candidate or LLM mode switch
  useEffect(() => {
    async function loadExplanations() {
      setLoadingExpl(true);
      setExplError(null);
      try {
        const data = await getLatestExplanations(candidate.user_id, 5, useLlm);
        setExplanations(data);
        if (data.length > 0) {
          setSelectedExpl(data[0]);
        } else {
          setSelectedExpl(null);
        }
      } catch (err: unknown) {
        // If candidate has no saved ranking yet in sqlite, we provide synthetic fallback demo
        setExplError(
          err instanceof Error
            ? err.message
            : 'No saved ranking evaluations found. Run Milestone 9 Ranking first or view demonstration mode.'
        );
        setExplanations([]);
        setSelectedExpl(null);
      } finally {
        setLoadingExpl(false);
      }
    }

    if (activeTab === 'explanations') {
      loadExplanations();
    }
  }, [candidate.user_id, useLlm, activeTab]);

  // Load gap analysis on demand or tab switch
  useEffect(() => {
    async function loadGaps() {
      setLoadingGaps(true);
      setGapError(null);
      try {
        const report = await runCareerGapAnalysis(candidate.user_id, undefined, true);
        setGapReport(report);
      } catch (err: unknown) {
        setGapError(
          err instanceof Error
            ? err.message
            : 'Could not load gap analysis for candidate.'
        );
        setGapReport(null);
      } finally {
        setLoadingGaps(false);
      }
    }

    if (activeTab === 'gap_analysis') {
      loadGaps();
    }
  }, [candidate.user_id, activeTab]);

  return (
    <div className="bg-white rounded-2xl border border-zinc-200 shadow-sm overflow-hidden text-zinc-900">
      {/* Header Banner */}
      <div className="border-b border-zinc-200 bg-zinc-50/70 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-emerald-100 text-emerald-800 border border-emerald-200">
                Milestone 11
              </span>
              <h3 className="text-lg font-bold text-zinc-900">
                Evidence-Grounded Explanations & Candidate Career Gap Analysis
              </h3>
            </div>
            <p className="text-xs text-zinc-500 mt-1 max-w-2xl">
              Transparent, citation-backed recommendation rationales with expandable evidence records,
              three-state gap categorization, and stage-proportional learning actions without false guarantees.
            </p>
          </div>

          {/* Controls: Candidate Selector & LLM Mode Toggle */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-col items-end">
              <label htmlFor="candidate-select" className="text-[10px] font-semibold uppercase text-zinc-400">
                Candidate Profile
              </label>
              <select
                id="candidate-select"
                value={selectedCandidateKey}
                onChange={(e) => setSelectedCandidateKey(e.target.value)}
                className="text-xs font-medium rounded-lg border border-zinc-300 bg-white px-2.5 py-1.5 text-zinc-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {Object.entries(SAMPLE_CANDIDATES).map(([key, item]) => (
                  <option key={key} value={key}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col items-end">
              <label className="text-[10px] font-semibold uppercase text-zinc-400">
                AI Text Polisher
              </label>
              <button
                type="button"
                onClick={() => setUseLlm(!useLlm)}
                className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition-colors ${
                  useLlm
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                    : 'bg-zinc-100 border-zinc-300 text-zinc-600'
                }`}
              >
                {useLlm ? 'Structured LLM Polished' : 'Pure Deterministic Factual'}
              </button>
            </div>
          </div>
        </div>

        {/* Candidate Context Pill */}
        <div className="mt-3 p-2.5 rounded-lg bg-zinc-100/80 border border-zinc-200/80 text-[11px] text-zinc-600 flex items-center justify-between">
          <span>{candidate.description}</span>
          <span className="font-mono text-zinc-400 text-[10px]">ID: {candidate.user_id}</span>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="flex border-b border-zinc-200 bg-zinc-50/40 text-xs font-semibold px-6">
        <button
          type="button"
          onClick={() => setActiveTab('explanations')}
          className={`py-3 px-4 border-b-2 transition-colors ${
            activeTab === 'explanations'
              ? 'border-emerald-600 text-emerald-800 font-bold bg-white'
              : 'border-transparent text-zinc-500 hover:text-zinc-800'
          }`}
        >
          Recommendation Explanations & Evidence Citations
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('gap_analysis')}
          className={`py-3 px-4 border-b-2 transition-colors ${
            activeTab === 'gap_analysis'
              ? 'border-emerald-600 text-emerald-800 font-bold bg-white'
              : 'border-transparent text-zinc-500 hover:text-zinc-800'
          }`}
        >
          Career Gap Analysis & Actionable Learning Suggestions
        </button>
      </div>

      {/* Main Content Area */}
      <div className="p-6">
        {/* ========================================================================= */}
        {/* TAB 1: RECOMMENDATION EXPLANATIONS                                        */}
        {/* ========================================================================= */}
        {activeTab === 'explanations' && (
          <div className="space-y-6">
            {loadingExpl && (
              <div className="py-12 text-center text-xs text-zinc-500 flex flex-col items-center gap-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600"></div>
                <span>Generating evidence-grounded explanations...</span>
              </div>
            )}

            {explError && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 space-y-2">
                <div className="font-bold flex items-center gap-1.5">
                  <span>ℹ️ Notice:</span>
                  <span>{explError}</span>
                </div>
                <p className="text-[11px] text-amber-700">
                  Tip: Use the button below to generate an on-demand explanation for this candidate using the live backend.
                </p>
                <button
                  type="button"
                  onClick={async () => {
                    setLoadingExpl(true);
                    setExplError(null);
                    try {
                      const sampleOppId = 'opp-b-1'; // standard sample id from ranking
                      const expl = await getOpportunityExplanation(candidate.user_id, sampleOppId, useLlm);
                      setExplanations([expl]);
                      setSelectedExpl(expl);
                    } catch (e: unknown) {
                      setExplError(e instanceof Error ? e.message : 'Evaluation error');
                    } finally {
                      setLoadingExpl(false);
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-medium text-xs shadow-sm transition-colors"
                >
                  Generate On-Demand Test Opportunity Explanation
                </button>
              </div>
            )}

            {!loadingExpl && explanations.length > 0 && selectedExpl && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Column: Recommendations List */}
                <div className="lg:col-span-4 space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
                    Recommendations ({explanations.length})
                  </span>
                  <div className="space-y-2">
                    {explanations.map((expl) => {
                      const isSelected = selectedExpl.opportunity_id === expl.opportunity_id;
                      return (
                        <button
                          key={expl.opportunity_id}
                          type="button"
                          onClick={() => setSelectedExpl(expl)}
                          className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                            isSelected
                              ? 'border-emerald-500 bg-emerald-50/40 shadow-sm ring-1 ring-emerald-500'
                              : 'border-zinc-200 hover:border-zinc-300 bg-white'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="text-xs font-bold text-zinc-900 line-clamp-1">
                                #{expl.rank ?? 1} {expl.title}
                              </div>
                              <div className="text-[11px] text-zinc-500">{expl.company_name}</div>
                            </div>
                            <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-bold bg-emerald-100 text-emerald-800">
                              {Math.round(expl.overall_fit_score * 100)}%
                            </span>
                          </div>

                          <div className="mt-2 flex items-center gap-2 text-[10px]">
                            <span className="text-emerald-700 font-medium">
                              {expl.matched_requirements.length} Verified Skills
                            </span>
                            <span className="text-zinc-300">•</span>
                            <span className="text-amber-700 font-medium">
                              {expl.skill_gaps.length} Gaps
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Right Column: Grounded Explanation Details */}
                <div className="lg:col-span-8 space-y-5">
                  {/* Explanation Header Card */}
                  <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-bold text-zinc-900">
                          Why This Opportunity Matches #{selectedExpl.rank ?? 1}
                        </div>
                        <div className="text-xs text-zinc-600">
                          {selectedExpl.title} at {selectedExpl.company_name}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {selectedExpl.is_llm_polished ? (
                          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wide uppercase bg-purple-100 text-purple-800 border border-purple-200">
                            ✨ AI Polished Prose
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wide uppercase bg-zinc-200 text-zinc-700 border border-zinc-300">
                            🛡️ Deterministic Factual
                          </span>
                        )}
                        {selectedExpl.fallback_used && (
                          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wide uppercase bg-amber-100 text-amber-800 border border-amber-200">
                            Safe Fallback
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-zinc-700 leading-relaxed font-sans bg-white p-3 rounded-lg border border-zinc-200">
                      {selectedExpl.why_matches_summary}
                    </p>

                    {/* Top Driving Dimensions */}
                    {selectedExpl.top_driving_dimensions.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                        <span className="text-zinc-400 font-semibold uppercase text-[10px] mr-1">
                          Key Fit Drivers:
                        </span>
                        {selectedExpl.top_driving_dimensions.map((dim, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 font-medium"
                          >
                            {dim}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Section 1: Verified Matched Requirements with Expandable Citations */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
                        <span>✓ Verified Matched Requirements</span>
                        <span className="text-zinc-400 font-normal">
                          ({selectedExpl.matched_requirements.length})
                        </span>
                      </span>
                      <span className="text-[10px] text-zinc-400">Click to expand provenance citations</span>
                    </div>

                    <div className="space-y-2">
                      {selectedExpl.matched_requirements.map((req) => {
                        const citeKey = `matched-${req.canonical_skill_id}`;
                        const isExpanded = !!expandedCitationKeys[citeKey];
                        return (
                          <div
                            key={req.canonical_skill_id}
                            className="p-3 rounded-xl border border-emerald-200/70 bg-emerald-50/20 text-xs space-y-2"
                          >
                            <div
                              onClick={() => toggleCitation(citeKey)}
                              className="flex items-center justify-between cursor-pointer select-none"
                            >
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-zinc-900">{req.skill_name}</span>
                                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-100 text-emerald-800">
                                  Prof: {req.candidate_proficiency?.toFixed(1)}/10
                                </span>
                                {req.is_mandatory && (
                                  <span className="text-[9px] font-bold uppercase tracking-wider text-rose-600 bg-rose-50 border border-rose-200 px-1.5 py-0.5 rounded">
                                    Mandatory
                                  </span>
                                )}
                              </div>
                              <span className="text-[11px] text-emerald-700 font-medium">
                                {isExpanded ? 'Hide Evidence ▲' : `${req.citations.length} Citations ▼`}
                              </span>
                            </div>

                            <p className="text-[11px] text-zinc-600">{req.status_rationale}</p>

                            {/* Expandable Citations */}
                            {isExpanded && req.citations.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-emerald-100 space-y-2">
                                <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wide">
                                  Backing Evidence Records (Provenance):
                                </span>
                                {req.citations.map((c) => (
                                  <div
                                    key={c.evidence_id}
                                    className="p-2.5 rounded-lg bg-white border border-emerald-200/80 text-[11px] space-y-1"
                                  >
                                    <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400">
                                      <span>Source: {c.source_type}</span>
                                      <span className="text-emerald-700 font-bold">
                                        Weight: {Math.round(c.verifiability_weight * 100)}%
                                      </span>
                                    </div>
                                    <p className="font-mono text-zinc-800 bg-zinc-50 p-1.5 rounded border border-zinc-100 text-[11px]">
                                      &quot;{c.snippet}&quot;
                                    </p>
                                    {c.source_uri && (
                                      <div className="text-[10px] text-zinc-400 font-mono">
                                        URI: {c.source_uri}
                                      </div>
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

                  {/* Section 2: Partially Supported Requirements */}
                  {selectedExpl.partially_supported_requirements.length > 0 && (
                    <div className="space-y-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
                        <span>⚠️ Partially Supported Requirements (Proficiency or Confidence Gap)</span>
                        <span className="text-zinc-400 font-normal">
                          ({selectedExpl.partially_supported_requirements.length})
                        </span>
                      </span>

                      <div className="space-y-2">
                        {selectedExpl.partially_supported_requirements.map((req) => (
                          <div
                            key={req.canonical_skill_id}
                            className="p-3 rounded-xl border border-amber-200 bg-amber-50/20 text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between font-bold text-zinc-900">
                              <span>{req.skill_name}</span>
                              <span className="text-[10px] font-mono text-amber-800">
                                Candidate: {req.candidate_proficiency?.toFixed(1)}/10 • Required: {req.expected_proficiency?.toFixed(1)}/10
                              </span>
                            </div>
                            <p className="text-[11px] text-zinc-600">{req.status_rationale}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Section 3: Skill Gaps (Unevidenced in Profile) */}
                  {selectedExpl.skill_gaps.length > 0 && (
                    <div className="space-y-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-zinc-600 flex items-center gap-1.5">
                        <span>○ Unevidenced Skill Gaps</span>
                        <span className="text-zinc-400 font-normal">
                          ({selectedExpl.skill_gaps.length})
                        </span>
                      </span>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {selectedExpl.skill_gaps.map((req) => (
                          <div
                            key={req.canonical_skill_id}
                            className="p-2.5 rounded-lg border border-zinc-200 bg-zinc-50/60 text-zinc-700 space-y-1"
                          >
                            <div className="font-semibold text-zinc-800 flex items-center justify-between">
                              <span>{req.skill_name}</span>
                              <span className="text-[10px] font-mono text-zinc-400">
                                {req.is_mandatory ? 'Required' : 'Preferred'}
                              </span>
                            </div>
                            <p className="text-[10px] text-zinc-500 leading-normal">
                              No corroborating evidence in profile. Note: not proof of inability.
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Section 4: Eligibility & Limitations */}
                  <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50/50 text-xs space-y-3">
                    <div>
                      <span className="font-bold text-zinc-800 uppercase text-[10px] tracking-wide block mb-1">
                        Deterministic Eligibility & Caveats
                      </span>
                      <p className="text-[11px] text-zinc-600">{selectedExpl.eligibility_explanation}</p>
                    </div>

                    <div>
                      <span className="font-bold text-zinc-800 uppercase text-[10px] tracking-wide block mb-1">
                        Career Relevance & Growth Potential
                      </span>
                      <p className="text-[11px] text-zinc-600">{selectedExpl.career_relevance}</p>
                      <p className="text-[11px] text-zinc-600 mt-1">{selectedExpl.growth_opportunity}</p>
                    </div>

                    {selectedExpl.limitations_and_uncertainties.length > 0 && (
                      <div className="pt-2 border-t border-zinc-200/80">
                        <span className="font-bold text-zinc-700 uppercase text-[10px] tracking-wide block mb-1">
                          Material Caveats & Missing Listing Info:
                        </span>
                        <ul className="list-disc list-inside text-[11px] text-zinc-500 space-y-0.5">
                          {selectedExpl.limitations_and_uncertainties.map((lim, idx) => (
                            <li key={idx}>{lim}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: CAREER GAP ANALYSIS & SUGGESTIONS                                  */}
        {/* ========================================================================= */}
        {activeTab === 'gap_analysis' && (
          <div className="space-y-6">
            {loadingGaps && (
              <div className="py-12 text-center text-xs text-zinc-500 flex flex-col items-center gap-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600"></div>
                <span>Executing candidate career gap analysis and action planning...</span>
              </div>
            )}

            {gapError && (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800">
                <span className="font-bold">Error:</span> {gapError}
              </div>
            )}

            {!loadingGaps && gapReport && (
              <div className="space-y-6">
                {/* Gap Report Header Banner */}
                <div className="p-5 rounded-xl border border-zinc-200 bg-zinc-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                      Gap Analysis Audit
                    </span>
                    <h4 className="text-sm font-bold text-zinc-900 mt-0.5">
                      Target Roles: {gapReport.target_roles_analyzed.join(', ')}
                    </h4>
                    <p className="text-xs text-zinc-500 mt-1">
                      Evaluated across {gapReport.total_opportunities_analyzed} active opportunities; identified {gapReport.total_gaps_identified} actionable skills.
                    </p>
                  </div>

                  {/* Filter Pills */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="text-[10px] font-semibold uppercase text-zinc-400 mr-1">Filter:</span>
                    {['ALL', 'NOT_DEMONSTRATED', 'PROFICIENCY_UNCERTAIN', 'REQUIREMENT_UNCLEAR'].map((f) => (
                      <button
                        key={f}
                        type="button"
                        onClick={() => setGapFilter(f)}
                        className={`px-2.5 py-1 rounded-md text-[10px] font-bold tracking-wide transition-colors ${
                          gapFilter === f
                            ? 'bg-emerald-600 text-white shadow-xs'
                            : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200'
                        }`}
                      >
                        {f.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Prioritized Gaps List */}
                <div className="space-y-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-zinc-600">
                    Prioritized Career Gaps ({gapReport.prioritized_gaps.length})
                  </span>

                  <div className="space-y-3">
                    {gapReport.prioritized_gaps
                      .filter((g) => gapFilter === 'ALL' || g.gap_status === gapFilter)
                      .map((gap) => {
                        const statusColors: Record<GapStatus, { bg: string; text: string; label: string }> = {
                          NOT_DEMONSTRATED: {
                            bg: 'bg-zinc-100 border-zinc-300',
                            text: 'text-zinc-700',
                            label: 'Not Demonstrated',
                          },
                          PROFICIENCY_UNCERTAIN: {
                            bg: 'bg-amber-50 border-amber-300',
                            text: 'text-amber-800',
                            label: 'Proficiency Uncertain',
                          },
                          REQUIREMENT_UNCLEAR: {
                            bg: 'bg-blue-50 border-blue-300',
                            text: 'text-blue-800',
                            label: 'Requirement Unclear',
                          },
                        };

                        const impColors: Record<string, string> = {
                          CRITICAL: 'bg-rose-100 text-rose-800 border-rose-200',
                          HIGH: 'bg-amber-100 text-amber-800 border-amber-200',
                          MEDIUM: 'bg-zinc-100 text-zinc-700 border-zinc-200',
                          NICE_TO_HAVE: 'bg-zinc-50 text-zinc-500 border-zinc-200',
                        };

                        const sc = statusColors[gap.gap_status];

                        return (
                          <div
                            key={gap.canonical_skill_id}
                            className="p-4 rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 transition-all space-y-2 text-xs"
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-sm text-zinc-900">{gap.skill_name}</span>
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${sc.bg} ${sc.text}`}
                                >
                                  {sc.label}
                                </span>
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border ${impColors[gap.importance]}`}
                                >
                                  {gap.importance}
                                </span>
                              </div>

                              <span className="text-[11px] font-mono text-zinc-400">
                                {gap.relevant_target_roles.join(', ') || 'General Technical Domain'}
                              </span>
                            </div>

                            <p className="text-[11px] text-zinc-600">{gap.why_it_matters}</p>

                            <div className="p-2.5 rounded-lg bg-zinc-50 border border-zinc-200 text-[11px] space-y-1">
                              <span className="font-semibold text-emerald-800 uppercase text-[10px] tracking-wide block">
                                Recommended Next Step:
                              </span>
                              <p className="text-zinc-700">{gap.suggested_action}</p>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* Stage-Proportional Improvement Suggestions */}
                <div className="space-y-4 pt-4 border-t border-zinc-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">
                        Actionable Portfolio & Learning Projects
                      </span>
                      <p className="text-[11px] text-zinc-500">
                        Realistic next steps calibrated to your career stage without false employment promises.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {gapReport.suggested_improvements.map((sug) => (
                      <div
                        key={sug.suggestion_id}
                        className="p-4 rounded-xl border border-emerald-200/80 bg-emerald-50/20 text-xs space-y-3 flex flex-col justify-between"
                      >
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-emerald-100 text-emerald-800">
                              {sug.action_type.replace('_', ' ')}
                            </span>
                            <span className="text-[10px] font-mono text-zinc-500">
                              Stage: {sug.proportional_stage}
                            </span>
                          </div>

                          <h5 className="font-bold text-zinc-900 text-sm">{sug.title}</h5>
                          <p className="text-[11px] text-zinc-600 leading-relaxed">{sug.description}</p>

                          <div className="flex flex-wrap items-center gap-1 text-[10px]">
                            <span className="text-zinc-400 font-semibold uppercase mr-1">Targeted Skills:</span>
                            {sug.targeted_gaps.map((tg) => (
                              <span
                                key={tg}
                                className="px-2 py-0.5 rounded-full bg-white border border-emerald-200 text-emerald-700 font-medium"
                              >
                                {tg}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Ethical Disclaimer */}
                        <div className="pt-2 border-t border-emerald-100 text-[10px] text-zinc-500 italic">
                          ⚖️ {sug.disclaimer}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

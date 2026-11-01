'use client';

import React, { useState } from 'react';
import {
  UserCheck,
  ShieldCheck,
  FileText,
  PlusCircle,
  GraduationCap,
  Compass,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  CandidateProfilingRequest,
} from '@/types/domain';
import { extractCandidateProfile } from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { EvidenceCard } from '@/components/ui/EvidenceCard';
import { WorkspaceTab } from '@/components/layout/Header';

interface ProfileWorkspaceProps {
  candidateProfile: CandidateCareerProfile;
  candidateName: string;
  onNavigateTab: (tab: WorkspaceTab) => void;
  onProfileUpdated?: (updated: CandidateCareerProfile) => void;
}

export function ProfileWorkspace({
  candidateProfile,
  candidateName,
  onNavigateTab,
  onProfileUpdated,
}: ProfileWorkspaceProps) {
  const [expandedSkillId, setExpandedSkillId] = useState<string | null>(null);
  const [showExtractModal, setShowExtractModal] = useState<boolean>(false);
  const [rawExtractText, setRawExtractText] = useState<string>('');
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractMessage, setExtractMessage] = useState<string | null>(null);

  const toggleSkill = (skillId: string) => {
    setExpandedSkillId(expandedSkillId === skillId ? null : skillId);
  };

  async function handleSimulateExtraction() {
    if (!rawExtractText.trim()) return;
    setIsExtracting(true);
    setExtractMessage(null);
    try {
      const req: CandidateProfilingRequest = {
        resume_text: rawExtractText,
        user_id: candidateProfile.user_id,
        save_to_repository: false,
      };
      const res = await extractCandidateProfile(req);
      if (res.extracted_profile && onProfileUpdated) {
        onProfileUpdated(res.extracted_profile);
      }
      const skillCount = res.extracted_profile?.assessed_skills?.length ?? (res.stated_skills_count + res.inferred_skills_count);
      setExtractMessage(`Successfully analyzed material. Extracted ${skillCount} skills with provenance.`);
      setRawExtractText('');
    } catch (err: unknown) {
      setExtractMessage(err instanceof Error ? err.message : 'Profiling service extraction failed');
    } finally {
      setIsExtracting(false);
    }
  }

  const totalEvidenceCount = candidateProfile.assessed_skills.reduce(
    (acc, s) => acc + s.evidence_records.length,
    0
  );

  return (
    <div className="space-y-8">
      {/* 1. Header & Metric Summary */}
      <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-md bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <UserCheck className="w-4 h-4" />
              </span>
              <h2 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Profile & Evidence Grounding Hub
              </h2>
            </div>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Every skill score in JobFalcon is anchored to inspectable, verifiable evidence records from
              resumes, projects, and code repositories.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowExtractModal(!showExtractModal)}
              className="px-3.5 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-semibold text-zinc-800 dark:text-zinc-200 transition-colors flex items-center gap-1.5"
            >
              <PlusCircle className="w-3.5 h-3.5 text-teal-600" />
              <span>Add Proof Material</span>
            </button>

            <button
              onClick={() => onNavigateTab('discover')}
              className="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Compass className="w-3.5 h-3.5 text-teal-400 dark:text-teal-600" />
              <span>Discover Opportunities</span>
            </button>
          </div>
        </div>

        {/* Essential Principle Callout */}
        <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-700/60 text-xs flex items-center gap-3">
          <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0" />
          <p className="text-zinc-700 dark:text-zinc-300">
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">Core Principle:</span> Missing evidence does not indicate a lack of ability. JobFalcon distinguishes unverified capabilities from demonstrated ones to prevent speculative hallucination.
          </p>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Candidate User</span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate block">{candidateName}</span>
            <span className="text-[10px] text-zinc-500 block truncate">({candidateProfile.user_id})</span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Profile Confidence</span>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {(candidateProfile.overall_profile_confidence * 100).toFixed(1)}%
            </span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Assessed Skills</span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">{candidateProfile.assessed_skills.length}</span>
          </div>

          <div className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-700/50">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Provenance Records</span>
            <span className="text-sm font-bold text-teal-600 dark:text-teal-400">{totalEvidenceCount}</span>
          </div>
        </div>
      </div>

      {/* 2. Optional Material Ingestion Modal */}
      {showExtractModal && (
        <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <FileText className="w-4 h-4 text-teal-600" />
              Ingest Experience or Project Material
            </h3>
            <button
              onClick={() => setShowExtractModal(false)}
              className="text-xs text-zinc-400 hover:text-zinc-600 font-mono"
            >
              Cancel
            </button>
          </div>

          <p className="text-xs text-zinc-500">
            Paste experience summaries, technical project write-ups, or repository README content. The profiling
            engine will extract canonical ESCO/O*NET competencies with verbatim evidence grounding.
          </p>

          <textarea
            value={rawExtractText}
            onChange={(e) => setRawExtractText(e.target.value)}
            rows={4}
            placeholder="e.g., Designed and implemented high-performance Redis caching layer with pub/sub architecture in Python..."
            className="w-full p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
          />

          <div className="flex items-center justify-between">
            {extractMessage && (
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                {extractMessage}
              </span>
            )}
            <button
              onClick={handleSimulateExtraction}
              disabled={isExtracting || !rawExtractText.trim()}
              className="ml-auto px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50"
            >
              {isExtracting ? 'Analyzing...' : 'Extract & Ground Evidence'}
            </button>
          </div>
        </div>
      )}

      {/* 3. Assessed Skills & Grounding Provenance */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
            Demonstrated Competencies ({candidateProfile.assessed_skills.length})
          </h3>
          <span className="text-xs text-zinc-500 font-mono">
            Click any skill to inspect verifiability snippets
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {candidateProfile.assessed_skills.map((skill) => {
            const isExpanded = expandedSkillId === skill.canonical_skill_id;
            const profPercent = (skill.proficiency_score / 10) * 100;

            return (
              <div
                key={skill.canonical_skill_id}
                className="rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-xs"
              >
                <div
                  onClick={() => toggleSkill(skill.canonical_skill_id)}
                  className="p-4 flex items-center justify-between gap-4 cursor-pointer hover:bg-zinc-50/70 dark:hover:bg-zinc-800/40 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                        {skill.skill_name}
                      </span>
                      <Badge variant="outline" size="sm" mono>
                        {skill.canonical_skill_id}
                      </Badge>
                      <Badge variant="verified" size="sm" mono>
                        {skill.evidence_records.length} record(s)
                      </Badge>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-zinc-500 font-mono">
                      <span>Proficiency: {skill.proficiency_score.toFixed(1)}/10</span>
                      <span>•</span>
                      <span>Confidence: {(skill.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {/* Proficiency Mini Bar */}
                    <div className="w-28 hidden sm:block space-y-1">
                      <div className="h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal-500 rounded-full"
                          style={{ width: `${profPercent}%` }}
                        />
                      </div>
                    </div>

                    <button
                      className="p-1 text-zinc-400 hover:text-zinc-600 transition-colors"
                      aria-label="Toggle details"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 bg-zinc-50/60 dark:bg-zinc-800/30 border-t border-zinc-100 dark:border-zinc-800/80 space-y-3">
                    <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider block">
                      Underlying Evidence Records ({skill.evidence_records.length})
                    </span>

                    <div className="grid grid-cols-1 gap-2.5">
                      {skill.evidence_records.map((ev) => (
                        <EvidenceCard
                          key={ev.evidence_id}
                          extractedSnippet={ev.extracted_snippet}
                          sourceType={ev.source_type}
                          sourceUri={ev.source_uri}
                          verifiabilityWeight={ev.verifiability_weight}
                          observedAt={ev.observed_at}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Hard Constraints & Deterministic Eligibility Profile */}
      <div className="p-6 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-teal-600" />
              Hard Eligibility Boundaries
            </h3>
            <p className="text-xs text-zinc-500">
              Evaluated strictly in pure Python code with zero LLM bypass.
            </p>
          </div>
          <Badge variant="verified" size="sm" mono>
            DETERMINISTIC PRIMACY
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/60 space-y-1">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">
              Work Authorization
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
              {candidateProfile.eligibility_constraints.authorized_country_codes.join(', ')} Authorized
            </span>
            <span className="text-[11px] text-zinc-500">
              Visa sponsorship required:{' '}
              {candidateProfile.eligibility_constraints.requires_visa_sponsorship ? 'Yes' : 'No'}
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/60 space-y-1">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">
              Academic Credentials
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
              Highest Degree: {candidateProfile.eligibility_constraints.highest_degree_level}
            </span>
            <span className="text-[11px] text-zinc-500">
              Active student: {candidateProfile.eligibility_constraints.is_currently_enrolled_student ? 'Yes' : 'No'}
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/60 space-y-1">
            <span className="text-[10px] text-zinc-400 font-mono uppercase tracking-wider block">
              Workplace Flexibility
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block">
              Modes: {candidateProfile.eligibility_constraints.allowed_work_modes.join(', ')}
            </span>
            <span className="text-[11px] text-zinc-500 truncate block">
              Locations: {candidateProfile.eligibility_constraints.preferred_locations.join(', ')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

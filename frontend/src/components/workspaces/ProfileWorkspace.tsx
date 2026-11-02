'use client';

import React, { useState, useRef } from 'react';
import {
  User,
  GraduationCap,
  ChevronDown,
  ChevronUp,
  Upload,
  RotateCw,
  CheckCircle,
  Sliders,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  CandidateProfilingRequest,
} from '@/types/domain';
import { extractCandidateProfile, parseResumeFile } from '@/lib/api';
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
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractMessage, setExtractMessage] = useState<string | null>(null);
  const [extractError, setExtractError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const toggleSkill = (skillId: string) => {
    setExpandedSkillId(expandedSkillId === skillId ? null : skillId);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFile(file);
    setExtractMessage(null);
    setExtractError(null);
    if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
      try {
        const text = await file.text();
        setRawExtractText(text);
      } catch {
        // Parsed on backend
      }
    }
  };

  async function handleExtractResume() {
    setIsExtracting(true);
    setExtractMessage(null);
    setExtractError(null);

    try {
      let textToExtract = rawExtractText.trim();
      if (uploadedFile && !textToExtract) {
        const parsed = await parseResumeFile(uploadedFile);
        textToExtract = parsed.text;
        setRawExtractText(textToExtract);
      }

      if (!textToExtract) {
        throw new Error('Please select a resume file or paste resume text first.');
      }

      const req: CandidateProfilingRequest = {
        resume_text: textToExtract,
        user_id: candidateProfile.user_id,
        save_to_repository: true,
      };
      const res = await extractCandidateProfile(req);
      if (res.extracted_profile && onProfileUpdated) {
        onProfileUpdated(res.extracted_profile);
      }
      const skillCount =
        res.extracted_profile?.assessed_skills?.length ??
        (res.stated_skills_count + res.inferred_skills_count);
      setExtractMessage(
        `Resume successfully analyzed! Extracted ${skillCount} skills and updated your profile.`
      );
      setUploadedFile(null);
      setRawExtractText('');
    } catch (err: unknown) {
      setExtractError(
        err instanceof Error ? err.message : 'Unable to parse and extract resume information.'
      );
    } finally {
      setIsExtracting(false);
    }
  }

  const totalEvidenceCount = candidateProfile.assessed_skills.reduce(
    (acc, s) => acc + s.evidence_records.length,
    0
  );

  const targetRole = candidateProfile.target_career_paths[0]?.title || 'Software Engineer';
  const expMonths = candidateProfile.eligibility_constraints.total_full_time_experience_months;
  const expDisplay =
    expMonths > 0
      ? `${(expMonths / 12).toFixed(1)} years (${expMonths} mos)`
      : 'Early Career / Not specified';

  return (
    <div className="space-y-6">
      {/* Top Navigation Anchor: Return to Discovery */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => onNavigateTab('discover')}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-2xs"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
          <span>Back to Opportunity Discovery</span>
        </button>

        <button
          onClick={() => setShowExtractModal(!showExtractModal)}
          className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-2xs"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload or Replace Resume</span>
        </button>
      </div>

      {/* 1. Header & Metric Summary */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800/80">
                <User className="w-4 h-4" />
              </span>
              <h2 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Career Profile
              </h2>
            </div>
            <p className="text-xs text-zinc-500 max-w-xl">
              Your profile represents your skills, experience, and career preferences. JobFalcon uses
              these to find opportunities matching your goals.
            </p>
          </div>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Candidate
            </span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate block">
              {candidateName}
            </span>
            <span className="text-[11px] text-zinc-500 truncate block">{targetRole}</span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Profile Strength
            </span>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {(candidateProfile.overall_profile_confidence * 100).toFixed(0)}%
            </span>
            <span className="text-[11px] text-zinc-500 block">Verified coverage</span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Skills on File
            </span>
            <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              {candidateProfile.assessed_skills.length}
            </span>
            <span className="text-[11px] text-zinc-500 block">{totalEvidenceCount} verified evidence excerpts</span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Experience Duration
            </span>
            <span className="text-sm font-bold text-teal-600 dark:text-teal-400 truncate block">
              {expDisplay}
            </span>
            <span className="text-[11px] text-zinc-500 block">Full-time professional</span>
          </div>
        </div>
      </div>

      {/* 2. Resume Upload & Document Analysis Drawer */}
      {showExtractModal && (
        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-teal-200 dark:border-teal-900/60 shadow-md space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Upload className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              Upload or Replace Resume
            </h3>
            <button
              onClick={() => setShowExtractModal(false)}
              className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 font-mono"
            >
              Close
            </button>
          </div>

          <p className="text-xs text-zinc-500">
            Upload your resume (.pdf, .docx, .doc, .txt, .md). JobFalcon parses readable text, extracts
            skills and project evidence, and updates your profile.
          </p>

          {extractError && (
            <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-400">
              {extractError}
            </div>
          )}

          {extractMessage && (
            <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{extractMessage}</span>
            </div>
          )}

          {/* File Picker Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="p-5 border-2 border-dashed border-zinc-300 dark:border-zinc-700 hover:border-teal-500 dark:hover:border-teal-400 rounded-xl bg-zinc-50/50 dark:bg-zinc-800/40 text-center cursor-pointer transition-colors"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,.md"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center gap-1 text-xs text-zinc-600 dark:text-zinc-300">
              <Upload className="w-5 h-5 text-teal-600 dark:text-teal-400 mb-1" />
              <span className="font-semibold">
                {uploadedFile ? uploadedFile.name : 'Click to select a resume file (.pdf, .docx, .txt)'}
              </span>
              <span className="text-[11px] text-zinc-400">
                PDF text, Word documents, Markdown, or plain text supported
              </span>
            </div>
          </div>

          <textarea
            value={rawExtractText}
            onChange={(e) => setRawExtractText(e.target.value)}
            rows={4}
            placeholder="Or paste resume text, project summaries, or experience description directly here..."
            className="w-full p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
          />

          <div className="flex items-center justify-end gap-3">
            <button
              onClick={() => setShowExtractModal(false)}
              className="px-3.5 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              onClick={handleExtractResume}
              disabled={isExtracting || (!rawExtractText.trim() && !uploadedFile)}
              className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 shadow-2xs"
            >
              {isExtracting ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Analyzing Resume...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Analyze & Update Profile</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* 3. Skills & Demonstrated Evidence */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <span>Skills & Demonstrated Evidence</span>
              <span className="text-xs font-normal text-zinc-500">
                ({candidateProfile.assessed_skills.length})
              </span>
            </h3>
            <p className="text-xs text-zinc-500">
              Skills extracted from your resume and projects. Click any skill to view supporting excerpts.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2.5">
          {candidateProfile.assessed_skills.map((skill) => {
            const isExpanded = expandedSkillId === skill.canonical_skill_id;
            const profPercent = (skill.proficiency_score / 10) * 100;

            return (
              <div
                key={skill.canonical_skill_id}
                className="rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-2xs"
              >
                <div
                  onClick={() => toggleSkill(skill.canonical_skill_id)}
                  className="p-3.5 flex items-center justify-between gap-4 cursor-pointer hover:bg-zinc-50/70 dark:hover:bg-zinc-800/40 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">
                        {skill.skill_name}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-teal-50 dark:bg-teal-950/80 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800 font-mono">
                        {skill.proficiency_score.toFixed(1)} / 10.0
                      </span>
                      {skill.evidence_records.length > 0 && (
                        <span className="text-[10px] text-zinc-400 font-mono">
                          {skill.evidence_records.length} evidence snippet{skill.evidence_records.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>

                    {skill.evidence_records[0]?.extracted_snippet && (
                      <p className="text-xs text-zinc-500 line-clamp-1 italic">
                        &ldquo;{skill.evidence_records[0].extracted_snippet}&rdquo;
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {/* Proficiency Mini Bar */}
                    <div className="w-24 hidden sm:block">
                      <div className="h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal-500 rounded-full"
                          style={{ width: `${profPercent}%` }}
                        />
                      </div>
                    </div>

                    <button
                      className="p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors"
                      aria-label="Toggle details"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 bg-zinc-50/60 dark:bg-zinc-800/30 border-t border-zinc-100 dark:border-zinc-800/80 space-y-2.5">
                    <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider block">
                      Supporting Excerpts from Your Materials
                    </span>

                    <div className="grid grid-cols-1 gap-2">
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

      {/* 4. Education & Career Preferences */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Education & Experience */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <GraduationCap className="w-4 h-4 text-teal-600 dark:text-teal-400" />
            Education & Background
          </h3>

          <div className="space-y-2 text-xs">
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 flex items-center justify-between">
              <span className="text-zinc-500">Highest Academic Degree:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {candidateProfile.eligibility_constraints.highest_degree_level}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 flex items-center justify-between">
              <span className="text-zinc-500">Current Student Status:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {candidateProfile.eligibility_constraints.is_currently_enrolled_student
                  ? 'Currently Enrolled'
                  : 'Not Currently Enrolled'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 flex items-center justify-between">
              <span className="text-zinc-500">Full-Time Experience:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {expDisplay}
              </span>
            </div>
          </div>
        </div>

        {/* Career Preferences */}
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-3">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-teal-600 dark:text-teal-400" />
            Career Preferences & Workplace
          </h3>

          <div className="space-y-2 text-xs">
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 flex items-center justify-between">
              <span className="text-zinc-500">Preferred Work Modes:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {candidateProfile.eligibility_constraints.allowed_work_modes.join(', ')}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 flex items-center justify-between">
              <span className="text-zinc-500">Target Locations:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate max-w-[200px]">
                {candidateProfile.eligibility_constraints.preferred_locations.join(', ') || 'Any'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-800 flex items-center justify-between">
              <span className="text-zinc-500">Work Visa Sponsorship:</span>
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {candidateProfile.eligibility_constraints.requires_visa_sponsorship
                  ? 'Required'
                  : 'Not Required'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

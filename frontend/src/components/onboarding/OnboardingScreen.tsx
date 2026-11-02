'use client';

import React, { useState } from 'react';
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  Plus,
  Trash2,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  StructuredProfileCreateRequest,
} from '@/types/domain';
import { createStructuredProfile } from '@/lib/api';

interface OnboardingScreenProps {
  onProfileCreated: (profile: CandidateCareerProfile) => void;
  onExploreDemo?: () => void;
}

export function OnboardingScreen({
  onProfileCreated,
  onExploreDemo,
}: OnboardingScreenProps) {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form State
  // Step 1: Basic Info
  const [displayName, setDisplayName] = useState('');
  const [headline, setHeadline] = useState('');
  const [userId, setUserId] = useState('');
  const [userIdEdited, setUserIdEdited] = useState(false);

  // Step 2: Education & Experience
  const [highestDegree, setHighestDegree] = useState('BACHELORS');
  const [isEnrolledStudent, setIsEnrolledStudent] = useState(false);
  const [expectedGraduationDate, setExpectedGraduationDate] = useState('');
  const [experienceMonths, setExperienceMonths] = useState(0);

  // Step 3: Work Preferences
  const [authorizedCountries] = useState<string[]>(['US']);
  const [visaRequired, setVisaRequired] = useState(false);
  const [allowedCategories, setAllowedCategories] = useState<string[]>(['FULL_TIME_JOB']);
  const [allowedWorkModes, setAllowedWorkModes] = useState<string[]>(['REMOTE', 'HYBRID']);
  const [preferredLocationsStr, setPreferredLocationsStr] = useState('Remote, San Francisco, CA');

  // Step 4: Career Direction & Skills
  const [targetRoleTitle, setTargetRoleTitle] = useState('Software Engineer');
  const [adjacentRoleTitle, setAdjacentRoleTitle] = useState('Backend Engineer');
  const [skills, setSkills] = useState<Array<{ name: string; proficiency: number; evidence: string }>>([
    { name: 'Python', proficiency: 8.0, evidence: 'Built asynchronous web services and database workflows.' },
    { name: 'PostgreSQL', proficiency: 7.5, evidence: 'Relational schema design and query indexing.' },
  ]);
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillProf, setNewSkillProf] = useState(7.0);
  const [newSkillEvidence, setNewSkillEvidence] = useState('');

  // Auto-generate slug from name if not manually edited
  const handleNameChange = (val: string) => {
    setDisplayName(val);
    if (!userIdEdited) {
      const slug = val
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)/g, '');
      setUserId(slug || 'usr-cand-1');
    }
  };

  const addSkill = () => {
    if (!newSkillName.trim()) return;
    setSkills([
      ...skills,
      {
        name: newSkillName.trim(),
        proficiency: newSkillProf,
        evidence: newSkillEvidence.trim() || `Demonstrated competency in ${newSkillName.trim()}.`,
      },
    ]);
    setNewSkillName('');
    setNewSkillProf(7.0);
    setNewSkillEvidence('');
  };

  const removeSkill = (index: number) => {
    setSkills(skills.filter((_, i) => i !== index));
  };

  const toggleCategory = (cat: string) => {
    if (allowedCategories.includes(cat)) {
      if (allowedCategories.length > 1) {
        setAllowedCategories(allowedCategories.filter((c) => c !== cat));
      }
    } else {
      setAllowedCategories([...allowedCategories, cat]);
    }
  };

  const toggleWorkMode = (mode: string) => {
    if (allowedWorkModes.includes(mode)) {
      if (allowedWorkModes.length > 1) {
        setAllowedWorkModes(allowedWorkModes.filter((m) => m !== mode));
      }
    } else {
      setAllowedWorkModes([...allowedWorkModes, mode]);
    }
  };

  const validateStep = (step: number): boolean => {
    setErrorMessage(null);
    if (step === 1) {
      if (!displayName.trim()) {
        setErrorMessage('Please enter your full name.');
        return false;
      }
      if (!userId.trim()) {
        setErrorMessage('Please provide a unique profile identifier.');
        return false;
      }
    }
    if (step === 4) {
      if (!targetRoleTitle.trim()) {
        setErrorMessage('Please enter your primary target career title.');
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((prev) => Math.min(prev + 1, 4));
    }
  };

  const handleBack = () => {
    setErrorMessage(null);
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleSubmit = async () => {
    if (!validateStep(4)) return;
    setIsSubmitting(true);
    setErrorMessage(null);

    const locations = preferredLocationsStr
      .split(',')
      .map((loc) => loc.trim())
      .filter((loc) => loc.length > 0);

    const payload: StructuredProfileCreateRequest = {
      user_id: userId.trim().toLowerCase(),
      display_name: displayName.trim(),
      headline: headline.trim() || `${targetRoleTitle}`,
      highest_degree_level: highestDegree,
      is_currently_enrolled_student: isEnrolledStudent,
      expected_graduation_date: isEnrolledStudent && expectedGraduationDate ? expectedGraduationDate : undefined,
      total_full_time_experience_months: Number(experienceMonths) || 0,
      authorized_country_codes: authorizedCountries,
      requires_visa_sponsorship: visaRequired,
      allowed_opportunity_categories: allowedCategories,
      allowed_work_modes: allowedWorkModes,
      preferred_locations: locations.length > 0 ? locations : ['Remote'],
      target_role_title: targetRoleTitle.trim(),
      target_occupation_code: '15-1252.00',
      adjacent_role_title: adjacentRoleTitle.trim() || undefined,
      adjacent_occupation_code: adjacentRoleTitle.trim() ? '15-1251.00' : undefined,
      initial_skills: skills.map((s) => ({
        skill_name: s.name,
        proficiency_score: s.proficiency,
        evidence_snippet: s.evidence,
      })),
    };

    try {
      const created = await createStructuredProfile(payload);
      onProfileCreated(created);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Failed to create candidate profile. Please verify your fields.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 sm:px-6">
      <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden">
        {/* Onboarding Header */}
        <div className="p-6 sm:p-8 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-50 dark:bg-teal-950/80 text-teal-700 dark:text-teal-400 border border-teal-200/80 dark:border-teal-800">
                <Sparkles className="w-3.5 h-3.5" />
                First-Run Profile Setup
              </span>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                Welcome to JobFalcon
              </h1>
              <p className="text-xs text-zinc-500 max-w-lg">
                Create your local career intelligence profile. Your qualifications, hard constraints, and verifiable
                skills drive 100% deterministic eligibility and ranking with zero LLM score hallucinations.
              </p>
            </div>
          </div>

          {/* Stepper Progress Bar */}
          <div className="grid grid-cols-4 gap-2 mt-6">
            {[
              { num: 1, label: 'Identity' },
              { num: 2, label: 'Credentials' },
              { num: 3, label: 'Preferences' },
              { num: 4, label: 'Target & Skills' },
            ].map((step) => {
              const isPast = step.num < currentStep;
              const isCurrent = step.num === currentStep;
              return (
                <div
                  key={step.num}
                  className={`flex items-center gap-2 p-2 rounded-lg border text-xs transition-colors ${
                    isCurrent
                      ? 'bg-teal-50 dark:bg-teal-950/60 border-teal-300 dark:border-teal-700 text-teal-800 dark:text-teal-300 font-semibold'
                      : isPast
                      ? 'bg-zinc-100 dark:bg-zinc-800/60 border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300'
                      : 'bg-transparent border-transparent text-zinc-400'
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${
                      isPast
                        ? 'bg-teal-600 text-white'
                        : isCurrent
                        ? 'bg-teal-500 text-white ring-2 ring-teal-300 dark:ring-teal-700'
                        : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-500'
                    }`}
                  >
                    {isPast ? <CheckCircle className="w-3.5 h-3.5" /> : step.num}
                  </div>
                  <span className="hidden sm:inline truncate">{step.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Step Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {errorMessage && (
            <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-400">
              {errorMessage}
            </div>
          )}

          {/* STEP 1: Basic Identity */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Full Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="e.g. Alex Rivera"
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Professional Headline / Current Focus
                </label>
                <input
                  type="text"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder="e.g. Full-Stack Engineer specializing in Distributed Systems"
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Local Profile ID (Slug) <span className="text-red-500">*</span>
                  </label>
                  <span className="text-[10px] text-zinc-400 font-mono">Used for local persistence file storage</span>
                </div>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => {
                    setUserId(e.target.value);
                    setUserIdEdited(true);
                  }}
                  placeholder="e.g. alex-rivera"
                  className="w-full text-xs font-mono bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>
          )}

          {/* STEP 2: Credentials & Academic Baseline */}
          {currentStep === 2 && (
            <div className="space-y-5">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Highest Degree Level
                </label>
                <select
                  value={highestDegree}
                  onChange={(e) => setHighestDegree(e.target.value)}
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                >
                  <option value="NONE">No Formal Degree</option>
                  <option value="HIGH_SCHOOL">High School Diploma / GED</option>
                  <option value="ASSOCIATES">Associate Degree (AA / AS)</option>
                  <option value="BACHELORS">Bachelor&apos;s Degree (BA / BS)</option>
                  <option value="MASTERS">Master&apos;s Degree (MS / MA)</option>
                  <option value="DOCTORATE">Doctoral Degree (Ph.D. / Ed.D.)</option>
                </select>
              </div>

              <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/80 dark:border-zinc-700 space-y-3">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isEnrolledStudent}
                    onChange={(e) => setIsEnrolledStudent(e.target.checked)}
                    className="w-4 h-4 text-teal-600 rounded-sm border-zinc-300 dark:border-zinc-600 focus:ring-teal-500"
                  />
                  <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Currently enrolled college/university student
                  </span>
                </label>

                {isEnrolledStudent && (
                  <div className="space-y-1 pl-6 pt-1">
                    <label className="text-[11px] text-zinc-500">
                      Expected Graduation Date
                    </label>
                    <input
                      type="date"
                      value={expectedGraduationDate}
                      onChange={(e) => setExpectedGraduationDate(e.target.value)}
                      className="text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-3 py-1.5 text-zinc-900 dark:text-zinc-100"
                    />
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Total Full-Time Professional Experience
                  </label>
                  <span className="text-xs font-mono font-semibold text-teal-600 dark:text-teal-400">
                    {experienceMonths} months ({(experienceMonths / 12).toFixed(1)} years)
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="120"
                  step="3"
                  value={experienceMonths}
                  onChange={(e) => setExperienceMonths(Number(e.target.value))}
                  className="w-full accent-teal-600 cursor-pointer"
                />
                <span className="text-[11px] text-zinc-500">
                  Slide to select your full-time post-graduate experience duration. Zero for new grads & students.
                </span>
              </div>
            </div>
          )}

          {/* STEP 3: Work Preferences & Eligibility Boundaries */}
          {currentStep === 3 && (
            <div className="space-y-5">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Allowed Opportunity Categories
                </label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {['FULL_TIME_JOB', 'INTERNSHIP'].map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => toggleCategory(cat)}
                      className={`p-3 rounded-lg border text-left font-medium transition-colors ${
                        allowedCategories.includes(cat)
                          ? 'bg-teal-50 dark:bg-teal-950/50 border-teal-300 dark:border-teal-700 text-teal-800 dark:text-teal-300'
                          : 'bg-zinc-50 dark:bg-zinc-800/40 border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400'
                      }`}
                    >
                      {cat.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Allowed Work Modes
                </label>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  {['REMOTE', 'HYBRID', 'ON_SITE'].map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => toggleWorkMode(mode)}
                      className={`p-2.5 rounded-lg border text-center font-medium transition-colors ${
                        allowedWorkModes.includes(mode)
                          ? 'bg-teal-50 dark:bg-teal-950/50 border-teal-300 dark:border-teal-700 text-teal-800 dark:text-teal-300'
                          : 'bg-zinc-50 dark:bg-zinc-800/40 border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400'
                      }`}
                    >
                      {mode.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Target Locations (Comma-separated)
                </label>
                <input
                  type="text"
                  value={preferredLocationsStr}
                  onChange={(e) => setPreferredLocationsStr(e.target.value)}
                  placeholder="e.g. Remote, San Francisco, CA, New York, NY"
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/80 dark:border-zinc-700">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visaRequired}
                    onChange={(e) => setVisaRequired(e.target.checked)}
                    className="w-4 h-4 text-teal-600 rounded-sm border-zinc-300 dark:border-zinc-600 focus:ring-teal-500"
                  />
                  <div>
                    <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 block">
                      Requires visa sponsorship (e.g. H-1B, OPT)
                    </span>
                    <span className="text-[11px] text-zinc-500">
                      Roles that do not sponsor work visas will be deterministically disqualified.
                    </span>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* STEP 4: Career Goals & Evidence-Backed Skills */}
          {currentStep === 4 && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Primary Target Career Ambition <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={targetRoleTitle}
                    onChange={(e) => setTargetRoleTitle(e.target.value)}
                    placeholder="e.g. Backend Software Engineer"
                    className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Adjacent Career Path (Optional)
                  </label>
                  <input
                    type="text"
                    value={adjacentRoleTitle}
                    onChange={(e) => setAdjacentRoleTitle(e.target.value)}
                    placeholder="e.g. Full Stack Developer"
                    className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              {/* Skills List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Initial Core Competencies ({skills.length})
                  </label>
                  <span className="text-[10px] text-zinc-400">Anchored to verifiable evidence snippets</span>
                </div>

                <div className="space-y-2">
                  {skills.map((s, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/80 dark:border-zinc-700 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-900 dark:text-zinc-100">{s.name}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-teal-50 dark:bg-teal-950/80 text-teal-700 dark:text-teal-400">
                            {s.proficiency.toFixed(1)}/10
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-500 italic line-clamp-1">&ldquo;{s.evidence}&rdquo;</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeSkill(idx)}
                        className="p-1 text-zinc-400 hover:text-red-500 transition-colors"
                        title="Remove skill"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Add Skill Mini-Form */}
                <div className="p-3.5 rounded-lg border border-dashed border-zinc-300 dark:border-zinc-700 space-y-3">
                  <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 block">
                    Add A Competency
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <input
                      type="text"
                      value={newSkillName}
                      onChange={(e) => setNewSkillName(e.target.value)}
                      placeholder="Skill name (e.g. TypeScript, React)"
                      className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-3 py-1.5 text-zinc-900 dark:text-zinc-100"
                    />
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-zinc-500 whitespace-nowrap">Proficiency:</span>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        step="0.5"
                        value={newSkillProf}
                        onChange={(e) => setNewSkillProf(Number(e.target.value))}
                        className="w-full accent-teal-600"
                      />
                      <span className="text-xs font-mono font-semibold text-teal-600 min-w-8">
                        {newSkillProf.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <input
                    type="text"
                    value={newSkillEvidence}
                    onChange={(e) => setNewSkillEvidence(e.target.value)}
                    placeholder="Evidence note or project excerpt (e.g. 'Built full-stack React portals in TypeScript')"
                    className="w-full text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-3 py-1.5 text-zinc-900 dark:text-zinc-100"
                  />
                  <button
                    type="button"
                    onClick={addSkill}
                    disabled={!newSkillName.trim()}
                    className="px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 dark:bg-zinc-700 dark:hover:bg-zinc-600 text-white text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Include Skill</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action Footer */}
        <div className="p-6 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            {onExploreDemo && (
              <button
                type="button"
                onClick={onExploreDemo}
                className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 underline font-mono"
              >
                Or explore with pre-built Demo Candidates
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {currentStep > 1 && (
              <button
                type="button"
                onClick={handleBack}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-xs font-semibold text-zinc-800 dark:text-zinc-200 transition-colors flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
            )}

            {currentStep < 4 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-white text-white dark:text-zinc-900 text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <span>Continue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-6 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>{isSubmitting ? 'Creating Profile...' : 'Complete Setup & Launch Workstation'}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

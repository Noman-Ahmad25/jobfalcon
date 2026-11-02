'use client';

import React, { useState, useRef } from 'react';
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  Plus,
  Trash2,
  Sparkles,
  Upload,
  FileText,
  RotateCw,
  FileCheck,
  FileCode,
  Briefcase,
  Check,
  AlertCircle,
  FolderGit2,
  GraduationCap,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  StructuredProfileCreateRequest,
  CandidateProfilingRequest,
  ExtractedWorkExperience,
  ExtractedProject,
  ExtractedEducation,
} from '@/types/domain';
import {
  createStructuredProfile,
  extractCandidateProfile,
  parseResumeFile,
} from '@/lib/api';

interface OnboardingScreenProps {
  onProfileCreated: (profile: CandidateCareerProfile) => void;
  onExploreDemo?: () => void;
}

export function OnboardingScreen({
  onProfileCreated,
  onExploreDemo,
}: OnboardingScreenProps) {
  // Steps: 1 = Upload / Input, 2 = Review Profile Draft, 3 = Preferences & Confirm
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Resume Ingestion State
  const [entryMode, setEntryMode] = useState<'upload' | 'manual'>('upload');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState<string>('');
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractSuccessMsg, setExtractSuccessMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Extracted Career Information (Editable Draft)
  const [displayName, setDisplayName] = useState('');
  const [headline, setHeadline] = useState('');
  const [userId, setUserId] = useState('');

  // Education & Experience
  const [highestDegree, setHighestDegree] = useState('BACHELORS');
  const [isEnrolledStudent, setIsEnrolledStudent] = useState(false);
  const [expectedGraduationDate, setExpectedGraduationDate] = useState('');
  const [experienceMonths, setExperienceMonths] = useState<number | null>(null);

  // Extracted Structured Items
  const [extractedExperiences, setExtractedExperiences] = useState<ExtractedWorkExperience[]>([]);
  const [extractedProjects, setExtractedProjects] = useState<ExtractedProject[]>([]);
  const [extractedEducation, setExtractedEducation] = useState<ExtractedEducation[]>([]);

  // Skills
  const [skills, setSkills] = useState<Array<{ name: string; proficiency: number; evidence: string }>>([]);
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillProf, setNewSkillProf] = useState(7.5);
  const [newSkillEvidence, setNewSkillEvidence] = useState('');

  // Career Preferences
  const [targetRoleTitle, setTargetRoleTitle] = useState('Software Engineer');
  const [adjacentRoleTitle, setAdjacentRoleTitle] = useState('Backend Engineer');
  const [authorizedCountries] = useState<string[]>(['US']);
  const [visaRequired, setVisaRequired] = useState(false);
  const [allowedCategories] = useState<string[]>(['FULL_TIME_JOB']);
  const [allowedWorkModes, setAllowedWorkModes] = useState<string[]>(['REMOTE', 'HYBRID']);
  const [preferredLocationsStr, setPreferredLocationsStr] = useState('Remote, San Francisco, CA');

  // Auto-generate slug from name
  const handleNameChange = (val: string) => {
    setDisplayName(val);
    const slug = val
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    setUserId(slug || 'candidate-user');
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
    setNewSkillProf(7.5);
    setNewSkillEvidence('');
  };

  const removeSkill = (index: number) => {
    setSkills(skills.filter((_, i) => i !== index));
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

  // Handle Resume File Selection
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setResumeFile(file);
    setErrorMessage(null);
    setExtractSuccessMsg(null);

    // If text file, preview text directly
    if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
      try {
        const text = await file.text();
        setResumeText(text);
      } catch {
        // Handled via backend on extract
      }
    }
  };

  // Perform AI extraction from uploaded file or text
  const handleExtractFromResume = async () => {
    let rawText = resumeText.trim();
    setIsExtracting(true);
    setErrorMessage(null);
    setExtractSuccessMsg(null);

    try {
      if (resumeFile && !rawText) {
        // Parse document via proper backend document extractor
        const parsed = await parseResumeFile(resumeFile);
        rawText = parsed.text;
        setResumeText(rawText);
      }

      if (!rawText) {
        throw new Error('Please select a resume file or paste your resume text first.');
      }

      const tempId = userId || 'new-candidate';
      const profilingReq: CandidateProfilingRequest = {
        user_id: tempId,
        resume_text: rawText,
        save_to_repository: false,
      };

      const res = await extractCandidateProfile(profilingReq);
      const extracted = res.extracted_profile;

      if (!extracted) {
        throw new Error('Analysis completed but did not produce a valid profile draft.');
      }

      // 1. Skills with evidence records (from skills section, projects, & experience)
      if (extracted.assessed_skills && extracted.assessed_skills.length > 0) {
        const parsedSkills = extracted.assessed_skills.map((s) => ({
          name: s.skill_name,
          proficiency: s.proficiency_score,
          evidence:
            s.evidence_records[0]?.extracted_snippet ||
            `Extracted competency in ${s.skill_name} from submitted resume.`,
        }));
        setSkills(parsedSkills);
      } else {
        // Fallback default skills if none recognized
        setSkills([
          { name: 'Problem Solving', proficiency: 8.0, evidence: 'Demonstrated in career experience' },
        ]);
      }

      // 2. Structured work experiences, projects, and education
      if (res.work_experiences) {
        setExtractedExperiences(res.work_experiences);
      }
      if (res.projects) {
        setExtractedProjects(res.projects);
      }
      if (res.education) {
        setExtractedEducation(res.education);
      }

      // 3. Constraints & credentials
      const c = extracted.eligibility_constraints;
      if (c) {
        if (c.highest_degree_level) setHighestDegree(c.highest_degree_level);
        if (typeof c.total_full_time_experience_months === 'number' && c.total_full_time_experience_months > 0) {
          setExperienceMonths(c.total_full_time_experience_months);
        } else {
          setExperienceMonths(null); // Unknown / unstated
        }
        if (c.is_currently_enrolled_student !== undefined) {
          setIsEnrolledStudent(c.is_currently_enrolled_student);
        }
        if (c.allowed_work_modes && c.allowed_work_modes.length > 0) {
          setAllowedWorkModes(c.allowed_work_modes);
        }
        if (c.preferred_locations && c.preferred_locations.length > 0) {
          setPreferredLocationsStr(c.preferred_locations.join(', '));
        }
        if (c.requires_visa_sponsorship !== undefined) {
          setVisaRequired(c.requires_visa_sponsorship);
        }
      }

      // 4. Candidate name & role direction
      if (extracted.display_name) {
        handleNameChange(extracted.display_name);
      } else if (!displayName) {
        const firstLine = rawText.split('\n')[0].replace(/[^a-zA-Z\s]/g, '').trim();
        if (firstLine.length > 2 && firstLine.length < 40) {
          handleNameChange(firstLine);
        }
      }

      if (extracted.target_career_paths && extracted.target_career_paths.length > 0) {
        setTargetRoleTitle(extracted.target_career_paths[0].title);
      }
      if (extracted.current_career_path?.title) {
        setHeadline(extracted.current_career_path.title);
      }

      const skillCount = extracted.assessed_skills?.length || 0;
      setExtractSuccessMsg(
        `Successfully analyzed resume: Extracted ${skillCount} skills and career details.`
      );
      setCurrentStep(2); // Automatically advance to the editable draft review step
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : 'Unable to parse document or analyze resume. Please check file format or paste text directly.'
      );
    } finally {
      setIsExtracting(false);
    }
  };

  const loadSampleResume = () => {
    const sample = `Jordan Lee
Software Engineer | Backend & Distributed Systems
San Francisco, CA • jordan.lee@example.com

SUMMARY
Full-stack software engineer with 3 years of production experience building high-throughput FastAPI microservices, relational PostgreSQL schemas, and Docker pipelines.

EXPERIENCE
Software Engineer — CloudScale Labs (2022 - Present)
• Built asynchronous microservices in Python with FastAPI handling 5,000 req/sec.
• Designed PostgreSQL relational schemas, query indexes, and connection pooling.
• Maintained Docker containers and automated CI/CD pipelines with GitHub Actions.

PROJECTS
High-Performance Cache Gateway
• Distributed caching proxy using Redis, Go, and REST APIs.

EDUCATION
B.S. in Computer Science — University of California, Berkeley (2022)
Coursework: Distributed Systems, Relational Databases, Operating Systems.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Go, Redis, TypeScript, Next.js, Git`;

    setResumeText(sample);
    setDisplayName('Jordan Lee');
    handleNameChange('Jordan Lee');
    setResumeFile(null);
  };

  const handleConfirmAndSave = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);

    const locations = preferredLocationsStr
      .split(',')
      .map((loc) => loc.trim())
      .filter((loc) => loc.length > 0);

    const payload: StructuredProfileCreateRequest = {
      user_id: userId.trim().toLowerCase() || 'candidate-user',
      display_name: displayName.trim() || 'Candidate',
      headline: headline.trim() || targetRoleTitle,
      highest_degree_level: highestDegree,
      is_currently_enrolled_student: isEnrolledStudent,
      expected_graduation_date: isEnrolledStudent && expectedGraduationDate ? expectedGraduationDate : undefined,
      total_full_time_experience_months: experienceMonths !== null ? Number(experienceMonths) : 0,
      authorized_country_codes: authorizedCountries,
      requires_visa_sponsorship: visaRequired,
      allowed_opportunity_categories: allowedCategories,
      allowed_work_modes: allowedWorkModes,
      preferred_locations: locations.length > 0 ? locations : ['Remote'],
      target_role_title: targetRoleTitle.trim() || 'Software Engineer',
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
        err instanceof Error ? err.message : 'Failed to save candidate profile. Please check your fields.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 sm:px-6">
      <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden">
        {/* Onboarding Header */}
        <div className="p-6 sm:p-8 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
          <div className="space-y-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-50 dark:bg-teal-950/80 text-teal-700 dark:text-teal-400 border border-teal-200/80 dark:border-teal-800">
              <Sparkles className="w-3.5 h-3.5" />
              Career Opportunity Discovery
            </span>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
              Find opportunities that fit you
            </h1>
            <p className="text-xs sm:text-sm text-zinc-500 max-w-xl leading-relaxed">
              Upload your resume and JobFalcon will build a career profile from your skills, projects,
              education, and experience.
            </p>
          </div>

          {/* Stepper Progress */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-6">
            {[
              { num: 1, label: 'Upload Resume' },
              { num: 2, label: 'Review Profile Draft' },
              { num: 3, label: 'Preferences & Start' },
            ].map((step) => {
              const isPast = step.num < currentStep;
              const isCurrent = step.num === currentStep;
              return (
                <div
                  key={step.num}
                  className={`flex items-center gap-2 p-2 rounded-xl border text-xs transition-colors ${
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
                    {isPast ? <Check className="w-3.5 h-3.5" /> : step.num}
                  </div>
                  <span className="truncate">{step.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Step Body */}
        <div className="p-6 sm:p-8 space-y-6">
          {errorMessage && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-400 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
              <div>
                <span className="font-semibold block">Document Analysis Error</span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          {extractSuccessMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{extractSuccessMsg}</span>
            </div>
          )}

          {/* =============================================================== */}
          {/* STEP 1: Upload Resume */}
          {/* =============================================================== */}
          {currentStep === 1 && (
            <div className="space-y-6">
              {/* Mode Toggle */}
              <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-3">
                <button
                  type="button"
                  onClick={() => setEntryMode('upload')}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    entryMode === 'upload'
                      ? 'bg-teal-600 text-white shadow-xs'
                      : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                  }`}
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload Resume Document</span>
                </button>

                <button
                  type="button"
                  onClick={() => setEntryMode('manual')}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    entryMode === 'manual'
                      ? 'bg-teal-600 text-white shadow-xs'
                      : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Paste Text or Form</span>
                </button>
              </div>

              {entryMode === 'upload' ? (
                <div className="space-y-4">
                  {/* Dropzone Area */}
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="p-8 border-2 border-dashed border-zinc-300 dark:border-zinc-700 hover:border-teal-500 dark:hover:border-teal-400 rounded-2xl bg-zinc-50/50 dark:bg-zinc-800/30 text-center cursor-pointer transition-colors space-y-3"
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.doc,.docx,.txt,.md"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                    <div className="w-12 h-12 mx-auto rounded-full bg-teal-50 dark:bg-teal-950/60 flex items-center justify-center text-teal-600 dark:text-teal-400">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 block">
                        {resumeFile ? resumeFile.name : 'Click to upload your resume'}
                      </span>
                      <p className="text-xs text-zinc-500 mt-1">
                        Supports PDF (.pdf), Word (.docx), or plain text (.txt, .md)
                      </p>
                    </div>
                    {resumeFile && (
                      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-teal-50 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 text-xs font-mono">
                        <FileCheck className="w-3.5 h-3.5" />
                        <span>Ready to analyze ({(resumeFile.size / 1024).toFixed(1)} KB)</span>
                      </div>
                    )}
                  </div>

                  {/* Or Paste Raw Text */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                        Or Paste Resume Text
                      </label>
                      <button
                        type="button"
                        onClick={loadSampleResume}
                        className="text-[11px] text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
                      >
                        <FileCode className="w-3 h-3" />
                        <span>Load Sample Resume</span>
                      </button>
                    </div>
                    <textarea
                      rows={5}
                      value={resumeText}
                      onChange={(e) => setResumeText(e.target.value)}
                      placeholder="Paste resume text, skills list, or experience description here..."
                      className="w-full text-xs font-mono bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-xl p-3 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                    />
                  </div>

                  {/* Analyze Button */}
                  <div className="pt-2 flex items-center justify-between">
                    {onExploreDemo && (
                      <button
                        type="button"
                        onClick={onExploreDemo}
                        className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 underline"
                      >
                        Explore with demo profile
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={handleExtractFromResume}
                      disabled={isExtracting || (!resumeFile && !resumeText.trim())}
                      className="ml-auto px-6 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm"
                    >
                      {isExtracting ? (
                        <>
                          <RotateCw className="w-4 h-4 animate-spin" />
                          <span>Reading & Analyzing Resume...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" />
                          <span>Analyze Resume & Build Profile Draft</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                /* Manual Setup */
                <div className="space-y-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                      Full Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => handleNameChange(e.target.value)}
                      placeholder="e.g. Jordan Lee"
                      className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                      Primary Target Role <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={targetRoleTitle}
                      onChange={(e) => setTargetRoleTitle(e.target.value)}
                      placeholder="e.g. Software Engineer"
                      className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => {
                        if (!displayName.trim()) {
                          setErrorMessage('Please enter your full name.');
                          return;
                        }
                        setCurrentStep(2);
                      }}
                      className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex items-center gap-1.5"
                    >
                      <span>Continue to Skills & Background</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =============================================================== */}
          {/* STEP 2: Review Profile Draft */}
          {/* =============================================================== */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="p-4 rounded-xl bg-teal-50/60 dark:bg-teal-950/40 border border-teal-200/80 dark:border-teal-800/60 text-xs flex items-center justify-between">
                <div>
                  <span className="font-semibold text-teal-900 dark:text-teal-200 block">
                    Structured Profile Draft
                  </span>
                  <span className="text-teal-700 dark:text-teal-300">
                    Review and customize the information extracted from your resume.
                  </span>
                </div>
                <span className="font-mono text-xs font-bold text-teal-800 dark:text-teal-300 shrink-0">
                  {skills.length} skills found
                </span>
              </div>

              {/* 1. Your Profile & Education Details */}
              <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700/80 space-y-4">
                <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono block">
                  Your Profile Information
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Your Full Name
                    </label>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => handleNameChange(e.target.value)}
                      placeholder="e.g. Jordan Lee"
                      className="w-full text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-zinc-100"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Target Career Role
                    </label>
                    <input
                      type="text"
                      value={targetRoleTitle}
                      onChange={(e) => setTargetRoleTitle(e.target.value)}
                      placeholder="e.g. Software Engineer"
                      className="w-full text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-zinc-100"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      Highest Academic Degree
                    </label>
                    <select
                      value={highestDegree}
                      onChange={(e) => setHighestDegree(e.target.value)}
                      className="w-full text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-zinc-100"
                    >
                      <option value="NONE">No Formal Degree</option>
                      <option value="HIGH_SCHOOL">High School Diploma</option>
                      <option value="ASSOCIATES">Associate Degree</option>
                      <option value="BACHELORS">Bachelor&apos;s Degree</option>
                      <option value="MASTERS">Master&apos;s Degree</option>
                      <option value="DOCTORATE">Doctoral Degree</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                        Professional Experience
                      </label>
                      <span className="text-xs font-mono text-teal-600 dark:text-teal-400">
                        {experienceMonths !== null
                          ? `${(experienceMonths / 12).toFixed(1)} years (${experienceMonths} mos)`
                          : 'Not specified'}
                      </span>
                    </div>
                    <select
                      value={experienceMonths !== null ? experienceMonths : -1}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setExperienceMonths(val >= 0 ? val : null);
                      }}
                      className="w-full text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-900 dark:text-zinc-100"
                    >
                      <option value={-1}>Not specified / Early Career</option>
                      <option value={6}>Entry-level (&lt; 1 year)</option>
                      <option value={12}>1 year experience</option>
                      <option value={24}>2 years experience</option>
                      <option value={36}>3 years experience</option>
                      <option value={60}>5+ years experience</option>
                    </select>
                  </div>
                </div>

                {/* Active Student Status & Expected Graduation */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-zinc-200 dark:border-zinc-700">
                  <label className="flex items-center gap-2 cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={isEnrolledStudent}
                      onChange={(e) => setIsEnrolledStudent(e.target.checked)}
                      className="w-4 h-4 text-teal-600 rounded-sm cursor-pointer"
                    />
                    <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                      Currently enrolled student
                    </span>
                  </label>
                  {isEnrolledStudent && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-zinc-500 text-[11px]">Expected Graduation:</span>
                      <input
                        type="date"
                        value={expectedGraduationDate}
                        onChange={(e) => setExpectedGraduationDate(e.target.value)}
                        className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded px-2.5 py-1 text-xs text-zinc-900 dark:text-zinc-100"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* 2. Skills We Found (Editable) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono">
                    Skills We Found
                  </label>
                  <span className="text-[11px] text-zinc-400">
                    Recognized from skills list, projects, and work experience
                  </span>
                </div>

                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {skills.map((skill, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                            {skill.name}
                          </span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-teal-50 dark:bg-teal-950/80 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800 font-mono">
                            Proficiency: {skill.proficiency.toFixed(1)} / 10
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-500 italic line-clamp-1">
                          &ldquo;{skill.evidence}&rdquo;
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => removeSkill(idx)}
                        className="text-zinc-400 hover:text-red-500 transition-colors p-1 self-end sm:self-center"
                        title="Remove skill"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                {/* Add Custom Skill */}
                <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
                  <span className="text-[11px] font-semibold text-zinc-700 dark:text-zinc-300">
                    Add another demonstrated skill:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                    <input
                      type="text"
                      placeholder="Skill name (e.g. Docker)"
                      value={newSkillName}
                      onChange={(e) => setNewSkillName(e.target.value)}
                      className="sm:col-span-2 text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-2.5 py-1.5 text-zinc-900 dark:text-zinc-100"
                    />
                    <select
                      value={newSkillProf}
                      onChange={(e) => setNewSkillProf(Number(e.target.value))}
                      className="text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-2.5 py-1.5 text-zinc-900 dark:text-zinc-100"
                    >
                      <option value="6.0">Proficiency: 6.0</option>
                      <option value="7.5">Proficiency: 7.5</option>
                      <option value="8.5">Proficiency: 8.5</option>
                      <option value="10.0">Proficiency: 10.0</option>
                    </select>
                    <button
                      type="button"
                      onClick={addSkill}
                      className="px-3 py-1.5 rounded-md bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex items-center justify-center gap-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add</span>
                    </button>
                  </div>
                </div>

                {/* Active Student Status & Expected Graduation */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-zinc-200 dark:border-zinc-700">
                  <label className="flex items-center gap-2 cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={isEnrolledStudent}
                      onChange={(e) => setIsEnrolledStudent(e.target.checked)}
                      className="w-4 h-4 text-teal-600 rounded-sm cursor-pointer"
                    />
                    <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                      Currently enrolled student
                    </span>
                  </label>
                  {isEnrolledStudent && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-zinc-500 text-[11px]">Expected Graduation:</span>
                      <input
                        type="date"
                        value={expectedGraduationDate}
                        onChange={(e) => setExpectedGraduationDate(e.target.value)}
                        className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded px-2.5 py-1 text-xs text-zinc-900 dark:text-zinc-100"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* 3. Extracted Experience, Projects, & Education Preview */}
              {(extractedExperiences.length > 0 || extractedProjects.length > 0 || extractedEducation.length > 0) && (
                <div className="space-y-3 pt-2 border-t border-zinc-200 dark:border-zinc-800">
                  <label className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider font-mono block">
                    Experience, Projects & Education Recognized
                  </label>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {extractedExperiences.map((exp, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 space-y-1"
                      >
                        <div className="flex items-center gap-1.5 font-semibold text-zinc-900 dark:text-zinc-100">
                          <Briefcase className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                          <span className="truncate">{exp.role_title}</span>
                        </div>
                        <span className="text-[11px] text-zinc-500 block truncate">
                          {exp.company_name} {exp.start_date && `(${exp.start_date} - ${exp.end_date || 'Present'})`}
                        </span>
                        {exp.technologies_used?.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap pt-1">
                            {exp.technologies_used.map((tech, tIdx) => (
                              <span
                                key={tIdx}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-200/70 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
                              >
                                {tech}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}

                    {extractedProjects.map((proj, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 space-y-1"
                      >
                        <div className="flex items-center gap-1.5 font-semibold text-zinc-900 dark:text-zinc-100">
                          <FolderGit2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                          <span className="truncate">{proj.project_name}</span>
                        </div>
                        <p className="text-[11px] text-zinc-500 line-clamp-2">
                          {proj.description}
                        </p>
                        {proj.technologies?.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap pt-1">
                            {proj.technologies.map((tech, tIdx) => (
                              <span
                                key={tIdx}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-200/70 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300"
                              >
                                {tech}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}

                    {extractedEducation.map((edu, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 space-y-1"
                      >
                        <div className="flex items-center gap-1.5 font-semibold text-zinc-900 dark:text-zinc-100">
                          <GraduationCap className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                          <span className="truncate">{edu.institution_name}</span>
                        </div>
                        <span className="text-[11px] text-zinc-500 block truncate">
                          {edu.degree_level} in {edu.field_of_study || 'Field'} {edu.graduation_date && `(${edu.graduation_date})`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Navigation Actions */}
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back</span>
                </button>

                <button
                  type="button"
                  onClick={() => setCurrentStep(3)}
                  className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-2xs"
                >
                  <span>Continue to Preferences</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* =============================================================== */}
          {/* STEP 3: Preferences & Confirm */}
          {/* =============================================================== */}
          {currentStep === 3 && (
            <div className="space-y-6">
              {/* Roles */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Primary Target Career Role
                  </label>
                  <input
                    type="text"
                    value={targetRoleTitle}
                    onChange={(e) => setTargetRoleTitle(e.target.value)}
                    placeholder="e.g. Software Engineer"
                    className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-xl px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                    Adjacent Role for Broader Matching (Optional)
                  </label>
                  <input
                    type="text"
                    value={adjacentRoleTitle}
                    onChange={(e) => setAdjacentRoleTitle(e.target.value)}
                    placeholder="e.g. Backend Engineer or Platform Engineer"
                    className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-xl px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100"
                  />
                </div>
              </div>

              {/* Work Modes */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Allowed Work Arrangements
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'REMOTE', label: 'Remote' },
                    { id: 'HYBRID', label: 'Hybrid' },
                    { id: 'ON_SITE', label: 'On-Site' },
                  ].map((mode) => {
                    const active = allowedWorkModes.includes(mode.id);
                    return (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => toggleWorkMode(mode.id)}
                        className={`p-3 rounded-xl border text-xs font-semibold transition-colors flex items-center justify-center gap-2 ${
                          active
                            ? 'bg-teal-50 dark:bg-teal-950/60 border-teal-500 text-teal-800 dark:text-teal-200'
                            : 'bg-zinc-50 dark:bg-zinc-800/40 border-zinc-200 dark:border-zinc-700 text-zinc-500'
                        }`}
                      >
                        {active && <Check className="w-3.5 h-3.5 text-teal-600" />}
                        <span>{mode.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Target Locations */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
                  Target Locations (Comma-separated)
                </label>
                <input
                  type="text"
                  value={preferredLocationsStr}
                  onChange={(e) => setPreferredLocationsStr(e.target.value)}
                  placeholder="e.g. Remote, San Francisco, CA, New York, NY"
                  className="w-full text-xs bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-xl px-3.5 py-2.5 text-zinc-900 dark:text-zinc-100"
                />
              </div>

              {/* Visa Sponsorship */}
              <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-700 flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 block">
                    Requires Work Visa Sponsorship
                  </span>
                  <span className="text-[11px] text-zinc-500">
                    Filter opportunities that do or do not require employer visa support
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={visaRequired}
                  onChange={(e) => setVisaRequired(e.target.checked)}
                  className="w-4 h-4 text-teal-600 rounded-sm cursor-pointer"
                />
              </div>

              {/* Final Confirm Button */}
              <div className="flex items-center justify-between pt-4 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Draft</span>
                </button>

                <button
                  type="button"
                  onClick={handleConfirmAndSave}
                  disabled={isSubmitting}
                  className="px-6 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RotateCw className="w-4 h-4 animate-spin" />
                      <span>Saving Profile...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span>Confirm Profile & Start Discovery</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

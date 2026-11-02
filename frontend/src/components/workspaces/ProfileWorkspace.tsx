'use client';

import React, { useState, useRef } from 'react';
import {
  User,
  GraduationCap,
  Briefcase,
  FolderGit2,
  ChevronDown,
  ChevronUp,
  Upload,
  RotateCw,
  CheckCircle2,
  Sliders,
  ArrowLeft,
  Sparkles,
  Plus,
  Trash2,
  Edit3,
  ExternalLink,
  Search,
  Save,
  MapPin,
  Building2,
  AlertCircle,
  X,
  Calendar,
  Code2,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  CandidateProfilingRequest,
  DegreeLevel,
  ExtractedWorkExperience,
  ExtractedProject,
  ExtractedEducation,
  AssessedSkill,
  WorkMode,
} from '@/types/domain';
import {
  extractCandidateProfile,
  parseResumeFile,
  updateCandidateProfile,
} from '@/lib/api';
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
  // 1. Core Profile Local State
  const [profile, setProfile] = useState<CandidateCareerProfile>(candidateProfile);
  const [prevPropProfile, setPrevPropProfile] = useState<CandidateCareerProfile>(candidateProfile);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Sync if incoming candidateProfile changes from external prop without effect
  if (candidateProfile !== prevPropProfile) {
    setPrevPropProfile(candidateProfile);
    if (!isDirty) {
      setProfile(candidateProfile);
    }
  }

  // 2. Resume Ingestion & Analysis State
  const [showUploadDrawer, setShowUploadDrawer] = useState<boolean>(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [rawExtractText, setRawExtractText] = useState<string>('');
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractStage, setExtractStage] = useState<number>(0);
  const [extractStageText, setExtractStageText] = useState<string>('');
  const [extractError, setExtractError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // 3. Extracted Draft Review Modal
  const [draftProfile, setDraftProfile] = useState<CandidateCareerProfile | null>(null);
  const [showDraftModal, setShowDraftModal] = useState<boolean>(false);
  const [draftActiveTab, setDraftActiveTab] = useState<'overview' | 'experience' | 'projects' | 'education' | 'skills'>('overview');

  // 4. Manual CRUD Modals
  const [activeModal, setActiveModal] = useState<
    'none' | 'experience' | 'project' | 'education' | 'skill' | 'overview' | 'preferences'
  >('none');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  // Experience Form State
  const [expRole, setExpRole] = useState('');
  const [expCompany, setExpCompany] = useState('');
  const [expStartDate, setExpStartDate] = useState('');
  const [expEndDate, setExpEndDate] = useState('');
  const [expIsCurrent, setExpIsCurrent] = useState(false);
  const [expResponsibilities, setExpResponsibilities] = useState('');
  const [expTechnologies, setExpTechnologies] = useState('');

  // Project Form State
  const [projName, setProjName] = useState('');
  const [projDescription, setProjDescription] = useState('');
  const [projTechnologies, setProjTechnologies] = useState('');
  const [projRepoUrl, setProjRepoUrl] = useState('');

  // Education Form State
  const [eduInstitution, setEduInstitution] = useState('');
  const [eduDegreeLevel, setEduDegreeLevel] = useState<DegreeLevel>('BACHELORS');
  const [eduField, setEduField] = useState('');
  const [eduGradDate, setEduGradDate] = useState('');
  const [eduIsEnrolled, setEduIsEnrolled] = useState(false);

  // Skill Form State
  const [skillNameInput, setSkillNameInput] = useState('');
  const [skillProfScore, setSkillProfScore] = useState<number>(8.0);
  const [skillEvidenceInput, setSkillEvidenceInput] = useState('');

  // Overview Form State
  const [overviewName, setOverviewName] = useState('');
  const [overviewHeadline, setOverviewHeadline] = useState('');
  const [overviewLocation, setOverviewLocation] = useState('');
  const [overviewBio, setOverviewBio] = useState('');

  // Preferences Form State
  const [prefTargetRoles, setPrefTargetRoles] = useState<string[]>([]);
  const [prefNewRole, setPrefNewRole] = useState('');
  const [prefLocations, setPrefLocations] = useState<string[]>([]);
  const [prefNewLocation, setPrefNewLocation] = useState('');
  const [prefWorkModes, setPrefWorkModes] = useState<WorkMode[]>(['REMOTE']);
  const [prefVisaRequired, setPrefVisaRequired] = useState(false);
  const [prefIsEnrolled, setPrefIsEnrolled] = useState(false);
  const [prefDegree, setPrefDegree] = useState<DegreeLevel>('BACHELORS');
  const [prefExperienceMonths, setPrefExperienceMonths] = useState<number>(0);

  // Skill search & expanded evidence state
  const [skillSearch, setSkillSearch] = useState('');
  const [expandedSkillId, setExpandedSkillId] = useState<string | null>(null);

  // =========================================================================
  // Resume File Selection & Multi-Step Analysis
  // =========================================================================

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFile(file);
    setExtractError(null);
    if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
      try {
        const text = await file.text();
        setRawExtractText(text);
      } catch {
        // Fallback to backend parser
      }
    }
  };

  async function handleExtractResume() {
    setIsExtracting(true);
    setExtractError(null);
    setExtractStage(1);
    setExtractStageText('Reading and validating document text...');

    try {
      let textToExtract = rawExtractText.trim();
      if (uploadedFile && !textToExtract) {
        setExtractStageText(`Parsing readable text from ${uploadedFile.name}...`);
        const parsed = await parseResumeFile(uploadedFile);
        textToExtract = parsed.text;
        setRawExtractText(textToExtract);
      }

      if (!textToExtract) {
        throw new Error('Please select a resume file (.pdf, .docx, .txt) or paste resume text.');
      }

      setExtractStage(2);
      setExtractStageText('Analyzing career history, roles, and experience trajectory...');

      // Small delay for UI smoothness
      await new Promise((r) => setTimeout(r, 400));

      setExtractStage(3);
      setExtractStageText('Extracting technical competencies & verifiable project evidence...');

      const req: CandidateProfilingRequest = {
        resume_text: textToExtract,
        user_id: profile.user_id,
        save_to_repository: false, // Extract into draft first for user review!
      };

      setExtractStage(4);
      setExtractStageText('Structuring projects, academic qualifications, and career goals...');

      const res = await extractCandidateProfile(req);

      setExtractStage(5);
      setExtractStageText('Preparing structured profile draft for your review...');

      if (!res.extracted_profile) {
        throw new Error('The extraction engine did not produce a valid candidate profile.');
      }

      setDraftProfile(res.extracted_profile);
      setShowDraftModal(true);
      setShowUploadDrawer(false);
      setUploadedFile(null);
      setRawExtractText('');
    } catch (err: unknown) {
      setExtractError(
        err instanceof Error ? err.message : 'Unable to parse and extract resume information.'
      );
    } finally {
      setIsExtracting(false);
      setExtractStage(0);
      setExtractStageText('');
    }
  }

  // Commit Draft to Active Profile
  async function handleApplyDraft() {
    if (!draftProfile) return;
    setIsSaving(true);
    try {
      const updated = await updateCandidateProfile(profile.user_id, draftProfile);
      setProfile(updated);
      setIsDirty(false);
      setShowDraftModal(false);
      setDraftProfile(null);
      setSaveMessage('Resume draft applied and profile saved successfully.');
      setTimeout(() => setSaveMessage(null), 4000);
      if (onProfileUpdated) {
        onProfileUpdated(updated);
      }
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save updated profile.');
      setTimeout(() => setSaveError(null), 5000);
    } finally {
      setIsSaving(false);
    }
  }

  // Save Current Profile State to Database
  async function handleSaveProfile() {
    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await updateCandidateProfile(profile.user_id, profile);
      setProfile(updated);
      setIsDirty(false);
      setSaveMessage('Profile saved successfully.');
      setTimeout(() => setSaveMessage(null), 3000);
      if (onProfileUpdated) {
        onProfileUpdated(updated);
      }
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save profile changes.');
      setTimeout(() => setSaveError(null), 5000);
    } finally {
      setIsSaving(false);
    }
  }

  // =========================================================================
  // Experience CRUD Handlers
  // =========================================================================

  function openAddExperience() {
    setExpRole('');
    setExpCompany('');
    setExpStartDate('');
    setExpEndDate('');
    setExpIsCurrent(false);
    setExpResponsibilities('');
    setExpTechnologies('');
    setEditingIndex(null);
    setActiveModal('experience');
  }

  function openEditExperience(idx: number) {
    const exp = (profile.work_experiences || [])[idx];
    if (!exp) return;
    setExpRole(exp.role_title);
    setExpCompany(exp.company_name);
    setExpStartDate(exp.start_date || '');
    setExpEndDate(exp.end_date || '');
    setExpIsCurrent(exp.is_current);
    setExpResponsibilities((exp.responsibilities || []).join('\n'));
    setExpTechnologies((exp.technologies_used || []).join(', '));
    setEditingIndex(idx);
    setActiveModal('experience');
  }

  function handleSaveExperience() {
    if (!expRole.trim() || !expCompany.trim()) return;
    const respList = expResponsibilities
      .split('\n')
      .map((r) => r.trim().replace(/^[•*\-]\s*/, ''))
      .filter((r) => r.length > 0);
    const techList = expTechnologies
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const newExp: ExtractedWorkExperience = {
      role_title: expRole.trim(),
      company_name: expCompany.trim(),
      start_date: expStartDate.trim() || null,
      end_date: expIsCurrent ? 'Present' : expEndDate.trim() || null,
      is_current: expIsCurrent,
      responsibilities: respList.length > 0 ? respList : ['Contributed to engineering workflows.'],
      technologies_used: techList,
    };

    const currentExps = [...(profile.work_experiences || [])];
    if (editingIndex !== null) {
      currentExps[editingIndex] = newExp;
    } else {
      currentExps.unshift(newExp);
    }

    setProfile({ ...profile, work_experiences: currentExps });
    setIsDirty(true);
    setActiveModal('none');
  }

  function handleDeleteExperience(idx: number) {
    const currentExps = [...(profile.work_experiences || [])];
    currentExps.splice(idx, 1);
    setProfile({ ...profile, work_experiences: currentExps });
    setIsDirty(true);
  }

  // =========================================================================
  // Project CRUD Handlers
  // =========================================================================

  function openAddProject() {
    setProjName('');
    setProjDescription('');
    setProjTechnologies('');
    setProjRepoUrl('');
    setEditingIndex(null);
    setActiveModal('project');
  }

  function openEditProject(idx: number) {
    const proj = (profile.projects || [])[idx];
    if (!proj) return;
    setProjName(proj.project_name);
    setProjDescription(proj.description);
    setProjTechnologies((proj.technologies || []).join(', '));
    setProjRepoUrl(proj.repository_url || '');
    setEditingIndex(idx);
    setActiveModal('project');
  }

  function handleSaveProject() {
    if (!projName.trim()) return;
    const techList = projTechnologies
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const newProj: ExtractedProject = {
      project_name: projName.trim(),
      description: projDescription.trim() || 'Demonstrated engineering implementation.',
      technologies: techList,
      repository_url: projRepoUrl.trim() || null,
    };

    const currentProjs = [...(profile.projects || [])];
    if (editingIndex !== null) {
      currentProjs[editingIndex] = newProj;
    } else {
      currentProjs.unshift(newProj);
    }

    setProfile({ ...profile, projects: currentProjs });
    setIsDirty(true);
    setActiveModal('none');
  }

  function handleDeleteProject(idx: number) {
    const currentProjs = [...(profile.projects || [])];
    currentProjs.splice(idx, 1);
    setProfile({ ...profile, projects: currentProjs });
    setIsDirty(true);
  }

  // =========================================================================
  // Education CRUD Handlers
  // =========================================================================

  function openAddEducation() {
    setEduInstitution('');
    setEduDegreeLevel('BACHELORS');
    setEduField('');
    setEduGradDate('');
    setEduIsEnrolled(false);
    setEditingIndex(null);
    setActiveModal('education');
  }

  function openEditEducation(idx: number) {
    const edu = (profile.education || [])[idx];
    if (!edu) return;
    setEduInstitution(edu.institution_name);
    setEduDegreeLevel(edu.degree_level);
    setEduField(edu.field_of_study || '');
    setEduGradDate(edu.graduation_date || '');
    setEduIsEnrolled(edu.is_enrolled);
    setEditingIndex(idx);
    setActiveModal('education');
  }

  function handleSaveEducation() {
    if (!eduInstitution.trim()) return;

    const newEdu: ExtractedEducation = {
      institution_name: eduInstitution.trim(),
      degree_level: eduDegreeLevel,
      field_of_study: eduField.trim() || 'Computer Science',
      graduation_date: eduGradDate.trim() || null,
      is_enrolled: eduIsEnrolled,
    };

    const currentEdus = [...(profile.education || [])];
    if (editingIndex !== null) {
      currentEdus[editingIndex] = newEdu;
    } else {
      currentEdus.unshift(newEdu);
    }

    // Automatically synchronize highest degree level in constraints
    const constraints = { ...profile.eligibility_constraints };
    constraints.highest_degree_level = eduDegreeLevel;
    constraints.is_currently_enrolled_student = eduIsEnrolled;

    setProfile({
      ...profile,
      education: currentEdus,
      eligibility_constraints: constraints,
    });
    setIsDirty(true);
    setActiveModal('none');
  }

  function handleDeleteEducation(idx: number) {
    const currentEdus = [...(profile.education || [])];
    currentEdus.splice(idx, 1);
    setProfile({ ...profile, education: currentEdus });
    setIsDirty(true);
  }

  // =========================================================================
  // Skill CRUD Handlers
  // =========================================================================

  function openAddSkill() {
    setSkillNameInput('');
    setSkillProfScore(8.0);
    setSkillEvidenceInput('');
    setEditingIndex(null);
    setActiveModal('skill');
  }

  function openEditSkill(idx: number) {
    const skill = profile.assessed_skills[idx];
    if (!skill) return;
    setSkillNameInput(skill.skill_name);
    setSkillProfScore(skill.proficiency_score);
    setSkillEvidenceInput(skill.evidence_records[0]?.extracted_snippet || '');
    setEditingIndex(idx);
    setActiveModal('skill');
  }

  function handleSaveSkill() {
    if (!skillNameInput.trim()) return;
    const cleanName = skillNameInput.trim();
    const canonId = `custom:${cleanName.toLowerCase().replace(/\s+/g, '-')}`;

    const evidence = {
      evidence_id: `ev_manual_${Date.now()}`,
      source_type: 'RESUME_WORK_EXPERIENCE' as const,
      extracted_snippet:
        skillEvidenceInput.trim() || `Demonstrated proficiency in ${cleanName} through career activities.`,
      observed_at: new Date().toISOString(),
      verifiability_weight: skillEvidenceInput.trim() ? 0.85 : 0.65,
    };

    const newSkill: AssessedSkill = {
      canonical_skill_id: canonId,
      skill_name: cleanName,
      proficiency_score: Number(skillProfScore),
      confidence_score: 0.9,
      evidence_records: [evidence],
    };

    const currentSkills = [...profile.assessed_skills];
    if (editingIndex !== null) {
      currentSkills[editingIndex] = newSkill;
    } else {
      // Check if skill already exists
      const existingIdx = currentSkills.findIndex(
        (s) => s.skill_name.toLowerCase() === cleanName.toLowerCase()
      );
      if (existingIdx >= 0) {
        currentSkills[existingIdx] = newSkill;
      } else {
        currentSkills.unshift(newSkill);
      }
    }

    setProfile({ ...profile, assessed_skills: currentSkills });
    setIsDirty(true);
    setActiveModal('none');
  }

  function handleDeleteSkill(idx: number) {
    const currentSkills = [...profile.assessed_skills];
    currentSkills.splice(idx, 1);
    setProfile({ ...profile, assessed_skills: currentSkills });
    setIsDirty(true);
  }

  // =========================================================================
  // Profile Overview Handlers
  // =========================================================================

  function openEditOverview() {
    setOverviewName(profile.display_name || candidateName || '');
    setOverviewHeadline(profile.headline || '');
    setOverviewLocation(profile.location || '');
    setOverviewBio(profile.bio || '');
    setActiveModal('overview');
  }

  function handleSaveOverview() {
    setProfile({
      ...profile,
      display_name: overviewName.trim() || profile.display_name,
      headline: overviewHeadline.trim() || profile.headline,
      location: overviewLocation.trim() || profile.location,
      bio: overviewBio.trim() || profile.bio,
    });
    setIsDirty(true);
    setActiveModal('none');
  }

  // =========================================================================
  // Career Preferences Handlers
  // =========================================================================

  function openEditPreferences() {
    setPrefTargetRoles(profile.target_career_paths.map((p) => p.title));
    setPrefNewRole('');
    setPrefLocations(profile.eligibility_constraints.preferred_locations || []);
    setPrefNewLocation('');
    setPrefWorkModes(profile.eligibility_constraints.allowed_work_modes || ['REMOTE']);
    setPrefVisaRequired(profile.eligibility_constraints.requires_visa_sponsorship);
    setPrefIsEnrolled(profile.eligibility_constraints.is_currently_enrolled_student);
    setPrefDegree(profile.eligibility_constraints.highest_degree_level);
    setPrefExperienceMonths(profile.eligibility_constraints.total_full_time_experience_months || 0);
    setActiveModal('preferences');
  }

  function handleSavePreferences() {
    const targetNodes = prefTargetRoles.map((role) => ({
      occupation_code: '15-1252.00',
      title: role,
      relationship_type: 'TARGET' as const,
      adjacency_similarity: 1.0,
      missing_core_skill_ids: [],
    }));

    const constraints = {
      ...profile.eligibility_constraints,
      preferred_locations: prefLocations,
      allowed_work_modes: prefWorkModes.length > 0 ? prefWorkModes : (['REMOTE'] as WorkMode[]),
      requires_visa_sponsorship: prefVisaRequired,
      is_currently_enrolled_student: prefIsEnrolled,
      highest_degree_level: prefDegree,
      total_full_time_experience_months: Number(prefExperienceMonths),
    };

    setProfile({
      ...profile,
      target_career_paths: targetNodes.length > 0 ? targetNodes : profile.target_career_paths,
      eligibility_constraints: constraints,
    });
    setIsDirty(true);
    setActiveModal('none');
  }

  // Filter skills by search query
  const filteredSkills = profile.assessed_skills.filter((s) =>
    s.skill_name.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const targetRole = profile.target_career_paths[0]?.title || profile.headline || 'Software Engineer';
  const expMonths = profile.eligibility_constraints.total_full_time_experience_months;
  const expDisplay =
    expMonths > 0
      ? `${(expMonths / 12).toFixed(1)} years (${expMonths} mos)`
      : 'Early Career';

  // Derived initials for avatar
  const displayName = profile.display_name || candidateName || 'Candidate';
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('') || 'CA';

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* 1. Top Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-zinc-200 dark:border-zinc-800 shadow-2xs">
        <button
          onClick={() => onNavigateTab('discover')}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/60 text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
          <span>Back to Opportunity Discovery</span>
        </button>

        <div className="flex items-center gap-2 flex-wrap">
          {isDirty && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-[11px] font-medium text-amber-700 dark:text-amber-400">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
              Unsaved changes
            </span>
          )}

          {saveMessage && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-[11px] font-medium text-emerald-700 dark:text-emerald-400 animate-in fade-in">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {saveMessage}
            </span>
          )}

          {saveError && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-[11px] font-medium text-red-700 dark:text-red-400">
              <AlertCircle className="w-3.5 h-3.5" />
              {saveError}
            </span>
          )}

          <button
            onClick={() => setShowUploadDrawer(!showUploadDrawer)}
            className="px-3.5 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800/80 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload or Replace Resume</span>
          </button>

          <button
            onClick={handleSaveProfile}
            disabled={isSaving || !isDirty}
            className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-2xs cursor-pointer"
          >
            {isSaving ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. Resume Ingestion & Progressive Analysis Drawer */}
      {showUploadDrawer && (
        <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-teal-200 dark:border-teal-900/60 shadow-md space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Upload className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              Upload or Replace Resume
            </h3>
            <button
              onClick={() => setShowUploadDrawer(false)}
              className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 font-mono cursor-pointer"
            >
              Close
            </button>
          </div>

          <p className="text-xs text-zinc-500">
            Upload your resume (.pdf, .docx, .doc, .txt, .md). JobFalcon extracts readable text, identifies your career trajectory, work experiences, projects, education, and technical competencies with verbatim source quotes.
          </p>

          {extractError && (
            <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-400 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{extractError}</span>
            </div>
          )}

          {/* Progressive Stage Stepper Indicator during analysis */}
          {isExtracting && (
            <div className="p-4 rounded-xl bg-teal-50/60 dark:bg-teal-950/30 border border-teal-200/80 dark:border-teal-800 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-teal-900 dark:text-teal-200">
                <span className="flex items-center gap-2">
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-teal-600" />
                  {extractStageText}
                </span>
                <span className="font-mono text-[11px] text-teal-600 dark:text-teal-400">
                  Step {extractStage} of 5
                </span>
              </div>
              <div className="w-full bg-zinc-200/80 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-teal-600 h-full transition-all duration-300"
                  style={{ width: `${extractStage * 20}%` }}
                />
              </div>
            </div>
          )}

          {/* File Picker Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="p-6 border-2 border-dashed border-zinc-300 dark:border-zinc-700 hover:border-teal-500 dark:hover:border-teal-400 rounded-xl bg-zinc-50/50 dark:bg-zinc-800/40 text-center cursor-pointer transition-colors"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,.md"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-300">
              <Upload className="w-6 h-6 text-teal-600 dark:text-teal-400 mb-1" />
              <span className="font-semibold text-sm">
                {uploadedFile ? uploadedFile.name : 'Click to select a resume document (.pdf, .docx, .txt)'}
              </span>
              <span className="text-[11px] text-zinc-400">
                Supports PDF text, Word documents, Markdown, and plain text.
              </span>
            </div>
          </div>

          <textarea
            value={rawExtractText}
            onChange={(e) => setRawExtractText(e.target.value)}
            rows={4}
            placeholder="Or paste resume text, project descriptions, or career summary directly here..."
            className="w-full p-3 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs font-sans focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
          />

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              onClick={() => setShowUploadDrawer(false)}
              className="px-3.5 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleExtractResume}
              disabled={isExtracting || (!rawExtractText.trim() && !uploadedFile)}
              className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5 shadow-2xs cursor-pointer"
            >
              {isExtracting ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Analyzing Resume...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Analyze Resume & Review Draft</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* 3. Hero Card: Candidate Career Profile (LinkedIn / Wellfound style) */}
      <div className="p-6 sm:p-8 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
          <div className="flex items-start gap-5">
            {/* Avatar Initials Badge */}
            <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-teal-500 to-emerald-700 text-white flex items-center justify-center text-xl sm:text-2xl font-bold font-mono shadow-md shrink-0">
              {initials}
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
                  {displayName}
                </h1>
                <button
                  onClick={openEditOverview}
                  className="p-1 rounded-md text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
                  title="Edit profile info"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
              </div>

              <p className="text-sm font-medium text-teal-600 dark:text-teal-400">
                {profile.headline || targetRole}
              </p>

              <div className="flex items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400 flex-wrap pt-0.5">
                {profile.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                    {profile.location}
                  </span>
                )}
                <span className="flex items-center gap-1 font-mono">
                  <User className="w-3.5 h-3.5 text-zinc-400" />
                  ID: {profile.user_id}
                </span>
                <span className="flex items-center gap-1">
                  <Briefcase className="w-3.5 h-3.5 text-zinc-400" />
                  {expDisplay}
                </span>
              </div>
            </div>
          </div>

          <div className="flex sm:flex-col items-start sm:items-end gap-2 shrink-0">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider font-mono">
              Profile Completeness
            </span>
            <div className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {(profile.overall_profile_confidence * 100).toFixed(0)}%
            </div>
            <span className="text-[11px] text-zinc-500">
              {profile.assessed_skills.length} verified skills
            </span>
          </div>
        </div>

        {/* Bio / Executive Summary */}
        {profile.bio && (
          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800/80 text-xs sm:text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
            {profile.bio}
          </div>
        )}

        {/* Quick Highlights Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Highest Degree
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate block mt-0.5">
              {profile.eligibility_constraints.highest_degree_level}
            </span>
            <span className="text-[10px] text-zinc-500 block">
              {profile.eligibility_constraints.is_currently_enrolled_student ? 'Currently Enrolled' : 'Graduated'}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Work Experience
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block mt-0.5">
              {profile.work_experiences?.length || 0} Positions
            </span>
            <span className="text-[10px] text-zinc-500 block">
              {expDisplay}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Projects & Code
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block mt-0.5">
              {profile.projects?.length || 0} Featured Projects
            </span>
            <span className="text-[10px] text-zinc-500 block">With tech stack evidence</span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Work Preferences
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate block mt-0.5">
              {profile.eligibility_constraints.allowed_work_modes.join(', ')}
            </span>
            <span className="text-[10px] text-zinc-500 block truncate">
              {profile.eligibility_constraints.requires_visa_sponsorship ? 'Visa Required' : 'No Visa Needed'}
            </span>
          </div>
        </div>
      </div>

      {/* 4. Work Experience Section */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Work Experience & Internships</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.work_experiences?.length || 0})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Professional roles, internships, and engineering contributions.
            </p>
          </div>

          <button
            onClick={openAddExperience}
            className="px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800/80 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Experience</span>
          </button>
        </div>

        {(!profile.work_experiences || profile.work_experiences.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <Briefcase className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-xs text-zinc-500">No work experience records added yet.</p>
            <button
              onClick={openAddExperience}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
            >
              + Add your first position
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {profile.work_experiences.map((exp, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                      {exp.role_title}
                    </h3>
                    <div className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400 flex-wrap">
                      <span className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5 text-zinc-500" />
                        {exp.company_name}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1 font-mono text-[11px]">
                        <Calendar className="w-3.5 h-3.5 text-zinc-400" />
                        {exp.start_date || 'Past'} – {exp.is_current ? 'Present' : exp.end_date || 'Past'}
                      </span>
                      {exp.is_current && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 font-mono">
                          Current Role
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => openEditExperience(idx)}
                      className="p-1.5 rounded-md text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                      title="Edit experience"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDeleteExperience(idx)}
                      className="p-1.5 rounded-md text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                      title="Delete experience"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Responsibilities */}
                {exp.responsibilities && exp.responsibilities.length > 0 && (
                  <ul className="space-y-1 text-xs text-zinc-600 dark:text-zinc-300 list-disc list-inside">
                    {exp.responsibilities.map((r, rIdx) => (
                      <li key={rIdx} className="leading-relaxed">
                        {r}
                      </li>
                    ))}
                  </ul>
                )}

                {/* Tech Tags */}
                {exp.technologies_used && exp.technologies_used.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-zinc-200/50 dark:border-zinc-700/50">
                    <span className="text-[10px] text-zinc-400 font-mono uppercase">Tech:</span>
                    {exp.technologies_used.map((tech, tIdx) => (
                      <span
                        key={tIdx}
                        className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-[11px] font-medium text-zinc-700 dark:text-zinc-300"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 5. Projects & Portfolio Section */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Projects & Engineering Artifacts</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.projects?.length || 0})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Significant projects, applications, and verifiable technical demonstrations.
            </p>
          </div>

          <button
            onClick={openAddProject}
            className="px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800/80 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Project</span>
          </button>
        </div>

        {(!profile.projects || profile.projects.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <FolderGit2 className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-xs text-zinc-500">No projects added yet.</p>
            <button
              onClick={openAddProject}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
            >
              + Add a portfolio project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.projects.map((proj, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                      {proj.project_name}
                    </h3>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => openEditProject(idx)}
                        className="p-1.5 rounded-md text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                        title="Edit project"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteProject(idx)}
                        className="p-1.5 rounded-md text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                        title="Delete project"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed">
                    {proj.description}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-zinc-200/50 dark:border-zinc-700/50">
                  {proj.technologies && proj.technologies.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {proj.technologies.map((t, tIdx) => (
                        <span
                          key={tIdx}
                          className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-[10px] font-mono text-zinc-700 dark:text-zinc-300"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}

                  {proj.repository_url && (
                    <a
                      href={proj.repository_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-mono text-teal-600 dark:text-teal-400 hover:underline"
                    >
                      <ExternalLink className="w-3 h-3" />
                      <span>{proj.repository_url.replace(/^https?:\/\//, '')}</span>
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 6. Education Section */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Education & Credentials</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.education?.length || 0})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Academic institutions, degrees, and student enrollment status.
            </p>
          </div>

          <button
            onClick={openAddEducation}
            className="px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800/80 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Education</span>
          </button>
        </div>

        {(!profile.education || profile.education.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <GraduationCap className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-xs text-zinc-500">No education records added yet.</p>
            <button
              onClick={openAddEducation}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
            >
              + Add academic degree
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.education.map((edu, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors flex items-start justify-between gap-3"
              >
                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                    {edu.institution_name}
                  </h3>
                  <p className="text-xs font-medium text-teal-600 dark:text-teal-400">
                    {edu.degree_level} in {edu.field_of_study || 'General Studies'}
                  </p>
                  <div className="flex items-center gap-2 text-[11px] text-zinc-500 font-mono pt-1">
                    <span>Graduation: {edu.graduation_date || 'Not stated'}</span>
                    <span>•</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] ${
                        edu.is_enrolled
                          ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                          : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400'
                      }`}
                    >
                      {edu.is_enrolled ? 'Currently Enrolled' : 'Completed'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => openEditEducation(idx)}
                    className="p-1.5 rounded-md text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                    title="Edit education"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDeleteEducation(idx)}
                    className="p-1.5 rounded-md text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                    title="Delete education"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 7. Skills & Demonstrated Evidence Section */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Code2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Skills & Demonstrated Evidence</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.assessed_skills.length})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Technical competencies extracted from your materials with verbatim excerpts.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search skills..."
                value={skillSearch}
                onChange={(e) => setSkillSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-xs w-44 focus:outline-hidden focus:ring-1 focus:ring-teal-500"
              />
            </div>

            <button
              onClick={openAddSkill}
              className="px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800/80 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Skill</span>
            </button>
          </div>
        </div>

        {filteredSkills.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <Code2 className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-xs text-zinc-500">
              {skillSearch ? 'No skills match your search.' : 'No skills recorded on profile.'}
            </p>
            <button
              onClick={openAddSkill}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
            >
              + Add a skill manually
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5">
            {filteredSkills.map((skill) => {
              const isExpanded = expandedSkillId === skill.canonical_skill_id;
              const profPercent = (skill.proficiency_score / 10) * 100;
              const realIdx = profile.assessed_skills.findIndex(
                (s) => s.canonical_skill_id === skill.canonical_skill_id
              );

              return (
                <div
                  key={skill.canonical_skill_id}
                  className="rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 overflow-hidden shadow-2xs transition-colors hover:border-zinc-300 dark:hover:border-zinc-700"
                >
                  <div
                    onClick={() =>
                      setExpandedSkillId(
                        isExpanded ? null : skill.canonical_skill_id
                      )
                    }
                    className="p-3.5 flex items-center justify-between gap-4 cursor-pointer"
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
                            {skill.evidence_records.length} evidence excerpt{skill.evidence_records.length > 1 ? 's' : ''}
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
                      {/* Mini Score Bar */}
                      <div className="w-24 hidden sm:block">
                        <div className="h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-teal-500 rounded-full"
                            style={{ width: `${profPercent}%` }}
                          />
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditSkill(realIdx);
                        }}
                        className="p-1 text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors cursor-pointer"
                        title="Edit skill"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSkill(realIdx);
                        }}
                        className="p-1 text-zinc-400 hover:text-red-600 dark:hover:text-red-400 transition-colors cursor-pointer"
                        title="Delete skill"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>

                      <button
                        className="p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors cursor-pointer"
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
                    <div className="p-4 bg-zinc-100/60 dark:bg-zinc-900/60 border-t border-zinc-200 dark:border-zinc-800 space-y-2.5">
                      <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block">
                        Verbatim Excerpts from Your Materials
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
        )}
      </div>

      {/* 8. Career Direction & Opportunity Preferences Section */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Career Direction & Work Preferences</span>
            </h2>
            <p className="text-xs text-zinc-500">
              JobFalcon uses these criteria to match and evaluate career opportunities.
            </p>
          </div>

          <button
            onClick={openEditPreferences}
            className="px-3 py-1.5 rounded-lg border border-teal-200 dark:border-teal-800/80 bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 hover:bg-teal-100 dark:hover:bg-teal-900/60 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit Preferences</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Target Career Roles
            </span>
            <div className="flex items-center gap-1.5 flex-wrap pt-1">
              {profile.target_career_paths.map((p, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 font-semibold text-zinc-800 dark:text-zinc-200"
                >
                  {p.title}
                </span>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Allowed Work Modes
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1">
              {profile.eligibility_constraints.allowed_work_modes.join(', ')}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Target Locations
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1 truncate">
              {profile.eligibility_constraints.preferred_locations.join(', ') || 'Any Location / Remote'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Visa Sponsorship
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1">
              {profile.eligibility_constraints.requires_visa_sponsorship ? 'Required' : 'Not Required'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Total Professional Experience
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1">
              {expDisplay}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Student Status
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1">
              {profile.eligibility_constraints.is_currently_enrolled_student ? 'Enrolled Student' : 'Not Enrolled'}
            </span>
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* MODAL 1: Structured AI Resume Draft Review Drawer/Modal               */}
      {/* ===================================================================== */}
      {showDraftModal && draftProfile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="relative w-full max-w-3xl max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl border border-teal-200 dark:border-teal-800 flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="p-6 border-b border-zinc-200 dark:border-zinc-800 bg-teal-50/50 dark:bg-teal-950/30 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                  <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                    Resume Extraction Complete
                  </h2>
                </div>
                <p className="text-xs text-zinc-600 dark:text-zinc-400">
                  We parsed your resume and built a structured draft. Review the extracted records below before applying them to your profile.
                </p>
              </div>

              <button
                onClick={() => setShowDraftModal(false)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Summary Counters */}
            <div className="grid grid-cols-4 gap-2 p-4 bg-zinc-50 dark:bg-zinc-800/40 border-b border-zinc-200 dark:border-zinc-800 text-center text-xs">
              <div className="p-2">
                <span className="text-[10px] text-zinc-400 uppercase font-mono block">Work Roles</span>
                <span className="text-base font-bold text-teal-600 dark:text-teal-400">
                  {draftProfile.work_experiences?.length || 0}
                </span>
              </div>
              <div className="p-2">
                <span className="text-[10px] text-zinc-400 uppercase font-mono block">Projects</span>
                <span className="text-base font-bold text-teal-600 dark:text-teal-400">
                  {draftProfile.projects?.length || 0}
                </span>
              </div>
              <div className="p-2">
                <span className="text-[10px] text-zinc-400 uppercase font-mono block">Education</span>
                <span className="text-base font-bold text-teal-600 dark:text-teal-400">
                  {draftProfile.education?.length || 0}
                </span>
              </div>
              <div className="p-2">
                <span className="text-[10px] text-zinc-400 uppercase font-mono block">Skills Found</span>
                <span className="text-base font-bold text-emerald-600 dark:text-emerald-400">
                  {draftProfile.assessed_skills.length}
                </span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-1 px-6 pt-3 border-b border-zinc-200 dark:border-zinc-800 overflow-x-auto text-xs font-medium">
              {(['overview', 'experience', 'projects', 'education', 'skills'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDraftActiveTab(tab)}
                  className={`px-3 py-2 border-b-2 transition-colors capitalize cursor-pointer ${
                    draftActiveTab === tab
                      ? 'border-teal-600 text-teal-600 dark:text-teal-400 font-semibold'
                      : 'border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Modal Body Preview */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
              {draftActiveTab === 'overview' && (
                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-2">
                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase font-mono">Candidate Name</span>
                      <p className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                        {draftProfile.display_name || 'Not detected'}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase font-mono">Professional Headline</span>
                      <p className="text-zinc-800 dark:text-zinc-200 font-medium">
                        {draftProfile.headline || 'Software Engineer'}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-zinc-400 uppercase font-mono">Location</span>
                      <p className="text-zinc-700 dark:text-zinc-300">
                        {draftProfile.location || 'Not detected'}
                      </p>
                    </div>
                    {draftProfile.bio && (
                      <div>
                        <span className="text-[10px] text-zinc-400 uppercase font-mono">Summary</span>
                        <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed pt-1">
                          {draftProfile.bio}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {draftActiveTab === 'experience' && (
                <div className="space-y-3">
                  {(draftProfile.work_experiences || []).map((exp, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-zinc-900 dark:text-zinc-100">
                          {exp.role_title}
                        </span>
                        <span className="text-[10px] font-mono text-zinc-400">
                          {exp.start_date || 'Past'} – {exp.is_current ? 'Present' : exp.end_date || 'Past'}
                        </span>
                      </div>
                      <p className="text-zinc-600 dark:text-zinc-400 font-medium">
                        {exp.company_name}
                      </p>
                      <ul className="list-disc list-inside space-y-0.5 text-zinc-600 dark:text-zinc-300">
                        {(exp.responsibilities || []).map((r, rIdx) => (
                          <li key={rIdx}>{r}</li>
                        ))}
                      </ul>
                      {exp.technologies_used && exp.technologies_used.length > 0 && (
                        <div className="flex items-center gap-1 flex-wrap pt-1">
                          {exp.technologies_used.map((t, tIdx) => (
                            <span
                              key={tIdx}
                              className="px-1.5 py-0.5 rounded bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-[10px] font-mono"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {draftActiveTab === 'projects' && (
                <div className="space-y-3">
                  {(draftProfile.projects || []).map((proj, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1.5"
                    >
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">
                        {proj.project_name}
                      </span>
                      <p className="text-zinc-600 dark:text-zinc-300 leading-relaxed">
                        {proj.description}
                      </p>
                      {proj.technologies && proj.technologies.length > 0 && (
                        <div className="flex items-center gap-1 flex-wrap pt-1">
                          {proj.technologies.map((t, tIdx) => (
                            <span
                              key={tIdx}
                              className="px-1.5 py-0.5 rounded bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-[10px] font-mono"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {draftActiveTab === 'education' && (
                <div className="space-y-3">
                  {(draftProfile.education || []).map((edu, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1"
                    >
                      <span className="font-bold text-zinc-900 dark:text-zinc-100">
                        {edu.institution_name}
                      </span>
                      <p className="text-teal-600 dark:text-teal-400 font-medium">
                        {edu.degree_level} in {edu.field_of_study}
                      </p>
                      <p className="text-zinc-500 font-mono text-[11px]">
                        Graduation: {edu.graduation_date || 'Expected'} • {edu.is_enrolled ? 'Currently Enrolled' : 'Completed'}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {draftActiveTab === 'skills' && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {draftProfile.assessed_skills.map((skill) => (
                    <div
                      key={skill.canonical_skill_id}
                      className="p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                          {skill.skill_name}
                        </span>
                        <span className="text-[10px] font-mono text-teal-600">
                          {skill.proficiency_score.toFixed(1)}
                        </span>
                      </div>
                      {skill.evidence_records[0]?.extracted_snippet && (
                        <p className="text-[10px] text-zinc-400 truncate italic">
                          &ldquo;{skill.evidence_records[0].extracted_snippet}&rdquo;
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 sm:p-6 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowDraftModal(false);
                  setDraftProfile(null);
                }}
                className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Discard Draft
              </button>
              <button
                onClick={handleApplyDraft}
                disabled={isSaving}
                className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-2xs cursor-pointer"
              >
                {isSaving ? (
                  <>
                    <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Applying & Saving...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Apply to Profile & Save</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 2: Add / Edit Experience                                       */}
      {/* ===================================================================== */}
      {activeModal === 'experience' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Work Experience' : 'Add Work Experience'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Job Title / Role *</label>
                <input
                  type="text"
                  value={expRole}
                  onChange={(e) => setExpRole(e.target.value)}
                  placeholder="e.g. Backend Developer Intern"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Company Name *</label>
                <input
                  type="text"
                  value={expCompany}
                  onChange={(e) => setExpCompany(e.target.value)}
                  placeholder="e.g. Dream Filler"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-500 mb-1 font-medium">Start Date</label>
                  <input
                    type="text"
                    value={expStartDate}
                    onChange={(e) => setExpStartDate(e.target.value)}
                    placeholder="e.g. Sep 2026"
                    className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block text-zinc-500 mb-1 font-medium">End Date</label>
                  <input
                    type="text"
                    value={expEndDate}
                    disabled={expIsCurrent}
                    onChange={(e) => setExpEndDate(e.target.value)}
                    placeholder="e.g. Present"
                    className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden disabled:opacity-40"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="exp_is_current"
                  checked={expIsCurrent}
                  onChange={(e) => setExpIsCurrent(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <label htmlFor="exp_is_current" className="text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  I currently work here
                </label>
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Responsibilities (one per line)</label>
                <textarea
                  value={expResponsibilities}
                  onChange={(e) => setExpResponsibilities(e.target.value)}
                  rows={3}
                  placeholder="• Built 40+ FastAPI endpoints&#10;• Implemented multi-role RBAC"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Technologies Used (comma-separated)</label>
                <input
                  type="text"
                  value={expTechnologies}
                  onChange={(e) => setExpTechnologies(e.target.value)}
                  placeholder="Python, FastAPI, PostgreSQL, Redis"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveExperience}
                disabled={!expRole.trim() || !expCompany.trim()}
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 cursor-pointer"
              >
                Save Experience
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 3: Add / Edit Project                                          */}
      {/* ===================================================================== */}
      {activeModal === 'project' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Project' : 'Add Project'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Project Name *</label>
                <input
                  type="text"
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  placeholder="e.g. AlumniConn Platform"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Description</label>
                <textarea
                  value={projDescription}
                  onChange={(e) => setProjDescription(e.target.value)}
                  rows={3}
                  placeholder="Built a deployed platform with hybrid mentor recommendations using 384-dimensional embeddings..."
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Technologies Used (comma-separated)</label>
                <input
                  type="text"
                  value={projTechnologies}
                  onChange={(e) => setProjTechnologies(e.target.value)}
                  placeholder="FastAPI, React, TypeScript, PostgreSQL, pgvector"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Repository or Demo URL</label>
                <input
                  type="text"
                  value={projRepoUrl}
                  onChange={(e) => setProjRepoUrl(e.target.value)}
                  placeholder="https://github.com/noman/project"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProject}
                disabled={!projName.trim()}
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 cursor-pointer"
              >
                Save Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 4: Add / Edit Education                                        */}
      {/* ===================================================================== */}
      {activeModal === 'education' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Education' : 'Add Education'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Institution Name *</label>
                <input
                  type="text"
                  value={eduInstitution}
                  onChange={(e) => setEduInstitution(e.target.value)}
                  placeholder="e.g. Vindhya Institute of Technology and Science"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-500 mb-1 font-medium">Degree Level</label>
                  <select
                    value={eduDegreeLevel}
                    onChange={(e) => setEduDegreeLevel(e.target.value as DegreeLevel)}
                    className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  >
                    <option value="BACHELORS">Bachelors</option>
                    <option value="MASTERS">Masters</option>
                    <option value="DOCTORATE">Doctorate</option>
                    <option value="ASSOCIATE">Associate</option>
                    <option value="HIGH_SCHOOL">High School</option>
                    <option value="NONE">None / Self-Taught</option>
                  </select>
                </div>
                <div>
                  <label className="block text-zinc-500 mb-1 font-medium">Field of Study</label>
                  <input
                    type="text"
                    value={eduField}
                    onChange={(e) => setEduField(e.target.value)}
                    placeholder="e.g. Computer Science"
                    className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Graduation Year / Date</label>
                <input
                  type="text"
                  value={eduGradDate}
                  onChange={(e) => setEduGradDate(e.target.value)}
                  placeholder="e.g. 2027"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="edu_is_enrolled"
                  checked={eduIsEnrolled}
                  onChange={(e) => setEduIsEnrolled(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <label htmlFor="edu_is_enrolled" className="text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  Currently enrolled student
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEducation}
                disabled={!eduInstitution.trim()}
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 cursor-pointer"
              >
                Save Education
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 5: Add / Edit Skill                                            */}
      {/* ===================================================================== */}
      {activeModal === 'skill' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Skill & Evidence' : 'Add Skill'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Skill Name *</label>
                <input
                  type="text"
                  value={skillNameInput}
                  onChange={(e) => setSkillNameInput(e.target.value)}
                  placeholder="e.g. FastAPI, PostgreSQL, Docker"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-zinc-500 font-medium">Proficiency Rating (1 - 10)</label>
                  <span className="font-mono font-bold text-teal-600 dark:text-teal-400">
                    {Number(skillProfScore).toFixed(1)} / 10.0
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.5"
                  value={skillProfScore}
                  onChange={(e) => setSkillProfScore(parseFloat(e.target.value))}
                  className="w-full accent-teal-600"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">
                  Supporting Evidence Snippet (from work or project)
                </label>
                <textarea
                  value={skillEvidenceInput}
                  onChange={(e) => setSkillEvidenceInput(e.target.value)}
                  rows={3}
                  placeholder="e.g. Built 40+ REST API endpoints using FastAPI and PostgreSQL with RBAC permissions."
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveSkill}
                disabled={!skillNameInput.trim()}
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 cursor-pointer"
              >
                Save Skill
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 6: Edit Profile Overview                                       */}
      {/* ===================================================================== */}
      {activeModal === 'overview' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Edit Profile Overview
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Candidate Name</label>
                <input
                  type="text"
                  value={overviewName}
                  onChange={(e) => setOverviewName(e.target.value)}
                  placeholder="e.g. Noman Ahmad"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Professional Headline</label>
                <input
                  type="text"
                  value={overviewHeadline}
                  onChange={(e) => setOverviewHeadline(e.target.value)}
                  placeholder="e.g. Backend Engineer | Python, FastAPI & AI Systems"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Location</label>
                <input
                  type="text"
                  value={overviewLocation}
                  onChange={(e) => setOverviewLocation(e.target.value)}
                  placeholder="e.g. Satna, Madhya Pradesh, India"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Bio / Summary</label>
                <textarea
                  value={overviewBio}
                  onChange={(e) => setOverviewBio(e.target.value)}
                  rows={4}
                  placeholder="Brief summary of your career, engineering background, and interests..."
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveOverview}
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer"
              >
                Apply Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 7: Edit Career Preferences                                     */}
      {/* ===================================================================== */}
      {activeModal === 'preferences' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Edit Career Preferences
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Target Roles */}
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Target Roles</label>
                <div className="flex items-center gap-1.5 flex-wrap mb-2">
                  {prefTargetRoles.map((role, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-300"
                    >
                      <span>{role}</span>
                      <button
                        type="button"
                        onClick={() =>
                          setPrefTargetRoles(prefTargetRoles.filter((_, i) => i !== idx))
                        }
                        className="hover:text-red-500 cursor-pointer"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={prefNewRole}
                    onChange={(e) => setPrefNewRole(e.target.value)}
                    placeholder="Add target role (e.g. Backend Engineer)"
                    className="flex-1 p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (prefNewRole.trim()) {
                        setPrefTargetRoles([...prefTargetRoles, prefNewRole.trim()]);
                        setPrefNewRole('');
                      }
                    }}
                    className="px-3 py-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 text-xs font-semibold cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Target Locations */}
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Target Locations</label>
                <div className="flex items-center gap-1.5 flex-wrap mb-2">
                  {prefLocations.map((loc, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200"
                    >
                      <span>{loc}</span>
                      <button
                        type="button"
                        onClick={() =>
                          setPrefLocations(prefLocations.filter((_, i) => i !== idx))
                        }
                        className="hover:text-red-500 cursor-pointer"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={prefNewLocation}
                    onChange={(e) => setPrefNewLocation(e.target.value)}
                    placeholder="Add target location (e.g. Remote, Bengaluru)"
                    className="flex-1 p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (prefNewLocation.trim()) {
                        setPrefLocations([...prefLocations, prefNewLocation.trim()]);
                        setPrefNewLocation('');
                      }
                    }}
                    className="px-3 py-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 text-xs font-semibold cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Work Modes */}
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">Allowed Work Modes</label>
                <div className="flex items-center gap-2">
                  {(['REMOTE', 'HYBRID', 'ON_SITE'] as WorkMode[]).map((mode) => {
                    const active = prefWorkModes.includes(mode);
                    return (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => {
                          if (active) {
                            if (prefWorkModes.length > 1) {
                              setPrefWorkModes(prefWorkModes.filter((m) => m !== mode));
                            }
                          } else {
                            setPrefWorkModes([...prefWorkModes, mode]);
                          }
                        }}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer transition-colors ${
                          active
                            ? 'bg-teal-50 dark:bg-teal-950/80 border-teal-300 dark:border-teal-700 text-teal-800 dark:text-teal-300'
                            : 'bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 text-zinc-500'
                        }`}
                      >
                        {mode}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Visa & Enrolled Status */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="pref_visa"
                    checked={prefVisaRequired}
                    onChange={(e) => setPrefVisaRequired(e.target.checked)}
                    className="rounded text-teal-600 focus:ring-teal-500"
                  />
                  <label htmlFor="pref_visa" className="text-zinc-700 dark:text-zinc-300 cursor-pointer">
                    Requires Visa Sponsorship
                  </label>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="pref_enrolled"
                    checked={prefIsEnrolled}
                    onChange={(e) => setPrefIsEnrolled(e.target.checked)}
                    className="rounded text-teal-600 focus:ring-teal-500"
                  />
                  <label htmlFor="pref_enrolled" className="text-zinc-700 dark:text-zinc-300 cursor-pointer">
                    Currently Enrolled Student
                  </label>
                </div>
              </div>

              {/* Total Experience Months */}
              <div>
                <label className="block text-zinc-500 mb-1 font-medium">
                  Total Experience Duration (in months)
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min="0"
                    max="480"
                    value={prefExperienceMonths}
                    onChange={(e) => setPrefExperienceMonths(parseInt(e.target.value) || 0)}
                    className="w-32 p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                  <span className="text-zinc-500 text-xs">
                    = {(prefExperienceMonths / 12).toFixed(1)} years
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSavePreferences}
                className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer"
              >
                Apply Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

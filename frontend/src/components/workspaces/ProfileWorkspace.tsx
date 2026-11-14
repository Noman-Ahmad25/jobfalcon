'use client';

import React, { useState, useRef, useMemo, useEffect, useCallback } from 'react';
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
  Layers,
  Database,
  Cpu,
  Cloud,
  Award,
  Globe,
  Brain,
  History,
  Clock,
} from 'lucide-react';
import {
  CandidateCareerProfile,
  CandidateProfilingRequest,
  CandidateCareerMemoryItem,
  DegreeLevel,
  ExtractedWorkExperience,
  ExtractedProject,
  ExtractedEducation,
  AssessedSkill,
  WorkMode,
  EvidenceRecord,
  MemoryType,
  ProvenanceLevel,
} from '@/types/domain';
import {
  extractCandidateProfile,
  parseResumeFile,
  updateCandidateProfile,
  getCandidateMemories,
  createCandidateMemory,
  updateCandidateMemory,
  deactivateCandidateMemory,
  getMemoryLineage,
} from '@/lib/api';
import { Badge } from '@/components/ui/Badge';
import { WorkspaceTab } from '@/components/layout/Header';

// =============================================================================
// 1. Skill Categorization Definitions & Engine
// =============================================================================

export type SkillCategoryKey =
  | 'languages'
  | 'backend'
  | 'frontend'
  | 'databases'
  | 'ai_ml'
  | 'devops_cloud'
  | 'other';

export interface SkillCategoryDef {
  key: SkillCategoryKey;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

export const SKILL_CATEGORIES: SkillCategoryDef[] = [
  {
    key: 'languages',
    title: 'Programming Languages',
    icon: Code2,
    accentColor: 'text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-900/60 bg-blue-50/50 dark:bg-blue-950/20',
  },
  {
    key: 'backend',
    title: 'Backend Development',
    icon: Layers,
    accentColor: 'text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/20',
  },
  {
    key: 'frontend',
    title: 'Frontend Development',
    icon: Globe,
    accentColor: 'text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-900/60 bg-sky-50/50 dark:bg-sky-950/20',
  },
  {
    key: 'databases',
    title: 'Databases & Storage',
    icon: Database,
    accentColor: 'text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/20',
  },
  {
    key: 'ai_ml',
    title: 'AI / Machine Learning',
    icon: Cpu,
    accentColor: 'text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-900/60 bg-purple-50/50 dark:bg-purple-950/20',
  },
  {
    key: 'devops_cloud',
    title: 'Cloud, DevOps & Tools',
    icon: Cloud,
    accentColor: 'text-teal-600 dark:text-teal-400 border-teal-200 dark:border-teal-900/60 bg-teal-50/50 dark:bg-teal-950/20',
  },
  {
    key: 'other',
    title: 'Other Competencies',
    icon: Award,
    accentColor: 'text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-800/20',
  },
];

export function categorizeSkill(skillName: string): SkillCategoryKey {
  const s = skillName.toLowerCase().trim();

  // 1. Languages
  const languages = [
    'python', 'typescript', 'javascript', 'java', 'c++', 'c#', 'c', 'golang', 'go',
    'rust', 'ruby', 'php', 'swift', 'kotlin', 'dart', 'scala', 'r', 'matlab',
    'lua', 'shell', 'bash', 'powershell', 'sql', 'html', 'css', 'sass', 'scss',
  ];
  if (languages.some((l) => s === l || s === `${l} programming` || s.startsWith(`${l} `) || s.endsWith(` ${l}`))) {
    return 'languages';
  }

  // 2. AI / ML
  const aiKeywords = [
    'machine learning', 'deep learning', 'artificial intelligence', 'llm', 'llms',
    'nlp', 'natural language', 'computer vision', 'pytorch', 'tensorflow', 'keras',
    'scikit-learn', 'scikit', 'hugging face', 'huggingface', 'transformers',
    'langchain', 'langgraph', 'rag', 'retrieval-augmented', 'embeddings',
    'vector search', 'yolo', 'roboflow', 'litellm', 'ollama', 'openai',
    'gemini', 'prompt engineering', 'generative ai', 'reinforcement learning',
  ];
  if (aiKeywords.some((k) => s.includes(k))) {
    return 'ai_ml';
  }

  // 3. Databases
  const dbKeywords = [
    'postgres', 'postgresql', 'mysql', 'sqlite', 'mongodb', 'redis', 'cassandra',
    'dynamodb', 'elasticsearch', 'pgvector', 'faiss', 'pinecone', 'supabase',
    'firebase', 'couchdb', 'mariadb', 'neo4j', 'database', 'rdbms', 'nosql', 'firestore',
  ];
  if (dbKeywords.some((k) => s.includes(k))) {
    return 'databases';
  }

  // 4. Backend
  const backendKeywords = [
    'fastapi', 'django', 'flask', 'node.js', 'nodejs', 'express.js', 'express',
    'spring', 'spring boot', 'nestjs', 'rest', 'restful', 'graphql', 'grpc',
    'microservices', 'rabbitmq', 'kafka', 'celery', 'arq', 'websockets', 'sse',
    'server-sent events', 'jwt', 'oauth', 'rbac', 'pydantic', 'sqlalchemy',
    'alembic', 'prisma', 'hibernate', 'asp.net', '.net', 'api design',
    'backend', 'distributed systems',
  ];
  if (backendKeywords.some((k) => s.includes(k))) {
    return 'backend';
  }

  // 5. Frontend
  const frontendKeywords = [
    'react', 'react.js', 'next.js', 'nextjs', 'vue', 'vue.js', 'angular', 'svelte',
    'tailwind', 'tailwind css', 'bootstrap', 'material ui', 'shadcn', 'redux',
    'zustand', 'mobx', 'html5', 'css3', 'frontend', 'web development',
    'responsive design', 'flutter', 'react native', 'ui/ux', 'vite', 'webpack',
  ];
  if (frontendKeywords.some((k) => s.includes(k))) {
    return 'frontend';
  }

  // 6. DevOps & Cloud
  const devopsKeywords = [
    'docker', 'kubernetes', 'k8s', 'aws', 'amazon web services', 'gcp', 'google cloud',
    'azure', 'git', 'github', 'gitlab', 'ci/cd', 'github actions', 'terraform',
    'ansible', 'linux', 'unix', 'nginx', 'apache', 'prometheus', 'grafana',
    'opentelemetry', 'datadog', 'pytest', 'ruff', 'mypy', 'jest', 'vitest',
    'render', 'vercel', 'postman', 'sentry', 'devops', 'monitoring', 'cloud',
  ];
  if (devopsKeywords.some((k) => s.includes(k))) {
    return 'devops_cloud';
  }

  return 'other';
}

// =============================================================================
// 2. Profile Completeness Calibration Engine
// =============================================================================

export interface CompletenessItem {
  label: string;
  points: number;
  maxPoints: number;
  met: boolean;
  hint: string;
}

export function calculateProfileCompleteness(profile: CandidateCareerProfile): {
  score: number;
  breakdown: CompletenessItem[];
} {
  const breakdown: CompletenessItem[] = [];

  // 1. Overview (Name, Headline, Location, Bio) - 20 pts
  let overviewPts = 0;
  if (profile.display_name?.trim()) overviewPts += 5;
  if (profile.headline?.trim()) overviewPts += 5;
  if (profile.location?.trim()) overviewPts += 5;
  if (profile.bio?.trim()) overviewPts += 5;
  breakdown.push({
    label: 'Profile Overview',
    points: overviewPts,
    maxPoints: 20,
    met: overviewPts >= 15,
    hint: overviewPts < 20 ? 'Add headline, bio, or location' : 'Complete',
  });

  // 2. Career Direction & Preferences - 15 pts
  let prefPts = 0;
  if (profile.target_career_paths && profile.target_career_paths.length > 0) prefPts += 8;
  if (profile.eligibility_constraints?.allowed_work_modes?.length > 0) prefPts += 4;
  if (profile.eligibility_constraints?.preferred_locations?.length > 0) prefPts += 3;
  breakdown.push({
    label: 'Career Preferences',
    points: prefPts,
    maxPoints: 15,
    met: prefPts >= 12,
    hint: prefPts < 15 ? 'Specify target roles and work modes' : 'Configured',
  });

  // 3. Demonstrated Skills - 25 pts (at least 5 skills gives full 25 pts)
  const skillCount = profile.assessed_skills?.length || 0;
  const skillPts = Math.min(25, skillCount * 5);
  breakdown.push({
    label: 'Demonstrated Skills',
    points: skillPts,
    maxPoints: 25,
    met: skillCount >= 5,
    hint: skillCount < 5 ? `Add ${5 - skillCount} more skill(s)` : `${skillCount} skills documented`,
  });

  // 4. Education History - 20 pts
  const hasEdu =
    (profile.education && profile.education.length > 0) ||
    Boolean(
      profile.eligibility_constraints?.highest_degree_level &&
      profile.eligibility_constraints.highest_degree_level !== 'NONE'
    );
  const eduPts = hasEdu ? 20 : 0;
  breakdown.push({
    label: 'Education & Credentials',
    points: eduPts,
    maxPoints: 20,
    met: hasEdu,
    hint: hasEdu ? 'Degree credentials recorded' : 'Add academic history',
  });

  // 5. Practical Experience OR Projects (Student-Friendly Calibration!) - 20 pts
  const hasWorkExp = (profile.work_experiences?.length || 0) > 0;
  const projectCount = profile.projects?.length || 0;
  const isStudent = Boolean(profile.eligibility_constraints?.is_currently_enrolled_student);

  let expPts = 0;
  if (hasWorkExp) {
    expPts = 20;
  } else if (isStudent && projectCount >= 2) {
    // Enrolled students with >= 2 projects are awarded full experience credit
    expPts = 20;
  } else if (projectCount > 0) {
    expPts = Math.min(20, projectCount * 10);
  }

  breakdown.push({
    label: 'Experience & Portfolio',
    points: expPts,
    maxPoints: 20,
    met: expPts >= 20,
    hint:
      expPts >= 20
        ? hasWorkExp
          ? 'Work history documented'
          : 'Portfolio projects qualify'
        : isStudent
          ? 'Add at least 2 portfolio projects'
          : 'Add work experience or projects',
  });

  const total = breakdown.reduce((sum, b) => sum + b.points, 0);
  return { score: Math.min(100, Math.max(0, total)), breakdown };
}

// =============================================================================
// 3. Main Workspace Component
// =============================================================================

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

  // Sync if incoming prop changes
  if (candidateProfile !== prevPropProfile) {
    setPrevPropProfile(candidateProfile);
    if (!isDirty) {
      setProfile(candidateProfile);
    }
  }

  // 2. Resume Ingestion Drawer State (Collapsed by default!)
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
  const [draftActiveTab, setDraftActiveTab] = useState<
    'overview' | 'experience' | 'projects' | 'education' | 'skills'
  >('overview');

  // 4. Modal Management & Form State
  const [activeModal, setActiveModal] = useState<
    'none' | 'experience' | 'project' | 'education' | 'skill' | 'overview' | 'preferences'
  >('none');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  // Overview Form
  const [overviewName, setOverviewName] = useState('');
  const [overviewHeadline, setOverviewHeadline] = useState('');
  const [overviewLocation, setOverviewLocation] = useState('');
  const [overviewBio, setOverviewBio] = useState('');

  // Experience Form
  const [expRole, setExpRole] = useState('');
  const [expCompany, setExpCompany] = useState('');
  const [expStartDate, setExpStartDate] = useState('');
  const [expEndDate, setExpEndDate] = useState('');
  const [expIsCurrent, setExpIsCurrent] = useState(false);
  const [expResponsibilities, setExpResponsibilities] = useState('');
  const [expTechnologies, setExpTechnologies] = useState('');

  // Project Form
  const [projName, setProjName] = useState('');
  const [projDescription, setProjDescription] = useState('');
  const [projTechnologies, setProjTechnologies] = useState('');
  const [projRepoUrl, setProjRepoUrl] = useState('');

  // Education Form
  const [eduInstitution, setEduInstitution] = useState('');
  const [eduDegreeLevel, setEduDegreeLevel] = useState<DegreeLevel>('BACHELORS');
  const [eduField, setEduField] = useState('');
  const [eduGradDate, setEduGradDate] = useState('');
  const [eduIsEnrolled, setEduIsEnrolled] = useState(false);

  // Skill Form
  const [skillNameInput, setSkillNameInput] = useState('');
  const [skillProfScore, setSkillProfScore] = useState<number>(8.0);
  const [skillEvidenceInput, setSkillEvidenceInput] = useState('');

  // Preferences Form
  const [prefTargetRoles, setPrefTargetRoles] = useState<string[]>([]);
  const [prefNewRole, setPrefNewRole] = useState('');
  const [prefLocations, setPrefLocations] = useState<string[]>([]);
  const [prefNewLocation, setPrefNewLocation] = useState('');
  const [prefWorkModes, setPrefWorkModes] = useState<WorkMode[]>(['REMOTE']);
  const [prefVisaRequired, setPrefVisaRequired] = useState(false);
  const [prefIsEnrolled, setPrefIsEnrolled] = useState(false);
  const [prefDegree, setPrefDegree] = useState<DegreeLevel>('BACHELORS');
  const [prefExperienceMonths, setPrefExperienceMonths] = useState<number>(0);

  // Skills Filtering & Accordion State
  const [skillSearch, setSkillSearch] = useState('');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<SkillCategoryKey | 'ALL'>('ALL');
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});
  const [expandedSkillEvidenceId, setExpandedSkillEvidenceId] = useState<string | null>(null);
  const [showCompletenessDetails, setShowCompletenessDetails] = useState(false);

  // ===========================================================================
  // Career Memory & Versioned Goals State
  // ===========================================================================
  const [memories, setMemories] = useState<CandidateCareerMemoryItem[]>([]);
  const [isLoadingMemories, setIsLoadingMemories] = useState(false);
  const [memoryModal, setMemoryModal] = useState<'none' | 'add' | 'update' | 'lineage'>('none');
  const [activeMemory, setActiveMemory] = useState<CandidateCareerMemoryItem | null>(null);
  const [memoryLineage, setMemoryLineage] = useState<CandidateCareerMemoryItem[]>([]);
  const [isLoadingLineage, setIsLoadingLineage] = useState(false);

  // Add / Edit memory form state
  const [memoryTypeInput, setMemoryTypeInput] = useState<MemoryType>('CAREER_GOAL');
  const [memoryStatementInput, setMemoryStatementInput] = useState('');
  const [memoryProvenanceInput, setMemoryProvenanceInput] = useState<ProvenanceLevel>('USER_PROVIDED');
  const [memoryChangeReasonInput, setMemoryChangeReasonInput] = useState('');
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [isSavingMemory, setIsSavingMemory] = useState(false);

  const loadMemories = useCallback(async () => {
    setIsLoadingMemories(true);
    try {
      const data = await getCandidateMemories(profile.user_id, undefined, false);
      setMemories(data);
    } catch (err) {
      console.warn('Failed to load career memories:', err);
    } finally {
      setIsLoadingMemories(false);
    }
  }, [profile.user_id]);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const data = await getCandidateMemories(profile.user_id, undefined, false);
        if (!ignore) setMemories(data);
      } catch (err) {
        console.warn('Failed to load career memories:', err);
      } finally {
        if (!ignore) setIsLoadingMemories(false);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, [profile.user_id]);

  const openAddMemory = () => {
    setMemoryTypeInput('CAREER_GOAL');
    setMemoryStatementInput('');
    setMemoryProvenanceInput('USER_PROVIDED');
    setMemoryChangeReasonInput('Initial candidate profile statement');
    setMemoryError(null);
    setMemoryModal('add');
  };

  const openUpdateMemory = (mem: CandidateCareerMemoryItem) => {
    setActiveMemory(mem);
    setMemoryTypeInput(mem.memory_type);
    setMemoryStatementInput(mem.statement);
    setMemoryProvenanceInput(mem.provenance_level);
    setMemoryChangeReasonInput('');
    setMemoryError(null);
    setMemoryModal('update');
  };

  const openLineage = async (mem: CandidateCareerMemoryItem) => {
    setActiveMemory(mem);
    setIsLoadingLineage(true);
    setMemoryModal('lineage');
    try {
      const history = await getMemoryLineage(profile.user_id, mem.memory_id);
      setMemoryLineage(history.version_history || [mem]);
    } catch (err) {
      console.warn('Failed to fetch memory lineage:', err);
      setMemoryLineage([mem]);
    } finally {
      setIsLoadingLineage(false);
    }
  };

  const handleSaveNewMemory = async () => {
    if (!memoryStatementInput.trim()) {
      setMemoryError('Please enter a statement or career goal.');
      return;
    }
    setIsSavingMemory(true);
    setMemoryError(null);
    try {
      await createCandidateMemory(profile.user_id, {
        memory_type: memoryTypeInput,
        statement: memoryStatementInput.trim(),
        provenance_level: memoryProvenanceInput,
        confidence_score: 1.0,
      });
      await loadMemories();
      setMemoryModal('none');
    } catch (err) {
      setMemoryError(err instanceof Error ? err.message : 'Failed to record memory');
    } finally {
      setIsSavingMemory(false);
    }
  };

  const handleSaveUpdatedMemory = async () => {
    if (!activeMemory) return;
    if (!memoryStatementInput.trim()) {
      setMemoryError('Statement cannot be blank.');
      return;
    }
    if (!memoryChangeReasonInput.trim()) {
      setMemoryError('Please specify the reason for this change to preserve provenance.');
      return;
    }
    setIsSavingMemory(true);
    setMemoryError(null);
    try {
      await updateCandidateMemory(profile.user_id, activeMemory.memory_id, {
        statement: memoryStatementInput.trim(),
        change_reason: memoryChangeReasonInput.trim(),
        provenance_level: memoryProvenanceInput,
      });
      await loadMemories();
      setMemoryModal('none');
    } catch (err) {
      setMemoryError(err instanceof Error ? err.message : 'Failed to update memory');
    } finally {
      setIsSavingMemory(false);
    }
  };

  const handleDeleteMemory = async (mem: CandidateCareerMemoryItem) => {
    try {
      await deactivateCandidateMemory(profile.user_id, mem.memory_id);
      await loadMemories();
    } catch (err) {
      console.error('Failed to deactivate memory:', err);
    }
  };

  // ===========================================================================
  // Memoized Skill Groups & Completeness
  // ===========================================================================

  const categorizedSkills = useMemo(() => {
    const groups: Record<SkillCategoryKey, AssessedSkill[]> = {
      languages: [],
      backend: [],
      frontend: [],
      databases: [],
      ai_ml: [],
      devops_cloud: [],
      other: [],
    };

    profile.assessed_skills.forEach((skill) => {
      const cat = categorizeSkill(skill.skill_name);
      groups[cat].push(skill);
    });

    return groups;
  }, [profile.assessed_skills]);

  const completeness = useMemo(() => {
    return calculateProfileCompleteness(profile);
  }, [profile]);

  // ===========================================================================
  // Handlers: Save Profile & Resume Ingestion
  // ===========================================================================

  async function handleSaveProfile() {
    setIsSaving(true);
    setSaveMessage(null);
    setSaveError(null);

    try {
      const updated = await updateCandidateProfile(profile.user_id, profile);
      setProfile(updated);
      setIsDirty(false);
      setSaveMessage('Profile changes saved successfully.');
      onProfileUpdated?.(updated);
      setTimeout(() => setSaveMessage(null), 4000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save profile changes.');
    } finally {
      setIsSaving(false);
    }
  }

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
      await new Promise((r) => setTimeout(r, 300));

      setExtractStage(3);
      setExtractStageText('Extracting technical competencies & verifiable project evidence...');

      const req: CandidateProfilingRequest = {
        resume_text: textToExtract,
        user_id: profile.user_id,
        save_to_repository: false,
      };

      setExtractStage(4);
      setExtractStageText('Structuring projects, academic qualifications, and career goals...');
      const response = await extractCandidateProfile(req);

      setExtractStage(5);
      setExtractStageText('Validating profile completeness and readiness...');
      await new Promise((r) => setTimeout(r, 200));

      setDraftProfile(response.extracted_profile);
      setShowDraftModal(true);
      setShowUploadDrawer(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to extract resume content.';
      setExtractError(msg);
    } finally {
      setIsExtracting(false);
      setExtractStage(0);
      setExtractStageText('');
    }
  }

  async function handleApplyDraft() {
    if (!draftProfile) return;
    setIsSaving(true);
    try {
      const updated = await updateCandidateProfile(draftProfile.user_id, draftProfile);
      setProfile(updated);
      setIsDirty(false);
      setShowDraftModal(false);
      setDraftProfile(null);
      setSaveMessage('Resume draft applied and profile saved successfully!');
      onProfileUpdated?.(updated);
      setTimeout(() => setSaveMessage(null), 4000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save updated profile.');
    } finally {
      setIsSaving(false);
    }
  }

  // ===========================================================================
  // Handlers: Profile Overview CRUD
  // ===========================================================================

  const openEditOverview = () => {
    setOverviewName(profile.display_name || candidateName || '');
    setOverviewHeadline(profile.headline || '');
    setOverviewLocation(profile.location || '');
    setOverviewBio(profile.bio || '');
    setActiveModal('overview');
  };

  const handleSaveOverview = () => {
    setProfile((prev) => ({
      ...prev,
      display_name: overviewName.trim() || prev.display_name,
      headline: overviewHeadline.trim() || null,
      location: overviewLocation.trim() || null,
      bio: overviewBio.trim() || null,
    }));
    setIsDirty(true);
    setActiveModal('none');
  };

  // ===========================================================================
  // Handlers: Work Experience CRUD
  // ===========================================================================

  const openAddExperience = () => {
    setEditingIndex(null);
    setExpRole('');
    setExpCompany('');
    setExpStartDate('');
    setExpEndDate('');
    setExpIsCurrent(false);
    setExpResponsibilities('');
    setExpTechnologies('');
    setActiveModal('experience');
  };

  const openEditExperience = (idx: number) => {
    const exp = profile.work_experiences?.[idx];
    if (!exp) return;
    setEditingIndex(idx);
    setExpRole(exp.role_title);
    setExpCompany(exp.company_name);
    setExpStartDate(exp.start_date || '');
    setExpEndDate(exp.end_date || '');
    setExpIsCurrent(exp.is_current);
    setExpResponsibilities(exp.responsibilities.join('\n'));
    setExpTechnologies(exp.technologies_used.join(', '));
    setActiveModal('experience');
  };

  const handleSaveExperience = () => {
    if (!expRole.trim() || !expCompany.trim()) return;

    const newExp: ExtractedWorkExperience = {
      role_title: expRole.trim(),
      company_name: expCompany.trim(),
      start_date: expStartDate.trim() || null,
      end_date: expIsCurrent ? null : expEndDate.trim() || null,
      is_current: expIsCurrent,
      responsibilities: expResponsibilities
        .split('\n')
        .map((r) => r.trim())
        .filter(Boolean),
      technologies_used: expTechnologies
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    };

    setProfile((prev) => {
      const existing = [...(prev.work_experiences || [])];
      if (editingIndex !== null) {
        existing[editingIndex] = newExp;
      } else {
        existing.unshift(newExp);
      }
      return { ...prev, work_experiences: existing };
    });

    setIsDirty(true);
    setActiveModal('none');
  };

  const handleDeleteExperience = (idx: number) => {
    setProfile((prev) => ({
      ...prev,
      work_experiences: (prev.work_experiences || []).filter((_, i) => i !== idx),
    }));
    setIsDirty(true);
  };

  // ===========================================================================
  // Handlers: Projects CRUD
  // ===========================================================================

  const openAddProject = () => {
    setEditingIndex(null);
    setProjName('');
    setProjDescription('');
    setProjTechnologies('');
    setProjRepoUrl('');
    setActiveModal('project');
  };

  const openEditProject = (idx: number) => {
    const proj = profile.projects?.[idx];
    if (!proj) return;
    setEditingIndex(idx);
    setProjName(proj.project_name);
    setProjDescription(proj.description);
    setProjTechnologies(proj.technologies.join(', '));
    setProjRepoUrl(proj.repository_url || '');
    setActiveModal('project');
  };

  const handleSaveProject = () => {
    if (!projName.trim() || !projDescription.trim()) return;

    const newProj: ExtractedProject = {
      project_name: projName.trim(),
      description: projDescription.trim(),
      technologies: projTechnologies
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      repository_url: projRepoUrl.trim() || null,
    };

    setProfile((prev) => {
      const existing = [...(prev.projects || [])];
      if (editingIndex !== null) {
        existing[editingIndex] = newProj;
      } else {
        existing.unshift(newProj);
      }
      return { ...prev, projects: existing };
    });

    setIsDirty(true);
    setActiveModal('none');
  };

  const handleDeleteProject = (idx: number) => {
    setProfile((prev) => ({
      ...prev,
      projects: (prev.projects || []).filter((_, i) => i !== idx),
    }));
    setIsDirty(true);
  };

  // ===========================================================================
  // Handlers: Education CRUD
  // ===========================================================================

  const openAddEducation = () => {
    setEditingIndex(null);
    setEduInstitution('');
    setEduDegreeLevel('BACHELORS');
    setEduField('');
    setEduGradDate('');
    setEduIsEnrolled(false);
    setActiveModal('education');
  };

  const openEditEducation = (idx: number) => {
    const edu = profile.education?.[idx];
    if (!edu) return;
    setEditingIndex(idx);
    setEduInstitution(edu.institution_name);
    setEduDegreeLevel(edu.degree_level);
    setEduField(edu.field_of_study || '');
    setEduGradDate(edu.graduation_date || '');
    setEduIsEnrolled(edu.is_enrolled);
    setActiveModal('education');
  };

  const handleSaveEducation = () => {
    if (!eduInstitution.trim()) return;

    const newEdu: ExtractedEducation = {
      institution_name: eduInstitution.trim(),
      degree_level: eduDegreeLevel,
      field_of_study: eduField.trim() || null,
      graduation_date: eduGradDate.trim() || null,
      is_enrolled: eduIsEnrolled,
    };

    setProfile((prev) => {
      const existing = [...(prev.education || [])];
      if (editingIndex !== null) {
        existing[editingIndex] = newEdu;
      } else {
        existing.push(newEdu);
      }
      return {
        ...prev,
        education: existing,
        eligibility_constraints: {
          ...prev.eligibility_constraints,
          highest_degree_level: newEdu.degree_level,
          is_currently_enrolled_student: newEdu.is_enrolled,
        },
      };
    });

    setIsDirty(true);
    setActiveModal('none');
  };

  const handleDeleteEducation = (idx: number) => {
    setProfile((prev) => ({
      ...prev,
      education: (prev.education || []).filter((_, i) => i !== idx),
    }));
    setIsDirty(true);
  };

  // ===========================================================================
  // Handlers: Skills CRUD (Allows Manual Addition with No Evidence Required!)
  // ===========================================================================

  const openAddSkill = () => {
    setEditingIndex(null);
    setSkillNameInput('');
    setSkillProfScore(8.0);
    setSkillEvidenceInput('');
    setActiveModal('skill');
  };

  const openEditSkill = (realIdx: number) => {
    const skill = profile.assessed_skills[realIdx];
    if (!skill) return;
    setEditingIndex(realIdx);
    setSkillNameInput(skill.skill_name);
    setSkillProfScore(skill.proficiency_score);
    setSkillEvidenceInput(skill.evidence_records[0]?.extracted_snippet || '');
    setActiveModal('skill');
  };

  const handleSaveSkill = () => {
    if (!skillNameInput.trim()) return;

    const trimmedName = skillNameInput.trim();
    const canonicalId = `skill_${trimmedName.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`;

    let evidenceRecords: EvidenceRecord[] = [];
    if (skillEvidenceInput.trim()) {
      evidenceRecords = [
        {
          evidence_id: `ev_${Date.now()}`,
          source_type: 'SELF_REPORTED_UNVERIFIED',
          extracted_snippet: skillEvidenceInput.trim(),
          observed_at: new Date().toISOString(),
          verifiability_weight: 0.9,
        },
      ];
    }

    setProfile((prev) => {
      const existing = [...prev.assessed_skills];
      if (editingIndex !== null) {
        const old = existing[editingIndex];
        existing[editingIndex] = {
          ...old,
          skill_name: trimmedName,
          proficiency_score: skillProfScore,
          evidence_records: evidenceRecords.length > 0 ? evidenceRecords : old.evidence_records,
        };
      } else {
        const newSkill: AssessedSkill = {
          canonical_skill_id: canonicalId,
          skill_name: trimmedName,
          proficiency_score: skillProfScore,
          confidence_score: 0.9,
          evidence_records: evidenceRecords,
        };
        existing.unshift(newSkill);
      }
      return { ...prev, assessed_skills: existing };
    });

    setIsDirty(true);
    setActiveModal('none');
  };

  const handleDeleteSkill = (realIdx: number) => {
    setProfile((prev) => ({
      ...prev,
      assessed_skills: prev.assessed_skills.filter((_, i) => i !== realIdx),
    }));
    setIsDirty(true);
  };

  // ===========================================================================
  // Handlers: Preferences CRUD
  // ===========================================================================

  const openEditPreferences = () => {
    setPrefTargetRoles(profile.target_career_paths.map((p) => p.title));
    setPrefNewRole('');
    setPrefLocations(profile.eligibility_constraints.preferred_locations || []);
    setPrefNewLocation('');
    setPrefWorkModes(profile.eligibility_constraints.allowed_work_modes || ['REMOTE']);
    setPrefVisaRequired(profile.eligibility_constraints.requires_visa_sponsorship || false);
    setPrefIsEnrolled(profile.eligibility_constraints.is_currently_enrolled_student || false);
    setPrefDegree(profile.eligibility_constraints.highest_degree_level || 'BACHELORS');
    setPrefExperienceMonths(profile.eligibility_constraints.total_full_time_experience_months || 0);
    setActiveModal('preferences');
  };

  const handleSavePreferences = () => {
    setProfile((prev) => ({
      ...prev,
      target_career_paths: prefTargetRoles.map((role) => ({
        occupation_code: `15-1252.00`,
        title: role,
        relationship_type: 'TARGET',
        adjacency_similarity: 1.0,
        missing_core_skill_ids: [],
      })),
      eligibility_constraints: {
        ...prev.eligibility_constraints,
        preferred_locations: prefLocations,
        allowed_work_modes: prefWorkModes,
        requires_visa_sponsorship: prefVisaRequired,
        is_currently_enrolled_student: prefIsEnrolled,
        highest_degree_level: prefDegree,
        total_full_time_experience_months: prefExperienceMonths,
      },
    }));
    setIsDirty(true);
    setActiveModal('none');
  };

  // Toggle category collapse
  const toggleCategoryCollapse = (catKey: string) => {
    setCollapsedCategories((prev) => ({
      ...prev,
      [catKey]: !prev[catKey],
    }));
  };

  const setAllCategoriesCollapsed = (collapsed: boolean) => {
    const updated: Record<string, boolean> = {};
    SKILL_CATEGORIES.forEach((c) => {
      updated[c.key] = collapsed;
    });
    setCollapsedCategories(updated);
  };

  // Filter skills by search and selectedCategoryFilter
  const filteredCategories = useMemo(() => {
    const q = skillSearch.toLowerCase().trim();
    return SKILL_CATEGORIES.map((catDef) => {
      let skills = categorizedSkills[catDef.key] || [];
      if (q) {
        skills = skills.filter((s) => s.skill_name.toLowerCase().includes(q));
      }
      return {
        ...catDef,
        skills,
        count: skills.length,
        totalInCat: (categorizedSkills[catDef.key] || []).length,
      };
    }).filter((cat) => {
      if (selectedCategoryFilter !== 'ALL' && cat.key !== selectedCategoryFilter) {
        return false;
      }
      // If searching, hide empty categories
      if (skillSearch && cat.skills.length === 0) {
        return false;
      }
      return true;
    });
  }, [categorizedSkills, skillSearch, selectedCategoryFilter]);

  // Derived Display Values
  const displayName = profile.display_name || candidateName || 'Candidate Profile';
  const targetRole = profile.target_career_paths[0]?.title || 'Software Engineer';
  const initials = displayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  const expMonths = profile.eligibility_constraints.total_full_time_experience_months;
  const expDisplay =
    expMonths >= 12
      ? `${(expMonths / 12).toFixed(1)} yrs exp`
      : `${expMonths} mos exp`;

  // ===========================================================================
  // RENDER
  // ===========================================================================

  return (
    <div className="space-y-6 pb-20 max-w-6xl mx-auto px-4 sm:px-6">
      {/* 1. Header Navigation & Sticky Actions Bar */}
      <div className="sticky top-0 z-30 py-3.5 bg-zinc-50/90 dark:bg-zinc-950/90 backdrop-blur-md border-b border-zinc-200/80 dark:border-zinc-800/80 flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={() => onNavigateTab('discover')}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer shadow-2xs"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
          <span>Back to Opportunities</span>
        </button>

        <div className="flex items-center gap-2.5 flex-wrap">
          {isDirty && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-xs font-medium text-amber-700 dark:text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              Unsaved changes
            </span>
          )}

          {saveMessage && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {saveMessage}
            </span>
          )}

          {saveError && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-xs font-medium text-red-700 dark:text-red-400">
              <AlertCircle className="w-3.5 h-3.5" />
              {saveError}
            </span>
          )}

          {/* Upload Button: Keeps upload panel collapsed by default, opens only on click */}
          <button
            onClick={() => setShowUploadDrawer(!showUploadDrawer)}
            className={`px-3.5 py-1.5 rounded-lg border text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs ${
              showUploadDrawer
                ? 'bg-teal-600 border-teal-600 text-white'
                : 'border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-200 hover:border-teal-500'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload or Replace Resume</span>
          </button>

          {/* Primary Save Button */}
          <button
            onClick={handleSaveProfile}
            disabled={isSaving || !isDirty}
            className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-40 transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer"
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

      {/* 2. Resume Ingestion & Parsing Drawer (Collapsed by default, opens on user demand) */}
      {showUploadDrawer && (
        <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-teal-200 dark:border-teal-900/80 shadow-lg space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400">
                <Upload className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                  Upload or Replace Resume Document
                </h3>
                <p className="text-xs text-zinc-500">
                  Supports PDF, DOCX, DOC, TXT, and Markdown files.
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowUploadDrawer(false)}
              className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {extractError && (
            <div className="p-3.5 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-400 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{extractError}</span>
            </div>
          )}

          {/* Multi-stage Progress Stepper */}
          {isExtracting && (
            <div className="p-4 rounded-xl bg-teal-50/70 dark:bg-teal-950/30 border border-teal-200/80 dark:border-teal-800 space-y-2.5">
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
            className="p-8 border-2 border-dashed border-zinc-300 dark:border-zinc-700 hover:border-teal-500 dark:hover:border-teal-400 rounded-xl bg-zinc-50/50 dark:bg-zinc-800/40 text-center cursor-pointer transition-colors"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt,.md"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="flex flex-col items-center justify-center gap-2 text-xs text-zinc-600 dark:text-zinc-300">
              <Upload className="w-7 h-7 text-teal-600 dark:text-teal-400 mb-1" />
              <span className="font-bold text-sm text-zinc-800 dark:text-zinc-200">
                {uploadedFile ? uploadedFile.name : 'Select or drop your resume document'}
              </span>
              <span className="text-zinc-500 text-xs">
                {uploadedFile
                  ? `${(uploadedFile.size / 1024).toFixed(1)} KB — Click to change file`
                  : 'PDF, DOCX, DOC, or TXT up to 10MB'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <button
              onClick={() => setShowUploadDrawer(false)}
              className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleExtractResume}
              disabled={isExtracting || (!uploadedFile && !rawExtractText.trim())}
              className="px-4 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold disabled:opacity-50 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
            >
              {isExtracting ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing...</span>
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

      {/* 3. Hero Card: Professional Career Profile Header */}
      <div className="p-4 sm:p-8 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6 min-w-0">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 min-w-0">
          <div className="flex items-start gap-3 sm:gap-5 min-w-0 flex-1">
            {/* Avatar Initials Badge */}
            <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-teal-500 to-emerald-700 text-white flex items-center justify-center text-lg sm:text-2xl font-bold font-mono shadow-md shrink-0">
              {initials}
            </div>

            <div className="space-y-2 min-w-0 flex-1">
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap min-w-0">
                <h1 className="text-xl sm:text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100 break-all min-w-0">
                  {displayName}
                </h1>
                <button
                  onClick={openEditOverview}
                  className="px-2.5 py-1 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-teal-500 bg-zinc-50 dark:bg-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs shrink-0"
                  title="Edit profile summary and contact details"
                >
                  <Edit3 className="w-3 h-3" />
                  <span>Edit Profile</span>
                </button>
              </div>

              <p className="text-sm font-semibold text-teal-600 dark:text-teal-400 break-words">
                {profile.headline || targetRole}
              </p>

              <div className="flex items-center gap-3 sm:gap-4 text-xs text-zinc-600 dark:text-zinc-400 flex-wrap pt-0.5">
                {profile.location && (
                  <span className="flex items-center gap-1.5 shrink-0">
                    <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                    <span>{profile.location}</span>
                  </span>
                )}
                <span className="flex items-center gap-1.5 font-mono min-w-0 max-w-full">
                  <User className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span className="truncate">ID: {profile.user_id}</span>
                </span>
                <span className="flex items-center gap-1.5 shrink-0">
                  <Briefcase className="w-3.5 h-3.5 text-zinc-400" />
                  <span>{expDisplay}</span>
                </span>
                {profile.eligibility_constraints.is_currently_enrolled_student && (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 font-medium shrink-0">
                    Currently Enrolled Student
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Profile Completeness Score Card */}
          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/80 dark:border-zinc-800 shrink-0 w-full md:w-64 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 uppercase tracking-wider font-mono">
                Completeness
              </span>
              <button
                onClick={() => setShowCompletenessDetails(!showCompletenessDetails)}
                className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 cursor-pointer font-medium"
              >
                <span>{completeness.score}%</span>
                {showCompletenessDetails ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-zinc-200 dark:bg-zinc-700 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  completeness.score >= 80
                    ? 'bg-emerald-500'
                    : completeness.score >= 50
                      ? 'bg-teal-500'
                      : 'bg-amber-500'
                }`}
                style={{ width: `${completeness.score}%` }}
              />
            </div>

            <p className="text-[11px] text-zinc-500">
              {completeness.score === 100
                ? 'Profile fully verified for matching'
                : 'Complete all sections for high-confidence matching'}
            </p>

            {/* Collapsible Details Drawer */}
            {showCompletenessDetails && (
              <div className="pt-2 border-t border-zinc-200 dark:border-zinc-700 space-y-1.5 animate-in fade-in duration-150">
                {completeness.breakdown.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <span className="text-zinc-600 dark:text-zinc-400 flex items-center gap-1.5">
                      {item.met ? (
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                      ) : (
                        <span className="w-3 h-3 rounded-full border border-zinc-400 inline-block" />
                      )}
                      <span>{item.label}</span>
                    </span>
                    <span className="font-mono text-[11px] text-zinc-500">
                      {item.points}/{item.maxPoints}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bio / Executive Summary */}
        {profile.bio && (
          <div className="p-4 rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
            {profile.bio}
          </div>
        )}

        {/* Quick Highlights Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800 space-y-0.5">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Highest Degree
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate block text-sm">
              {profile.eligibility_constraints.highest_degree_level}
            </span>
            <span className="text-[11px] text-zinc-500 block">
              {profile.eligibility_constraints.is_currently_enrolled_student
                ? 'Currently Enrolled'
                : 'Graduated'}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800 space-y-0.5">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Work Experience
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block text-sm">
              {profile.work_experiences?.length || 0} Positions
            </span>
            <span className="text-[11px] text-zinc-500 block">{expDisplay}</span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800 space-y-0.5">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Projects & Code
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 block text-sm">
              {profile.projects?.length || 0} Projects
            </span>
            <span className="text-[11px] text-zinc-500 block">With tech stack evidence</span>
          </div>

          <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200/60 dark:border-zinc-800 space-y-0.5">
            <span className="text-[10px] text-zinc-400 uppercase tracking-wider block font-mono">
              Work Preferences
            </span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate block text-sm">
              {profile.eligibility_constraints.allowed_work_modes.join(', ')}
            </span>
            <span className="text-[11px] text-zinc-500 block truncate">
              {profile.eligibility_constraints.requires_visa_sponsorship
                ? 'Visa Required'
                : 'No Visa Needed'}
            </span>
          </div>
        </div>
      </div>

      {/* 4. Work Experience & Internships Section */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Work Experience & Professional History</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.work_experiences?.length || 0})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Employment roles, internships, and engineering impact.
            </p>
          </div>

          <button
            onClick={openAddExperience}
            className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Position</span>
          </button>
        </div>

        {(!profile.work_experiences || profile.work_experiences.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <Briefcase className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              No work experience records recorded yet.
            </p>
            <p className="text-xs text-zinc-400">
              Students and fresh graduates can highlight portfolio projects and coursework.
            </p>
            <button
              onClick={openAddExperience}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer pt-1 block mx-auto"
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
                {/* Information Hierarchy: 1. Role Title, 2. Company, 3. Period */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                      {exp.role_title}
                    </h3>
                    <div className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400 flex-wrap">
                      <span className="font-semibold text-teal-700 dark:text-teal-400 flex items-center gap-1 text-sm">
                        <Building2 className="w-3.5 h-3.5" />
                        {exp.company_name}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1 font-mono text-zinc-500">
                        <Calendar className="w-3.5 h-3.5 text-zinc-400" />
                        {exp.start_date || 'Past'} – {exp.is_current ? 'Present' : exp.end_date || 'Past'}
                      </span>
                      {exp.is_current && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 font-semibold">
                          Current Position
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Discoverable, Visible Action Buttons */}
                  <div className="flex items-center gap-2 shrink-0 pt-1 sm:pt-0">
                    <button
                      onClick={() => openEditExperience(idx)}
                      className="px-2.5 py-1 rounded-md border border-zinc-200 dark:border-zinc-700 hover:border-teal-500 bg-white dark:bg-zinc-900 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                      title="Edit experience entry"
                    >
                      <Edit3 className="w-3 h-3" />
                      <span>Edit</span>
                    </button>
                    <button
                      onClick={() => handleDeleteExperience(idx)}
                      className="px-2.5 py-1 rounded-md border border-red-200/80 dark:border-red-900/60 hover:bg-red-50 dark:hover:bg-red-950/40 text-xs font-medium text-red-600 dark:text-red-400 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                      title="Delete experience entry"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>

                {/* Key Responsibilities */}
                {exp.responsibilities && exp.responsibilities.length > 0 && (
                  <ul className="space-y-1.5 text-sm text-zinc-700 dark:text-zinc-300 list-disc list-inside leading-relaxed pt-1">
                    {exp.responsibilities.map((r, rIdx) => (
                      <li key={rIdx}>{r}</li>
                    ))}
                  </ul>
                )}

                {/* Tech Tags */}
                {exp.technologies_used && exp.technologies_used.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-zinc-200/60 dark:border-zinc-700/60">
                    <span className="text-[11px] text-zinc-400 font-mono uppercase tracking-wider mr-1">
                      Technologies:
                    </span>
                    {exp.technologies_used.map((tech, tIdx) => (
                      <span
                        key={tIdx}
                        className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-xs font-medium text-zinc-700 dark:text-zinc-300"
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

      {/* 5. Projects & Engineering Portfolio Section */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Projects & Engineering Artifacts</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.projects?.length || 0})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Applications, systems architecture, and demonstrated codebases.
            </p>
          </div>

          <button
            onClick={openAddProject}
            className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Project</span>
          </button>
        </div>

        {(!profile.projects || profile.projects.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <FolderGit2 className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              No portfolio projects recorded yet.
            </p>
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
                    <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
                      <span>{proj.project_name}</span>
                      {proj.repository_url && (
                        <a
                          href={proj.repository_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-teal-600 hover:text-teal-500 dark:text-teal-400 inline-flex items-center"
                          title="Open external project link"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </h3>

                    {/* Discoverable, Visible Action Buttons */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => openEditProject(idx)}
                        className="px-2 py-1 rounded-md border border-zinc-200 dark:border-zinc-700 hover:border-teal-500 bg-white dark:bg-zinc-900 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors flex items-center gap-1 cursor-pointer shadow-2xs"
                        title="Edit project"
                      >
                        <Edit3 className="w-3 h-3" />
                        <span>Edit</span>
                      </button>
                      <button
                        onClick={() => handleDeleteProject(idx)}
                        className="px-2 py-1 rounded-md border border-red-200/80 dark:border-red-900/60 hover:bg-red-50 dark:hover:bg-red-950/40 text-xs font-medium text-red-600 dark:text-red-400 transition-colors flex items-center gap-1 cursor-pointer shadow-2xs"
                        title="Delete project"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>

                  <p className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
                    {proj.description}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-zinc-200/60 dark:border-zinc-700/60">
                  {proj.technologies && proj.technologies.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {proj.technologies.map((t, tIdx) => (
                        <span
                          key={tIdx}
                          className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-xs font-medium text-zinc-700 dark:text-zinc-300"
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
                      rel="noreferrer"
                      className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline inline-flex items-center gap-1 pt-1"
                    >
                      <span>View Repository / Live Demo</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 6. Education & Academic Credentials Section */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <GraduationCap className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Education & Credentials</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.education?.length || 0})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Academic degrees, institutions, and enrollment status.
            </p>
          </div>

          <button
            onClick={openAddEducation}
            className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Education</span>
          </button>
        </div>

        {(!profile.education || profile.education.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <GraduationCap className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              No education records listed yet.
            </p>
            <button
              onClick={openAddEducation}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
            >
              + Add academic history
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {profile.education.map((edu, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                      {edu.institution_name}
                    </h3>
                    {edu.is_enrolled ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 font-semibold">
                        Currently Enrolled Student
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 font-semibold">
                        Graduated
                      </span>
                    )}
                  </div>

                  <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                    {edu.degree_level}
                    {edu.field_of_study ? ` in ${edu.field_of_study}` : ''}
                  </p>

                  {edu.graduation_date && (
                    <span className="text-xs text-zinc-500 font-mono block">
                      Graduation: {edu.graduation_date}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => openEditEducation(idx)}
                    className="px-2.5 py-1 rounded-md border border-zinc-200 dark:border-zinc-700 hover:border-teal-500 bg-white dark:bg-zinc-900 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                    title="Edit education"
                  >
                    <Edit3 className="w-3 h-3" />
                    <span>Edit</span>
                  </button>
                  <button
                    onClick={() => handleDeleteEducation(idx)}
                    className="px-2.5 py-1 rounded-md border border-red-200/80 dark:border-red-900/60 hover:bg-red-50 dark:hover:bg-red-950/40 text-xs font-medium text-red-600 dark:text-red-400 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                    title="Delete education"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 7. Skills & Demonstrated Evidence (Categorized Accordion) */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Code2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Skills & Demonstrated Evidence</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({profile.assessed_skills.length})
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Organized into competencies with verbatim excerpts from resume and project evidence.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search competencies..."
                value={skillSearch}
                onChange={(e) => setSkillSearch(e.target.value)}
                className="pl-8 pr-7 py-1.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-xs w-48 focus:outline-hidden focus:ring-1 focus:ring-teal-500"
              />
              {skillSearch && (
                <button
                  onClick={() => setSkillSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 cursor-pointer"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Expand / Collapse All Toggle */}
            <button
              onClick={() => {
                const anyCollapsed = Object.values(collapsedCategories).some(Boolean);
                setAllCategoriesCollapsed(!anyCollapsed);
              }}
              className="px-2.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
              title="Expand or collapse all skill categories"
            >
              Toggle All
            </button>

            {/* Prominent Add Skill Button (Allows manual entry without resume/evidence) */}
            <button
              onClick={openAddSkill}
              className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Skill</span>
            </button>
          </div>
        </div>

        {/* Category Filter Pills (Compact Overview Bar) */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1 text-xs">
          <button
            onClick={() => setSelectedCategoryFilter('ALL')}
            className={`px-3 py-2 sm:py-1.5 rounded-lg font-semibold whitespace-nowrap transition-colors cursor-pointer shrink-0 min-h-[38px] ${
              selectedCategoryFilter === 'ALL'
                ? 'bg-teal-600 text-white shadow-2xs'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700'
            }`}
          >
            All Categories ({profile.assessed_skills.length})
          </button>

          {SKILL_CATEGORIES.map((cat) => {
            const count = (categorizedSkills[cat.key] || []).length;
            if (count === 0 && !skillSearch) return null;
            const Icon = cat.icon;
            const isSelected = selectedCategoryFilter === cat.key;

            return (
              <button
                key={cat.key}
                onClick={() => setSelectedCategoryFilter(cat.key)}
                className={`px-2.5 py-2 sm:py-1.5 rounded-lg font-medium whitespace-nowrap flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 min-h-[38px] ${
                  isSelected
                    ? 'bg-teal-600 text-white shadow-2xs'
                    : 'bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200/70 dark:border-zinc-700/70 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{cat.title}</span>
                <span className="font-mono text-[11px] opacity-80">({count})</span>
              </button>
            );
          })}
        </div>

        {/* Categorized Skills Accordions */}
        {filteredCategories.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2">
            <Code2 className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {skillSearch
                ? `No skills match "${skillSearch}".`
                : 'No skills found in this category.'}
            </p>
            <button
              onClick={openAddSkill}
              className="text-xs text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer"
            >
              + Add a skill manually
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredCategories.map((cat) => {
              const isCollapsed = Boolean(collapsedCategories[cat.key]);
              const Icon = cat.icon;

              return (
                <div
                  key={cat.key}
                  className="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-2xs bg-white dark:bg-zinc-900"
                >
                  {/* Category Header Accordion Bar */}
                  <div
                    onClick={() => toggleCategoryCollapse(cat.key)}
                    className="p-3.5 sm:px-4 bg-zinc-50 dark:bg-zinc-800/50 hover:bg-zinc-100/80 dark:hover:bg-zinc-800 flex items-center justify-between gap-3 cursor-pointer select-none transition-colors border-b border-zinc-200/60 dark:border-zinc-800"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`p-1.5 rounded-md border ${cat.accentColor}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <h3 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                        {cat.title}
                      </h3>
                      <span className="px-2 py-0.5 rounded-full text-xs font-mono font-semibold bg-zinc-200/70 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300">
                        {cat.count}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-zinc-400 font-mono hidden sm:inline">
                        {isCollapsed ? 'Click to expand' : 'Click to collapse'}
                      </span>
                      {isCollapsed ? (
                        <ChevronDown className="w-4 h-4 text-zinc-400" />
                      ) : (
                        <ChevronUp className="w-4 h-4 text-zinc-400" />
                      )}
                    </div>
                  </div>

                  {/* Skills Grid within Category */}
                  {!isCollapsed && (
                    <div className="p-4 bg-white dark:bg-zinc-900/60">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {cat.skills.map((skill) => {
                          const realIdx = profile.assessed_skills.findIndex(
                            (s) => s.canonical_skill_id === skill.canonical_skill_id
                          );
                          const isEvidenceExpanded =
                            expandedSkillEvidenceId === skill.canonical_skill_id;
                          const hasEvidence =
                            skill.evidence_records && skill.evidence_records.length > 0;

                          return (
                            <div
                              key={skill.canonical_skill_id}
                              className="p-3.5 rounded-xl bg-zinc-50/80 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors space-y-2.5"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                                      {skill.skill_name}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-bold bg-teal-50 dark:bg-teal-950/80 text-teal-700 dark:text-teal-400 border border-teal-200 dark:border-teal-800">
                                      {skill.proficiency_score.toFixed(1)} / 10
                                    </span>
                                    {hasEvidence ? (
                                      <span className="text-[10px] text-zinc-500 font-mono">
                                        {skill.evidence_records.length} quote
                                        {skill.evidence_records.length > 1 ? 's' : ''}
                                      </span>
                                    ) : (
                                      <span className="text-[10px] text-zinc-400 font-mono">
                                        Self-reported
                                      </span>
                                    )}
                                  </div>
                                </div>

                                {/* Visible Actions: Edit, Delete, Evidence toggle */}
                                <div className="flex items-center gap-1 shrink-0">
                                  <button
                                    onClick={() => openEditSkill(realIdx)}
                                    className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-zinc-500 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-zinc-200/60 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                                    title="Edit skill proficiency"
                                  >
                                    <Edit3 className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleDeleteSkill(realIdx)}
                                    className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg text-zinc-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors cursor-pointer"
                                    title="Delete skill"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </div>

                              {/* Proficiency Mini Bar */}
                              <div className="w-full bg-zinc-200 dark:bg-zinc-700 h-1.5 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-teal-500 rounded-full"
                                  style={{
                                    width: `${(skill.proficiency_score / 10) * 100}%`,
                                  }}
                                />
                              </div>

                              {/* Verbatim Excerpt Drawer / Quote Preview */}
                              {hasEvidence && (
                                <div className="pt-1">
                                  <button
                                    onClick={() =>
                                      setExpandedSkillEvidenceId(
                                        isEvidenceExpanded
                                          ? null
                                          : skill.canonical_skill_id
                                      )
                                    }
                                    className="text-[11px] text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 cursor-pointer font-medium"
                                  >
                                    <span>
                                      {isEvidenceExpanded
                                        ? 'Hide verbatim excerpt'
                                        : 'View verbatim excerpt'}
                                    </span>
                                    {isEvidenceExpanded ? (
                                      <ChevronUp className="w-3 h-3" />
                                    ) : (
                                      <ChevronDown className="w-3 h-3" />
                                    )}
                                  </button>

                                  {isEvidenceExpanded && (
                                    <div className="mt-2 p-2.5 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700/80 text-xs text-zinc-700 dark:text-zinc-300 italic space-y-1 animate-in fade-in duration-150">
                                      <p>&ldquo;{skill.evidence_records[0].extracted_snippet}&rdquo;</p>
                                      <span className="text-[10px] text-zinc-400 font-mono not-italic block">
                                        Source: {skill.evidence_records[0].source_type}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 8. Career Direction & Eligibility Constraints */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Career Direction & Work Preferences</span>
            </h2>
            <p className="text-xs text-zinc-500">
              Deterministic gates used to filter opportunities without AI guesswork.
            </p>
          </div>

          <button
            onClick={openEditPreferences}
            className="px-3.5 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:border-teal-500 bg-white dark:bg-zinc-900 text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:text-teal-600 dark:hover:text-teal-400 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs self-start sm:self-auto"
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
                  className="px-2.5 py-1 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 font-semibold text-zinc-800 dark:text-zinc-200"
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
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1 text-sm">
              {profile.eligibility_constraints.allowed_work_modes.join(', ')}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Target Locations
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1 text-sm truncate">
              {profile.eligibility_constraints.preferred_locations.join(', ') || 'Any Location / Remote'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Visa Sponsorship
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1 text-sm">
              {profile.eligibility_constraints.requires_visa_sponsorship ? 'Required' : 'Not Required'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Total Professional Experience
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1 text-sm">
              {expDisplay}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/70 dark:border-zinc-800 space-y-1">
            <span className="text-[10px] text-zinc-400 uppercase font-mono tracking-wider block">
              Student Status
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 block pt-1 text-sm">
              {profile.eligibility_constraints.is_currently_enrolled_student
                ? 'Enrolled Student'
                : 'Not Enrolled'}
            </span>
          </div>
        </div>
      </div>

      {/* 9. Persistent Career Memory & Goals Evolution */}
      <div className="p-4 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Brain className="w-4 h-4 text-teal-600 dark:text-teal-400" />
              <span>Career Memory & Versioned Goals</span>
              <span className="text-xs font-normal text-zinc-400 font-mono">
                ({memories.length} active facts)
              </span>
            </h2>
            <p className="text-xs text-zinc-500">
              Persistent candidate intelligence preserved across sessions with immutable version history and provenance.
            </p>
          </div>

          <button
            onClick={openAddMemory}
            className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs self-start sm:self-auto"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Career Goal / Fact</span>
          </button>
        </div>

        {isLoadingMemories ? (
          <div className="py-8 text-center text-xs text-zinc-400 flex items-center justify-center gap-2">
            <RotateCw className="w-4 h-4 animate-spin text-teal-600" />
            <span>Loading career memory records...</span>
          </div>
        ) : memories.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-dashed border-zinc-300 dark:border-zinc-700 space-y-2 text-xs">
            <Brain className="w-6 h-6 text-zinc-400 mx-auto" />
            <p className="font-semibold text-zinc-700 dark:text-zinc-300">
              No career memory facts recorded yet.
            </p>
            <p className="text-zinc-500 max-w-md mx-auto">
              Record long-term career goals, target industries, relocation plans, or key constraints. JobFalcon version-controls each statement as your career evolves.
            </p>
            <button
              onClick={openAddMemory}
              className="text-teal-600 dark:text-teal-400 font-semibold hover:underline cursor-pointer pt-1 inline-block"
            >
              + Record your first career memory fact
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {memories.map((mem) => (
              <div
                key={mem.memory_id}
                className="p-4 rounded-xl bg-zinc-50/70 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors space-y-2.5 text-xs"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-300 font-mono font-bold text-[11px]">
                      v{mem.version}
                    </span>

                    <Badge variant="outline" size="sm" mono>
                      {mem.memory_type}
                    </Badge>

                    <Badge
                      variant={
                        mem.provenance_level === 'VERIFIED'
                          ? 'verified'
                          : mem.provenance_level === 'USER_PROVIDED'
                          ? 'teal'
                          : 'caveat'
                      }
                      size="sm"
                    >
                      {mem.provenance_level}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => openLineage(mem)}
                      className="px-2.5 py-1.5 min-h-[36px] rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400 flex items-center gap-1 text-xs font-medium cursor-pointer"
                      title="Inspect complete version history and audit lineage"
                    >
                      <History className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                      <span>Lineage</span>
                    </button>

                    <button
                      onClick={() => openUpdateMemory(mem)}
                      className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 hover:text-teal-600 transition-colors cursor-pointer"
                      title="Update statement (creates new version with change reason)"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => handleDeleteMemory(mem)}
                      className="p-2 min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-rose-600 transition-colors cursor-pointer"
                      title="Deactivate memory fact"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Statement Body */}
                <p className="text-zinc-800 dark:text-zinc-200 text-sm font-medium leading-relaxed">
                  {mem.statement}
                </p>

                {/* Provenance & Metadata Strip */}
                <div className="flex items-center gap-3 text-[11px] text-zinc-500 font-mono flex-wrap pt-1 border-t border-zinc-200/50 dark:border-zinc-800/60">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-zinc-400" />
                    <span>Active since {new Date(mem.effective_from).toLocaleDateString()}</span>
                  </span>

                  {mem.change_reason && (
                    <>
                      <span>•</span>
                      <span className="italic text-zinc-600 dark:text-zinc-400">
                        Reason: &quot;{mem.change_reason}&quot;
                      </span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
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
                  Review the structured draft below before applying it to your profile.
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
                      <span className="text-[10px] text-zinc-400 uppercase font-mono">Headline</span>
                      <p className="font-medium text-teal-600 dark:text-teal-400">
                        {draftProfile.headline || 'Not specified'}
                      </p>
                    </div>
                    {draftProfile.bio && (
                      <div>
                        <span className="text-[10px] text-zinc-400 uppercase font-mono">Summary</span>
                        <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed mt-1">
                          {draftProfile.bio}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {draftActiveTab === 'experience' && (
                <div className="space-y-3">
                  {(!draftProfile.work_experiences || draftProfile.work_experiences.length === 0) ? (
                    <p className="text-zinc-500 italic">No work experience entries extracted.</p>
                  ) : (
                    draftProfile.work_experiences.map((exp, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-zinc-900 dark:text-zinc-100">
                            {exp.role_title}
                          </span>
                          <span className="text-zinc-500 font-mono text-[11px]">
                            {exp.start_date || 'Past'} – {exp.is_current ? 'Present' : exp.end_date || 'Past'}
                          </span>
                        </div>
                        <p className="text-teal-600 dark:text-teal-400 font-medium">{exp.company_name}</p>
                        {exp.responsibilities?.length > 0 && (
                          <ul className="list-disc list-inside space-y-0.5 text-zinc-600 dark:text-zinc-300 pt-1">
                            {exp.responsibilities.slice(0, 3).map((r, rI) => (
                              <li key={rI}>{r}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}

              {draftActiveTab === 'projects' && (
                <div className="space-y-3">
                  {(!draftProfile.projects || draftProfile.projects.length === 0) ? (
                    <p className="text-zinc-500 italic">No projects extracted.</p>
                  ) : (
                    draftProfile.projects.map((proj, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1.5"
                      >
                        <span className="font-bold text-zinc-900 dark:text-zinc-100">
                          {proj.project_name}
                        </span>
                        <p className="text-zinc-600 dark:text-zinc-300">{proj.description}</p>
                        <div className="flex items-center gap-1.5 flex-wrap pt-1">
                          {proj.technologies?.map((t, tI) => (
                            <span
                              key={tI}
                              className="px-2 py-0.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 text-[10px] font-medium"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {draftActiveTab === 'education' && (
                <div className="space-y-3">
                  {(!draftProfile.education || draftProfile.education.length === 0) ? (
                    <p className="text-zinc-500 italic">No education entries extracted.</p>
                  ) : (
                    draftProfile.education.map((edu, i) => (
                      <div
                        key={i}
                        className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200 dark:border-zinc-800 space-y-1"
                      >
                        <span className="font-bold text-zinc-900 dark:text-zinc-100">
                          {edu.institution_name}
                        </span>
                        <p className="text-zinc-700 dark:text-zinc-300">
                          {edu.degree_level}
                          {edu.field_of_study ? ` in ${edu.field_of_study}` : ''}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}

              {draftActiveTab === 'skills' && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    {draftProfile.assessed_skills.map((skill, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg bg-teal-50 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-300 font-medium text-xs flex items-center gap-1.5"
                      >
                        <span>{skill.skill_name}</span>
                        <span className="font-mono text-[10px] opacity-70">
                          ({skill.proficiency_score.toFixed(1)})
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="p-4 bg-zinc-50 dark:bg-zinc-800/60 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowDraftModal(false)}
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
      {/* MODAL 2: Add / Edit Work Experience                                   */}
      {/* ===================================================================== */}
      {activeModal === 'experience' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 shrink-0">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Work Position' : 'Add Work Position'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1 pr-1">
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Job Title / Role *
                </label>
                <input
                  type="text"
                  value={expRole}
                  onChange={(e) => setExpRole(e.target.value)}
                  placeholder="e.g. Senior Software Engineer"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-sm focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Company or Organization *
                </label>
                <input
                  type="text"
                  value={expCompany}
                  onChange={(e) => setExpCompany(e.target.value)}
                  placeholder="e.g. Acme Systems"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-sm focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Start Date
                  </label>
                  <input
                    type="text"
                    value={expStartDate}
                    onChange={(e) => setExpStartDate(e.target.value)}
                    placeholder="e.g. Jan 2022"
                    className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    End Date
                  </label>
                  <input
                    type="text"
                    value={expEndDate}
                    disabled={expIsCurrent}
                    onChange={(e) => setExpEndDate(e.target.value)}
                    placeholder="e.g. Present"
                    className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs disabled:opacity-40 focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="exp_current"
                  checked={expIsCurrent}
                  onChange={(e) => setExpIsCurrent(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <label htmlFor="exp_current" className="text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  I currently work in this role
                </label>
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Key Responsibilities & Achievements (1 per line)
                </label>
                <textarea
                  rows={3}
                  value={expResponsibilities}
                  onChange={(e) => setExpResponsibilities(e.target.value)}
                  placeholder="Architected microservices handling 10k RPS&#10;Mentored team of 4 junior developers"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs leading-relaxed focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Technologies Used (comma separated)
                </label>
                <input
                  type="text"
                  value={expTechnologies}
                  onChange={(e) => setExpTechnologies(e.target.value)}
                  placeholder="Python, FastAPI, Docker, PostgreSQL"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveExperience}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Save Position
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 3: Add / Edit Project                                           */}
      {/* ===================================================================== */}
      {activeModal === 'project' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 shrink-0">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Project' : 'Add Project Showcase'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1 pr-1">
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Project Name *
                </label>
                <input
                  type="text"
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  placeholder="e.g. Distributed Semantic Search Engine"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Project Description & Outcomes *
                </label>
                <textarea
                  rows={3}
                  value={projDescription}
                  onChange={(e) => setProjDescription(e.target.value)}
                  placeholder="Built a sub-50ms vector search engine indexing 500k documents using pgvector and FastAPI."
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs leading-relaxed focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Technologies Used (comma separated)
                </label>
                <input
                  type="text"
                  value={projTechnologies}
                  onChange={(e) => setProjTechnologies(e.target.value)}
                  placeholder="Next.js, TypeScript, Tailwind, Python, Redis"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Repository or Live Demo Link (optional)
                </label>
                <input
                  type="url"
                  value={projRepoUrl}
                  onChange={(e) => setProjRepoUrl(e.target.value)}
                  placeholder="https://github.com/username/project"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProject}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Save Project
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 4: Add / Edit Education                                         */}
      {/* ===================================================================== */}
      {activeModal === 'education' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 shrink-0">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Education' : 'Add Education Record'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1 pr-1">
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Institution Name *
                </label>
                <input
                  type="text"
                  value={eduInstitution}
                  onChange={(e) => setEduInstitution(e.target.value)}
                  placeholder="e.g. University of Engineering and Technology"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Degree Level *
                  </label>
                  <select
                    value={eduDegreeLevel}
                    onChange={(e) => setEduDegreeLevel(e.target.value as DegreeLevel)}
                    className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  >
                    <option value="BACHELORS">Bachelors</option>
                    <option value="MASTERS">Masters</option>
                    <option value="DOCTORATE">Doctorate (PhD)</option>
                    <option value="ASSOCIATES">Associates</option>
                    <option value="BOOTCAMP">Bootcamp / Specialized</option>
                    <option value="HIGH_SCHOOL">High School</option>
                    <option value="SELF_TAUGHT">Self Taught</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Field of Study
                  </label>
                  <input
                    type="text"
                    value={eduField}
                    onChange={(e) => setEduField(e.target.value)}
                    placeholder="e.g. Computer Science"
                    className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Graduation Year or Date
                </label>
                <input
                  type="text"
                  value={eduGradDate}
                  onChange={(e) => setEduGradDate(e.target.value)}
                  placeholder="e.g. 2024 or Expected May 2025"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="edu_enrolled"
                  checked={eduIsEnrolled}
                  onChange={(e) => setEduIsEnrolled(e.target.checked)}
                  className="rounded text-teal-600 focus:ring-teal-500"
                />
                <label htmlFor="edu_enrolled" className="text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  Currently Enrolled Student
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEducation}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Save Education
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 5: Add / Edit Skill (Evidence is purely OPTIONAL!)              */}
      {/* ===================================================================== */}
      {activeModal === 'skill' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-md max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 shrink-0">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                {editingIndex !== null ? 'Edit Skill Competency' : 'Add Skill Competency'}
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs overflow-y-auto flex-1 pr-1">
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Skill / Technology Name *
                </label>
                <input
                  type="text"
                  value={skillNameInput}
                  onChange={(e) => setSkillNameInput(e.target.value)}
                  placeholder="e.g. PyTorch, Next.js, Docker, SQL"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-zinc-600 dark:text-zinc-400 font-medium">
                    Proficiency Score (1.0 – 10.0)
                  </label>
                  <span className="font-mono font-bold text-teal-600 dark:text-teal-400 text-sm">
                    {skillProfScore.toFixed(1)} / 10
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="0.5"
                  value={skillProfScore}
                  onChange={(e) => setSkillProfScore(parseFloat(e.target.value))}
                  className="w-full accent-teal-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-zinc-400 font-mono mt-1">
                  <span>1.0 Beginner</span>
                  <span>5.0 Intermediate</span>
                  <span>10.0 Advanced</span>
                </div>
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Evidence Excerpt or Note (Optional)
                </label>
                <textarea
                  rows={2}
                  value={skillEvidenceInput}
                  onChange={(e) => setSkillEvidenceInput(e.target.value)}
                  placeholder="Optional verbatim excerpt or project note. Leave empty for self-reported skills."
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs leading-relaxed focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
                <p className="text-[11px] text-zinc-400 mt-1">
                  No resume upload or evidence quote is required to add skills.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveSkill}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Save Skill
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 6: Edit Profile Overview & Bio                                  */}
      {/* ===================================================================== */}
      {activeModal === 'overview' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 shrink-0">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Edit Profile Overview
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1 pr-1">
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Full Name
                </label>
                <input
                  type="text"
                  value={overviewName}
                  onChange={(e) => setOverviewName(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Headline / Professional Role
                </label>
                <input
                  type="text"
                  value={overviewHeadline}
                  onChange={(e) => setOverviewHeadline(e.target.value)}
                  placeholder="e.g. Full-Stack Software Engineer & AI Systems Developer"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Location
                </label>
                <input
                  type="text"
                  value={overviewLocation}
                  onChange={(e) => setOverviewLocation(e.target.value)}
                  placeholder="e.g. Lahore, Pakistan or Remote"
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Professional Bio / Executive Summary
                </label>
                <textarea
                  rows={4}
                  value={overviewBio}
                  onChange={(e) => setOverviewBio(e.target.value)}
                  placeholder="Passionate engineer with experience in distributed systems, AI agents, and web applications..."
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs leading-relaxed focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveOverview}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Save Overview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 7: Edit Career Preferences & Eligibility Constraints            */}
      {/* ===================================================================== */}
      {activeModal === 'preferences' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3 shrink-0">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Edit Career Preferences
              </h3>
              <button
                onClick={() => setActiveModal('none')}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs overflow-y-auto flex-1 pr-1">
              {/* Target Roles */}
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Target Career Roles
                </label>
                <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                  {prefTargetRoles.map((role, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-teal-50 dark:bg-teal-950/60 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-300 font-semibold flex items-center gap-1.5"
                    >
                      <span>{role}</span>
                      <button
                        type="button"
                        onClick={() =>
                          setPrefTargetRoles(prefTargetRoles.filter((_, i) => i !== idx))
                        }
                        className="text-teal-600 hover:text-teal-800 dark:hover:text-teal-200 cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={prefNewRole}
                    onChange={(e) => setPrefNewRole(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        if (prefNewRole.trim()) {
                          setPrefTargetRoles([...prefTargetRoles, prefNewRole.trim()]);
                          setPrefNewRole('');
                        }
                      }
                    }}
                    placeholder="Add target role (e.g. AI Engineer) and press enter"
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
                    className="px-3 py-2 rounded-lg bg-teal-600 text-white font-semibold cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Target Locations */}
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Target Locations
                </label>
                <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                  {prefLocations.map((loc, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-300 font-semibold flex items-center gap-1.5"
                    >
                      <span>{loc}</span>
                      <button
                        type="button"
                        onClick={() =>
                          setPrefLocations(prefLocations.filter((_, i) => i !== idx))
                        }
                        className="text-zinc-500 hover:text-red-500 cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={prefNewLocation}
                    onChange={(e) => setPrefNewLocation(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        if (prefNewLocation.trim()) {
                          setPrefLocations([...prefLocations, prefNewLocation.trim()]);
                          setPrefNewLocation('');
                        }
                      }
                    }}
                    placeholder="Add location (e.g. Remote, San Francisco, London) and press enter"
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
                    className="px-3 py-2 rounded-lg bg-teal-600 text-white font-semibold cursor-pointer"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Work Modes */}
              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Allowed Work Modes
                </label>
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
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
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
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
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
                  <span className="text-zinc-500 text-xs font-mono">
                    = {(prefExperienceMonths / 12).toFixed(1)} years
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setActiveModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSavePreferences}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Apply Preferences
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 7: Add Career Memory Fact Modal                                  */}
      {/* ===================================================================== */}
      {memoryModal === 'add' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 flex flex-col overflow-hidden">
            <div className="flex items-start justify-between shrink-0">
              <div>
                <div className="flex items-center gap-1.5 text-teal-600 dark:text-teal-400">
                  <Brain className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase font-mono tracking-wider">Career Intelligence Memory</span>
                </div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  Record Career Memory Fact
                </h3>
              </div>
              <button
                onClick={() => setMemoryModal('none')}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1 pr-1">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Memory Category
                  </label>
                  <select
                    value={memoryTypeInput}
                    onChange={(e) => setMemoryTypeInput(e.target.value as MemoryType)}
                    className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  >
                    <option value="CAREER_GOAL">Career Goal</option>
                    <option value="STRENGTH">Demonstrated Strength</option>
                    <option value="CONSTRAINT">Hard Constraint</option>
                    <option value="TRAJECTORY_PREFERENCE">Trajectory Preference</option>
                    <option value="INTEREST">Domain Interest</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                    Provenance Level
                  </label>
                  <select
                    value={memoryProvenanceInput}
                    onChange={(e) => setMemoryProvenanceInput(e.target.value as ProvenanceLevel)}
                    className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                  >
                    <option value="USER_PROVIDED">User Provided</option>
                    <option value="VERIFIED">Verified Evidence</option>
                    <option value="AI_INFERRED">AI Inferred</option>
                  </select>
                </div>
              </div>

              {memoryError && (
                <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 text-rose-700 dark:text-rose-300 text-xs">
                  {memoryError}
                </div>
              )}

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Memory Statement / Goal
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Targeting Senior Backend roles at Series A-B startups with Rust or Go stacks; open to remote or Bengaluru hybrid."
                  value={memoryStatementInput}
                  onChange={(e) => setMemoryStatementInput(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setMemoryModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveNewMemory}
                disabled={isSavingMemory}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer disabled:opacity-50 min-h-[38px] sm:min-h-0"
              >
                {isSavingMemory ? 'Recording...' : 'Record Memory Fact'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 8: Update Career Memory Fact (Versioned) Modal                   */}
      {/* ===================================================================== */}
      {memoryModal === 'update' && activeMemory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-lg max-h-[90vh] bg-white dark:bg-zinc-900 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 flex flex-col overflow-hidden">
            <div className="flex items-start justify-between shrink-0">
              <div>
                <div className="flex items-center gap-1.5 text-teal-600 dark:text-teal-400">
                  <Brain className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase font-mono tracking-wider">
                    Evolving Version (v{activeMemory.version} → v{activeMemory.version + 1})
                  </span>
                </div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  Update Career Memory Fact
                </h3>
              </div>
              <button
                onClick={() => setMemoryModal('none')}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs overflow-y-auto flex-1 pr-1">
              <div className="p-3 rounded-lg bg-teal-50/50 dark:bg-teal-950/20 border border-teal-200/60 dark:border-teal-800/50 text-[11px] text-teal-800 dark:text-teal-300 leading-relaxed">
                Updating this fact creates a new version while preserving the previous statement, effective dates, and change rationale in your permanent career lineage.
              </div>

              {memoryError && (
                <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 text-rose-700 dark:text-rose-300 text-xs">
                  {memoryError}
                </div>
              )}

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Updated Memory Statement
                </label>
                <textarea
                  rows={3}
                  value={memoryStatementInput}
                  onChange={(e) => setMemoryStatementInput(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-400 mb-1 font-medium">
                  Reason for Change (Mandatory Provenance):
                </label>
                <input
                  type="text"
                  placeholder="e.g. Completed AWS Solution Architect; shifting focus to Cloud Infrastructure"
                  value={memoryChangeReasonInput}
                  onChange={(e) => setMemoryChangeReasonInput(e.target.value)}
                  className="w-full p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 text-base sm:text-xs focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setMemoryModal('none')}
                className="px-3.5 py-2 sm:py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveUpdatedMemory}
                disabled={isSavingMemory}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-semibold cursor-pointer disabled:opacity-50 min-h-[38px] sm:min-h-0"
              >
                {isSavingMemory ? 'Saving Version...' : 'Save New Version'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 9: Memory Lineage Audit Drawer / Modal                           */}
      {/* ===================================================================== */}
      {memoryModal === 'lineage' && activeMemory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="w-full max-w-2xl bg-white dark:bg-zinc-900 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-800 p-4 sm:p-6 space-y-4 max-h-[85vh] flex flex-col overflow-hidden">
            <div className="flex items-start justify-between shrink-0">
              <div>
                <div className="flex items-center gap-1.5 text-teal-600 dark:text-teal-400">
                  <History className="w-4 h-4" />
                  <span className="text-xs font-bold uppercase font-mono tracking-wider">Immutable Version Lineage</span>
                </div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-1">
                  Career Memory Evolution Audit
                </h3>
                <p className="text-xs text-zinc-500 font-mono">
                  Memory ID: {activeMemory.memory_id}
                </p>
              </div>
              <button
                onClick={() => setMemoryModal('none')}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
              {isLoadingLineage ? (
                <div className="py-8 text-center text-zinc-400 flex items-center justify-center gap-2">
                  <RotateCw className="w-4 h-4 animate-spin text-teal-600" />
                  <span>Loading full version trail...</span>
                </div>
              ) : memoryLineage.length === 0 ? (
                <p className="text-zinc-500 italic text-center py-6">No previous versions on record.</p>
              ) : (
                memoryLineage.map((item) => (
                  <div
                    key={item.memory_id}
                    className={`p-4 rounded-xl border space-y-2 ${
                      item.is_active
                        ? 'bg-teal-50/40 dark:bg-teal-950/20 border-teal-300 dark:border-teal-800'
                        : 'bg-zinc-50/70 dark:bg-zinc-800/40 border-zinc-200/80 dark:border-zinc-800 opacity-80'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-mono font-bold text-[10px]">
                          v{item.version}
                        </span>

                        <Badge
                          variant={item.is_active ? 'verified' : 'neutral'}
                          size="sm"
                        >
                          {item.is_active ? 'CURRENT ACTIVE' : 'SUPERSEDED'}
                        </Badge>

                        <Badge variant="outline" size="sm" mono>
                          {item.provenance_level}
                        </Badge>
                      </div>

                      <span className="text-[11px] text-zinc-400 font-mono">
                        {new Date(item.effective_from).toLocaleDateString()}
                        {item.effective_to ? ` → ${new Date(item.effective_to).toLocaleDateString()}` : ' → Present'}
                      </span>
                    </div>

                    <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 leading-relaxed">
                      {item.statement}
                    </p>

                    {item.change_reason && (
                      <div className="pt-1.5 border-t border-zinc-200/50 dark:border-zinc-700/50 text-[11px] text-zinc-600 dark:text-zinc-400 italic">
                        <strong>Change Reason:</strong> &quot;{item.change_reason}&quot;
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="flex items-center justify-end pt-2 border-t border-zinc-100 dark:border-zinc-800 shrink-0">
              <button
                onClick={() => setMemoryModal('none')}
                className="px-4 py-2 sm:py-1.5 rounded-lg bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-xs font-semibold cursor-pointer min-h-[38px] sm:min-h-0"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

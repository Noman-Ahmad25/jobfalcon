'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Header, WorkspaceTab } from '@/components/layout/Header';
import { CANDIDATES } from '@/lib/candidates';
import { CandidateCareerProfile, CandidateProfileSummary } from '@/types/domain';
import { getBackendHealth, listProfiles, getCandidateProfile } from '@/lib/api';
import { DiscoveryWorkspace } from '@/components/workspaces/DiscoveryWorkspace';
import { ProfileWorkspace } from '@/components/workspaces/ProfileWorkspace';
import { DevelopmentWorkspace } from '@/components/workspaces/DevelopmentWorkspace';
import { CareerPathWorkspace } from '@/components/workspaces/CareerPathWorkspace';
import { OnboardingScreen } from '@/components/onboarding/OnboardingScreen';
import { Users, UserPlus, Loader2 } from 'lucide-react';

const KNOWN_DEMO_IDS = new Set([
  'maya-chen-junior',
  'usr_cand_student_02',
  'alex-rivera-fullstack',
  'usr_cand_backend_01',
  'usr-api-demo',
  'usr_explanation_test_01',
]);

export default function Home() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('discover');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>('');
  const [candidateProfile, setCandidateProfile] = useState<CandidateCareerProfile | null>(null);
  const [candidateSummaries, setCandidateSummaries] = useState<CandidateProfileSummary[]>([]);
  const [candidateName, setCandidateName] = useState<string>('Candidate');
  const [candidateHeadline, setCandidateHeadline] = useState<string>('Candidate Profile');
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [isLoadingProfile, setIsLoadingProfile] = useState<boolean>(true);
  const [showOnboarding, setShowOnboarding] = useState<boolean>(false);

  // Load a candidate profile from backend repository
  const loadProfile = useCallback(async (userId: string) => {
    setIsLoadingProfile(true);
    try {
      const profile = await getCandidateProfile(userId);
      setCandidateProfile(profile);
      setSelectedCandidateId(profile.user_id);
      const name = profile.display_name || profile.user_id;
      setCandidateName(name);
      const targetTitle = profile.target_career_paths[0]?.title || 'Candidate';
      setCandidateHeadline(targetTitle);
      setShowOnboarding(false);
    } catch {
      // If backend lookup fails but it's a known demo, check local fixture
      if (CANDIDATES[userId]) {
        const demo = CANDIDATES[userId];
        setCandidateProfile(demo.profile);
        setSelectedCandidateId(demo.id);
        setCandidateName(demo.name);
        setCandidateHeadline(demo.headline);
        setShowOnboarding(false);
      }
    } finally {
      setIsLoadingProfile(false);
    }
  }, []);

  // Check health and discover stored profiles on startup
  useEffect(() => {
    let isMounted = true;

    async function init() {
      let online = false;
      try {
        const health = await getBackendHealth();
        online = health.status === 'ok' || health.status === 'degraded';
        if (isMounted) setBackendOnline(online);
      } catch {
        if (isMounted) setBackendOnline(false);
      }

      if (!online) {
        const defaultDemo = CANDIDATES['maya-chen-junior'];
        if (isMounted) {
          setCandidateProfile(defaultDemo.profile);
          setSelectedCandidateId(defaultDemo.id);
          setCandidateName(defaultDemo.name);
          setCandidateHeadline(defaultDemo.headline);
          setIsLoadingProfile(false);
        }
        return;
      }

      try {
        const summaries = await listProfiles();
        if (!isMounted) return;
        setCandidateSummaries(summaries);

        const realProfiles = summaries.filter((s) => !KNOWN_DEMO_IDS.has(s.user_id));
        const demoProfiles = summaries.filter((s) => KNOWN_DEMO_IDS.has(s.user_id));

        if (realProfiles.length > 0) {
          const profile = await getCandidateProfile(realProfiles[0].user_id);
          if (!isMounted) return;
          setCandidateProfile(profile);
          setSelectedCandidateId(profile.user_id);
          setCandidateName(profile.display_name || profile.user_id);
          setCandidateHeadline(profile.target_career_paths[0]?.title || 'Candidate');
          setShowOnboarding(false);
        } else if (demoProfiles.length > 0) {
          const profile = await getCandidateProfile(demoProfiles[0].user_id);
          if (!isMounted) return;
          setCandidateProfile(profile);
          setSelectedCandidateId(profile.user_id);
          setCandidateName(profile.display_name || profile.user_id);
          setCandidateHeadline(profile.target_career_paths[0]?.title || 'Candidate');
          setShowOnboarding(false);
        } else {
          setCandidateProfile(null);
          setShowOnboarding(true);
        }
      } catch {
        if (isMounted) setShowOnboarding(true);
      } finally {
        if (isMounted) setIsLoadingProfile(false);
      }
    }

    init();
    return () => {
      isMounted = false;
    };
  }, []);

  // Handle switching candidates
  const handleSelectCandidate = async (userId: string) => {
    if (userId === '__NEW_PROFILE__') {
      setShowOnboarding(true);
      return;
    }
    await loadProfile(userId);
  };

  // Called when onboarding completes
  const handleProfileCreated = (newProfile: CandidateCareerProfile) => {
    setCandidateProfile(newProfile);
    setSelectedCandidateId(newProfile.user_id);
    setCandidateName(newProfile.display_name || newProfile.user_id);
    const targetTitle = newProfile.target_career_paths[0]?.title || 'Candidate';
    setCandidateHeadline(targetTitle);
    setShowOnboarding(false);
    setActiveTab('discover');

    // Refresh summary list
    listProfiles().then((res) => setCandidateSummaries(res)).catch(() => {});
  };

  // Cross-workspace navigation handler
  const handleNavigateTab = (tab: WorkspaceTab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const realSummaries = candidateSummaries.filter((s) => !KNOWN_DEMO_IDS.has(s.user_id));
  const demoSummaries = candidateSummaries.filter((s) => KNOWN_DEMO_IDS.has(s.user_id));

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col font-sans text-zinc-900 dark:text-zinc-100 antialiased selection:bg-teal-500 selection:text-white">
      {/* Top Application Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        candidateName={candidateName}
        candidateRole={candidateHeadline}
        backendOnline={backendOnline}
      />

      {/* Main Workstation Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {isLoadingProfile ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-3">
            <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
            <span className="text-xs font-mono text-zinc-500">Connecting to JobFalcon local repository...</span>
          </div>
        ) : showOnboarding || !candidateProfile ? (
          <OnboardingScreen
            onProfileCreated={handleProfileCreated}
            onExploreDemo={
              demoSummaries.length > 0 || Object.keys(CANDIDATES).length > 0
                ? () => {
                    const fallbackId = demoSummaries[0]?.user_id || 'maya-chen-junior';
                    loadProfile(fallbackId);
                  }
                : undefined
            }
          />
        ) : (
          <>
            {/* Candidate Switcher Bar */}
            <div className="p-3.5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="p-1.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                  <Users className="w-4 h-4" />
                </span>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-zinc-500 font-mono">Active Profile:</span>
                  <select
                    value={selectedCandidateId}
                    onChange={(e) => handleSelectCandidate(e.target.value)}
                    className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-2.5 py-1 focus:ring-2 focus:ring-teal-500 focus:outline-hidden cursor-pointer"
                  >
                    {realSummaries.length > 0 && (
                      <optgroup label="Local User Profiles">
                        {realSummaries.map((cand) => (
                          <option key={cand.user_id} value={cand.user_id}>
                            {cand.display_name} ({cand.target_role || cand.user_id})
                          </option>
                        ))}
                      </optgroup>
                    )}

                    {demoSummaries.length > 0 && (
                      <optgroup label="Development & Demo Candidates">
                        {demoSummaries.map((cand) => (
                          <option key={cand.user_id} value={cand.user_id}>
                            [DEMO] {cand.display_name} ({cand.target_role || cand.user_id})
                          </option>
                        ))}
                      </optgroup>
                    )}

                    {candidateSummaries.length === 0 && (
                      <optgroup label="Demo Candidates (In-Memory)">
                        {Object.values(CANDIDATES).map((cand) => (
                          <option key={cand.id} value={cand.id}>
                            [DEMO] {cand.name} ({cand.role})
                          </option>
                        ))}
                      </optgroup>
                    )}

                    <option value="__NEW_PROFILE__">+ Create New Profile...</option>
                  </select>
                </div>

                <button
                  onClick={() => setShowOnboarding(true)}
                  className="px-2.5 py-1 rounded-md border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-[11px] font-medium text-zinc-600 dark:text-zinc-300 transition-colors flex items-center gap-1"
                  title="Create another candidate profile"
                >
                  <UserPlus className="w-3 h-3 text-teal-600" />
                  <span>New Profile</span>
                </button>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 flex-wrap">
                <span>
                  Target:{' '}
                  <strong className="text-zinc-800 dark:text-zinc-200">
                    {candidateProfile.target_career_paths[0]?.title}
                  </strong>
                </span>
                <span>•</span>
                <span>{candidateProfile.assessed_skills.length} skills on file</span>
                <span>•</span>
                <span>Degree: {candidateProfile.eligibility_constraints.highest_degree_level}</span>
                {KNOWN_DEMO_IDS.has(selectedCandidateId) && (
                  <>
                    <span>•</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                      DEMO MODE
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Active Workspace View */}
            {activeTab === 'discover' && (
              <DiscoveryWorkspace
                candidateProfile={candidateProfile}
                candidateName={candidateName}
                onNavigateTab={handleNavigateTab}
              />
            )}

            {activeTab === 'profile' && (
              <ProfileWorkspace
                candidateProfile={candidateProfile}
                candidateName={candidateName}
                onNavigateTab={handleNavigateTab}
                onProfileUpdated={(updated) => {
                  setCandidateProfile(updated);
                  setCandidateName(updated.display_name || updated.user_id);
                }}
              />
            )}

            {activeTab === 'development' && (
              <DevelopmentWorkspace
                candidateProfile={candidateProfile}
                candidateName={candidateName}
                onNavigateTab={handleNavigateTab}
              />
            )}

            {activeTab === 'career-path' && (
              <CareerPathWorkspace
                candidateProfile={candidateProfile}
                candidateName={candidateName}
                onNavigateTab={handleNavigateTab}
              />
            )}
          </>
        )}
      </main>

      {/* Engineering Invariants Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 py-6 mt-12 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-zinc-500">
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">JobFalcon V1</span>
            <span>•</span>
            <span>Deterministic Career Intelligence</span>
            <span>•</span>
            <span className="font-mono text-[11px]">LangGraph StateGraph Engine</span>
          </div>

          <div className="flex items-center gap-4 text-zinc-500 font-mono text-[11px]">
            <span>100% Deterministic Gating</span>
            <span>•</span>
            <span>Zero LLM Score Hallucination</span>
            <span>•</span>
            <span>Evidence Grounded</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

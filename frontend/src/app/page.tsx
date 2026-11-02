'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Header, WorkspaceTab } from '@/components/layout/Header';
import { CANDIDATES } from '@/lib/candidates';
import { CandidateCareerProfile, CandidateProfileSummary } from '@/types/domain';
import { getBackendHealth, listProfiles, getCandidateProfile } from '@/lib/api';
import { DiscoveryWorkspace } from '@/components/workspaces/DiscoveryWorkspace';
import { ProfileWorkspace } from '@/components/workspaces/ProfileWorkspace';
import { OnboardingScreen } from '@/components/onboarding/OnboardingScreen';
import { applyTheme, ThemeMode, useIsDarkMode } from '@/lib/theme';
import { Loader2 } from 'lucide-react';

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
  const isDarkMode = useIsDarkMode();

  const handleToggleTheme = () => {
    const nextMode: ThemeMode = isDarkMode ? 'light' : 'dark';
    applyTheme(nextMode);
  };

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

        // Find the first usable candidate profile (one that actually has skills extracted/saved)
        let activeProfile: CandidateCareerProfile | null = null;
        for (const s of realProfiles) {
          try {
            const p = await getCandidateProfile(s.user_id);
            if (p && p.assessed_skills && p.assessed_skills.length > 0) {
              activeProfile = p;
              break;
            }
          } catch {
            // continue checking
          }
        }

        if (!activeProfile) {
          for (const s of demoProfiles) {
            try {
              const p = await getCandidateProfile(s.user_id);
              if (p && p.assessed_skills && p.assessed_skills.length > 0) {
                activeProfile = p;
                break;
              }
            } catch {
              // continue checking
            }
          }
        }

        if (!isMounted) return;

        if (activeProfile && activeProfile.assessed_skills.length > 0) {
          setCandidateProfile(activeProfile);
          setSelectedCandidateId(activeProfile.user_id);
          setCandidateName(activeProfile.display_name || activeProfile.user_id);
          setCandidateHeadline(activeProfile.target_career_paths[0]?.title || 'Candidate');
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

  const demoSummaries = candidateSummaries.filter((s) => KNOWN_DEMO_IDS.has(s.user_id));

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col font-sans text-zinc-900 dark:text-zinc-100 antialiased selection:bg-teal-500 selection:text-white">
      {/* Top Application Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        candidateName={candidateName}
        candidateRole={candidateHeadline}
        candidateId={selectedCandidateId}
        backendOnline={backendOnline}
        isDarkMode={isDarkMode}
        onToggleTheme={handleToggleTheme}
        candidateSummaries={candidateSummaries}
        onSelectCandidate={handleSelectCandidate}
        onNewProfile={() => setShowOnboarding(true)}
        onOpenUploadResume={() => {
          setActiveTab('profile');
        }}
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
            {/* Active Workspace View: Strictly Two Main Areas */}
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
          </>
        )}
      </main>

      {/* Precision Career Intelligence Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 py-6 mt-12 text-xs transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-zinc-500">
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">JobFalcon V1</span>
            <span>•</span>
            <span>Evidence-First Career Intelligence</span>
            <span>•</span>
            <span>Local Workstation</span>
          </div>

          <div className="flex items-center gap-4 text-zinc-500 font-mono text-[11px]">
            <span>100% Deterministic Gating</span>
            <span>•</span>
            <span>Zero Hallucinated Metrics</span>
            <span>•</span>
            <span>Verifiable Evidence Records</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

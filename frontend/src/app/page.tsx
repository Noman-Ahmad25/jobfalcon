'use client';

import React, { useState, useEffect } from 'react';
import { Header, WorkspaceTab } from '@/components/layout/Header';
import { CANDIDATES, DEFAULT_CANDIDATE_ID } from '@/lib/candidates';
import { CandidateCareerProfile } from '@/types/domain';
import { getBackendHealth } from '@/lib/api';
import { DiscoveryWorkspace } from '@/components/workspaces/DiscoveryWorkspace';
import { ProfileWorkspace } from '@/components/workspaces/ProfileWorkspace';
import { DevelopmentWorkspace } from '@/components/workspaces/DevelopmentWorkspace';
import { CareerPathWorkspace } from '@/components/workspaces/CareerPathWorkspace';
import { Users } from 'lucide-react';

export default function Home() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('discover');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>(DEFAULT_CANDIDATE_ID);
  const [activeCandidate, setActiveCandidate] = useState(CANDIDATES[DEFAULT_CANDIDATE_ID]);
  const [candidateProfile, setCandidateProfile] = useState<CandidateCareerProfile>(
    CANDIDATES[DEFAULT_CANDIDATE_ID].profile
  );
  const [backendOnline, setBackendOnline] = useState<boolean>(true);

  // Check backend health on initial mount
  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        const res = await getBackendHealth();
        if (isMounted) setBackendOnline(res.status === 'ok' || res.status === 'degraded');
      } catch {
        if (isMounted) setBackendOnline(false);
      }
    }
    checkHealth();
    return () => {
      isMounted = false;
    };
  }, []);

  // Update candidate profile when candidate selector changes
  const handleSelectCandidate = (candidateId: string) => {
    if (CANDIDATES[candidateId]) {
      setSelectedCandidateId(candidateId);
      setActiveCandidate(CANDIDATES[candidateId]);
      setCandidateProfile(CANDIDATES[candidateId].profile);
    }
  };

  // Cross-workspace navigation handler
  const handleNavigateTab = (tab: WorkspaceTab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col font-sans text-zinc-900 dark:text-zinc-100 antialiased selection:bg-teal-500 selection:text-white">
      {/* Top Application Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        candidateName={activeCandidate.name}
        candidateRole={activeCandidate.headline}
        backendOnline={backendOnline}
      />

      {/* Main Workstation Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Candidate Switcher Bar */}
        <div className="p-3.5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="p-1.5 rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
              <Users className="w-4 h-4" />
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-zinc-500 font-mono">Active Candidate:</span>
              <select
                value={selectedCandidateId}
                onChange={(e) => handleSelectCandidate(e.target.value)}
                className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-2.5 py-1 focus:ring-2 focus:ring-teal-500 focus:outline-hidden cursor-pointer"
              >
                {Object.values(CANDIDATES).map((cand) => (
                  <option key={cand.id} value={cand.id}>
                    {cand.name} ({cand.role})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 flex-wrap">
            <span>
              Target: <strong className="text-zinc-800 dark:text-zinc-200">{candidateProfile.target_career_paths[0]?.title}</strong>
            </span>
            <span>•</span>
            <span>{candidateProfile.assessed_skills.length} skills on file</span>
            <span>•</span>
            <span>Degree: {candidateProfile.eligibility_constraints.highest_degree_level}</span>
          </div>
        </div>

        {/* Active Workspace View */}
        {activeTab === 'discover' && (
          <DiscoveryWorkspace
            candidateProfile={candidateProfile}
            candidateName={activeCandidate.name}
            onNavigateTab={handleNavigateTab}
          />
        )}

        {activeTab === 'profile' && (
          <ProfileWorkspace
            candidateProfile={candidateProfile}
            candidateName={activeCandidate.name}
            onNavigateTab={handleNavigateTab}
            onProfileUpdated={(updated) => setCandidateProfile(updated)}
          />
        )}

        {activeTab === 'development' && (
          <DevelopmentWorkspace
            candidateProfile={candidateProfile}
            candidateName={activeCandidate.name}
            onNavigateTab={handleNavigateTab}
          />
        )}

        {activeTab === 'career-path' && (
          <CareerPathWorkspace
            candidateProfile={candidateProfile}
            candidateName={activeCandidate.name}
            onNavigateTab={handleNavigateTab}
          />
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

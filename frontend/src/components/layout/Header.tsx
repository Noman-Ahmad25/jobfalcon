'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Compass,
  Sun,
  Moon,
  ChevronDown,
  User,
  Upload,
  Users,
  PlusCircle,
  Check,
  TrendingUp,
  History,
} from 'lucide-react';
import { useIsMounted } from '@/lib/theme';
import { CandidateProfileSummary } from '@/types/domain';

export type WorkspaceTab = 'discover' | 'career' | 'market' | 'activity' | 'profile';

interface HeaderProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  candidateName?: string;
  candidateRole?: string;
  candidateId?: string;
  backendOnline?: boolean;
  isDarkMode?: boolean;
  onToggleTheme?: () => void;
  onOpenUploadResume?: () => void;
  candidateSummaries?: CandidateProfileSummary[];
  onSelectCandidate?: (userId: string) => void;
  onNewProfile?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  candidateName = 'Candidate',
  candidateRole = 'Software Engineer',
  candidateId = '',  
  isDarkMode = false,
  onToggleTheme,
  onOpenUploadResume,
  candidateSummaries = [],
  onSelectCandidate,
  onNewProfile,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const mounted = useIsMounted();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Compute initials from candidate name
  const getInitials = (name: string): string => {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return (name.slice(0, 2) || 'JF').toUpperCase();
  };

  const initials = getInitials(candidateName);

  return (
    <header className="border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md sticky top-0 z-30 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-16 flex items-center justify-between gap-4">
          {/* 1. Left: Logo & Primary Discovery Workspace Anchor */}
          <div className="flex items-center gap-6 shrink-0">
            <div
              onClick={() => onTabChange('discover')}
              className="flex items-center gap-3 cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-teal-600 dark:bg-teal-500 flex items-center justify-center text-white font-bold text-xs tracking-wider shadow-xs transition-transform group-hover:scale-105">
                JF
              </div>
              <div>
                <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 leading-tight">
                  JobFalcon
                </span>
                <p className="text-[11px] text-zinc-500 hidden sm:block">
                  Career Opportunity Discovery
                </p>
              </div>
            </div>

            {/* Primary Four Product Destinations (Desktop >= 1024px) */}
            <nav className="hidden lg:flex items-center gap-1.5" aria-label="Desktop Navigation">
              <button
                onClick={() => onTabChange('discover')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeTab === 'discover'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-2xs border border-zinc-200/90 dark:border-zinc-700'
                    : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                }`}
              >
                <Compass className={`w-3.5 h-3.5 ${activeTab === 'discover' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
                <span>Discovery</span>
              </button>

              <button
                onClick={() => onTabChange('career')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeTab === 'career' || activeTab === 'profile'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-2xs border border-zinc-200/90 dark:border-zinc-700'
                    : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                }`}
              >
                <User className={`w-3.5 h-3.5 ${activeTab === 'career' || activeTab === 'profile' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
                <span>My Career</span>
              </button>

              <button
                onClick={() => onTabChange('market')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeTab === 'market'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-2xs border border-zinc-200/90 dark:border-zinc-700'
                    : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                }`}
              >
                <TrendingUp className={`w-3.5 h-3.5 ${activeTab === 'market' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
                <span>Market Intelligence</span>
              </button>

              <button
                onClick={() => onTabChange('activity')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                  activeTab === 'activity'
                    ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-2xs border border-zinc-200/90 dark:border-zinc-700'
                    : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50'
                }`}
              >
                <History className={`w-3.5 h-3.5 ${activeTab === 'activity' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
                <span>Activity & History</span>
              </button>
            </nav>
          </div>

          {/* 2. Right: Theme Toggle & User/Profile Area */}
          <div className="flex items-center gap-3 shrink-0">
          
    

            {/* Theme Toggle Button */}
            {onToggleTheme && (
              <button
                onClick={onToggleTheme}
                className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 transition-colors"
                title={mounted && isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                aria-label="Toggle Theme"
              >
                {mounted && isDarkMode ? (
                  <Sun className="w-4 h-4 text-amber-400" />
                ) : (
                  <Moon className="w-4 h-4 text-zinc-600" />
                )}
              </button>
            )}

            {/* Profile Menu Trigger & Dropdown */}
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className={`flex items-center gap-2 sm:gap-2.5 p-1.5 sm:px-2.5 sm:py-1.5 rounded-xl border transition-all ${
                  menuOpen
                    ? 'border-teal-500 bg-teal-50/50 dark:bg-teal-950/40 text-zinc-900 dark:text-zinc-100 ring-2 ring-teal-500/20'
                    : 'border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/80 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200'
                }`}
                aria-expanded={menuOpen}
                aria-label="User profile and settings menu"
              >
                <div className="w-7 h-7 rounded-lg bg-teal-600 dark:bg-teal-500 text-white font-bold text-xs flex items-center justify-center shadow-2xs shrink-0">
                  {initials}
                </div>
                <div className="flex flex-col items-start text-left leading-tight pr-0.5 hidden sm:flex">
                  <span className="font-semibold text-xs text-zinc-900 dark:text-zinc-100 truncate max-w-[130px]">
                    {candidateName}
                  </span>
                  <span className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate max-w-[130px]">
                    {candidateRole}
                  </span>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 shrink-0 transition-transform ${menuOpen ? 'rotate-180 text-teal-600' : ''}`} />
              </button>

              {/* Profile Dropdown Menu */}
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-72 max-w-[calc(100vw-1.5rem)] rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-lg py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  {/* Current Active Candidate Header */}
                  <div className="px-4 py-2.5 border-b border-zinc-100 dark:border-zinc-800/80">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block">
                      Active Candidate Profile
                    </span>
                    <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate block">
                      {candidateName}
                    </span>
                    <span className="text-xs text-zinc-500 dark:text-zinc-400 truncate block">
                      {candidateRole}
                    </span>
                  </div>

                  {/* Profile Actions */}
                  <div className="py-1">
                    <button
                      onClick={() => {
                        onTabChange('career');
                        setMenuOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-xs text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center gap-2.5 transition-colors"
                    >
                      <User className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                      <span>View & Edit Career Profile</span>
                    </button>

                    {onOpenUploadResume && (
                      <button
                        onClick={() => {
                          onOpenUploadResume();
                          setMenuOpen(false);
                        }}
                        className="w-full text-left px-4 py-2 text-xs text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 flex items-center gap-2.5 transition-colors"
                      >
                        <Upload className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                        <span>Upload or Replace Resume</span>
                      </button>
                    )}
                  </div>

                  {/* Profile Switching Section */}
                  {candidateSummaries.length > 0 && (
                    <div className="border-t border-zinc-100 dark:border-zinc-800/80 pt-1.5 pb-1">
                      <div className="px-4 py-1 flex items-center justify-between text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
                        <span>Switch Profiles</span>
                        <Users className="w-3 h-3 text-zinc-400" />
                      </div>
                      <div className="max-h-40 overflow-y-auto px-1">
                        {candidateSummaries.map((summary) => {
                          const isCurrent = summary.user_id === candidateId;
                          return (
                            <button
                              key={summary.user_id}
                              onClick={() => {
                                if (onSelectCandidate) onSelectCandidate(summary.user_id);
                                setMenuOpen(false);
                              }}
                              className={`w-full text-left px-3 py-1.5 rounded-lg text-xs flex items-center justify-between transition-colors ${
                                isCurrent
                                  ? 'bg-teal-50 dark:bg-teal-950/50 text-teal-700 dark:text-teal-300 font-semibold'
                                  : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                              }`}
                            >
                              <div className="truncate pr-2">
                                <span className="block truncate">{summary.display_name}</span>
                                <span className="text-[10px] text-zinc-400 block truncate">
                                  {summary.target_role || summary.user_id}
                                </span>
                              </div>
                              {isCurrent && <Check className="w-3.5 h-3.5 shrink-0 text-teal-600" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Create New Profile */}
                  <div className="border-t border-zinc-100 dark:border-zinc-800/80 pt-1 px-1">
                    <button
                      onClick={() => {
                        if (onNewProfile) onNewProfile();
                        setMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-1.5 rounded-lg text-xs font-medium text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-950/40 flex items-center gap-2 transition-colors"
                    >
                      <PlusCircle className="w-3.5 h-3.5" />
                      <span>Create New Profile...</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile & Tablet Bottom Navigation Bar (Fixed for screens < 1024px) */}
      <nav
        aria-label="Mobile Navigation"
        className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md border-t border-zinc-200 dark:border-zinc-800 lg:hidden px-2 py-1 shadow-lg"
        style={{ paddingBottom: 'calc(0.4rem + env(safe-area-inset-bottom, 0px))' }}
      >
        <div className="grid grid-cols-4 max-w-md mx-auto">
          <button
            onClick={() => onTabChange('discover')}
            className={`flex flex-col items-center justify-center py-1.5 px-1 rounded-xl transition-all min-h-[48px] active:scale-95 ${
              activeTab === 'discover'
                ? 'text-teal-600 dark:text-teal-400 font-semibold'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            <Compass className={`w-5 h-5 mb-0.5 ${activeTab === 'discover' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
            <span className="text-[10px] leading-tight font-medium">Discovery</span>
          </button>

          <button
            onClick={() => onTabChange('career')}
            className={`flex flex-col items-center justify-center py-1.5 px-1 rounded-xl transition-all min-h-[48px] active:scale-95 ${
              activeTab === 'career' || activeTab === 'profile'
                ? 'text-teal-600 dark:text-teal-400 font-semibold'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            <User className={`w-5 h-5 mb-0.5 ${activeTab === 'career' || activeTab === 'profile' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
            <span className="text-[10px] leading-tight font-medium">My Career</span>
          </button>

          <button
            onClick={() => onTabChange('market')}
            className={`flex flex-col items-center justify-center py-1.5 px-1 rounded-xl transition-all min-h-[48px] active:scale-95 ${
              activeTab === 'market'
                ? 'text-teal-600 dark:text-teal-400 font-semibold'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            <TrendingUp className={`w-5 h-5 mb-0.5 ${activeTab === 'market' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
            <span className="text-[10px] leading-tight font-medium truncate max-w-full">Market</span>
          </button>

          <button
            onClick={() => onTabChange('activity')}
            className={`flex flex-col items-center justify-center py-1.5 px-1 rounded-xl transition-all min-h-[48px] active:scale-95 ${
              activeTab === 'activity'
                ? 'text-teal-600 dark:text-teal-400 font-semibold'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            <History className={`w-5 h-5 mb-0.5 ${activeTab === 'activity' ? 'text-teal-600 dark:text-teal-400' : ''}`} />
            <span className="text-[10px] leading-tight font-medium">Activity</span>
          </button>
        </div>
      </nav>
    </header>
  );
};

'use client';

import React from 'react';
import {
  Compass,
  Search,
  BarChart3,
  UserCheck,
  Target,
  Activity,
  Sun,
  Moon,
  Terminal,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

export type WorkspaceTab =
  | 'discover'
  | 'search'
  | 'market'
  | 'profile'
  | 'development'
  | 'career-path';

interface HeaderProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  candidateName?: string;
  candidateRole?: string;
  backendOnline?: boolean;
  isDevMode?: boolean;
  onToggleDevMode?: () => void;
  isDarkMode?: boolean;
  onToggleTheme?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  candidateName = 'Maya Chen',
  candidateRole = 'Junior ML & Backend',
  backendOnline = true,
  isDevMode = false,
  onToggleDevMode,
  isDarkMode = false,
  onToggleTheme,
}) => {
  const tabs: { id: WorkspaceTab; label: string; icon: React.ReactNode }[] = [
    { id: 'discover', label: 'Personalized Matches', icon: <Compass className="w-4 h-4" /> },
    { id: 'search', label: 'Market Search', icon: <Search className="w-4 h-4" /> },
    { id: 'market', label: 'Market Intelligence', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'profile', label: 'Profile & Evidence', icon: <UserCheck className="w-4 h-4" /> },
    { id: 'career-path', label: 'Career Growth & Gaps', icon: <Target className="w-4 h-4" /> },
  ];

  return (
    <header className="border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md sticky top-0 z-30 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-16 flex items-center justify-between gap-4">
          {/* Logo & Platform Tag */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-teal-600 dark:bg-teal-500 flex items-center justify-center text-white font-bold text-xs tracking-wider shadow-xs">
              JF
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 leading-tight">
                  JobFalcon
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
                  Workspace
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 hidden sm:block">
                Evidence-First Career Intelligence Workstation
              </p>
            </div>
          </div>

          {/* Core Workspaces Navigation */}
          <nav className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800/80 p-1 rounded-xl border border-zinc-200/80 dark:border-zinc-700/80 overflow-x-auto max-w-full">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 whitespace-nowrap ${
                    isActive
                      ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs border border-zinc-200/80 dark:border-zinc-700'
                      : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
                  }`}
                >
                  <span className={isActive ? 'text-teal-600 dark:text-teal-400' : ''}>
                    {tab.icon}
                  </span>
                  <span className="hidden md:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Actions & Health Indicator */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Developer Observability Mode Toggle */}
            {onToggleDevMode && (
              <button
                onClick={onToggleDevMode}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono transition-all border ${
                  isDevMode
                    ? 'bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300'
                    : 'bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200'
                }`}
                title="Toggle Technical Observability & LangGraph Traces"
              >
                <Terminal className="w-3.5 h-3.5" />
                <span className="hidden lg:inline">{isDevMode ? 'Dev Mode: ON' : 'Dev Mode'}</span>
              </button>
            )}

            {/* Theme Toggle Button */}
            {onToggleTheme && (
              <button
                onClick={onToggleTheme}
                className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 transition-colors"
                title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                aria-label="Toggle Theme"
              >
                {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-zinc-600" />}
              </button>
            )}

            {/* User Info */}
            <div className="hidden xl:flex flex-col items-end text-right pl-1">
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 leading-tight">
                {candidateName}
              </span>
              <span className="text-[10px] text-zinc-400 font-mono truncate max-w-[140px]">
                {candidateRole}
              </span>
            </div>

            <Badge
              variant={backendOnline ? 'verified' : 'disqualified'}
              size="sm"
              icon={<Activity className="w-3 h-3" />}
              mono
            >
              {backendOnline ? 'ONLINE' : 'OFFLINE'}
            </Badge>
          </div>
        </div>
      </div>
    </header>
  );
};

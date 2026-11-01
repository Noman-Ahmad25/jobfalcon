'use client';

import React from 'react';
import { Compass, UserCheck, Target, TrendingUp, Activity } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

export type WorkspaceTab = 'discover' | 'profile' | 'development' | 'career-path';

interface HeaderProps {
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  candidateName?: string;
  candidateRole?: string;
  backendOnline?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  candidateName = 'Maya Chen',
  candidateRole = 'Junior ML & Backend',
  backendOnline = true,
}) => {
  const tabs: { id: WorkspaceTab; label: string; icon: React.ReactNode }[] = [
    { id: 'discover', label: 'Discovery & Matches', icon: <Compass className="w-4 h-4" /> },
    { id: 'profile', label: 'Profile & Evidence', icon: <UserCheck className="w-4 h-4" /> },
    { id: 'development', label: 'Development & Gaps', icon: <Target className="w-4 h-4" /> },
    { id: 'career-path', label: 'Career Paths', icon: <TrendingUp className="w-4 h-4" /> },
  ];

  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-16 flex items-center justify-between gap-4">
          {/* Logo & Platform Tag */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-white dark:text-zinc-900 font-bold text-xs tracking-wider shadow-xs">
              JF
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 leading-tight">
                  JobFalcon
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
                  v1.0-local
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 hidden sm:block">
                Precision Career Intelligence Workstation
              </p>
            </div>
          </div>

          {/* Core Workspaces Navigation */}
          <nav className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800/80 p-1 rounded-lg border border-zinc-200/80 dark:border-zinc-700/80">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
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

          {/* Active Profile & Health Indicator */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="hidden lg:flex flex-col items-end text-right">
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 leading-tight">
                {candidateName}
              </span>
              <span className="text-[10px] text-zinc-400 font-mono">
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

import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-zinc-200 bg-white sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-zinc-900 flex items-center justify-center text-white font-bold text-sm tracking-wider shadow-sm">
            JF
          </div>
          <div>
            <h1 className="text-base font-semibold text-zinc-900 leading-tight">JobFalcon</h1>
            <p className="text-xs text-zinc-500">Agentic Career Intelligence Platform</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-zinc-500 bg-zinc-100 px-2 py-1 rounded border border-zinc-200">
            Phase 1 • Vertical Foundation
          </span>
        </div>
      </div>
    </header>
  );
};

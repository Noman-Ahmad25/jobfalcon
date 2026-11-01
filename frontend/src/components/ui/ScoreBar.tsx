import React from 'react';

interface ScoreBarProps {
  label: string;
  score: number; // 0.00 to 1.00
  weight?: number;
  rationale?: string;
  className?: string;
}

export function ScoreBar({
  label,
  score,
  weight,
  rationale,
  className = '',
}: ScoreBarProps) {
  const percentage = Math.min(Math.max(score * 100, 0), 100);

  // Semantic color based on score threshold
  const barColor =
    percentage >= 75
      ? 'bg-emerald-500 dark:bg-emerald-400'
      : percentage >= 50
      ? 'bg-teal-500 dark:bg-teal-400'
      : percentage >= 30
      ? 'bg-amber-500 dark:bg-amber-400'
      : 'bg-zinc-400 dark:bg-zinc-500';

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-zinc-700 dark:text-zinc-300">
          {label}
        </span>
        <div className="flex items-center gap-2">
          {weight !== undefined && (
            <span className="text-[11px] text-zinc-400 font-mono">
              w: {(weight * 100).toFixed(0)}%
            </span>
          )}
          <span className="font-mono font-semibold text-zinc-900 dark:text-zinc-100">
            {percentage.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Progress Track */}
      <div className="h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden border border-zinc-200/50 dark:border-zinc-700/50">
        <div
          className={`h-full rounded-full transition-all duration-300 ease-out ${barColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {rationale && (
        <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-tight">
          {rationale}
        </p>
      )}
    </div>
  );
}

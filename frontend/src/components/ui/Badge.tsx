import React from 'react';

export type BadgeVariant =
  | 'verified'
  | 'caveat'
  | 'disqualified'
  | 'neutral'
  | 'teal'
  | 'outline';

interface BadgeProps {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  children: React.ReactNode;
  mono?: boolean;
  className?: string;
  title?: string;
}

export function Badge({
  variant = 'neutral',
  size = 'md',
  icon,
  children,
  mono = false,
  className = '',
  title,
}: BadgeProps) {
  const sizeClasses =
    size === 'sm'
      ? 'px-2 py-0.5 text-xs'
      : 'px-2.5 py-1 text-xs sm:text-xs font-medium';

  const variantClasses = {
    verified:
      'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60',
    caveat:
      'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60',
    disqualified:
      'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60',
    neutral:
      'bg-zinc-100 text-zinc-700 border border-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700',
    teal:
      'bg-teal-50 text-teal-700 border border-teal-200 dark:bg-teal-950/40 dark:text-teal-300 dark:border-teal-800/60',
    outline:
      'bg-transparent text-zinc-600 border border-zinc-300 dark:text-zinc-400 dark:border-zinc-700',
  }[variant];

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-md font-sans tracking-tight transition-colors ${sizeClasses} ${variantClasses} ${
        mono ? 'font-mono' : ''
      } ${className}`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
}

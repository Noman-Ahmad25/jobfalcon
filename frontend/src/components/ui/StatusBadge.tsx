import React from 'react';

export type StatusVariant = 'ok' | 'ready' | 'degraded' | 'error' | 'loading' | 'offline';

interface StatusBadgeProps {
  status: StatusVariant;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = '' }) => {
  const getVariantStyles = (): { bg: string; text: string; dot: string; defaultLabel: string } => {
    switch (status) {
      case 'ok':
      case 'ready':
        return {
          bg: 'bg-emerald-50 border-emerald-200',
          text: 'text-emerald-800',
          dot: 'bg-emerald-500',
          defaultLabel: 'Operational',
        };
      case 'degraded':
        return {
          bg: 'bg-amber-50 border-amber-200',
          text: 'text-amber-800',
          dot: 'bg-amber-500',
          defaultLabel: 'Degraded',
        };
      case 'error':
      case 'offline':
        return {
          bg: 'bg-rose-50 border-rose-200',
          text: 'text-rose-800',
          dot: 'bg-rose-500',
          defaultLabel: 'Disconnected',
        };
      case 'loading':
        return {
          bg: 'bg-zinc-100 border-zinc-200',
          text: 'text-zinc-700',
          dot: 'bg-zinc-400 animate-pulse',
          defaultLabel: 'Checking...',
        };
    }
  };

  const variant = getVariantStyles();
  const displayLabel = label || variant.defaultLabel;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${variant.bg} ${variant.text} ${className}`}
      role="status"
    >
      <span className={`w-1.5 h-1.5 rounded-full ${variant.dot}`} aria-hidden="true" />
      <span>{displayLabel}</span>
    </span>
  );
};

import React from 'react';
import { FileText, CheckCircle2, GitCommit } from 'lucide-react';
import { EvidenceSourceType } from '@/types/domain';
import { Badge } from './Badge';

interface EvidenceCardProps {
  extractedSnippet: string;
  sourceType: EvidenceSourceType | string;
  sourceUri?: string | null;
  verifiabilityWeight: number; // 0.0 to 1.0
  observedAt?: string;
  className?: string;
}

export function EvidenceCard({
  extractedSnippet,
  sourceType,
  sourceUri,
  verifiabilityWeight,
  observedAt,
  className = '',
}: EvidenceCardProps) {
  const weightPercent = (verifiabilityWeight * 100).toFixed(0);

  const getSourceIcon = () => {
    switch (sourceType) {
      case 'RESUME_WORK_EXPERIENCE':
      case 'RESUME_PROJECT':
        return <FileText className="w-3.5 h-3.5" />;
      case 'VERIFIED_CODE_REPOSITORY':
        return <GitCommit className="w-3.5 h-3.5" />;
      default:
        return <CheckCircle2 className="w-3.5 h-3.5" />;
    }
  };

  const getSourceLabel = () => {
    switch (sourceType) {
      case 'RESUME_WORK_EXPERIENCE':
        return 'Work Experience';
      case 'RESUME_PROJECT':
        return 'Project Portfolio';
      case 'VERIFIED_CODE_REPOSITORY':
        return 'Code Repository';
      case 'ACADEMIC_TRANSCRIPT':
        return 'Academic Record';
      case 'CERTIFICATION':
        return 'Certification';
      case 'LIVE_ATS_POSTING':
        return 'Direct Job Description';
      default:
        return sourceType.replace(/_/g, ' ');
    }
  };

  return (
    <div
      className={`p-3.5 rounded-lg bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700/80 space-y-2 text-xs ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <Badge
          variant="outline"
          size="sm"
          icon={getSourceIcon()}
          className="text-[11px]"
        >
          {getSourceLabel()}
        </Badge>

        <div className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-500">
          <span>Verifiability:</span>
          <span
            className={`font-semibold ${
              verifiabilityWeight >= 0.85
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-amber-600 dark:text-amber-400'
            }`}
          >
            {weightPercent}%
          </span>
        </div>
      </div>

      <blockquote className="italic text-zinc-700 dark:text-zinc-300 font-sans border-l-2 border-teal-500/70 pl-2.5 py-0.5 leading-relaxed break-words">
        &ldquo;{extractedSnippet}&rdquo;
      </blockquote>

      {(sourceUri || observedAt) && (
        <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono pt-1">
          {sourceUri && (
            <span className="truncate max-w-[280px]" title={sourceUri}>
              URI: {sourceUri}
            </span>
          )}
          {observedAt && (
            <span>
              Observed: {new Date(observedAt).toLocaleDateString()}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

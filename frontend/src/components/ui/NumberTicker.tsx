'use client';

import React, { useEffect, useState } from 'react';

interface NumberTickerProps {
  value: number;
  decimals?: number;
  durationMs?: number;
  suffix?: string;
  className?: string;
}

export function NumberTicker({
  value,
  decimals = 1,
  durationMs = 400,
  suffix = '%',
  className = '',
}: NumberTickerProps) {
  const [displayValue, setDisplayValue] = useState<number>(() => {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return value;
    }
    return 0;
  });

  useEffect(() => {
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      return;
    }

    let startTimestamp: number | null = null;
    let animationFrameId: number;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / durationMs, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      const current = value * easedProgress;

      setDisplayValue(current);

      if (progress < 1) {
        animationFrameId = window.requestAnimationFrame(step);
      }
    };

    animationFrameId = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(animationFrameId);
  }, [value, durationMs]);

  return (
    <span className={`tabular-nums font-mono font-bold tracking-tight ${className}`}>
      {displayValue.toFixed(decimals)}
      {suffix}
    </span>
  );
}

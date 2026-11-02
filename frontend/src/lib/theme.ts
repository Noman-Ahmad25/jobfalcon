'use client';

import { useSyncExternalStore } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';

export function getStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'system';
  const stored = localStorage.getItem('jf_theme') as ThemeMode;
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return 'system';
}

export function applyTheme(mode: ThemeMode): void {
  if (typeof window === 'undefined') return;

  const root = document.documentElement;
  const isDark =
    mode === 'dark' ||
    (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  if (isDark) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }

  localStorage.setItem('jf_theme', mode);
  window.dispatchEvent(new Event('jf_theme_change'));
}

const emptySubscribe = () => () => {};

export function useIsMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}

export function useIsDarkMode(): boolean {
  return useSyncExternalStore(
    (callback) => {
      if (typeof window === 'undefined') return () => {};
      window.addEventListener('jf_theme_change', callback);
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      media.addEventListener('change', callback);
      return () => {
        window.removeEventListener('jf_theme_change', callback);
        media.removeEventListener('change', callback);
      };
    },
    () => {
      if (typeof window === 'undefined') return false;
      const stored = getStoredTheme();
      return (
        stored === 'dark' ||
        (stored === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
      );
    },
    () => false
  );
}

'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { getBackendHealth } from '@/lib/api';
import { HealthStatusResponse } from '@/types/api';
import { StatusBadge } from '@/components/ui/StatusBadge';

export const HealthMonitor: React.FC = () => {
  const [data, setData] = useState<HealthStatusResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const executeProbe = useCallback(async () => {
    const start = performance.now();
    try {
      const response = await getBackendHealth();
      const elapsed = Math.round(performance.now() - start);
      setData(response);
      setLatencyMs(elapsed);
      setError(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to reach API server';
      setError(message);
      setData(null);
      setLatencyMs(null);
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }, []);

  const handleManualProbe = useCallback(() => {
    setLoading(true);
    setError(null);
    executeProbe();
  }, [executeProbe]);

  useEffect(() => {
    let isMounted = true;

    const initialProbe = async () => {
      const start = performance.now();
      try {
        const response = await getBackendHealth();
        if (!isMounted) return;
        const elapsed = Math.round(performance.now() - start);
        setData(response);
        setLatencyMs(elapsed);
        setError(null);
      } catch (err: unknown) {
        if (!isMounted) return;
        const message = err instanceof Error ? err.message : 'Failed to reach API server';
        setError(message);
        setData(null);
        setLatencyMs(null);
      } finally {
        if (isMounted) {
          setLoading(false);
          setLastChecked(new Date());
        }
      }
    };

    initialProbe();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section 
      aria-labelledby="system-health-heading"
      className="bg-white rounded-xl border border-zinc-200 shadow-sm p-6 max-w-2xl w-full"
    >
      <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
        <div>
          <h2 id="system-health-heading" className="text-base font-semibold text-zinc-900">
            Backend API Health Status
          </h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Real-time communication probe between Next.js and FastAPI
          </p>
        </div>

        {loading ? (
          <StatusBadge status="loading" />
        ) : error ? (
          <StatusBadge status="error" label="Unreachable" />
        ) : (
          <StatusBadge status="ok" label="Operational" />
        )}
      </div>

      <div className="py-4 space-y-3" role="status" aria-live="polite">
        {loading && !data && (
          <div className="py-8 text-center text-sm text-zinc-500 animate-pulse">
            Connecting to FastAPI backend...
          </div>
        )}

        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-900 space-y-1.5">
            <div className="font-semibold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              Connection Error
            </div>
            <p className="font-mono break-all">{error}</p>
            <p className="text-zinc-600 pt-1 text-[11px]">
              Make sure the backend is running locally at <code className="bg-white px-1 py-0.5 rounded border border-rose-200">http://localhost:8000</code>.
            </p>
          </div>
        )}

        {data && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
            <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100">
              <dt className="text-zinc-500 font-medium">Service Name</dt>
              <dd className="font-semibold text-zinc-900 mt-0.5">FastAPI Modular Core</dd>
            </div>

            <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100">
              <dt className="text-zinc-500 font-medium">Status</dt>
              <dd className="font-semibold text-emerald-700 mt-0.5 capitalize flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                {data.status}
              </dd>
            </div>

            <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100">
              <dt className="text-zinc-500 font-medium">API Version</dt>
              <dd className="font-mono text-zinc-800 mt-0.5">{data.version}</dd>
            </div>

            <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100">
              <dt className="text-zinc-500 font-medium">Environment</dt>
              <dd className="font-mono text-zinc-800 mt-0.5 uppercase tracking-wide">{data.environment}</dd>
            </div>

            <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100">
              <dt className="text-zinc-500 font-medium">Latency</dt>
              <dd className="font-mono text-zinc-800 mt-0.5">
                {latencyMs !== null ? `${latencyMs} ms` : '—'}
              </dd>
            </div>

            <div className="p-3 bg-zinc-50 rounded-lg border border-zinc-100">
              <dt className="text-zinc-500 font-medium">Internal Probes</dt>
              <dd className="font-mono text-zinc-800 mt-0.5">
                {Object.entries(data.services)
                  .map(([svc, stat]) => `${svc}: ${stat}`)
                  .join(', ')}
              </dd>
            </div>
          </dl>
        )}
      </div>

      <div className="pt-3 border-t border-zinc-100 flex items-center justify-between text-xs text-zinc-500">
        <span>
          {lastChecked ? `Checked ${lastChecked.toLocaleTimeString()}` : 'Not checked yet'}
        </span>

        <button
          type="button"
          onClick={handleManualProbe}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-900 text-white hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-2"
        >
          {loading ? (
            <>
              <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Probing...
            </>
          ) : (
            'Probe Backend'
          )}
        </button>
      </div>
    </section>
  );
};

import React from 'react';
import { Header } from '@/components/layout/Header';
import { HealthMonitor } from '@/components/health/HealthMonitor';
import { DeterministicPipelineDemo } from '@/components/pipeline/DeterministicPipelineDemo';
import { CandidateProfilingDemo } from '@/components/profiling/CandidateProfilingDemo';
import { DiscoveryDemo } from '@/components/discovery/DiscoveryDemo';

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-50 flex flex-col font-sans text-zinc-900">
      <Header />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        {/* Workspace Introduction */}
        <div className="space-y-3">
          <h2 className="text-2xl font-bold tracking-tight text-zinc-900">
            Career Opportunity Recommendation System
          </h2>
          <p className="text-sm text-zinc-600 max-w-3xl leading-relaxed">
            Welcome to the vertical foundation of JobFalcon. This environment coordinates
            a modular FastAPI backend with a Next.js App Router frontend, strictly establishing
            the separation between deterministic application rules and future agentic AI orchestration.
          </p>
        </div>

        {/* Live Backend Communication & Health Check */}
        <div className="flex flex-col items-start gap-4">
          <HealthMonitor />
        </div>

        {/* Milestone 6: Candidate Skill Profiling & Evidence Extraction */}
        <section aria-labelledby="profiling-demo-heading" className="space-y-4">
          <h3 id="profiling-demo-heading" className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
            AI-Powered Candidate Skill Profiling & Evidence Grounding
          </h3>
          <CandidateProfilingDemo />
        </section>

        {/* Milestone 7: Skill-to-Role Mapping & Multi-Source Discovery */}
        <section aria-labelledby="discovery-demo-heading" className="space-y-4">
          <h3 id="discovery-demo-heading" className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
            Multi-Source Discovery Foundation & Skill-to-Role Mapping
          </h3>
          <DiscoveryDemo />
        </section>

        {/* Milestone 4: Deterministic Core Integration Demo */}
        <section aria-labelledby="pipeline-demo-heading" className="space-y-4">
          <h3 id="pipeline-demo-heading" className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
            Deterministic Pipeline Execution
          </h3>
          <DeterministicPipelineDemo />
        </section>


        {/* Core Architecture Invariant Cards */}
        <section aria-labelledby="architecture-principles-heading" className="space-y-4">
          <h3 id="architecture-principles-heading" className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
            System Invariants & Boundaries
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-white p-5 rounded-xl border border-zinc-200 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700 font-semibold text-xs">
                01
              </div>
              <h4 className="text-sm font-semibold text-zinc-900">Deterministic Primacy</h4>
              <p className="text-xs text-zinc-600 leading-normal">
                Hard eligibility gates, graduation window verification, and multi-dimensional scoring math
                execute exclusively in deterministic code with zero LLM bypass.
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-zinc-200 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700 font-semibold text-xs">
                02
              </div>
              <h4 className="text-sm font-semibold text-zinc-900">Modular Monolith</h4>
              <p className="text-xs text-zinc-600 leading-normal">
                Standard application services (auth, profiles, saved opportunities) are cleanly decoupled
                from AI orchestration workflows without introducing premature microservices.
              </p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-zinc-200 shadow-sm space-y-2">
              <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center text-zinc-700 font-semibold text-xs">
                03
              </div>
              <h4 className="text-sm font-semibold text-zinc-900">Evidence Provenance</h4>
              <p className="text-xs text-zinc-600 leading-normal">
                Every skill assessment, recommendation explanation, and career match is anchored to
                discrete, verifiable evidence records with epistemic confidence calibration.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-200 bg-white py-6 text-center text-xs text-zinc-500">
        <div className="max-w-6xl mx-auto px-4">
          JobFalcon Architecture v1.0 • Initial Working Vertical Foundation
        </div>
      </footer>
    </div>
  );
}

---
name: frontend-engineering
description: Implement frontend applications using Next.js, React, TypeScript, and Tailwind CSS. Use when building App Router pages, client/server components, typed API clients, SSE streaming consumers, or integrating with modern-web-guidance.
---

# Frontend Engineering & Next.js Implementation

This skill guides the implementation of JobFalcon's web application using **Next.js (App Router)**, **React**, **TypeScript**, and **Tailwind CSS**.

---

## 1. When to Use This Skill

- Implementing App Router pages, layouts, and route handlers under `frontend/src/app/`.
- Building reusable UI components conforming to JobFalcon's design system tokens.
- Consuming Server-Sent Events (SSE) streaming endpoints for agent execution telemetry.
- Defining TypeScript types that strictly mirror backend Pydantic v2 schemas.
- Setting up error boundaries, suspense fallbacks, and optimistic UI updates.
- Optimizing Core Web Vitals (LCP, INP, CLS) and ensuring web standards compliance.

---

## 2. Technical Stack & Architecture

```text
frontend/src/
├── app/
│   ├── layout.tsx             # Root layout with providers & global metadata
│   ├── page.tsx               # Landing / workspace overview
│   ├── dashboard/             # Main candidate recommendations & feed
│   ├── profile/               # Career profile, skills editor, & resume upload
│   └── opportunities/         # Search, filter, and comparison catalog
├── components/
│   ├── ui/                    # Base primitives (buttons, inputs, dialogs, badges)
│   ├── recommendation/        # Opportunity cards, 6D score graphs, evidence drawer
│   ├── telemetry/             # Agent execution progress feed & status badges
│   └── profile/               # Assessed skill badges, career path nodes
├── lib/
│   ├── api.ts                 # Strongly typed fetch client with error handling
│   ├── sse.ts                 # SSE connection manager with auto-reconnect
│   └── utils.ts               # Classnames, date formatters, math utilities
└── types/
    ├── api.ts                 # TypeScript types mirroring Pydantic models
    └── telemetry.ts           # Agent progress event types
```

---

## 3. Workflow: Implementing Frontend Features

### Step 1: Consult `modern-web-guidance` First
Before implementing new components or client-side interactions, execute `modern-web-guidance`:
```bash
npx -y modern-web-guidance@latest search "<component or web feature>"
```
Follow standardized HTML/CSS patterns, dialog popovers, container queries, and accessibility best practices rather than adding heavy third-party UI libraries.

### Step 2: Server vs. Client Component Boundaries
- **Server Components (Default)**: Use for initial page data fetching, metadata generation, and static structural layouts.
- **Client Components (`'use client'`)**: Confine strictly to components requiring browser APIs, interactive form state, modal toggling, or SSE event listeners.

```tsx
// frontend/src/components/telemetry/AgentProgressFeed.tsx
'use client';

import React, { useEffect, useState } from 'react';
import type { AgentWorkflowEvent } from '@/types/telemetry';

export function AgentProgressFeed({ sessionId }: { sessionId: string }) {
  const [events, setEvents] = useState<AgentWorkflowEvent[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);

  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/recommendations/stream?session_id=${sessionId}`);

    eventSource.onmessage = (event) => {
      const data: AgentWorkflowEvent = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
      if (data.status === 'SUCCESS' || data.status === 'ERROR') {
        setIsCompleted(true);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm" role="status" aria-live="polite">
      <h3 className="text-sm font-semibold text-zinc-900">Career Agent Orchestration</h3>
      <ul className="mt-3 space-y-2">
        {events.map((evt, idx) => (
          <li key={idx} className="flex items-center gap-2 text-xs text-zinc-600">
            <span className="h-2 w-2 rounded-full bg-teal-500" />
            <span>{evt.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Step 3: Type Safety & Schema Mirroring
- Ensure all frontend API request bodies and response types match backend Pydantic models exactly:
```typescript
// frontend/src/types/api.ts
export type OpportunityCategory = 
  | 'INTERNSHIP' 
  | 'FULL_TIME_JOB' 
  | 'PART_TIME_JOB' 
  | 'APPRENTICESHIP' 
  | 'FELLOWSHIP' 
  | 'CONTRACT';

export interface SixDimensionalScoreBreakdown {
  skill_match_score: number;
  career_match_score: number;
  growth_potential_score: number;
  market_relevance_score: number;
  user_preference_score: number;
  opportunity_quality_score: number;
  composite_total_score: number;
}
```

### Step 4: Verification & Performance Auditing
- Verify accessibility with `a11y-debugging` and ensure no missing labels or broken focus traps exist.
- Audit Largest Contentful Paint (LCP) with `debug-optimize-lcp`, ensuring hero elements and fonts load efficiently without layout shifts.

---

## 4. Frontend Constraints & Anti-Patterns

- ❌ **DO NOT** duplicate complex scoring or eligibility calculations in client-side code. The backend is the single source of truth.
- ❌ **DO NOT** make every component a client component (`'use client'`). Maximize Server Components for speed and SEO.
- ❌ **DO NOT** introduce bloated styling libraries or arbitrary CSS frameworks; adhere strictly to Tailwind CSS and modern CSS standards.
- ❌ **DO NOT** leave SSE event sources open on component unmount; always clean up subscriptions.
- ❌ **DO NOT** hardcode API secrets or sensitive tokens in client-accessible bundles.

---

## 5. Verification Checklist

Before completing a frontend engineering task:
- [ ] TypeScript compiles cleanly with zero errors: `tsc --noEmit`.
- [ ] ESLint passes without errors: `npm run lint`.
- [ ] Server and Client boundaries are appropriately separated.
- [ ] Accessibility validated (semantic HTML, ARIA attributes, keyboard navigation).
- [ ] Reconnections and error states in SSE consumers are tested.

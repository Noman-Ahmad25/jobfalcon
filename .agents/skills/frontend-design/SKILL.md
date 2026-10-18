---
name: frontend-design
description: UX/UI product design for JobFalcon's agentic career intelligence platform. Use when designing user interfaces, establishing design tokens, designing transparent recommendation cards, laying out multi-step agent activity feeds, or preventing cliché AI UI tropes.
---

# Frontend Design & Product UX

This skill guides the visual design, user experience, typography, component patterns, and aesthetic philosophy for **JobFalcon**, an Agentic Career Opportunity Recommendation System.

---

## 1. When to Use This Skill

- Designing or refining user flows for resume uploading, profile verification, and opportunity exploration.
- Designing transparent recommendation cards with interactive 6-dimensional score breakdowns.
- Visualizing multi-agent execution progress, streaming telemetry feeds, and degraded state banners.
- Establishing design tokens (color palettes, typography scale, spacing grids, elevation).
- Crafting accessible states for empty pools, query expansion notices, and ungrounded claim warnings.
- Preventing clichéd or generic AI interface tropes.

---

## 2. Product Design Philosophy & Aesthetics

JobFalcon is a **precision career intelligence tool**, not a generic marketing landing page or a flashy AI toy. Its design must convey rigor, trust, and clarity:

### 1. Function-Driven Information Hierarchy
- **Evidence Inspectability First**: Every skill rating, matched qualification, and career recommendation must offer a one-click path to view its underlying verifiable evidence snippet.
- **Transparent Scoring**: Show the deterministic 6-dimensional breakdown ($S_{\text{skill}}, S_{\text{career}}, S_{\text{growth}}, S_{\text{market}}, S_{\text{pref}}, S_{\text{qual}}$) with clear, understandable visual bars—never an opaque, magical single number.
- **Explicit Eligibility Disclosure**: Clearly state why an opportunity is eligible (e.g., "Verified: Visa sponsorship offered • Graduation date matches 2027 window") or why excluded opportunities were filtered out.

### 2. Visual System & Design Tokens
- **Palette**: Sophisticated, functional palette with high contrast:
  - Background: Crisp, neutral canvas (e.g., slate/zinc neutrals `slate-50` / `zinc-900`).
  - Text: Deep, readable tones (`zinc-900` / `zinc-100`) meeting WCAG AAA for body text.
  - Accent / Primary: Deliberate, purposeful color (e.g., deep aerospace teal or refined indigo).
  - Status Semantics: Amber for degraded/stale cache warnings, Emerald for verified eligibility, Rose for disqualification or critical errors.
- **Typography**: Clean, geometric sans-serif (e.g., Inter, Geist, or Plus Jakarta Sans) with tracked letter-spacing, clear hierarchy, and tabular numbers for scores.

---

## 3. Workflow: Interface Patterns for Agentic Workspaces

### Step 1: Design the Agent Progress Feed (Streaming UX)
- While the Hierarchical Supervisor executes (up to 30s cold start), display meaningful, calibrated progress:
  - Show active agent phases: *Analyzing Resume & Skills* $\rightarrow$ *Researching Labor Market* $\rightarrow$ *Discovering Opportunities* $\rightarrow$ *Applying Eligibility Rules* $\rightarrow$ *Ranking & Generating Rationale*.
  - Differentiate high-level milestone progress from raw internal operational logs.
  - Allow the user to minimize the progress feed while retaining background notification readiness.

### Step 2: Design the Transparent Opportunity Recommendation Card
Every recommended opportunity must present:
1. **Header**: Role title, verified company name, location, work mode, and opportunity category badge (Internship, Full-Time, Fellowship).
2. **Total Score & Confidence Indicator**: Prominent composite score percentage with explicit note of deterministic calculation.
3. **Six-Dimensional Radar or Bar Breakdown**: Interactive visual showing skill fit, market momentum, and growth potential.
4. **Verifiable Rationale**: Grounded explanation citing exact candidate skills and market demand trends.
5. **Growth Skill Trajectory**: Highlight the specific skills the candidate will acquire in this role.

### Step 3: Design Degraded & Partial Result Indicators
- When discovery expands to adjacent career paths (Level 2 expansion) because primary roles yielded $< 5$ candidates:
  - Display an informative banner: *"Expanded to adjacent career paths (e.g., Cloud Platform Engineering) to provide high-quality matching opportunities."*
- When market data is served from cache:
  - Display a subtle freshness indicator: *"Market trend data refreshed 4 days ago."*

---

## 4. Design Constraints & Anti-Patterns

### Forbidden Cliché AI Design Tropes
Unless explicitly requested, **STRICTLY AVOID**:
- ❌ **No Purple on Dark**: No neon violet, magenta, or glowing purple accents on pitch-black backgrounds.
- ❌ **No Colored Border Accents**: Avoid glowing outlines or gradient borders around cards.
- ❌ **No Icon-Stuffed Bento Boxes**: Avoid grid containers cluttered with non-functional decorative icons.
- ❌ **No Headline Biscuit Pills**: Do not place pulsing dot pills above main headlines.
- ❌ **No Gradient Keywords**: Avoid multi-color gradient fills across headline text.
- ❌ **No Over-Nested Cards**: Never nest cards within cards more than two levels deep.

### Accessibility Constraints
- Maintain minimum contrast ratio of 4.5:1 for standard text and 3:1 for large text / graphical controls.
- Full keyboard navigation: All interactive badges, tooltips, score expanders, and filters must be focusable with visible focus rings.
- Fluid responsive layout: Seamless transitions from multi-column desktop workstation down to mobile screens without horizontal scroll.

---

## 5. Verification Checklist

Before approving a frontend design:
- [ ] Interface avoids all forbidden cliché tropes (no neon purple on dark, no gradient text, no pulsing pills).
- [ ] Evidence provenance and deterministic score breakdowns are clearly inspectable.
- [ ] Agent execution states handle loading, streaming updates, partial results, and failures cleanly.
- [ ] Contrast ratios and keyboard navigation satisfy WCAG AA/AAA guidelines.

# JobFalcon — Architectural Decisions & Provisional Parameters

This document records the provisional parameters, empirical calibration requirements, and open architectural design decisions that must be explicitly validated during implementation rather than silently assumed.

---

## 1. Growth-Potential Equation & Parameter Calibration

- **Baseline Formula**:
  $$S_{\text{growth}}(u, o) = \frac{\sum_{s \in G(u, o)} M_{\text{demand}}(s, c_{\text{target}}) \cdot \left(1 - \frac{P_u(s)}{10}\right) \cdot \mathcal{B}\left(\Delta_{\text{gap}}(u, o, s)\right)}{\sum_{s \in \text{TargetSkills}(c_{\text{target}})} M_{\text{demand}}(s, c_{\text{target}})}$$
- **Status**: **Provisional Implementation (Milestone 9 Verified Baseline)**
- **Milestone 9 Baseline Implemented**:
  1. **Gaussian Zone of Proximal Development Curve $\mathcal{B}(g)$**: Implemented continuous response curve $\mathcal{B}(g) = \exp\left(-\frac{(g - 0.30)^2}{2(0.20)^2}\right)$ where $g$ represents the skill stretch ratio.
  2. **Foundational Competency Gating**: Requires candidate to satisfy $\ge 40\%$ of mandatory prerequisites; candidates lacking foundational competencies receive a $50\%$ penalty to prevent stunting growth through cognitive overwhelm.
  3. **Near-Mastery Guard**: Roles with $<10\%$ new skill requirements receive a capped growth score ($0.40$), prioritizing candidates toward opportunities with balanced career expansion.
- **Open Decisions & Calibration Tasks**:
  1. **Labor Market Demand Integration $M_{\text{demand}}(s)$**: Currently weights missing skills uniformly; live labor market dynamic demand weighting ($M_{\text{demand}} \in [1.0, 3.0]$) will be calibrated when live labor market telemetry is connected.
  2. **Career Stage Variance Tuning**: Calibrate $\sigma$ across internship cohorts ($\sigma = 0.25$) versus executive leadership transitions ($\sigma = 0.12$).

---

## 2. Skill-Proficiency & Evidence-Confidence Scoring

- **Baseline Formulas**:
  $$P(s) = \text{clip}\left(\sum_{e \in E_s} w_{\text{source}}(e) \cdot d_{\text{depth}}(e) \cdot e^{-\lambda_{\text{decay}} \cdot \Delta t(e)}, \, 1.0, \, 10.0\right)$$
  $$C(s) = 1 - \prod_{e \in E_s} \left(1 - r_{\text{verifiability}}(e)\right)$$
- **Status**: **Provisional Implementation (Milestone 6 Verified Baseline)**
- **Milestone 6 Baseline Implemented**:
  1. **Evidence Grounding**: Extracted skills in `CandidateCareerProfile` must anchor to one or more verbatim `EvidenceRecord` snippets with categorized source types (`RESUME_WORK_EXPERIENCE`, `RESUME_PROJECT`, `CERTIFICATION`, `SELF_REPORTED_UNVERIFIED`).
  2. **Stated vs Inferred Tracking**: Flagged explicitly via `is_explicitly_stated` so downstream ranking can distinguish verified direct claims from contextually inferred technologies.
  3. **Epistemic Uncertainty Surfacing**: Ambiguities, contradictory timelines, and unsupported claims are captured in `epistemic_uncertainties` rather than hallucinating values.
- **Open Decisions & Calibration Tasks**:
  1. **Temporal Decay Constant $\lambda_{\text{decay}}$**: Needs calibration by domain (e.g., web frameworks evolve faster than fundamental algorithms).
  2. **Source Weight Calibration $w_{\text{source}}(e)$**: Proposed weights (1.0 for production experience / verified repos, 0.6 for academic coursework, 0.25 for uncorroborated keywords) must be benchmarked against human technical recruiter baselines.
  3. **Complexity Depth Function $d_{\text{depth}}(e)$**: Concrete heuristic or model-based extraction for measuring repository or project complexity must be defined and tested against adversarial fluff.


---

## 3. Handling of Unknown / Missing Eligibility Information

- **Context**: Real-world job listings and candidate profiles frequently omit explicit fields (e.g., visa sponsorship unspecified, graduation date range not mentioned, GPA requirements absent, rolling deadlines).
- **Status**: **Provisional Implementation (Milestone 2 Verified)**
- **Options Evaluated**:
  1. **Strict Exclusion (Fail-Closed)**: Disqualify opportunities or candidates whenever mandatory fields are missing. Guarantees 0% false positives for eligibility but drastically lowers opportunity recall.
  2. **Optimistic Inclusion with Soft Warning (Fail-Open)**: Mark unstated eligibility criteria as `ELIGIBILITY_UNCERTAIN`, permit ranking, but flag clearly in the UI that the user must verify specific terms.
  3. **Interactive Candidate Clarification**: For ambiguous candidate profile attributes, trigger a quick interactive prompt prior to running full ranking.
- **Milestone 2 Conservative Baseline Implemented**:
  - **Three-Valued Status**: Aggregate eligibility evaluates to `ELIGIBLE` (all criteria explicitly satisfied), `ELIGIBLE_WITH_UNCERTAINTY` (no hard violations found, but missing attributes flagged as caveats), or `INELIGIBLE` (one or more confirmed rule failures).
  - **Confirmed Failures**: Produce `is_eligible = False` and populate `disqualification_reasons` with standardized codes (`DISQ_CATEGORY_MISMATCH`, `DISQ_COUNTRY_UNAUTHORIZED`, `DISQ_VISA_SPONSORSHIP_UNAVAILABLE`, `DISQ_DEGREE_BELOW_MINIMUM`, `DISQ_STUDENT_STATUS_REQUIRED`, `DISQ_GRADUATION_DATE_BEFORE_WINDOW`, `DISQ_GRADUATION_DATE_AFTER_WINDOW`, `DISQ_EXPERIENCE_BELOW_MINIMUM`, `DISQ_EXPERIENCE_EXCEEDS_MAXIMUM`, `DISQ_WORK_MODE_MISMATCH`, `DISQ_LOCATION_MISMATCH`, `DISQ_EXPIRED_DEADLINE`).
  - **Preserved Uncertainty**: When critical fields are unstated (missing application deadline, unrestricted candidate location on an on-site role, unstated cities on a hybrid role, or unstated graduation date during a restricted graduation cohort), the engine emits `is_eligible = True` and flags discrete caveats (`UNCERT_NO_DEADLINE_SPECIFIED`, `UNCERT_LOCATION_UNRESTRICTED`, `UNCERT_OPPORTUNITY_LOCATION_UNSPECIFIED`, `UNCERT_GRADUATION_DATE_MISSING`), preserving transparency for downstream ranking and UI display without inventing false assumptions.
  - **Zero LLM Evaluation**: All checks execute exclusively in pure Python deterministic code.

---

## 4. Ranking Weights & Minimum-Score Thresholds

- **Baseline Formula**:
  $$\text{Score}_{\text{total}} = 0.30 S_{\text{skill}} + 0.20 S_{\text{career}} + 0.20 S_{\text{growth}} + 0.12 S_{\text{market}} + 0.10 S_{\text{pref}} + 0.08 S_{\text{qual}}$$
- **Status**: **Provisional Implementation (Milestone 9 Verified Baseline)**
- **Milestone 9 Baseline Implemented**:
  1. **Multi-Dimensional Engine (`engine.py`)**: Computes all 6 dimensions deterministically in pure Python; normalizes each dimension and aggregate score strictly to $[0.0, 1.0]$.
  2. **Configurable Weight Profiles**: Supports `'DEFAULT'` (30/20/20/12/10/8), `'EARLY_CAREER'` (25/20/28/12/10/5), and `'EXPERIENCED'` (35/20/15/10/10/10) with automatic normalization to $\sum w = 1.00$.
  3. **Deterministic Separation of Eligibility**: Ineligible opportunities (`INELIGIBLE`) are strictly excluded from recommendations regardless of skill scores. Opportunities with caveats (`ELIGIBLE_WITH_UNCERTAINTY`) are ranked with explicit caveat transparency.
  4. **Deterministic Tie-Breaking**: Ordinal ranks determined by `overall_fit_score` (descending, 4 decimals) $\to$ `skill_alignment` (descending) $\to$ `completeness_score` (descending) $\to$ `opportunity_id` (alphabetical ascending).
- **Open Decisions & Calibration Tasks**:
  1. **Weights Validation Against Human Recruiter Judgments**: The linear weights are provisional baselines; ongoing calibration against human technical hiring manager judgments will fine-tune the balance between $S_{\text{skill}}$ and $S_{\text{growth}}$.
  2. **Candidate Pool Sizing**: Recommended top-K defaults to 10 for presentation; evaluate optimal batch sizes for deep multi-page candidate exploration.

---

## 5. Agent Dependencies, Partial Failures & Concurrency

- **Status**: **Provisional — Needs Validation**
- **Open Decisions & Calibration Tasks**:
  1. **Timeout Allocations**: Node timeouts (Profile: 6,000 ms, Market: 8,000 ms, Discovery: 10,000 ms, Ranking: 4,000 ms, Explanation: 5,000 ms, Global: 30,000 ms) require validation under loaded network and GPU/Ollama scenarios.
  2. **Degraded Mode Execution**: When secondary or external feeds (e.g. O*NET live API, external ATS) fail or timeout, the system should gracefully proceed with cached snapshots (`is_stale = True`) without stalling the pipeline.
  3. **Circuit Breaker Calibration**: LiteLLM circuit breaker parameters (`allowed_fails = 3`, `cooldown_time = 60s`) must be tuned to prevent flapping during minor network blips.

---

## 6. Authentication & Session Strategy

- **Status**: **Unresolved Design Decision**
- **Options to Validate**:
  1. **Token vs Cookie Session**: Stateless JWTs (asymmetric Ed25519 or RS256) vs Redis-backed server-side sessions with secure HTTP-only cookies.
  2. **Identity Providers**: Direct email/password + magic link vs OAuth2 (GitHub, Google, LinkedIn) to facilitate frictionless candidate profile hydration.
  3. **LangGraph Thread Association**: Deterministic generation of `thread_id = uuid7(user_id + session_id)` ensuring isolation across concurrent recommendations while enabling auditability.

---

## 7. External Opportunity-Source Integrations & Multi-Source Discovery

- **Status**: **Milestone 10 Live Discovery & Honest Connectivity Verified Baseline**
- **Milestone 10 Baseline Implemented & Verified**:
  1. **Verified Live Connectors**:
     - `CompanyCareerPageConnector` (`ATS_DIRECT_API`): Verified live querying of public Greenhouse endpoints (`boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true` across Vercel, Cloudflare, GitLab, Figma) and Ashby (`api.ashbyhq.com/posting-api/job-board/linear`). Normalizes real-world job records, strips HTML tags, extracts skills using canonical taxonomy, parses experience requirements, and retains real application URLs (`absolute_url`, `jobUrl`).
     - `JobSpyMCPConnector` (`MCP_STDIO`): Verified live scraping via `python-jobspy` on Indeed, LinkedIn, and Glassdoor. Normalizes pandas DataFrames into `PolymorphicOpportunity` schemas with direct application URLs and salary intervals.
  2. **Honest Capability & Missing Prerequisite Reporting**:
     - `IndiaJobsMCPConnector`: Verified that `@borgius/india-jobs-mcp` returns 404 on npm registry and no binary is installed on PATH. In live mode, honestly reports `ConnectorStatus.UNAVAILABLE_MISSING_BINARY` without claiming false connectivity.
     - `WebSearchConnector`: Operates in deterministic simulated fallback (`ConnectorStatus.MOCKED_FALLBACK`) because no SearXNG gateway or Google Jobs credentials are configured in local environment.
  3. **End-to-End Career Intelligence Pipeline**:
     - Integrates Candidate Evidence Profile $\to$ O*NET Role Mapping $\to$ Multi-Source Discovery $\to$ MinHash LSH Deduplication $\to$ Deterministic Eligibility $\to$ 6-Dimensional Fit Ranking $\to$ Idempotent Persistence.
     - Real listings with unstated deadlines evaluate safely as `ELIGIBLE_WITH_UNCERTAINTY` with `UNCERT_NO_DEADLINE_SPECIFIED` caveat, preventing false rejection of real opportunities.
     - Differentiated fit scores on real listings (e.g., 0.579 to 0.722) with verified skill matches and growth explanations.
  4. **Discovery Coordinator with Partial Failure Resilience (`coordinator.py`)**:
     - Bounded concurrent retrieval via `asyncio.gather` with error shielding and timeouts (5.0s per connector).
     - Fault Isolation: Exceptions, rate limits, or crashes in any individual connector are recorded as `ConnectorStatus.ERROR` while all listings from healthy connectors are preserved.
     - Early cross-source MinHash LSH deduplication (Jaccard $\ge 0.85$) clusters multi-board syndicated postings into `OpportunityCluster` without losing source provenance.
     - Feeds canonical opportunities into the deterministic eligibility engine with full audit breakdown.
- **Open Decisions & Calibration Tasks**:
  1. **Permitted Live Feeds & Rate Limits**: Validate production integration boundaries and rate-limit backoff profiles for direct employer ATS feeds versus syndicated job board MCP tools.
  2. **Terms of Service Compliance**: Ensure compliance with platform rate limits, robots.txt, and terms of service; implement cached ingestion via background workers (`arq` + Redis) rather than on-demand unauthenticated scraping during user requests.
  3. **Ad-Hoc Candidate Ingestion**: Support candidate-provided job posting URLs with automated adversarial sanitization and MinHash deduplication.

---

## 8. Performance Targets & Benchmark Methodology

- **Baseline Targets**:
  - Synchronous warm cache SLA: $\le 8,000\text{ ms}$
  - Asynchronous cold start SLA: $\le 30,000\text{ ms}$
  - Checkpointer throughput: $> 1,000\text{ req/s}$ under 500 concurrent users
  - Deterministic eligibility accuracy: $100\%$ precision and recall on 500-case golden benchmark
- **Status**: **Provisional Targets — Requires Benchmark Testbed**
- **Open Decisions & Calibration Tasks**:
  1. Construct a standardized golden evaluation dataset (500 synthetic candidate-opportunity pairs).
  2. Establish a load testing suite (`k6` or `Locust`) to benchmark `AsyncPostgresSaver` connection pool under realistic concurrent supersteps.
  3. Measure latency across local Ollama quantized models vs cloud API endpoints.

---

## 9. Opportunity Deduplication & MinHash LSH Calibration

- **Baseline Parameters**:
  - Shingle length: $k = 3$ words (trigram word n-grams).
  - MinHash permutations: $K = 128$ linear congruential hash functions with Mersenne prime $p = 2^{61} - 1$.
  - LSH partitioning: $b = 16$ bands, $r = 8$ rows per band ($b \times r = 128$).
  - Provisional Jaccard similarity threshold: $\ge 0.85$.
- **Status**: **Provisional Implementation (Milestone 3 Verified) — Requires Real-World Calibration**
- **Algorithm Limitations & Known Trade-offs**:
  1. **Short-Text Sensitivity**: Trigram shingles on short blurbs ($< 60$ words) exhibit elevated sensitivity to small footer modifications (e.g., adding an EEO disclaimer drops Jaccard below 0.80 on 30-word snippets, whereas the identical addition maintains $> 0.94$ similarity on realistic 150-word postings).
  2. **Non-Destructive Provenance Invariant**: Duplicate detection must never silently drop or irreversibly merge records. All duplicate postings are preserved with `is_duplicate = True` and clustered via `DuplicateRecord` keeping original source URLs and identifiers intact.
  3. **Title Independence**: Matching job titles alone must never trigger deduplication. The algorithm evaluates composite normalized text (title + company + description) to prevent collapsing distinct roles at the same or different companies.
- **Evaluation Plan for False Positives and False Negatives**:
  1. **False Positive Benchmark**: Curate 200 distinct job pairs sharing identical titles (e.g., "Software Engineer" across 50 companies) to ensure 0% false duplicate linkages.
  2. **False Negative Benchmark**: Ingest 300 verified multi-board syndicated listings (Greenhouse, Lever, Ashby, Workday) and evaluate cluster recall across candidate thresholds $[0.75, 0.80, 0.85, 0.90]$.

---

## 10. Persistence, Ingestion Boundary & Audit Log Retention

- **Status**: **Provisional Implementation (Milestone 5 Verified)**
- **Baseline Implementations Established**:
  1. **Decoupled Ports**: `CandidateProfileRepository`, `OpportunityRepository`, `DuplicateClusterRepository`, and `EligibilityAuditRepository` decouple business and domain logic from the relational database layer.
  2. **Dual Relational Support**:
     - Local development & testing: SQLite with WAL mode (`PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL;`), `PRAGMA foreign_keys = ON;`, and explicit segregated `read_connection()` and `transaction()` boundaries.
     - Production: Complete PostgreSQL 16 relational DDL migration (`001_initial_schema_postgres.sql`) with JSONB, UUIDs, and foreign key cascades.
  3. **Ingestion Abstraction**: `BaseOpportunityAdapter` and `JSONFixtureOpportunityAdapter` allow air-gapped, reproducible ingestion of multi-source opportunities with early deterministic MinHash deduplication, change tracking, and expiration handling.
- **Open Decisions & Calibration Tasks**:
  1. **Audit Retention Window**: Currently defaulted to 30 days via `EligibilityAuditRepository.prune_older_than(days=30)`. The exact production retention window (30 vs 60 vs 90 days) will be tuned based on user feedback and GDPR/CCPA compliance obligations.
  2. **Real ATS Ingestion Scheduling**: External scrapers/APIs (Greenhouse, Lever, Ashby) must be run via scheduled asynchronous background jobs (`arq` + Redis) rather than synchronous request-time fetching. Rate-limiting strategies, backoff profiles, and circuit breakers need specification during infrastructure provisioning.

---

## 11. Model Gateway, Provider Selection & Extraction Fallbacks

- **Status**: **Provisional Implementation (Milestone 6 Verified)**
- **Baseline Implementations Established**:
  1. **Provider Port Abstraction**: `BaseLLMClient` defines `generate_structured(system_prompt, user_prompt, schema)`.
  2. **Pluggable Implementations**:
     - `MockLLMClient`: Offline deterministic extraction engine with configurable error simulation (timeouts, rate limits, schema errors) enabling 100% test coverage with zero external network access.
     - `HTTPXOpenAICompatibleClient`: Async/sync HTTP client using existing `httpx` to connect to OpenAI-compatible endpoints (LiteLLM proxy, Ollama, OpenAI).
  3. **Credential & Prompt Isolation**: Credentials configured exclusively via backend `.env` (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`). Candidate text is sanitized via `sanitize_untrusted_text` and wrapped in structured `{"trust_level": "untrusted_data"}` envelopes.
- **Open Decisions & Calibration Tasks**:
  1. **Model Architecture Selection**: Compare accuracy, latency, and resource footprint across local quantized models (`qwen2.5:14b-instruct`, `llama3.1:8b-instruct` via Ollama) versus hosted cloud endpoints (`gpt-4o-mini`, `claude-3-5-haiku`).
  2. **LiteLLM Gateway Deployment Topology**: Evaluate containerized LiteLLM proxy with Redis circuit breakers versus in-process direct model adapters based on production deployment target.

---

## 12. Agent Orchestration, Adaptive Discovery & Loop Bounds

- **Status**: **Provisional Implementation (Milestone 8 Verified Baseline)**
- **Milestone 8 Baseline Implemented**:
  1. **Typed Orchestration State Machine (`AdaptiveDiscoveryWorkflow`)**:
     - Coordinates candidate profile retrieval, role mapping, multi-source discovery, MinHash LSH deduplication, deterministic eligibility evaluation, coverage gap analysis, adaptive search decisions, and persistence.
     - Discrete lifecycle stages: `INITIALIZING` $\to$ `STRATEGY_FORMULATION` $\to$ `SEARCHING` $\to$ `EVALUATING` $\to$ `GAP_ANALYSIS` $\to$ `ADAPTING` $\to$ `FINALIZING` $\to$ `COMPLETED` (or `FAILED`).
     - Observable timeline emission: Every stage transition, tool call, error, and adaptive shift emits typed `WorkflowTimelineEvent` telemetry with precise UTC timestamps and structured payloads.
  2. **Controlled Agent Tools (`tools.py`)**:
     - Six modular, typed tools (`ProfileRetrievalTool`, `RoleMappingTool`, `OpportunitySearchTool`, `DeduplicationTool`, `DeterministicEligibilityTool`, `PersistenceTool`).
     - Strict Pydantic v2 input schemas, timeout shielding, and sanitized untrusted text.
     - Standardized `ToolResult[T]` envelopes returning execution latency, status (`SUCCESS`, `ERROR`, `EMPTY`), and shielded exception diagnostics.
  3. **Adaptive Decision Making & Coverage Gap Analysis (`agent.py`)**:
     - `DiscoveryAgentDecisionMaker` supports LLM structured extraction with automatic, deterministic heuristic fallback on model timeout, rate limiting, or malformed responses.
     - Epistemic gap detection: Distinguishes zero-result queries, under-covered target roles, and insufficient overall canonical count against the user's coverage goal.
     - Three-tier adaptation hierarchy:
       - Level 1 (Query Relaxation): Drops narrow modifiers, broadens keywords.
       - Level 2 (Adjacent Role Expansion): Queries taxonomy-adjacent occupations identified during O*NET skill mapping.
       - Level 3 (Connector Replacement): Shifts queries to alternate healthy discovery adapters.
  4. **Strict Loop Guards & Termination Guarantees**:
     - Query deduplication via `compute_query_hash`: Guarantees identical query strings are never re-issued to the same connector across iterations.
     - Hard iteration budget (`max_iterations`, default 3, max 5).
     - Tool invocation budget (`max_tool_calls`, default 10, max 20).
     - Standardized termination reasons: `COVERAGE_SATISFIED`, `MAX_ITERATIONS_REACHED`, `BUDGET_EXHAUSTED`, `ALL_SOURCES_EXHAUSTED`, `ABORTED_ERROR`.
  5. **Deterministic Primacy & Truthfulness**:
     - Hard eligibility, MinHash LSH deduplication, and database writes execute exclusively in pure Python deterministic code; models cannot evaluate or override candidate eligibility.
     - Honest connector reporting: Zero fabricated live claims; missing binaries (`india_jobs_mcp`, `jobspy_mcp`) are reported honestly as `UNAVAILABLE_MISSING_BINARY` or `MOCKED_FALLBACK`.
- **Open Decisions & Calibration Tasks**:
  1. **Full LangGraph Cyclic Integration**: When Python 3.14 LangGraph wheel binaries stabilize, wrap the state machine in a cyclic `StateGraph` with `AsyncPostgresSaver` checkpointing and `checkpoint_ns` isolation.
  2. **Dynamic Coverage Goal Tuning**: Calibrate whether $K_{\text{target}}$ should be dynamically suggested based on candidate seniority (e.g., higher for entry-level, lower for niche specialist roles).
  3. **Multi-Turn User Steering**: Permit human-in-the-loop candidate intervention (e.g., approving adjacent role suggestions before adaptive searching resumes).




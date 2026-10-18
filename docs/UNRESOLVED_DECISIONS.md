# JobFalcon — Architectural Decisions & Provisional Parameters

This document records the provisional parameters, empirical calibration requirements, and open architectural design decisions that must be explicitly validated during implementation rather than silently assumed.

---

## 1. Growth-Potential Equation & Parameter Calibration

- **Baseline Formula**:
  $$S_{\text{growth}}(u, o) = \frac{\sum_{s \in G(u, o)} M_{\text{demand}}(s, c_{\text{target}}) \cdot \left(1 - \frac{P_u(s)}{10}\right) \cdot \mathcal{B}\left(\Delta_{\text{gap}}(u, o, s)\right)}{\sum_{s \in \text{TargetSkills}(c_{\text{target}})} M_{\text{demand}}(s, c_{\text{target}})}$$
- **Status**: **Provisional — Needs Validation**
- **Open Decisions & Calibration Tasks**:
  1. **Bell-Curve Factor $\mathcal{B}(\Delta_{\text{gap}})$**: The exact mathematical function and variance for the zone of proximal development must be parameterized. If a gap is too wide, $\mathcal{B}$ must strongly penalize over-stretching; if too narrow, growth value is negligible.
  2. **Skill-Gap Boundary**: The current cutoff $P_u(s) < 6.0$ for defining a gap $G(u, o)$ is provisional and requires tuning against entry-level vs experienced roles.
  3. **Prerequisite Gating**: A mechanism must be established to ensure candidates possess necessary foundational skills before growth points are credited on dependent competencies (e.g., Python proficiency before advanced distributed computing).

---

## 2. Skill-Proficiency & Evidence-Confidence Scoring

- **Baseline Formulas**:
  $$P(s) = \text{clip}\left(\sum_{e \in E_s} w_{\text{source}}(e) \cdot d_{\text{depth}}(e) \cdot e^{-\lambda_{\text{decay}} \cdot \Delta t(e)}, \, 1.0, \, 10.0\right)$$
  $$C(s) = 1 - \prod_{e \in E_s} \left(1 - r_{\text{verifiability}}(e)\right)$$
- **Status**: **Provisional — Needs Validation**
- **Open Decisions & Calibration Tasks**:
  1. **Temporal Decay Constant $\lambda_{\text{decay}}$**: Needs calibration by domain (e.g., web frameworks evolve faster than fundamental algorithms).
  2. **Source Weight Calibration $w_{\text{source}}(e)$**: Proposed weights (1.0 for production experience / verified repos, 0.6 for academic coursework, 0.25 for uncorroborated keywords) must be benchmarked against human technical recruiter baselines.
  3. **Complexity Depth Function $d_{\text{depth}}(e)$**: Concrete heuristic or model-based extraction for measuring repository or project complexity must be defined and tested against adversarial fluff.

---

## 3. Handling of Unknown / Missing Eligibility Information

- **Context**: Real-world job listings and candidate profiles frequently omit explicit fields (e.g., visa sponsorship unspecified, graduation date range not mentioned, GPA requirements absent).
- **Status**: **Unresolved Design Decision**
- **Options to Validate**:
  1. **Strict Exclusion (Fail-Closed)**: Disqualify opportunities or candidates whenever mandatory fields are missing. Guarantees 0% false positives for eligibility but may drastically lower opportunity recall.
  2. **Optimistic Inclusion with Soft Warning (Fail-Open)**: Mark unstated eligibility criteria as `ELIGIBILITY_UNCERTAIN`, permit ranking, but flag clearly in the UI that the user must verify specific terms.
  3. **Interactive Candidate Clarification**: For ambiguous candidate profile attributes, trigger a quick interactive prompt prior to running full ranking.
- **Recommended Default**: Strict exclusion for clear negative constraints (e.g., explicit "Must be authorized without sponsorship"); Optimistic with user-facing caveat for completely unstated criteria, paired with confidence discount in $S_{\text{qual}}$.

---

## 4. Ranking Weights & Minimum-Score Thresholds

- **Baseline Formula**:
  $$\text{Score}_{\text{total}} = 0.30 S_{\text{skill}} + 0.20 S_{\text{career}} + 0.20 S_{\text{growth}} + 0.12 S_{\text{market}} + 0.10 S_{\text{pref}} + 0.08 S_{\text{qual}}$$
- **Status**: **Provisional — Needs Validation**
- **Open Decisions & Calibration Tasks**:
  1. **Weights Balance**: The linear weights (0.30, 0.20, 0.20, 0.12, 0.10, 0.08) represent a proposed baseline. For specific categories (e.g., internships vs senior staff roles), the balance between $S_{\text{skill}}$ and $S_{\text{growth}}$ should be configurable or calibrated.
  2. **Eligible Pool Minimum Cardinality ($K_{\text{min}} = 5$)**: If fewer than 5 opportunities pass deterministic eligibility, the supervisor expands discovery (Level 1 soft preference relaxation, Level 2 adjacent career fan-out). The threshold of 5 and pass score cutoff (0.55) must be validated against real search volumes.
  3. **Candidate Pool Sizing ($M = 20$ for deep scoring, $K = 10$ for explanations)**: Sizing must balance latency and computational cost against recommendation diversity.

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

## 7. External Opportunity-Source Integrations & Permitted Usage

- **Status**: **Unresolved Design Decision**
- **Open Decisions & Calibration Tasks**:
  1. **Permitted Feeds**: Validate integration boundaries for direct employer ATS feeds (Greenhouse, Lever, Ashby public job boards) versus syndicated aggregators.
  2. **Terms of Service & Rate Limits**: Ensure compliance with platform rate limits, robots.txt, and terms of service; implement cached ingestion via background workers (`arq`) rather than on-demand unauthenticated scraping during user requests.
  3. **Candidate-Submitted Listings**: Support ad-hoc opportunity URL ingestion with automated adversarial sanitization and MinHash deduplication.

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

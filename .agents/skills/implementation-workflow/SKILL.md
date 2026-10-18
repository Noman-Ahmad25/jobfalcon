---
name: implementation-workflow
description: General code-writing and implementation discipline for JobFalcon. Use when scoping changes, inspecting surrounding context, writing surgical diffs, avoiding placeholder stubs, or verifying changes through linters and tests.
---

# Implementation & Code-Writing Discipline

This skill governs general implementation discipline, code quality standards, and verification procedures across all JobFalcon languages and frameworks.

---

## 1. When to Use This Skill

- At the start of any feature implementation, bug fix, or refactor.
- When planning the sequence of edits across backend, frontend, and database layers.
- When inspecting existing conventions before modifying unfamiliar files.
- When conducting pre-completion verification (linting, type checking, testing, diff review).

---

## 2. Workflow: The Five-Phase Implementation Cycle

Every implementation task must execute through these disciplined phases:

```
[Phase 1: Inspect] → Read related files, imports, schemas, and tests first
        ↓
[Phase 2: Plan]    → Draft minimal coherent changes satisfying the requirement
        ↓
[Phase 3: Execute] → Make surgical, localized edits; preserve existing comments/conventions
        ↓
[Phase 4: Verify]  → Run linters, type checks, and tests; examine real command output
        ↓
[Phase 5: Review]  → Inspect git diff; report verified outcomes with total truthfulness
```

### Phase 1: Inspect Before Modifying
- Never edit a file without first viewing its surrounding context using `view_file`.
- Inspect existing tests, schemas, and data models to understand assumptions and constraints.
- Verify whether the task touches deterministic business rules or probabilistic agent logic.

### Phase 2: Scoped Implementation Plan
- Define the smallest coherent change set that solves the problem.
- Identify edge cases, error conditions, and failure modes up front.
- Ensure the planned change does not introduce unnecessary dependencies or speculative design patterns.

### Phase 3: Surgical Execution
- Write clean, direct, and readable code following existing naming and typing conventions.
- **Zero Placeholders**: Never leave `pass`, `TODO: implement later`, or mock data in production code paths.
- Handle error states explicitly (network timeouts, null values, malformed inputs).
- Preserve existing comments, docstrings, and formatting.

### Phase 4: Rigorous Verification
- Execute actual terminal commands to verify code changes:
  - Python: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`
  - Frontend: `npm run lint`, `tsc --noEmit`, test runners
- **Never claim a command or test succeeded without actually executing it and inspecting the return code and stdout.**

### Phase 5: Diff Review & Truthful Reporting
- Review the final `git status` and `git diff` before concluding.
- Confirm that no unintended files (such as `.DS_Store`, `.env`, temporary logs) are staged or modified.
- Report precisely what was changed, what was verified, and what could not be tested.

---

## 3. Anti-Patterns & Constraints

- ❌ **DO NOT** make speculative refactors to unrelated code while working on a targeted task.
- ❌ **DO NOT** commit secrets, passwords, or `.env` files to git.
- ❌ **DO NOT** claim tests passed based on assumptions. Execute the test runner.
- ❌ **DO NOT** introduce framework wrappers or abstract base classes when simple functions suffice.
- ❌ **DO NOT** suppress linter or type-checker errors with blanket `# type: ignore` or `eslint-disable` without an explicit, documented reason.

---

## 4. Verification Checklist

Before completing an implementation task:
- [ ] Surrounding code and existing tests were inspected prior to editing.
- [ ] Edits are surgical, minimal, and fully implemented (no placeholder stubs).
- [ ] Linters and formatters pass cleanly.
- [ ] Type checkers (`mypy` / `tsc`) report zero errors.
- [ ] Test suites execute and pass.
- [ ] Final `git diff` is reviewed and confirmed free of stray files or secrets.

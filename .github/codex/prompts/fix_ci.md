# Codex CI Autofix Prompt

A CI run has failed for this branch. Apply the smallest safe code change to make CI pass.

Rules:
- Read `AGENTS.md`, `PROJECT_STATE.md`, and touched ADRs before changing code.
- Focus only on failures surfaced by lint/test workflow.
- Preserve determinism and evidence-gating invariants.
- Do not introduce scope creep or unrelated refactors.
- Add or update tests only when required by the fix.

Execution checklist:
1. Reproduce failure locally via `make lint` and `make test`.
2. Implement minimal fix.
3. Re-run `make lint` and `make test`.
4. Summarize root cause and changed files.

Output:
- Keep commit-ready changes only.
- If no safe fix is possible, explain why and make no code changes.

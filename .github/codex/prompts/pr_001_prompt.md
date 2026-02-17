# PR-001 Implementation Prompt

Implement PR-001 only.

Scope:
- Add baseline developer tooling and CI for lint/test.
- Ensure these commands exist and run:
  - `make lint`
  - `make test`
- Add minimal, deterministic unit tests for new logic.

Constraints:
- Keep architecture unchanged except tooling and CI wiring.
- Avoid adding Codex GitHub Action automation (reserved for PR-002).

Before finishing:
1. Run `make lint` and `make test`.
2. Update `PROJECT_STATE.md` to record PR-001 completion and next PR ID.
3. Provide concise summary and residual risks.

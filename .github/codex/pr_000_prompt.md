# PR-000 Implementation Prompt

Implement PR-000 only.

Scope:
- Scaffold baseline repository structure for the Compliance App.
- Ensure governance/context files are present and current:
  - `AGENTS.md`
  - `PROJECT_STATE.md`
  - ADR starter docs in `docs/adr/`
- Ensure PR template/checklist files are present.

Constraints:
- Keep changes minimal and deterministic.
- Do not implement PR-001 or PR-002 scope in this run.
- Add/update tests only if code behavior changes.

Before finishing:
1. Run `make lint` and `make test` if targets exist.
2. Update `PROJECT_STATE.md` with PR completion details.
3. Summarize changed files and any follow-up work.

# PR-002 Implementation Prompt

Implement PR-002 only.

Scope:
- Add GitHub Actions workflows that invoke `openai/codex-action@v1`.
- Wire prompt files under `.github/codex/prompts/` to PR review automation.
- Keep security posture conservative (least-privilege permissions, explicit secret usage).

Constraints:
- Do not modify core compliance logic in this PR.
- Keep workflow behavior deterministic and auditable.
- Use repository-owned prompt files, not inline mega-prompts.

Before finishing:
1. Validate workflow YAML syntax and references.
2. Run `make lint` and `make test` if available.
3. Update `PROJECT_STATE.md` for PR-002 completion and next PR ID.
4. Summarize required repository secrets/permissions.

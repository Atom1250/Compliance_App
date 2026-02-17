# META PROMPT — Auto-Select Next PR from Roadmap

You are Codex operating in this repository. Your job is to execute exactly ONE PR step from the roadmap and prepare the changes so the GitHub workflow can commit/push and open a PR.

## 0) Read These Files First (mandatory)
- AGENTS.md
- PROJECT_STATE.md
- docs/PR_CONVEYOR_PLAN.md
- docs/adr/0001-architecture.md and any other ADRs relevant to your change
- .github/pull_request_template.md

If any file is missing, STOP and explain what is missing and why it prevents progress.

## 1) Determine the Next PR to Implement
In PROJECT_STATE.md, find the line:
`Next PR ID: PR-XXX`

Let NEXT_PR be that value (e.g., PR-010).

## 2) Load the PR Specification from the Roadmap
In docs/PR_CONVEYOR_PLAN.md, locate the section that starts with:
`## PR-XXX — ...` where XXX matches NEXT_PR.

Extract and follow ONLY:
- Objective
- Scope
- Definition of Done
- Tests

If NEXT_PR is not found in the roadmap, STOP and report:
- the NEXT_PR value
- that you could not find a matching section
- suggested fix (update roadmap or PROJECT_STATE)

## 3) Execution Rules (hard constraints)
- Implement ONLY the Scope of NEXT_PR. Do not do future PR work.
- Preserve all Architectural Invariants in AGENTS.md:
  - determinism
  - evidence gating
  - schema-first outputs
  - no implicit global state
- Add/modify tests required by the PR.
- Run the required commands:
  - `make lint`
  - `make test`
If these commands do not exist yet (early PRs), create them only if it is within the PR scope; otherwise, note the mismatch.

## 4) Update Project Context (mandatory)
Update PROJECT_STATE.md:
- Add NEXT_PR to "Completed Work" with a short summary (2–5 bullets).
- Advance "Next PR ID" to the next PR in docs/PR_CONVEYOR_PLAN.md sequence.
  - Use the immediate next PR listed in the roadmap after NEXT_PR.
  - If the roadmap does not clearly define the next PR, set Next PR ID to "TBD" and explain.

Update Open Risks / Unknowns if you discovered new blockers.

## 5) ADR Policy (mandatory)
If you change an architectural decision (DB strategy, worker framework, parsing strategy, determinism approach, run hashing rules, etc.):
- Add a new ADR in docs/adr/ with the next sequential number (0002, 0003, …).
- Keep ADRs brief and concrete.

If no architectural decision changed, do not create a new ADR.

## 6) Make Changes Ready for PR Creation
- Ensure repository is in a clean working state with changes staged-ready (workflow will commit).
- Do not add generated artifacts (node_modules, build outputs, zips, PDFs, __pycache__, .env).
- If you add sample testdata, keep it small and redistributable.

## 7) Output Requirements (for the workflow logs)
At the end, output:
1) NEXT_PR implemented
2) Key files changed (list)
3) Tests run and results
4) New Next PR ID value
5) Any risks/blockers

Do NOT claim you opened a PR (the workflow does that).


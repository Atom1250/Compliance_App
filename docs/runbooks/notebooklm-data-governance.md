# NotebookLM Data Governance

## Boundary
- NotebookLM workflow inputs are restricted to public regulatory materials in this phase.
- No tenant-private disclosures, customer documents, or sensitive uploads are allowed.

## Allowed data classes
- Public EU directives, delegated acts, guidance, and official standards.
- Public regulator FAQs and consultation papers.

## Prohibited data classes
- Client-provided unpublished reports.
- Proprietary evidence packs.
- Personally identifiable or confidential information.

## Enforcement
- Keep feature flags off by default.
- Review prompts and corpus mapping before enabling in non-dev environments.
- Use additive notes tables only; do not mutate canonical requirement rows directly.

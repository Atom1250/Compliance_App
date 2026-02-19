# ADR-0002: Persistence Cutover to Postgres + pgvector

Date: 2026-02-19
Status: Accepted

## Context
ADR-0001 establishes Postgres as system-of-record, pgvector for embeddings, and S3-compatible
storage for source documents and evidence packs. The implementation has included SQLite-based
local/test workflows during bootstrapping, which is acceptable only as a temporary transition.

To preserve deterministic and audit-grade operation semantics at scale, persistence behavior must
be explicitly locked to Postgres-compatible operational patterns.

## Decision
We formalize a staged cutover policy:

1. Postgres + pgvector are the authoritative persistence targets for runtime/system-of-record
   workloads.
2. SQLite remains allowed only for test fixtures and transitional local development workflows
   until the cutover sequence is complete.
3. SQL query paths where row ordering materially affects outputs MUST include explicit
   deterministic ordering clauses.
4. Migration and CI gates must prioritize Postgres-path validation as the canonical persistence
   path.

## Consequences
Pros:
- Aligns implementation with ADR-0001 and audit requirements.
- Reduces risk of SQLite/Postgres behavior drift in production-like workflows.
- Improves confidence in deterministic output reproducibility under system-of-record settings.

Cons:
- Requires additional local infrastructure setup for developers.
- Transitional period must maintain dual-path confidence checks.
- CI/runtime configuration becomes more explicit and stricter.

## Transitional Policy
- SQLite is not considered a production system-of-record backend.
- SQLite usage is restricted to test/transitional workflows and may be removed from non-test
  runbooks once cutover stability criteria are met.

## Follow-ups
- PR-042: local Postgres/pgvector + MinIO provisioning baseline.
- Subsequent PRs: migration/cutover enforcement and SQLite deprecation in runtime paths.

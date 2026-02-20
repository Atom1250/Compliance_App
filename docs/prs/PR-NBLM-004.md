# PR-NBLM-004 — DB-Backed Regulatory Research Cache

## Checklist
- Added migration/model for `regulatory_research_cache`.
- Added cache repository with success/failure TTL behavior.
- Added cache read-through in `RegulatoryResearchService`.
- Added tests for hit/miss/failure caching paths.

## Commands
- `make lint` ✅
- `make test` ✅

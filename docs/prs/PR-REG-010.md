# PR-REG-010 — Document Universe and Deterministic Inventory Engine

## Scope implemented
- Added deterministic document classification service (`annual report`, `sustainability`, `transparency act`, `slavery`, `pillar 3`, `factbook`).
- Extended document ingestion to persist inventory metadata (`doc_type`, `reporting_year`, `source_url`, `classification_confidence`).
- Added inventory listing service and API endpoint `GET /documents/inventory/{company_id}`.
- Added integration/API tests for deterministic inventory rendering.

## Commands run
- `make lint` ✅
- `make test` ✅

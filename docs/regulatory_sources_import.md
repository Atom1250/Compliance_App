# Regulatory Source Register Import

This import loads curated legal/source-document metadata into `regulatory_source_document`.
It is separate from requirements/obligation bundles:

- Source register: provenance catalog of laws, standards, guidance, and official links.
- Requirement bundles: compiled datapoint obligations used in run-time compliance evaluation.

Use this importer to seed and maintain the source register with deterministic, idempotent behavior.

## CLI

Run with module CLI:

```bash
python -m apps.api.app.scripts.import_regulatory_sources --file ./path/to/register.xlsx
```

EU-only import:

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file ./path/to/register.xlsx \
  --jurisdiction EU
```

Dry-run validation (no DB writes):

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file ./path/to/register.csv \
  --dry-run \
  --issues-out ./outputs/regulatory_import_issues.csv
```

Explicit sheets (XLSX):

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file ./path/to/register.xlsx \
  --sheets Master_Documents,ESRS_Standards,EU_Taxonomy_Acts
```

## Determinism and Idempotency

- Row checksum: SHA256 of canonical normalized row payload.
- Batch dedup key: `record_id`.
- Upsert key: `record_id` primary key.
- Second import of unchanged content yields only `skipped` rows.

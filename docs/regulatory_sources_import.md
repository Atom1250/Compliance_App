# Regulatory Source Register Import

This import loads curated legal/source-document metadata into `regulatory_source_document`.
It is separate from requirements/obligation bundles:

- Source register: provenance catalog of laws, standards, guidance, and official links.
- Requirement bundles: compiled datapoint obligations used in run-time compliance evaluation.

Use this importer to seed and maintain the source register with deterministic, idempotent behavior.

## Recommended Ingestion (CSV-first)

Use `SOURCE_SHEETS_*` CSVs to avoid non-data tabs
(`Ops_Checklist`, `JSON_Schema`, `Lists`).
Avoid `regulatory_source_document_full.csv` unless you intentionally preprocess
non-data tabs first.

EU-only import:

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file regulatory_source_document_SOURCE_SHEETS_EU_only.csv \
  --jurisdiction EU
```

Full import:

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file regulatory_source_document_SOURCE_SHEETS_full.csv
```

Dry-run + issues report:

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file regulatory_source_document_SOURCE_SHEETS_full.csv \
  --dry-run \
  --issues-out regulatory_import_issues.csv
```

## Optional Convenience (XLSX)

XLSX remains supported, but CSV is preferred for deterministic ingestion:

```bash
python -m apps.api.app.scripts.import_regulatory_sources \
  --file regulatory_source_document_SOURCE_SHEETS.xlsx \
  --sheets Master_Documents,ESRS_Standards,EU_Taxonomy_Acts
```

## Determinism and Idempotency

- Row checksum: SHA256 of canonical normalized row payload.
- Batch dedup key: `record_id`.
- Upsert key: `record_id` primary key.
- Second import of unchanged content yields only `skipped` rows.
- Required fields: `record_id`, `jurisdiction`.
- Recommended fields: `document_name`, `official_source_url`.
- If `document_name` is missing, importer derives a deterministic fallback from `record_id`.

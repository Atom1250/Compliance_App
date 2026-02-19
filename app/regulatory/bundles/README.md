# Regulatory Bundles

Bundles are versioned JSON contracts loaded into `regulatory_bundle`.

Naming:
- `<bundle_id>@<version>.json` (example: `csrd_esrs_core@2026.02.json`)

Versioning:
- Increment version on any structural or logic change.
- Keep prior versions for reproducible historical runs.

Required top-level fields:
- `regime`
- `bundle_id`
- `version`
- `jurisdiction`
- `obligations`

Optional:
- `source_record_ids`
- `applicability_rules`
- `overlays`

Sync:
```bash
python -m apps.api.app.scripts.sync_regulatory_bundles --path app/regulatory/bundles --mode sync
```

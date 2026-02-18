# Datapoint Bundle Schema and Current Mappings

This is a snapshot of the current requirements bundles in the repository and how datapoints map to standards.

## Canonical Bundle Schema

Defined in: `/Users/atom/Projects/Compliance_App/app/requirements/schema.py`

```json
{
  "bundle_id": "string",
  "version": "string",
  "standard": "string",
  "datapoints": [
    {
      "datapoint_key": "string",
      "title": "string",
      "disclosure_reference": "string",
      "materiality_topic": "string"
    }
  ],
  "applicability_rules": [
    {
      "rule_id": "string",
      "datapoint_key": "string",
      "expression": "string"
    }
  ]
}
```

## Bundle Inventory

1. `esrs_mini@2026.01` (`standard=ESRS`)
2. `esrs_mini@2024.01` (`standard=ESRS`, legacy)
3. `green_finance_icma_eugb@2026.01` (`standard=GREEN_FINANCE`)

## Datapoints: Mapping to Standards

### ESRS (Current)
Bundle: `esrs_mini@2026.01`

| datapoint_key | title | disclosure_reference | mapped standard |
|---|---|---|---|
| ESRS-E1-1 | Transition plan disclosure | ESRS E1-1 | ESRS |
| ESRS-E1-6 | Gross GHG emissions | ESRS E1-6 | ESRS |

Applicability rules:
- `rule-esrs-e1-all`: `company.reporting_year >= 2025`
- `rule-esrs-ghg-all`: `company.reporting_year >= 2025`

### ESRS (Legacy / Historical Testing)
Bundle: `esrs_mini@2024.01`

| datapoint_key | title | disclosure_reference | mapped standard |
|---|---|---|---|
| ESRS-E1-1 | Transition plan disclosure | ESRS E1-1 | ESRS |
| ESRS-E1-6 | Gross GHG emissions | ESRS E1-6 | ESRS |

Applicability rules:
- `rule-esrs-e1-legacy`: `company.reporting_year_end >= 2022`
- `rule-esrs-ghg-legacy`: `company.reporting_year_end >= 2022`

### Green Finance (ICMA GBP / EuGB)
Bundle: `green_finance_icma_eugb@2026.01`

| datapoint_key | title | disclosure_reference | mapped standard |
|---|---|---|---|
| GF-OBL-01 | Use of Proceeds Framework | ICMA GBP Use of Proceeds | GREEN_FINANCE (ICMA GBP) |
| GF-OBL-02 | Annual Allocation Reporting | EuGB Allocation Report | GREEN_FINANCE (EuGB) |

Applicability rules:
- `rule-gf-all-1`: `company.reporting_year >= 2025`
- `rule-gf-all-2`: `company.reporting_year >= 2025`

## Note on Green Finance `obligations`

`green_finance_icma_eugb@2026.01` also contains an `obligations` section (obligation IDs, required artifacts, required data elements).  
This section is currently used by the green-finance pipeline domain logic and is not part of the strict `RequirementsBundle` Pydantic schema above.

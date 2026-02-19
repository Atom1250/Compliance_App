# GOLD STANDARD REPORT TEMPLATE (v1)

## CSRD & ESRS Regulatory Compliance Report
`{{Company Name}}`  
Reporting Period: `{{Start Year}}–{{End Year}}`  
Jurisdictions: `{{Jurisdictions}}`  
Regimes Applied: `{{Regimes}}`

## 0. Report Metadata (Deterministic Header)

| Field | Value |
|---|---|
| Run ID | `{{run_id}}` |
| Generated On | `{{timestamp_iso}}` |
| Requirements Bundles | `{{bundle_ids + versions}}` |
| Regulatory Registry Version | `{{registry_version}}` |
| Compiler Version | `{{compiler_version}}` |
| Model Used | `{{model_id}}` |
| Retrieval Parameters | `{{retrieval_config_hash}}` |
| Git SHA | `{{git_sha}}` |

This section must be auto-generated from the run manifest.

## 1. Executive Summary

### Purpose
This report assesses `{{Company}}`'s compliance with `{{Regimes}}` for the reporting period `{{period}}`.

### Regulatory Status Overview
- CSRD Cohort: `{{Phase 1 / 2 / SME / NA}}`
- First CSRD Reporting Year: `{{year or NA}}`
- Assurance Requirement: `{{Limited / Reasonable / NA}}`
- Jurisdictional Overlays Applied: `{{list}}`

### Key Findings (Deterministic Highlights)
- `{{Key compliance strength}}`
- `{{Major material topic}}`
- `{{Significant KPI}}`
- `{{Major gap or phase-in}}`

### Overall Compliance Rating
`{{COMPLIANT / PARTIALLY COMPLIANT / NON-COMPLIANT / INCOMPLETE DATA}}`

This rating must be computed from obligation coverage, not narrative inference.

## 2. Regulatory Framework & Applicability

### 2.1 Applicable Regimes

| Regime | Applicable | Basis | Phase-in Applied |
|---|---|---|---|
| CSRD | Yes | `{{cohort logic}}` | `{{Yes/No}}` |
| ESRS | Yes | `{{legal reference}}` | `{{Yes/No}}` |
| UK Modern Slavery | `{{Yes/No}}` | `{{jurisdiction}}` | N/A |
| Norway Transparency Act | `{{Yes/No}}` | `{{jurisdiction}}` | N/A |
| EuGB | `{{Yes/No}}` | `{{bond issuance}}` | N/A |
| ICMA GBP | `{{Yes/No}}` | `{{framework existence}}` | N/A |

Generated from regulatory compiler output.

### 2.2 Double Materiality & Scope
- Impact Materiality (Inside-Out): `{{summary}}`
- Financial Materiality (Outside-In): `{{summary}}`
- Value Chain Coverage: `{{scope description}}`
- Reporting Boundary: `{{group/subsidiary/ops}}`

If unavailable, explicitly state: `"No evidence found for documented DMA in reviewed materials."`

## 3. Public Filing & Disclosure Inventory

### 3.1 Filing Inventory Table

| Document Title | Publication Date | Document Type | Regime Linkage | Evidence Source ID |
|---|---|---|---|---|

Types should be controlled taxonomy:
- Annual Report
- Sustainability Statement
- Risk & Capital Report
- Transparency Act Statement
- Modern Slavery Statement
- PRB Report
- SASB Index
- EuGB Allocation Report
- Impact Report
- Technical Methodology Report

This must be generated deterministically from ingested document metadata.

## 4. Material Topics & ESRS Mapping

### 4.1 Environmental (ESRS E)
#### ESRS E1 – Climate Change
- Obligation Coverage Status: `{{Full / Partial / Absent}}`
- Disclosures Identified:
  - Transition Plan: `{{Present/Absent}}`
  - GHG Emissions (Scope 1/2/3): `{{Present/Partial/Absent}}`
  - Financed Emissions (if FI): `{{Present/NA}}`
  - Targets & Progress: `{{summary}}`
  - Climate Scenario Analysis: `{{Present/Absent}}`

Key Metrics:

| Metric | Baseline | Latest Year | Target | Status |
|---|---|---|---|---|

#### ESRS E2 – Pollution
Only render if applicable or material.

#### ESRS E3 – Water
Only render if applicable or material.

#### ESRS E4 – Biodiversity
Only render if applicable or material.

#### ESRS E5 – Circular Economy
Only render if applicable or material.

### 4.2 Social (ESRS S)
#### ESRS S1 – Own Workforce
- Diversity Metrics: `{{summary}}`
- Employee Engagement: `{{summary}}`
- Remuneration Linkage: `{{Present/Absent}}`

#### ESRS S2 – Workers in Value Chain
- Due Diligence Statement: `{{Present/Absent}}`
- Supply Chain Policy: `{{summary}}`

#### ESRS S3 – Affected Communities
Only render if applicable or material.

#### ESRS S4 – Consumers & End Users
Only render if applicable or material.

### 4.3 Governance (ESRS G1 – Business Conduct)
- Board Oversight: `{{Present/Absent}}`
- ESG Committee Structure: `{{summary}}`
- Anti-Corruption Framework: `{{Present/Absent}}`
- Risk Integration: `{{summary}}`

## 5. Quantitative Performance & Targets

### 5.1 Strategic Targets Table

| Target Area | Baseline Year | Baseline Value | Latest Value | Target | Progress % | Status |
|---|---|---|---|---|---|---|

Rules:
- Percentages must be computed deterministically.
- Baseline year must be present if % reduction is stated.
- If baseline missing, mark `Insufficient Evidence`.

## 6. ESRS Disclosure Compliance Matrix

### 6.1 Cross-Cutting Standards

| Standard | Obligation Count | Full | Partial | Absent | Phase-in |
|---|---|---|---|---|---|

### 6.2 Topical Standards

| ESRS Standard | Material | Compliance Level | Notes |
|---|---|---|---|

Compliance level logic:
- Full = All mandatory datapoints Present
- Partial = At least one Present but not all
- Absent = None Present
- NA = Not applicable

## 7. Jurisdiction-Specific Compliance

### Norway (if applicable)
- Transparency Act Statement: `{{Present/Absent}}`
- Due Diligence Description: `{{Present/Absent}}`

### UK (if applicable)
- Modern Slavery Statement: `{{Present/Absent}}`
- Required Content Sections: `{{coverage summary}}`

## 8. Assurance & External Framework Alignment

### 8.1 External Assurance
- Assurance Provider: `{{name}}`
- Assurance Level: `{{Limited/Reasonable}}`
- Scope of Assurance: `{{summary}}`

### 8.2 Other Frameworks
- TCFD Alignment: `{{Yes/No}}`
- SASB Index: `{{Yes/No}}`
- PRB Reporting: `{{Yes/No}}`

## 9. Gap Analysis & Risk Commentary

### Strengths
- `{{bullet list from high coverage areas}}`

### Gaps
- `{{obligations with Absent status}}`
- `{{phase-in pending obligations}}`

### Recommended Actions
- `{{action}}`
- `{{action}}`

## 10. Conclusion

Summary paragraph should include:
- Overall compliance state
- Readiness for next reporting cycle
- Priority remediation areas

Final Determination:  
`{{COMPLIANT / PARTIAL / HIGH RISK / INCOMPLETE}}`

## Appendix A — Evidence Traceability
Each datapoint must list:

| Datapoint Key | Status | Evidence Chunk IDs | Document | Page |
|---|---|---|---|---|

## Appendix B — Run Manifest Snapshot
- Document Hashes
- Bundle Versions
- Retrieval Params
- Model + Prompt Hash
- Git SHA

## Narrative Style Specification (For LLM Composer Layer)
When generating narrative sections:
- Use formal regulatory tone.
- Avoid speculative language.
- Do not introduce facts not present in validated datapoints.
- If evidence is missing, explicitly state: `"No evidence was identified in reviewed materials."`
- Quantitative claims must:
  - include baseline
  - include reporting year
  - match extracted values exactly
- Use headings consistent with ESRS taxonomy.
- Avoid adjectives like `excellent` or `strong` unless tied to measurable coverage.
- Always separate:
  - Compliance determination
  - Strategic commentary

## Rendering Rules for the App
This template should be implemented as:
- Deterministic section assembly
- Structured tables from DB queries
- LLM only for:
  - Executive summary synthesis
  - Gap analysis explanation
  - Conclusion narrative

LLM must consume:
- Fact registry (validated datapoints only)
- Coverage matrix output
- No raw document text

## Versioning Strategy
- Embed in code as: `REPORT_TEMPLATE_VERSION = "gold_standard_v1"`
- When structure changes:
  - Increment version
  - Store version in `run_manifest`
  - Keep backward compatibility for archived runs

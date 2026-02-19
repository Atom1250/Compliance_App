"""Deterministic HTML report generation for compliance assessments."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from apps.api.app.db.models import DatapointAssessment

_TIMESTAMP_PATTERN = re.compile(
    r"<span id=\"generated-at\">[^<]+</span>",
)

REPORT_TEMPLATE_VERSION = "gold_standard_v1"


@dataclass(frozen=True)
class RegistryCoverageRow:
    obligation_id: str
    total_elements: int
    present: int
    partial: int
    absent: int
    na: int
    coverage_pct: float
    status: str


@dataclass(frozen=True)
class ReportRow:
    datapoint_key: str
    status: str
    value: str | None
    evidence_chunk_ids: str
    rationale: str


@dataclass(frozen=True)
class ReportData:
    run_id: int
    rows: list[ReportRow]
    total_datapoints: int
    denominator_datapoints: int
    excluded_na_count: int
    present: int
    partial: int
    absent: int
    na: int
    covered: int
    coverage_pct: float
    overall_rating: str
    final_determination: str


@dataclass(frozen=True)
class ReportManifestMetadata:
    requirements_bundles: str = "n/a"
    regulatory_registry_version: str = "n/a"
    compiler_version: str = "n/a"
    model_used: str = "n/a"
    retrieval_parameters: str = "n/a"
    git_sha: str = "n/a"
    applied_regimes: str = "n/a"
    applied_overlays: str = "n/a"
    obligations_applied_count: int = 0


def _to_generated_at(timestamp: datetime | None) -> str:
    value = timestamp or datetime.now(UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _citations(evidence_chunk_ids_json: str) -> str:
    chunk_ids = sorted(json.loads(evidence_chunk_ids_json))
    if not chunk_ids:
        return "-"
    return " ".join(f"<code>[{html.escape(chunk_id)}]</code>" for chunk_id in chunk_ids)


def _obligation_status(*, present: int, partial: int, absent: int, na: int, total: int) -> str:
    covered = present + partial
    if present == total:
        return "Present"
    if na == total:
        return "NA"
    if absent == total or (covered == 0 and absent > 0):
        return "Absent"
    return "Partial"


def compute_registry_coverage_matrix(
    assessments: Sequence[DatapointAssessment],
    *,
    obligation_ids: Sequence[str] | None = None,
) -> list[RegistryCoverageRow]:
    grouped: dict[str, list[DatapointAssessment]] = {}
    for assessment in assessments:
        if "::" not in assessment.datapoint_key:
            continue
        obligation_id = assessment.datapoint_key.split("::", 1)[0]
        grouped.setdefault(obligation_id, []).append(assessment)

    rows: list[RegistryCoverageRow] = []
    for obligation_id in sorted(grouped):
        items = sorted(grouped[obligation_id], key=lambda item: item.datapoint_key)
        present = sum(1 for item in items if item.status == "Present")
        partial = sum(1 for item in items if item.status == "Partial")
        absent = sum(1 for item in items if item.status == "Absent")
        na = sum(1 for item in items if item.status == "NA")
        total = len(items)
        coverage_pct = ((present + partial) / total * 100.0) if total else 0.0
        rows.append(
            RegistryCoverageRow(
                obligation_id=obligation_id,
                total_elements=total,
                present=present,
                partial=partial,
                absent=absent,
                na=na,
                coverage_pct=coverage_pct,
                status=_obligation_status(
                    present=present, partial=partial, absent=absent, na=na, total=total
                ),
            )
        )
    if obligation_ids:
        existing = {row.obligation_id for row in rows}
        for obligation_id in sorted(set(obligation_ids)):
            if obligation_id in existing:
                continue
            rows.append(
                RegistryCoverageRow(
                    obligation_id=obligation_id,
                    total_elements=0,
                    present=0,
                    partial=0,
                    absent=0,
                    na=0,
                    coverage_pct=0.0,
                    status="Absent",
                )
            )
    rows.sort(key=lambda item: item.obligation_id)
    return rows


def build_report_data(*, run_id: int, assessments: Sequence[DatapointAssessment]) -> ReportData:
    rows = [
        ReportRow(
            datapoint_key=item.datapoint_key,
            status=item.status,
            value=item.value,
            evidence_chunk_ids=item.evidence_chunk_ids,
            rationale=item.rationale,
        )
        for item in sorted(assessments, key=lambda item: item.datapoint_key)
    ]
    total = len(rows)
    present = sum(1 for item in rows if item.status == "Present")
    partial = sum(1 for item in rows if item.status == "Partial")
    absent = sum(1 for item in rows if item.status == "Absent")
    na = sum(1 for item in rows if item.status == "NA")
    covered = present + partial
    denominator = total - na
    coverage_pct = (covered / denominator * 100.0) if denominator else 0.0
    if denominator == 0:
        overall_rating = "INCOMPLETE DATA"
        final_determination = "INCOMPLETE"
    elif absent == 0 and partial == 0:
        overall_rating = "COMPLIANT"
        final_determination = "COMPLIANT"
    elif covered > 0:
        overall_rating = "PARTIALLY COMPLIANT"
        final_determination = "PARTIAL"
    else:
        overall_rating = "NON-COMPLIANT"
        final_determination = "HIGH RISK"
    return ReportData(
        run_id=run_id,
        rows=rows,
        total_datapoints=total,
        denominator_datapoints=denominator,
        excluded_na_count=na,
        present=present,
        partial=partial,
        absent=absent,
        na=na,
        covered=covered,
        coverage_pct=coverage_pct,
        overall_rating=overall_rating,
        final_determination=final_determination,
    )


def generate_html_report(
    *,
    run_id: int,
    assessments: Sequence[DatapointAssessment],
    generated_at: datetime | None = None,
    include_registry_report_matrix: bool = False,
    metadata: ReportManifestMetadata | None = None,
) -> str:
    """Render deterministic HTML report content from datapoint assessments."""
    report = build_report_data(run_id=run_id, assessments=assessments)

    gap_items = [item for item in report.rows if item.status in {"Absent", "Partial"}]
    gap_summary_items = "".join(
        f"<li><strong>{html.escape(item.datapoint_key)}</strong>: {html.escape(item.status)}</li>"
        for item in gap_items
    )
    if not gap_summary_items:
        gap_summary_items = "<li>No gaps identified.</li>"

    table_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(item.datapoint_key)}</td>"
            f"<td>{html.escape(item.status)}</td>"
            f"<td>{html.escape(item.value or '-')}</td>"
            f"<td>{_citations(item.evidence_chunk_ids)}</td>"
            f"<td>{html.escape(item.rationale)}</td>"
            "</tr>"
        )
        for item in report.rows
    )

    metadata = metadata or ReportManifestMetadata()
    registry_section = ""
    if include_registry_report_matrix:
        obligation_ids: list[str] = []
        if metadata.obligations_applied_count and metadata.regulatory_registry_version != "n/a":
            # Kept as metadata-only hint; IDs themselves are rendered from plan where available.
            obligation_ids = []
        rows = compute_registry_coverage_matrix(assessments, obligation_ids=obligation_ids)
        matrix_rows = "".join(
            (
                "<tr>"
                f"<td>{html.escape(row.obligation_id)}</td>"
                f"<td>{row.total_elements}</td>"
                f"<td>{row.present}</td>"
                f"<td>{row.partial}</td>"
                f"<td>{row.absent}</td>"
                f"<td>{row.na}</td>"
                f"<td>{row.coverage_pct:.1f}%</td>"
                f"<td>{html.escape(row.status)}</td>"
                "</tr>"
            )
            for row in rows
        )
        if not matrix_rows:
            matrix_rows = (
                "<tr><td colspan=\"8\">No registry datapoints available for this run.</td></tr>"
            )
        registry_section = (
            "<section id=\"registry-coverage-matrix\">"
            "<h2>Registry Coverage Matrix</h2>"
            "<table>"
            "<thead><tr>"
            "<th>Obligation</th><th>Elements</th><th>Present</th><th>Partial</th>"
            "<th>Absent</th><th>NA</th><th>Coverage</th><th>Status</th>"
            "</tr></thead>"
            f"<tbody>{matrix_rows}</tbody>"
            "</table>"
            "</section>"
        )

    generated_at_text = _to_generated_at(generated_at)
    return (
        "<!doctype html>"
        "<html lang=\"en\">"
        "<head><meta charset=\"utf-8\"><title>Compliance Report</title></head>"
        "<body>"
        f"<h1>Compliance Report for Run {report.run_id}</h1>"
        f"<section id=\"report-metadata\"><h2>Report Metadata</h2>"
        "<table><tbody>"
        f"<tr><th>Run ID</th><td>{report.run_id}</td></tr>"
        f"<tr><th>Generated On</th><td>{generated_at_text}</td></tr>"
        f"<tr><th>Report Template Version</th><td>{REPORT_TEMPLATE_VERSION}</td></tr>"
        f"<tr><th>Requirements Bundles</th>"
        f"<td>{html.escape(metadata.requirements_bundles)}</td></tr>"
        f"<tr><th>Regulatory Registry Version</th>"
        f"<td>{html.escape(metadata.regulatory_registry_version)}</td></tr>"
        f"<tr><th>Compiler Version</th><td>{html.escape(metadata.compiler_version)}</td></tr>"
        f"<tr><th>Model Used</th><td>{html.escape(metadata.model_used)}</td></tr>"
        f"<tr><th>Retrieval Parameters</th>"
        f"<td>{html.escape(metadata.retrieval_parameters)}</td></tr>"
        f"<tr><th>Git SHA</th><td>{html.escape(metadata.git_sha)}</td></tr>"
        f"<tr><th>Applied Regimes</th><td>{html.escape(metadata.applied_regimes)}</td></tr>"
        f"<tr><th>Applied Overlays</th><td>{html.escape(metadata.applied_overlays)}</td></tr>"
        f"<tr><th>Obligations Applied</th><td>{metadata.obligations_applied_count}</td></tr>"
        "</tbody></table></section>"
        "<section id=\"executive-summary\">"
        "<h2>Executive Summary</h2>"
        f"<p>Coverage: {report.covered}/{report.denominator_datapoints} "
        f"applicable datapoints ({report.coverage_pct:.1f}%). "
        f"NA excluded: {report.excluded_na_count}.</p>"
        f"<p>Overall Compliance Rating: <strong>{report.overall_rating}</strong></p>"
        f"<p>Final Determination: <strong>{report.final_determination}</strong></p>"
        "</section>"
        "<section id=\"regulatory-framework-applicability\">"
        "<h2>Regulatory Framework &amp; Applicability</h2>"
        "<p>No evidence was identified in reviewed materials.</p>"
        "</section>"
        "<section id=\"public-filing-inventory\">"
        "<h2>Public Filing &amp; Disclosure Inventory</h2>"
        "<table><thead><tr><th>Document Title</th><th>Publication Date</th>"
        "<th>Document Type</th><th>Regime Linkage</th><th>Evidence Source ID</th>"
        "</tr></thead><tbody></tbody></table>"
        "</section>"
        "<section id=\"material-topics-esrs-mapping\">"
        "<h2>Material Topics &amp; ESRS Mapping</h2>"
        "<p>No evidence was identified in reviewed materials.</p>"
        "</section>"
        "<section id=\"quantitative-performance-targets\">"
        "<h2>Quantitative Performance &amp; Targets</h2>"
        "<table><thead><tr><th>Target Area</th><th>Baseline Year</th><th>Baseline Value</th>"
        "<th>Latest Value</th><th>Target</th><th>Progress %</th><th>Status</th>"
        "</tr></thead><tbody></tbody></table>"
        "</section>"
        "<section id=\"esrs-disclosure-compliance-matrix\">"
        "<h2>ESRS Disclosure Compliance Matrix</h2>"
        "</section>"
        "<section id=\"jurisdiction-specific-compliance\">"
        "<h2>Jurisdiction-Specific Compliance</h2>"
        "</section>"
        "<section id=\"assurance-framework-alignment\">"
        "<h2>Assurance &amp; External Framework Alignment</h2>"
        "</section>"
        "<section id=\"coverage-metrics\">"
        "<h2>Coverage Metrics</h2>"
        "<ul>"
        f"<li>Present: {report.present}</li>"
        f"<li>Partial: {report.partial}</li>"
        f"<li>Absent: {report.absent}</li>"
        f"<li>NA: {report.na}</li>"
        f"<li>Denominator (excludes NA): {report.denominator_datapoints}</li>"
        "</ul>"
        "</section>"
        "<section id=\"gap-summary\">"
        "<h2>Gap Summary</h2>"
        f"<ul>{gap_summary_items}</ul>"
        "</section>"
        "<section id=\"datapoint-table\">"
        "<h2>Datapoint Table</h2>"
        "<table>"
        "<thead><tr><th>Datapoint</th><th>Status</th><th>Value</th><th>Citations</th><th>Rationale</th></tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table>"
        "</section>"
        "<section id=\"conclusion\">"
        "<h2>Conclusion</h2>"
        f"<p>Final Determination: <strong>{report.final_determination}</strong></p>"
        "</section>"
        "<section id=\"appendix-evidence-traceability\">"
        "<h2>Appendix A — Evidence Traceability</h2>"
        "</section>"
        "<section id=\"appendix-manifest-snapshot\">"
        "<h2>Appendix B — Run Manifest Snapshot</h2>"
        "</section>"
        f"{registry_section}"
        f"<footer>Generated at <span id=\"generated-at\">{generated_at_text}</span></footer>"
        "</body>"
        "</html>"
    )


def normalize_report_html(html_text: str) -> str:
    """Normalize non-deterministic report fields for snapshot testing."""
    return _TIMESTAMP_PATTERN.sub('<span id="generated-at">TIMESTAMP</span>', html_text)

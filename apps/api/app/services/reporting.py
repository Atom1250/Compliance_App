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
    return rows


def generate_html_report(
    *,
    run_id: int,
    assessments: Sequence[DatapointAssessment],
    generated_at: datetime | None = None,
    include_registry_report_matrix: bool = False,
) -> str:
    """Render deterministic HTML report content from datapoint assessments."""
    ordered = sorted(assessments, key=lambda item: item.datapoint_key)
    total = len(ordered)
    present = sum(1 for item in ordered if item.status == "Present")
    partial = sum(1 for item in ordered if item.status == "Partial")
    absent = sum(1 for item in ordered if item.status == "Absent")
    na = sum(1 for item in ordered if item.status == "NA")
    covered = present + partial
    coverage_pct = (covered / total * 100.0) if total else 0.0

    gap_items = [item for item in ordered if item.status in {"Absent", "Partial"}]
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
        for item in ordered
    )

    registry_section = ""
    if include_registry_report_matrix:
        rows = compute_registry_coverage_matrix(ordered)
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
        f"<h1>Compliance Report for Run {run_id}</h1>"
        "<section id=\"executive-summary\">"
        "<h2>Executive Summary</h2>"
        f"<p>Coverage: {covered}/{total} datapoints ({coverage_pct:.1f}%).</p>"
        "</section>"
        "<section id=\"coverage-metrics\">"
        "<h2>Coverage Metrics</h2>"
        "<ul>"
        f"<li>Present: {present}</li>"
        f"<li>Partial: {partial}</li>"
        f"<li>Absent: {absent}</li>"
        f"<li>NA: {na}</li>"
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
        f"{registry_section}"
        f"<footer>Generated at <span id=\"generated-at\">{generated_at_text}</span></footer>"
        "</body>"
        "</html>"
    )


def normalize_report_html(html_text: str) -> str:
    """Normalize non-deterministic report fields for snapshot testing."""
    return _TIMESTAMP_PATTERN.sub('<span id="generated-at">TIMESTAMP</span>', html_text)

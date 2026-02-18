"""Deterministic HTML report generation for compliance assessments."""

from __future__ import annotations

import html
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime

from apps.api.app.db.models import DatapointAssessment

_TIMESTAMP_PATTERN = re.compile(
    r"<span id=\"generated-at\">[^<]+</span>",
)


def _to_generated_at(timestamp: datetime | None) -> str:
    value = timestamp or datetime.now(UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _citations(evidence_chunk_ids_json: str) -> str:
    chunk_ids = sorted(json.loads(evidence_chunk_ids_json))
    if not chunk_ids:
        return "-"
    return " ".join(f"<code>[{html.escape(chunk_id)}]</code>" for chunk_id in chunk_ids)


def generate_html_report(
    *,
    run_id: int,
    assessments: Sequence[DatapointAssessment],
    generated_at: datetime | None = None,
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
            "</tr>"
        )
        for item in ordered
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
        "<thead><tr><th>Datapoint</th><th>Status</th><th>Value</th><th>Citations</th></tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table>"
        "</section>"
        f"<footer>Generated at <span id=\"generated-at\">{generated_at_text}</span></footer>"
        "</body>"
        "</html>"
    )


def normalize_report_html(html_text: str) -> str:
    """Normalize non-deterministic report fields for snapshot testing."""
    return _TIMESTAMP_PATTERN.sub('<span id="generated-at">TIMESTAMP</span>', html_text)

from datetime import UTC, datetime

from apps.api.app.db.models import DatapointAssessment
from apps.api.app.services.reporting import generate_html_report, normalize_report_html


def _assessment(
    *,
    datapoint_key: str,
    status: str,
    value: str | None,
    evidence_chunk_ids: str,
) -> DatapointAssessment:
    return DatapointAssessment(
        run_id=1,
        datapoint_key=datapoint_key,
        status=status,
        value=value,
        evidence_chunk_ids=evidence_chunk_ids,
        rationale="rationale",
        model_name="gpt-5",
        prompt_hash="prompt-hash",
        retrieval_params='{"query_mode":"hybrid","top_k":3}',
    )


def test_html_report_snapshot_normalized_timestamp() -> None:
    assessments = [
        _assessment(
            datapoint_key="ESRS-E1-6",
            status="Present",
            value="42 tCO2e",
            evidence_chunk_ids='["chunk-b","chunk-a"]',
        ),
        _assessment(
            datapoint_key="ESRS-E1-1",
            status="Absent",
            value=None,
            evidence_chunk_ids="[]",
        ),
    ]

    html = generate_html_report(
        run_id=99,
        assessments=assessments,
        generated_at=datetime(2026, 2, 18, 12, 0, tzinfo=UTC),
    )
    normalized = normalize_report_html(html)

    expected = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>Compliance Report</title></head>"
        "<body><h1>Compliance Report for Run 99</h1><section id=\"executive-summary\">"
        "<h2>Executive Summary</h2><p>Coverage: 1/2 datapoints (50.0%).</p></section>"
        "<section id=\"coverage-metrics\"><h2>Coverage Metrics</h2><ul>"
        "<li>Present: 1</li><li>Partial: 0</li><li>Absent: 1</li><li>NA: 0</li>"
        "</ul></section><section id=\"gap-summary\"><h2>Gap Summary</h2><ul>"
        "<li><strong>ESRS-E1-1</strong>: Absent</li></ul></section><section id=\"datapoint-table\">"
        "<h2>Datapoint Table</h2><table><thead><tr><th>Datapoint</th><th>Status</th><th>Value</th>"
        "<th>Citations</th><th>Rationale</th></tr></thead><tbody>"
        "<tr><td>ESRS-E1-1</td><td>Absent</td><td>-</td><td>-</td><td>rationale</td></tr>"
        "<tr><td>ESRS-E1-6</td><td>Present</td><td>42 tCO2e</td>"
        "<td><code>[chunk-a]</code> <code>[chunk-b]</code></td><td>rationale</td></tr>"
        "</tbody></table></section><footer>Generated at "
        "<span id=\"generated-at\">TIMESTAMP</span></footer></body></html>"
    )
    assert normalized == expected


def test_html_report_is_stable_for_identical_inputs() -> None:
    assessments = [
        _assessment(
            datapoint_key="ESRS-E1-6",
            status="Present",
            value="42 tCO2e",
            evidence_chunk_ids='["chunk-b","chunk-a"]',
        ),
        _assessment(
            datapoint_key="ESRS-E1-1",
            status="Absent",
            value=None,
            evidence_chunk_ids="[]",
        ),
    ]

    first = normalize_report_html(generate_html_report(run_id=1, assessments=assessments))
    second = normalize_report_html(generate_html_report(run_id=1, assessments=assessments))
    assert first == second

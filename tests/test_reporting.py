from datetime import UTC, datetime

from apps.api.app.db.models import DatapointAssessment
from apps.api.app.services.reporting import (
    build_report_data,
    compute_registry_coverage_matrix,
    generate_html_report,
    normalize_report_html,
)


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

    assert "<h1>Compliance Report for Run 99</h1>" in normalized
    assert "<section id=\"report-metadata\">" in normalized
    assert "<section id=\"executive-summary\">" in normalized
    assert "<section id=\"esrs-disclosure-compliance-matrix\">" in normalized
    assert "<section id=\"appendix-evidence-traceability\">" in normalized
    assert "<section id=\"appendix-manifest-snapshot\">" in normalized
    assert "<li>Present: 1</li>" in normalized
    assert "<li>Absent: 1</li>" in normalized
    assert "<strong>ESRS-E1-1</strong>: Absent" in normalized
    assert "<span id=\"generated-at\">TIMESTAMP</span>" in normalized


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


def test_report_data_denominator_excludes_na() -> None:
    assessments = [
        _assessment(
            datapoint_key="D1",
            status="Present",
            value="x",
            evidence_chunk_ids='["chunk-1"]',
        ),
        _assessment(
            datapoint_key="D2",
            status="NA",
            value=None,
            evidence_chunk_ids="[]",
        ),
        _assessment(
            datapoint_key="D3",
            status="Absent",
            value=None,
            evidence_chunk_ids="[]",
        ),
    ]
    report = build_report_data(run_id=1, assessments=assessments)
    assert report.total_datapoints == 3
    assert report.denominator_datapoints == 2
    assert report.excluded_na_count == 1
    assert report.covered == 1
    assert report.coverage_pct == 50.0


def test_registry_coverage_matrix_is_deterministic() -> None:
    assessments = [
        _assessment(
            datapoint_key="OBL-B::Z",
            status="Absent",
            value=None,
            evidence_chunk_ids="[]",
        ),
        _assessment(
            datapoint_key="OBL-A::A",
            status="Present",
            value="yes",
            evidence_chunk_ids='["chunk-1"]',
        ),
        _assessment(
            datapoint_key="OBL-A::B",
            status="Partial",
            value="partial",
            evidence_chunk_ids='["chunk-2"]',
        ),
        _assessment(
            datapoint_key="ESRS-E1-1",
            status="Absent",
            value=None,
            evidence_chunk_ids="[]",
        ),
    ]

    rows = compute_registry_coverage_matrix(assessments)
    assert [row.obligation_id for row in rows] == ["OBL-A", "OBL-B"]
    assert rows[0].total_elements == 2
    assert rows[0].present == 1
    assert rows[0].partial == 1
    assert rows[0].absent == 0
    assert rows[0].na == 0
    assert rows[0].coverage_pct == 100.0
    assert rows[0].status == "Partial"
    assert rows[1].status == "Absent"


def test_html_report_registry_matrix_rendering_is_flagged() -> None:
    assessments = [
        _assessment(
            datapoint_key="OBL-1::A",
            status="Present",
            value="ok",
            evidence_chunk_ids='["chunk-a"]',
        ),
    ]

    disabled = generate_html_report(
        run_id=7,
        assessments=assessments,
        generated_at=datetime(2026, 2, 18, 12, 0, tzinfo=UTC),
        include_registry_report_matrix=False,
    )
    enabled = generate_html_report(
        run_id=7,
        assessments=assessments,
        generated_at=datetime(2026, 2, 18, 12, 0, tzinfo=UTC),
        include_registry_report_matrix=True,
    )
    assert 'id="registry-coverage-matrix"' not in disabled
    assert 'id="registry-coverage-matrix"' in enabled
    assert "<td>OBL-1</td>" in enabled
    assert "<td>100.0%</td>" in enabled

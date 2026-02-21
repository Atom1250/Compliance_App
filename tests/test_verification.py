from apps.api.app.services.retrieval import RetrievalResult
from apps.api.app.services.verification import verify_assessment


def _retrieval_result(chunk_id: str, text: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id=1,
        page_number=1,
        start_offset=0,
        end_offset=len(text),
        text=text,
        lexical_score=1.0,
        vector_score=0.0,
        combined_score=1.0,
    )


def test_verification_keeps_status_when_numeric_unit_and_year_match() -> None:
    result = verify_assessment(
        status="Present",
        value="42 tCO2e FY2025",
        evidence_chunk_ids=["chunk-1"],
        rationale="Extracted from annual report.",
        retrieval_results=[
            _retrieval_result("chunk-1", "For FY2025, gross Scope 1 emissions are 42 tCO2e.")
        ],
    )

    assert result.status == "Present"
    assert "Verification downgraded" not in result.rationale


def test_verification_downgrades_present_when_numeric_not_in_cited_chunk() -> None:
    result = verify_assessment(
        status="Present",
        value="99",
        evidence_chunk_ids=["chunk-1"],
        rationale="Extracted from annual report.",
        retrieval_results=[_retrieval_result("chunk-1", "Gross Scope 1 emissions are 42 tCO2e.")],
    )

    assert result.status == "Absent"
    assert result.failure_reason_code == "NUMERIC_MISMATCH"
    assert "numeric value not found in evidence: 99" in result.rationale


def test_verification_downgrades_present_when_year_missing() -> None:
    result = verify_assessment(
        status="Present",
        value="42 FY2026",
        evidence_chunk_ids=["chunk-1"],
        rationale="Extracted from annual report.",
        retrieval_results=[_retrieval_result("chunk-1", "For FY2025, emissions are 42 tCO2e.")],
    )

    assert result.status == "Absent"
    assert result.failure_reason_code == "NUMERIC_MISMATCH"
    assert "year not found in evidence: 2026" in result.rationale


def test_verification_downgrades_partial_to_absent_when_evidence_chunk_missing() -> None:
    result = verify_assessment(
        status="Partial",
        value="42",
        evidence_chunk_ids=["missing-chunk"],
        rationale="Extracted from annual report.",
        retrieval_results=[_retrieval_result("chunk-1", "For FY2025, emissions are 42 tCO2e.")],
    )

    assert result.status == "Absent"
    assert result.failure_reason_code == "CHUNK_NOT_FOUND"
    assert "missing cited chunk(s): missing-chunk" in result.rationale


def test_metric_verification_requires_baseline_when_configured() -> None:
    result = verify_assessment(
        status="Present",
        value="12.5 % FY2026",
        evidence_chunk_ids=["chunk-1"],
        rationale="Metric extracted.",
        retrieval_results=[_retrieval_result("chunk-1", "FY2026 emissions reduced by 12.5%.")],
        datapoint_type="metric",
        requires_baseline=True,
    )
    assert result.status == "Absent"
    assert result.failure_reason_code == "BASELINE_MISSING"


def test_verification_enforces_evidence_gating_for_present_without_evidence() -> None:
    result = verify_assessment(
        status="Present",
        value="42",
        evidence_chunk_ids=[],
        rationale="Model marked as present.",
        retrieval_results=[
            RetrievalResult(
                chunk_id="chunk-1",
                document_id=1,
                page_number=1,
                start_offset=0,
                end_offset=20,
                text="42 appears in this passage.",
                lexical_score=0.5,
                vector_score=0.4,
                combined_score=0.46,
            )
        ],
    )

    assert result.status == "Absent"
    assert "Evidence gating downgraded: missing evidence_chunk_ids." in result.rationale


def test_verification_enforces_evidence_gating_for_partial_without_evidence() -> None:
    result = verify_assessment(
        status="Partial",
        value="42",
        evidence_chunk_ids=[],
        rationale="Model marked as partial.",
        retrieval_results=[
            RetrievalResult(
                chunk_id="chunk-1",
                document_id=1,
                page_number=1,
                start_offset=0,
                end_offset=20,
                text="42 appears in this passage.",
                lexical_score=0.5,
                vector_score=0.4,
                combined_score=0.46,
            )
        ],
    )

    assert result.status == "Absent"
    assert "Evidence gating downgraded: missing evidence_chunk_ids." in result.rationale

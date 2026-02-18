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

    assert result.status == "Partial"
    assert "numeric value not found in evidence: 99" in result.rationale


def test_verification_downgrades_present_when_year_missing() -> None:
    result = verify_assessment(
        status="Present",
        value="42 FY2026",
        evidence_chunk_ids=["chunk-1"],
        rationale="Extracted from annual report.",
        retrieval_results=[_retrieval_result("chunk-1", "For FY2025, emissions are 42 tCO2e.")],
    )

    assert result.status == "Partial"
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
    assert "missing cited chunk(s): missing-chunk" in result.rationale

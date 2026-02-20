"""Post-extraction verification for deterministic assessment downgrades."""

from __future__ import annotations

import re
from dataclasses import dataclass

from apps.api.app.services.retrieval import RetrievalResult

_STATUS_PRESENT = "Present"
_STATUS_PARTIAL = "Partial"
_STATUS_ABSENT = "Absent"

_NUMBER_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)?")
_YEAR_PATTERN = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_UNIT_PATTERN = re.compile(r"(?i)\b(?:tco2e|co2e|kg|tonnes?|tons?|mwh|kwh|gwh|eur|usd)\b")


@dataclass(frozen=True)
class VerificationResult:
    status: str
    rationale: str
    verification_status: str
    failure_reason_code: str | None
    numeric_matches_found: list[str]
    metric_payload: dict[str, object] | None = None


def _extract_numbers(text: str) -> list[str]:
    return [item.replace(",", ".") for item in _NUMBER_PATTERN.findall(text)]


def _extract_years(text: str) -> list[str]:
    return _YEAR_PATTERN.findall(text)


def _extract_units(text: str) -> list[str]:
    units: list[str] = []
    if "%" in text:
        units.append("%")
    for candidate in _UNIT_PATTERN.findall(text):
        token = candidate.lower()
        if token not in units:
            units.append(token)
    return units


def _downgrade_status(status: str) -> str:
    if status == _STATUS_PRESENT:
        return _STATUS_PARTIAL
    if status == _STATUS_PARTIAL:
        return _STATUS_ABSENT
    return status


def _enforce_evidence_gating(status: str, evidence_chunk_ids: list[str]) -> str:
    if status in {_STATUS_PRESENT, _STATUS_PARTIAL} and not evidence_chunk_ids:
        return _STATUS_ABSENT
    return status


def verify_assessment(
    *,
    status: str,
    value: str | None,
    evidence_chunk_ids: list[str],
    rationale: str,
    retrieval_results: list[RetrievalResult],
    datapoint_type: str = "narrative",
    requires_baseline: bool = False,
) -> VerificationResult:
    """Validate extracted value/evidence consistency with deterministic downgrade rules."""
    if status not in {_STATUS_PRESENT, _STATUS_PARTIAL}:
        return VerificationResult(
            status=status,
            rationale=rationale,
            verification_status="pass",
            failure_reason_code=None,
            numeric_matches_found=[],
            metric_payload=None,
        )

    if not evidence_chunk_ids:
        return VerificationResult(
            status=_STATUS_ABSENT,
            rationale=f"{rationale} Evidence gating downgraded: missing evidence_chunk_ids.",
            verification_status="failed",
            failure_reason_code="CHUNK_NOT_FOUND",
            numeric_matches_found=[],
            metric_payload=None,
        )

    by_chunk_id = {item.chunk_id: item.text for item in retrieval_results}
    failures: list[str] = []
    failure_reason_code: str | None = None

    missing_chunk_ids = [chunk_id for chunk_id in evidence_chunk_ids if chunk_id not in by_chunk_id]
    if missing_chunk_ids:
        failures.append(f"missing cited chunk(s): {','.join(sorted(missing_chunk_ids))}")
        failure_reason_code = "CHUNK_NOT_FOUND"
        return VerificationResult(
            status=_STATUS_ABSENT,
            rationale=(
                f"{rationale} Verification downgraded: "
                f"{'; '.join(sorted(set(failures)))}."
            ),
            verification_status="failed",
            failure_reason_code=failure_reason_code,
            numeric_matches_found=[],
            metric_payload=None,
        )

    cited_text = " ".join(
        by_chunk_id[chunk_id] for chunk_id in evidence_chunk_ids if chunk_id in by_chunk_id
    )
    if not cited_text.strip():
        failures.append("cited chunks empty")
        failure_reason_code = "EMPTY_CHUNK"
        return VerificationResult(
            status=_STATUS_ABSENT,
            rationale=(
                f"{rationale} Verification downgraded: "
                f"{'; '.join(sorted(set(failures)))}."
            ),
            verification_status="failed",
            failure_reason_code=failure_reason_code,
            numeric_matches_found=[],
            metric_payload=None,
        )
    cited_text_lower = cited_text.lower()
    value_text = value or ""

    years = set(_extract_years(value_text))
    numeric_matches_found: list[str] = []
    for numeric_token in _extract_numbers(value_text):
        if numeric_token in years:
            continue
        if numeric_token in cited_text.replace(",", "."):
            numeric_matches_found.append(numeric_token)
            continue
        if numeric_token not in cited_text.replace(",", "."):
            failures.append(f"numeric value not found in evidence: {numeric_token}")
            failure_reason_code = "NUMERIC_MISMATCH"

    for year in years:
        if year not in cited_text:
            failures.append(f"year not found in evidence: {year}")
            failure_reason_code = "NUMERIC_MISMATCH"

    for unit in _extract_units(value_text):
        if unit not in cited_text_lower:
            failures.append(f"unit not found in evidence: {unit}")
            failure_reason_code = "NUMERIC_MISMATCH"

    metric_payload: dict[str, object] | None = None
    if datapoint_type == "metric":
        numbers = _extract_numbers(value_text)
        units = _extract_units(value_text)
        metric_years = _extract_years(value_text)
        if not numbers or not units or not metric_years:
            failures.append("metric payload missing value/unit/year")
            failure_reason_code = failure_reason_code or "NUMERIC_MISMATCH"
        else:
            metric_payload = {
                "value": float(numbers[0]),
                "unit": units[0],
                "year": int(metric_years[0]),
                "source_chunk_id": evidence_chunk_ids[0] if evidence_chunk_ids else None,
            }
            if "%" in value_text or requires_baseline:
                baseline_years = _extract_years(value_text)
                baseline_numbers = _extract_numbers(value_text)
                if len(baseline_years) < 2 or len(baseline_numbers) < 2:
                    failures.append("metric baseline missing")
                    failure_reason_code = "BASELINE_MISSING"
                else:
                    metric_payload["baseline_year"] = int(baseline_years[1])
                    metric_payload["baseline_value"] = float(baseline_numbers[1])

    downgraded_status = status
    updated_rationale = rationale
    if failures:
        downgraded_status = _STATUS_ABSENT
        updated_rationale = (
            f"{rationale} Verification downgraded: {'; '.join(sorted(set(failures)))}."
        )

    enforced_status = _enforce_evidence_gating(downgraded_status, evidence_chunk_ids)
    if enforced_status != downgraded_status:
        updated_rationale = (
            f"{updated_rationale} Evidence gating downgraded: missing evidence_chunk_ids."
        )
    return VerificationResult(
        status=enforced_status,
        rationale=updated_rationale,
        verification_status="failed" if failures else "pass",
        failure_reason_code=failure_reason_code,
        numeric_matches_found=sorted(set(numeric_matches_found)),
        metric_payload=metric_payload,
    )

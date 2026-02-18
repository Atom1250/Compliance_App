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
_UNIT_PATTERN = re.compile(r"(?i)\b(?:tco2e|co2e|%|kg|tonnes?|tons?|mwh|kwh|gwh|eur|usd)\b")


@dataclass(frozen=True)
class VerificationResult:
    status: str
    rationale: str


def _extract_numbers(text: str) -> list[str]:
    return [item.replace(",", ".") for item in _NUMBER_PATTERN.findall(text)]


def _extract_years(text: str) -> list[str]:
    return _YEAR_PATTERN.findall(text)


def _extract_units(text: str) -> list[str]:
    units: list[str] = []
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


def verify_assessment(
    *,
    status: str,
    value: str | None,
    evidence_chunk_ids: list[str],
    rationale: str,
    retrieval_results: list[RetrievalResult],
) -> VerificationResult:
    """Validate extracted value/evidence consistency with deterministic downgrade rules."""
    if status not in {_STATUS_PRESENT, _STATUS_PARTIAL}:
        return VerificationResult(status=status, rationale=rationale)

    by_chunk_id = {item.chunk_id: item.text for item in retrieval_results}
    failures: list[str] = []

    missing_chunk_ids = [chunk_id for chunk_id in evidence_chunk_ids if chunk_id not in by_chunk_id]
    if missing_chunk_ids:
        failures.append(f"missing cited chunk(s): {','.join(sorted(missing_chunk_ids))}")

    cited_text = " ".join(
        by_chunk_id[chunk_id] for chunk_id in evidence_chunk_ids if chunk_id in by_chunk_id
    )
    cited_text_lower = cited_text.lower()
    value_text = value or ""

    years = set(_extract_years(value_text))
    for numeric_token in _extract_numbers(value_text):
        if numeric_token in years:
            continue
        if numeric_token not in cited_text.replace(",", "."):
            failures.append(f"numeric value not found in evidence: {numeric_token}")

    for year in years:
        if year not in cited_text:
            failures.append(f"year not found in evidence: {year}")

    for unit in _extract_units(value_text):
        if unit not in cited_text_lower:
            failures.append(f"unit not found in evidence: {unit}")

    if not failures:
        return VerificationResult(status=status, rationale=rationale)

    downgraded_status = _downgrade_status(status)
    updated_rationale = f"{rationale} Verification downgraded: {'; '.join(sorted(set(failures)))}."
    return VerificationResult(status=downgraded_status, rationale=updated_rationale)

"""Deterministic green finance obligations matrix generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.green_finance.schema import GreenFinanceBundle, GreenFinanceObligation
from apps.api.app.db.models import DatapointAssessment


def load_green_finance_bundle(bundle_path: Path) -> GreenFinanceBundle:
    payload = json.loads(bundle_path.read_text())
    return GreenFinanceBundle.model_validate(payload)


def generate_obligations_matrix(
    *,
    enabled: bool,
    obligations: list[GreenFinanceObligation],
    produced_artifacts: set[str],
    produced_data_elements: set[str],
    evidence_by_obligation: dict[str, list[str]],
) -> list[dict[str, object]]:
    """Return deterministic obligations matrix rows for green finance mode."""
    if not enabled:
        return []

    rows: list[dict[str, object]] = []
    for obligation in sorted(obligations, key=lambda item: item.obligation_id):
        required_items = sorted(
            set(obligation.required_artifacts) | set(obligation.required_data_elements)
        )
        missing_items = [
            item
            for item in required_items
            if item not in produced_artifacts and item not in produced_data_elements
        ]
        evidence = sorted(set(evidence_by_obligation.get(obligation.obligation_id, [])))
        produced = len(missing_items) == 0
        rows.append(
            {
                "obligation": obligation.obligation,
                "required": required_items,
                "produced": produced,
                "evidence": evidence,
                "gap": missing_items,
            }
        )
    return rows


def generate_obligations_matrix_from_assessments(
    *,
    enabled: bool,
    obligations: list[GreenFinanceObligation],
    assessments: list[DatapointAssessment],
) -> list[dict[str, object]]:
    """Render obligations matrix directly from extracted green-finance assessments."""
    if not enabled:
        return []

    assessments_by_key = {row.datapoint_key: row for row in assessments}
    rows: list[dict[str, object]] = []
    for obligation in sorted(obligations, key=lambda item: item.obligation_id):
        required_items = sorted(
            set(obligation.required_artifacts) | set(obligation.required_data_elements)
        )
        assessment = assessments_by_key.get(obligation.obligation_id)
        evidence: list[str] = []
        produced = False
        if assessment is not None:
            evidence = sorted(set(json.loads(assessment.evidence_chunk_ids)))
            produced = assessment.status in {"Present", "Partial"} and len(evidence) > 0

        rows.append(
            {
                "obligation": obligation.obligation,
                "required": required_items,
                "produced": produced,
                "evidence": evidence,
                "gap": [] if produced else required_items,
            }
        )
    return rows

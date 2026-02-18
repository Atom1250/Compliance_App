"""Deterministic green finance obligations matrix generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.green_finance.schema import GreenFinanceBundle, GreenFinanceObligation


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

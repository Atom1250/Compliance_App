"""Adapter views for legacy datapoints and obligations-native bundle content."""

from __future__ import annotations

from dataclasses import dataclass

from app.requirements.schema import DatapointDefinition, RequirementsBundle


@dataclass(frozen=True)
class ObligationElementView:
    obligation_id: str
    obligation: str
    element_key: str
    required_artifacts: tuple[str, ...]


def iter_datapoints(bundle: RequirementsBundle) -> list[DatapointDefinition]:
    """Return legacy datapoints with deterministic ordering."""
    return sorted(bundle.datapoints, key=lambda item: item.datapoint_key)


def iter_obligation_elements(bundle: RequirementsBundle) -> list[ObligationElementView]:
    """Return deterministic flattened obligation elements for obligations-native bundles."""
    views: list[ObligationElementView] = []
    for obligation in sorted(bundle.obligations, key=lambda item: item.obligation_id):
        for element in sorted(obligation.required_data_elements):
            views.append(
                ObligationElementView(
                    obligation_id=obligation.obligation_id,
                    obligation=obligation.obligation,
                    element_key=element,
                    required_artifacts=tuple(sorted(obligation.required_artifacts)),
                )
            )
    return views


"""Generate deterministic datapoint keys from compiled regulatory plans."""

from __future__ import annotations

from dataclasses import dataclass

from app.regulatory.compiler import CompiledRegulatoryPlan


@dataclass(frozen=True)
class GeneratedDatapoint:
    datapoint_key: str
    title: str
    disclosure_reference: str


def generate_registry_datapoints(plan: CompiledRegulatoryPlan) -> list[GeneratedDatapoint]:
    generated: list[GeneratedDatapoint] = []
    for obligation in sorted(plan.obligations, key=lambda item: item.obligation_id):
        for element in sorted(obligation.elements, key=lambda item: item.element_id):
            generated.append(
                GeneratedDatapoint(
                    datapoint_key=f"{obligation.obligation_id}::{element.element_id}",
                    title=f"{obligation.title} - {element.label}",
                    disclosure_reference=obligation.standard_reference,
                )
            )
    return generated


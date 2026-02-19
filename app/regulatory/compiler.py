"""Regulatory compiler: bundle -> deterministic compiled plan."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.regulatory.safe_eval import evaluate_expression
from app.regulatory.schema import Element, Obligation, RegulatoryBundle


class CompiledElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    required: bool


class CompiledObligation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    standard_reference: str = Field(min_length=1)
    elements: list[CompiledElement] = Field(default_factory=list)


class CompiledRegulatoryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    regime: str = Field(min_length=1)
    obligations: list[CompiledObligation] = Field(default_factory=list)


def _rule_expression(rule_key: str, operator: str, value: str | int | float | bool) -> str:
    path = rule_key if "." in rule_key else f"company.{rule_key}"
    return f"{path} {operator} {repr(value)}"


def _element_applies(element: Element, *, context: dict[str, Any]) -> bool:
    if not element.phase_in_rules:
        return True
    allowed_symbols = set(context.keys())
    for rule in element.phase_in_rules:
        expression = _rule_expression(rule.key, rule.operator, rule.value)
        if not evaluate_expression(expression, context=context, allowed_symbols=allowed_symbols):
            return False
    return True


def _compile_obligation(
    obligation: Obligation,
    *,
    context: dict[str, Any],
) -> CompiledObligation | None:
    compiled_elements: list[CompiledElement] = []
    for element in sorted(obligation.elements, key=lambda item: item.element_id):
        if not _element_applies(element, context=context):
            continue
        compiled_elements.append(
            CompiledElement(
                element_id=element.element_id,
                label=element.label,
                required=element.required,
            )
        )
    if not compiled_elements:
        return None
    return CompiledObligation(
        obligation_id=obligation.obligation_id,
        title=obligation.title,
        standard_reference=obligation.standard_reference,
        elements=compiled_elements,
    )


def compile_bundle(
    bundle: RegulatoryBundle,
    *,
    context: dict[str, Any],
) -> CompiledRegulatoryPlan:
    """Compile a bundle deterministically to applicable obligations/elements."""
    obligations: list[CompiledObligation] = []
    for obligation in sorted(bundle.obligations, key=lambda item: item.obligation_id):
        compiled = _compile_obligation(obligation, context=context)
        if compiled is not None:
            obligations.append(compiled)
    return CompiledRegulatoryPlan(
        bundle_id=bundle.bundle_id,
        version=bundle.version,
        jurisdiction=bundle.jurisdiction,
        regime=bundle.regime,
        obligations=obligations,
    )


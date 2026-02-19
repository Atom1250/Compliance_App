"""Pydantic schema for regulatory bundles (v1 minimal)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PhaseInRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    value: str | int | float | bool


class Element(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    required: bool = True
    phase_in_rules: list[PhaseInRule] = Field(default_factory=list)


class Obligation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    standard_reference: str = Field(min_length=1)
    elements: list[Element] = Field(default_factory=list)


class RegulatoryBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    regime: str = Field(min_length=1)
    obligations: list[Obligation] = Field(default_factory=list)


"""Pydantic schema for regulatory bundles (v1, backward compatible extensions)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PhaseInRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    value: str | int | float | bool


class Element(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: str = Field(default="narrative", min_length=1)
    required: bool = True
    phase_in_rules: list[PhaseInRule] = Field(default_factory=list)


class Obligation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str = Field(min_length=1)
    title: str = Field(default="", min_length=0)
    standard_reference: str = Field(default="", min_length=0)
    standard_ref: str = Field(default="", min_length=0)
    disclosure_reference: str = Field(default="", min_length=0)
    applies_if: str = Field(default="", min_length=0)
    phase_in: dict[str, Any] | None = None
    source_record_ids: list[str] = Field(default_factory=list)
    elements: list[Element] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize_fields(self) -> Obligation:
        # Backward compatibility: existing bundles use standard_reference/title only.
        if not self.standard_ref and self.standard_reference:
            self.standard_ref = self.standard_reference
        if not self.standard_reference and self.standard_ref:
            self.standard_reference = self.standard_ref
        if not self.title:
            self.title = self.obligation_id
        if not self.disclosure_reference:
            self.disclosure_reference = self.standard_reference or self.standard_ref
        return self


class Overlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jurisdiction: str = Field(min_length=1)
    overlay_id: str = Field(min_length=1)
    obligations_add: list[Obligation] = Field(default_factory=list)
    obligations_modify: list[dict[str, Any]] = Field(default_factory=list)
    obligations_disable: list[str] = Field(default_factory=list)


class RegulatoryBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    regime: str = Field(min_length=1)
    source_record_ids: list[str] = Field(default_factory=list)
    applicability_rules: list[str] = Field(default_factory=list)
    overlays: list[Overlay] = Field(default_factory=list)
    compiler_version: str = Field(default="reg-compiler-v1", min_length=1)
    obligations: list[Obligation] = Field(default_factory=list)

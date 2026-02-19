"""Schema definitions for requirements bundles."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatapointDefinition(BaseModel):
    datapoint_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    disclosure_reference: str = Field(min_length=1)
    materiality_topic: str = Field(default="general", min_length=1)


class ApplicabilityRule(BaseModel):
    rule_id: str = Field(min_length=1)
    datapoint_key: str = Field(min_length=1)
    expression: str = Field(min_length=1)


class ObligationDefinition(BaseModel):
    obligation_id: str = Field(min_length=1)
    obligation: str = Field(min_length=1)
    required_artifacts: list[str] = Field(default_factory=list)
    required_data_elements: list[str] = Field(default_factory=list)


class RequirementsBundle(BaseModel):
    bundle_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    standard: str = Field(min_length=1)
    datapoints: list[DatapointDefinition]
    applicability_rules: list[ApplicabilityRule]
    obligations: list[ObligationDefinition] = Field(default_factory=list)

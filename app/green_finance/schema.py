"""Schema definitions for green finance obligations bundles."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GreenFinanceObligation(BaseModel):
    obligation_id: str = Field(min_length=1)
    obligation: str = Field(min_length=1)
    required_artifacts: list[str] = Field(default_factory=list)
    required_data_elements: list[str] = Field(default_factory=list)


class GreenFinanceBundle(BaseModel):
    bundle_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    obligations: list[GreenFinanceObligation]

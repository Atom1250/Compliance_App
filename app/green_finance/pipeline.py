"""Green finance extraction pipeline reusing the datapoint assessment engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.green_finance.matrix import (
    generate_obligations_matrix_from_assessments,
    load_green_finance_bundle,
)
from apps.api.app.db.models import DatapointAssessment
from apps.api.app.services.assessment_pipeline import AssessmentRunConfig, execute_assessment_pipeline
from apps.api.app.services.llm_extraction import ExtractionClient

_DEFAULT_BUNDLE_ID = "green_finance_icma_eugb"
_DEFAULT_BUNDLE_PATH = Path("requirements/green_finance_icma_eugb/bundle.json")


@dataclass(frozen=True)
class GreenFinanceRunConfig:
    run_id: int
    bundle_version: str
    enabled: bool
    retrieval_top_k: int = 5
    retrieval_model_name: str = "default"
    bundle_id: str = _DEFAULT_BUNDLE_ID
    bundle_path: Path = _DEFAULT_BUNDLE_PATH


def execute_green_finance_pipeline(
    db: Session,
    *,
    extraction_client: ExtractionClient,
    config: GreenFinanceRunConfig,
) -> tuple[list[DatapointAssessment], list[dict[str, object]]]:
    """Run retrieval+extraction for green finance obligations and return matrix rows."""
    if not config.enabled:
        return [], []

    assessments = execute_assessment_pipeline(
        db,
        extraction_client=extraction_client,
        config=AssessmentRunConfig(
            run_id=config.run_id,
            bundle_id=config.bundle_id,
            bundle_version=config.bundle_version,
            retrieval_top_k=config.retrieval_top_k,
            retrieval_model_name=config.retrieval_model_name,
        ),
    )
    bundle = load_green_finance_bundle(config.bundle_path)
    matrix = generate_obligations_matrix_from_assessments(
        enabled=True,
        obligations=bundle.obligations,
        assessments=assessments,
    )
    return assessments, matrix

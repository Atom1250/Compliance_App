"""Datapoint assessment pipeline (retrieval -> extraction -> persistence)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.db.models import DatapointAssessment, DatapointDefinition, RequirementBundle, Run
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.retrieval import retrieve_chunks


@dataclass(frozen=True)
class AssessmentRunConfig:
    run_id: int
    bundle_id: str
    bundle_version: str
    retrieval_top_k: int = 5
    retrieval_model_name: str = "default"


def execute_assessment_pipeline(
    db: Session,
    *,
    extraction_client: ExtractionClient,
    config: AssessmentRunConfig,
) -> list[DatapointAssessment]:
    """Execute deterministic retrieval->extraction->storage for required datapoints."""
    run = db.get(Run, config.run_id)
    if run is None:
        raise ValueError(f"Run not found: {config.run_id}")

    bundle = db.scalar(
        select(RequirementBundle).where(
            RequirementBundle.bundle_id == config.bundle_id,
            RequirementBundle.version == config.bundle_version,
        )
    )
    if bundle is None:
        raise ValueError(f"Bundle not found: {config.bundle_id}@{config.bundle_version}")

    required_datapoints = resolve_required_datapoint_ids(
        db,
        company_id=run.company_id,
        bundle_id=config.bundle_id,
        bundle_version=config.bundle_version,
        run_id=run.id,
    )

    datapoint_defs = {
        row.datapoint_key: row
        for row in db.scalars(
            select(DatapointDefinition)
            .where(DatapointDefinition.requirement_bundle_id == bundle.id)
            .order_by(DatapointDefinition.datapoint_key)
        ).all()
    }

    db.execute(delete(DatapointAssessment).where(DatapointAssessment.run_id == run.id))

    created: list[DatapointAssessment] = []
    retrieval_params_payload = {
        "top_k": config.retrieval_top_k,
        "retrieval_model_name": config.retrieval_model_name,
        "query_mode": "hybrid",
    }
    retrieval_params_json = json.dumps(
        retrieval_params_payload, sort_keys=True, separators=(",", ":")
    )

    for datapoint_key in sorted(required_datapoints):
        datapoint_def = datapoint_defs.get(datapoint_key)
        if datapoint_def is None:
            continue

        query = f"{datapoint_def.title} {datapoint_def.disclosure_reference}"
        retrieval_results = retrieve_chunks(
            db,
            query=query,
            query_embedding=None,
            top_k=config.retrieval_top_k,
            model_name=config.retrieval_model_name,
        )
        context_chunks = [item.text for item in retrieval_results]

        extraction = extraction_client.extract(
            datapoint_key=datapoint_key,
            context_chunks=context_chunks,
        )
        prompt = extraction_client.build_prompt(
            datapoint_key=datapoint_key,
            context_chunks=context_chunks,
        )
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        assessment = DatapointAssessment(
            run_id=run.id,
            datapoint_key=datapoint_key,
            status=extraction.status.value,
            value=extraction.value,
            evidence_chunk_ids=json.dumps(
                extraction.evidence_chunk_ids,
                sort_keys=True,
                separators=(",", ":"),
            ),
            rationale=extraction.rationale,
            model_name=extraction_client.model_name,
            prompt_hash=prompt_hash,
            retrieval_params=retrieval_params_json,
        )
        db.add(assessment)
        created.append(assessment)

    db.commit()
    for item in created:
        db.refresh(item)
    return created

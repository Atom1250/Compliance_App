"""Datapoint assessment pipeline (retrieval -> extraction -> persistence)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.regulatory.datapoint_generation import generate_registry_datapoints
from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import (
    Company,
    DatapointAssessment,
    DatapointDefinition,
    RequirementBundle,
    Run,
)
from apps.api.app.services.audit import append_run_event, log_structured_event
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.regulatory_registry import compile_from_db
from apps.api.app.services.retrieval import (
    get_retrieval_policy,
    retrieval_policy_to_dict,
    retrieve_chunks,
)
from apps.api.app.services.run_registry_artifacts import persist_retrieval_trace_for_run
from apps.api.app.services.verification import verify_assessment


@dataclass(frozen=True)
class AssessmentRunConfig:
    run_id: int
    bundle_id: str
    bundle_version: str
    retrieval_top_k: int = 5
    retrieval_model_name: str = "default"


@dataclass(frozen=True)
class _DatapointQueryDef:
    title: str
    disclosure_reference: str


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

    settings = get_settings()
    use_registry_mode = settings.feature_registry_compiler and run.compiler_mode == "registry"

    append_run_event(
        db,
        run_id=run.id,
        tenant_id=run.tenant_id,
        event_type="assessment.pipeline.started",
        payload={
            "tenant_id": run.tenant_id,
            "bundle_id": config.bundle_id,
            "bundle_version": config.bundle_version,
        },
    )
    log_structured_event(
        "assessment.pipeline.started",
        run_id=run.id,
        tenant_id=run.tenant_id,
        bundle_id=config.bundle_id,
        bundle_version=config.bundle_version,
    )

    if use_registry_mode:
        company = db.scalar(
            select(Company).where(Company.id == run.company_id, Company.tenant_id == run.tenant_id)
        )
        if company is None:
            raise ValueError(f"Company not found: {run.company_id}")

        compiled_plan = compile_from_db(
            db,
            bundle_id=config.bundle_id,
            version=config.bundle_version,
            context={
                "company": {
                    "employees": company.employees,
                    "turnover": company.turnover,
                    "listed_status": company.listed_status,
                    "reporting_year": company.reporting_year,
                    "reporting_year_start": company.reporting_year_start,
                    "reporting_year_end": company.reporting_year_end,
                }
            },
        )
        generated = generate_registry_datapoints(compiled_plan)
        required_datapoints = [item.datapoint_key for item in generated]
        datapoint_defs = {
            item.datapoint_key: _DatapointQueryDef(
                title=item.title,
                disclosure_reference=item.disclosure_reference,
            )
            for item in generated
        }
    else:
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
            row.datapoint_key: _DatapointQueryDef(
                title=row.title,
                disclosure_reference=row.disclosure_reference,
            )
            for row in db.scalars(
                select(DatapointDefinition)
                .where(DatapointDefinition.requirement_bundle_id == bundle.id)
                .order_by(DatapointDefinition.datapoint_key)
            ).all()
        }

    db.execute(
        delete(DatapointAssessment).where(
            DatapointAssessment.run_id == run.id,
            DatapointAssessment.tenant_id == run.tenant_id,
        )
    )

    created: list[DatapointAssessment] = []
    retrieval_params_payload = {
        "top_k": config.retrieval_top_k,
        "retrieval_model_name": config.retrieval_model_name,
        "query_mode": "hybrid",
        "retrieval_policy": retrieval_policy_to_dict(get_retrieval_policy()),
    }
    retrieval_policy_payload = retrieval_policy_to_dict(get_retrieval_policy())
    retrieval_params_json = json.dumps(
        retrieval_params_payload, sort_keys=True, separators=(",", ":")
    )
    retrieval_trace_entries: list[dict[str, object]] = []

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
            tenant_id=run.tenant_id,
            model_name=config.retrieval_model_name,
            policy=get_retrieval_policy(),
        )
        context_chunks = [item.text for item in retrieval_results]

        extraction = extraction_client.extract(
            datapoint_key=datapoint_key,
            context_chunks=context_chunks,
        )
        verification = verify_assessment(
            status=extraction.status.value,
            value=extraction.value,
            evidence_chunk_ids=extraction.evidence_chunk_ids,
            rationale=extraction.rationale,
            retrieval_results=retrieval_results,
        )
        prompt = extraction_client.build_prompt(
            datapoint_key=datapoint_key,
            context_chunks=context_chunks,
        )
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        assessment = DatapointAssessment(
            run_id=run.id,
            tenant_id=run.tenant_id,
            datapoint_key=datapoint_key,
            status=verification.status,
            value=extraction.value,
            evidence_chunk_ids=json.dumps(
                extraction.evidence_chunk_ids,
                sort_keys=True,
                separators=(",", ":"),
            ),
            rationale=verification.rationale,
            model_name=extraction_client.model_name,
            prompt_hash=prompt_hash,
            retrieval_params=retrieval_params_json,
        )
        db.add(assessment)
        created.append(assessment)
        retrieval_trace_entries.append(
            {
                "datapoint_key": datapoint_key,
                "query": query,
                "selected_chunk_ids": sorted(extraction.evidence_chunk_ids),
                "candidates": [
                    {
                        "rank": idx,
                        "chunk_id": item.chunk_id,
                        "document_id": item.document_id,
                        "page_number": item.page_number,
                        "start_offset": item.start_offset,
                        "end_offset": item.end_offset,
                        "lexical_score": item.lexical_score,
                        "vector_score": item.vector_score,
                        "combined_score": item.combined_score,
                    }
                    for idx, item in enumerate(retrieval_results, start=1)
                ],
            }
        )

    db.commit()
    persist_retrieval_trace_for_run(
        db,
        run_id=run.id,
        tenant_id=run.tenant_id,
        retrieval_top_k=config.retrieval_top_k,
        retrieval_policy=retrieval_policy_payload,
        entries=sorted(retrieval_trace_entries, key=lambda item: str(item["datapoint_key"])),
    )
    append_run_event(
        db,
        run_id=run.id,
        tenant_id=run.tenant_id,
        event_type="assessment.pipeline.completed",
        payload={"tenant_id": run.tenant_id, "assessment_count": len(created)},
    )
    log_structured_event(
        "assessment.pipeline.completed",
        run_id=run.id,
        tenant_id=run.tenant_id,
        assessment_count=len(created),
    )
    db.commit()
    for item in created:
        db.refresh(item)
    return created

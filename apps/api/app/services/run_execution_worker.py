"""Asynchronous run execution worker with deterministic lifecycle semantics."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.regulatory.datapoint_generation import generate_registry_datapoints
from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import (
    Company,
    DatapointAssessment,
    RegulatoryBundle,
    Run,
    RunMateriality,
)
from apps.api.app.db.session import get_session_factory
from apps.api.app.services.assessment_pipeline import (
    AssessmentRunConfig,
    execute_assessment_pipeline,
)
from apps.api.app.services.audit import append_run_event, log_structured_event
from apps.api.app.services.company_documents import list_company_document_hashes
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.llm_provider import build_extraction_client_from_settings
from apps.api.app.services.regulatory_compiler import compile_company_regulatory_plan
from apps.api.app.services.regulatory_registry import compile_from_db
from apps.api.app.services.retrieval import get_retrieval_policy, retrieval_policy_to_dict
from apps.api.app.services.run_cache import RunHashInput, get_or_compute_cached_output
from apps.api.app.services.run_input_snapshot import persist_run_input_snapshot
from apps.api.app.services.run_manifest import RunManifestPayload, persist_run_manifest
from apps.api.app.services.run_registry_artifacts import persist_registry_outputs_for_run


@dataclass(frozen=True)
class RunExecutionPayload:
    bundle_id: str
    bundle_version: str
    retrieval_top_k: int
    retrieval_model_name: str
    llm_provider: str


class _DeterministicAbsentTransport:
    def create_response(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float,
        json_schema: dict,
    ):
        del model, input_text, temperature, json_schema
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                '{"status":"Absent","value":null,"evidence_chunk_ids":[],'  # noqa: E501
                                '"rationale":"Deterministic local execution fallback."}'
                            ),
                        }
                    ],
                }
            ]
        }


def _assessment_count(db: Session, *, run_id: int, tenant_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DatapointAssessment)
            .where(
                DatapointAssessment.run_id == run_id,
                DatapointAssessment.tenant_id == tenant_id,
            )
        )
        or 0
    )


def _classify_failure(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, TimeoutError | httpx.TimeoutException | httpx.ConnectError):
        return "provider_transient", True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code if exc.response is not None else 0
        if 500 <= status_code <= 599:
            return "provider_transient", True
        return "provider_request_invalid", False
    message = str(exc)
    if "openai_api_key is required" in message:
        return "config_error", False
    if "Bundle not found:" in message:
        return "bundle_not_found", False
    if "llm_schema_parse_error" in message:
        return "schema_parse_error", False
    if "llm_schema_validation_error" in message:
        return "schema_validation_error", False
    return "internal_error", False


def _process_run_execution(run_id: int, payload: RunExecutionPayload) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        run = db.get(Run, run_id)
        if run is None:
            return

        run.status = "running"
        append_run_event(
            db,
            run_id=run.id,
            tenant_id=run.tenant_id,
            event_type="run.execution.started",
            payload={
                "tenant_id": run.tenant_id,
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
            },
        )
        log_structured_event(
            "run.execution.started",
            run_id=run.id,
            tenant_id=run.tenant_id,
            bundle_id=payload.bundle_id,
            bundle_version=payload.bundle_version,
        )
        db.commit()

        try:
            settings = get_settings()
            extraction_client = (
                build_extraction_client_from_settings(settings, provider=payload.llm_provider)
                if payload.llm_provider in {"local_lm_studio", "openai_cloud"}
                else ExtractionClient(
                    transport=_DeterministicAbsentTransport(),
                    model="deterministic-local-v1",
                )
            )

            company = db.scalar(
                select(Company).where(
                    Company.id == run.company_id,
                    Company.tenant_id == run.tenant_id,
                )
            )
            if company is None:
                raise ValueError("company not found")

            materiality_rows = db.scalars(
                select(RunMateriality)
                .where(RunMateriality.run_id == run.id, RunMateriality.tenant_id == run.tenant_id)
                .order_by(RunMateriality.topic)
            ).all()
            materiality_inputs = {row.topic: row.is_material for row in materiality_rows}

            document_hashes = list_company_document_hashes(
                db, company_id=run.company_id, tenant_id=run.tenant_id
            )
            retrieval_policy = get_retrieval_policy()

            retrieval_params = {
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "compiler_mode": run.compiler_mode,
                "llm_provider": payload.llm_provider,
                "query_mode": "hybrid",
                "retrieval_model_name": payload.retrieval_model_name,
                "retrieval_policy": retrieval_policy_to_dict(retrieval_policy),
                "top_k": payload.retrieval_top_k,
            }
            registry_checksums: list[str] = []
            if settings.feature_registry_compiler and run.compiler_mode == "registry":
                registry_rows = db.scalars(
                    select(RegulatoryBundle.checksum)
                    .where(
                        RegulatoryBundle.bundle_id == payload.bundle_id,
                        RegulatoryBundle.version == payload.bundle_version,
                    )
                    .order_by(RegulatoryBundle.checksum)
                ).all()
                registry_checksums = sorted(set(registry_rows))
                retrieval_params["registry"] = {
                    "bundle_checksums": registry_checksums,
                    "mode": "registry",
                }
            prompt_seed = {
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "compiler_mode": run.compiler_mode,
                "llm_provider": payload.llm_provider,
                "model_name": extraction_client.model_name,
                "retrieval_params": retrieval_params,
            }
            prompt_hash = hashlib.sha256(
                json.dumps(prompt_seed, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            regulatory_plan_result = compile_company_regulatory_plan(
                db,
                company=company,
            )

            if settings.feature_registry_compiler and run.compiler_mode == "registry":
                compiled_for_snapshot = compile_from_db(
                    db,
                    bundle_id=payload.bundle_id,
                    version=payload.bundle_version,
                    context={
                        "company": {
                            "employees": company.employees,
                            "listed_status": company.listed_status,
                            "reporting_year": company.reporting_year,
                            "reporting_year_start": company.reporting_year_start,
                            "reporting_year_end": company.reporting_year_end,
                            "turnover": company.turnover,
                        }
                    },
                )
                required_datapoint_universe = sorted(
                    item.datapoint_key
                    for item in generate_registry_datapoints(compiled_for_snapshot)
                )
            else:
                required_datapoint_universe = resolve_required_datapoint_ids(
                    db,
                    company_id=run.company_id,
                    bundle_id=payload.bundle_id,
                    bundle_version=payload.bundle_version,
                    run_id=run.id,
                )
            persist_run_input_snapshot(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                payload={
                    "run_id": run.id,
                    "tenant_id": run.tenant_id,
                    "company_id": run.company_id,
                    "company_profile": {
                        "employees": company.employees,
                        "listed_status": company.listed_status,
                        "reporting_year": company.reporting_year,
                        "reporting_year_start": company.reporting_year_start,
                        "reporting_year_end": company.reporting_year_end,
                        "turnover": company.turnover,
                    },
                    "materiality_inputs": materiality_inputs,
                    "bundle_id": payload.bundle_id,
                    "bundle_version": payload.bundle_version,
                    "compiler_mode": run.compiler_mode,
                    "retrieval": retrieval_params,
                    "required_datapoint_universe": required_datapoint_universe,
                },
            )

            computed_assessments: list[DatapointAssessment] | None = None

            def _compute_assessments():
                nonlocal computed_assessments
                computed_assessments = execute_assessment_pipeline(
                    db,
                    extraction_client=extraction_client,
                    config=AssessmentRunConfig(
                        run_id=run.id,
                        bundle_id=payload.bundle_id,
                        bundle_version=payload.bundle_version,
                        retrieval_top_k=payload.retrieval_top_k,
                        retrieval_model_name=payload.retrieval_model_name,
                    ),
                )
                return computed_assessments

            output_json, cache_hit = get_or_compute_cached_output(
                db,
                run_id=run.id,
                hash_input=RunHashInput(
                    tenant_id=run.tenant_id,
                    document_hashes=document_hashes,
                    company_profile={
                        "employees": company.employees,
                        "listed_status": company.listed_status,
                        "reporting_year": company.reporting_year,
                        "reporting_year_start": company.reporting_year_start,
                        "reporting_year_end": company.reporting_year_end,
                        "turnover": company.turnover,
                    },
                    materiality_inputs=materiality_inputs,
                    bundle_version=payload.bundle_version,
                    retrieval_params=retrieval_params,
                    prompt_hash=prompt_hash,
                    compiler_mode=run.compiler_mode,
                    registry_checksums=registry_checksums,
                ),
                compute_assessments=_compute_assessments,
            )
            assessment_count = len(json.loads(output_json))

            persist_run_manifest(
                db,
                payload=RunManifestPayload(
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    company_id=run.company_id,
                    bundle_id=payload.bundle_id,
                    bundle_version=payload.bundle_version,
                    retrieval_params=retrieval_params,
                    model_name=extraction_client.model_name,
                    prompt_hash=prompt_hash,
                    regulatory_registry_version={
                        "selected_bundles": regulatory_plan_result.plan["selected_bundles"]
                    },
                    regulatory_compiler_version=regulatory_plan_result.plan["compiler_version"],
                    regulatory_plan_json=regulatory_plan_result.plan,
                    regulatory_plan_hash=regulatory_plan_result.plan_hash,
                    git_sha=settings.git_sha,
                ),
                assessments=computed_assessments or [],
            )
            if settings.feature_registry_compiler and run.compiler_mode == "registry":
                compiled_plan = compile_from_db(
                    db,
                    bundle_id=payload.bundle_id,
                    version=payload.bundle_version,
                    context={
                        "company": {
                            "employees": company.employees,
                            "listed_status": company.listed_status,
                            "reporting_year": company.reporting_year,
                            "reporting_year_start": company.reporting_year_start,
                            "reporting_year_end": company.reporting_year_end,
                            "turnover": company.turnover,
                        }
                    },
                )
                run_assessments = computed_assessments
                if run_assessments is None:
                    run_assessments = db.scalars(
                        select(DatapointAssessment)
                        .where(
                            DatapointAssessment.run_id == run.id,
                            DatapointAssessment.tenant_id == run.tenant_id,
                        )
                        .order_by(DatapointAssessment.datapoint_key)
                    ).all()
                persist_registry_outputs_for_run(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    compiled_plan=compiled_plan,
                    assessments=run_assessments,
                )
            run.status = "completed"
            append_run_event(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                event_type="run.execution.completed",
                payload={
                    "tenant_id": run.tenant_id,
                    "assessment_count": assessment_count,
                    "cache_hit": cache_hit,
                },
            )
            log_structured_event(
                "run.execution.completed",
                run_id=run.id,
                tenant_id=run.tenant_id,
                assessment_count=assessment_count,
                cache_hit=cache_hit,
            )
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive worker path
            failure_category, retryable = _classify_failure(exc)
            run.status = "failed"
            append_run_event(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                event_type="run.execution.failed",
                payload={
                    "tenant_id": run.tenant_id,
                    "error": str(exc),
                    "failure_category": failure_category,
                    "retryable": retryable,
                },
            )
            log_structured_event(
                "run.execution.failed",
                run_id=run.id,
                tenant_id=run.tenant_id,
                error=str(exc),
                failure_category=failure_category,
                retryable=retryable,
            )
            db.commit()


def enqueue_run_execution(run_id: int, payload: RunExecutionPayload) -> None:
    thread = threading.Thread(
        target=_process_run_execution,
        args=(run_id, payload),
        daemon=True,
        name=f"run-exec-{run_id}",
    )
    thread.start()


def current_assessment_count(db: Session, *, run_id: int, tenant_id: str) -> int:
    return _assessment_count(db, run_id=run_id, tenant_id=tenant_id)

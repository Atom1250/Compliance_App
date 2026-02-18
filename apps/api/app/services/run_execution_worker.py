"""Asynchronous run execution worker with deterministic lifecycle semantics."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.core.config import get_settings
from apps.api.app.db.models import (
    Company,
    DatapointAssessment,
    Document,
    DocumentFile,
    Run,
    RunMateriality,
)
from apps.api.app.db.session import get_session_factory
from apps.api.app.services.assessment_pipeline import (
    AssessmentRunConfig,
    execute_assessment_pipeline,
)
from apps.api.app.services.audit import append_run_event, log_structured_event
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.llm_provider import build_extraction_client_from_settings
from apps.api.app.services.run_cache import RunHashInput, get_or_compute_cached_output
from apps.api.app.services.run_manifest import RunManifestPayload, persist_run_manifest


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


def _assessment_count(db: Session, *, run_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DatapointAssessment)
            .where(DatapointAssessment.run_id == run_id)
        )
        or 0
    )


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
                build_extraction_client_from_settings(settings)
                if payload.llm_provider == "local_lm_studio"
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
                .where(RunMateriality.run_id == run.id)
                .order_by(RunMateriality.topic)
            ).all()
            materiality_inputs = {row.topic: row.is_material for row in materiality_rows}

            document_hashes = db.scalars(
                select(DocumentFile.sha256_hash)
                .join(Document, Document.id == DocumentFile.document_id)
                .where(Document.company_id == run.company_id, Document.tenant_id == run.tenant_id)
                .order_by(DocumentFile.sha256_hash)
            ).all()
            document_hashes = sorted(set(document_hashes))

            retrieval_params = {
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "llm_provider": payload.llm_provider,
                "query_mode": "hybrid",
                "retrieval_model_name": payload.retrieval_model_name,
                "top_k": payload.retrieval_top_k,
            }
            prompt_seed = {
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "llm_provider": payload.llm_provider,
                "model_name": extraction_client.model_name,
                "retrieval_params": retrieval_params,
            }
            prompt_hash = hashlib.sha256(
                json.dumps(prompt_seed, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()

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
                    document_hashes=document_hashes,
                    company_profile={
                        "employees": company.employees,
                        "listed_status": company.listed_status,
                        "reporting_year": company.reporting_year,
                        "turnover": company.turnover,
                    },
                    materiality_inputs=materiality_inputs,
                    bundle_version=payload.bundle_version,
                    retrieval_params=retrieval_params,
                    prompt_hash=prompt_hash,
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
                    git_sha=settings.git_sha,
                ),
                assessments=computed_assessments or [],
            )
            run.status = "completed"
            append_run_event(
                db,
                run_id=run.id,
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
            run.status = "failed"
            append_run_event(
                db,
                run_id=run.id,
                event_type="run.execution.failed",
                payload={"tenant_id": run.tenant_id, "error": str(exc)},
            )
            log_structured_event(
                "run.execution.failed",
                run_id=run.id,
                tenant_id=run.tenant_id,
                error=str(exc),
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


def current_assessment_count(db: Session, *, run_id: int) -> int:
    return _assessment_count(db, run_id=run_id)

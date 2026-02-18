"""Materiality questionnaire endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import Company, Run, RunManifest, RunMateriality
from apps.api.app.db.session import get_db_session
from apps.api.app.services.assessment_pipeline import (
    AssessmentRunConfig,
    execute_assessment_pipeline,
)
from apps.api.app.services.audit import append_run_event, list_run_events, log_structured_event
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.llm_provider import build_extraction_client_from_settings
from apps.api.app.services.run_manifest import RunManifestPayload, persist_run_manifest

router = APIRouter(prefix="/runs", tags=["materiality"])


class MaterialityEntry(BaseModel):
    topic: str = Field(min_length=1)
    is_material: bool


class MaterialityUpsertRequest(BaseModel):
    entries: list[MaterialityEntry]


class MaterialityUpsertResponse(BaseModel):
    run_id: int
    entries: list[MaterialityEntry]


class RequiredDatapointsRequest(BaseModel):
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)


class RequiredDatapointsResponse(BaseModel):
    run_id: int
    required_datapoint_ids: list[str]


class RunEventItem(BaseModel):
    event_type: str
    payload: dict[str, object]
    created_at: str


class RunEventsResponse(BaseModel):
    run_id: int
    events: list[RunEventItem]


class RunCreateRequest(BaseModel):
    company_id: int = Field(ge=1)


class RunCreateResponse(BaseModel):
    run_id: int
    status: str


class RunStatusResponse(BaseModel):
    run_id: int
    status: str


class RunReportResponse(BaseModel):
    run_id: int
    url: str


class RunManifestResponse(BaseModel):
    run_id: int
    document_hashes: list[str]
    bundle_id: str
    bundle_version: str
    retrieval_params: dict[str, object]
    model_name: str
    prompt_hash: str
    git_sha: str


class RunExecuteRequest(BaseModel):
    bundle_id: str = Field(min_length=1)
    bundle_version: str = Field(min_length=1)
    retrieval_top_k: int = Field(default=5, ge=1, le=100)
    retrieval_model_name: str = Field(default="default", min_length=1)
    llm_provider: str = Field(default="deterministic_fallback", min_length=1)


class RunExecuteResponse(BaseModel):
    run_id: int
    status: str
    assessment_count: int


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


@router.post("", response_model=RunCreateResponse)
def create_run(
    payload: RunCreateRequest,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RunCreateResponse:
    company = db.scalar(
        select(Company).where(Company.id == payload.company_id, Company.tenant_id == auth.tenant_id)
    )
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")

    run = Run(company_id=company.id, tenant_id=auth.tenant_id, status="queued")
    db.add(run)
    db.flush()
    append_run_event(
        db,
        run_id=run.id,
        event_type="run.created",
        payload={"tenant_id": auth.tenant_id, "company_id": company.id, "status": run.status},
    )
    log_structured_event(
        "run.created",
        run_id=run.id,
        tenant_id=auth.tenant_id,
        company_id=company.id,
        status=run.status,
    )
    db.commit()
    db.refresh(run)
    return RunCreateResponse(run_id=run.id, status=run.status)


@router.get("/{run_id}/status", response_model=RunStatusResponse)
def run_status(
    run_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RunStatusResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    append_run_event(
        db,
        run_id=run.id,
        event_type="run.status.requested",
        payload={"tenant_id": auth.tenant_id, "status": run.status},
    )
    log_structured_event(
        "run.status.requested",
        run_id=run.id,
        tenant_id=auth.tenant_id,
        status=run.status,
    )
    db.commit()
    return RunStatusResponse(run_id=run.id, status=run.status)


@router.get("/{run_id}/report", response_model=RunReportResponse)
def run_report(
    run_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RunReportResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    url = f"/reports/run-{run.id}.html"
    append_run_event(
        db,
        run_id=run.id,
        event_type="run.report.requested",
        payload={"tenant_id": auth.tenant_id, "url": url},
    )
    log_structured_event(
        "run.report.requested",
        run_id=run.id,
        tenant_id=auth.tenant_id,
        url=url,
    )
    db.commit()
    return RunReportResponse(run_id=run.id, url=url)


@router.get("/{run_id}/manifest", response_model=RunManifestResponse)
def run_manifest(
    run_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RunManifestResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    manifest = db.scalar(select(RunManifest).where(RunManifest.run_id == run.id))
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="manifest not found")

    return RunManifestResponse(
        run_id=run.id,
        document_hashes=json.loads(manifest.document_hashes),
        bundle_id=manifest.bundle_id,
        bundle_version=manifest.bundle_version,
        retrieval_params=json.loads(manifest.retrieval_params),
        model_name=manifest.model_name,
        prompt_hash=manifest.prompt_hash,
        git_sha=manifest.git_sha,
    )


@router.post("/{run_id}/execute", response_model=RunExecuteResponse)
def execute_run(
    run_id: int,
    payload: RunExecuteRequest,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RunExecuteResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    run.status = "running"
    append_run_event(
        db,
        run_id=run.id,
        event_type="run.execution.started",
        payload={
            "tenant_id": auth.tenant_id,
            "bundle_id": payload.bundle_id,
            "bundle_version": payload.bundle_version,
        },
    )
    log_structured_event(
        "run.execution.started",
        run_id=run.id,
        tenant_id=auth.tenant_id,
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
        assessments = execute_assessment_pipeline(
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
        persist_run_manifest(
            db,
            payload=RunManifestPayload(
                run_id=run.id,
                tenant_id=run.tenant_id,
                company_id=run.company_id,
                bundle_id=payload.bundle_id,
                bundle_version=payload.bundle_version,
                retrieval_params={
                    "top_k": payload.retrieval_top_k,
                    "retrieval_model_name": payload.retrieval_model_name,
                    "query_mode": "hybrid",
                },
                model_name=extraction_client.model_name,
                git_sha=settings.git_sha,
            ),
            assessments=assessments,
        )
        run.status = "completed"
        append_run_event(
            db,
            run_id=run.id,
            event_type="run.execution.completed",
            payload={"tenant_id": auth.tenant_id, "assessment_count": len(assessments)},
        )
        log_structured_event(
            "run.execution.completed",
            run_id=run.id,
            tenant_id=auth.tenant_id,
            assessment_count=len(assessments),
        )
        db.commit()
        return RunExecuteResponse(
            run_id=run.id,
            status=run.status,
            assessment_count=len(assessments),
        )
    except Exception as exc:  # pragma: no cover - defensive run-state update
        run.status = "failed"
        append_run_event(
            db,
            run_id=run.id,
            event_type="run.execution.failed",
            payload={"tenant_id": auth.tenant_id, "error": str(exc)},
        )
        log_structured_event(
            "run.execution.failed",
            run_id=run.id,
            tenant_id=auth.tenant_id,
            error=str(exc),
        )
        db.commit()
        raise


@router.post("/{run_id}/materiality", response_model=MaterialityUpsertResponse)
def upsert_materiality(
    run_id: int,
    payload: MaterialityUpsertRequest,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> MaterialityUpsertResponse:
    """Store topic-level materiality decisions for a run."""
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    existing_rows = db.scalars(select(RunMateriality).where(RunMateriality.run_id == run_id)).all()
    by_topic = {row.topic: row for row in existing_rows}

    for entry in sorted(payload.entries, key=lambda item: item.topic):
        existing = by_topic.get(entry.topic)
        if existing is None:
            db.add(RunMateriality(run_id=run_id, topic=entry.topic, is_material=entry.is_material))
        else:
            existing.is_material = entry.is_material

    append_run_event(
        db,
        run_id=run_id,
        event_type="materiality.updated",
        payload={
            "tenant_id": auth.tenant_id,
            "topics": [
                entry.topic for entry in sorted(payload.entries, key=lambda item: item.topic)
            ],
        },
    )
    log_structured_event(
        "materiality.updated",
        run_id=run_id,
        tenant_id=auth.tenant_id,
        topic_count=len(payload.entries),
    )

    db.commit()

    refreshed = db.scalars(
        select(RunMateriality).where(RunMateriality.run_id == run_id).order_by(RunMateriality.topic)
    ).all()

    return MaterialityUpsertResponse(
        run_id=run_id,
        entries=[
            MaterialityEntry(topic=row.topic, is_material=row.is_material) for row in refreshed
        ],
    )


@router.post("/{run_id}/required-datapoints", response_model=RequiredDatapointsResponse)
def required_datapoints_for_run(
    run_id: int,
    payload: RequiredDatapointsRequest,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RequiredDatapointsResponse:
    """Resolve required datapoints with materiality integration."""
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    required = resolve_required_datapoint_ids(
        db,
        company_id=run.company_id,
        bundle_id=payload.bundle_id,
        bundle_version=payload.bundle_version,
        run_id=run.id,
    )
    append_run_event(
        db,
        run_id=run_id,
        event_type="required_datapoints.resolved",
        payload={
            "tenant_id": auth.tenant_id,
            "bundle_id": payload.bundle_id,
            "bundle_version": payload.bundle_version,
            "required_count": len(required),
        },
    )
    log_structured_event(
        "required_datapoints.resolved",
        run_id=run_id,
        tenant_id=auth.tenant_id,
        required_count=len(required),
    )
    db.commit()

    return RequiredDatapointsResponse(run_id=run.id, required_datapoint_ids=required)


@router.get("/{run_id}/events", response_model=RunEventsResponse)
def run_events(
    run_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RunEventsResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    events = list_run_events(db, run_id=run_id)
    return RunEventsResponse(
        run_id=run_id,
        events=[
            RunEventItem(
                event_type=event.event_type,
                payload=json.loads(event.payload),
                created_at=event.created_at.isoformat(),
            )
            for event in events
        ],
    )

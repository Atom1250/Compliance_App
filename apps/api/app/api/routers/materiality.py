"""Materiality questionnaire endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import (
    Company,
    Run,
    RunEvent,
    RunManifest,
    RunMateriality,
)
from apps.api.app.db.session import get_db_session
from apps.api.app.services.audit import append_run_event, list_run_events, log_structured_event
from apps.api.app.services.evidence_pack import export_evidence_pack
from apps.api.app.services.run_execution_worker import (
    RunExecutionPayload,
    current_assessment_count,
    enqueue_run_execution,
)

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
    retry_failed: bool = False


class RunExecuteResponse(BaseModel):
    run_id: int
    status: str
    assessment_count: int


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


@router.get("/{run_id}/evidence-pack")
def run_evidence_pack(
    run_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> FileResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    if run.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="evidence pack available only for completed runs",
        )

    settings = get_settings()
    tenant_dir = Path(settings.evidence_pack_output_root) / auth.tenant_id
    output_zip = tenant_dir / f"run-{run.id}-evidence-pack.zip"
    export_evidence_pack(db, run_id=run.id, output_zip_path=output_zip)
    return FileResponse(
        path=output_zip,
        media_type="application/zip",
        filename=f"run-{run.id}-evidence-pack.zip",
    )


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
    assessment_count = current_assessment_count(db, run_id=run.id)
    latest_execution_event = db.scalar(
        select(RunEvent.event_type)
        .where(
            RunEvent.run_id == run.id,
            RunEvent.event_type.in_(
                [
                    "run.execution.queued",
                    "run.execution.started",
                    "run.execution.completed",
                    "run.execution.failed",
                ]
            ),
        )
        .order_by(RunEvent.id.desc())
        .limit(1)
    )
    if run.status == "completed":
        return RunExecuteResponse(
            run_id=run.id,
            status=run.status,
            assessment_count=assessment_count,
        )
    if run.status == "running":
        return RunExecuteResponse(
            run_id=run.id,
            status=run.status,
            assessment_count=assessment_count,
        )
    if run.status == "queued" and latest_execution_event in {
        "run.execution.queued",
        "run.execution.started",
    }:
        return RunExecuteResponse(
            run_id=run.id,
            status=run.status,
            assessment_count=assessment_count,
        )
    if run.status == "failed" and not payload.retry_failed:
        return RunExecuteResponse(
            run_id=run.id,
            status=run.status,
            assessment_count=assessment_count,
        )

    run.status = "queued"
    append_run_event(
        db,
        run_id=run.id,
        event_type="run.execution.queued",
        payload={
            "tenant_id": auth.tenant_id,
            "bundle_id": payload.bundle_id,
            "bundle_version": payload.bundle_version,
            "retry_failed": payload.retry_failed,
        },
    )
    log_structured_event(
        "run.execution.queued",
        run_id=run.id,
        tenant_id=auth.tenant_id,
        bundle_id=payload.bundle_id,
        bundle_version=payload.bundle_version,
        retry_failed=payload.retry_failed,
    )
    db.commit()

    enqueue_run_execution(
        run.id,
        RunExecutionPayload(
            bundle_id=payload.bundle_id,
            bundle_version=payload.bundle_version,
            retrieval_top_k=payload.retrieval_top_k,
            retrieval_model_name=payload.retrieval_model_name,
            llm_provider=payload.llm_provider,
        ),
    )

    return RunExecuteResponse(run_id=run.id, status=run.status, assessment_count=assessment_count)


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

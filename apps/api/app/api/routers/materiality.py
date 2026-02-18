"""Materiality questionnaire endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.db.models import Run, RunMateriality
from apps.api.app.db.session import get_db_session

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

    return RequiredDatapointsResponse(run_id=run.id, required_datapoint_ids=required)

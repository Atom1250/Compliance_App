"""Read-only regulatory context endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.auth import AuthContext, require_auth_context
from apps.api.app.db.models import RegulatoryBundle, RegulatorySourceDocument, Run, RunManifest
from apps.api.app.db.session import get_db_session

router = APIRouter(prefix="/regulatory", tags=["regulatory"])


class RegulatorySourceItem(BaseModel):
    record_id: str
    jurisdiction: str
    document_name: str
    framework_level: str | None
    legal_reference: str | None
    official_source_url: str | None
    status: str | None


class RegulatoryBundleItem(BaseModel):
    regime: str
    bundle_id: str
    version: str
    checksum: str
    status: str


class RegulatoryPlanResponse(BaseModel):
    run_id: int
    compiler_version: str | None
    plan_hash: str | None
    plan: dict[str, object] | None


@router.get("/sources", response_model=list[RegulatorySourceItem])
def list_sources(
    jurisdiction: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> list[RegulatorySourceItem]:
    query = select(RegulatorySourceDocument)
    if jurisdiction:
        query = query.where(RegulatorySourceDocument.jurisdiction == jurisdiction)
    rows = db.scalars(
        query.order_by(RegulatorySourceDocument.jurisdiction, RegulatorySourceDocument.record_id)
    ).all()
    return [
        RegulatorySourceItem(
            record_id=row.record_id,
            jurisdiction=row.jurisdiction,
            document_name=row.document_name,
            framework_level=row.framework_level,
            legal_reference=row.legal_reference,
            official_source_url=row.official_source_url,
            status=row.status,
        )
        for row in rows
    ]


@router.get("/bundles", response_model=list[RegulatoryBundleItem])
def list_bundles(
    regime: str | None = Query(default=None),
    _auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> list[RegulatoryBundleItem]:
    query = select(RegulatoryBundle)
    if regime:
        query = query.where(RegulatoryBundle.regime == regime)
    rows = db.scalars(
        query.order_by(
            RegulatoryBundle.regime,
            RegulatoryBundle.bundle_id,
            RegulatoryBundle.version,
        )
    ).all()
    return [
        RegulatoryBundleItem(
            regime=row.regime,
            bundle_id=row.bundle_id,
            version=row.version,
            checksum=row.checksum,
            status=row.status,
        )
        for row in rows
    ]


@router.get("/runs/{run_id}/regulatory-plan", response_model=RegulatoryPlanResponse)
def run_regulatory_plan(
    run_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db_session),
) -> RegulatoryPlanResponse:
    run = db.scalar(select(Run).where(Run.id == run_id, Run.tenant_id == auth.tenant_id))
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    manifest = db.scalar(
        select(RunManifest).where(
            RunManifest.run_id == run_id,
            RunManifest.tenant_id == auth.tenant_id,
        )
    )
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="manifest not found")
    plan = json.loads(manifest.regulatory_plan_json) if manifest.regulatory_plan_json else None
    return RegulatoryPlanResponse(
        run_id=run_id,
        compiler_version=manifest.regulatory_compiler_version,
        plan_hash=manifest.regulatory_plan_hash,
        plan=plan,
    )

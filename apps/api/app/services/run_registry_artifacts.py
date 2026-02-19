"""Persist and load run-scoped registry artifacts deterministically."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.regulatory.canonical import sha256_checksum
from app.regulatory.compiler import CompiledRegulatoryPlan
from apps.api.app.db.models import RunRegistryArtifact
from apps.api.app.services.reporting import compute_registry_coverage_matrix

COMPILED_PLAN_ARTIFACT_KEY = "compiled_plan"
COVERAGE_MATRIX_ARTIFACT_KEY = "coverage_matrix"
RETRIEVAL_TRACE_ARTIFACT_KEY = "retrieval_trace"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def upsert_run_registry_artifact(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
    artifact_key: str,
    payload: Any,
) -> RunRegistryArtifact:
    content_json = _canonical_json(payload)
    checksum = sha256_checksum(payload)
    existing = db.scalar(
        select(RunRegistryArtifact).where(
            RunRegistryArtifact.run_id == run_id,
            RunRegistryArtifact.tenant_id == tenant_id,
            RunRegistryArtifact.artifact_key == artifact_key,
        )
    )
    if existing is None:
        row = RunRegistryArtifact(
            run_id=run_id,
            tenant_id=tenant_id,
            artifact_key=artifact_key,
            content_json=content_json,
            checksum=checksum,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    existing.content_json = content_json
    existing.checksum = checksum
    db.commit()
    db.refresh(existing)
    return existing


def persist_registry_outputs_for_run(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
    compiled_plan: CompiledRegulatoryPlan,
    assessments: list[Any],
) -> list[RunRegistryArtifact]:
    compiled_payload = compiled_plan.model_dump(mode="json")
    compiled_payload["checksum"] = sha256_checksum(compiled_payload)
    matrix_payload = [
        {
            "obligation_id": row.obligation_id,
            "total_elements": row.total_elements,
            "present": row.present,
            "partial": row.partial,
            "absent": row.absent,
            "na": row.na,
            "coverage_pct": row.coverage_pct,
            "status": row.status,
        }
        for row in compute_registry_coverage_matrix(assessments)
    ]
    plan_row = upsert_run_registry_artifact(
        db,
        run_id=run_id,
        tenant_id=tenant_id,
        artifact_key=COMPILED_PLAN_ARTIFACT_KEY,
        payload=compiled_payload,
    )
    matrix_row = upsert_run_registry_artifact(
        db,
        run_id=run_id,
        tenant_id=tenant_id,
        artifact_key=COVERAGE_MATRIX_ARTIFACT_KEY,
        payload=matrix_payload,
    )
    return [plan_row, matrix_row]


def load_run_registry_artifacts(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
) -> dict[str, bytes]:
    rows = db.scalars(
        select(RunRegistryArtifact)
        .where(
            RunRegistryArtifact.run_id == run_id,
            RunRegistryArtifact.tenant_id == tenant_id,
            RunRegistryArtifact.artifact_key.in_(
                [COMPILED_PLAN_ARTIFACT_KEY, COVERAGE_MATRIX_ARTIFACT_KEY]
            ),
        )
        .order_by(RunRegistryArtifact.artifact_key)
    ).all()
    mapping: dict[str, bytes] = {}
    for row in rows:
        if row.artifact_key == COMPILED_PLAN_ARTIFACT_KEY:
            mapping["registry/compiled_plan.json"] = row.content_json.encode()
        elif row.artifact_key == COVERAGE_MATRIX_ARTIFACT_KEY:
            mapping["registry/coverage_matrix.json"] = row.content_json.encode()
    return mapping


def persist_retrieval_trace_for_run(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
    retrieval_top_k: int,
    retrieval_policy: dict[str, Any],
    entries: list[dict[str, Any]],
) -> RunRegistryArtifact:
    payload = {
        "run_id": run_id,
        "retrieval_top_k": retrieval_top_k,
        "retrieval_policy": retrieval_policy,
        "entries": entries,
    }
    return upsert_run_registry_artifact(
        db,
        run_id=run_id,
        tenant_id=tenant_id,
        artifact_key=RETRIEVAL_TRACE_ARTIFACT_KEY,
        payload=payload,
    )

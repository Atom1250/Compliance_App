"""Run manifest persistence and deterministic serialization helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import DatapointAssessment, Document, DocumentFile, RunManifest


@dataclass(frozen=True)
class RunManifestPayload:
    run_id: int
    tenant_id: str
    company_id: int
    bundle_id: str
    bundle_version: str
    retrieval_params: dict[str, Any]
    model_name: str
    prompt_hash: str
    git_sha: str


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _aggregate_prompt_hash(assessments: list[DatapointAssessment]) -> str:
    prompt_hashes = sorted({item.prompt_hash for item in assessments})
    if len(prompt_hashes) == 1:
        return prompt_hashes[0]
    return hashlib.sha256(_canonical_json(prompt_hashes).encode()).hexdigest()


def _document_hashes_for_company(
    db: Session,
    *,
    tenant_id: str,
    company_id: int,
) -> list[str]:
    rows = db.scalars(
        select(DocumentFile.sha256_hash)
        .join(Document, Document.id == DocumentFile.document_id)
        .where(Document.tenant_id == tenant_id, Document.company_id == company_id)
        .order_by(DocumentFile.sha256_hash)
    ).all()
    return sorted(set(rows))


def persist_run_manifest(
    db: Session,
    *,
    payload: RunManifestPayload,
    assessments: list[DatapointAssessment],
) -> RunManifest:
    document_hashes = _document_hashes_for_company(
        db, tenant_id=payload.tenant_id, company_id=payload.company_id
    )
    prompt_hash = payload.prompt_hash
    if assessments:
        prompt_hash = _aggregate_prompt_hash(assessments)
    retrieval_params_json = _canonical_json(payload.retrieval_params)
    document_hashes_json = _canonical_json(document_hashes)

    existing = db.scalar(select(RunManifest).where(RunManifest.run_id == payload.run_id))
    if existing is None:
        manifest = RunManifest(
            run_id=payload.run_id,
            document_hashes=document_hashes_json,
            bundle_id=payload.bundle_id,
            bundle_version=payload.bundle_version,
            retrieval_params=retrieval_params_json,
            model_name=payload.model_name,
            prompt_hash=prompt_hash,
            git_sha=payload.git_sha,
        )
        db.add(manifest)
        db.commit()
        db.refresh(manifest)
        return manifest

    existing.document_hashes = document_hashes_json
    existing.bundle_id = payload.bundle_id
    existing.bundle_version = payload.bundle_version
    existing.retrieval_params = retrieval_params_json
    existing.model_name = payload.model_name
    existing.prompt_hash = prompt_hash
    existing.git_sha = payload.git_sha
    db.commit()
    db.refresh(existing)
    return existing

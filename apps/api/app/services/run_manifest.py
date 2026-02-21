"""Run manifest persistence and deterministic serialization helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import DatapointAssessment, RunManifest
from apps.api.app.services.company_documents import list_company_document_hashes
from apps.api.app.services.reporting import REPORT_TEMPLATE_VERSION


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
    regulatory_plan_id: int | None = None
    regulatory_registry_version: dict[str, Any] | None = None
    regulatory_compiler_version: str | None = None
    regulatory_plan_json: dict[str, Any] | None = None
    regulatory_plan_hash: str | None = None
    report_template_version: str = REPORT_TEMPLATE_VERSION


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
    return list_company_document_hashes(db, company_id=company_id, tenant_id=tenant_id)


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
    regulatory_registry_version_json = (
        _canonical_json(payload.regulatory_registry_version)
        if payload.regulatory_registry_version is not None
        else None
    )
    regulatory_plan_json = (
        _canonical_json(payload.regulatory_plan_json)
        if payload.regulatory_plan_json is not None
        else None
    )

    existing = db.scalar(
        select(RunManifest).where(
            RunManifest.run_id == payload.run_id, RunManifest.tenant_id == payload.tenant_id
        )
    )
    if existing is None:
        manifest = RunManifest(
            run_id=payload.run_id,
            regulatory_plan_id=payload.regulatory_plan_id,
            tenant_id=payload.tenant_id,
            document_hashes=document_hashes_json,
            bundle_id=payload.bundle_id,
            bundle_version=payload.bundle_version,
            retrieval_params=retrieval_params_json,
            model_name=payload.model_name,
            prompt_hash=prompt_hash,
            regulatory_registry_version=regulatory_registry_version_json,
            regulatory_compiler_version=payload.regulatory_compiler_version,
            regulatory_plan_json=regulatory_plan_json,
            regulatory_plan_hash=payload.regulatory_plan_hash,
            report_template_version=payload.report_template_version,
            git_sha=payload.git_sha,
        )
        db.add(manifest)
        db.commit()
        db.refresh(manifest)
        return manifest

    existing.document_hashes = document_hashes_json
    existing.regulatory_plan_id = payload.regulatory_plan_id
    existing.bundle_id = payload.bundle_id
    existing.bundle_version = payload.bundle_version
    existing.retrieval_params = retrieval_params_json
    existing.model_name = payload.model_name
    existing.prompt_hash = prompt_hash
    existing.regulatory_registry_version = regulatory_registry_version_json
    existing.regulatory_compiler_version = payload.regulatory_compiler_version
    existing.regulatory_plan_json = regulatory_plan_json
    existing.regulatory_plan_hash = payload.regulatory_plan_hash
    existing.report_template_version = payload.report_template_version
    existing.git_sha = payload.git_sha
    db.commit()
    db.refresh(existing)
    return existing

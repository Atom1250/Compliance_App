"""Deterministic run hashing and cache lookup/store utilities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import DatapointAssessment, RunCacheEntry


@dataclass(frozen=True)
class RunHashInput:
    tenant_id: str
    document_hashes: list[str]
    company_profile: dict[str, Any]
    materiality_inputs: dict[str, bool]
    bundle_version: str
    retrieval_params: dict[str, Any]
    prompt_hash: str
    compiler_mode: str = "legacy"
    registry_checksums: list[str] = field(default_factory=list)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_run_hash(inputs: RunHashInput) -> str:
    payload = {
        "tenant_id": inputs.tenant_id,
        "document_hashes": sorted(inputs.document_hashes),
        "company_profile": inputs.company_profile,
        "materiality_inputs": inputs.materiality_inputs,
        "bundle_version": inputs.bundle_version,
        "retrieval_params": inputs.retrieval_params,
        "prompt_hash": inputs.prompt_hash,
        "compiler_mode": inputs.compiler_mode,
        "registry_checksums": sorted(inputs.registry_checksums),
    }
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode()).hexdigest()


def serialize_assessments(assessments: Sequence[DatapointAssessment]) -> str:
    rows = []
    for item in sorted(assessments, key=lambda row: row.datapoint_key):
        rows.append(
            {
                "datapoint_key": item.datapoint_key,
                "status": item.status,
                "value": item.value,
                "evidence_chunk_ids": sorted(json.loads(item.evidence_chunk_ids)),
                "rationale": item.rationale,
                "model_name": item.model_name,
                "prompt_hash": item.prompt_hash,
                "retrieval_params": json.loads(item.retrieval_params),
            }
        )
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))


def get_cached_output(db: Session, *, tenant_id: str, run_hash: str) -> str | None:
    entry = db.scalar(
        select(RunCacheEntry).where(
            RunCacheEntry.tenant_id == tenant_id,
            RunCacheEntry.run_hash == run_hash,
        )
    )
    if entry is None:
        return None
    return entry.output_json


def store_cached_output(
    db: Session, *, run_id: int, tenant_id: str, run_hash: str, output_json: str
) -> RunCacheEntry:
    existing = db.scalar(
        select(RunCacheEntry).where(
            RunCacheEntry.tenant_id == tenant_id,
            RunCacheEntry.run_hash == run_hash,
        )
    )
    if existing is not None:
        return existing

    entry = RunCacheEntry(
        run_id=run_id, tenant_id=tenant_id, run_hash=run_hash, output_json=output_json
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_or_compute_cached_output(
    db: Session,
    *,
    run_id: int,
    hash_input: RunHashInput,
    compute_assessments: Callable[[], Sequence[DatapointAssessment]],
) -> tuple[str, bool]:
    run_hash = compute_run_hash(hash_input)
    cached = get_cached_output(db, tenant_id=hash_input.tenant_id, run_hash=run_hash)
    if cached is not None:
        return cached, True

    assessments = compute_assessments()
    output_json = serialize_assessments(assessments)
    store_cached_output(
        db,
        run_id=run_id,
        tenant_id=hash_input.tenant_id,
        run_hash=run_hash,
        output_json=output_json,
    )
    return output_json, False

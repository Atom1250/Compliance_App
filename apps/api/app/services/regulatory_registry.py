"""Regulatory bundle registry storage service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.regulatory.canonical import sha256_checksum
from app.regulatory.compiler import CompiledRegulatoryPlan, compile_bundle
from app.regulatory.loader import load_bundle
from app.regulatory.schema import RegulatoryBundle as RegulatoryBundleSchema
from apps.api.app.db.models import RegulatoryBundle
from apps.api.app.services.audit import log_structured_event

SyncMode = Literal["merge", "sync"]


def get_bundle(
    db: Session,
    *,
    regime: str | None = None,
    bundle_id: str,
    version: str,
) -> RegulatoryBundle | None:
    """Fetch one stored regulatory bundle by ID and version."""
    query = select(RegulatoryBundle).where(
        RegulatoryBundle.bundle_id == bundle_id,
        RegulatoryBundle.version == version,
    )
    if regime is not None:
        query = query.where(RegulatoryBundle.regime == regime)
    return db.scalar(query)


def upsert_bundle(
    db: Session,
    *,
    bundle: RegulatoryBundleSchema,
    mode: SyncMode = "merge",
) -> RegulatoryBundle:
    """Idempotently store or update a regulatory bundle by bundle_id/version."""
    payload = bundle.model_dump(mode="json")
    checksum = sha256_checksum(payload)

    existing = get_bundle(
        db,
        regime=bundle.regime,
        bundle_id=bundle.bundle_id,
        version=bundle.version,
    )
    if existing is not None:
        if existing.checksum == checksum:
            return existing
        existing.jurisdiction = bundle.jurisdiction
        existing.regime = bundle.regime
        existing.checksum = checksum
        existing.payload = payload
        existing.source_record_ids = sorted(set(bundle.source_record_ids))
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        return existing

    created = RegulatoryBundle(
        bundle_id=bundle.bundle_id,
        version=bundle.version,
        jurisdiction=bundle.jurisdiction,
        regime=bundle.regime,
        checksum=checksum,
        payload=payload,
        source_record_ids=sorted(set(bundle.source_record_ids)),
        status="active",
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return created


def _iter_bundle_paths(bundles_root: Path) -> list[Path]:
    return sorted(path for path in bundles_root.rglob("*.json") if path.is_file())


def sync_from_filesystem(
    db: Session,
    *,
    bundles_root: Path,
    mode: SyncMode = "merge",
) -> list[tuple[str, str, str]]:
    """Deterministically sync bundle files from filesystem into the registry."""
    log_structured_event("regulatory.sync.started", bundles_root=str(bundles_root.resolve()))
    synced: list[tuple[str, str, str]] = []
    try:
        seen_triplets: set[tuple[str, str, str]] = set()
        for bundle_path in _iter_bundle_paths(bundles_root.resolve()):
            bundle, checksum, _ = load_bundle(bundle_path)
            upsert_bundle(db, bundle=bundle, mode=mode)
            synced.append((bundle.bundle_id, bundle.version, checksum))
            seen_triplets.add((bundle.regime, bundle.bundle_id, bundle.version))
        if mode == "sync":
            # Symmetric sync mode: deactivate bundles not present in source tree.
            rows = db.scalars(select(RegulatoryBundle)).all()
            changed = False
            for row in rows:
                key = (row.regime, row.bundle_id, row.version)
                if key in seen_triplets:
                    if row.status != "active":
                        row.status = "active"
                        changed = True
                    continue
                if row.status != "inactive":
                    row.status = "inactive"
                    changed = True
            if changed:
                db.commit()
        ordered = sorted(synced)
        log_structured_event(
            "regulatory.sync.completed",
            bundles_root=str(bundles_root.resolve()),
            synced_count=len(ordered),
            mode=mode,
        )
        return ordered
    except Exception as exc:
        log_structured_event(
            "regulatory.sync.failed",
            bundles_root=str(bundles_root.resolve()),
            error=str(exc),
        )
        raise


def compile_from_db(
    db: Session,
    *,
    bundle_id: str,
    version: str,
    context: dict[str, Any],
) -> CompiledRegulatoryPlan:
    """Load bundle payload from registry and compile deterministic plan."""
    log_structured_event(
        "regulatory.compile.started",
        bundle_id=bundle_id,
        bundle_version=version,
    )
    try:
        row = get_bundle(db, bundle_id=bundle_id, version=version)
        if row is None:
            raise ValueError(f"Bundle not found: {bundle_id}@{version}")
        bundle = RegulatoryBundleSchema.model_validate(row.payload)
        compiled = compile_bundle(bundle, context=context)
        log_structured_event(
            "regulatory.compile.completed",
            bundle_id=bundle_id,
            bundle_version=version,
            obligation_count=len(compiled.obligations),
        )
        return compiled
    except Exception as exc:
        log_structured_event(
            "regulatory.compile.failed",
            bundle_id=bundle_id,
            bundle_version=version,
            error=str(exc),
        )
        raise


def list_bundles(
    db: Session,
    *,
    regime: str | None = None,
) -> list[RegulatoryBundle]:
    query = select(RegulatoryBundle).where(RegulatoryBundle.status == "active")
    if regime:
        query = query.where(RegulatoryBundle.regime == regime)
    return db.scalars(
        query.order_by(
            RegulatoryBundle.regime,
            RegulatoryBundle.bundle_id,
            RegulatoryBundle.version,
        )
    ).all()

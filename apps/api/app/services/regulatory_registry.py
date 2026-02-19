"""Regulatory bundle registry storage service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.regulatory.canonical import sha256_checksum
from app.regulatory.compiler import CompiledRegulatoryPlan, compile_bundle
from app.regulatory.loader import load_bundle
from app.regulatory.schema import RegulatoryBundle as RegulatoryBundleSchema
from apps.api.app.db.models import RegulatoryBundle


def get_bundle(
    db: Session,
    *,
    bundle_id: str,
    version: str,
) -> RegulatoryBundle | None:
    """Fetch one stored regulatory bundle by ID and version."""
    return db.scalar(
        select(RegulatoryBundle).where(
            RegulatoryBundle.bundle_id == bundle_id,
            RegulatoryBundle.version == version,
        )
    )


def upsert_bundle(
    db: Session,
    *,
    bundle: RegulatoryBundleSchema,
) -> RegulatoryBundle:
    """Idempotently store or update a regulatory bundle by bundle_id/version."""
    payload = bundle.model_dump(mode="json")
    checksum = sha256_checksum(payload)

    existing = get_bundle(db, bundle_id=bundle.bundle_id, version=bundle.version)
    if existing is not None:
        if existing.checksum == checksum:
            return existing
        existing.jurisdiction = bundle.jurisdiction
        existing.regime = bundle.regime
        existing.checksum = checksum
        existing.payload = payload
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
) -> list[tuple[str, str, str]]:
    """Deterministically sync bundle files from filesystem into the registry."""
    synced: list[tuple[str, str, str]] = []
    for bundle_path in _iter_bundle_paths(bundles_root.resolve()):
        bundle, checksum, _ = load_bundle(bundle_path)
        upsert_bundle(db, bundle=bundle)
        synced.append((bundle.bundle_id, bundle.version, checksum))
    return sorted(synced)


def compile_from_db(
    db: Session,
    *,
    bundle_id: str,
    version: str,
    context: dict[str, Any],
) -> CompiledRegulatoryPlan:
    """Load bundle payload from registry and compile deterministic plan."""
    row = get_bundle(db, bundle_id=bundle_id, version=version)
    if row is None:
        raise ValueError(f"Bundle not found: {bundle_id}@{version}")
    bundle = RegulatoryBundleSchema.model_validate(row.payload)
    return compile_bundle(bundle, context=context)

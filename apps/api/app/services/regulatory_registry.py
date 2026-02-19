"""Regulatory bundle registry storage service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.regulatory.canonical import sha256_checksum
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


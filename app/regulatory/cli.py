"""CLI helpers for regulatory registry inspection and sync."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import RegulatoryBundle
from apps.api.app.services.regulatory_registry import compile_from_db, sync_from_filesystem


def list_bundles(db: Session) -> list[tuple[str, str, str]]:
    rows = db.scalars(
        select(RegulatoryBundle).order_by(RegulatoryBundle.bundle_id, RegulatoryBundle.version)
    ).all()
    return [(row.bundle_id, row.version, row.checksum) for row in rows]


def sync_bundles(db: Session, *, bundles_root: Path) -> list[tuple[str, str, str]]:
    return sync_from_filesystem(db, bundles_root=bundles_root)


def compile_preview(
    db: Session,
    *,
    bundle_id: str,
    version: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    compiled = compile_from_db(
        db,
        bundle_id=bundle_id,
        version=version,
        context=context,
    )
    return compiled.model_dump(mode="json")


def context_from_json(value: str) -> dict[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("context JSON must decode to an object")
    return payload


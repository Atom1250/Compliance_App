"""Run input snapshot persistence helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import RunInputSnapshot


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def persist_run_input_snapshot(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
    payload: dict[str, Any],
) -> RunInputSnapshot:
    existing = db.scalar(
        select(RunInputSnapshot).where(
            RunInputSnapshot.run_id == run_id,
            RunInputSnapshot.tenant_id == tenant_id,
        )
    )
    if existing is not None:
        return existing

    payload_json = _canonical_json(payload)
    checksum = hashlib.sha256(payload_json.encode()).hexdigest()
    row = RunInputSnapshot(
        run_id=run_id,
        tenant_id=tenant_id,
        payload_json=payload_json,
        checksum=checksum,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


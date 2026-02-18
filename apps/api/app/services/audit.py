"""Structured logging and run-event audit trail helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.ops import redact_sensitive_fields
from apps.api.app.db.models import RunEvent

_audit_logger = logging.getLogger("compliance.audit")


def log_structured_event(event_type: str, **fields: Any) -> str:
    payload = redact_sensitive_fields({"event_type": event_type, **fields})
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _audit_logger.info(serialized)
    return serialized


def append_run_event(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> RunEvent:
    serialized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    event = RunEvent(
        run_id=run_id, tenant_id=tenant_id, event_type=event_type, payload=serialized_payload
    )
    db.add(event)
    return event


def list_run_events(db: Session, *, run_id: int, tenant_id: str) -> list[RunEvent]:
    return db.scalars(
        select(RunEvent)
        .where(RunEvent.run_id == run_id, RunEvent.tenant_id == tenant_id)
        .order_by(RunEvent.created_at.asc(), RunEvent.id.asc())
    ).all()

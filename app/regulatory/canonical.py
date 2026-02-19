"""Deterministic canonicalization and checksum helpers for regulatory bundles."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json(payload: dict[str, Any] | BaseModel) -> str:
    """Serialize payload using deterministic JSON formatting."""
    data: Any
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json")
    else:
        data = payload
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256_checksum(payload: dict[str, Any] | BaseModel) -> str:
    """Return deterministic SHA-256 over canonical JSON."""
    canonical = canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


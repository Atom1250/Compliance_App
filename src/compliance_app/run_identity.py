"""Deterministic run identity helpers.

These helpers are intentionally pure and side-effect free so they can be
reused by later pipeline stages that require reproducible run hashing.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_json(payload: dict[str, Any]) -> str:
    """Serialize payload in a stable canonical form."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_run_input_fingerprint(payload: dict[str, Any]) -> str:
    """Return a stable SHA-256 digest for run inputs.

    The hash stays stable for semantically identical dictionaries, regardless
    of insertion order.
    """
    canonical = _canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

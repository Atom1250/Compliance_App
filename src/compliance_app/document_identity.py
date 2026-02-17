"""Deterministic document identity helpers for ingestion scaffolding."""

from __future__ import annotations

import hashlib


def sha256_bytes(content: bytes) -> str:
    """Return deterministic SHA-256 digest for raw document bytes."""
    return hashlib.sha256(content).hexdigest()


def stable_document_id(*, content_hash: str, source_name: str) -> str:
    """Return deterministic document identity derived from explicit inputs.

    The identifier is stable for identical `content_hash` and `source_name`
    and changes when either input changes.
    """
    normalized_name = source_name.strip().lower()
    identity_seed = f"{content_hash}:{normalized_name}".encode()
    return hashlib.sha256(identity_seed).hexdigest()

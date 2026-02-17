"""Object storage helpers for immutable document bytes."""

from __future__ import annotations

from pathlib import Path


def object_path_for_hash(storage_root: Path, sha256_hash: str) -> Path:
    """Build deterministic object path from content hash."""
    return storage_root / sha256_hash[:2] / f"{sha256_hash}.bin"


def ensure_bytes_stored(storage_root: Path, sha256_hash: str, content: bytes) -> Path:
    """Store bytes only if object for hash does not already exist."""
    object_path = object_path_for_hash(storage_root, sha256_hash)
    object_path.parent.mkdir(parents=True, exist_ok=True)
    if not object_path.exists():
        object_path.write_bytes(content)
    return object_path

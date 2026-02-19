"""Filesystem loader for validated regulatory bundles."""

from __future__ import annotations

import json
from pathlib import Path

from app.regulatory.canonical import sha256_checksum
from app.regulatory.schema import RegulatoryBundle


def load_bundle(bundle_path: Path) -> tuple[RegulatoryBundle, str, Path]:
    """Load, validate, and checksum a regulatory bundle JSON file."""
    source_path = bundle_path.resolve()
    payload = json.loads(source_path.read_text())
    bundle = RegulatoryBundle.model_validate(payload)
    checksum = sha256_checksum(bundle)
    return bundle, checksum, source_path


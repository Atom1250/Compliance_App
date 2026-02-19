"""Sync repo regulatory bundles into DB registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.app.db.session import get_session_factory
from apps.api.app.services.regulatory_registry import sync_from_filesystem


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        default="app/regulatory/bundles",
        help="Root path containing regulatory bundle JSON files",
    )
    parser.add_argument(
        "--mode",
        choices=("merge", "sync"),
        default="sync",
        help="merge=upsert only; sync=deactivate bundles missing from source path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    bundle_root = Path(args.path).expanduser().resolve()
    if not bundle_root.exists():
        parser.error(f"path does not exist: {bundle_root}")
    session_factory = get_session_factory()
    with session_factory() as db:
        synced = sync_from_filesystem(db, bundles_root=bundle_root, mode=args.mode)
    print(json.dumps({"mode": args.mode, "synced": synced}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

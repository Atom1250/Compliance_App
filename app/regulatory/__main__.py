"""Regulatory registry CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.regulatory.cli import compile_preview, context_from_json, list_bundles, sync_bundles
from apps.api.app.db.session import get_session_factory


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Regulatory registry CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List stored registry bundles")

    sync_parser = sub.add_parser("sync", help="Sync bundles from filesystem")
    sync_parser.add_argument("--bundles-root", required=True, help="Root directory containing bundle JSON")
    sync_parser.add_argument(
        "--mode",
        choices=("merge", "sync"),
        default="sync",
        help="merge=upsert only, sync=deactivate bundles absent from source path",
    )

    preview_parser = sub.add_parser("compile-preview", help="Compile plan preview from DB bundle")
    preview_parser.add_argument("--bundle-id", required=True)
    preview_parser.add_argument("--version", required=True)
    preview_parser.add_argument("--context-json", required=True)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    session_factory = get_session_factory()
    session = session_factory()
    try:
        if args.command == "list":
            print(json.dumps(list_bundles(session), indent=2))
            return 0
        if args.command == "sync":
            print(
                json.dumps(
                    sync_bundles(session, bundles_root=Path(args.bundles_root), mode=args.mode),
                    indent=2,
                )
            )
            return 0
        if args.command == "compile-preview":
            context = context_from_json(args.context_json)
            print(
                json.dumps(
                    compile_preview(
                        session,
                        bundle_id=args.bundle_id,
                        version=args.version,
                        context=context,
                    ),
                    indent=2,
                )
            )
            return 0
        parser.error(f"Unknown command: {args.command}")
    finally:
        session.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

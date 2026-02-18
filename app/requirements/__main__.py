"""CLI for requirements bundle imports.

Usage:
    python -m app.requirements import --bundle requirements/esrs_mini/bundle.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.core.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.requirements")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import requirements bundle")
    import_parser.add_argument("--bundle", required=True, help="Path to bundle JSON file")
    import_parser.add_argument(
        "--database-url",
        required=False,
        help="Optional SQLAlchemy database URL override",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command != "import":
        parser.error("Unsupported command")

    bundle_path = Path(args.bundle)
    bundle = load_bundle(bundle_path)

    database_url = args.database_url or get_settings().database_url
    engine = create_engine(database_url)

    with Session(engine) as session:
        imported = import_bundle(session, bundle)

    print(
        f"imported bundle_id={imported.bundle_id} version={imported.version} id={imported.id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

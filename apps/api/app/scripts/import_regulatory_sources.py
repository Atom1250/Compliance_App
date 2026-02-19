"""CLI for importing curated regulatory source documents into Postgres."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from apps.api.app.db.session import get_session_factory
from apps.api.app.services.regulatory_sources_import import import_regulatory_sources


def _parse_sheets(sheet_args: list[str], sheets_csv: str | None) -> tuple[str, ...] | None:
    values: list[str] = []
    for sheet in sheet_args:
        token = sheet.strip()
        if token:
            values.append(token)
    if sheets_csv:
        values.extend(token.strip() for token in sheets_csv.split(",") if token.strip())
    if not values:
        return None
    return tuple(sorted(set(values)))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Path to .csv or .xlsx source register")
    parser.add_argument(
        "--sheet",
        action="append",
        default=[],
        help="Optional sheet name for XLSX imports (repeat for multiple)",
    )
    parser.add_argument(
        "--sheets",
        default=None,
        help="Optional comma-separated sheet names for XLSX imports",
    )
    parser.add_argument(
        "--jurisdiction",
        default=None,
        help="Optional exact jurisdiction filter (example: EU)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate/preview without DB writes")
    parser.add_argument(
        "--issues-out",
        default="./regulatory_import_issues.csv",
        help="CSV path for validation issues output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    sheets = _parse_sheets(args.sheet, args.sheets)
    file_path = Path(args.file).expanduser().resolve()
    issues_out = Path(args.issues_out).expanduser().resolve() if args.issues_out else None
    if not file_path.exists():
        print(f"error: file not found: {file_path}", file=sys.stderr)
        return 2

    session_factory = get_session_factory()
    with session_factory() as db:
        try:
            summary = import_regulatory_sources(
                db,
                file_path=file_path,
                sheets=sheets,
                jurisdiction=args.jurisdiction,
                dry_run=bool(args.dry_run),
                issues_out=issues_out,
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    result = summary.as_dict()
    result["issues_out"] = str(issues_out) if issues_out else None
    result["dry_run"] = bool(args.dry_run)
    print(json.dumps(result, sort_keys=True))
    if summary.invalid_rows > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

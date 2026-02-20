"""CLI wrapper for internal regulatory research workflows."""

from __future__ import annotations

import argparse
import json
import sys

from apps.api.app.core.config import get_settings
from apps.api.app.db.session import get_session_factory
from apps.api.app.services.regulatory_research.factory import build_regulatory_research_service
from apps.api.app.services.regulatory_research.service import ResearchActor
from apps.api.app.services.regulatory_research.types import ResearchRequest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--requirement",
        default=None,
        help="Requirement ID for persistence linkage",
    )
    parser.add_argument("--corpus", required=True, help="Corpus key (example: EU-CSRD-ESRS)")
    parser.add_argument(
        "--mode",
        choices=("tagging", "mapping", "qa", "draft_prd"),
        required=True,
        help="Research mode",
    )
    parser.add_argument("--question", required=True, help="Research question")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--actor", default="cli-user", help="Actor ID for persisted notes")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist note when persistence flag is enabled and requirement is provided",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    service = build_regulatory_research_service(settings)

    tags = [item.strip() for item in args.tags.split(",") if item.strip()]
    request = ResearchRequest(
        question=args.question,
        corpus_key=args.corpus,
        mode=args.mode,  # type: ignore[arg-type]
        requirement_id=args.requirement,
        tags=tags,
    )

    session_factory = get_session_factory()
    with session_factory() as db:
        try:
            if args.persist:
                result = service.query_and_maybe_persist_with_note(
                    db,
                    req=request,
                    actor=ResearchActor(id=args.actor),
                )
                response = result.response
                note_id = result.note_id
            else:
                response = service.query(db, req=request)
                note_id = None
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    payload = {
        "answer_markdown": response.answer_markdown,
        "provider": response.provider,
        "request_hash": response.request_hash,
        "latency_ms": response.latency_ms,
        "persisted_note_id": note_id,
        "citations": [citation.__dict__ for citation in response.citations],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

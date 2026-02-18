"""Backfill deterministic chunks for documents that have pages but no chunks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from apps.api.app.db.models import Chunk, Document, DocumentFile, DocumentPage
from apps.api.app.services.chunking import persist_chunks_for_document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    engine = create_engine(args.database_url)
    with Session(engine) as db:
        documents = db.scalars(select(Document).order_by(Document.id)).all()
        updated = 0
        for document in documents:
            page_count = db.query(DocumentPage).filter(DocumentPage.document_id == document.id).count()
            if page_count == 0:
                continue
            chunk_count = db.query(Chunk).filter(Chunk.document_id == document.id).count()
            if chunk_count > 0:
                continue
            file_row = db.scalar(select(DocumentFile).where(DocumentFile.document_id == document.id))
            if file_row is None:
                continue
            persist_chunks_for_document(
                db,
                document_id=document.id,
                document_hash=file_row.sha256_hash,
            )
            updated += 1
        db.commit()

    print(f"backfilled_documents={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

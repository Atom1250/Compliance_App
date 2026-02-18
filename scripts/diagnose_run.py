"""Run-stage diagnostics for a completed/failed run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.db.models import (
    Chunk,
    Company,
    DatapointAssessment,
    Document,
    DocumentFile,
    DocumentPage,
    Run,
    RunEvent,
    RunManifest,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    args = parser.parse_args()

    engine = create_engine(args.database_url)
    with Session(engine) as db:
        run = db.get(Run, args.run_id)
        if run is None:
            print(f"run not found: {args.run_id}")
            return 1
        company = db.get(Company, run.company_id)
        if company is None:
            print(f"company not found for run: {args.run_id}")
            return 1

        print("== Run ==")
        print(f"run_id={run.id} status={run.status} tenant_id={run.tenant_id}")
        print(
            "company="
            f"{company.name} reporting_year={company.reporting_year} "
            f"listed_status={company.listed_status} employees={company.employees} turnover={company.turnover}"
        )

        docs = db.scalars(
            select(Document).where(Document.company_id == company.id).order_by(Document.id)
        ).all()
        print("\n== Documents ==")
        print(f"document_count={len(docs)}")
        for doc in docs:
            file_row = db.scalar(select(DocumentFile).where(DocumentFile.document_id == doc.id))
            page_count = (
                db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).count()
            )
            chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
            print(
                f"- document_id={doc.id} title={doc.title!r} "
                f"pages={page_count} chunks={chunk_count} "
                f"sha256={file_row.sha256_hash if file_row else 'n/a'}"
            )

        manifest = db.scalar(select(RunManifest).where(RunManifest.run_id == run.id))
        print("\n== Manifest ==")
        if manifest is None:
            print("manifest=missing")
            bundle_id = "unknown"
            bundle_version = "unknown"
        else:
            retrieval = json.loads(manifest.retrieval_params)
            print(
                "bundle="
                f"{manifest.bundle_id}@{manifest.bundle_version} "
                f"model={manifest.model_name} provider={retrieval.get('llm_provider')}"
            )
            bundle_id = manifest.bundle_id
            bundle_version = manifest.bundle_version

        print("\n== Applicability ==")
        if bundle_id == "unknown":
            print("required_datapoints=unknown (manifest missing)")
        else:
            required = resolve_required_datapoint_ids(
                db,
                company_id=company.id,
                bundle_id=bundle_id,
                bundle_version=bundle_version,
                run_id=run.id,
            )
            print(f"required_datapoints_count={len(required)}")
            print(f"required_datapoints={required}")

        assessments = db.scalars(
            select(DatapointAssessment)
            .where(DatapointAssessment.run_id == run.id)
            .order_by(DatapointAssessment.datapoint_key)
        ).all()
        counts = Counter(item.status for item in assessments)
        print("\n== Assessments ==")
        print(f"assessment_count={len(assessments)}")
        print(f"status_counts={dict(counts)}")

        print("\n== Events ==")
        events = db.scalars(
            select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.id)
        ).all()
        for evt in events:
            print(f"- {evt.event_type} payload={evt.payload}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Golden-run snapshot harness for determinism contract tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from apps.api.app.db.models import DatapointAssessment
from apps.api.app.services.chunking import build_page_chunks, rank_chunks_for_query_sanity
from apps.api.app.services.reporting import generate_html_report, normalize_report_html
from apps.api.app.services.run_cache import RunHashInput, compute_run_hash
from compliance_app.document_identity import sha256_bytes, stable_document_id


def generate_golden_snapshot(*, document_text: str) -> dict[str, object]:
    content = document_text.encode()
    content_hash = sha256_bytes(content)
    document_id = stable_document_id(content_hash=content_hash, source_name="sample_report.txt")

    chunks = build_page_chunks(
        document_hash=content_hash,
        page_number=1,
        text=document_text,
        chunk_size=90,
        chunk_overlap=20,
    )
    ranked = rank_chunks_for_query_sanity("green allocation balance", chunks, top_k=3)

    evidence_chunk_ids = [ranked[0].chunk_id] if ranked else []
    assessments = [
        DatapointAssessment(
            run_id=900,
            datapoint_key="GF-OBL-01",
            status="Present",
            value="allocation framework published",
            evidence_chunk_ids=json.dumps(evidence_chunk_ids),
            rationale="Disclosed in framework report.",
            model_name="gpt-5",
            prompt_hash="golden-prompt-hash",
            retrieval_params='{"query_mode":"hybrid","top_k":3}',
        ),
        DatapointAssessment(
            run_id=900,
            datapoint_key="GF-OBL-02",
            status="Partial",
            value="42 million EUR",
            evidence_chunk_ids=json.dumps(evidence_chunk_ids),
            rationale="Allocation amount disclosed.",
            model_name="gpt-5",
            prompt_hash="golden-prompt-hash",
            retrieval_params='{"query_mode":"hybrid","top_k":3}',
        ),
    ]

    html = normalize_report_html(
        generate_html_report(
            run_id=900,
            assessments=assessments,
            generated_at=datetime(2026, 2, 18, 12, 0, tzinfo=UTC),
        )
    )

    run_hash = compute_run_hash(
        RunHashInput(
            document_hashes=[content_hash],
            company_profile={"employees": 500, "listed_status": True, "reporting_year": 2026},
            materiality_inputs={"green_finance": True},
            bundle_version="2026.01",
            retrieval_params={"query_mode": "hybrid", "top_k": 3},
            prompt_hash="golden-prompt-hash",
        )
    )

    return {
        "content_hash": content_hash,
        "document_id": document_id,
        "chunk_ids": [chunk.chunk_id for chunk in chunks],
        "top_ranked_chunk_ids": [chunk.chunk_id for chunk in ranked],
        "run_hash": run_hash,
        "normalized_report_html": html,
    }

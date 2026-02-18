"""Deterministic evidence pack ZIP export for assessment runs."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import Chunk, DatapointAssessment, DocumentFile

_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class PackFile:
    path: str
    content: bytes


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _document_bytes_from_uri(storage_uri: str) -> bytes:
    prefix = "file://"
    if not storage_uri.startswith(prefix):
        raise ValueError(f"Unsupported storage URI: {storage_uri}")
    return Path(storage_uri[len(prefix) :]).read_bytes()


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path)
    info.date_time = _ZIP_TIMESTAMP
    info.compress_type = zipfile.ZIP_STORED
    return info


def export_evidence_pack(
    db: Session,
    *,
    run_id: int,
    output_zip_path: Path,
) -> Path:
    assessments = db.scalars(
        select(DatapointAssessment)
        .where(DatapointAssessment.run_id == run_id)
        .order_by(DatapointAssessment.datapoint_key)
    ).all()

    assessments_rows: list[dict[str, object]] = []
    cited_chunk_ids: set[str] = set()
    for assessment in assessments:
        evidence_ids = sorted(json.loads(assessment.evidence_chunk_ids))
        cited_chunk_ids.update(evidence_ids)
        assessments_rows.append(
            {
                "datapoint_key": assessment.datapoint_key,
                "status": assessment.status,
                "value": assessment.value,
                "evidence_chunk_ids": evidence_ids,
                "rationale": assessment.rationale,
                "model_name": assessment.model_name,
                "prompt_hash": assessment.prompt_hash,
                "retrieval_params": json.loads(assessment.retrieval_params),
            }
        )

    chunks = db.scalars(
        select(Chunk).where(Chunk.chunk_id.in_(sorted(cited_chunk_ids))).order_by(Chunk.chunk_id)
    ).all()
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}

    evidence_rows: list[dict[str, object]] = []
    referenced_document_ids: set[int] = set()
    for chunk_id in sorted(cited_chunk_ids):
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            continue
        referenced_document_ids.add(chunk.document_id)
        evidence_rows.append(
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "text": chunk.text,
            }
        )

    document_files = db.scalars(
        select(DocumentFile)
        .where(DocumentFile.document_id.in_(sorted(referenced_document_ids)))
        .order_by(DocumentFile.sha256_hash)
    ).all()

    files: list[PackFile] = []
    assessments_jsonl = "".join(
        f"{json.dumps(row, sort_keys=True, separators=(',', ':'))}\n" for row in assessments_rows
    ).encode()
    evidence_jsonl = "".join(
        f"{json.dumps(row, sort_keys=True, separators=(',', ':'))}\n" for row in evidence_rows
    ).encode()
    files.append(PackFile(path="assessments.jsonl", content=assessments_jsonl))
    files.append(PackFile(path="evidence.jsonl", content=evidence_jsonl))

    documents_manifest: list[dict[str, str]] = []
    for document_file in document_files:
        bytes_content = _document_bytes_from_uri(document_file.storage_uri)
        content_hash = _sha256_bytes(bytes_content)
        if content_hash != document_file.sha256_hash:
            raise ValueError(
                f"Document hash mismatch for {document_file.document_id}: "
                f"expected {document_file.sha256_hash}, got {content_hash}"
            )
        path = f"documents/{document_file.sha256_hash}.bin"
        files.append(PackFile(path=path, content=bytes_content))
        documents_manifest.append(
            {
                "document_id": str(document_file.document_id),
                "sha256_hash": document_file.sha256_hash,
                "path": path,
            }
        )

    manifest_base = {
        "run_id": run_id,
        "documents": documents_manifest,
    }
    manifest_with_hashes = {
        **manifest_base,
        "pack_files": [
            {"path": entry.path, "sha256": _sha256_bytes(entry.content)}
            for entry in sorted(files, key=lambda item: item.path)
        ],
    }
    manifest_json = json.dumps(manifest_with_hashes, sort_keys=True, separators=(",", ":")).encode()
    files.append(PackFile(path="manifest.json", content=manifest_json))

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip_path, mode="w") as zip_file:
        for entry in sorted(files, key=lambda item: item.path):
            zip_file.writestr(_zip_info(entry.path), entry.content)
    return output_zip_path

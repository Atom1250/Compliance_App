"""ORM models for initial system-of-record tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.app.db.base import Base


class Company(Base):
    __tablename__ = "company"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    employees: Mapped[int | None] = mapped_column(nullable=True)
    turnover: Mapped[float | None] = mapped_column(nullable=True)
    listed_status: Mapped[bool | None] = mapped_column(nullable=True)
    reporting_year: Mapped[int | None] = mapped_column(nullable=True)
    reporting_year_start: Mapped[int | None] = mapped_column(nullable=True)
    reporting_year_end: Mapped[int | None] = mapped_column(nullable=True)
    regulatory_jurisdictions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    regulatory_regimes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentFile(Base):
    __tablename__ = "document_file"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False, index=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentPage(Base):
    __tablename__ = "document_page"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False, index=True)
    page_number: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Chunk(Base):
    __tablename__ = "chunk"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False, index=True)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    page_number: Mapped[int] = mapped_column(nullable=False)
    start_offset: Mapped[int] = mapped_column(nullable=False)
    end_offset: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_tsv: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Embedding(Base):
    __tablename__ = "embedding"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunk.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dimensions: Mapped[int] = mapped_column(nullable=False)
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RequirementBundle(Base):
    __tablename__ = "requirement_bundle"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    standard: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DatapointDefinition(Base):
    __tablename__ = "datapoint_def"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requirement_bundle_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_bundle.id"), nullable=False, index=True
    )
    datapoint_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    disclosure_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    materiality_topic: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ApplicabilityRule(Base):
    __tablename__ = "applicability_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requirement_bundle_id: Mapped[int] = mapped_column(
        ForeignKey("requirement_bundle.id"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    datapoint_key: Mapped[str] = mapped_column(String(128), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Run(Base):
    __tablename__ = "run"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    compiler_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="legacy")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RunEvent(Base):
    __tablename__ = "run_event"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RunMateriality(Base):
    __tablename__ = "run_materiality"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    is_material: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DatapointAssessment(Base):
    __tablename__ = "datapoint_assessment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    datapoint_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_chunk_ids: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_params: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RunCacheEntry(Base):
    __tablename__ = "run_cache_entry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    run_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RunManifest(Base):
    __tablename__ = "run_manifest"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("run.id"), nullable=False, unique=True, index=True
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    document_hashes: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_id: Mapped[str] = mapped_column(String(128), nullable=False)
    bundle_version: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_params: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RegulatoryBundle(Base):
    __tablename__ = "regulatory_bundle"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bundle_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(64), nullable=False)
    regime: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RunRegistryArtifact(Base):
    __tablename__ = "run_registry_artifact"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    artifact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentDiscoveryCandidate(Base):
    __tablename__ = "document_discovery_candidate"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    accepted: Mapped[bool] = mapped_column(nullable=False, default=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RunInputSnapshot(Base):
    __tablename__ = "run_input_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("run.id"),
        nullable=False,
        index=True,
        unique=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", index=True
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

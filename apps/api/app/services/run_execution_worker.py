"""Asynchronous run execution worker with deterministic lifecycle semantics."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.regulatory.datapoint_generation import generate_registry_datapoints
from app.requirements.applicability import resolve_required_datapoint_ids
from apps.api.app.core.config import get_settings
from apps.api.app.db.models import (
    Chunk,
    Company,
    DatapointAssessment,
    DatapointDefinition,
    Document,
    DocumentDiscoveryCandidate,
    DocumentFile,
    ExtractionDiagnostics,
    RegulatoryBundle,
    RequirementBundle,
    Run,
    RunMateriality,
)
from apps.api.app.db.session import get_session_factory
from apps.api.app.services.assessment_pipeline import (
    AssessmentRunConfig,
    execute_assessment_pipeline,
)
from apps.api.app.services.audit import append_run_event, log_structured_event
from apps.api.app.services.company_documents import (
    list_company_document_hashes,
    list_company_document_ids,
)
from apps.api.app.services.compiled_plan_persistence import (
    persist_compiled_plan,
    persist_obligation_coverage,
)
from apps.api.app.services.llm_extraction import ExtractionClient
from apps.api.app.services.llm_provider import build_extraction_client_from_settings
from apps.api.app.services.regulatory_compiler import compile_company_regulatory_plan
from apps.api.app.services.regulatory_registry import compile_from_db
from apps.api.app.services.retrieval import (
    get_retrieval_policy,
    retrieval_policy_to_dict,
    retrieve_chunks,
)
from apps.api.app.services.run_cache import (
    RunHashInput,
    get_or_compute_cached_output,
    serialize_assessments,
)
from apps.api.app.services.run_input_snapshot import persist_run_input_snapshot
from apps.api.app.services.run_manifest import RunManifestPayload, persist_run_manifest
from apps.api.app.services.run_quality_gate import (
    TERMINAL_STATUS_FAILED_PIPELINE,
    RunQualityGateConfig,
    RunQualityGateDecision,
    RunQualityMetrics,
    evaluate_run_quality_gate,
)
from apps.api.app.services.run_registry_artifacts import persist_registry_outputs_for_run


@dataclass(frozen=True)
class RunExecutionPayload:
    bundle_id: str
    bundle_version: str
    retrieval_top_k: int
    retrieval_model_name: str
    llm_provider: str
    research_provider: str = "disabled"
    bypass_cache: bool = False


class _DeterministicAbsentTransport:
    def create_response(
        self,
        *,
        model: str,
        input_text: str,
        temperature: float,
        json_schema: dict,
    ):
        del model, input_text, temperature, json_schema
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                '{"status":"Absent","value":null,"evidence_chunk_ids":[],'  # noqa: E501
                                '"rationale":"Deterministic local execution fallback."}'
                            ),
                        }
                    ],
                }
            ]
        }


def _assessment_count(db: Session, *, run_id: int, tenant_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(DatapointAssessment)
            .where(
                DatapointAssessment.run_id == run_id,
                DatapointAssessment.tenant_id == tenant_id,
            )
        )
        or 0
    )


def _classify_failure(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, TimeoutError | httpx.TimeoutException | httpx.ConnectError):
        return "provider_transient", True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code if exc.response is not None else 0
        if 500 <= status_code <= 599:
            return "provider_transient", True
        return "provider_request_invalid", False
    message = str(exc)
    if "openai_api_key is required" in message:
        return "config_error", False
    if "Bundle not found:" in message:
        return "bundle_not_found", False
    if "compiled_obligations_empty_for_csrd_entity" in message:
        return "compiled_plan_empty", False
    if "chunk_table_empty_for_run" in message:
        return "chunk_prerequisite_missing", False
    if "llm_schema_parse_error" in message:
        return "schema_parse_error", False
    if "llm_schema_validation_error" in message:
        return "schema_validation_error", False
    return "internal_error", False


def _materialize_assessments_from_cache(
    db: Session,
    *,
    run_id: int,
    tenant_id: str,
    output_json: str,
) -> list[DatapointAssessment]:
    payload = json.loads(output_json)
    if not isinstance(payload, list):
        raise ValueError("invalid_cached_output_format")
    rows: list[DatapointAssessment] = []
    for item in sorted(payload, key=lambda row: str(row.get("datapoint_key", ""))):
        datapoint_key = str(item.get("datapoint_key") or "").strip()
        status = str(item.get("status") or "").strip()
        if not datapoint_key or not status:
            continue
        evidence_chunk_ids = item.get("evidence_chunk_ids") or []
        if not isinstance(evidence_chunk_ids, list):
            evidence_chunk_ids = []
        retrieval_params = item.get("retrieval_params") or {}
        if not isinstance(retrieval_params, dict):
            retrieval_params = {}
        rows.append(
            DatapointAssessment(
                run_id=run_id,
                tenant_id=tenant_id,
                datapoint_key=datapoint_key,
                status=status,
                value=item.get("value"),
                evidence_chunk_ids=json.dumps(sorted(set(map(str, evidence_chunk_ids)))),
                rationale=str(item.get("rationale") or ""),
                model_name=str(item.get("model_name") or "deterministic-local-v1"),
                prompt_hash=str(item.get("prompt_hash") or ""),
                retrieval_params=json.dumps(
                    retrieval_params, sort_keys=True, separators=(",", ":")
                ),
            )
        )
    for row in rows:
        db.add(row)
    db.flush()
    return rows


def _quality_gate_config_from_settings() -> RunQualityGateConfig:
    settings = get_settings()
    return RunQualityGateConfig(
        min_docs_discovered=settings.quality_gate_min_docs_discovered,
        min_docs_ingested=settings.quality_gate_min_docs_ingested,
        min_chunks_indexed=settings.quality_gate_min_chunks_indexed,
        max_chunk_not_found_rate=settings.quality_gate_max_chunk_not_found_rate,
        min_evidence_hits=settings.quality_gate_min_evidence_hits,
        min_evidence_hits_per_section=settings.quality_gate_min_evidence_hits_per_section,
        fail_on_required_narrative_chunk_not_found=(
            settings.quality_gate_fail_on_required_narrative_chunk_not_found
        ),
        pipeline_failure_status=settings.quality_gate_pipeline_failure_status,
        evidence_failure_status=settings.quality_gate_evidence_failure_status,
    )


def _required_narrative_datapoints(
    db: Session,
    *,
    bundle_id: str,
    bundle_version: str,
    required_datapoint_universe: list[str],
) -> set[str]:
    required_set = set(required_datapoint_universe)
    if not required_set:
        return set()
    rows = db.scalars(
        select(DatapointDefinition)
        .join(RequirementBundle, RequirementBundle.id == DatapointDefinition.requirement_bundle_id)
        .where(
            RequirementBundle.bundle_id == bundle_id,
            RequirementBundle.version == bundle_version,
            DatapointDefinition.datapoint_key.in_(required_set),
            DatapointDefinition.datapoint_type == "narrative",
        )
    ).all()
    return {row.datapoint_key for row in rows}


def _evaluate_quality_gate(
    *,
    db: Session,
    run: Run,
    bundle_id: str,
    bundle_version: str,
    required_datapoint_universe: list[str],
    company_document_ids: list[int],
    chunk_count: int,
    assessment_count: int,
    assessments: list[DatapointAssessment],
    diagnostics_rows: list[ExtractionDiagnostics],
) -> tuple[RunQualityGateDecision, RunQualityMetrics]:
    required_narrative_keys = _required_narrative_datapoints(
        db,
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        required_datapoint_universe=required_datapoint_universe,
    )
    evidence_hits_by_key = {
        row.datapoint_key: len(json.loads(row.evidence_chunk_ids))
        for row in assessments
    }
    required_section_hits = [evidence_hits_by_key.get(key, 0) for key in required_narrative_keys]
    min_required_section_hits = min(required_section_hits) if required_section_hits else 0
    chunk_not_found_keys: set[str] = set()
    for row in diagnostics_rows:
        payload_json = row.diagnostics_json if isinstance(row.diagnostics_json, dict) else {}
        if payload_json.get("failure_reason_code") == "CHUNK_NOT_FOUND":
            chunk_not_found_keys.add(row.datapoint_key)

    docs_discovered = int(
        db.scalar(
            select(func.count())
            .select_from(DocumentDiscoveryCandidate)
            .where(
                DocumentDiscoveryCandidate.company_id == run.company_id,
                DocumentDiscoveryCandidate.tenant_id == run.tenant_id,
                DocumentDiscoveryCandidate.accepted.is_(True),
            )
        )
        or 0
    )
    metrics = RunQualityMetrics(
        docs_discovered=docs_discovered,
        docs_ingested=len(company_document_ids),
        chunks_indexed=chunk_count,
        required_narrative_section_count=len(required_narrative_keys),
        required_narrative_chunk_not_found_count=len(
            chunk_not_found_keys & required_narrative_keys
        ),
        chunk_not_found_count=len(chunk_not_found_keys),
        assessment_count=assessment_count,
        evidence_hits_total=sum(evidence_hits_by_key.values()),
        min_evidence_hits_in_required_section=min_required_section_hits,
    )
    decision = evaluate_run_quality_gate(
        config=_quality_gate_config_from_settings(),
        metrics=metrics,
    )
    return decision, metrics


def _canonicalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url.strip())
    if not parsed.netloc:
        return url.strip()
    normalized = urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            parsed.query,
            "",
        )
    )
    return normalized


def _extract_http_status_from_reason(reason: str) -> int | None:
    if not reason.startswith("http_status_"):
        return None
    suffix = reason.split("http_status_", 1)[1].strip()
    if not suffix.isdigit():
        return None
    return int(suffix)


def _discovery_candidates_snapshot(
    db: Session,
    *,
    run: Run,
) -> list[dict[str, object]]:
    rows = db.scalars(
        select(DocumentDiscoveryCandidate)
        .where(
            DocumentDiscoveryCandidate.company_id == run.company_id,
            DocumentDiscoveryCandidate.tenant_id == run.tenant_id,
        )
        .order_by(DocumentDiscoveryCandidate.id)
    ).all()
    snapshot: list[dict[str, object]] = []
    for row in rows:
        host = urlsplit(row.source_url).netloc.lower() if row.source_url else ""
        snapshot.append(
            {
                "url": row.source_url,
                "host": host,
                "http_status": _extract_http_status_from_reason(row.reason or ""),
                "accepted": bool(row.accepted),
                "reason": row.reason,
                "score": row.score,
            }
        )
    return snapshot


def _selected_documents_snapshot(
    db: Session,
    *,
    run: Run,
    company_document_ids: list[int],
) -> list[dict[str, object]]:
    if not company_document_ids:
        return []
    rows = (
        db.query(Document, DocumentFile)
        .outerjoin(DocumentFile, DocumentFile.document_id == Document.id)
        .filter(Document.id.in_(company_document_ids), Document.tenant_id == run.tenant_id)
        .order_by(Document.id)
        .all()
    )
    snapshot: list[dict[str, object]] = []
    for document, document_file in rows:
        snapshot.append(
            {
                "document_id": document.id,
                "title": document.title,
                "source_url": document.source_url,
                "canonical_url": _canonicalize_url(document.source_url),
                "checksum": document_file.sha256_hash if document_file is not None else None,
                "year": document.reporting_year,
                "doc_type": document.doc_type,
            }
        )
    return snapshot


def _retrieval_smoke_query(
    db: Session,
    *,
    bundle_id: str,
    bundle_version: str,
    required_datapoint_universe: list[str],
    company: Company,
) -> str:
    required_set = set(required_datapoint_universe)
    if required_set:
        row = db.scalar(
            select(DatapointDefinition)
            .join(
                RequirementBundle,
                RequirementBundle.id == DatapointDefinition.requirement_bundle_id,
            )
            .where(
                RequirementBundle.bundle_id == bundle_id,
                RequirementBundle.version == bundle_version,
                DatapointDefinition.datapoint_key.in_(required_set),
            )
            .order_by(DatapointDefinition.datapoint_key)
            .limit(1)
        )
        if row is not None:
            return f"{row.title} {row.disclosure_reference}".strip()
    reporting_year = company.reporting_year_end or company.reporting_year
    if reporting_year:
        return f"{company.name} annual report {reporting_year}"
    return f"{company.name} annual report"


def _run_retrieval_smoke_test(
    db: Session,
    *,
    run: Run,
    company: Company,
    bundle_id: str,
    bundle_version: str,
    required_datapoint_universe: list[str],
    top_k: int,
    model_name: str,
) -> dict[str, object]:
    settings = get_settings()
    query = _retrieval_smoke_query(
        db,
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        required_datapoint_universe=required_datapoint_universe,
        company=company,
    )
    strict_results = retrieve_chunks(
        db,
        query=query,
        query_embedding=None,
        top_k=top_k,
        tenant_id=run.tenant_id,
        company_id=run.company_id,
        model_name=model_name,
        policy=get_retrieval_policy(),
    )
    relaxed_results: list = []
    if len(strict_results) == 0:
        relaxed_results = retrieve_chunks(
            db,
            query=query,
            query_embedding=None,
            top_k=top_k,
            tenant_id=run.tenant_id,
            company_id=None,
            model_name=model_name,
            policy=get_retrieval_policy(),
        )
    diagnostic = "none"
    if len(strict_results) == 0 and len(relaxed_results) > 0:
        diagnostic = "FILTER_TOO_STRICT"
    auto_relaxed = diagnostic == "FILTER_TOO_STRICT" and settings.retrieval_smoke_auto_relax_filters
    return {
        "query": query,
        "top_k": top_k,
        "strict_result_count": len(strict_results),
        "strict_chunk_ids": [item.chunk_id for item in strict_results],
        "relaxed_result_count": len(relaxed_results),
        "relaxed_chunk_ids": [item.chunk_id for item in relaxed_results],
        "diagnostic": diagnostic,
        "auto_relaxed_filters": auto_relaxed,
        "strict_filters": {"tenant_id": run.tenant_id, "company_id": run.company_id},
        "relaxed_filters": {"tenant_id": run.tenant_id, "company_id": None},
    }


def _process_run_execution(run_id: int, payload: RunExecutionPayload) -> None:
    session_factory = get_session_factory()
    with session_factory() as db:
        run = db.get(Run, run_id)
        if run is None:
            return

        run.status = "running"
        append_run_event(
            db,
            run_id=run.id,
            tenant_id=run.tenant_id,
            event_type="run.execution.started",
            payload={
                "tenant_id": run.tenant_id,
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "llm_provider": payload.llm_provider,
                "research_provider": payload.research_provider,
                "bypass_cache": payload.bypass_cache,
            },
        )
        log_structured_event(
            "run.execution.started",
            run_id=run.id,
            tenant_id=run.tenant_id,
            bundle_id=payload.bundle_id,
            bundle_version=payload.bundle_version,
            llm_provider=payload.llm_provider,
            research_provider=payload.research_provider,
            bypass_cache=payload.bypass_cache,
        )
        db.commit()

        try:
            settings = get_settings()
            extraction_client = (
                build_extraction_client_from_settings(settings, provider=payload.llm_provider)
                if payload.llm_provider in {"local_lm_studio", "openai_cloud"}
                else ExtractionClient(
                    transport=_DeterministicAbsentTransport(),
                    model="deterministic-local-v1",
                )
            )

            company = db.scalar(
                select(Company).where(
                    Company.id == run.company_id,
                    Company.tenant_id == run.tenant_id,
                )
            )
            if company is None:
                raise ValueError("company not found")

            materiality_rows = db.scalars(
                select(RunMateriality)
                .where(RunMateriality.run_id == run.id, RunMateriality.tenant_id == run.tenant_id)
                .order_by(RunMateriality.topic)
            ).all()
            materiality_inputs = {row.topic: row.is_material for row in materiality_rows}

            company_document_ids = list_company_document_ids(
                db, company_id=run.company_id, tenant_id=run.tenant_id
            )
            document_count = len(company_document_ids)
            if document_count == 0:
                append_run_event(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    event_type="run.execution.warning",
                    payload={
                        "tenant_id": run.tenant_id,
                        "reason": "document_universe_empty",
                        "company_document_count": document_count,
                    },
                )

            document_hashes = list_company_document_hashes(
                db, company_id=run.company_id, tenant_id=run.tenant_id
            )
            retrieval_policy = get_retrieval_policy()

            retrieval_params = {
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "compiler_mode": run.compiler_mode,
                "llm_provider": payload.llm_provider,
                "research_provider": payload.research_provider,
                "query_mode": "hybrid",
                "retrieval_model_name": payload.retrieval_model_name,
                "retrieval_policy": retrieval_policy_to_dict(retrieval_policy),
                "top_k": payload.retrieval_top_k,
            }
            registry_checksums: list[str] = []
            if settings.feature_registry_compiler and run.compiler_mode == "registry":
                registry_rows = db.scalars(
                    select(RegulatoryBundle.checksum)
                    .where(
                        RegulatoryBundle.bundle_id == payload.bundle_id,
                        RegulatoryBundle.version == payload.bundle_version,
                    )
                    .order_by(RegulatoryBundle.checksum)
                ).all()
                registry_checksums = sorted(set(registry_rows))
                retrieval_params["registry"] = {
                    "bundle_checksums": registry_checksums,
                    "mode": "registry",
                }
            prompt_seed = {
                "bundle_id": payload.bundle_id,
                "bundle_version": payload.bundle_version,
                "compiler_mode": run.compiler_mode,
                "llm_provider": payload.llm_provider,
                "research_provider": payload.research_provider,
                "model_name": extraction_client.model_name,
                "retrieval_params": retrieval_params,
            }
            prompt_hash = hashlib.sha256(
                json.dumps(prompt_seed, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            regulatory_plan_result = compile_company_regulatory_plan(
                db,
                company=company,
            )
            persisted_plan = persist_compiled_plan(
                db,
                company_id=company.id,
                reporting_year=company.reporting_year_end or company.reporting_year,
                jurisdictions=list(regulatory_plan_result.plan.get("jurisdictions", [])),
                regimes=list(regulatory_plan_result.plan.get("regimes", [])),
                plan=regulatory_plan_result.plan,
            )
            if run.compiler_mode == "registry" and "CSRD_ESRS" in regulatory_plan_result.plan.get(
                "regimes", []
            ):
                if persisted_plan.obligations_count == 0:
                    raise ValueError("compiled_obligations_empty_for_csrd_entity")

            if settings.feature_registry_compiler and run.compiler_mode == "registry":
                compiled_for_snapshot = compile_from_db(
                    db,
                    bundle_id=payload.bundle_id,
                    version=payload.bundle_version,
                    context={
                        "company": {
                            "employees": company.employees,
                            "listed_status": company.listed_status,
                            "reporting_year": company.reporting_year,
                            "reporting_year_start": company.reporting_year_start,
                            "reporting_year_end": company.reporting_year_end,
                            "turnover": company.turnover,
                        }
                    },
                )
                required_datapoint_universe = sorted(
                    item.datapoint_key
                    for item in generate_registry_datapoints(compiled_for_snapshot)
                )
            else:
                required_datapoint_universe = resolve_required_datapoint_ids(
                    db,
                    company_id=run.company_id,
                    bundle_id=payload.bundle_id,
                    bundle_version=payload.bundle_version,
                    run_id=run.id,
                )
            discovery_candidates_snapshot = _discovery_candidates_snapshot(db, run=run)
            selected_documents_snapshot = _selected_documents_snapshot(
                db, run=run, company_document_ids=company_document_ids
            )
            retrieval_smoke_test = _run_retrieval_smoke_test(
                db,
                run=run,
                company=company,
                bundle_id=payload.bundle_id,
                bundle_version=payload.bundle_version,
                required_datapoint_universe=required_datapoint_universe,
                top_k=max(1, settings.retrieval_smoke_top_k),
                model_name=payload.retrieval_model_name,
            )
            retrieval_params["smoke_test"] = {
                "diagnostic": retrieval_smoke_test["diagnostic"],
                "auto_relaxed_filters": retrieval_smoke_test["auto_relaxed_filters"],
            }
            append_run_event(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                event_type="run.execution.retrieval_smoke_test",
                payload={"tenant_id": run.tenant_id, **retrieval_smoke_test},
            )
            persist_run_input_snapshot(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                payload={
                    "run_id": run.id,
                    "tenant_id": run.tenant_id,
                    "company_id": run.company_id,
                    "company_profile": {
                        "employees": company.employees,
                        "listed_status": company.listed_status,
                        "reporting_year": company.reporting_year,
                        "reporting_year_start": company.reporting_year_start,
                        "reporting_year_end": company.reporting_year_end,
                        "turnover": company.turnover,
                    },
                    "materiality_inputs": materiality_inputs,
                    "bundle_id": payload.bundle_id,
                    "bundle_version": payload.bundle_version,
                    "compiler_mode": run.compiler_mode,
                    "retrieval": retrieval_params,
                    "required_datapoint_universe": required_datapoint_universe,
                    "discovery_candidates": discovery_candidates_snapshot,
                    "selected_documents": selected_documents_snapshot,
                    "retrieval_smoke_test": retrieval_smoke_test,
                },
            )

            chunk_count = (
                int(
                    db.scalar(
                        select(func.count())
                        .select_from(Chunk)
                        .where(Chunk.document_id.in_(company_document_ids))
                    )
                    or 0
                )
                if company_document_ids
                else 0
            )
            computed_assessments: list[DatapointAssessment] | None = None

            def _compute_assessments():
                nonlocal computed_assessments
                computed_assessments = execute_assessment_pipeline(
                    db,
                    extraction_client=extraction_client,
                    config=AssessmentRunConfig(
                        run_id=run.id,
                        bundle_id=payload.bundle_id,
                        bundle_version=payload.bundle_version,
                        retrieval_top_k=payload.retrieval_top_k,
                        retrieval_model_name=payload.retrieval_model_name,
                        relax_retrieval_company_filter=bool(
                            retrieval_smoke_test["auto_relaxed_filters"]
                        ),
                    ),
                )
                return computed_assessments

            if payload.bypass_cache:
                computed_assessments = _compute_assessments()
                output_json = serialize_assessments(computed_assessments)
                cache_hit = False
            else:
                output_json, cache_hit = get_or_compute_cached_output(
                    db,
                    run_id=run.id,
                    hash_input=RunHashInput(
                        tenant_id=run.tenant_id,
                        document_hashes=document_hashes,
                        company_profile={
                            "employees": company.employees,
                            "listed_status": company.listed_status,
                            "reporting_year": company.reporting_year,
                            "reporting_year_start": company.reporting_year_start,
                            "reporting_year_end": company.reporting_year_end,
                            "turnover": company.turnover,
                        },
                        materiality_inputs=materiality_inputs,
                        bundle_version=payload.bundle_version,
                        retrieval_params=retrieval_params,
                        prompt_hash=prompt_hash,
                        compiler_mode=run.compiler_mode,
                        registry_checksums=registry_checksums,
                    ),
                    compute_assessments=_compute_assessments,
                )
            if cache_hit and computed_assessments is None:
                computed_assessments = _materialize_assessments_from_cache(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    output_json=output_json,
                )
            assessment_count = len(json.loads(output_json))

            persist_run_manifest(
                db,
                payload=RunManifestPayload(
                    run_id=run.id,
                    regulatory_plan_id=persisted_plan.plan_id,
                    tenant_id=run.tenant_id,
                    company_id=run.company_id,
                    bundle_id=payload.bundle_id,
                    bundle_version=payload.bundle_version,
                    retrieval_params=retrieval_params,
                    model_name=extraction_client.model_name,
                    prompt_hash=prompt_hash,
                    regulatory_registry_version={
                        "selected_bundles": regulatory_plan_result.plan["selected_bundles"]
                    },
                    regulatory_compiler_version=regulatory_plan_result.plan["compiler_version"],
                    regulatory_plan_json=regulatory_plan_result.plan,
                    regulatory_plan_hash=regulatory_plan_result.plan_hash,
                    git_sha=settings.git_sha,
                ),
                assessments=computed_assessments or [],
            )
            if settings.feature_registry_compiler and run.compiler_mode == "registry":
                compiled_plan = compile_from_db(
                    db,
                    bundle_id=payload.bundle_id,
                    version=payload.bundle_version,
                    context={
                        "company": {
                            "employees": company.employees,
                            "listed_status": company.listed_status,
                            "reporting_year": company.reporting_year,
                            "reporting_year_start": company.reporting_year_start,
                            "reporting_year_end": company.reporting_year_end,
                            "turnover": company.turnover,
                        }
                    },
                )
                run_assessments = computed_assessments
                if run_assessments is None:
                    run_assessments = db.scalars(
                        select(DatapointAssessment)
                        .where(
                            DatapointAssessment.run_id == run.id,
                            DatapointAssessment.tenant_id == run.tenant_id,
                        )
                        .order_by(DatapointAssessment.datapoint_key)
                    ).all()
                persist_registry_outputs_for_run(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    compiled_plan=compiled_plan,
                    assessments=run_assessments,
                )
            persist_obligation_coverage(
                db,
                compiled_plan_id=persisted_plan.plan_id,
                run_id=run.id,
                tenant_id=run.tenant_id,
            )
            diag_rows = db.scalars(
                select(ExtractionDiagnostics).where(
                    ExtractionDiagnostics.run_id == run.id,
                    ExtractionDiagnostics.tenant_id == run.tenant_id,
                )
            ).all()
            run_assessments_for_quality = computed_assessments
            if run_assessments_for_quality is None:
                run_assessments_for_quality = db.scalars(
                    select(DatapointAssessment)
                    .where(
                        DatapointAssessment.run_id == run.id,
                        DatapointAssessment.tenant_id == run.tenant_id,
                    )
                    .order_by(DatapointAssessment.datapoint_key)
                ).all()
            failure_count = 0
            for row in diag_rows:
                payload_json = (
                    row.diagnostics_json if isinstance(row.diagnostics_json, dict) else {}
                )
                if payload_json.get("failure_reason_code"):
                    failure_count += 1
            integrity_warning = False
            if diag_rows:
                failure_ratio = failure_count / len(diag_rows)
                if failure_ratio > settings.integrity_warning_failure_threshold:
                    integrity_warning = True
            if integrity_warning:
                append_run_event(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    event_type="run.execution.integrity_warning",
                    payload={
                        "tenant_id": run.tenant_id,
                        "failure_count": failure_count,
                        "diagnostics_count": len(diag_rows),
                    },
                )
            quality_decision, quality_metrics = _evaluate_quality_gate(
                db=db,
                run=run,
                bundle_id=payload.bundle_id,
                bundle_version=payload.bundle_version,
                required_datapoint_universe=required_datapoint_universe,
                company_document_ids=company_document_ids,
                chunk_count=chunk_count,
                assessment_count=assessment_count,
                assessments=run_assessments_for_quality,
                diagnostics_rows=diag_rows,
            )
            append_run_event(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                event_type="run.execution.quality_gated",
                payload={
                    "tenant_id": run.tenant_id,
                    "decision": quality_decision.as_payload(),
                    "metrics": {
                        "docs_discovered": quality_metrics.docs_discovered,
                        "docs_ingested": quality_metrics.docs_ingested,
                        "chunks_indexed": quality_metrics.chunks_indexed,
                        "required_narrative_section_count": (
                            quality_metrics.required_narrative_section_count
                        ),
                        "required_narrative_chunk_not_found_count": (
                            quality_metrics.required_narrative_chunk_not_found_count
                        ),
                        "chunk_not_found_count": quality_metrics.chunk_not_found_count,
                        "assessment_count": quality_metrics.assessment_count,
                        "evidence_hits_total": quality_metrics.evidence_hits_total,
                        "min_evidence_hits_in_required_section": (
                            quality_metrics.min_evidence_hits_in_required_section
                        ),
                    },
                },
            )
            run.status = quality_decision.final_status
            completion_payload = {
                "tenant_id": run.tenant_id,
                "assessment_count": assessment_count,
                "cache_hit": cache_hit,
                "research_provider": payload.research_provider,
                "final_status": quality_decision.final_status,
                "quality_gate_passed": quality_decision.passed,
                "quality_gate_failures": quality_decision.failures,
                "quality_gate_warnings": quality_decision.warnings,
            }
            if quality_decision.final_status == TERMINAL_STATUS_FAILED_PIPELINE:
                append_run_event(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    event_type="run.execution.failed",
                    payload={
                        **completion_payload,
                        "error": "run_quality_gate_failed",
                        "failure_category": "quality_gate_failed",
                        "retryable": False,
                    },
                )
                log_structured_event(
                    "run.execution.failed",
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    error="run_quality_gate_failed",
                    failure_category="quality_gate_failed",
                    retryable=False,
                    final_status=quality_decision.final_status,
                )
            else:
                append_run_event(
                    db,
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    event_type="run.execution.completed",
                    payload=completion_payload,
                )
                log_structured_event(
                    "run.execution.completed",
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    assessment_count=assessment_count,
                    cache_hit=cache_hit,
                    research_provider=payload.research_provider,
                    final_status=quality_decision.final_status,
                    quality_gate_passed=quality_decision.passed,
                )
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive worker path
            failure_category, retryable = _classify_failure(exc)
            run.status = TERMINAL_STATUS_FAILED_PIPELINE
            append_run_event(
                db,
                run_id=run.id,
                tenant_id=run.tenant_id,
                event_type="run.execution.failed",
                payload={
                    "tenant_id": run.tenant_id,
                    "error": str(exc),
                    "failure_category": failure_category,
                    "retryable": retryable,
                },
            )
            log_structured_event(
                "run.execution.failed",
                run_id=run.id,
                tenant_id=run.tenant_id,
                error=str(exc),
                failure_category=failure_category,
                retryable=retryable,
            )
            db.commit()


def enqueue_run_execution(run_id: int, payload: RunExecutionPayload) -> None:
    thread = threading.Thread(
        target=_process_run_execution,
        args=(run_id, payload),
        daemon=True,
        name=f"run-exec-{run_id}",
    )
    thread.start()


def current_assessment_count(db: Session, *, run_id: int, tenant_id: str) -> int:
    return _assessment_count(db, run_id=run_id, tenant_id=tenant_id)

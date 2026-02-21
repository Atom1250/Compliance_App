"""Deterministic regulatory compiler service (company -> applicable obligations plan)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.regulatory.canonical import sha256_checksum
from app.regulatory.compiler import compile_bundle
from app.regulatory.schema import Obligation
from app.regulatory.schema import RegulatoryBundle as RegulatoryBundleSchema
from apps.api.app.db.models import Company, RegulatoryBundle
from apps.api.app.services.regulatory_registry import list_bundles

COMPILER_VERSION = "reg-compiler-v1"


@dataclass(frozen=True)
class CompiledRegulatoryPlanResult:
    plan: dict[str, Any]
    plan_hash: str


def _decode_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return sorted(str(item) for item in payload if str(item).strip())


def _selected_regimes(company: Company, jurisdictions: list[str]) -> list[str]:
    configured = _decode_json_list(company.regulatory_regimes)
    if configured:
        return configured
    if "EU" in jurisdictions:
        return ["CSRD_ESRS"]
    return []


def _selected_jurisdictions(company: Company) -> list[str]:
    configured = _decode_json_list(company.regulatory_jurisdictions)
    if configured:
        return configured
    return ["EU"]


def _version_sort_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for token in version.replace("-", ".").split("."):
        if token.isdigit():
            parts.append(int(token))
        else:
            parts.append(0)
    return tuple(parts)


def _pick_latest_bundles(
    rows: list[RegulatoryBundle], *, regimes: list[str], jurisdictions: list[str]
) -> list[RegulatoryBundle]:
    filtered = [
        row
        for row in rows
        if row.regime in regimes
        and (row.jurisdiction in jurisdictions or row.jurisdiction == "GLOBAL")
    ]
    grouped: dict[tuple[str, str], list[RegulatoryBundle]] = {}
    for row in filtered:
        grouped.setdefault((row.regime, row.bundle_id), []).append(row)
    selected: list[RegulatoryBundle] = []
    for key in sorted(grouped):
        candidates = sorted(
            grouped[key],
            key=lambda item: _version_sort_key(item.version),
            reverse=True,
        )
        selected.append(candidates[0])
    return selected


def _compile_overlay_obligation(
    obligation: Obligation, *, context: dict[str, Any]
) -> dict[str, Any] | None:
    overlay_bundle = RegulatoryBundleSchema(
        bundle_id="overlay",
        version="v1",
        jurisdiction="GLOBAL",
        regime="OVERLAY",
        obligations=[obligation],
    )
    compiled = compile_bundle(overlay_bundle, context=context)
    if not compiled.obligations:
        return None
    row = compiled.obligations[0]
    return {
        "id": row.obligation_id,
        "standard_reference": row.standard_reference,
        "disclosure_reference": row.disclosure_reference,
        "elements": [
            {"element_id": item.element_id, "label": item.label, "required": item.required}
            for item in row.elements
        ],
        "phase_in_applied": False,
        "source_record_ids": sorted(set(row.source_record_ids)),
    }


def compile_company_regulatory_plan(
    db,
    *,
    company: Company,
) -> CompiledRegulatoryPlanResult:
    jurisdictions = _selected_jurisdictions(company)
    regimes = _selected_regimes(company, jurisdictions)
    context = {
        "company": {
            "employees": company.employees,
            "turnover": company.turnover,
            "listed_status": company.listed_status,
            "reporting_year": company.reporting_year,
            "reporting_year_start": company.reporting_year_start,
            "reporting_year_end": company.reporting_year_end,
        },
        "jurisdictions": jurisdictions,
        "regimes": regimes,
        "reporting_period": {
            "start": company.reporting_year_start,
            "end": company.reporting_year_end,
        },
    }

    bundle_rows = list_bundles(db)
    selected_bundles = _pick_latest_bundles(
        bundle_rows,
        regimes=regimes,
        jurisdictions=jurisdictions,
    )

    applied: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []

    for row in selected_bundles:
        bundle = RegulatoryBundleSchema.model_validate(row.payload)
        compiled = compile_bundle(bundle, context=context)
        applied_ids = {item.obligation_id for item in compiled.obligations}
        for original in sorted(bundle.obligations, key=lambda item: item.obligation_id):
            if original.obligation_id not in applied_ids:
                excluded.append(
                    {"id": original.obligation_id, "reason": "applies_if_false_or_phase_in"}
                )
        for item in compiled.obligations:
            applied.append(
                {
                    "id": item.obligation_id,
                    "standard_reference": item.standard_reference,
                    "disclosure_reference": item.disclosure_reference,
                    "elements": [
                        {"element_id": el.element_id, "label": el.label, "required": el.required}
                        for el in item.elements
                    ],
                    "phase_in_applied": False,
                    "source_record_ids": sorted(
                        set(item.source_record_ids or bundle.source_record_ids)
                    ),
                }
            )

        for overlay in bundle.overlays:
            if overlay.jurisdiction not in jurisdictions:
                continue
            for obligation_id in overlay.obligations_disable:
                before = len(applied)
                applied = [item for item in applied if item["id"] != obligation_id]
                if len(applied) != before:
                    excluded.append(
                        {"id": obligation_id, "reason": f"overlay_disabled:{overlay.overlay_id}"}
                    )
            for patch in overlay.obligations_modify:
                target = str(patch.get("obligation_id", ""))
                if not target:
                    continue
                for item in applied:
                    if item["id"] != target:
                        continue
                    if "disclosure_reference" in patch:
                        item["disclosure_reference"] = str(patch["disclosure_reference"])
                    if "standard_reference" in patch:
                        item["standard_reference"] = str(patch["standard_reference"])
            for overlay_obligation in overlay.obligations_add:
                compiled_overlay = _compile_overlay_obligation(overlay_obligation, context=context)
                if compiled_overlay is not None:
                    applied.append(compiled_overlay)

    applied = sorted(applied, key=lambda item: item["id"])
    excluded = sorted(excluded, key=lambda item: item["id"])

    plan = {
        "compiler_version": COMPILER_VERSION,
        "selected_bundles": [
            {
                "regime": row.regime,
                "bundle_id": row.bundle_id,
                "version": row.version,
                "checksum": row.checksum,
            }
            for row in sorted(
                selected_bundles,
                key=lambda item: (item.regime, item.bundle_id, item.version),
            )
        ],
        "jurisdictions": jurisdictions,
        "regimes": regimes,
        "obligations_applied": applied,
        "obligations_excluded": excluded,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    plan_hash_payload = dict(plan)
    plan_hash_payload.pop("generated_at", None)
    plan_hash = sha256_checksum(plan_hash_payload)
    return CompiledRegulatoryPlanResult(plan=plan, plan_hash=plan_hash)

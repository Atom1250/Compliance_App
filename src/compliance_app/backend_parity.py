"""Dual-backend parity helpers for deterministic migration validation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParityComparison:
    is_equal: bool
    mismatches: list[str]
    sqlite: dict[str, object]
    postgres: dict[str, object]


def normalize_sqlite_summary(summary: dict[str, object]) -> dict[str, object]:
    scenario_results = summary.get("scenario_results")
    if not isinstance(scenario_results, list):
        raise ValueError("sqlite summary missing scenario_results")
    primary = next(
        (item for item in scenario_results if item.get("id") == "local_deterministic_success"),
        None,
    )
    if primary is None:
        raise ValueError("sqlite summary missing local_deterministic_success scenario")

    manifest = summary.get("manifest")
    evidence_pack = summary.get("evidence_pack")
    if not isinstance(manifest, dict) or not isinstance(evidence_pack, dict):
        raise ValueError("sqlite summary missing manifest/evidence_pack")

    return {
        "terminal_status": summary["flow"]["terminal_status"],
        "manifest": {
            "bundle_id": manifest["bundle_id"],
            "bundle_version": manifest["bundle_version"],
            "retrieval_policy_version": manifest["retrieval_policy_version"],
            "retrieval_top_k": manifest["retrieval_top_k"],
        },
        "export": {
            "report_ready": primary["report_ready"],
            "evidence_pack_ready": primary["evidence_pack_ready"],
            "blocking_reasons": primary["blocking_reasons"],
        },
        "contracts": {
            "report_status_code": primary["report_status_code"],
            "evidence_preview_status_code": primary["evidence_preview_status_code"],
        },
        "evidence_metadata": {"file_count": evidence_pack["manifest_file_count"]},
    }


def normalize_postgres_summary(summary: dict[str, object]) -> dict[str, object]:
    return {
        "terminal_status": summary["terminal_status"],
        "manifest": {
            "bundle_id": summary["bundle_id"],
            "bundle_version": summary["bundle_version"],
            "retrieval_policy_version": summary["retrieval_policy_version"],
            "retrieval_top_k": summary["retrieval_top_k"],
        },
        "export": {
            "report_ready": summary["report_ready"],
            "evidence_pack_ready": summary["evidence_pack_ready"],
            "blocking_reasons": summary["blocking_reasons"],
        },
        "contracts": {
            "report_status_code": summary["report_status_code"],
            "evidence_preview_status_code": summary["evidence_preview_status_code"],
        },
        "evidence_metadata": {"file_count": summary["evidence_file_count"]},
    }


def compare_backend_parity(
    *, sqlite_summary: dict[str, object], postgres_summary: dict[str, object]
) -> ParityComparison:
    sqlite_normalized = normalize_sqlite_summary(sqlite_summary)
    postgres_normalized = normalize_postgres_summary(postgres_summary)

    mismatches: list[str] = []
    for key in sqlite_normalized:
        if sqlite_normalized[key] != postgres_normalized.get(key):
            mismatches.append(key)

    return ParityComparison(
        is_equal=not mismatches,
        mismatches=mismatches,
        sqlite=sqlite_normalized,
        postgres=postgres_normalized,
    )

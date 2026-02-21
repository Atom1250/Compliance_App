"""Run quality gate evaluation for deterministic terminal status selection."""

from __future__ import annotations

from dataclasses import dataclass

TERMINAL_STATUS_COMPLETED = "completed"
TERMINAL_STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
TERMINAL_STATUS_DEGRADED_NO_EVIDENCE = "degraded_no_evidence"
TERMINAL_STATUS_FAILED_PIPELINE = "failed_pipeline"


@dataclass(frozen=True)
class RunQualityGateConfig:
    min_docs_discovered: int
    min_docs_ingested: int
    min_chunks_indexed: int
    max_chunk_not_found_rate: float
    min_evidence_hits: int
    min_evidence_hits_per_section: int
    fail_on_required_narrative_chunk_not_found: bool
    pipeline_failure_status: str
    evidence_failure_status: str


@dataclass(frozen=True)
class RunQualityMetrics:
    docs_discovered: int
    docs_ingested: int
    chunks_indexed: int
    required_narrative_section_count: int
    required_narrative_chunk_not_found_count: int
    chunk_not_found_count: int
    assessment_count: int
    evidence_hits_total: int
    min_evidence_hits_in_required_section: int


@dataclass(frozen=True)
class RunQualityGateDecision:
    final_status: str
    passed: bool
    failures: list[str]
    warnings: list[str]

    def as_payload(self) -> dict[str, object]:
        return {
            "final_status": self.final_status,
            "passed": self.passed,
            "failures": self.failures,
            "warnings": self.warnings,
        }


def _chunk_not_found_rate(metrics: RunQualityMetrics) -> float:
    if metrics.assessment_count <= 0:
        return 0.0
    return metrics.chunk_not_found_count / metrics.assessment_count


def evaluate_run_quality_gate(
    *,
    config: RunQualityGateConfig,
    metrics: RunQualityMetrics,
) -> RunQualityGateDecision:
    failures: list[str] = []
    warnings: list[str] = []
    pipeline_failures: list[str] = []
    evidence_failures: list[str] = []

    if metrics.docs_discovered < config.min_docs_discovered:
        pipeline_failures.append(
            f"docs_discovered_below_min:{metrics.docs_discovered}<{config.min_docs_discovered}"
        )
    if metrics.docs_ingested < config.min_docs_ingested:
        pipeline_failures.append(
            f"docs_ingested_below_min:{metrics.docs_ingested}<{config.min_docs_ingested}"
        )
    if metrics.chunks_indexed < config.min_chunks_indexed:
        pipeline_failures.append(
            f"chunks_indexed_below_min:{metrics.chunks_indexed}<{config.min_chunks_indexed}"
        )

    chunk_not_found_rate = _chunk_not_found_rate(metrics)
    if chunk_not_found_rate > config.max_chunk_not_found_rate:
        evidence_failures.append(
            
                "chunk_not_found_rate_above_max:"
                f"{chunk_not_found_rate:.6f}>{config.max_chunk_not_found_rate:.6f}"
            
        )
    if (
        config.fail_on_required_narrative_chunk_not_found
        and metrics.required_narrative_chunk_not_found_count > 0
    ):
        evidence_failures.append(
            "required_narrative_chunk_not_found:"
            f"{metrics.required_narrative_chunk_not_found_count}"
        )
    if metrics.evidence_hits_total < config.min_evidence_hits:
        evidence_failures.append(
            f"evidence_hits_below_min:{metrics.evidence_hits_total}<{config.min_evidence_hits}"
        )
    if (
        metrics.required_narrative_section_count > 0
        and metrics.min_evidence_hits_in_required_section < config.min_evidence_hits_per_section
    ):
        evidence_failures.append(
            "required_section_evidence_hits_below_min:"
            f"{metrics.min_evidence_hits_in_required_section}"
            f"<{config.min_evidence_hits_per_section}"
        )

    if pipeline_failures:
        failures.extend(pipeline_failures)
        final_status = config.pipeline_failure_status
        return RunQualityGateDecision(
            final_status=final_status,
            passed=False,
            failures=sorted(failures),
            warnings=warnings,
        )

    if evidence_failures:
        failures.extend(evidence_failures)
        final_status = config.evidence_failure_status
        return RunQualityGateDecision(
            final_status=final_status,
            passed=False,
            failures=sorted(failures),
            warnings=warnings,
        )

    if warnings:
        return RunQualityGateDecision(
            final_status=TERMINAL_STATUS_COMPLETED_WITH_WARNINGS,
            passed=True,
            failures=[],
            warnings=sorted(warnings),
        )
    return RunQualityGateDecision(
        final_status=TERMINAL_STATUS_COMPLETED,
        passed=True,
        failures=[],
        warnings=[],
    )

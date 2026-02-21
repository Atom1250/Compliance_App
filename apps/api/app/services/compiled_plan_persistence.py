"""Relational persistence for compiled regulatory plans and obligation coverage."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.api.app.db.models import (
    CompiledObligation,
    CompiledPlan,
    DatapointAssessment,
    ObligationCoverage,
)


@dataclass(frozen=True)
class PersistedCompiledPlan:
    plan_id: int
    obligations_count: int
    cohort: str


def _cohort_from_company(*, listed_status: bool | None, reporting_year: int | None) -> str:
    if listed_status:
        return "phase_1"
    if reporting_year is not None and reporting_year <= 2025:
        return "phase_2"
    return "phase_3"


def persist_compiled_plan(
    db: Session,
    *,
    company_id: int,
    reporting_year: int | None,
    jurisdictions: list[str],
    regimes: list[str],
    plan: dict,
) -> PersistedCompiledPlan:
    cohort = _cohort_from_company(listed_status=None, reporting_year=reporting_year)
    record = CompiledPlan(
        entity_id=company_id,
        reporting_year=reporting_year,
        regime=",".join(regimes) if regimes else "CSRD",
        cohort=cohort,
        phase_in_flags={
            "jurisdictions": sorted(jurisdictions),
            "regimes": sorted(regimes),
        },
    )
    db.add(record)
    db.flush()

    obligations = plan.get("obligations_applied", [])
    for item in obligations:
        db.add(
            CompiledObligation(
                compiled_plan_id=record.id,
                obligation_code=str(item.get("id", "")),
                mandatory=True,
                jurisdiction=(jurisdictions[0] if jurisdictions else "EU"),
            )
        )
    db.flush()
    return PersistedCompiledPlan(
        plan_id=record.id,
        obligations_count=len(obligations),
        cohort=cohort,
    )


def persist_obligation_coverage(
    db: Session,
    *,
    compiled_plan_id: int,
    run_id: int,
    tenant_id: str,
) -> int:
    obligations = db.scalars(
        select(CompiledObligation)
        .where(CompiledObligation.compiled_plan_id == compiled_plan_id)
        .order_by(CompiledObligation.obligation_code)
    ).all()

    db.execute(
        delete(ObligationCoverage).where(ObligationCoverage.compiled_plan_id == compiled_plan_id)
    )

    count = 0
    for obligation in obligations:
        matched = db.scalars(
            select(DatapointAssessment)
            .where(
                DatapointAssessment.run_id == run_id,
                DatapointAssessment.tenant_id == tenant_id,
            )
            .where(
                (DatapointAssessment.datapoint_key == obligation.obligation_code)
                | DatapointAssessment.datapoint_key.startswith(f"{obligation.obligation_code}::")
            )
            .order_by(DatapointAssessment.datapoint_key)
        ).all()

        present = sum(1 for item in matched if item.status == "Present")
        partial = sum(1 for item in matched if item.status == "Partial")
        absent = sum(1 for item in matched if item.status == "Absent")
        na = sum(1 for item in matched if item.status == "NA")

        if matched and present == len(matched):
            status = "Full"
            full_count = len(matched)
        elif present + partial > 0:
            status = "Partial"
            full_count = 0
        else:
            status = "Absent"
            full_count = 0

        db.add(
            ObligationCoverage(
                compiled_plan_id=compiled_plan_id,
                obligation_code=obligation.obligation_code,
                coverage_status=status,
                full_count=full_count,
                partial_count=partial,
                absent_count=absent if matched else 1,
                na_count=na,
            )
        )
        count += 1

    db.flush()
    return count

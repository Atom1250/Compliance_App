"""Deterministic requirements bundle version routing."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import Company, RequirementBundle

AUTO_SELECTOR = "auto"
DEFAULT_REQUIREMENTS_BUNDLE_ID = "esrs_mini"


@dataclass(frozen=True)
class ResolvedBundleSelection:
    bundle_id: str
    bundle_version: str


def resolve_bundle_selection(
    db: Session,
    *,
    company_id: int,
    requested_bundle_id: str | None,
    requested_bundle_version: str | None,
) -> ResolvedBundleSelection:
    explicit_id = requested_bundle_id and requested_bundle_id != AUTO_SELECTOR
    explicit_version = requested_bundle_version and requested_bundle_version != AUTO_SELECTOR

    bundle_id = requested_bundle_id if explicit_id else DEFAULT_REQUIREMENTS_BUNDLE_ID
    assert bundle_id is not None  # for type checkers

    if explicit_id and explicit_version:
        return ResolvedBundleSelection(bundle_id=bundle_id, bundle_version=requested_bundle_version)

    versions = db.scalars(
        select(RequirementBundle.version)
        .where(RequirementBundle.bundle_id == bundle_id)
        .order_by(RequirementBundle.version)
    ).all()
    unique_versions = sorted(set(versions))
    if not unique_versions:
        raise ValueError(f"Bundle not found: {bundle_id}")

    if explicit_version:
        if requested_bundle_version not in unique_versions:
            raise ValueError(f"Bundle not found: {bundle_id}@{requested_bundle_version}")
        return ResolvedBundleSelection(bundle_id=bundle_id, bundle_version=requested_bundle_version)

    company = db.get(Company, company_id)
    if company is None:
        raise ValueError(f"Company not found: {company_id}")

    routing_year = (
        company.reporting_year_end
        if company.reporting_year_end is not None
        else company.reporting_year
        if company.reporting_year is not None
        else company.reporting_year_start
    )
    if bundle_id == "esrs_mini" and routing_year is not None:
        preferred = "2024.01" if routing_year < 2026 else "2026.01"
        if preferred in unique_versions:
            return ResolvedBundleSelection(bundle_id=bundle_id, bundle_version=preferred)

    return ResolvedBundleSelection(bundle_id=bundle_id, bundle_version=unique_versions[-1])


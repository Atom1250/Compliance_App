"""Requirements bundle importer."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.requirements.schema import RequirementsBundle
from apps.api.app.db.models import ApplicabilityRule, DatapointDefinition, RequirementBundle


def load_bundle(bundle_path: Path) -> RequirementsBundle:
    """Load and validate bundle JSON from disk."""
    payload = json.loads(bundle_path.read_text())
    return RequirementsBundle.model_validate(payload)


def import_bundle(db: Session, bundle: RequirementsBundle) -> RequirementBundle:
    """Import requirements bundle idempotently into DB."""
    existing_bundle = db.scalar(
        select(RequirementBundle).where(
            RequirementBundle.bundle_id == bundle.bundle_id,
            RequirementBundle.version == bundle.version,
        )
    )
    if existing_bundle is not None:
        return existing_bundle

    requirement_bundle = RequirementBundle(
        bundle_id=bundle.bundle_id,
        version=bundle.version,
        standard=bundle.standard,
    )
    db.add(requirement_bundle)
    db.flush()

    for datapoint in bundle.datapoints:
        db.add(
            DatapointDefinition(
                requirement_bundle_id=requirement_bundle.id,
                datapoint_key=datapoint.datapoint_key,
                title=datapoint.title,
                disclosure_reference=datapoint.disclosure_reference,
            )
        )

    for rule in bundle.applicability_rules:
        db.add(
            ApplicabilityRule(
                requirement_bundle_id=requirement_bundle.id,
                rule_id=rule.rule_id,
                datapoint_key=rule.datapoint_key,
                expression=rule.expression,
            )
        )

    db.commit()
    db.refresh(requirement_bundle)
    return requirement_bundle

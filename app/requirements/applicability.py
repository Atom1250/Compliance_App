"""Deterministic applicability engine for requirements datapoints."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.db.models import (
    ApplicabilityRule,
    Company,
    DatapointDefinition,
    RequirementBundle,
    RunMateriality,
)


@dataclass(frozen=True)
class CompanyProfile:
    employees: int | None
    turnover: float | None
    listed_status: bool | None
    reporting_year: int | None


_ALLOWED_COMPARE_OPS = (ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE)
_ALLOWED_BOOL_OPS = (ast.And, ast.Or)
_ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_ALLOWED_FIELDS = {"employees", "turnover", "listed_status", "reporting_year"}


def _safe_eval(node: ast.AST, profile: CompanyProfile):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, profile)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id == "company":
            return profile
        raise ValueError(f"Unsupported name: {node.id}")

    if isinstance(node, ast.Attribute):
        value = _safe_eval(node.value, profile)
        if isinstance(value, CompanyProfile) and node.attr in _ALLOWED_FIELDS:
            return getattr(value, node.attr)
        raise ValueError(f"Unsupported attribute access: {node.attr}")

    if isinstance(node, ast.BoolOp) and isinstance(node.op, _ALLOWED_BOOL_OPS):
        values = [_safe_eval(value, profile) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, profile)

    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BIN_OPS):
        left = _safe_eval(node.left, profile)
        right = _safe_eval(node.right, profile)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right

    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, profile)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = _safe_eval(comparator, profile)
            if not isinstance(op, _ALLOWED_COMPARE_OPS):
                raise ValueError("Unsupported comparison operator")
            if isinstance(op, ast.Eq) and not (left == right):
                return False
            if isinstance(op, ast.NotEq) and not (left != right):
                return False
            if isinstance(op, ast.Gt) and not (left > right):
                return False
            if isinstance(op, ast.GtE) and not (left >= right):
                return False
            if isinstance(op, ast.Lt) and not (left < right):
                return False
            if isinstance(op, ast.LtE) and not (left <= right):
                return False
            left = right
        return True

    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_rule(expression: str, profile: CompanyProfile) -> bool:
    """Evaluate one applicability rule deterministically."""
    parsed = ast.parse(expression, mode="eval")
    return bool(_safe_eval(parsed, profile))


def resolve_required_datapoint_ids(
    db: Session,
    *,
    company_id: int,
    bundle_id: str,
    bundle_version: str,
    run_id: int | None = None,
) -> list[str]:
    """Return deterministically ordered required datapoint IDs."""
    company = db.get(Company, company_id)
    if company is None:
        raise ValueError(f"Company not found: {company_id}")

    bundle = db.scalar(
        select(RequirementBundle).where(
            RequirementBundle.bundle_id == bundle_id,
            RequirementBundle.version == bundle_version,
        )
    )
    if bundle is None:
        raise ValueError(f"Bundle not found: {bundle_id}@{bundle_version}")

    profile = CompanyProfile(
        employees=company.employees,
        turnover=company.turnover,
        listed_status=company.listed_status,
        reporting_year=company.reporting_year,
    )

    rules = db.scalars(
        select(ApplicabilityRule)
        .where(ApplicabilityRule.requirement_bundle_id == bundle.id)
        .order_by(ApplicabilityRule.rule_id, ApplicabilityRule.datapoint_key)
    ).all()

    datapoint_topics = {
        row.datapoint_key: row.materiality_topic
        for row in db.scalars(
            select(DatapointDefinition)
            .where(DatapointDefinition.requirement_bundle_id == bundle.id)
            .order_by(DatapointDefinition.datapoint_key)
        ).all()
    }

    materiality_by_topic: dict[str, bool] = {}
    if run_id is not None:
        for row in db.scalars(
            select(RunMateriality)
            .where(RunMateriality.run_id == run_id)
            .order_by(RunMateriality.topic)
        ).all():
            materiality_by_topic[row.topic] = row.is_material

    required: list[str] = []
    for rule in rules:
        if not evaluate_rule(rule.expression, profile):
            continue

        topic = datapoint_topics.get(rule.datapoint_key, "general")
        if topic in materiality_by_topic and not materiality_by_topic[topic]:
            continue

        required.append(rule.datapoint_key)

    return sorted(set(required))

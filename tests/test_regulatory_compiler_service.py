from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company
from apps.api.app.services.regulatory_compiler import compile_company_regulatory_plan
from apps.api.app.services.regulatory_registry import sync_from_filesystem


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "regulatory_compiler_service.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_compiler_applies_expected_obligations_for_eu_company(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"), mode="sync")
        company = Company(
            name="In Scope EU",
            tenant_id="default",
            listed_status=True,
            reporting_year=2026,
            reporting_year_start=2025,
            reporting_year_end=2026,
            regulatory_jurisdictions='["EU"]',
            regulatory_regimes='["CSRD_ESRS"]',
        )
        session.add(company)
        session.commit()
        session.refresh(company)

        result = compile_company_regulatory_plan(session, company=company)

    applied_ids = [item["id"] for item in result.plan["obligations_applied"]]
    assert applied_ids == sorted(applied_ids)
    assert "ESRS-E1-1" in applied_ids
    assert "ESRS-E1-6" in applied_ids
    assert len(result.plan_hash) == 64


def test_compiler_applies_no_company_regime_by_default_when_no_eu(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"), mode="sync")
        company = Company(
            name="Out Scope",
            tenant_id="default",
            listed_status=False,
            reporting_year=2024,
            reporting_year_start=2023,
            reporting_year_end=2024,
            regulatory_jurisdictions='["US"]',
            regulatory_regimes="[]",
        )
        session.add(company)
        session.commit()
        session.refresh(company)

        result = compile_company_regulatory_plan(session, company=company)

    assert result.plan["regimes"] == []
    assert result.plan["obligations_applied"] == []


def test_compiler_overlay_for_no_jurisdiction_is_applied(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        sync_from_filesystem(session, bundles_root=Path("app/regulatory/bundles"), mode="sync")
        company = Company(
            name="Norway Scope",
            tenant_id="default",
            listed_status=True,
            reporting_year=2026,
            reporting_year_start=2025,
            reporting_year_end=2026,
            regulatory_jurisdictions='["EU","NO"]',
            regulatory_regimes='["CSRD_ESRS"]',
        )
        session.add(company)
        session.commit()
        session.refresh(company)

        result = compile_company_regulatory_plan(session, company=company)

    applied_ids = {item["id"] for item in result.plan["obligations_applied"]}
    assert "NO-TRANSPARENCY-STATEMENT-1" in applied_ids

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import (
    Company,
    RegulatoryBundle,
    RegulatorySourceDocument,
    Run,
    RunManifest,
)
from apps.api.main import app

AUTH_DEFAULT = {"X-API-Key": "dev-key", "X-Tenant-ID": "default"}


def _prepare_db(tmp_path: Path) -> str:
    db_path = tmp_path / "regulatory_context_api.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    return db_url


def test_regulatory_context_endpoints_return_200(monkeypatch, tmp_path: Path) -> None:
    db_url = _prepare_db(tmp_path)
    monkeypatch.setenv("COMPLIANCE_APP_DATABASE_URL", db_url)

    from apps.api.app.core.config import get_settings

    get_settings.cache_clear()
    engine = create_engine(db_url)
    with Session(engine) as session:
        company = Company(name="Reg Context Co", tenant_id="default")
        session.add(company)
        session.flush()
        run = Run(company_id=company.id, tenant_id="default", status="completed")
        session.add(run)
        session.flush()
        session.add(
            RegulatorySourceDocument(
                record_id="EU-L1-CSRD",
                jurisdiction="EU",
                document_name="CSRD",
                row_checksum="a" * 64,
            )
        )
        session.add(
            RegulatoryBundle(
                regime="CSRD_ESRS",
                bundle_id="csrd_esrs_core",
                version="2026.02",
                checksum="b" * 64,
                jurisdiction="EU",
                payload={
                    "bundle_id": "csrd_esrs_core",
                    "version": "2026.02",
                    "jurisdiction": "EU",
                    "regime": "CSRD_ESRS",
                    "obligations": [],
                },
                source_record_ids=[],
                status="active",
            )
        )
        session.add(
            RunManifest(
                run_id=run.id,
                tenant_id="default",
                document_hashes="[]",
                bundle_id="csrd_esrs_core",
                bundle_version="2026.02",
                retrieval_params='{"query_mode":"hybrid"}',
                model_name="deterministic-local-v1",
                prompt_hash="c" * 64,
                report_template_version="gold_standard_v1",
                regulatory_registry_version='{"selected_bundles":[{"bundle_id":"csrd_esrs_core","version":"2026.02","checksum":"bbbb"}]}',
                regulatory_compiler_version="reg-compiler-v1",
                regulatory_plan_json='{"compiler_version":"reg-compiler-v1","obligations_applied":[]}',
                regulatory_plan_hash="d" * 64,
                git_sha="e" * 40,
            )
        )
        session.commit()
        run_id = run.id

    client = TestClient(app)
    sources = client.get("/regulatory/sources?jurisdiction=EU", headers=AUTH_DEFAULT)
    bundles = client.get("/regulatory/bundles?regime=CSRD_ESRS", headers=AUTH_DEFAULT)
    plan = client.get(f"/runs/{run_id}/regulatory-plan", headers=AUTH_DEFAULT)

    assert sources.status_code == 200
    assert bundles.status_code == 200
    assert plan.status_code == 200
    assert sources.json()[0]["record_id"] == "EU-L1-CSRD"
    assert bundles.json()[0]["bundle_id"] == "csrd_esrs_core"
    assert plan.json()["compiler_version"] == "reg-compiler-v1"

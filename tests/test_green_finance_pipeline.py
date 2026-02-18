import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.green_finance.pipeline import GreenFinanceRunConfig, execute_green_finance_pipeline
from app.requirements.importer import import_bundle, load_bundle
from apps.api.app.db.models import Chunk, Company, DatapointAssessment, Document, Run
from apps.api.app.services.llm_extraction import ExtractionClient


class MockTransport:
    def create_response(self, *, model, input_text, temperature, json_schema):
        if "GF-OBL-01" in input_text:
            payload = {
                "status": "Present",
                "value": "framework published",
                "evidence_chunk_ids": ["chunk-gf-1"],
                "rationale": "Obligation satisfied.",
            }
        else:
            payload = {
                "status": "Absent",
                "value": None,
                "evidence_chunk_ids": [],
                "rationale": "No evidence found.",
            }
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(payload)}],
                }
            ]
        }


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "green_finance_pipeline.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_green_finance_pipeline_reuses_assessment_engine_and_reports_matrix(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        import_bundle(
            session,
            load_bundle(Path("requirements/green_finance_icma_eugb/bundle.json")),
        )

        company = Company(
            name="GF Co",
            employees=300,
            turnover=50_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.flush()

        document = Document(company_id=company.id, title="Green bond framework")
        session.add(document)
        session.flush()
        session.add_all(
            [
                Chunk(
                    document_id=document.id,
                    chunk_id="chunk-gf-1",
                    page_number=1,
                    start_offset=0,
                    end_offset=64,
                    text="Use of proceeds framework and project categories are disclosed.",
                    content_tsv="use of proceeds framework project categories disclosed",
                ),
                Chunk(
                    document_id=document.id,
                    chunk_id="chunk-gf-2",
                    page_number=2,
                    start_offset=0,
                    end_offset=64,
                    text="No annual allocation report for bond proceeds was located.",
                    content_tsv="no annual allocation report located",
                ),
            ]
        )
        session.commit()

        assessments, matrix = execute_green_finance_pipeline(
            session,
            extraction_client=ExtractionClient(transport=MockTransport(), model="gpt-5"),
            config=GreenFinanceRunConfig(run_id=run.id, bundle_version="2026.01", enabled=True),
        )

        assert len(assessments) == 2
        persisted = session.scalars(
            select(DatapointAssessment).where(DatapointAssessment.run_id == run.id)
        ).all()
        assert len(persisted) == 2

        assert len(matrix) == 2
        assert matrix[0]["produced"] is True
        assert matrix[0]["evidence"] == ["chunk-gf-1"]
        assert matrix[1]["produced"] is False


def test_green_finance_pipeline_disabled_mode_returns_no_output(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        company = Company(name="GF Disabled")
        session.add(company)
        session.flush()
        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.commit()

        assessments, matrix = execute_green_finance_pipeline(
            session,
            extraction_client=ExtractionClient(transport=MockTransport(), model="gpt-5"),
            config=GreenFinanceRunConfig(run_id=run.id, bundle_version="2026.01", enabled=False),
        )
        assert assessments == []
        assert matrix == []

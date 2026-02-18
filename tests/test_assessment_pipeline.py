import hashlib
import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import (
    ApplicabilityRule,
    Chunk,
    Company,
    DatapointAssessment,
    DatapointDefinition,
    Document,
    RequirementBundle,
    Run,
)
from apps.api.app.services.assessment_pipeline import (
    AssessmentRunConfig,
    execute_assessment_pipeline,
)
from apps.api.app.services.llm_extraction import ExtractionClient


class MockTransport:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.payload = payload or {
            "status": "Present",
            "value": "42",
            "evidence_chunk_ids": ["chunk-evidence-1"],
            "rationale": "Value appears in cited chunk.",
        }

    def create_response(self, *, model, input_text, temperature, json_schema):
        self.calls.append(
            {
                "model": model,
                "input_text": input_text,
                "temperature": temperature,
                "json_schema": json_schema,
            }
        )
        return {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(self.payload)}],
                }
            ]
        }


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "assessment_pipeline.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_assessment_pipeline_stores_extraction_outputs_with_manifest_fields(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        company = Company(
            name="Assessment Co",
            employees=500,
            turnover=100_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.flush()

        bundle = RequirementBundle(bundle_id="esrs_mini", version="2026.01", standard="ESRS")
        session.add(bundle)
        session.flush()

        datapoint = DatapointDefinition(
            requirement_bundle_id=bundle.id,
            datapoint_key="ESRS-E1-6",
            title="Gross Scope 1 emissions",
            disclosure_reference="E1-6",
            materiality_topic="climate",
        )
        session.add(datapoint)
        session.flush()

        session.add(
            ApplicabilityRule(
                requirement_bundle_id=bundle.id,
                rule_id="rule-1",
                datapoint_key=datapoint.datapoint_key,
                expression="company.listed_status == True",
            )
        )

        document = Document(company_id=company.id, title="Annual report")
        session.add(document)
        session.flush()
        session.add(
            Chunk(
                document_id=document.id,
                chunk_id="chunk-evidence-1",
                page_number=1,
                start_offset=0,
                end_offset=64,
                text="Gross Scope 1 emissions are reported as 42 tCO2e.",
                content_tsv="gross scope 1 emissions reported 42",
            )
        )
        session.commit()

        transport = MockTransport()
        extraction_client = ExtractionClient(transport=transport, model="gpt-5")
        config = AssessmentRunConfig(
            run_id=run.id,
            bundle_id="esrs_mini",
            bundle_version="2026.01",
            retrieval_top_k=3,
            retrieval_model_name="default",
        )

        stored = execute_assessment_pipeline(
            session,
            extraction_client=extraction_client,
            config=config,
        )

        assert len(stored) == 1
        assessment = stored[0]
        assert assessment.run_id == run.id
        assert assessment.datapoint_key == "ESRS-E1-6"
        assert assessment.status == "Present"
        assert json.loads(assessment.evidence_chunk_ids) == ["chunk-evidence-1"]
        assert assessment.model_name == "gpt-5"
        assert json.loads(assessment.retrieval_params) == {
            "query_mode": "hybrid",
            "retrieval_model_name": "default",
            "top_k": 3,
        }

        prompt = extraction_client.build_prompt(
            datapoint_key="ESRS-E1-6",
            context_chunks=["Gross Scope 1 emissions are reported as 42 tCO2e."],
        )
        assert assessment.prompt_hash == hashlib.sha256(prompt.encode()).hexdigest()

        persisted = session.scalars(
            select(DatapointAssessment).where(DatapointAssessment.run_id == run.id)
        ).all()
        assert len(persisted) == 1
        assert transport.calls[0]["temperature"] == 0.0


def test_assessment_pipeline_applies_verification_downgrade(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        company = Company(
            name="Assessment Co",
            employees=500,
            turnover=100_000_000.0,
            listed_status=True,
            reporting_year=2026,
        )
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.flush()

        bundle = RequirementBundle(bundle_id="esrs_mini", version="2026.01", standard="ESRS")
        session.add(bundle)
        session.flush()

        datapoint = DatapointDefinition(
            requirement_bundle_id=bundle.id,
            datapoint_key="ESRS-E1-6",
            title="Gross Scope 1 emissions",
            disclosure_reference="E1-6",
            materiality_topic="climate",
        )
        session.add(datapoint)
        session.flush()

        session.add(
            ApplicabilityRule(
                requirement_bundle_id=bundle.id,
                rule_id="rule-1",
                datapoint_key=datapoint.datapoint_key,
                expression="company.listed_status == True",
            )
        )

        document = Document(company_id=company.id, title="Annual report")
        session.add(document)
        session.flush()
        session.add(
            Chunk(
                document_id=document.id,
                chunk_id="chunk-evidence-1",
                page_number=1,
                start_offset=0,
                end_offset=64,
                text="Gross Scope 1 emissions are reported as 42 tCO2e.",
                content_tsv="gross scope 1 emissions reported 42",
            )
        )
        session.commit()

        transport = MockTransport(
            payload={
                "status": "Present",
                "value": "99",
                "evidence_chunk_ids": ["chunk-evidence-1"],
                "rationale": "Value appears in cited chunk.",
            }
        )
        extraction_client = ExtractionClient(transport=transport, model="gpt-5")
        config = AssessmentRunConfig(
            run_id=run.id,
            bundle_id="esrs_mini",
            bundle_version="2026.01",
            retrieval_top_k=3,
            retrieval_model_name="default",
        )

        stored = execute_assessment_pipeline(
            session,
            extraction_client=extraction_client,
            config=config,
        )

        assert len(stored) == 1
        assessment = stored[0]
        assert assessment.status == "Partial"
        assert "Verification downgraded" in assessment.rationale

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from apps.api.app.db.models import Company, DatapointAssessment, Run
from apps.api.app.services.run_cache import (
    RunHashInput,
    compute_run_hash,
    get_or_compute_cached_output,
)


def _prepare_session(tmp_path: Path) -> Session:
    db_path = tmp_path / "run_cache.sqlite"
    db_url = f"sqlite:///{db_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(config, "head")
    engine = create_engine(db_url)
    return Session(engine, expire_on_commit=False)


def test_compute_run_hash_is_deterministic_and_changes_with_input() -> None:
    inputs_a = RunHashInput(
        tenant_id="default",
        document_hashes=["b", "a"],
        company_profile={"employees": 100, "listed_status": True, "reporting_year": 2026},
        materiality_inputs={"climate": True},
        bundle_version="2026.01",
        retrieval_params={"top_k": 5, "query_mode": "hybrid"},
        prompt_hash="prompt-abc",
    )
    inputs_b = RunHashInput(
        tenant_id="default",
        document_hashes=["a", "b"],
        company_profile={"employees": 100, "listed_status": True, "reporting_year": 2026},
        materiality_inputs={"climate": True},
        bundle_version="2026.01",
        retrieval_params={"query_mode": "hybrid", "top_k": 5},
        prompt_hash="prompt-abc",
    )
    inputs_c = RunHashInput(
        tenant_id="other",
        document_hashes=["a", "b"],
        company_profile={"employees": 101, "listed_status": True, "reporting_year": 2026},
        materiality_inputs={"climate": True},
        bundle_version="2026.01",
        retrieval_params={"query_mode": "hybrid", "top_k": 5},
        prompt_hash="prompt-abc",
    )

    assert compute_run_hash(inputs_a) == compute_run_hash(inputs_b)
    assert compute_run_hash(inputs_a) != compute_run_hash(inputs_c)


def test_run_cache_hit_skips_reprocessing_and_returns_identical_output(tmp_path: Path) -> None:
    with _prepare_session(tmp_path) as session:
        company = Company(name="Cache Co")
        session.add(company)
        session.flush()

        run = Run(company_id=company.id, status="queued")
        session.add(run)
        session.commit()

        hash_input = RunHashInput(
            tenant_id="default",
            document_hashes=["doc-hash-1"],
            company_profile={"employees": 100, "listed_status": True, "reporting_year": 2026},
            materiality_inputs={"climate": True},
            bundle_version="2026.01",
            retrieval_params={"query_mode": "hybrid", "top_k": 3},
            prompt_hash="prompt-hash-1",
        )

        call_count = {"count": 0}

        def compute_assessments() -> list[DatapointAssessment]:
            call_count["count"] += 1
            return [
                DatapointAssessment(
                    run_id=run.id,
                    datapoint_key="ESRS-E1-6",
                    status="Present",
                    value="42",
                    evidence_chunk_ids='["chunk-1"]',
                    rationale="Reported in section E1-6.",
                    model_name="gpt-5",
                    prompt_hash="prompt-hash-1",
                    retrieval_params='{"query_mode":"hybrid","top_k":3}',
                )
            ]

        first_output, first_hit = get_or_compute_cached_output(
            session,
            run_id=run.id,
            hash_input=hash_input,
            compute_assessments=compute_assessments,
        )
        second_output, second_hit = get_or_compute_cached_output(
            session,
            run_id=run.id,
            hash_input=hash_input,
            compute_assessments=compute_assessments,
        )

        assert first_hit is False
        assert second_hit is True
        assert call_count["count"] == 1
        assert first_output == second_output


def test_run_hash_changes_when_retrieval_policy_version_changes() -> None:
    base = RunHashInput(
        tenant_id="default",
        document_hashes=["doc-hash-1"],
        company_profile={"employees": 100, "listed_status": True, "reporting_year": 2026},
        materiality_inputs={"climate": True},
        bundle_version="2026.01",
        retrieval_params={
            "query_mode": "hybrid",
            "retrieval_policy": {"version": "hybrid-v1"},
            "top_k": 3,
        },
        prompt_hash="prompt-hash-1",
    )
    changed = RunHashInput(
        tenant_id="default",
        document_hashes=["doc-hash-1"],
        company_profile={"employees": 100, "listed_status": True, "reporting_year": 2026},
        materiality_inputs={"climate": True},
        bundle_version="2026.01",
        retrieval_params={
            "query_mode": "hybrid",
            "retrieval_policy": {"version": "hybrid-v2"},
            "top_k": 3,
        },
        prompt_hash="prompt-hash-1",
    )
    assert compute_run_hash(base) != compute_run_hash(changed)

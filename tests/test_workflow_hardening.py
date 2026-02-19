from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text()


def test_codex_run_prompt_workflow_is_pinned_and_secret_guarded() -> None:
    workflow = _read(".github/workflows/codex_run_prompt.yml")
    assert 'uses: openai/codex-action@v1.3' in workflow
    assert 'codex-version: "0.58.0"' in workflow
    assert "Verify OPENAI_API_KEY is present" in workflow


def test_codex_review_workflow_is_pinned_and_secret_guarded() -> None:
    workflow = _read(".github/workflows/codex_review.yml")
    assert 'uses: openai/codex-action@v1.3' in workflow
    assert 'codex-version: "0.58.0"' in workflow
    assert "Verify OPENAI_API_KEY is present" in workflow


def test_codex_autofix_workflow_is_pinned_and_secret_guarded() -> None:
    workflow = _read(".github/workflows/codex_fix_ci.yml")
    assert 'uses: openai/codex-action@v1.3' in workflow
    assert 'codex-version: "0.58.0"' in workflow
    assert "Verify OPENAI_API_KEY is present" in workflow


def test_ci_workflow_contains_pr_template_gate() -> None:
    workflow = _read(".github/workflows/ci.yml")
    assert "pr-template-gate:" in workflow
    assert "Enforce PR template checklist" in workflow
    assert "determinism-gates:" in workflow
    assert "workflow-validation:" in workflow
    assert "tests/test_chunking_golden.py" in workflow
    assert "tests/test_run_cache.py" in workflow
    assert "tests/test_evidence_pack.py" in workflow
    assert "tests/test_uat_harness.py" in workflow
    assert "tests/test_db_migrations.py" in workflow
    assert "workflow_yaml_syntax=ok" in workflow

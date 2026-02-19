import json
from pathlib import Path

from compliance_app.uat_harness import run_uat_harness

SNAPSHOT_PATH = Path("tests/golden/uat_harness_snapshot.json")
RUNBOOK_PATH = Path("docs/runbooks/uat_execution.md")
SCENARIOS_PATH = Path("tests/fixtures/uat/scenarios.json")


def test_uat_harness_matches_golden_snapshot(tmp_path: Path) -> None:
    summary = run_uat_harness(work_dir=tmp_path / "uat")
    expected = json.loads(SNAPSHOT_PATH.read_text())
    assert summary == expected


def test_uat_harness_is_repeatable(tmp_path: Path) -> None:
    first = run_uat_harness(work_dir=tmp_path / "uat-first")
    second = run_uat_harness(work_dir=tmp_path / "uat-second")
    assert first == second


def test_uat_runbook_and_scenario_pack_exist() -> None:
    assert RUNBOOK_PATH.exists()
    assert SCENARIOS_PATH.exists()

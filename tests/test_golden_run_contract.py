import json
from pathlib import Path

from compliance_app.golden_run import generate_golden_snapshot

FIXTURE_PATH = Path("tests/fixtures/golden/sample_report.txt")
SNAPSHOT_PATH = Path("tests/golden/golden_run_snapshot.json")


def test_golden_run_snapshot_contract_matches_expected() -> None:
    snapshot = generate_golden_snapshot(document_text=FIXTURE_PATH.read_text())
    expected = json.loads(SNAPSHOT_PATH.read_text())
    assert snapshot == expected


def test_golden_run_snapshot_is_repeatable() -> None:
    first = generate_golden_snapshot(document_text=FIXTURE_PATH.read_text())
    second = generate_golden_snapshot(document_text=FIXTURE_PATH.read_text())
    assert first == second

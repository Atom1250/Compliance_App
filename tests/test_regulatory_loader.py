import json
from pathlib import Path

from pydantic import ValidationError

from app.regulatory.loader import load_bundle


def test_loader_loads_sample_bundle_with_stable_checksum() -> None:
    sample_path = Path("app/regulatory/bundles/eu_csrd_sample.json")
    bundle_a, checksum_a, source_a = load_bundle(sample_path)
    bundle_b, checksum_b, source_b = load_bundle(sample_path)

    assert bundle_a.bundle_id == "eu_csrd_sample"
    assert checksum_a == checksum_b
    assert source_a == sample_path.resolve()
    assert source_b == sample_path.resolve()


def test_loader_rejects_invalid_bundle(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid_bundle.json"
    invalid_path.write_text(
        json.dumps(
            {
                "version": "2026.01",
                "jurisdiction": "EU",
                "regime": "CSRD_ESRS",
                "obligations": [],
            }
        )
    )
    try:
        load_bundle(invalid_path)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_loader_checksum_changes_when_payload_changes(tmp_path: Path) -> None:
    baseline = {
        "bundle_id": "x",
        "version": "2026.01",
        "jurisdiction": "EU",
        "regime": "CSRD_ESRS",
        "obligations": [],
    }
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    path_a.write_text(json.dumps(baseline))
    updated = dict(baseline)
    updated["version"] = "2026.02"
    path_b.write_text(json.dumps(updated))

    _, checksum_a, _ = load_bundle(path_a)
    _, checksum_b, _ = load_bundle(path_b)
    assert checksum_a != checksum_b


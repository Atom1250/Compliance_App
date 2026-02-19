from pathlib import Path

from app.requirements.bundle_view import iter_datapoints, iter_obligation_elements
from app.requirements.importer import load_bundle


def test_bundle_view_preserves_legacy_datapoints() -> None:
    bundle = load_bundle(Path("requirements/esrs_mini/bundle.json"))
    datapoints = iter_datapoints(bundle)

    assert [item.datapoint_key for item in datapoints] == ["ESRS-E1-1", "ESRS-E1-6"]
    assert iter_obligation_elements(bundle) == []


def test_bundle_view_exposes_obligation_elements_when_present() -> None:
    bundle = load_bundle(Path("requirements/green_finance_icma_eugb/bundle.json"))
    obligation_elements = iter_obligation_elements(bundle)

    assert [item.obligation_id for item in obligation_elements] == [
        "GF-OBL-01",
        "GF-OBL-01",
        "GF-OBL-02",
        "GF-OBL-02",
    ]
    assert [item.element_key for item in obligation_elements] == [
        "allocation_approach",
        "eligible_project_categories",
        "allocation_table",
        "unallocated_balance",
    ]

from pathlib import Path

from app.green_finance.matrix import generate_obligations_matrix, load_green_finance_bundle
from app.requirements.importer import load_bundle


def test_green_finance_bundle_loads_for_requirements_importer() -> None:
    requirements_bundle = load_bundle(Path("requirements/green_finance_icma_eugb/bundle.json"))
    green_finance_bundle = load_green_finance_bundle(
        Path("requirements/green_finance_icma_eugb/bundle.json")
    )

    assert requirements_bundle.bundle_id == "green_finance_icma_eugb"
    assert green_finance_bundle.bundle_id == "green_finance_icma_eugb"
    assert len(green_finance_bundle.obligations) == 2


def test_green_finance_matrix_generated_when_mode_enabled() -> None:
    bundle = load_green_finance_bundle(Path("requirements/green_finance_icma_eugb/bundle.json"))

    rows = generate_obligations_matrix(
        enabled=True,
        obligations=bundle.obligations,
        produced_artifacts={"green_bond_framework", "allocation_report"},
        produced_data_elements={"eligible_project_categories", "allocation_approach"},
        evidence_by_obligation={
            "GF-OBL-01": ["chunk-b", "chunk-a"],
            "GF-OBL-02": ["chunk-z"],
        },
    )

    assert rows == [
        {
            "obligation": "Publish eligible green project categories and allocation framework",
            "required": [
                "allocation_approach",
                "eligible_project_categories",
                "green_bond_framework",
            ],
            "produced": True,
            "evidence": ["chunk-a", "chunk-b"],
            "gap": [],
        },
        {
            "obligation": "Publish annual allocation report for bond proceeds",
            "required": ["allocation_report", "allocation_table", "unallocated_balance"],
            "produced": False,
            "evidence": ["chunk-z"],
            "gap": ["allocation_table", "unallocated_balance"],
        },
    ]


def test_green_finance_matrix_not_generated_when_mode_disabled() -> None:
    bundle = load_green_finance_bundle(Path("requirements/green_finance_icma_eugb/bundle.json"))

    rows = generate_obligations_matrix(
        enabled=False,
        obligations=bundle.obligations,
        produced_artifacts=set(),
        produced_data_elements=set(),
        evidence_by_obligation={},
    )

    assert rows == []

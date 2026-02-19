from app.regulatory.compiler import compile_bundle
from app.regulatory.schema import RegulatoryBundle


def test_compile_bundle_has_deterministic_ordering() -> None:
    payload = {
        "bundle_id": "eu_csrd_sample",
        "version": "2026.01",
        "jurisdiction": "EU",
        "regime": "CSRD_ESRS",
        "obligations": [
            {
                "obligation_id": "OBL-2",
                "title": "Second",
                "standard_reference": "ESRS E1-6",
                "elements": [
                    {"element_id": "B", "label": "B", "required": True, "phase_in_rules": []},
                    {"element_id": "A", "label": "A", "required": True, "phase_in_rules": []},
                ],
            },
            {
                "obligation_id": "OBL-1",
                "title": "First",
                "standard_reference": "ESRS E1-1",
                "elements": [
                    {"element_id": "C", "label": "C", "required": True, "phase_in_rules": []}
                ],
            },
        ],
    }
    bundle = RegulatoryBundle.model_validate(payload)
    context = {"company": {"reporting_year": 2026}}
    first = compile_bundle(bundle, context=context).model_dump(mode="json")
    second = compile_bundle(bundle, context=context).model_dump(mode="json")

    assert first == second
    assert [item["obligation_id"] for item in first["obligations"]] == ["OBL-1", "OBL-2"]
    assert [item["element_id"] for item in first["obligations"][1]["elements"]] == ["A", "B"]


def test_compile_bundle_applies_phase_in_rules() -> None:
    payload = {
        "bundle_id": "eu_csrd_sample",
        "version": "2026.01",
        "jurisdiction": "EU",
        "regime": "CSRD_ESRS",
        "obligations": [
            {
                "obligation_id": "OBL-1",
                "title": "First",
                "standard_reference": "ESRS E1-1",
                "elements": [
                    {
                        "element_id": "E-1",
                        "label": "Phase-in element",
                        "required": True,
                        "phase_in_rules": [
                            {"key": "reporting_year", "operator": ">=", "value": 2025}
                        ],
                    }
                ],
            }
        ],
    }
    bundle = RegulatoryBundle.model_validate(payload)

    pre_phase = compile_bundle(bundle, context={"company": {"reporting_year": 2024}})
    post_phase = compile_bundle(bundle, context={"company": {"reporting_year": 2026}})

    assert pre_phase.obligations == []
    assert len(post_phase.obligations) == 1
    assert post_phase.obligations[0].elements[0].element_id == "E-1"

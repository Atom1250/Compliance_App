from pydantic import ValidationError

from app.regulatory.canonical import canonical_json, sha256_checksum
from app.regulatory.schema import RegulatoryBundle


def _sample_bundle_payload() -> dict[str, object]:
    return {
        "bundle_id": "eu_csrd",
        "version": "2026.01",
        "jurisdiction": "EU",
        "regime": "CSRD_ESRS",
        "obligations": [
            {
                "obligation_id": "OBL-1",
                "title": "Climate transition plan",
                "standard_reference": "ESRS E1-1",
                "elements": [
                    {
                        "element_id": "EL-1",
                        "label": "Transition plan narrative",
                        "required": True,
                        "phase_in_rules": [
                            {"key": "reporting_year", "operator": ">=", "value": 2025}
                        ],
                    }
                ],
            }
        ],
    }


def test_regulatory_bundle_schema_accepts_valid_payload() -> None:
    payload = _sample_bundle_payload()
    bundle = RegulatoryBundle.model_validate(payload)
    assert bundle.bundle_id == "eu_csrd"
    assert bundle.obligations[0].obligation_id == "OBL-1"
    assert bundle.obligations[0].elements[0].phase_in_rules[0].value == 2025


def test_regulatory_bundle_schema_rejects_invalid_payload() -> None:
    payload = _sample_bundle_payload()
    payload.pop("bundle_id")
    try:
        RegulatoryBundle.model_validate(payload)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_regulatory_bundle_schema_rejects_unknown_fields() -> None:
    payload = _sample_bundle_payload()
    payload["unexpected"] = "nope"
    try:
        RegulatoryBundle.model_validate(payload)
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_canonical_checksum_is_stable_across_repeated_calls() -> None:
    bundle = RegulatoryBundle.model_validate(_sample_bundle_payload())
    first = sha256_checksum(bundle)
    second = sha256_checksum(bundle)
    assert first == second
    assert len(first) == 64


def test_canonical_checksum_changes_when_payload_changes() -> None:
    left = RegulatoryBundle.model_validate(_sample_bundle_payload())
    right_payload = _sample_bundle_payload()
    right_payload["version"] = "2026.02"
    right = RegulatoryBundle.model_validate(right_payload)
    assert sha256_checksum(left) != sha256_checksum(right)


def test_canonical_json_sorts_keys_deterministically() -> None:
    unordered = {"b": 2, "a": 1}
    assert canonical_json(unordered) == '{"a":1,"b":2}'

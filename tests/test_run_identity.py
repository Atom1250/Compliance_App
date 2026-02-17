from compliance_app.run_identity import build_run_input_fingerprint


def test_fingerprint_is_stable_for_equal_payloads() -> None:
    payload_a = {
        "document_hashes": ["abc", "def"],
        "bundle_version": "esrs-2026.01",
        "retrieval": {"top_k": 12, "mode": "hybrid"},
    }
    payload_b = {
        "bundle_version": "esrs-2026.01",
        "retrieval": {"mode": "hybrid", "top_k": 12},
        "document_hashes": ["abc", "def"],
    }

    assert build_run_input_fingerprint(payload_a) == build_run_input_fingerprint(payload_b)


def test_fingerprint_changes_when_payload_changes() -> None:
    base_payload = {"document_hash": "abc", "bundle_version": "esrs-2026.01"}
    changed_payload = {"document_hash": "xyz", "bundle_version": "esrs-2026.01"}

    assert build_run_input_fingerprint(base_payload) != build_run_input_fingerprint(changed_payload)

from apps.api.app.services.regulatory_research.hash import compute_request_hash
from apps.api.app.services.regulatory_research.types import ResearchRequest


def test_compute_request_hash_is_deterministic_for_whitespace_variants() -> None:
    first = ResearchRequest(question="  What is CSRD? ", corpus_key="eu-core", mode="qa")
    second = ResearchRequest(question="What   is   CSRD?", corpus_key="eu-core", mode="qa")

    assert compute_request_hash(first) == compute_request_hash(second)


def test_compute_request_hash_changes_with_mode_or_requirement() -> None:
    base = ResearchRequest(question="Map ESRS E1", corpus_key="eu-core", mode="mapping")
    changed_mode = ResearchRequest(question="Map ESRS E1", corpus_key="eu-core", mode="qa")
    changed_req = ResearchRequest(
        question="Map ESRS E1", corpus_key="eu-core", mode="mapping", requirement_id="REQ-1"
    )

    assert compute_request_hash(base) != compute_request_hash(changed_mode)
    assert compute_request_hash(base) != compute_request_hash(changed_req)

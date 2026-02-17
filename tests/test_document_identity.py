from compliance_app.document_identity import sha256_bytes, stable_document_id


def test_sha256_bytes_is_stable_for_identical_content() -> None:
    content = b"sample disclosure content"

    assert sha256_bytes(content) == sha256_bytes(content)


def test_sha256_bytes_changes_when_content_changes() -> None:
    content_a = b"sample disclosure content"
    content_b = b"sample disclosure content changed"

    assert sha256_bytes(content_a) != sha256_bytes(content_b)


def test_stable_document_id_is_stable_for_same_inputs() -> None:
    content_hash = sha256_bytes(b"doc bytes")

    id_a = stable_document_id(content_hash=content_hash, source_name="Report.PDF")
    id_b = stable_document_id(content_hash=content_hash, source_name=" report.pdf ")

    assert id_a == id_b


def test_stable_document_id_changes_when_inputs_change() -> None:
    base_hash = sha256_bytes(b"doc bytes")
    changed_hash = sha256_bytes(b"doc bytes changed")

    base_id = stable_document_id(content_hash=base_hash, source_name="report.pdf")
    changed_by_hash = stable_document_id(content_hash=changed_hash, source_name="report.pdf")
    changed_by_name = stable_document_id(content_hash=base_hash, source_name="report-v2.pdf")

    assert base_id != changed_by_hash
    assert base_id != changed_by_name

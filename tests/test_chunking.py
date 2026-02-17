from apps.api.app.services.chunking import build_page_chunks


def test_chunk_ids_are_deterministic_for_same_input() -> None:
    text = "A" * 1200

    chunks_first = build_page_chunks(document_hash="doc-hash", page_number=1, text=text)
    chunks_second = build_page_chunks(document_hash="doc-hash", page_number=1, text=text)

    assert chunks_first == chunks_second
    assert [chunk.chunk_id for chunk in chunks_first] == [chunk.chunk_id for chunk in chunks_second]


def test_chunk_ids_change_with_offsets() -> None:
    base_text = "A" * 1200
    changed_text = "B" + base_text

    chunks_base = build_page_chunks(document_hash="doc-hash", page_number=1, text=base_text)
    chunks_changed = build_page_chunks(document_hash="doc-hash", page_number=1, text=changed_text)

    assert [chunk.chunk_id for chunk in chunks_base] != [chunk.chunk_id for chunk in chunks_changed]

from apps.api.app.services.chunking import ChunkPayload, rank_chunks_for_query_sanity


def test_retrieval_sanity_ordering_is_deterministic() -> None:
    chunks = [
        ChunkPayload("c3", 1, 0, 10, "green bond proceeds allocation"),
        ChunkPayload("c1", 1, 10, 20, "green bond framework alignment"),
        ChunkPayload("c2", 2, 0, 10, "unrelated disclosure text"),
    ]

    ranked_once = rank_chunks_for_query_sanity("green bond", chunks, top_k=2)
    ranked_twice = rank_chunks_for_query_sanity("green bond", chunks, top_k=2)

    assert [chunk.chunk_id for chunk in ranked_once] == ["c1", "c3"]
    assert ranked_once == ranked_twice

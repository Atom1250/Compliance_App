from pathlib import Path


def test_persistence_cutover_adr_exists_and_mentions_required_storage_contracts() -> None:
    path = Path("docs/adr/0002-persistence-cutover-postgres-pgvector.md")
    assert path.exists()
    text = path.read_text()
    assert "Postgres + pgvector" in text
    assert "SQLite remains allowed only for test fixtures" in text
    assert "deterministic ordering clauses" in text

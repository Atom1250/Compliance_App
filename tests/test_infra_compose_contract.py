from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text()


def test_compose_uses_pgvector_image_and_extension_init_mount() -> None:
    compose = _read("docker-compose.yml")
    assert "image: pgvector/pgvector:pg16" in compose
    assert "./docker/postgres/init:/docker-entrypoint-initdb.d:ro" in compose
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in _read(
        "docker/postgres/init/001-enable-pgvector.sql"
    )


def test_compose_includes_minio_healthcheck() -> None:
    compose = _read("docker-compose.yml")
    assert "minio/health/live" in compose
    assert "healthcheck:" in compose


def test_makefile_exposes_compose_and_db_wait_targets() -> None:
    makefile = _read("Makefile")
    assert "compose-up:" in makefile
    assert "compose-down:" in makefile
    assert "db-wait:" in makefile
    assert "docker compose up -d postgres minio" in makefile
    assert "docker compose exec -T postgres pg_isready" in makefile

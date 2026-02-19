from __future__ import annotations

from pathlib import Path

import pytest

from apps.api.app.scripts import import_regulatory_sources as cli


def test_help_includes_csv_first_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Recommended (CSV)" in captured.out
    assert "Optional (XLSX)" in captured.out
    assert "Dry-run" in captured.out
    assert "regulatory_source_document_SOURCE_SHEETS_full.csv" in captured.out


def test_xlsx_emits_csv_recommendation_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    xlsx_path = tmp_path / "sources.xlsx"
    xlsx_path.write_text("placeholder", encoding="utf-8")

    class _DummySession:
        def __enter__(self) -> _DummySession:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    class _DummyFactory:
        def __call__(self) -> _DummySession:
            return _DummySession()

    def _fake_get_session_factory() -> _DummyFactory:
        return _DummyFactory()

    class _Summary:
        invalid_rows = 0

        @staticmethod
        def as_dict() -> dict[str, int]:
            return {
                "rows_seen": 0,
                "rows_deduped": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "invalid_rows": 0,
            }

    def _fake_import(*_args: object, **_kwargs: object) -> _Summary:
        return _Summary()

    monkeypatch.setattr(cli, "get_session_factory", _fake_get_session_factory)
    monkeypatch.setattr(cli, "import_regulatory_sources", _fake_import)

    code = cli.main(["--file", str(xlsx_path), "--dry-run"])
    captured = capsys.readouterr()
    assert code == 0
    assert "CSV is recommended for deterministic ingestion" in captured.out


def test_cli_missing_table_guard_is_user_friendly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    csv_path = tmp_path / "regulatory_source_document_SOURCE_SHEETS_full.csv"
    csv_path.write_text(
        "record_id,jurisdiction,document_name\nEU-L1-CSRD,EU,CSRD\n",
        encoding="utf-8",
    )

    class _DummySession:
        def __enter__(self) -> _DummySession:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    class _DummyFactory:
        def __call__(self) -> _DummySession:
            return _DummySession()

    def _fake_get_session_factory() -> _DummyFactory:
        return _DummyFactory()

    def _fake_import(*_args: object, **_kwargs: object) -> object:
        raise ValueError(
            "Table regulatory_source_document does not exist. "
            "Apply migrations (alembic upgrade head) then retry."
        )

    monkeypatch.setattr(cli, "get_session_factory", _fake_get_session_factory)
    monkeypatch.setattr(cli, "import_regulatory_sources", _fake_import)

    code = cli.main(["--file", str(csv_path)])
    captured = capsys.readouterr()
    assert code == 2
    assert "Table regulatory_source_document does not exist." in captured.err
    assert "Traceback" not in captured.err

from pathlib import Path

import pytest

from apps.api.app.services.pdf_export import export_pdf_report


def test_pdf_export_returns_none_when_feature_disabled(tmp_path: Path) -> None:
    output_path = tmp_path / "report.pdf"
    result = export_pdf_report(
        html_text="<html><body>report</body></html>",
        output_path=output_path,
        enabled=False,
    )

    assert result is None
    assert not output_path.exists()


def test_pdf_export_writes_file_when_enabled_with_renderer(tmp_path: Path) -> None:
    output_path = tmp_path / "report.pdf"
    result = export_pdf_report(
        html_text="<html><body>report</body></html>",
        output_path=output_path,
        enabled=True,
        renderer=lambda html_text: b"%PDF-1.4\nmock\n%%EOF",
    )

    assert result == output_path
    assert output_path.read_bytes() == b"%PDF-1.4\nmock\n%%EOF"


def test_pdf_export_raises_when_dependency_missing(tmp_path: Path) -> None:
    def _raise_missing(_html_text: str) -> bytes:
        raise RuntimeError(
            "PDF export dependency missing: install weasyprint or disable PDF export."
        )

    with pytest.raises(RuntimeError, match="dependency missing"):
        export_pdf_report(
            html_text="<html><body>report</body></html>",
            output_path=tmp_path / "report.pdf",
            enabled=True,
            renderer=_raise_missing,
        )

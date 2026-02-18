"""Optional PDF export from HTML report content."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path


def _default_pdf_renderer(html_text: str) -> bytes:
    try:
        weasyprint = importlib.import_module("weasyprint")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PDF export dependency missing: install weasyprint or disable PDF export."
        ) from exc

    return weasyprint.HTML(string=html_text).write_pdf()


def export_pdf_report(
    *,
    html_text: str,
    output_path: Path,
    enabled: bool,
    renderer: Callable[[str], bytes] | None = None,
) -> Path | None:
    """Write PDF file when enabled; return None when feature is disabled."""
    if not enabled:
        return None

    selected_renderer = renderer or _default_pdf_renderer
    pdf_bytes = selected_renderer(html_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    return output_path

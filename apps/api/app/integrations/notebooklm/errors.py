"""Typed NotebookLM MCP integration errors."""

from __future__ import annotations


class NotebookLMMCPError(RuntimeError):
    """Base error for NotebookLM MCP integration failures."""


class NotebookLMMCPTransportError(NotebookLMMCPError):
    """Raised when the HTTP transport to MCP fails."""


class NotebookLMMCPResponseError(NotebookLMMCPError):
    """Raised when MCP returns an invalid response payload."""


class NotebookLMMissingNotebookMappingError(NotebookLMMCPError):
    """Raised when no notebook ID mapping exists for corpus_key."""

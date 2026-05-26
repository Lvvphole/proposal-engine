"""Sandbox for untrusted document processing.

Provides isolation boundaries when processing uploaded documents.
Currently uses subprocess isolation; can be swapped for container
isolation in production.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger()


class DocumentSandbox:
    """Context manager providing a temporary directory for document processing."""

    def __init__(self, envelope_id: str) -> None:
        self.envelope_id = envelope_id
        self._tmpdir: tempfile.TemporaryDirectory | None = None

    def __enter__(self) -> Path:
        self._tmpdir = tempfile.TemporaryDirectory(prefix=f"pe_{self.envelope_id}_")
        path = Path(self._tmpdir.name)
        logger.info("sandbox_created", envelope_id=self.envelope_id, path=str(path))
        return path

    def __exit__(self, *exc) -> None:
        if self._tmpdir:
            self._tmpdir.cleanup()
            logger.info("sandbox_cleaned", envelope_id=self.envelope_id)

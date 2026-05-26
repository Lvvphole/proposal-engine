"""MCP tool handlers for proposal operations."""

from __future__ import annotations

from typing import Any

from mcp.server import Server


def register(server: Server) -> None:
    """Register proposal-related MCP tools."""

    @server.tool("submit_quote")
    async def submit_quote(
        filename: str,
        content_b64: str,
        content_type: str = "application/pdf",
        contractor_id: str | None = None,
    ) -> dict[str, Any]:
        """Submit a supplier quote for extraction and proposal generation.

        Args:
            filename: Original filename of the quote document.
            content_b64: Base64-encoded document content.
            content_type: MIME type of the document.
            contractor_id: Optional contractor to generate proposal for.

        Returns:
            Dict with envelope_id and initial status.
        """
        from contracts.envelope import Envelope

        envelope = Envelope(
            source_filename=filename,
            source_content_type=content_type,
            source_bytes_b64=content_b64,
            contractor_id=contractor_id,
        )

        # In production, this dispatches to the orchestrator asynchronously
        return {
            "envelope_id": envelope.id,
            "status": envelope.status,
            "message": f"Quote '{filename}' received. Processing will begin shortly.",
        }

    @server.tool("get_proposal_status")
    async def get_proposal_status(envelope_id: str) -> dict[str, Any]:
        """Check the processing status of a submitted quote.

        Args:
            envelope_id: The envelope ID returned from submit_quote.

        Returns:
            Current status and any available results.
        """
        # Placeholder — production queries the database
        return {
            "envelope_id": envelope_id,
            "status": "review_pending",
            "message": "Extraction complete. Awaiting human review.",
        }

    @server.tool("list_recent_proposals")
    async def list_recent_proposals(
        limit: int = 10,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List recent proposals with optional status filter.

        Args:
            limit: Max number of proposals to return.
            status: Filter by status (e.g., 'review_pending', 'approved').

        Returns:
            List of proposal summaries.
        """
        return {"proposals": [], "total": 0}

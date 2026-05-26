"""MCP tool handlers for contractor management."""

from __future__ import annotations

from typing import Any

from mcp.server import Server


def register(server: Server) -> None:
    """Register contractor-related MCP tools."""

    @server.tool("register_contractor")
    async def register_contractor(
        name: str,
        company: str = "",
        default_markup_pct: float = 0.20,
        payment_terms: str = "Due on completion",
    ) -> dict[str, Any]:
        """Register a new contractor profile.

        Args:
            name: Contractor's name.
            company: Company name.
            default_markup_pct: Default markup percentage (0.0–1.0).
            payment_terms: Default payment terms text.

        Returns:
            The new contractor profile with generated ID.
        """
        import uuid
        contractor_id = str(uuid.uuid4())[:8]

        from rag.contractor_context import register_contractor as reg
        reg(contractor_id, {
            "name": name,
            "company": company,
            "markup_rules": {"default_pct": default_markup_pct},
            "payment_terms": payment_terms,
        })

        return {
            "contractor_id": contractor_id,
            "name": name,
            "company": company,
            "default_markup_pct": default_markup_pct,
        }

    @server.tool("list_contractors")
    async def list_contractors() -> dict[str, Any]:
        """List all registered contractors."""
        from rag.contractor_context import list_contractors as lc
        return {"contractors": lc()}

    @server.tool("get_contractor")
    async def get_contractor(contractor_id: str) -> dict[str, Any]:
        """Get a contractor's full profile and context."""
        from rag.contractor_context import get_context
        return get_context(contractor_id)

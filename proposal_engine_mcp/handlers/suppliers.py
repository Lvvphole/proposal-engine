"""MCP tool handlers for supplier catalog management."""

from __future__ import annotations

from typing import Any

from mcp.server import Server


def register(server: Server) -> None:
    """Register supplier-related MCP tools."""

    @server.tool("register_supplier")
    async def register_supplier(
        name: str,
        preferred_pipeline: str = "c",
        notes: str = "",
    ) -> dict[str, Any]:
        """Register a new supplier in the catalog.

        Args:
            name: Supplier name.
            preferred_pipeline: Which extraction pipeline works best (a, b, or c).
            notes: Free-text notes about the supplier's quote format.

        Returns:
            The registered supplier entry.
        """
        from rag.supplier_catalog import register_supplier as reg
        reg(name, preferred_pipeline=preferred_pipeline, notes=notes)

        return {
            "name": name,
            "preferred_pipeline": preferred_pipeline,
            "notes": notes,
        }

    @server.tool("list_suppliers")
    async def list_suppliers() -> dict[str, Any]:
        """List all known suppliers."""
        from rag.supplier_catalog import list_suppliers as ls
        return {"suppliers": ls()}

    @server.tool("get_supplier")
    async def get_supplier(name: str) -> dict[str, Any]:
        """Get supplier details and extraction history."""
        from rag.supplier_catalog import get_supplier
        entry = get_supplier(name)
        if entry is None:
            return {"error": f"Supplier '{name}' not found in catalog."}
        return entry

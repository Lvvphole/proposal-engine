"""MCP HTTP/SSE server setup.

Creates and configures the MCP server with all tool handlers registered.
"""

from __future__ import annotations

from mcp.server import Server

from proposal_engine_mcp.handlers import contractors, proposals, suppliers


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("proposal-engine")

    # Register tool handlers
    proposals.register(server)
    contractors.register(server)
    suppliers.register(server)

    return server

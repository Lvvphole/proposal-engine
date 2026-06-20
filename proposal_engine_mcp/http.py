"""MCP HTTP/SSE server setup."""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.types import TextContent, Tool


def create_server() -> Server:
    server = Server("proposal-engine")

    tools = {
        "submit_quote": {
            "description": "Submit a supplier quote for extraction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content_b64": {"type": "string"},
                    "content_type": {"type": "string", "default": "application/pdf"},
                    "contractor_id": {"type": "string"},
                },
                "required": ["filename", "content_b64"],
            },
        },
        "get_proposal_status": {
            "description": "Check processing status of a submitted quote",
            "inputSchema": {
                "type": "object",
                "properties": {"envelope_id": {"type": "string"}},
                "required": ["envelope_id"],
            },
        },
        "list_recent_proposals": {
            "description": "List recent proposals",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                    "status": {"type": "string"},
                },
            },
        },
        "register_contractor": {
            "description": "Register a new contractor profile",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "company": {"type": "string", "default": ""},
                    "default_markup_pct": {"type": "number", "default": 0.20},
                    "payment_terms": {"type": "string", "default": "Due on completion"},
                },
                "required": ["name"],
            },
        },
        "list_contractors": {
            "description": "List all registered contractors",
            "inputSchema": {"type": "object", "properties": {}},
        },
        "get_contractor": {
            "description": "Get contractor profile and context",
            "inputSchema": {
                "type": "object",
                "properties": {"contractor_id": {"type": "string"}},
                "required": ["contractor_id"],
            },
        },
        "register_supplier": {
            "description": "Register a new supplier in the catalog",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "preferred_pipeline": {"type": "string", "default": "c"},
                    "notes": {"type": "string", "default": ""},
                },
                "required": ["name"],
            },
        },
        "list_suppliers": {
            "description": "List all known suppliers",
            "inputSchema": {"type": "object", "properties": {}},
        },
    }

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name=k, description=v["description"], inputSchema=v["inputSchema"])
            for k, v in tools.items()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        from proposal_engine_mcp.handlers import dispatch

        result = await dispatch.handle(name, arguments)
        return [TextContent(type="text", text=json.dumps(result))]

    return server

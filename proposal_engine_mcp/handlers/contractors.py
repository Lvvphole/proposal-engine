"""MCP tool handlers for contractor management."""

from __future__ import annotations

import uuid
from typing import Any

from mcp.server import Server

from contracts.contractor import ContractorProfile
from core.db import _get_session_factory
from rag.contractor_context import get_context, upsert_contractor
from rag.contractor_context import list_contractors as list_contractor_profiles


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
        contractor_id = str(uuid.uuid4())[:8]
        profile = ContractorProfile(
            id=contractor_id,
            name=name,
            company=company,
            default_markup_pct=default_markup_pct,
            payment_terms=payment_terms,
        )
        async with _get_session_factory()() as session:
            await upsert_contractor(profile, session)

        return {
            "contractor_id": contractor_id,
            "name": name,
            "company": company,
            "default_markup_pct": default_markup_pct,
        }

    @server.tool("list_contractors")
    async def list_contractors() -> dict[str, Any]:
        """List all registered contractors."""
        async with _get_session_factory()() as session:
            profiles = await list_contractor_profiles(session)
        return {"contractors": [p.model_dump() for p in profiles]}

    @server.tool("get_contractor")
    async def get_contractor(contractor_id: str) -> dict[str, Any]:
        """Get a contractor's full proposal-generation context."""
        async with _get_session_factory()() as session:
            return await get_context(contractor_id, session)

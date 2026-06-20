"""Entry point for python -m proposal_engine_mcp."""

import asyncio

from mcp.server.stdio import stdio_server

from proposal_engine_mcp.http import create_server


async def main() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

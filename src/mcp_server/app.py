"""Factory that assembles a FastMCP server instance with all four tools registered.

Kept separate from the stdio/HTTP entrypoints so tests can build an isolated
server (its own temp sandbox dir, its own Settings) without touching env vars
or process-wide state.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server.config import Settings, load_settings
from mcp_server.tools import files, http_request, transform, web

INSTRUCTIONS = (
    "Tools for sandboxed local file access, public web scraping, JSON/CSV data "
    "transformation, and authenticated outbound HTTP requests. File access is "
    "restricted to a single configured directory; outbound network calls are "
    "restricted to public addresses (private/loopback/link-local ranges are blocked)."
)


def create_server(settings: Settings | None = None) -> FastMCP:
    """Build a fully configured FastMCP server. Pass `settings` explicitly in
    tests; production entrypoints should omit it to load from the environment.
    """
    settings = settings or load_settings()

    mcp = FastMCP(
        name="claude-mcp-server",
        instructions=INSTRUCTIONS,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )

    files.register(mcp, settings)
    web.register(mcp, settings)
    transform.register(mcp, settings)
    http_request.register(mcp, settings)

    return mcp

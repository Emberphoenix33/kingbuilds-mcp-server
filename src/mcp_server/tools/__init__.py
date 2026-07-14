"""Tool implementations for the Claude MCP server.

Each module exposes a `register(mcp, settings)` function that attaches its
tool(s) to a `mcp.server.fastmcp.FastMCP` instance. Keeping registration
explicit (rather than relying on decorator-time global state) lets tests
build isolated server instances with their own temp directories and settings.
"""

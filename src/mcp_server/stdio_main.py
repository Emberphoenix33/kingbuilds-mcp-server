"""Entrypoint for the stdio transport (used by Claude Desktop and other local clients).

Run with: `python -m mcp_server.stdio_main` or the `mcp-server-stdio` console script.
"""

from __future__ import annotations

from mcp_server.app import create_server


def main() -> None:
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

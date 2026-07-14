"""Unified CLI: `python -m mcp_server --transport stdio|streamable-http|sse`."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp_server", description="Claude MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport to run (default: stdio)",
    )
    args, remaining = parser.parse_known_args()

    if args.transport == "stdio":
        from mcp_server.stdio_main import main as stdio_main

        stdio_main()
    else:
        sys.argv = [sys.argv[0], "--transport", args.transport, *remaining]
        from mcp_server.http_main import main as http_main

        http_main()


if __name__ == "__main__":
    main()

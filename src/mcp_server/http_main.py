"""Entrypoint for the HTTP transport (Streamable HTTP by default, or legacy SSE).

Run with: `python -m mcp_server.http_main [--transport streamable-http|sse]`
or the `mcp-server-http` console script.

If `MCP_SERVER_AUTH_TOKEN` is set, every request must include
`Authorization: Bearer <token>` or it is rejected with 401 before it reaches
the MCP session layer. This protects the server endpoint itself; it is
separate from the credential the `http_request` tool injects into its own
outbound calls.
"""

from __future__ import annotations

import argparse
import hmac
import logging

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from mcp_server.app import create_server
from mcp_server.config import Settings, load_settings

logger = logging.getLogger("mcp_server.http_main")


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Rejects any request lacking a matching `Authorization: Bearer <token>` header."""

    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._expected = f"Bearer {token}"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        provided = request.headers.get("authorization", "")
        if not hmac.compare_digest(provided, self._expected):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


async def _health(_request: Request) -> Response:
    return JSONResponse({"status": "ok"})


def build_app(transport: str = "streamable-http", settings: Settings | None = None) -> Starlette:
    settings = settings or load_settings()
    mcp = create_server(settings)

    if transport == "sse":
        starlette_app = mcp.sse_app()
    elif transport == "streamable-http":
        starlette_app = mcp.streamable_http_app()
    else:
        raise ValueError(f"Unsupported HTTP transport: {transport!r} (expected 'streamable-http' or 'sse')")

    starlette_app.router.routes.insert(0, Route("/health", _health, methods=["GET"]))

    if settings.server_auth_token:
        starlette_app.add_middleware(BearerTokenMiddleware, token=settings.server_auth_token)
        logger.info("HTTP transport auth ENABLED (bearer token required)")
    else:
        logger.warning(
            "HTTP transport auth DISABLED (MCP_SERVER_AUTH_TOKEN not set) — "
            "do not expose this server on a public network without setting it"
        )

    return starlette_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse"],
        default="streamable-http",
        help="HTTP transport variant to serve (default: streamable-http)",
    )
    args = parser.parse_args()

    settings = load_settings()
    starlette_app = build_app(args.transport, settings)

    uvicorn.run(
        starlette_app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()

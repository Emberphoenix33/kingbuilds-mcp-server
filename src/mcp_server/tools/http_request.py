"""Authenticated, SSRF-safe generic HTTP request tool.

The credential (bearer token or API key) lives only in server-side settings
(`MCP_HTTP_TOOL_AUTH_TOKEN`) and is injected here. The model can never see or
override it: any client-supplied `Authorization` header is stripped before
the server's own credential is attached.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.config import Settings
from mcp_server.net import safe_request
from mcp_server.security import SecurityError

logger = logging.getLogger("mcp_server.tools.http_request")

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="http_request",
        description=(
            "Make an authenticated HTTP request to a public API. The server attaches its own "
            "configured credential (bearer token or API key) — do not attempt to pass "
            "Authorization headers yourself, they will be ignored. GET/POST/PUT/PATCH/DELETE/HEAD "
            "supported. Blocks requests to private, loopback, link-local, and other non-public "
            "addresses, and re-validates every redirect hop."
        ),
    )
    async def http_request(
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json_body: Any | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        method_upper = method.upper()
        if method_upper not in _ALLOWED_METHODS:
            return {"error": f"Unsupported HTTP method: {method!r} (allowed: {sorted(_ALLOWED_METHODS)})"}

        if json_body is not None and body is not None:
            return {"error": "Provide either json_body or body, not both"}

        merged_headers = {k: v for k, v in (headers or {}).items() if k.lower() != "authorization"}

        if settings.http_tool_auth_scheme == "bearer" and settings.http_tool_auth_token:
            merged_headers["Authorization"] = f"Bearer {settings.http_tool_auth_token}"
        elif settings.http_tool_auth_scheme == "api_key" and settings.http_tool_auth_token:
            merged_headers[settings.http_tool_api_key_header] = settings.http_tool_auth_token

        try:
            response = await safe_request(
                method_upper,
                url,
                settings=settings,
                headers=merged_headers,
                params=query_params,
                json_body=json_body,
                content=body,
            )
        except SecurityError as exc:
            logger.warning("http_request blocked: %s", exc)
            return {"error": str(exc)}

        logger.info("http_request: %s %s -> %d", method_upper, url, response.status_code)
        return {
            "status_code": response.status_code,
            "url": response.url,
            "headers": response.headers,
            "body": response.text,
            "truncated": response.truncated,
        }

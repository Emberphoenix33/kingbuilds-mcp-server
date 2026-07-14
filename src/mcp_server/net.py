"""SSRF-safe outbound HTTP client shared by the web-scraping and http_request tools.

Redirects are followed manually (rather than via httpx's `follow_redirects=True`)
so that every hop is re-validated against the same SSRF policy as the original
URL — a raw scheme/host check on the initial URL alone would not stop a
"safe" URL from redirecting to an internal service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from mcp_server.config import Settings
from mcp_server.security import SecurityError, validate_public_url


@dataclass
class SafeHttpResponse:
    status_code: int
    headers: dict[str, str]
    url: str
    text: str
    truncated: bool


async def safe_request(
    method: str,
    url: str,
    *,
    settings: Settings,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    content: str | bytes | None = None,
) -> SafeHttpResponse:
    """Perform an outbound HTTP request, enforcing SSRF and size/time limits.

    Raises SecurityError if the URL (or any redirect target) is disallowed.
    """
    current_url = url
    validate_public_url(
        current_url,
        allowed_schemes=settings.allowed_url_schemes,
        host_allowlist=settings.outbound_host_allowlist,
    )

    merged_headers = {"User-Agent": settings.user_agent}
    if headers:
        merged_headers.update(headers)

    async with httpx.AsyncClient(follow_redirects=False, timeout=settings.http_timeout_seconds) as client:
        for hop in range(settings.max_redirects + 1):
            request_kwargs: dict[str, Any] = {"headers": merged_headers}
            if hop == 0:
                if params is not None:
                    request_kwargs["params"] = params
                if json_body is not None:
                    request_kwargs["json"] = json_body
                if content is not None:
                    request_kwargs["content"] = content

            async with client.stream(method, current_url, **request_kwargs) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise SecurityError("Redirect response is missing a Location header")
                    current_url = str(httpx.URL(current_url).join(location))
                    validate_public_url(
                        current_url,
                        allowed_schemes=settings.allowed_url_schemes,
                        host_allowlist=settings.outbound_host_allowlist,
                    )
                    continue

                body = bytearray()
                truncated = False
                async for chunk in response.aiter_bytes():
                    remaining = settings.max_response_bytes - len(body)
                    if remaining <= 0:
                        truncated = True
                        break
                    if len(chunk) > remaining:
                        body.extend(chunk[:remaining])
                        truncated = True
                        break
                    body.extend(chunk)

                text = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                return SafeHttpResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    url=str(response.url),
                    text=text,
                    truncated=truncated,
                )

    raise SecurityError(f"Exceeded the maximum of {settings.max_redirects} redirects")

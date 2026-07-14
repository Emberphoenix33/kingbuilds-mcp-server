"""Web scraping tool: fetch a page and extract structured content with BeautifulSoup.

Fetching goes through `mcp_server.net.safe_request`, which enforces the
SSRF policy in `mcp_server.security` (scheme allowlist, private/loopback/
link-local IP blocking, redirect re-validation) and response size/time limits.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

from mcp_server.config import Settings
from mcp_server.net import safe_request
from mcp_server.security import SecurityError

logger = logging.getLogger("mcp_server.tools.web")

_MAX_TEXT_CHARS = 20_000
_MAX_SELECTOR_MATCHES = 200


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="scrape_web_page",
        description=(
            "Fetch a public web page and extract its content. Without `selector`, returns the "
            "page title, visible text (script/style stripped), and outgoing links. With "
            "`selector`, returns the text of every element matching that CSS selector instead. "
            "Blocks requests to private, loopback, link-local, and other non-public addresses."
        ),
    )
    async def scrape_web_page(url: str, selector: str | None = None, max_links: int = 50) -> dict[str, Any]:
        try:
            response = await safe_request("GET", url, settings=settings)
        except SecurityError as exc:
            logger.warning("scrape_web_page blocked: %s", exc)
            return {"error": str(exc)}

        if response.status_code >= 400:
            return {
                "error": f"Server returned HTTP {response.status_code}",
                "status_code": response.status_code,
                "url": response.url,
            }

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else None

        result: dict[str, Any] = {
            "url": response.url,
            "status_code": response.status_code,
            "title": title,
            "response_truncated": response.truncated,
        }

        if selector:
            try:
                matches = soup.select(selector)
            except Exception as exc:  # invalid CSS selector syntax from bs4/soupsieve
                return {"error": f"Invalid selector '{selector}': {exc}"}

            result["selector"] = selector
            result["match_count"] = len(matches)
            result["matches"] = [m.get_text(" ", strip=True) for m in matches[:_MAX_SELECTOR_MATCHES]]
            logger.info("scrape_web_page: %s selector=%r matches=%d", response.url, selector, len(matches))
            return result

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text("\n", strip=True)
        result["text"] = text[:_MAX_TEXT_CHARS]
        result["text_truncated"] = len(text) > _MAX_TEXT_CHARS

        links: list[dict[str, str]] = []
        for anchor in soup.find_all("a", href=True):
            href = urljoin(response.url, anchor["href"])
            links.append({"text": anchor.get_text(strip=True), "href": href})
            if len(links) >= max_links:
                break
        result["links"] = links

        logger.info("scrape_web_page: %s (%d chars, %d links)", response.url, len(text), len(links))
        return result

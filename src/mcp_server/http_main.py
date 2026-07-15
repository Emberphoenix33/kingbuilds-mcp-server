"""
Entrypoint for the HTTP transport (Streamable HTTP by default, or legacy SSE).

Run with: `python -m mcp_server.http_main [--transport streamable-http|sse]`
or the `mcp-server-http` console script.

All endpoints are public - no authentication required.
"""

from __future__ import annotations

import argparse
import logging

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route

from mcp_server.app import create_server
from mcp_server.config import Settings, load_settings

logger = logging.getLogger("mcp_server.http_main")


async def _health(_request: Request) -> Response:
    return JSONResponse({"status": "ok"})


LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KingBuilds MCP Server</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #333; }
        h1 { color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 0.5rem; }
        h2 { color: #1a1a2e; border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3rem; margin-top: 2.5rem; }
        h3 { color: #e94560; margin-top: 0; }
        code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }
        pre { background: #1a1a2e; color: #eaeaea; padding: 1rem; border-radius: 8px; overflow-x: auto; }
        .badge { display: inline-block; background: #e94560; color: white; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; margin-left: 0.5rem; }
        .endpoint { background: #f8f9fa; border-left: 4px solid #e94560; padding: 1rem; margin: 1rem 0; border-radius: 0 8px 8px 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0; }
        .card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; transition: box-shadow 0.2s; }
        .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #e94560; font-size: 1.1rem; }
        footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e0e0e0; color: #666; font-size: 0.9rem; text-align: center; }
        a { color: #e94560; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .demo-panel { background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0; }
        .demo-panel h3 { margin-top: 0; }
        .demo-form { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }
        .demo-form select, .demo-form textarea { flex: 1; min-width: 200px; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 0.9rem; }
        .demo-form textarea { min-height: 100px; }
        .demo-form button { background: #e94560; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-weight: 600; }
        .demo-form button:hover { background: #c73650; }
        .demo-form button:disabled { background: #999; cursor: not-allowed; }
        .result { background: #1a1a2e; color: #eaeaea; padding: 1rem; border-radius: 8px; margin-top: 1rem; white-space: pre-wrap; font-family: monospace; font-size: 0.85rem; max-height: 400px; overflow: auto; }
        .result.error { background: #3d1a1a; color: #ff6b6b; }
        .example { background: #fff3cd; border: 1px solid #ffc107; padding: 0.75rem; border-radius: 6px; margin: 0.5rem 0; }
        .example summary { cursor: pointer; font-weight: 600; color: #856404; }
        .example pre { margin: 0.5rem 0 0; background: #1a1a2e; color: #eaeaea; }
        .soliven-ref { background: #e8f5e9; border: 1px solid #4caf50; border-radius: 8px; padding: 1.5rem; margin: 2rem 0; }
        .soliven-ref h3 { color: #2e7d32; margin-top: 0; }
        .soliven-ref code { background: #c8e6c9; }
        .tool-section { margin: 2rem 0; padding: 1.5rem; background: #fafafa; border-radius: 8px; }
        .tool-section h2 { margin-top: 0; border-bottom: none; padding-bottom: 0; }
        .badge-arch { background: #4caf50; }
        .status-badge { display: inline-block; background: #4caf50; color: white; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; margin-left: 0.5rem; }
    </style>
</head>
<body>
    <h1>KingBuilds MCP Server <span class="badge">v0.1.0</span> <span class="status-badge">LIVE</span></h1>
    <p>Production-ready Model Context Protocol server with 4 tools for file operations, web scraping, data transformation, and authenticated HTTP requests.</    <div class="soliven-ref">
        <h3>🏗️ Built on Soliven Architecture</h3>
        <p>This MCP server follows the same patterns as <strong>Soliven</strong> — the autonomous build agent running on this VPS. Key shared components:</p>
        <ul>
            <li><strong>Security-first design</strong> — Sandboxed file operations with path traversal protection (<code>security.py</code>)</li>
            <li><strong>SSRF-safe networking</strong> — Private/loopback/link-local IP blocking for all outbound requests (<code>net.py</code>)</li>
            <li><strong>Config-driven</strong> — Pydantic Settings with <code>MCP_</code> prefix, validated at startup (<code>config.py</code>)</li>
            <li><strong>Structured logging</strong> — Consistent format across all tools and transports</li>
            <li><strong>Dual transport</strong> — stdio (Claude Desktop) + HTTP/SSE (web clients) from same codebase</li>
            <li><strong>Testable by design</strong> — Security primitives isolated for unit testing</li>
        </ul>
        <p>See <code>src/mcp_server/security.py</code>, <code>src/mcp_server/net.py</code>, and <code>src/mcp_server/config.py</code> for the shared primitives.</p>
    </div>

    <div class="grid">
        <div class="card">
            <h3>📁 file_ops</h3>
            <p>Sandboxed read/write/list within <code>ALLOWED_DIR</code>. Path traversal blocked.</p>
        </div>
        <div class="card">
            <h3>🌐 web_scraper</h3>
            <p>Clean HTML extraction: title, text, links, or CSS selector matches. SSRF protected.</p>
        </div>
        <div class="card">
            <h3>🔄 data_transform</h3>
            <p>JSON ↔ CSV conversion + aggregations (sum, avg, min, max, count, unique).</p>
        </div>
        <div class="card">
            <h3>🔐 http_request</h3>
            <p>Authenticated outbound requests with SSRF protection (private IPs blocked).</p>
        </div>
    </div>

    <div class="endpoint">
        <strong>Endpoints:</strong>
        <ul>
            <li><code>GET /health</code> — Health check</li>
            <li><code>POST /mcp/</code> — MCP Streamable HTTP transport</li>
            <li><code>GET /mcp/sse</code> — SSE transport (legacy)</li>
        </ul>
    </div>

    <h2>🎮 Interactive Demo</h2>
    <p>Test the MCP tools directly from this page. Select a tool, edit the arguments, and click Execute.</p>

    <div class="demo-panel">
        <h3>Try It Now</h3>
        <form class="demo-form" id="demoForm">
            <select id="toolSelect" onchange="updateExample()">
                <option value="tools/list">📋 List All Tools</option>
                <option value="read_file">📁 read_file</option>
                <option value="write_file">📁 write_file</option>
                <option value="list_directory">📁 list_directory</option>
                <option value="scrape_web_page">🌐 scrape_web_page</option>
                <option value="transform_data">🔄 transform_data</option>
                <option value="http_request">🔐 http_request</option>
            </select>
            <textarea id="argsInput" placeholder='{"path": "README.md"}'></textarea>
            <button type="button" onclick="executeTool()">Execute</button>
        </form>
        <div id="result" class="result" style="display:none;"></div>
    </div>

    <h2>📝 Example Prompts for Each Tool</h2>

    <div class="tool-section">
        <h3>📁 file_ops</h3>
        <details class="example">
            <summary>Read a file</summary>
            <pre>{"name": "read_file", "arguments": {"path": "README.md"}}</pre>
        </details>
        <details class="example">
            <summary>Write a file</summary>
            <pre>{"name": "write_file", "arguments": {"path": "notes.txt", "content": "Hello from MCP!", "overwrite": true}}</pre>
        </details>
        <details class="example">
            <summary>List directory</summary>
            <pre>{"name": "list_directory", "arguments": {"path": "."}}</pre>
        </details>
        <p><strong>Prompt:</strong> "Read the README.md file and summarize it" or "Create a file called todo.txt with my task list"</p>
    </div>

    <div class="tool-section">
        <h3>🌐 web_scraper</h3>
        <details class="example">
            <summary>Scrape a page (full text)</summary>
            <pre>{"name": "scrape_web_page", "arguments": {"url": "https://example.com"}}</pre>
        </details>
        <details class="example">
            <summary>Extract with CSS selector</summary>
            <pre>{"name": "scrape_web_page", "arguments": {"url": "https://news.ycombinator.com", "selector": ".titleline a", "max_links": 10}}</pre>
        </details>
        <p><strong>Prompt:</strong> "Fetch the latest headlines from Hacker News" or "Get the title and main text from this article URL"</p>
    </div>

    <div class="tool-section">
        <h3>🔄 data_transform</h3>
        <details class="example">
            <summary>JSON to CSV</summary>
            <pre>{"name": "transform_data", "arguments": {"data": "[{\"name\": \"Alice\", \"age\": 30}, {\"name\": \"Bob\", \"age\": 25}]", "input_format": "json", "operation": "convert", "output_format": "csv"}}</pre>
        </details>
        <details class="example">
            <summary>Sum numbers</summary>
            <pre>{"name": "transform_data", "arguments": {"data": "[10, 20, 30, 40, 50]", "input_format": "json", "operation": "sum"}}</pre>
        </details>
        <details class="example">
            <summary>Average with field</summary>
            <pre>{"name": "transform_data", "arguments": {"data": "[{\"score\": 85}, {\"score\": 92}, {\"score\": 78}]", "input_format": "json", "operation": "average", "field": "score"}}</pre>
        </details>
        <p><strong>Prompt:</strong> "Convert this JSON data to CSV" or "Calculate the average score from this data"</p>
    </div>

    <div class="tool-section">
        <h3>🔐 http_request</h3>
        <details class="example">
            <summary>GET request</summary>
            <pre>{"name": "http_request", "arguments": {"method": "GET", "url": "https://api.github.com/users/octocat"}}</pre>
        </details>
        <details class="example">
            <summary>POST with Bearer auth</summary>
            <pre>{"name": "http_request", "arguments": {"method": "POST", "url": "https://api.example.com/data", "headers": {"Content-Type": "application/json"}, "body": {"key": "value"}, "auth": {"scheme": "bearer", "token": "your-token-here"}}}</pre>
        </details>
        <p><strong>Prompt:</strong> "Call this API endpoint and return the JSON response" or "POST this data to the webhook"</p>
    </div>

    <div class="endpoint">
        <strong>Claude Desktop Config:</strong>
        <pre><code>{
  "mcpServers": {
    "kingbuilds-mcp": {
      "command": "mcp-server-stdio",
      "env": { "ALLOWED_DIR": "/home/user/data" }
    }
  }
}</code></pre>
    </div>

    <div class="endpoint">
        <strong>Quick Test (HTTP):</strong>
        <pre><code>curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'</code></pre>
    </div>

    <footer>
        Built by <a href="https://kingbuilds.dev">KingBuilds</a> • 
        <a href="https://github.com/Emberphoenix33">GitHub</a> •
        <a href="https://upwork.com/freelancers/emberphoenix33">Upwork</a>
    </footer>

    <script>
        const examples = {
            "tools/list": {},
            "read_file": {"path": "README.md"},
            "write_file": {"path": "demo.txt", "content": "Hello from KingBuilds MCP!", "overwrite": true},
            "list_directory": {"path": "."},
            "scrape_web_page": {"url": "https://example.com"},
            "transform_data": {"data": "[1,2,3,4,5]", "input_format": "json", "operation": "sum"},
            "http_request": {"method": "GET", "url": "https://api.github.com/users/octocat"}
        };

        function updateExample() {
            const tool = document.getElementById('toolSelect').value;
            const args = examples[tool] || {};
            document.getElementById('argsInput').value = JSON.stringify(args, null, 2);
        }

        async function executeTool() {
            const tool = document.getElementById('toolSelect').value;
            const argsText = document.getElementById('argsInput').value;
            const resultDiv = document.getElementById('result');

            let args;
            try {
                args = JSON.parse(argsText);
            } catch (e) {
                resultDiv.textContent = "Error: Invalid JSON in arguments\n" + e.message;
                resultDiv.className = "result error";
                resultDiv.style.display = "block";
                return;
            }

            const payload = tool === "tools/list"
                ? {"jsonrpc": "2.0", "id": Date.now(), "method": "tools/list"}
                : {"jsonrpc": "2.0", "id": Date.now(), "method": "tools/call", "params": {"name": tool, "arguments": args}};

            resultDiv.textContent = "Executing...";
            resultDiv.className = "result";
            resultDiv.style.display = "block";

            try {
                const response = await fetch("/mcp/", {
                    method: "POST",
                    headers: {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                    body: JSON.stringify(payload)
                });

                const contentType = response.headers.get("content-type") || "";
                let data;

                if (contentType.includes("text/event-stream")) {
                    // SSE stream - read first event
                    const text = await response.text();
                    const lines = text.split("\n");
                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            data = JSON.parse(line.slice(6));
                            break;
                        }
                    }
                } else {
                    data = await response.json();
                }

                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.className = data?.error ? "result error" : "result";
            } catch (e) {
                resultDiv.textContent = "Request failed: " + e.message;
                resultDiv.className = "result error";
            }
        }

        // Initialize
        updateExample();
    </script>
</body>
</html>"""


async def landing_page(request):
    return HTMLResponse(LANDING_PAGE)


def build_app(transport: str = "streamable-http", settings: Settings | None = None) -> Starlette:
    settings = settings or load_settings()
    mcp = create_server(settings)

    if transport == "sse":
        mcp_app = mcp.sse_app()
    elif transport == "streamable-http":
        mcp_app = mcp.streamable_http_app()
    else:
        raise ValueError(f"Unsupported HTTP transport: {transport!r} (expected 'streamable-http' or 'sse')")

    # Public routes (no auth)
    public_app = Starlette(
        routes=[
            Route("/", landing_page, methods=["GET"]),
            Route("/health", _health, methods=["GET"]),
        ]
    )

    # No auth - all endpoints public
    logger.info("HTTP transport auth DISABLED - all endpoints public")

    # Mount MCP app at root to get /mcp and /mcp/sse endpoints
    public_app.router.routes.insert(0, Mount("/", app=mcp_app))

    return public_app


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
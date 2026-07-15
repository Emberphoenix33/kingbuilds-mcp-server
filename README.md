# KingBuilds MCP Server

Production-ready reference MCP server with 4 tools:
- **file_ops** — Sandboxed file read/write/list within allowed directory
- **web_scraper** — Clean HTML extraction (title, text, links, CSS selectors)
- **data_transform** — JSON↔CSV conversion + aggregation (sum/avg/count/min/max/filter/sort)
- **http_request** — Authenticated HTTP requests with SSRF protection

## Architecture

This server is built on the **Soliven architecture** — the autonomous build agent running on this VPS. Shared patterns:

| Component | Purpose | Soliven Reference |
|-----------|---------|-------------------|
| `security.py` | Path traversal protection, SSRF-safe URL validation | Soliven sandbox |
| `net.py` | Safe HTTP client with redirect validation | Soliven outbound requests |
| `config.py` | Pydantic Settings with `MCP_` prefix, validated at startup | Soliven config |
| Dual transport | stdio (Claude Desktop) + HTTP/SSE (web) | Soliven multi-interface |
| Structured logging | Consistent format across all tools | Soliven observability |

## Quickstart

```bash
# Install
pip install -e .

# Run stdio transport (for Claude Desktop)
mcp-server-stdio

# Run HTTP/SSE server
mcp-server-http
```

## Configuration

Environment variables:
- `ALLOWED_DIR` — Sandbox directory for file operations (default: `./data`)
- `MCP_TRANSPORT` — `stdio` or `streamable-http` (default: `streamable-http`)
- `MCP_HOST` — Host to bind (default: `0.0.0.0`)
- `MCP_PORT` — Port for HTTP transport (default: `8080`)
- `MAX_FILE_BYTES` — Max file size for read/write (default: `1048576`)
- `REQUEST_TIMEOUT` — HTTP request timeout seconds (default: `30`)

## Tools

### file_ops
- `read_file(path: str)` — Read UTF-8 text file
- `write_file(path: str, content: str, overwrite: bool)` — Write file
- `list_directory(path: str)` — List directory contents

**Example prompts:**
- "Read the README.md file and summarize it"
- "Create a file called todo.txt with my task list"
- "List all files in the data directory"

### web_scraper
- `fetch_page(url: str, selector: str = None)` — Fetch and extract HTML content

**Example prompts:**
- "Fetch the latest headlines from Hacker News"
- "Get the title and main text from this article URL"
- "Extract all links from this page matching `.titleline a`"

### data_transform
- `transform_data(data: list, operation: str, **kwargs)` — Transform data

**Example prompts:**
- "Convert this JSON data to CSV"
- "Calculate the average score from this data"
- "Sum these numbers: [10, 20, 30, 40, 50]"
- "Count unique values in the 'category' field"

### http_request
- `http_request(method: str, url: str, headers: dict, body: dict, auth: dict)` — Make HTTP requests

**Example prompts:**
- "Call this API endpoint and return the JSON response"
- "POST this data to the webhook with Bearer auth"

## Example Tool Calls (MCP JSON-RPC)

### file_ops
```json
{"name": "read_file", "arguments": {"path": "README.md"}}
{"name": "write_file", "arguments": {"path": "notes.txt", "content": "Hello from MCP!", "overwrite": true}}
{"name": "list_directory", "arguments": {"path": "."}}
```

### web_scraper
```json
{"name": "scrape_web_page", "arguments": {"url": "https://example.com"}}
{"name": "scrape_web_page", "arguments": {"url": "https://news.ycombinator.com", "selector": ".titleline a", "max_links": 10}}
```

### data_transform
```json
{"name": "transform_data", "arguments": {"data": "[{\"name\": \"Alice\", \"age\": 30}, {\"name\": \"Bob\", \"age\": 25}]", "input_format": "json", "operation": "convert", "output_format": "csv"}}
{"name": "transform_data", "arguments": {"data": "[10, 20, 30, 40, 50]", "input_format": "json", "operation": "sum"}}
{"name": "transform_data", "arguments": {"data": "[{\"score\": 85}, {\"score\": 92}, {\"score\": 78}]", "input_format": "json", "operation": "average", "field": "score"}}
```

### http_request
```json
{"name": "http_request", "arguments": {"method": "GET", "url": "https://api.github.com/users/octocat"}}
{"name": "http_request", "arguments": {"method": "POST", "url": "https://api.example.com/data", "headers": {"Content-Type": "application/json"}, "body": {"key": "value"}, "auth": {"scheme": "bearer", "token": "your-token-here"}}}
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "kingbuilds-mcp": {
      "command": "mcp-server-stdio",
      "env": {
        "ALLOWED_DIR": "/home/user/data"
      }
    }
  }
}
```

## Deployment

```bash
# Docker
docker-compose up -d

# Systemd
sudo cp deploy/systemd/claude-mcp-server.service /etc/systemd/system/
sudo systemctl enable --now claude-mcp-server
```

## Security

- File operations sandboxed to `ALLOWED_DIR` with path traversal protection
- SSRF protection: private/loopback/link-local IPs blocked by default
- Request size/timeouts enforced
- Input validation on all tool inputs

## License

MIT
# KingBuilds MCP Server

Production-ready reference MCP server with 4 tools:
- **file_ops** — Sandboxed file read/write/list within allowed directory
- **web_scraper** — Clean HTML extraction (title, text, links, CSS selectors)
- **data_transform** — JSON↔CSV conversion + aggregation (sum/avg/count/min/max/filter/sort)
- **http_request** — Authenticated HTTP requests with SSRF protection

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

### web_scraper
- `fetch_page(url: str, selector: str = None)` — Fetch and extract HTML content

### data_transform
- `transform_data(data: list, operation: str, **kwargs)` — Transform data

### http_request
- `http_request(method: str, url: str, headers: dict, body: dict, auth: dict)` — Make HTTP requests

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
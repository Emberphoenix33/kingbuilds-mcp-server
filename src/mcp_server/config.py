"""Central configuration for the MCP server, sourced from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All fields can be set via environment variables
    (or a `.env` file) using the `MCP_` prefix, e.g. `MCP_ALLOWED_DIR=/data`.
    """

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        extra="ignore",
    )

    # --- File tool sandbox ---
    allowed_dir: Path = Field(
        default=Path.cwd(),
        description="Absolute directory that the file tool is restricted to.",
    )
    max_file_bytes: int = Field(
        default=5 * 1024 * 1024,
        description="Maximum file size (bytes) the file tool will read or write.",
    )

    # --- Outbound network (web scraping + http request tools) ---
    http_timeout_seconds: float = Field(default=15.0, description="Per-request timeout for outbound HTTP calls.")
    max_response_bytes: int = Field(
        default=2 * 1024 * 1024,
        description="Maximum response body size read from any outbound HTTP call.",
    )
    max_redirects: int = Field(default=5, description="Maximum redirect hops followed for outbound HTTP calls.")
    user_agent: str = Field(
        default="claude-mcp-server/0.1 (+https://modelcontextprotocol.io)",
        description="User-Agent header sent on outbound HTTP calls.",
    )
    allowed_url_schemes: tuple[str, ...] = Field(default=("http", "https"))
    outbound_host_allowlist: tuple[str, ...] = Field(
        default=(),
        description=(
            "If non-empty, outbound HTTP/web requests are restricted to these hostnames "
            "(exact match or subdomain). Empty means 'any public host' (still SSRF-filtered)."
        ),
    )

    # --- HTTP request tool credentials ---
    http_tool_auth_scheme: str = Field(
        default="bearer",
        description="Auth scheme the http_request tool injects: 'bearer', 'api_key', or 'none'.",
    )
    http_tool_auth_token: str | None = Field(
        default=None,
        description="Credential injected by the http_request tool. Never exposed to the model.",
    )
    http_tool_api_key_header: str = Field(
        default="X-API-Key",
        description="Header name used when http_tool_auth_scheme == 'api_key'.",
    )

    # --- HTTP/SSE transport auth (protects the MCP server endpoint itself) ---
    server_auth_token: str | None = Field(
        default=None,
        description="If set, the HTTP/SSE transport requires 'Authorization: Bearer <token>'.",
    )
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)

    log_level: str = Field(default="INFO")

    @field_validator("allowed_dir", mode="after")
    @classmethod
    def _resolve_allowed_dir(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("http_tool_auth_scheme", mode="after")
    @classmethod
    def _validate_scheme(cls, value: str) -> str:
        allowed = {"bearer", "api_key", "none"}
        if value not in allowed:
            raise ValueError(f"http_tool_auth_scheme must be one of {allowed}, got {value!r}")
        return value


def load_settings() -> Settings:
    """Load settings from the environment, ensuring the sandbox directory exists."""
    settings = Settings()
    settings.allowed_dir.mkdir(parents=True, exist_ok=True)
    return settings

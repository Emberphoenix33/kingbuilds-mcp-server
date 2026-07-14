"""File operations tool: read / write / list, sandboxed to a single directory.

Every path supplied by the model is resolved through
`security.safe_resolve_path`, which rejects any attempt (via `..`, an
absolute-path override, or a symlink) to escape `settings.allowed_dir`.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.config import Settings
from mcp_server.security import SecurityError, safe_resolve_path

logger = logging.getLogger("mcp_server.tools.files")

_TEXT_ENCODING = "utf-8"


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="read_file",
        description=(
            "Read a UTF-8 text file from within the server's sandboxed directory "
            f"({settings.allowed_dir}). Path is relative to that directory. "
            "Refuses files above the configured size limit or outside the sandbox."
        ),
    )
    def read_file(path: str) -> dict[str, Any]:
        try:
            resolved = safe_resolve_path(settings.allowed_dir, path)
        except SecurityError as exc:
            logger.warning("read_file blocked: %s", exc)
            return {"error": str(exc)}

        if not resolved.exists():
            return {"error": f"File not found: {path}"}
        if not resolved.is_file():
            return {"error": f"Not a regular file: {path}"}

        size = resolved.stat().st_size
        if size > settings.max_file_bytes:
            return {
                "error": (
                    f"File is {size} bytes, exceeding the {settings.max_file_bytes}-byte limit"
                )
            }

        try:
            content = resolved.read_text(encoding=_TEXT_ENCODING)
        except UnicodeDecodeError:
            return {"error": "File is not valid UTF-8 text"}

        logger.info("read_file: %s (%d bytes)", resolved, size)
        return {"path": str(resolved.relative_to(settings.allowed_dir)), "content": content, "size_bytes": size}

    @mcp.tool(
        name="write_file",
        description=(
            "Write UTF-8 text to a file within the server's sandboxed directory "
            f"({settings.allowed_dir}). Path is relative to that directory. "
            "Creates parent directories as needed; refuses to write outside the sandbox "
            "or above the configured size limit."
        ),
    )
    def write_file(path: str, content: str, overwrite: bool = True) -> dict[str, Any]:
        encoded_size = len(content.encode(_TEXT_ENCODING))
        if encoded_size > settings.max_file_bytes:
            return {
                "error": (
                    f"Content is {encoded_size} bytes, exceeding the {settings.max_file_bytes}-byte limit"
                )
            }

        try:
            resolved = safe_resolve_path(settings.allowed_dir, path)
        except SecurityError as exc:
            logger.warning("write_file blocked: %s", exc)
            return {"error": str(exc)}

        if resolved.exists() and resolved.is_dir():
            return {"error": f"Path is a directory: {path}"}
        if resolved.exists() and not overwrite:
            return {"error": f"File already exists and overwrite=False: {path}"}

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding=_TEXT_ENCODING)

        logger.info("write_file: %s (%d bytes)", resolved, encoded_size)
        return {
            "path": str(resolved.relative_to(settings.allowed_dir)),
            "bytes_written": encoded_size,
        }

    @mcp.tool(
        name="list_directory",
        description=(
            "List files and subdirectories within the server's sandboxed directory "
            f"({settings.allowed_dir}). Path is relative to that directory ('' or '.' for the root)."
        ),
    )
    def list_directory(path: str = ".") -> dict[str, Any]:
        try:
            resolved = safe_resolve_path(settings.allowed_dir, path)
        except SecurityError as exc:
            logger.warning("list_directory blocked: %s", exc)
            return {"error": str(exc)}

        if not resolved.exists():
            return {"error": f"Directory not found: {path}"}
        if not resolved.is_dir():
            return {"error": f"Not a directory: {path}"}

        entries = []
        for entry in sorted(resolved.iterdir(), key=lambda p: p.name):
            entries.append(
                {
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size_bytes": entry.stat().st_size if entry.is_file() else None,
                }
            )

        logger.info("list_directory: %s (%d entries)", resolved, len(entries))
        return {"path": str(resolved.relative_to(settings.allowed_dir)), "entries": entries}

"""Shared security primitives: filesystem sandboxing and SSRF-safe URL validation.

These helpers are deliberately dependency-light so they can be unit tested in
isolation from the MCP protocol plumbing and from any specific tool.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class SecurityError(ValueError):
    """Raised when a requested operation would violate a sandbox or SSRF policy."""


# --------------------------------------------------------------------------
# Filesystem sandbox
# --------------------------------------------------------------------------


def safe_resolve_path(allowed_dir: Path | str, requested_path: str) -> Path:
    """Resolve `requested_path` (relative or absolute) against `allowed_dir`,
    guaranteeing the result stays inside `allowed_dir` even in the presence of
    `..` segments, absolute-path overrides, or symlinks that point outside.

    Raises SecurityError if the resolved path escapes the sandbox.
    """
    allowed_dir = Path(allowed_dir).expanduser().resolve()

    candidate = Path(requested_path)
    # Treat the incoming path as relative to the sandbox root even if the
    # caller supplied a leading "/" — an absolute path must not let a client
    # opt out of the sandbox entirely. If the path is absolute, we strip the
    # anchor and treat the remainder as relative to the sandbox root.
    if candidate.is_absolute():
        candidate = candidate.relative_to(candidate.anchor)
    
    combined = allowed_dir / candidate

    # os.path.realpath / Path.resolve follows symlinks; strict=False lets us
    # validate paths that don't exist yet (needed for write_file).
    resolved = combined.resolve(strict=False)

    try:
        resolved.relative_to(allowed_dir)
    except ValueError:
        raise SecurityError(
            f"Path '{requested_path}' resolves outside the allowed directory '{allowed_dir}'"
        ) from None

    return resolved


# --------------------------------------------------------------------------
# SSRF-safe outbound URL validation
# --------------------------------------------------------------------------

# Networks that must never be reachable from server-side tool calls, even if
# a hostname resolves there. Covers loopback, link-local (incl. the cloud
# metadata address 169.254.169.254), RFC1918 private space, CGNAT, multicast,
# unspecified, and reserved ranges.
_BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local, incl. cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("240.0.0.0/4"),  # reserved
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("64:ff9b::/96"),  # NAT64 (can carry mapped IPv4)
    ipaddress.ip_network("fc00::/7"),  # unique local
    ipaddress.ip_network("fe80::/10"),  # link-local
)


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return True
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return any(ip in network for network in _BLOCKED_NETWORKS)


@dataclass(frozen=True)
class ValidatedUrl:
    """A URL that has passed scheme/host/IP validation."""

    url: str
    hostname: str
    resolved_ips: tuple[str, ...]


def validate_public_url(
    url: str,
    *,
    allowed_schemes: tuple[str, ...] = ("http", "https"),
    host_allowlist: tuple[str, ...] = (),
) -> ValidatedUrl:
    """Validate that `url` is safe to fetch from server-side code.

    Rejects:
      - non-allowlisted schemes
      - embedded credentials (http://user:pass@host)
      - missing hostname
      - hostnames not in `host_allowlist` (when non-empty; exact or subdomain match)
      - hostnames that resolve (via DNS or IP literal) to any private/loopback/
        link-local/reserved/multicast address

    Returns the parsed hostname and the resolved IPs on success. Callers that
    follow redirects MUST call this again on every redirect target — a single
    upfront check does not protect a request that is later redirected
    somewhere unsafe.
    """
    parts = urlsplit(url)

    if parts.scheme not in allowed_schemes:
        raise SecurityError(f"URL scheme '{parts.scheme}' is not allowed (allowed: {allowed_schemes})")

    if parts.username or parts.password:
        raise SecurityError("URLs with embedded credentials are not allowed")

    hostname = parts.hostname
    if not hostname:
        raise SecurityError("URL has no hostname")

    if host_allowlist:
        normalized = hostname.lower()
        if not any(normalized == h.lower() or normalized.endswith("." + h.lower()) for h in host_allowlist):
            raise SecurityError(f"Host '{hostname}' is not in the outbound host allowlist")

    # If the hostname is itself an IP literal, ipaddress.ip_address handles it.
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    resolved_ips: list[str] = []
    if literal_ip is not None:
        if _is_blocked_ip(literal_ip):
            raise SecurityError(f"Host resolves to a disallowed address: {literal_ip}")
        resolved_ips.append(str(literal_ip))
    else:
        try:
            addr_infos = socket.getaddrinfo(hostname, parts.port or (443 if parts.scheme == "https" else 80))
        except socket.gaierror as exc:
            raise SecurityError(f"Could not resolve host '{hostname}': {exc}") from exc

        if not addr_infos:
            raise SecurityError(f"Host '{hostname}' did not resolve to any address")

        for family, _, _, _, sockaddr in addr_infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if _is_blocked_ip(ip):
                raise SecurityError(
                    f"Host '{hostname}' resolves to a disallowed address ({ip}); refusing to fetch"
                )
            resolved_ips.append(str(ip))

    return ValidatedUrl(url=url, hostname=hostname, resolved_ips=tuple(resolved_ips))

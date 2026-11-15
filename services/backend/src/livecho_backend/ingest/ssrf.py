"""Offline SSRF-safe URL validation. Never opens sockets."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]+(?:\.[a-z0-9-]+)+$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class UrlPolicy:
    allowed_hosts: frozenset[str]
    allowed_schemes: frozenset[str] = frozenset({"https"})
    max_redirects: int = 3
    allow_nondefault_ports: bool = False


@dataclass(frozen=True, slots=True)
class UrlDecision:
    accepted: bool
    reason: str
    host: str | None = None


def _is_blocked_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or ip.compressed in {"169.254.169.254"}
        or (ip.version == 4 and ip.packed[0] == 0)
    )


def validate_url(url: str, policy: UrlPolicy) -> UrlDecision:
    if not isinstance(url, str) or not url or len(url) > 2048:
        return UrlDecision(False, "url_invalid")
    # Reject credentials / userinfo early even before parse quirks.
    if "@" in url.split("://", 1)[-1].split("/", 1)[0]:
        return UrlDecision(False, "userinfo_forbidden")
    parts = urlsplit(url)
    if parts.scheme.lower() not in policy.allowed_schemes:
        return UrlDecision(False, "scheme_forbidden")
    if parts.username is not None or parts.password is not None:
        return UrlDecision(False, "userinfo_forbidden")
    host = parts.hostname
    if host is None or host == "":
        return UrlDecision(False, "host_missing")
    host_l = host.lower().rstrip(".")
    if host_l in {"localhost"} or host_l.endswith(".localhost"):
        return UrlDecision(False, "host_blocked")
    if _is_blocked_ip(host_l):
        return UrlDecision(False, "host_blocked")
    # Literal IPs are never allowlisted for this fixture policy.
    try:
        ipaddress.ip_address(host_l)
        return UrlDecision(False, "host_blocked")
    except ValueError:
        pass
    if not _HOSTNAME.fullmatch(host_l):
        return UrlDecision(False, "host_invalid")
    if host_l not in {h.lower() for h in policy.allowed_hosts}:
        return UrlDecision(False, "host_not_allowlisted")
    port = parts.port
    if port is not None:
        default = 443 if parts.scheme.lower() == "https" else 80
        if port != default and not policy.allow_nondefault_ports:
            return UrlDecision(False, "port_forbidden")
    if parts.fragment:
        return UrlDecision(False, "fragment_forbidden")
    return UrlDecision(True, "accepted", host=host_l)


def validate_redirect_target(
    location: str,
    policy: UrlPolicy,
    *,
    hop: int,
) -> UrlDecision:
    if hop >= policy.max_redirects:
        return UrlDecision(False, "redirect_limit")
    return validate_url(location, policy)

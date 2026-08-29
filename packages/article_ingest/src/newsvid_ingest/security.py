from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from .errors import ArticleExtractionError


def assert_public_http_url(raw: str, *, resolve_dns: bool = True) -> str:
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ArticleExtractionError("Only public HTTP(S) article URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise ArticleExtractionError("Article URLs must not contain credentials")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ArticleExtractionError(f"Refusing local article host: {host}")
    addresses: set[str] = set()
    try:
        addresses.add(str(ipaddress.ip_address(host)))
    except ValueError:
        if resolve_dns:
            try:
                addresses.update(item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443))
            except socket.gaierror as exc:
                raise ArticleExtractionError(f"Article host could not be resolved: {host}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ArticleExtractionError(f"Refusing non-public article address: {address}")
    return raw

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

import requests


_configs = {}


def _normalize_issuer(issuer):
    parsed = urlparse(issuer)
    if parsed.scheme != "https":
        raise ValueError("Invalid issuer")

    if not parsed.netloc or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("Invalid issuer")

    hostname = parsed.hostname
    if not hostname or hostname.rstrip(".").lower() == "localhost":
        raise ValueError("Invalid issuer")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError("Invalid issuer")

    for _, _, _, _, sockaddr in addrinfo:
        address = ipaddress.ip_address(sockaddr[0])
        if not address.is_global:
            raise ValueError("Invalid issuer")

    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def fetch_openid_config(issuer):
    global _configs

    normalized_issuer = _normalize_issuer(issuer)

    if normalized_issuer not in _configs:
        resp = requests.get(normalized_issuer + "/.well-known/openid-configuration")
        _configs[normalized_issuer] = resp.json()

    return _configs[normalized_issuer]

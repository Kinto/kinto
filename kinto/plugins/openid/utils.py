import fnmatch
import string
from typing import Any
from urllib.parse import urlsplit

import requests


_configs: dict[str, Any] = {}


def fetch_openid_config(issuer: str) -> Any:
    global _configs

    if issuer not in _configs:
        resp = requests.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
        _configs[issuer] = resp.json()

    return _configs[issuer]


# Local ports are used by command-line clients (eg. ``kinto-http`` browser login).
DEFAULT_TRUSTED_LOCAL_CALLBACK_URLS = ("http://localhost:*/*", "http://127.0.0.1:*/*")

DEFAULT_PORTS = {"http": "80", "https": "443"}

# ``urlsplit()`` is more indulgent than browsers (eg. ``https://evil.com\.trusted.com``
# is parsed with hostname ``evil.com\.trusted.com``, but browsers go to ``evil.com``).
# So we only accept these characters in hostnames and ports (``*`` for wildcards).
HOSTNAME_CHARS = set(string.ascii_lowercase + string.digits + ".-*")
IPV6_CHARS = set(string.hexdigits.lower() + ":.")
PORT_CHARS = set(string.digits + "*")


def _url_parts(url: str) -> tuple[str, str, str, str] | None:
    # ``urlsplit()`` silently strips whitespace and control characters.
    if any(c.isspace() or not c.isprintable() for c in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in DEFAULT_PORTS or "@" in parts.netloc:
        return None

    # Lowercased, and without brackets for IPv6 (eg. ``[::1]`` gives ``::1``).
    host = parts.hostname or ""
    allowed_chars = IPV6_CHARS if parts.netloc.startswith("[") else HOSTNAME_CHARS
    if not host or not set(host).issubset(allowed_chars):
        return None

    # Read the port as text, since ``parts.port`` fails with wildcards.
    # (eg. ``localhost:8000`` or ``[::1]:8000``)
    after_host = parts.netloc.rsplit("]", 1)[-1]
    _, _, port = after_host.partition(":")
    if not set(port).issubset(PORT_CHARS):
        return None
    port = port or DEFAULT_PORTS[parts.scheme]

    # Path, querystring and fragment, as is.
    rest = url[len(parts.scheme) + len("://") + len(parts.netloc) :] or "/"
    return parts.scheme, host, port, rest


def _match(value: str, pattern: str) -> bool:
    # We use filename matching with ``*`` like on shell.
    # Unlike normal regexp, only ``*`` is a wildcard. (eg. brackets
    # and querystrings ? are literal).
    return fnmatch.fnmatchcase(value, pattern.replace("[", "[[]").replace("?", "[?]"))


def is_trusted_callback(callback: str, trusted_urls: list[str]) -> bool:
    """Return ``True`` if the ``callback`` URL matches one of the ``trusted_urls``
    patterns, where ``*`` acts as a wildcard in host, port, and path.
    """
    callback_parts = _url_parts(callback)
    if callback_parts is None:
        return False
    cb_scheme, cb_host, cb_port, cb_rest = callback_parts

    for trusted_url in trusted_urls:
        trusted_parts = _url_parts(trusted_url)
        if trusted_parts is None:
            continue
        t_scheme, t_host, t_port, t_rest = trusted_parts
        if (
            cb_scheme == t_scheme
            and _match(cb_host, t_host)
            and _match(cb_port, t_port)
            and _match(cb_rest, t_rest)
        ):
            return True
    return False

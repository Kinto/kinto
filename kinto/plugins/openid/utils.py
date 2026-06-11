from typing import Any

import requests


_configs: dict[str, Any] = {}


def fetch_openid_config(issuer: str) -> Any:
    global _configs

    if issuer not in _configs:
        resp = requests.get(issuer.rstrip("/") + "/.well-known/openid-configuration")
        _configs[issuer] = resp.json()

    return _configs[issuer]

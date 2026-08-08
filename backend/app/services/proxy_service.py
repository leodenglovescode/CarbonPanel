from __future__ import annotations

import urllib.request
from typing import Any

from app.services.settings_store import get_key, set_key

DEFAULT_PROXY: dict[str, Any] = {
    "enabled": False,
    "type": "http",
    "host": "127.0.0.1",
    "port": 7890,
}


def get_proxy() -> dict[str, Any]:
    return get_key("proxy", dict(DEFAULT_PROXY))


def set_proxy(config: dict[str, Any]) -> None:
    set_key("proxy", config)


def build_opener() -> urllib.request.OpenerDirector | None:
    """Return a configured opener for the saved proxy, or None if disabled."""
    cfg = get_proxy()
    if not cfg.get("enabled"):
        return None

    proxy_type = cfg.get("type", "http")
    host = str(cfg.get("host", "127.0.0.1"))
    port = int(cfg.get("port", 7890))

    if proxy_type == "http":
        proxy_url = f"http://{host}:{port}"
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )

    if proxy_type == "socks5":
        try:
            import socks
            from sockshandler import SocksiPyHandler  # provided by PySocks
        except ImportError as exc:
            raise RuntimeError(
                "PySocks is required for SOCKS5 proxy support. "
                "Install it with: pip install PySocks"
            ) from exc
        return urllib.request.build_opener(SocksiPyHandler(socks.SOCKS5, host, port))

    return None

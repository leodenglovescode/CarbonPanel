from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

_SETTINGS_FILE = Path(
    os.getenv(
        "CARBONPANEL_SETTINGS_FILE",
        str(Path.home() / ".config" / "carbonpanel" / "settings.json"),
    )
)

DEFAULT_PROXY: dict[str, Any] = {
    "enabled": False,
    "type": "http",
    "host": "127.0.0.1",
    "port": 7890,
}


def _read() -> dict[str, Any]:
    try:
        return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(data: dict[str, Any]) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_proxy() -> dict[str, Any]:
    return _read().get("proxy", dict(DEFAULT_PROXY))


def set_proxy(config: dict[str, Any]) -> None:
    data = _read()
    data["proxy"] = config
    _write(data)


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

import asyncio
import ipaddress
import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse to follow redirects — a validated URL could otherwise redirect
    to a blocked address (e.g. cloud metadata) after the SSRF check passes."""

    def redirect_request(self, *args, **kwargs):
        return None


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # can't parse — fail closed
    # Loopback (127.0.0.0/8, ::1) + link-local (169.254.0.0/16, fe80::/10 —
    # covers the AWS/GCP/Azure/DO cloud metadata address on every provider).
    # Deliberately NOT blocking RFC1918/private ranges — self-hosted webhook
    # targets (ntfy, Gotify, Home Assistant, etc.) commonly live on the LAN.
    return ip.is_loopback or ip.is_link_local


def _validate_webhook_host(url: str) -> None:
    # ponytail: resolve-then-check, not IP-pinned — closes the common case
    # (literal loopback/metadata URL, or a hostname that resolves there), not
    # a fully DNS-rebinding-proof SSRF defense. Upgrade if that threat matters here.
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Webhook URL must be http or https")
    host = parsed.hostname
    if not host:
        raise ValueError("Webhook URL has no host")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve webhook host: {exc}")
    for info in infos:
        if _is_blocked_ip(info[4][0]):
            raise ValueError(f"Webhook host resolves to a blocked address ({info[4][0]})")


async def get_all(db: AsyncSession) -> list[Webhook]:
    result = await db.execute(select(Webhook))
    return list(result.scalars().all())


def _post_sync(url: str, body: str) -> None:
    try:
        _validate_webhook_host(url)
    except ValueError as exc:
        logger.warning("Webhook delivery blocked for %s: %s", url, exc)
        return
    data = body.encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Content-Length": str(len(data))},
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=8):
            pass
    except Exception as exc:
        logger.warning("Webhook delivery failed for %s: %s", url, exc)


async def fire_event(db: AsyncSession, event: str, payload: dict[str, Any]) -> None:
    hooks = await get_all(db)
    enabled = [h for h in hooks if h.enabled and event in h.events.split(",")]
    if not enabled:
        return

    body = json.dumps({
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    })

    loop = asyncio.get_event_loop()
    await asyncio.gather(
        *[loop.run_in_executor(None, _post_sync, h.url, body) for h in enabled],
        return_exceptions=True,
    )

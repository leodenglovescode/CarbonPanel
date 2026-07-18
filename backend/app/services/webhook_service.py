import asyncio
import contextlib
import ipaddress
import json
import logging
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)

# DNS-pinning to close the resolve-then-connect TOCTOU: a short-TTL DNS
# record could otherwise resolve to a public IP for `_validate_webhook_host`
# and then to 127.0.0.1/169.254.169.254 for the real connect a moment later.
# Pinning is thread-local (not a global override) so concurrent webhook
# deliveries — fired in parallel via asyncio.gather/run_in_executor — can't
# race and apply one delivery's pinned IP to another's hostname. The Host
# header / TLS SNI still use the original hostname (only the low-level
# getaddrinfo() call is redirected), so certificate validation is unaffected.
_real_getaddrinfo = socket.getaddrinfo
_dns_pin = threading.local()


def _pinned_getaddrinfo(host, *args, **kwargs):
    pin = getattr(_dns_pin, "target", None)
    if pin is not None and host == pin[0]:
        host = pin[1]
    return _real_getaddrinfo(host, *args, **kwargs)


socket.getaddrinfo = _pinned_getaddrinfo


@contextlib.contextmanager
def _pin_dns(hostname: str, ip: str):
    _dns_pin.target = (hostname, ip)
    try:
        yield
    finally:
        _dns_pin.target = None


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


def _validate_webhook_host(url: str) -> tuple[str, str]:
    """Validate the URL's host resolves only to non-blocked addresses.
    Returns (hostname, first_resolved_ip) so the caller can pin the actual
    connection to the exact address that was checked here."""
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
    if not infos:
        raise ValueError("Could not resolve webhook host")
    for info in infos:
        if _is_blocked_ip(info[4][0]):
            raise ValueError(f"Webhook host resolves to a blocked address ({info[4][0]})")
    return host, infos[0][4][0]


async def get_all(db: AsyncSession) -> list[Webhook]:
    result = await db.execute(select(Webhook))
    return list(result.scalars().all())


def _post_sync(url: str, body: str) -> None:
    try:
        host, ip = _validate_webhook_host(url)
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
        with _pin_dns(host, ip), opener.open(req, timeout=8):
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

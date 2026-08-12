import asyncio
import contextlib
import ipaddress
import json
import logging
import re
import smtplib
import socket
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)

CHANNEL_KINDS = {"webhook", "ntfy", "email"}
EVENT_NAMES = (
    "alert.cpu",
    "alert.ram",
    "alert.disk",
    "alert.gpu",
    "alert.gpu_temperature",
    "alert.network_rx",
    "alert.network_tx",
)
EVENTS = set(EVENT_NAMES)
SEVERITIES = {"info", "warning", "critical"}
SMTP_SECURITY_MODES = {"starttls", "ssl", "none"}
NTFY_TOPIC_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# DNS-pinning closes the resolve-then-connect TOCTOU between validation and
# delivery. The pin is thread-local because deliveries run in worker threads.
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
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass(frozen=True)
class DeliveryResult:
    channel_id: str
    success: bool
    status: int | None = None
    error: str | None = None


def _valid_email(value: str | None) -> bool:
    if not value or len(value) > 320 or any(ord(char) < 32 for char in value):
        return False
    _, address = parseaddr(value)
    return address == value and "@" in address and not address.startswith("@")


def validate_channel_config(
    *,
    kind: str,
    url: str = "",
    topic: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_security: str | None = None,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    email_from: str | None = None,
    email_to: str | None = None,
) -> str:
    if kind not in CHANNEL_KINDS:
        raise ValueError("Notification type must be webhook, ntfy, or email")

    if kind == "email":
        if (
            not smtp_host
            or len(smtp_host) > 253
            or any(char.isspace() or ord(char) < 32 for char in smtp_host)
        ):
            raise ValueError("SMTP host is invalid")
        if smtp_port is None or not 1 <= smtp_port <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535")
        if smtp_security not in SMTP_SECURITY_MODES:
            raise ValueError("SMTP security must be STARTTLS, SSL/TLS, or none")
        if bool(smtp_username) != bool(smtp_password):
            raise ValueError("SMTP username and password must be provided together")
        if smtp_username and smtp_security == "none":
            raise ValueError("SMTP authentication requires STARTTLS or SSL/TLS")
        if not _valid_email(email_from) or not _valid_email(email_to):
            raise ValueError("Sender and recipient must be valid email addresses")
        return ""

    if not url or len(url) > 2048 or any(ord(char) < 32 for char in url):
        raise ValueError("Notification URL is invalid")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        raise ValueError("Notification URL must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials must not be embedded in the notification URL")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Notification URL has an invalid port") from exc

    if kind == "ntfy":
        if parsed.query or parsed.fragment:
            raise ValueError("ntfy server URL must not contain a query or fragment")
        if not topic or not NTFY_TOPIC_RE.fullmatch(topic):
            raise ValueError(
                "ntfy topic must be 1-64 letters, numbers, hyphens, or underscores"
            )
    return url.rstrip("/") or url


def _is_blocked_ip(
    ip_str: str,
    *,
    allow_loopback: bool,
    allow_private: bool = True,
) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    if ip.is_link_local:
        return True
    if ip.is_loopback and not allow_loopback:
        return True
    return ip.is_private and not allow_private and not ip.is_loopback


def _resolve_target(
    host: str,
    port: int | None,
    *,
    allow_loopback: bool,
) -> tuple[str, str]:
    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve notification host: {exc}") from exc
    if not infos:
        raise ValueError("Could not resolve notification host")
    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip, allow_loopback=allow_loopback):
            raise ValueError(f"Notification host resolves to a blocked address ({ip})")
    return host, infos[0][4][0]


def _validate_http_host(url: str, *, allow_loopback: bool = False) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(url)
    if not parsed.hostname:
        raise ValueError("Notification URL has no host")
    return _resolve_target(parsed.hostname, parsed.port, allow_loopback=allow_loopback)


async def get_all(db: AsyncSession) -> list[Webhook]:
    result = await db.execute(select(Webhook))
    return list(result.scalars().all())


def _notification_content(
    event: str,
    payload: dict[str, Any],
) -> tuple[str, str, int, list[str]]:
    if event == "test":
        return (
            "CarbonPanel test",
            "Notification delivery is working.",
            3,
            ["white_check_mark", "carbonpanel"],
        )

    severity = str(payload.get("severity", "warning")).lower()
    if severity not in SEVERITIES:
        severity = "warning"
    priority, severity_tag = {
        "info": (3, "information_source"),
        "warning": (4, "warning"),
        "critical": (5, "rotating_light"),
    }[severity]

    metric = str(payload.get("label") or payload.get("metric") or event.removeprefix("alert."))
    message = payload.get("message")
    if not message:
        unit = str(payload.get("unit", "%"))
        separator = "" if unit in {"", "%", "°C"} else " "
        message = (
            f"{metric} is at {float(payload.get('value', 0)):.1f}{separator}{unit} "
            f"(threshold {float(payload.get('threshold', 0)):.1f}{separator}{unit})."
        )
    title = f"[{severity.upper()}] CarbonPanel {metric} alert"
    return title, str(message), priority, [severity_tag, "carbonpanel"]


def _request_for(channel: Webhook, event: str, payload: dict[str, Any]) -> urllib.request.Request:
    headers = {"Content-Type": "application/json"}
    if channel.kind == "ntfy":
        title, message, priority, tags = _notification_content(event, payload)
        body = {
            "topic": channel.topic,
            "title": title,
            "message": message,
            "priority": priority,
            "tags": tags,
        }
        if channel.token:
            headers["Authorization"] = f"Bearer {channel.token}"
    else:
        body = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }

    data = json.dumps(body).encode()
    headers["Content-Length"] = str(len(data))
    return urllib.request.Request(channel.url, data=data, headers=headers, method="POST")


def _deliver_http(channel: Webhook, event: str, payload: dict[str, Any]) -> int:
    host, ip = _validate_http_host(
        channel.url,
        allow_loopback=channel.kind == "ntfy",
    )
    request = _request_for(channel, event, payload)
    opener = urllib.request.build_opener(_NoRedirect)
    with _pin_dns(host, ip), opener.open(request, timeout=8) as response:
        status = response.getcode()
    if not 200 <= status < 300:
        raise RuntimeError(f"HTTP {status}")
    return status


def _deliver_email(channel: Webhook, event: str, payload: dict[str, Any]) -> int:
    host, ip = _resolve_target(channel.smtp_host or "", channel.smtp_port, allow_loopback=True)
    title, body, _, _ = _notification_content(event, payload)
    message = EmailMessage()
    message["Subject"] = title
    message["From"] = channel.email_from
    message["To"] = channel.email_to
    message.set_content(body)

    context = ssl.create_default_context()
    with _pin_dns(host, ip):
        if channel.smtp_security == "ssl":
            client: smtplib.SMTP = smtplib.SMTP_SSL(
                host,
                channel.smtp_port or 465,
                timeout=10,
                context=context,
            )
        else:
            client = smtplib.SMTP(host, channel.smtp_port or 587, timeout=10)
        with client:
            client.ehlo()
            if channel.smtp_security == "starttls":
                client.starttls(context=context)
                client.ehlo()
            if channel.smtp_username:
                client.login(channel.smtp_username, channel.smtp_password or "")
            client.send_message(message)
    return 250


def _post_sync(channel: Webhook, event: str, payload: dict[str, Any]) -> DeliveryResult:
    try:
        validate_channel_config(
            kind=channel.kind,
            url=channel.url,
            topic=channel.topic,
            smtp_host=channel.smtp_host,
            smtp_port=channel.smtp_port,
            smtp_security=channel.smtp_security,
            smtp_username=channel.smtp_username,
            smtp_password=channel.smtp_password,
            email_from=channel.email_from,
            email_to=channel.email_to,
        )
        status = (
            _deliver_email(channel, event, payload)
            if channel.kind == "email"
            else _deliver_http(channel, event, payload)
        )
        return DeliveryResult(channel.id, True, status=status)
    except urllib.error.HTTPError as exc:
        detail = exc.read(512).decode(errors="replace").strip()
        error = f"HTTP {exc.code}" + (f": {detail}" if detail else "")
    except smtplib.SMTPAuthenticationError:
        error = "SMTP authentication failed"
    except Exception as exc:
        error = str(exc) or exc.__class__.__name__

    logger.warning("Notification delivery failed for channel %s: %s", channel.id, error)
    return DeliveryResult(channel.id, False, error=error)


async def deliver_channel(
    channel: Webhook,
    event: str,
    payload: dict[str, Any],
) -> DeliveryResult:
    return await asyncio.to_thread(_post_sync, channel, event, payload)


async def fire_event(
    db: AsyncSession,
    event: str,
    payload: dict[str, Any],
) -> list[DeliveryResult]:
    hooks = await get_all(db)
    enabled = [
        hook
        for hook in hooks
        if hook.enabled and event in {item.strip() for item in hook.events.split(",")}
    ]
    if not enabled:
        return []
    return list(
        await asyncio.gather(
            *(deliver_channel(hook, event, payload) for hook in enabled),
        )
    )

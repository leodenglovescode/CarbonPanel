"""
Candidate URLs a paired client can use to reach this panel.

A phone is not always on the same network as the server. The address the
browser used to load the panel (typically a LAN IP like 192.168.1.x) is only
one of several ways in, and it's the one that stops working the moment the
phone leaves the house. Overlay networks — Tailscale/Headscale in particular —
give the server a second, location-independent address that keeps working
remotely, and a lot of self-hosters reach their panel that way.

So pairing hands the client a *list* of endpoints rather than a single URL, and
the client fails over between them. This module discovers the candidates:

  * the address the pairing request itself arrived on (known-good right now)
  * every routable address on a local interface, classified by reachability
  * whatever external URL the operator configured by hand

Ordering matters to the client — it tries them in the order given — so overlay
addresses sort ahead of LAN ones. An overlay address works both at home and
away, which makes it the better default; a LAN address is faster but only
sometimes reachable.
"""

import ipaddress
import socket

import psutil

from app.services.settings_store import get_key, set_key

_EXTRA_KEY = "pairing_endpoints"

# Tailscale/Headscale hand out addresses from the 100.64.0.0/10 CGNAT range,
# and ZeroTier/Nebula deployments commonly sit on their own private ranges.
# Matching on the range rather than the interface name keeps this working when
# the interface is named something other than tailscale0 (userspace mode, *BSD,
# renamed links).
_CGNAT = ipaddress.ip_network("100.64.0.0/10")
# Tailscale's fixed IPv6 ULA prefix — its v6 addresses would otherwise look
# like any other private address and get sorted behind the LAN ones.
_TAILSCALE_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")

# WireGuard, ZeroTier, Nebula and OpenVPN tunnels hand out addresses from
# ordinary private ranges, so the range alone can't identify them — but an
# address on one of these interfaces is reachable off-LAN, which is the
# property that actually matters for ordering.
_OVERLAY_IFACE_PREFIXES = ("tailscale", "ts", "wg", "zt", "nebula", "tun", "utun")

_SKIP_IFACE_PREFIXES = ("lo", "docker", "br-", "veth", "virbr", "vmnet")


class Endpoint(dict):
    """Plain dict so it serialises straight to JSON without a schema import."""

    def __init__(self, url: str, kind: str, label: str) -> None:
        super().__init__(url=url, kind=kind, label=label)


def _classify(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address, iface: str
) -> str | None:
    """Return an endpoint kind, or None if the address isn't worth offering."""
    if addr.is_loopback or addr.is_link_local or addr.is_multicast:
        return None
    if addr.version == 4 and addr in _CGNAT:
        return "overlay"
    if addr.version == 6 and addr in _TAILSCALE_V6:
        return "overlay"
    if iface.lower().startswith(_OVERLAY_IFACE_PREFIXES):
        return "overlay"
    if addr.is_private:
        return "lan"
    return "public"


def _iface_is_interesting(name: str) -> bool:
    return not name.startswith(_SKIP_IFACE_PREFIXES)


def server_name() -> str:
    """Human-readable name for this panel, shown in the app's server list."""
    try:
        return socket.gethostname() or "CarbonPanel"
    except Exception:
        return "CarbonPanel"


def get_extra_endpoints() -> list[str]:
    """Operator-configured URLs (public domain, DDNS, Tailscale MagicDNS name).

    Autodiscovery can only see addresses bound to a local interface, so
    anything that reaches the panel through a name or a forwarded port has to
    be entered by hand.
    """
    value = get_key(_EXTRA_KEY, [])
    return [str(u) for u in value] if isinstance(value, list) else []


def set_extra_endpoints(urls: list[str]) -> None:
    cleaned: list[str] = []
    for raw in urls:
        url = str(raw).strip().rstrip("/")
        if url and url not in cleaned:
            cleaned.append(url)
    set_key(_EXTRA_KEY, cleaned)


def discover(scheme: str, port: int | None, host_header: str | None = None) -> list[Endpoint]:
    """Build the candidate endpoint list for a pairing payload.

    `host_header` is the Host the pairing request arrived on — included first
    because it is empirically working for at least one client right now.
    """
    endpoints: list[Endpoint] = []
    seen: set[str] = set()

    def add(url: str, kind: str, label: str) -> None:
        if url not in seen:
            seen.add(url)
            endpoints.append(Endpoint(url, kind, label))

    suffix = f":{port}" if port else ""

    overlay: list[tuple[str, str]] = []
    lan: list[tuple[str, str]] = []
    public: list[tuple[str, str]] = []

    try:
        if_addrs = psutil.net_if_addrs()
    except Exception:
        if_addrs = {}

    for iface, addrs in if_addrs.items():
        if not _iface_is_interesting(iface):
            continue
        for a in addrs:
            if a.family not in (socket.AF_INET, socket.AF_INET6):
                continue
            raw = a.address.split("%", 1)[0]  # strip IPv6 zone id
            try:
                parsed = ipaddress.ip_address(raw)
            except ValueError:
                continue
            kind = _classify(parsed, iface)
            if kind is None:
                continue
            hostpart = f"[{raw}]" if parsed.version == 6 else raw
            url = f"{scheme}://{hostpart}{suffix}"
            entry = (url, f"{iface} ({raw})")
            if kind == "overlay":
                overlay.append(entry)
            elif kind == "lan":
                lan.append(entry)
            else:
                public.append(entry)

    # Operator-configured URLs first — someone typed these in specifically so
    # the panel could be reached from outside, which makes them the best guess
    # for a phone that may be anywhere.
    for url in get_extra_endpoints():
        add(url, "custom", "Configured manually")
    # Then overlay addresses: reachable from anywhere without port-forwarding,
    # which is what a phone needs most.
    for url, label in overlay:
        add(url, "overlay", label)
    # Then the address this request came in on — fast on the local network and
    # proven to work, but only while the phone is on that network.
    if host_header:
        add(f"{scheme}://{host_header}", "current", "This browser's address")
    for url, label in lan:
        add(url, "lan", label)
    for url, label in public:
        add(url, "public", label)

    return endpoints

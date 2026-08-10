"""
Short-lived, single-use pairing codes for native (Android) clients.

A signed-in browser asks for a code, renders it as a QR, and the phone posts
the code back to claim a long-lived bearer token. The window between those two
events is seconds, so codes live entirely in memory — there is nothing here
worth surviving a restart, and a restart invalidating in-flight codes is the
correct behaviour rather than a limitation.

Codes are single-use: claiming one consumes it immediately, so a QR left on
screen (or photographed by someone else) can't be redeemed twice. The claim
endpoint is necessarily unauthenticated — the phone has no credentials yet —
which is why the code is high-entropy, expires in minutes, and the endpoint
sits behind the same brute-force guard as login.
"""

import secrets
import time
from dataclasses import dataclass
from threading import Lock

from app.config import settings

# Crockford-ish base32: no I/L/O/U/0/1 so a code stays unambiguous if someone
# reads it off the screen and types it instead of scanning.
_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
_CODE_LEN = 12


@dataclass
class PendingPairing:
    user_id: str
    username: str
    created_at: float          # time.monotonic()
    claimed: bool = False
    device_name: str | None = None


_lock = Lock()
_pending: dict[str, PendingPairing] = {}
# Codes claimed recently, kept so the polling browser can render a "Paired ✓"
# confirmation naming the device, rather than an indistinguishable "expired".
# Value is (claimed_at_monotonic, device_name).
_recently_claimed: dict[str, tuple[float, str]] = {}


def _ttl_seconds() -> float:
    return settings.pairing_code_expire_minutes * 60


def _sweep(now: float) -> None:
    """Drop expired codes. Must hold _lock."""
    ttl = _ttl_seconds()
    for code in [c for c, p in _pending.items() if now - p.created_at >= ttl]:
        del _pending[code]


def generate(user_id: str, username: str) -> tuple[str, int]:
    """Create a pairing code for a signed-in user.

    Returns (code, expires_in_seconds).
    """
    now = time.monotonic()
    code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))
    with _lock:
        _sweep(now)
        _pending[code] = PendingPairing(
            user_id=user_id,
            username=username,
            created_at=now,
        )
    return code, int(_ttl_seconds())


def claim(code: str) -> PendingPairing | None:
    """Consume a pairing code. Returns the pending record, or None if the code
    is unknown, already used, or expired.

    The record is removed on success — a code is redeemable exactly once.
    """
    now = time.monotonic()
    with _lock:
        _sweep(now)
        pending = _pending.get(code)
        if pending is None or pending.claimed:
            return None
        del _pending[code]
        pending.claimed = True
        return pending


def peek(code: str, user_id: str) -> tuple[str, str | None]:
    """Status of a code for the browser that created it, without consuming it.

    Returns (status, device_name) where status is "pending", "claimed", or
    "expired". A successfully claimed code is already gone from _pending, so
    "not found" is disambiguated via the _recently_claimed record.
    """
    now = time.monotonic()
    with _lock:
        _sweep(now)
        pending = _pending.get(code)
        if pending is None:
            claimed = _recently_claimed.get(code)
            if claimed is not None:
                return "claimed", claimed[1]
            return "expired", None
        # Don't let one user poll the status of another user's code.
        if pending.user_id != user_id:
            return "expired", None
        return "pending", None


def mark_claimed(code: str, device_name: str) -> None:
    """Record that a code was claimed, so the browser's next poll can confirm it."""
    now = time.monotonic()
    with _lock:
        ttl = _ttl_seconds()
        for c in [c for c, (t, _) in _recently_claimed.items() if now - t >= ttl]:
            del _recently_claimed[c]
        _recently_claimed[code] = (now, device_name)


def reset() -> None:
    """Clear all state — for tests."""
    with _lock:
        _pending.clear()
        _recently_claimed.clear()

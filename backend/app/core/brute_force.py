"""
Brute-force protection, keyed by IP and by username independently.

Tracks failed login attempts per key. After MAX_ATTEMPTS failures within
WINDOW_SECONDS that key is banned for BAN_SECONDS. A successful login clears
the counter for that key.

Two keyspaces are tracked (call both check/record functions with "ip:<addr>"
and "user:<username>"): per-IP alone is trivially bypassed by rotating source
IPs (proxies, botnets), and per-username alone would let an attacker with many
IPs still grind one account — the pair closes both gaps without either one
alone being a single point of failure.
"""

import time
from collections import defaultdict
from threading import Lock

MAX_ATTEMPTS = 10
BAN_SECONDS = 15 * 60       # 15 minutes
WINDOW_SECONDS = 15 * 60    # rolling window over which failures are counted

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)  # key -> failure timestamps
_banned: dict[str, float] = {}                          # key -> ban_until (monotonic)


def _cleanup(key: str, now: float) -> None:
    """Drop attempt timestamps outside the rolling window. Must hold _lock."""
    _attempts[key] = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]
    if not _attempts[key]:
        del _attempts[key]


def _keys(ip: str | None, username: str | None) -> list[str]:
    keys = []
    if ip:
        keys.append(f"ip:{ip}")
    if username:
        keys.append(f"user:{username.strip().lower()}")
    return keys


def is_banned(ip: str | None, username: str | None = None) -> bool:
    now = time.monotonic()
    with _lock:
        for key in _keys(ip, username):
            until = _banned.get(key)
            if until is None:
                continue
            if now >= until:
                _banned.pop(key, None)
                _attempts.pop(key, None)
                continue
            return True
    return False


def retry_after(ip: str | None, username: str | None = None) -> int:
    """Seconds remaining in the longest active ban among the given keys (0 if none)."""
    now = time.monotonic()
    remaining = 0
    with _lock:
        for key in _keys(ip, username):
            until = _banned.get(key)
            if until is not None:
                remaining = max(remaining, int(until - now))
    return max(0, remaining)


def record_failure(ip: str | None, username: str | None = None) -> int:
    """Record a failed attempt against both keys. Returns the fewest attempts
    remaining before ban, across keys (i.e. however close the closer one is)."""
    now = time.monotonic()
    min_remaining = MAX_ATTEMPTS
    with _lock:
        for key in _keys(ip, username):
            _cleanup(key, now)
            _attempts[key].append(now)
            count = len(_attempts[key])
            if count >= MAX_ATTEMPTS:
                _banned[key] = now + BAN_SECONDS
            min_remaining = min(min_remaining, max(0, MAX_ATTEMPTS - count))
    return min_remaining


def record_success(ip: str | None, username: str | None = None) -> None:
    """Clear the failure counter for both keys after a successful login."""
    with _lock:
        for key in _keys(ip, username):
            _attempts.pop(key, None)
            _banned.pop(key, None)

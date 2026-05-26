"""
IP-based brute-force protection.

Tracks failed login attempts per IP. After MAX_ATTEMPTS failures within
WINDOW_SECONDS the IP is banned for BAN_SECONDS. A successful login clears
the counter for that IP.
"""

import time
from collections import defaultdict
from threading import Lock

MAX_ATTEMPTS = 10
BAN_SECONDS = 15 * 60       # 15 minutes
WINDOW_SECONDS = 15 * 60    # rolling window over which failures are counted

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)  # ip -> failure timestamps
_banned: dict[str, float] = {}                          # ip -> ban_until (monotonic)


def _cleanup(ip: str, now: float) -> None:
    """Drop attempt timestamps outside the rolling window. Must hold _lock."""
    _attempts[ip] = [t for t in _attempts[ip] if now - t < WINDOW_SECONDS]
    if not _attempts[ip]:
        del _attempts[ip]


def is_banned(ip: str | None) -> bool:
    if not ip:
        return False
    now = time.monotonic()
    with _lock:
        until = _banned.get(ip)
        if until is None:
            return False
        if now >= until:
            _banned.pop(ip, None)
            _attempts.pop(ip, None)
            return False
        return True


def retry_after(ip: str | None) -> int:
    """Seconds remaining in the ban (0 if not banned)."""
    if not ip:
        return 0
    now = time.monotonic()
    with _lock:
        until = _banned.get(ip)
        if until is None:
            return 0
        remaining = until - now
        return max(0, int(remaining))


def record_failure(ip: str | None) -> int:
    """Record a failed attempt. Returns how many attempts remain before ban."""
    if not ip:
        return MAX_ATTEMPTS
    now = time.monotonic()
    with _lock:
        _cleanup(ip, now)
        _attempts[ip].append(now)
        count = len(_attempts[ip])
        if count >= MAX_ATTEMPTS:
            _banned[ip] = now + BAN_SECONDS
        return max(0, MAX_ATTEMPTS - count)


def record_success(ip: str | None) -> None:
    """Clear the failure counter after a successful login."""
    if not ip:
        return
    with _lock:
        _attempts.pop(ip, None)
        _banned.pop(ip, None)

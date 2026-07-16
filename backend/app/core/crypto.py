"""Symmetric encryption for sensitive columns (TOTP secrets), keyed off SECRET_KEY.

Rotating SECRET_KEY invalidates anything encrypted here — that's an accepted
tradeoff (see EncryptedString below) rather than managing a second secret.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def is_encrypted(value: str) -> bool:
    """True if `value` decrypts cleanly under the current key (vs. legacy plaintext)."""
    try:
        decrypt(value)
        return True
    except Exception:
        return False

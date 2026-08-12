from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt, encrypt


class EncryptedString(TypeDecorator):
    """Transparently encrypt/decrypt sensitive string columns."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return decrypt(value)
        except Exception:
            # A rotated SECRET_KEY makes old ciphertext unreadable. Treat it as
            # absent so one stale secret cannot break the containing record.
            return None

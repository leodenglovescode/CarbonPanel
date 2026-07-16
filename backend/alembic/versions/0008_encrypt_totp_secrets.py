"""Encrypt any legacy-plaintext totp_secret / pending_totp_secret values

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-16 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

from app.core.crypto import encrypt, is_encrypted

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, totp_secret, pending_totp_secret FROM users")
    ).fetchall()
    for row_id, totp_secret, pending_totp_secret in rows:
        updates = {}
        if totp_secret and not is_encrypted(totp_secret):
            updates["totp_secret"] = encrypt(totp_secret)
        if pending_totp_secret and not is_encrypted(pending_totp_secret):
            updates["pending_totp_secret"] = encrypt(pending_totp_secret)
        if updates:
            set_clause = ", ".join(f"{col} = :{col}" for col in updates)
            conn.execute(
                sa.text(f"UPDATE users SET {set_clause} WHERE id = :id"),
                {**updates, "id": row_id},
            )


def downgrade() -> None:
    # ponytail: one-way — decrypting back to plaintext on downgrade isn't worth the code.
    pass

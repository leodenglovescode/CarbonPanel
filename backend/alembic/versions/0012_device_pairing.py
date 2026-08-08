"""Add kind and expires_at to devices — QR pairing for native clients

Native (non-browser) clients can't use the httpOnly session cookie, so they
authenticate with a long-lived bearer token issued by the pairing flow. Those
rows need to be distinguishable from browser sessions in the UI (`kind`) and
carry their own expiry independent of access_token_expire_minutes, which is
tuned for browsers (`expires_at`).

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-08 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default="browser" so every pre-existing row — all of which are
    # browser sessions — is correct without a backfill pass.
    op.add_column(
        "devices",
        sa.Column("kind", sa.String(), nullable=False, server_default="browser"),
    )
    op.add_column("devices", sa.Column("expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "expires_at")
    op.drop_column("devices", "kind")

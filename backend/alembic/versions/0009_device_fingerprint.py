"""Add device_id fingerprint column to devices

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-17 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("device_id", sa.String(), nullable=True))
    op.create_index("ix_devices_user_device", "devices", ["user_id", "device_id"])


def downgrade() -> None:
    op.drop_index("ix_devices_user_device", table_name="devices")
    op.drop_column("devices", "device_id")

"""Extend webhooks into webhook, ntfy, and email notification channels

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-12 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "webhooks",
        sa.Column("kind", sa.String(), nullable=False, server_default="webhook"),
    )
    op.add_column("webhooks", sa.Column("topic", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("token", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("smtp_host", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("smtp_port", sa.Integer(), nullable=True))
    op.add_column("webhooks", sa.Column("smtp_security", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("smtp_username", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("smtp_password", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("email_from", sa.String(), nullable=True))
    op.add_column("webhooks", sa.Column("email_to", sa.String(), nullable=True))


def downgrade() -> None:
    for column in (
        "email_to",
        "email_from",
        "smtp_password",
        "smtp_username",
        "smtp_security",
        "smtp_port",
        "smtp_host",
        "token",
        "topic",
        "kind",
    ):
        op.drop_column("webhooks", column)

"""Add onboarding_completed_at column to users

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-17 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True))
    # Existing users predate the onboarding wizard entirely — back-fill them as
    # already onboarded so an update doesn't suddenly force a re-run of setup
    # on an account that's been live for months. Only brand-new users (created
    # after this migration, e.g. by seed_admin on a fresh install) start null.
    op.execute("UPDATE users SET onboarding_completed_at = CURRENT_TIMESTAMP")


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")

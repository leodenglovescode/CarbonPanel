"""Drop webauthn_credentials — passkeys removed

Most installs are reached over a bare IP with a self-signed cert, and several
platform authenticators (Windows Hello, iCloud Keychain, Android biometrics)
refuse or silently fail WebAuthn ceremonies on an untrusted certificate — a
constraint no amount of in-app fixing can work around for that access
pattern. Password + TOTP remains the supported auth path.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-18 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("webauthn_credentials")


def downgrade() -> None:
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("device_name", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id"),
    )

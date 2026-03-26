from alembic import op
import sqlalchemy as sa


revision = "0003_starred_system_services"
down_revision = "0002_sites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "starred_system_services",
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "service_name",
            sa.String(),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "position",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_starred_system_services_user_id",
        "starred_system_services",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_starred_system_services_user_id", table_name="starred_system_services")
    op.drop_table("starred_system_services")

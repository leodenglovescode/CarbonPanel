from alembic import op
import sqlalchemy as sa


revision = "0004_app_labels"
down_revision = "0003_starred_system_services"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_labels",
        sa.Column("port", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_labels")

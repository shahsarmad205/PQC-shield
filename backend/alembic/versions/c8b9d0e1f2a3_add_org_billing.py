"""add org billing (plan, stripe, quota)

Revision ID: c8b9d0e1f2a3
Revises: b7a8c9d0e1f2
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8b9d0e1f2a3"
down_revision: Union[str, None] = "b7a8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("plan", sa.String(length=32), nullable=False, server_default=sa.text("'starter'")),
    )
    op.add_column("organizations", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.add_column("organizations", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("organizations", sa.Column("monthly_quota", sa.Integer(), nullable=False, server_default=sa.text("10000")))
    op.add_column("organizations", sa.Column("ops_used_this_month", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    op.drop_column("organizations", "ops_used_this_month")
    op.drop_column("organizations", "monthly_quota")
    op.drop_column("organizations", "stripe_subscription_id")
    op.drop_column("organizations", "stripe_customer_id")
    op.drop_column("organizations", "plan")

"""create learning_path_waitlist table

Revision ID: legal_005
Revises: legal_004
Create Date: 2026-05-11

Note: Table was created directly in production. This migration
exists for consistency so new deployments get the table via alembic.
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "legal_005"
down_revision: Union[str, None] = "legal_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_path_waitlist",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("learning_path_id", sa.Integer(), sa.ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "learning_path_id", name="uq_lp_waitlist_user_path"),
    )


def downgrade() -> None:
    op.drop_table("learning_path_waitlist")

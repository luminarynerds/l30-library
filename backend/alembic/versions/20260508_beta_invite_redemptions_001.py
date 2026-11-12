"""add beta_invite_redemptions junction table

Revision ID: beta_redemptions_001
Revises: f8509872ebab
Create Date: 2026-05-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "beta_redemptions_001"
down_revision: Union[str, None] = "f8509872ebab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "beta_invite_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "invite_id",
            sa.Integer(),
            sa.ForeignKey("beta_invites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "redeemed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "invite_id", "user_id", name="uq_beta_invite_redemption_user"
        ),
    )
    op.create_index(
        "ix_beta_invite_redemptions_invite_id",
        "beta_invite_redemptions",
        ["invite_id"],
    )
    op.create_index(
        "ix_beta_invite_redemptions_user_id",
        "beta_invite_redemptions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_beta_invite_redemptions_user_id", table_name="beta_invite_redemptions")
    op.drop_index("ix_beta_invite_redemptions_invite_id", table_name="beta_invite_redemptions")
    op.drop_table("beta_invite_redemptions")

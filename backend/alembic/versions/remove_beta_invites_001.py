# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""remove unused beta-invites feature (drop beta_invites + beta_invite_redemptions)

Revision ID: remove_beta_invites_001
Revises: staff_kb_summary_001
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "remove_beta_invites_001"
down_revision: Union[str, None] = "staff_kb_summary_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the junction table first (it FKs beta_invites), then the parent
    # table, then the now-orphaned PG enum type. op.drop_table cascades each
    # table's own indexes/constraints, so no explicit drop_index is needed
    # (and the prior explicit names targeted indexes that don't exist in prod,
    # which would have aborted the migration).
    op.drop_table("beta_invite_redemptions")
    op.drop_table("beta_invites")
    op.execute("DROP TYPE IF EXISTS invitestatus")


def downgrade() -> None:
    # Recreate the enum explicitly, then the parent table, then the junction
    # table (reverse drop order). create_type=False so create_table does not
    # try to re-create the type we just made.
    invitestatus = postgresql.ENUM(
        "active",
        "used",
        "expired",
        "revoked",
        name="invitestatus",
    )
    invitestatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "beta_invites",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "used",
                "expired",
                "revoked",
                name="invitestatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "used_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("use_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", name="uq_beta_invite_code"),
    )
    op.create_index("ix_beta_invites_id", "beta_invites", ["id"])
    op.create_index(
        "ix_beta_invites_code", "beta_invites", ["code"], unique=True
    )

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
        "ix_beta_invite_redemptions_id",
        "beta_invite_redemptions",
        ["id"],
    )

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create fine_waivers table

Revision ID: fine_waivers_001
Revises: contact_form_fields_001
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa

revision = "fine_waivers_001"
down_revision = "cdb306acb450"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fine_waivers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "fine_id",
            sa.Integer(),
            sa.ForeignKey("fines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_waived", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "waived",
                "pending_approval",
                "rejected",
                name="finewaiverstatus",
            ),
            nullable=False,
            server_default="pending_approval",
        ),
        sa.Column(
            "waived_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_fine_waivers_fine_id", "fine_waivers", ["fine_id"]
    )
    op.create_index(
        "ix_fine_waivers_status", "fine_waivers", ["status"]
    )
    op.create_index(
        "ix_fine_waivers_waived_by", "fine_waivers", ["waived_by_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_fine_waivers_waived_by", table_name="fine_waivers")
    op.drop_index("ix_fine_waivers_status", table_name="fine_waivers")
    op.drop_index("ix_fine_waivers_fine_id", table_name="fine_waivers")
    op.drop_table("fine_waivers")
    op.execute("DROP TYPE IF EXISTS finewaiverstatus")

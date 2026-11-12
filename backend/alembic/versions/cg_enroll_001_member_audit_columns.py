# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""parent_connection_group_members: staff enrollment audit columns.

Adds five columns capturing who enrolled/removed each member and why:

- enrolled_by_id: FK users (nullable; NULL = patron self-enrolled via legacy /join)
- enrollment_consent_note: free text up to ~500 chars, how patron consented
- capacity_override: bool flag, true when admin enrolled over max_members
- override_justification: required when capacity_override = true
- removed_by_id: FK users; staff who triggered DELETE /members/{patron_id}
- removal_reason: short-code enum stored as VARCHAR(40)
  (patron_request | attendance_lapse | safety | program_ended | other)

All columns nullable so legacy rows backfill cleanly. The boolean has a
server_default of 'false' for the same reason.

Revision ID: cg_enroll_001
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "cg_enroll_001"
down_revision: Union[str, Sequence[str], None] = "org_features_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parent_connection_group_members",
        sa.Column(
            "enrolled_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_pcgm_enrolled_by_id",
        "parent_connection_group_members",
        ["enrolled_by_id"],
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column("enrollment_consent_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column(
            "capacity_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column("override_justification", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column(
            "removed_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_pcgm_removed_by_id",
        "parent_connection_group_members",
        ["removed_by_id"],
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column("removal_reason", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parent_connection_group_members", "removal_reason")
    op.drop_index(
        "ix_pcgm_removed_by_id",
        table_name="parent_connection_group_members",
    )
    op.drop_column("parent_connection_group_members", "removed_by_id")
    op.drop_column("parent_connection_group_members", "override_justification")
    op.drop_column("parent_connection_group_members", "capacity_override")
    op.drop_column("parent_connection_group_members", "enrollment_consent_note")
    op.drop_index(
        "ix_pcgm_enrolled_by_id",
        table_name="parent_connection_group_members",
    )
    op.drop_column("parent_connection_group_members", "enrolled_by_id")

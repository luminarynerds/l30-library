# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""parent_connection_groups: confidentiality + approval-gated waitlist.

Adds 4 columns to parent_connection_groups (confidentiality config) and
6 columns to parent_connection_group_members (request/decision audit).

The status column stays VARCHAR(50); the two new GroupMemberStatus values
(pending_approval, denied) are Python-enum-only per the spec.

Revision ID: cg_confidential_001
Create Date: 2026-05-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "cg_confidential_001"
down_revision: Union[str, Sequence[str], None] = "mergepoint_3way_20260519"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # parent_connection_groups: 4 columns
    op.add_column(
        "parent_connection_groups",
        sa.Column(
            "confidential",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_pcg_confidential",
        "parent_connection_groups",
        ["confidential"],
    )
    op.add_column(
        "parent_connection_groups",
        sa.Column("confidential_card_description", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "parent_connection_groups",
        sa.Column("confidential_approval_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_connection_groups",
        sa.Column(
            "estimated_response_window_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("48"),
        ),
    )

    # parent_connection_group_members: 6 columns
    op.add_column(
        "parent_connection_group_members",
        sa.Column("request_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column(
            "consent_to_share_contact",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column(
            "decided_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_pcgm_decided_by_id",
        "parent_connection_group_members",
        ["decided_by_id"],
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column("decision_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "parent_connection_group_members",
        sa.Column("decision_patron_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parent_connection_group_members", "decision_patron_message")
    op.drop_column("parent_connection_group_members", "decision_note")
    op.drop_column("parent_connection_group_members", "decided_at")
    op.drop_index("ix_pcgm_decided_by_id", table_name="parent_connection_group_members")
    op.drop_column("parent_connection_group_members", "decided_by_id")
    op.drop_column("parent_connection_group_members", "consent_to_share_contact")
    op.drop_column("parent_connection_group_members", "request_message")
    op.drop_column("parent_connection_groups", "estimated_response_window_hours")
    op.drop_column("parent_connection_groups", "confidential_approval_message")
    op.drop_column("parent_connection_groups", "confidential_card_description")
    op.drop_index("ix_pcg_confidential", table_name="parent_connection_groups")
    op.drop_column("parent_connection_groups", "confidential")

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add indie_author_id to events

Revision ID: indie_events_001
Revises: staff_time_entry_001, legal_005
Create Date: 2026-05-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "indie_events_001"
down_revision: tuple[str, ...] = ("staff_time_entry_001", "legal_005")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("indie_author_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_events_indie_author_id",
        "events",
        "indie_authors",
        ["indie_author_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_events_indie_author_id", "events", ["indie_author_id"])


def downgrade() -> None:
    op.drop_index("ix_events_indie_author_id", table_name="events")
    op.drop_constraint("fk_events_indie_author_id", "events", type_="foreignkey")
    op.drop_column("events", "indie_author_id")

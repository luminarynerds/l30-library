# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add minor / patron-type gating to library_agents

check_minor_access(tool, user) reads block_for_minors / requires_parental_consent
/ block_for_patron_types via getattr with defaults, so calling it against a
LibraryAgent silently allowed every minor through -- ai_minor_gating_001 added
those three columns to ai_tools only. This adds the same columns to
library_agents so the patron-chat path gets real enforcement.

Revision ID: library_agent_minor_gating_001
Revises: transit_requested_by_nullable_001
Create Date: 2026-07-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "library_agent_minor_gating_001"
down_revision: Union[str, None] = "transit_requested_by_nullable_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # library_agents: per-agent minor / patron_type access flags. server_default
    # (not just the ORM-level default=) is required here -- these are NOT NULL
    # columns on a table with existing rows, and a plain add_column with only a
    # Python-side default would leave those rows NULL.
    op.add_column(
        "library_agents",
        sa.Column("block_for_minors", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "library_agents",
        sa.Column(
            "requires_parental_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "library_agents",
        sa.Column(
            "block_for_patron_types",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("library_agents", "block_for_patron_types")
    op.drop_column("library_agents", "requires_parental_consent")
    op.drop_column("library_agents", "block_for_minors")

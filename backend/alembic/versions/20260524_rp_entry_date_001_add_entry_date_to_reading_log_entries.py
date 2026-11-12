# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add entry_date to reading_log_entries

Issue #828: paper-log redeemed entries lose their actual reading date.
Add a nullable Date column so transcribed paper entries can preserve the
date the patron wrote. Direct patron self-logs (where logged_at is
authoritative) leave it NULL; existing rows are not backfilled.

Revision ID: rp_entry_date_001
Revises: home_visit_safety_001
Create Date: 2026-05-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rp_entry_date_001"
down_revision: Union[str, Sequence[str], None] = "home_visit_safety_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reading_log_entries",
        sa.Column("entry_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reading_log_entries", "entry_date")

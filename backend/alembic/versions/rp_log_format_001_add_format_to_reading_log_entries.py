# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add format column to reading_log_entries

Revision ID: rp_log_format_001
Revises: merge_2026_05_12_001
Create Date: 2026-05-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "rp_log_format_001"
down_revision: Union[str, Sequence[str], None] = "merge_2026_05_12_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reading_log_entries",
        sa.Column(
            "format",
            sa.String(length=20),
            nullable=True,
            server_default="print",
        ),
    )


def downgrade() -> None:
    op.drop_column("reading_log_entries", "format")

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add sensory / ND access fields to library_branding.

Revision ID: branding_nd_access_001
Revises: merge_pii_donate_001
Create Date: 2026-06-11

Adds three nullable text columns to library_branding (the singleton settings
table) so staff can publish quiet-hours and sensory-friendly info on the
public homepage. All three columns are optional -- NULL means the section is
hidden on the frontend.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "branding_nd_access_001"
down_revision: Union[str, Sequence[str], None] = "merge_pii_donate_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "library_branding",
        sa.Column("quiet_hours", sa.Text(), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("sensory_friendly_times", sa.Text(), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("low_stim_seating", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("library_branding", "low_stim_seating")
    op.drop_column("library_branding", "sensory_friendly_times")
    op.drop_column("library_branding", "quiet_hours")

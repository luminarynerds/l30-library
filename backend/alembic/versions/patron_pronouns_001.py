# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add pronouns column to users table.

Revision ID: patron_pronouns_001
Revises: genealogy_nonbinary_001
Create Date: 2026-06-17

Free-text pronouns field (50 chars max). Nullable — never required.
Downgrade drops the column.
"""
import sqlalchemy as sa
from alembic import op


revision = "patron_pronouns_001"
down_revision = "genealogy_nonbinary_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pronouns", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "pronouns")

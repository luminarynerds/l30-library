# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add 'nonbinary' value to persongender enum.

Revision ID: genealogy_nonbinary_001
Revises: legal_clinic_notify_001
Create Date: 2026-06-17

Postgres cannot drop enum values, so downgrade is a documented no-op.
The nonbinary value stays in the type even if this migration is reverted.
"""
from alembic import op


revision = "genealogy_nonbinary_001"
down_revision = "legal_clinic_notify_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE persongender ADD VALUE IF NOT EXISTS 'nonbinary'")


def downgrade() -> None:
    # Postgres cannot cleanly drop enum values.
    # Any existing nonbinary rows are reassigned to 'other' so the
    # application stays coherent if reverted, but the enum value itself remains.
    op.execute(
        "UPDATE genealogy_persons SET gender = 'other' WHERE gender = 'nonbinary'"
    )

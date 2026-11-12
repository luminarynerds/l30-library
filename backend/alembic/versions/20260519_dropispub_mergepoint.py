# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mergepoint: unite bc_archive_001 + cg_confidential_001 pre PR-C4.

Two heads accumulated on main after the 3-way mergepoint family:
  - bc_archive_001 (book club discussion archive + FTS search)
  - cg_confidential_001 (parent connection-group confidentiality +
    approval-gated waitlist)

PR-C4 (drop courses.is_published) needs a single head to chain its
down_revision off. This is an empty mergepoint: no schema changes, just
one revision that descends from both heads so ``alembic upgrade head``
reaches one tip.

Revision ID: dropispub_mergepoint_20260519
Revises: bc_archive_001, cg_confidential_001
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "dropispub_mergepoint_20260519"
down_revision = (
    "bc_archive_001",
    "cg_confidential_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: pure mergepoint.
    pass


def downgrade() -> None:
    # No-op: each parent owns its own downgrade.
    pass

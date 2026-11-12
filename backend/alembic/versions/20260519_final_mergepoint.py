# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mergepoint: unite drop_courses_is_published_001 + book_club_member_imports_001.

cg_confidential_001 became a branchpoint with two tips on main:
  - drop_courses_is_published_001 (PR-C4: drop legacy courses.is_published)
  - book_club_member_imports_001 (book club member bulk-import audit table)

PR-C4 was verified single-head against its worktree, but book-club
member-imports merged to main afterward off cg_confidential_001,
re-diverging the DAG. ``alembic upgrade head`` fails with multiple
heads until they are rejoined. This is an empty mergepoint: no schema
changes, just one revision descending from both tips so deploys reach a
single head again.

Revision ID: final_mergepoint_20260519
Revises: drop_courses_is_published_001, book_club_member_imports_001
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "final_mergepoint_20260519"
down_revision = (
    "drop_courses_is_published_001",
    "book_club_member_imports_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: pure mergepoint.
    pass


def downgrade() -> None:
    # No-op: each parent owns its own downgrade.
    pass

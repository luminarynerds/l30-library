"""Mergepoint: unify 3 divergent heads on main.

Three heads accumulated from parallel feature work:
  - cg_enroll_001 (connection-group enrollment audit columns)
  - course_lifecycle_001 (course lifecycle additions)
  - orgfeat_mergepoint_20260519 (org-features mergepoint)

Surfaced by the head-gate added in PR #876. This is an empty mergepoint:
no schema changes, just a single revision that descends from all three
heads so alembic upgrade head reaches one tip.

Revision ID: mergepoint_3way_20260519
Revises: cg_enroll_001, course_lifecycle_001, orgfeat_mergepoint_20260519
"""
from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision = "mergepoint_3way_20260519"
down_revision = (
    "cg_enroll_001",
    "course_lifecycle_001",
    "orgfeat_mergepoint_20260519",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: pure mergepoint.
    pass


def downgrade() -> None:
    # No-op: each parent owns its own downgrade.
    pass

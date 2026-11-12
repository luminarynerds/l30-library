# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drop the legacy courses.is_published column (PR-C4 of 4).

``lifecycle_stage`` (added in PR-C1, kept in sync by the PR-C2 compat
shim, surfaced in the PR-C3 admin FE) is now the single source of truth
for course visibility. The patron-facing reads were migrated to
``lifecycle_stage == 'published'`` in this PR, so the legacy boolean is
no longer read anywhere and the shim has been removed from
``transition_course_stage``.

There is NO index on ``courses.is_published`` in prod (verified via
inspector), so the column can be dropped directly. ``lifecycle_stage``
already carries ``ix_courses_lifecycle_stage`` so the patron query stays
performant.

Idempotent + reversible:
  * upgrade(): drop ``is_published`` only if it still exists.
  * downgrade(): re-add it NOT NULL with a temporary server_default,
    backfill from ``lifecycle_stage``, then drop the server_default so
    the restored schema matches the pre-PR-C4 definition (the column
    had a Python-side ``default=False``, no DB server_default).

Revision ID: drop_courses_is_published_001
Revises: dropispub_mergepoint_20260519
Create Date: 2026-05-19 00:00:00.000000+00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "drop_courses_is_published_001"
down_revision: Union[str, None] = "dropispub_mergepoint_20260519"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_cols(inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def _existing_indexes(inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table)}


def upgrade() -> None:
    if op.get_context().as_sql:
        # Offline --sql preview: assume the column still exists and emit
        # the drop unconditionally; the operator pipes to psql.
        op.drop_column("courses", "is_published")
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = _existing_cols(inspector, "courses")
    if "is_published" not in cols:
        return

    # Defensive: drop any index on the column first (none expected in
    # prod, but a hand-patched DB might differ).
    for idx in inspector.get_indexes("courses"):
        if idx["column_names"] == ["is_published"]:
            op.drop_index(idx["name"], table_name="courses")

    op.drop_column("courses", "is_published")


def downgrade() -> None:
    if op.get_context().as_sql:
        cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        cols = _existing_cols(inspector, "courses")
    if "is_published" in cols:
        return

    # Re-add NOT NULL with a temporary server_default so existing rows
    # don't violate the constraint, then backfill from lifecycle_stage,
    # then drop the server_default to match the original column shape
    # (Python-side default only, no DB default).
    op.add_column(
        "courses",
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        "UPDATE courses SET is_published = (lifecycle_stage = 'published')"
    )
    op.alter_column("courses", "is_published", server_default=None)

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""course lifecycle stages: columns on courses + course_stage_transitions

Revision ID: course_lifecycle_001
Revises: org_features_005
Create Date: 2026-05-19 00:00:00.000000+00:00

PR-C1 of the admin-courses lifecycle-stages spec:
  * Add lifecycle_stage / last_reviewed_at / last_reviewed_by_id /
    review_due_at to ``courses``.
  * Backfill lifecycle_stage from is_published, and pre-seed
    last_reviewed_at + review_due_at for rows that land on 'published'
    (so the inherited published courses don't immediately appear "overdue
    for review").
  * Create the append-only ``course_stage_transitions`` audit table.

``is_published`` is kept alongside lifecycle_stage for one release; a
later PR (C4) drops it after the compat shim has been in place.

Idempotent guards on every step so prods that were ALTER-fixed by hand
or stamped forward still apply cleanly.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "course_lifecycle_001"
down_revision: Union[str, None] = "org_features_005"
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
    offline = op.get_context().as_sql
    if offline:
        inspector = None
        cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        cols = _existing_cols(inspector, "courses")

    # 1. Add the four new columns with server defaults so existing rows
    #    don't violate NOT NULL on lifecycle_stage.
    if "lifecycle_stage" not in cols:
        op.add_column(
            "courses",
            sa.Column(
                "lifecycle_stage",
                sa.Enum("draft", "in_review", "published", "needs_revision", "archived", name="course_lifecycle_stage", native_enum=False),
                nullable=False,
                server_default="draft",
            ),
        )
    if "last_reviewed_at" not in cols:
        op.add_column(
            "courses",
            sa.Column(
                "last_reviewed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
    if "last_reviewed_by_id" not in cols:
        op.add_column(
            "courses",
            sa.Column(
                "last_reviewed_by_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "review_due_at" not in cols:
        op.add_column(
            "courses",
            sa.Column(
                "review_due_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    # 2. Backfill lifecycle_stage from is_published. Rows that were already
    #    'draft' (the server default) stay draft; published rows flip to
    #    'published'. Safe to re-run because the WHERE clause excludes rows
    #    already in a non-default stage.
    op.execute(
        """
        UPDATE courses
        SET lifecycle_stage = CASE WHEN is_published THEN 'published'
                                   ELSE 'draft'
                              END
        WHERE lifecycle_stage = 'draft'
        """
    )

    # 3. For published rows, seed last_reviewed_at = now() and
    #    review_due_at = now() + 365 days so the freshly-migrated published
    #    catalog doesn't immediately look "overdue for review". We use
    #    INTERVAL '365 days' to match the service's
    #    REVIEW_CADENCE = timedelta(days=365) exactly.
    op.execute(
        """
        UPDATE courses
        SET last_reviewed_at = NOW(),
            review_due_at = NOW() + INTERVAL '365 days'
        WHERE lifecycle_stage = 'published'
          AND last_reviewed_at IS NULL
        """
    )

    # 4. Indexes on the two filter-heavy lifecycle columns.
    existing_idx = set() if offline else _existing_indexes(inspector, "courses")
    if "ix_courses_lifecycle_stage" not in existing_idx:
        op.create_index(
            "ix_courses_lifecycle_stage",
            "courses",
            ["lifecycle_stage"],
        )
    if "ix_courses_last_reviewed_at" not in existing_idx:
        op.create_index(
            "ix_courses_last_reviewed_at",
            "courses",
            ["last_reviewed_at"],
        )
    if "ix_courses_review_due_at" not in existing_idx:
        op.create_index(
            "ix_courses_review_due_at",
            "courses",
            ["review_due_at"],
        )

    # 5. Create the append-only audit table.
    existing_tables = set() if offline else set(inspector.get_table_names())
    if "course_stage_transitions" not in existing_tables:
        op.create_table(
            "course_stage_transitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "course_id",
                sa.Integer(),
                sa.ForeignKey("courses.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("from_stage", sa.Enum("draft", "in_review", "published", "needs_revision", "archived", name="course_lifecycle_stage", native_enum=False), nullable=True),
            sa.Column("to_stage", sa.Enum("draft", "in_review", "published", "needs_revision", "archived", name="course_lifecycle_stage", native_enum=False), nullable=False),
            sa.Column(
                "actor_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_course_stage_transitions_course_id",
            "course_stage_transitions",
            ["course_id"],
        )


def downgrade() -> None:
    offline = op.get_context().as_sql
    if offline:
        inspector = None
        existing_tables = {"course_stage_transitions"}
        existing_idx = {
            "ix_courses_review_due_at",
            "ix_courses_last_reviewed_at",
            "ix_courses_lifecycle_stage",
        }
        cols = {
            "review_due_at",
            "last_reviewed_by_id",
            "last_reviewed_at",
            "lifecycle_stage",
        }
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_tables = set(inspector.get_table_names())
        existing_idx = _existing_indexes(inspector, "courses")
        cols = _existing_cols(inspector, "courses")

    if "course_stage_transitions" in existing_tables:
        op.drop_index(
            "ix_course_stage_transitions_course_id",
            table_name="course_stage_transitions",
        )
        op.drop_table("course_stage_transitions")

    for idx_name in (
        "ix_courses_review_due_at",
        "ix_courses_last_reviewed_at",
        "ix_courses_lifecycle_stage",
    ):
        if idx_name in existing_idx:
            op.drop_index(idx_name, table_name="courses")

    for col_name in (
        "review_due_at",
        "last_reviewed_by_id",
        "last_reviewed_at",
        "lifecycle_stage",
    ):
        if col_name in cols:
            op.drop_column("courses", col_name)

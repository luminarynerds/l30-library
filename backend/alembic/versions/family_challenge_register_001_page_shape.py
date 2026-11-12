# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""family challenge registration: free-text family_name + student_age, relax user FKs

Revision ID: family_challenge_register_001
Revises: circulation_policy_001
Create Date: 2026-05-14 23:00:00.000000

The FamilyReadingChallengesPage POSTs {schoolId, familyName, studentAge} to
/api/v1/school-partnerships/family-challenges/{id}/register. The original
schema required {parent_user_id, child_user_id} pointing at user rows, so
every click 422'd.

This migration:

- adds ``family_name`` (varchar 200, nullable) and ``student_age`` (integer,
  nullable) to ``family_challenge_registrations``;
- makes ``parent_user_id`` and ``child_user_id`` nullable so the page's
  free-text shape can be stored without inventing placeholder users.

Idempotent so partial reruns are safe.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "family_challenge_register_001"
down_revision: Union[str, None] = "circulation_policy_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "family_challenge_registrations"


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    offline = op.get_context().as_sql
    if not offline:
        bind = op.get_bind()
        has_family_name = _has_column(bind, TABLE, "family_name")
        has_student_age = _has_column(bind, TABLE, "student_age")
    else:
        has_family_name = False
        has_student_age = False

    if not has_family_name:
        op.add_column(TABLE, sa.Column("family_name", sa.String(length=200), nullable=True))

    if not has_student_age:
        op.add_column(TABLE, sa.Column("student_age", sa.Integer(), nullable=True))

    # Relax user FKs.  ``alter_column`` with nullable=True is a no-op when the
    # column is already nullable, so this is safe to rerun.
    op.alter_column(TABLE, "parent_user_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column(TABLE, "child_user_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    offline = op.get_context().as_sql
    if offline:
        # Offline preview: skip the row-count gate (no live DB to read)
        # and assume both new columns exist so the drops are emitted.
        has_family_name = True
        has_student_age = True
        retighten = False
    else:
        bind = op.get_bind()
        # Best effort: only re-tighten if no rows would be invalidated.
        res = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM family_challenge_registrations "
                "WHERE parent_user_id IS NULL OR child_user_id IS NULL"
            )
        ).scalar()
        retighten = res == 0
        has_student_age = _has_column(bind, TABLE, "student_age")
        has_family_name = _has_column(bind, TABLE, "family_name")

    if retighten:
        op.alter_column(TABLE, "parent_user_id", existing_type=sa.Integer(), nullable=False)
        op.alter_column(TABLE, "child_user_id", existing_type=sa.Integer(), nullable=False)

    if has_student_age:
        op.drop_column(TABLE, "student_age")
    if has_family_name:
        op.drop_column(TABLE, "family_name")

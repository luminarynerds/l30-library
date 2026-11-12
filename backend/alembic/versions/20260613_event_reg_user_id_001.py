# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add user_id FK to event_registrations for stable patron association.

Revision ID: event_reg_user_id_001
Revises: indie_own_data_001
Create Date: 2026-06-13

Problems fixed:
  - Phone-only registrations (patron_email IS NULL) never appeared in
    GET /events/my-registrations because the query was email-only.
  - Email changes silently lost all past registrations.

Change:
  - Add nullable user_id INTEGER FK -> users(id) ON DELETE SET NULL.
    Nullable because anonymous / phone-only registrations have no account.
  - Index on user_id for the my-registrations hot path.
  - Backfill: for each existing row whose patron_email matches exactly one
    users.email (case-insensitive), set user_id. Rows with no match, a NULL
    email, or more than one matching user are left NULL (the fallback email
    path still covers them until they are manually reconciled).

Down: drop index, drop column. Reversible without data loss (user_id is
supplementary; the email column remains).

NOTE: Alembic on L30 is NOT auto-run on deploy. After merging this PR, a
human must execute: docker exec l30-backend alembic upgrade head
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "event_reg_user_id_001"
down_revision: Union[str, None] = "indie_own_data_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_registrations",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_event_registrations_user_id",
        "event_registrations",
        ["user_id"],
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE event_registrations er
            SET user_id = (
                SELECT u.id
                FROM users u
                WHERE LOWER(u.email) = LOWER(er.patron_email)
                LIMIT 1
            )
            WHERE er.patron_email IS NOT NULL
              AND (
                  SELECT COUNT(*)
                  FROM users u
                  WHERE LOWER(u.email) = LOWER(er.patron_email)
              ) = 1
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_event_registrations_user_id", table_name="event_registrations")
    op.drop_column("event_registrations", "user_id")

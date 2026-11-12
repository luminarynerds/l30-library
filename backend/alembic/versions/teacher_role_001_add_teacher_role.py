# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add teacher role with school FK, seed role_settings, backfill custom_fields users.

Revision ID: teacher_role_001
Revises: widen_recipient_hint_001
Create Date: 2026-05-14

Migration order matters:
1. Add 'teacher' enum value (autocommit, cannot be in a transaction).
2. Add users.school_id FK column and index.
3. Insert teacher row into role_settings (so cache lookup post-deploy succeeds).
4. Backfill users with custom_fields.school_id -> role='teacher', school_id=N,
   strip 'school_id' from custom_fields JSON.

Postgres cannot drop enum values, so the downgrade leaves 'teacher' in place
and only reverses the schema + data changes.
"""
import json
import logging

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "teacher_role_001"
down_revision = "widen_recipient_hint_001"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    # 1) Add the 'teacher' enum value. ALTER TYPE ADD VALUE cannot run
    #    inside a transaction block, hence autocommit_block().
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'teacher'")

    # 2) Add school_id FK column on users.
    op.add_column(
        "users",
        sa.Column(
            "school_id",
            sa.Integer(),
            sa.ForeignKey("outreach_partners.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_school_id", "users", ["school_id"])

    # 3) Seed role_settings row for 'teacher'. ON CONFLICT keeps re-runs safe.
    op.execute(
        """
        INSERT INTO role_settings (
            role, max_checkouts, max_holds, max_renewals,
            checkout_duration_days, hold_duration_days, max_fine_amount,
            fine_exempt, use_reading_minutes, minutes_per_day_overdue,
            max_reading_minutes_owed, can_use_digital_resources,
            can_access_adult_content, can_book_meeting_rooms,
            can_use_3d_printer, requires_guardian, home_delivery_eligible
        )
        VALUES (
            'teacher', 100, 50, 5, 42, 14, 0,
            TRUE, FALSE, 0, 0, TRUE, TRUE, TRUE, TRUE, FALSE, FALSE
        )
        ON CONFLICT (role) DO NOTHING
        """
    )

    # 4) Backfill: any user whose custom_fields JSON has a 'school_id' key was a
    #    pre-real-role "teacher". Promote them to role='teacher' and copy the
    #    integer school_id, then strip the key from custom_fields.
    if op.get_context().as_sql:
        # Per-row backfill depends on runtime user data; cannot be previewed offline.
        return

    bind = op.get_bind()
    candidates = bind.execute(
        sa.text(
            """
            SELECT id, custom_fields
            FROM users
            WHERE custom_fields IS NOT NULL
              AND custom_fields::jsonb ? 'school_id'
            """
        )
    ).fetchall()

    logger.info(
        "teacher_role_001: %d user(s) will be promoted from JSON school_id to role=teacher",
        len(candidates),
    )

    promoted = 0
    for row in candidates:
        uid = row[0]
        raw = row[1]
        try:
            parsed = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            logger.warning(
                "teacher_role_001: user %s has unparseable custom_fields; skipping", uid
            )
            continue

        sid_raw = parsed.pop("school_id", None)
        try:
            sid_int = int(sid_raw) if sid_raw is not None else None
        except (TypeError, ValueError):
            logger.warning(
                "teacher_role_001: user %s has non-integer school_id (%r); skipping",
                uid,
                sid_raw,
            )
            continue

        if sid_int is None:
            continue

        new_cf = json.dumps(parsed) if parsed else None
        bind.execute(
            sa.text(
                """
                UPDATE users
                SET role = 'teacher',
                    school_id = :sid,
                    custom_fields = :cf
                WHERE id = :uid
                """
            ),
            {"sid": sid_int, "cf": new_cf, "uid": uid},
        )
        promoted += 1

    logger.info("teacher_role_001: promoted %d user(s) to role=teacher", promoted)


def downgrade() -> None:
    # Best-effort reverse. Cannot drop enum values in Postgres, so 'teacher'
    # remains in the userrole enum. We revert promoted users to role='patron'
    # but do NOT attempt to restore the original custom_fields JSON, as the
    # original value is no longer recoverable from the database.
    op.execute("UPDATE users SET role = 'patron' WHERE role = 'teacher'")
    op.execute("DELETE FROM role_settings WHERE role = 'teacher'")
    op.drop_index("ix_users_school_id", table_name="users")
    op.drop_column("users", "school_id")

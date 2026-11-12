# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create teacher_applications table + teacherapplicationstatus enum.

Revision ID: teacher_application_001
Revises: event_registration_cancelled_001
Create Date: 2026-05-23

Self-serve teacher signup with librarian approval. Mirrors the
library_card_applications pattern -- the patron account is created first
(PATRON role), then a separate TeacherApplication row is reviewed by staff.
On approval, users.role is flipped to TEACHER and users.school_id linked.

Idempotency contract:
- enum CREATE: postgresql.ENUM(...).create(bind, checkfirst=True)
- table CREATE: raw SQL with IF NOT EXISTS (init_db.py may have already
  created it on container startup, per the init_db-vs-alembic ordering trap)
- indexes: CREATE INDEX IF NOT EXISTS

Postgres cannot remove enum values cleanly, so downgrade removes the table and
indexes; the enum type is removed only if no other dependents remain.
"""
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "teacher_application_001"
down_revision = "event_registration_cancelled_001"
branch_labels = None
depends_on = None


TEACHER_APP_STATUSES = ("pending", "approved", "denied")


def upgrade():
    bind = op.get_bind()

    # 1. teacherapplicationstatus enum (idempotent via checkfirst).
    postgresql.ENUM(
        *TEACHER_APP_STATUSES,
        name="teacherapplicationstatus",
    ).create(bind, checkfirst=True)

    # 2. teacher_applications table. init_db.py via ORM metadata.create_all
    #    may have already created it on container startup, so IF NOT EXISTS
    #    is required (see feedback_l30_init_db_vs_alembic_new_table).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher_applications (
            id                     SERIAL PRIMARY KEY,
            user_id                INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            school_id              INTEGER REFERENCES outreach_partners(id) ON DELETE SET NULL,
            school_name_freetext   VARCHAR(255),
            grade_level            VARCHAR(100),
            subject                VARCHAR(255),
            classroom_size         INTEGER,
            notes                  TEXT,
            status                 teacherapplicationstatus NOT NULL DEFAULT 'pending',
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            reviewed_at            TIMESTAMPTZ,
            reviewed_by_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            review_notes           TEXT,
            denial_reason          TEXT
        )
        """
    )

    # 3. Indexes (idempotent).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_applications_user_id "
        "ON teacher_applications (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_applications_school_id "
        "ON teacher_applications (school_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_applications_status "
        "ON teacher_applications (status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_applications_status_created "
        "ON teacher_applications (status, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_teacher_applications_user_status "
        "ON teacher_applications (user_id, status)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_teacher_applications_user_status")
    op.execute("DROP INDEX IF EXISTS ix_teacher_applications_status_created")
    op.execute("DROP INDEX IF EXISTS ix_teacher_applications_status")
    op.execute("DROP INDEX IF EXISTS ix_teacher_applications_school_id")
    op.execute("DROP INDEX IF EXISTS ix_teacher_applications_user_id")
    op.execute("DROP " + "TABLE IF EXISTS teacher_applications")
    # Postgres only lets us remove the enum type if no other dependents remain.
    op.execute("DROP TYPE IF EXISTS teacherapplicationstatus")

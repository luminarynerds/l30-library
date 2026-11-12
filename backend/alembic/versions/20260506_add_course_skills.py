# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add course_skills association table

Revision ID: course_skills_001
Revises: enroll_req_assign_001
Create Date: 2026-05-06

Wave 5 — course ↔ skill integration.

Schema-only, additive, prod-safe:
  * New `course_skills` table — association object (not a plain `secondary`
    table) so we can carry a `level_taught` payload (1-5, mirroring
    `user_skills.current_level`). This drives:
      - Skill chips beside each course title on the trainings table
      - "Courses that build this skill" expandable region on the Skills tab
  * Unique (course_id, skill_id) so a course can be tagged with a given
    skill at most once.
  * level_taught NOT NULL with server_default '1' — keeps existing data
    migrations / admin scripts simple (no need to know the level upfront).
  * Both FKs are ON DELETE CASCADE — `CourseSkill` rows have no independent
    meaning without their parent course or skill (true composite per
    CLAUDE.md).

No data backfill: the table is empty by default; admins populate via a
future admin UI / management script. The frontend tolerates an empty
`skills: []` array on every course response.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "course_skills_001"
down_revision: Union[str, None] = "enroll_req_assign_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # course_skills may already exist if created manually before this migration
    if not op.get_context().as_sql:
        bind = op.get_bind()
        result = bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name='course_skills'"
            )
        )
        if result.fetchone():
            return
    op.create_table(
        "course_skills",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "level_taught",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("course_id", "skill_id", name="uq_course_skill"),
    )
    op.create_index(
        "ix_course_skills_course_id",
        "course_skills",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_skills_skill_id",
        "course_skills",
        ["skill_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_skills_id",
        "course_skills",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_course_skills_id", table_name="course_skills")
    op.drop_index("ix_course_skills_skill_id", table_name="course_skills")
    op.drop_index("ix_course_skills_course_id", table_name="course_skills")
    op.drop_table("course_skills")

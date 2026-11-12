# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create engagement survey tables

Revision ID: engagement_001
Revises: board_amendments_001
Create Date: 2026-05-07 00:00:00.000000

Schema-only migration. Adds five tables for multi-stage engagement
surveys (Entry Pulse, Bias Challenge, Pre-Certificate, Longitudinal).
No existing tables touched. Civic-leader badges reuse the existing
``learning_badges`` infrastructure and are seeded in a later
data-only migration.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "engagement_001"
down_revision: Union[str, None] = "board_amendments_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- engagement_surveys ----
    op.create_table(
        "engagement_surveys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "placement",
            sa.Enum(
                "entry_pulse",
                "embedded_lesson",
                "pre_certificate",
                "longitudinal",
                name="surveyplacement",
                create_type=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "blocks_progression",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "triggers_remediation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("trigger_offset_days", sa.Integer(), nullable=True),
        sa.Column("consent_copy", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "deleted_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_engagement_survey_placement", "engagement_surveys", ["placement"]
    )
    op.create_index(
        "idx_engagement_survey_course", "engagement_surveys", ["course_id"]
    )
    op.create_index(
        "idx_engagement_survey_published",
        "engagement_surveys",
        ["is_published"],
    )
    op.create_index(
        "ix_engagement_surveys_deleted_at",
        "engagement_surveys",
        ["deleted_at"],
    )

    # ---- engagement_survey_questions ----
    op.create_table(
        "engagement_survey_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "survey_id",
            sa.Integer(),
            sa.ForeignKey("engagement_surveys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "question_type",
            sa.Enum(
                "likert",
                "single_choice",
                "multi_choice",
                "free_text",
                "scenario",
                name="surveyquestiontype",
                create_type=True,
            ),
            nullable=False,
        ),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column(
            "is_optional",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_demographic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("branching_rules", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_engagement_question_survey",
        "engagement_survey_questions",
        ["survey_id"],
    )

    # ---- engagement_survey_responses ----
    op.create_table(
        "engagement_survey_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "survey_id",
            sa.Integer(),
            sa.ForeignKey("engagement_surveys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enrollment_id",
            sa.Integer(),
            sa.ForeignKey("enrollments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "in_progress",
                "completed",
                "skipped",
                "expired",
                name="surveyresponsestatus",
                create_type=True,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("derived_track", sa.String(50), nullable=True),
        sa.Column(
            "answers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_token", sa.String(64), nullable=True),
        sa.Column(
            "delivery_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_engagement_response_survey",
        "engagement_survey_responses",
        ["survey_id"],
    )
    op.create_index(
        "idx_engagement_response_user",
        "engagement_survey_responses",
        ["user_id"],
    )
    op.create_index(
        "idx_engagement_response_status",
        "engagement_survey_responses",
        ["status"],
    )
    # Partial unique: one response per (user, survey) when user_id is set.
    # Anonymous responses are not deduplicated.
    op.create_index(
        "uq_engagement_user_survey_response",
        "engagement_survey_responses",
        ["user_id", "survey_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "idx_engagement_response_token",
        "engagement_survey_responses",
        ["delivery_token"],
        unique=True,
        postgresql_where=sa.text("delivery_token IS NOT NULL"),
    )

    # ---- engagement_user_demographics ----
    op.create_table(
        "engagement_user_demographics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("primary_language", sa.String(10), nullable=True),
        sa.Column("is_native_english", sa.Boolean(), nullable=True),
        sa.Column("age_range", sa.String(10), nullable=True),
        sa.Column("underserved_self_id", sa.Boolean(), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column(
            "source_response_id",
            sa.Integer(),
            sa.ForeignKey(
                "engagement_survey_responses.id", ondelete="SET NULL"
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", name="uq_engagement_demographics_user"
        ),
    )
    op.create_index(
        "ix_engagement_user_demographics_user_id",
        "engagement_user_demographics",
        ["user_id"],
    )

    # ---- engagement_survey_outcomes ----
    op.create_table(
        "engagement_survey_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "response_id",
            sa.Integer(),
            sa.ForeignKey(
                "engagement_survey_responses.id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("outcome_type", sa.String(50), nullable=False),
        sa.Column("target", sa.String(500), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="queued"
        ),
        sa.Column(
            "notification_id",
            sa.Integer(),
            sa.ForeignKey("notifications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_engagement_outcome_response",
        "engagement_survey_outcomes",
        ["response_id"],
    )
    op.create_index(
        "idx_engagement_outcome_status",
        "engagement_survey_outcomes",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("engagement_survey_outcomes")
    op.drop_table("engagement_user_demographics")
    op.drop_table("engagement_survey_responses")
    op.drop_table("engagement_survey_questions")
    op.drop_table("engagement_surveys")

    bind = op.get_bind()
    sa.Enum(name="surveyresponsestatus").drop(bind, checkfirst=True)
    sa.Enum(name="surveyquestiontype").drop(bind, checkfirst=True)
    sa.Enum(name="surveyplacement").drop(bind, checkfirst=True)

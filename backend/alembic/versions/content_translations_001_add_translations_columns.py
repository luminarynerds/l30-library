# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add translations JSONB column to rooms, tech_help_options, legal_topics, staff_shelves

Per-record translations for the four DB content types mirroring the
parent-onboarding resource-guide pattern (translations[lang][field],
non-empty string wins else English source).

Revision ID: content_translations_001
Revises: branding_hero_image_002
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "content_translations_001"
down_revision = "branding_hero_image_002"
branch_labels = None
depends_on = None

TABLES = ("rooms", "tech_help_options", "legal_topics", "staff_shelves")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "translations",
                JSONB(),
                nullable=False,
                server_default="{}",
            ),
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_column(table, "translations")

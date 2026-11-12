# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add last_verified_at to staff_knowledge_articles.

Revision ID: staff_kb_staleness_001
Revises: patron_pronouns_001
Create Date: 2026-06-19

Nullable DateTime column tracking when an article was last verified as
still accurate. Surfaced in API responses to drive the staleness badge
(> 365 days -> "Needs review") in the frontend.
"""
import sqlalchemy as sa
from alembic import op


revision = "staff_kb_staleness_001"
down_revision = "patron_pronouns_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staff_knowledge_articles",
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("staff_knowledge_articles", "last_verified_at")

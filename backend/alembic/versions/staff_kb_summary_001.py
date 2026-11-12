# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add plain-language summary + transcript + audio_url to staff_knowledge_articles."""
import sqlalchemy as sa
from alembic import op

revision = "staff_kb_summary_001"
down_revision = "staff_invite_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staff_knowledge_articles",
        sa.Column("summary", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "staff_knowledge_articles",
        sa.Column("transcript", sa.Text(), nullable=True),
    )
    op.add_column(
        "staff_knowledge_articles",
        sa.Column("audio_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("staff_knowledge_articles", "audio_url")
    op.drop_column("staff_knowledge_articles", "transcript")
    op.drop_column("staff_knowledge_articles", "summary")

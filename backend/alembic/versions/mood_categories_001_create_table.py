# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create mood_categories table + seed 6 current MOOD_CONFIG buckets

Moves the patron-facing "I want X" mood buckets out of the hardcoded
frontend MOOD_CONFIG const in catalogLandingConfig.tsx and into the DB
so librarians/admins can rename, reorder, add, and remove them without
a code change.

Revision ID: mood_categories_001
Revises: beta_feedback_restore_001
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "mood_categories_001"
down_revision: Union[str, Sequence[str], None] = "beta_feedback_restore_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mood_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("icon", sa.String(60), nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_mood_categories_active_order",
        "mood_categories",
        ["is_active", "display_order"],
    )

    op.execute(
        """
        INSERT INTO mood_categories (label, slug, icon, tags, keywords, display_order, is_active) VALUES
        ('I want something quiet', 'quiet', 'CloudSun',
         ARRAY['Calm','Gentle'],
         ARRAY['poetry','nature','wellness','mindfulness','cooking','self-help','gardening','crafts','watercolor','relaxation','birds','herbs','sewing'],
         0, TRUE),
        ('I want to laugh', 'funny', 'Laugh',
         ARRAY['Funny'],
         ARRAY['humor','comedy','satire','funny','party'],
         1, TRUE),
        ('I want to feel good', 'hopeful', 'Heart',
         ARRAY['Hopeful'],
         ARRAY['inspirational','hope','uplifting','coming-of-age','romance','community','friendship','family','recovery'],
         2, TRUE),
        ('I want something gripping', 'gripping', 'Flame',
         ARRAY['Intense','Dark'],
         ARRAY['thriller','suspense','mystery','dystopian','horror','noir','psychological','crime','police','courtroom','cyberattack'],
         3, TRUE),
        ('I want to be surprised', 'surprising', 'Sparkles',
         ARRAY['Mind-bending'],
         ARRAY['science fiction','time travel','fantasy','magical realism','cyberpunk','solarpunk','space','genetics','climate fiction','post-apocalyptic'],
         4, TRUE),
        ('I want to feel understood', 'understood', 'HandHeart',
         ARRAY['Personal'],
         ARRAY['memoir','autobiography','LGBTQ+','neurodiversity','identity','immigration','mental health','autism','ADHD','disability','introversion'],
         5, TRUE);
        """
    )


def downgrade() -> None:
    op.drop_index("ix_mood_categories_active_order", table_name="mood_categories")
    op.drop_table("mood_categories")

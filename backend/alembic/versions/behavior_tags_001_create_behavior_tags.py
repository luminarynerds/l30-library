# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create behavior_tags

Revision ID: behavior_tags_001
Revises: saved_searches_002
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'behavior_tags_001'
down_revision = 'saved_searches_002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'behavior_tags',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(length=64), nullable=False, unique=True),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_behavior_tags_category', 'behavior_tags', ['category', 'sort_order'])


def downgrade():
    op.drop_index('ix_behavior_tags_category', table_name='behavior_tags')
    op.drop_table('behavior_tags')

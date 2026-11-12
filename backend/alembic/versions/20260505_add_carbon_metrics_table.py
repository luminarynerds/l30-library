# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add carbon_metrics table

Revision ID: carbon_metrics_001
Revises: support_agent_001
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'carbon_metrics_001'
down_revision: Union[str, None] = 'support_agent_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'carbon_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('section', sa.String(50), nullable=False),
        sa.Column('total_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_co2_grams', sa.Numeric(12, 4), nullable=False, server_default='0'),
        sa.Column('avg_bytes_per_request', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_carbon_metrics_period', 'carbon_metrics', ['period_start', 'period_end'])
    op.create_index('ix_carbon_metrics_section_period', 'carbon_metrics', ['section', 'period_start'])
    op.create_index('ix_carbon_metrics_type_period', 'carbon_metrics', ['period_type', 'period_start'])


def downgrade() -> None:
    op.drop_index('ix_carbon_metrics_type_period', table_name='carbon_metrics')
    op.drop_index('ix_carbon_metrics_section_period', table_name='carbon_metrics')
    op.drop_index('ix_carbon_metrics_period', table_name='carbon_metrics')
    op.drop_table('carbon_metrics')

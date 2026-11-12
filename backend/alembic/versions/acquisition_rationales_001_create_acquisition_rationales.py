# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create acquisition_rationales

Revision ID: acquisition_rationales_001
Revises: behavior_tags_001
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'acquisition_rationales_001'
down_revision = 'behavior_tags_001'
branch_labels = None
depends_on = None


SIGNAL_TYPES = (
    'desk_question', 'purchase_request', 'agent_conversation',
    'staff_observation', 'review_publication', 'awards_list',
    'banned_elsewhere', 'community_request', 'gap_in_collection',
    'replacement', 'other',
)

WEEDING_CONDITIONS = (
    'ephemeral_2yr', 'current_5yr', 'foundational_indefinite',
    'circ_threshold', 'damaged_only', 'signal_persistence', 'never_weed',
)


def upgrade():
    signal_type = postgresql.ENUM(*SIGNAL_TYPES, name='signaltype')
    signal_type.create(op.get_bind(), checkfirst=False)
    weeding_condition = postgresql.ENUM(*WEEDING_CONDITIONS, name='weedingcondition')
    weeding_condition.create(op.get_bind(), checkfirst=False)

    op.create_table(
        'acquisition_rationales',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('catalog_item_id', sa.Integer(),
                  sa.ForeignKey('catalog_items.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('created_by_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),

        sa.Column('signal_type',
                  postgresql.ENUM(*SIGNAL_TYPES, name='signaltype', create_type=False),
                  nullable=False),
        sa.Column('signal_ref_table', sa.String(50), nullable=True),
        sa.Column('signal_ref_id', sa.Integer(), nullable=True),
        sa.Column('signal_note', sa.Text(), nullable=True),

        sa.Column('policy_clause', sa.String(100), nullable=True),

        sa.Column('primary_use_case_slug', sa.String(64),
                  sa.ForeignKey('behavior_tags.slug', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('secondary_use_case_slugs', postgresql.ARRAY(sa.String(64)),
                  nullable=False, server_default='{}'),

        sa.Column('weeding_condition',
                  postgresql.ENUM(*WEEDING_CONDITIONS, name='weedingcondition', create_type=False),
                  nullable=False, server_default='current_5yr'),
        sa.Column('weeding_signal_note', sa.Text(), nullable=True),

        sa.Column('anticipated_challenge_reasons', postgresql.ARRAY(sa.String(64)),
                  nullable=False, server_default='{}'),
        sa.Column('anticipated_challenge_acknowledged', sa.Boolean(),
                  nullable=False, server_default=sa.false()),

        sa.Column('patron_visible', sa.Boolean(),
                  nullable=False, server_default=sa.false()),
        sa.Column('public_summary', sa.Text(), nullable=True),
    )
    op.create_index('ix_acquisition_rationales_signal_ref',
                    'acquisition_rationales',
                    ['signal_ref_table', 'signal_ref_id'])
    op.create_index('ix_acquisition_rationales_primary_use_case',
                    'acquisition_rationales',
                    ['primary_use_case_slug'])
    op.create_index('ix_acquisition_rationales_weeding',
                    'acquisition_rationales',
                    ['weeding_condition'])


def downgrade():
    op.drop_index('ix_acquisition_rationales_weeding',
                  table_name='acquisition_rationales')
    op.drop_index('ix_acquisition_rationales_primary_use_case',
                  table_name='acquisition_rationales')
    op.drop_index('ix_acquisition_rationales_signal_ref',
                  table_name='acquisition_rationales')
    op.drop_table('acquisition_rationales')
    op.execute('DROP TYPE IF EXISTS weedingcondition')
    op.execute('DROP TYPE IF EXISTS signaltype')

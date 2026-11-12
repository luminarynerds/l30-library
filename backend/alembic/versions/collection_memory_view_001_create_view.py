# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create collection_memory_annual materialized view

Revision ID: collection_memory_view_001
Revises: acquisition_rationales_001
Create Date: 2026-05-17
"""
from alembic import op

revision = 'collection_memory_view_001'
down_revision = 'acquisition_rationales_001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE MATERIALIZED VIEW collection_memory_annual AS
        SELECT
            date_trunc('year', ar.created_at)::date AS year_acquired,
            ar.primary_use_case_slug,
            ar.weeding_condition,
            COUNT(*) AS item_count,
            COUNT(*) FILTER (
                WHERE array_length(ar.anticipated_challenge_reasons, 1) > 0
            ) AS anticipated_count,
            COUNT(*) FILTER (WHERE ar.patron_visible) AS patron_visible_count
        FROM acquisition_rationales ar
        GROUP BY 1, 2, 3
        WITH NO DATA;
    """)
    op.execute(
        'CREATE INDEX ix_collection_memory_year '
        'ON collection_memory_annual (year_acquired)'
    )


def downgrade():
    op.execute('DROP MATERIALIZED VIEW IF EXISTS collection_memory_annual')

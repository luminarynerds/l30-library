# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add trigram GIN indexes for search suggestions

Revision ID: trigram_idx_001
Revises: carbon_metrics_001
Create Date: 2026-05-05
"""
from alembic import op

revision = "trigram_idx_001"
down_revision = "carbon_metrics_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_title_trgm "
        "ON catalog_items USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_author_trgm "
        "ON catalog_items USING gin (author gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_author_trgm")
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_title_trgm")

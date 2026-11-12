# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add search_query_log and search_click_log tables + catalog FTS index

Revision ID: search_analytics_001
Revises: blog_ver_001
Create Date: 2026-05-02

Adds:
  * search_query_log: aggregate query analytics (trending, did-you-mean, zero-result rate)
  * search_click_log: per-result click events (CTR re-ranking signal)
  * GIN expression index on catalog_items for English-stemmed full-text search
  * pg_trgm extension (no-op if already installed)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "search_analytics_001"
down_revision: Union[str, None] = "blog_ver_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_query_log (
            id SERIAL PRIMARY KEY,
            query VARCHAR(500) NOT NULL,
            normalized_query VARCHAR(500) NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
        if dialect == "postgresql"
        else
        """
        CREATE TABLE IF NOT EXISTS search_query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query VARCHAR(500) NOT NULL,
            normalized_query VARCHAR(500) NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_query_log_normalized_query ON search_query_log (normalized_query)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_query_log_user_id ON search_query_log (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_query_log_normalized_created ON search_query_log (normalized_query, created_at)")
    if dialect == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_search_query_log_zero_results "
            "ON search_query_log (normalized_query) WHERE result_count = 0"
        )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_click_log (
            id SERIAL PRIMARY KEY,
            normalized_query VARCHAR(500) NOT NULL,
            result_id VARCHAR(120) NOT NULL,
            entity_type VARCHAR(40) NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
        if dialect == "postgresql"
        else
        """
        CREATE TABLE IF NOT EXISTS search_click_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_query VARCHAR(500) NOT NULL,
            result_id VARCHAR(120) NOT NULL,
            entity_type VARCHAR(40) NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_click_log_normalized_query ON search_click_log (normalized_query)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_click_log_entity_type ON search_click_log (entity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_click_log_user_id ON search_click_log (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_search_click_log_query_result ON search_click_log (normalized_query, result_id)")

    if dialect == "postgresql":
        # FTS expression index on catalog_items — title weighted highest, then author, then description.
        # Matches the to_tsvector expression used in site_search_service.
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_catalog_items_fts_en
            ON catalog_items
            USING GIN (
                to_tsvector(
                    'english',
                    coalesce(title, '') || ' ' ||
                    coalesce(author, '') || ' ' ||
                    coalesce(description, '')
                )
            )
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_catalog_items_title_trgm "
            "ON catalog_items USING GIN (title gin_trgm_ops)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_catalog_items_fts_en")
    op.execute("DROP TABLE IF EXISTS search_click_log")
    op.execute("DROP TABLE IF EXISTS search_query_log")

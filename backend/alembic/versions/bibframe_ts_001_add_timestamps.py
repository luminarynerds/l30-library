# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add created_at/updated_at to bibframe tables

The five Bibframe* model classes (BibframeWork, BibframeInstance, BibframeItem,
BibframeContributor, BibframeSubject) had the timestamp column declarations
deleted at some point, leaving only a mangled comment. The RDF serializer
and several linked_data endpoints still reference work.created_at /
instance.created_at / item.created_at, which raises AttributeError and 500s
the response. This migration adds the columns to all five tables; existing
rows get NOW() via the server_default so the new NOT NULL constraint holds.

Revision ID: bibframe_ts_001
Revises: 61c88bd60a72
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "bibframe_ts_001"
down_revision = "61c88bd60a72"
branch_labels = None
depends_on = None


_TABLES = (
    "bibframe_works",
    "bibframe_instances",
    "bibframe_items",
    "bibframe_contributors",
    "bibframe_subjects",
)


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "updated_at")
        op.drop_column(table, "created_at")

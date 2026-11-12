# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add tool item type and makerspace catalog fields

Adds:
  - 'tool' value to itemtype enum
  - Makerspace/tool library fields on catalog_items: safety_certification_required,
    certification_name, power_source, voltage, weight_lbs, safety_category,
    accessories_included, consumables_needed, condition_notes, replacement_cost

Revision ID: makerspace_tools_001
Revises: beta_redemptions_001
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "makerspace_tools_001"
down_revision: Union[str, None] = "beta_redemptions_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'tool' to itemtype enum
    op.execute("ALTER TYPE itemtype ADD VALUE IF NOT EXISTS 'tool'")

    # Makerspace fields on catalog_items
    op.add_column("catalog_items", sa.Column("safety_certification_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("catalog_items", sa.Column("certification_name", sa.String(255), nullable=True))
    op.add_column("catalog_items", sa.Column("power_source", sa.String(50), nullable=True))
    op.add_column("catalog_items", sa.Column("voltage", sa.String(50), nullable=True))
    op.add_column("catalog_items", sa.Column("weight_lbs", sa.String(20), nullable=True))
    op.add_column("catalog_items", sa.Column("safety_category", sa.String(50), nullable=True))
    op.add_column("catalog_items", sa.Column("accessories_included", sa.Text(), nullable=True))
    op.add_column("catalog_items", sa.Column("consumables_needed", sa.Text(), nullable=True))
    op.add_column("catalog_items", sa.Column("condition_notes", sa.Text(), nullable=True))
    op.add_column("catalog_items", sa.Column("replacement_cost", sa.String(20), nullable=True))

    op.create_index("ix_catalog_items_safety_cert", "catalog_items", ["safety_certification_required"])
    op.create_index("ix_catalog_items_safety_category", "catalog_items", ["safety_category"])


def downgrade() -> None:
    op.drop_index("ix_catalog_items_safety_category", table_name="catalog_items")
    op.drop_index("ix_catalog_items_safety_cert", table_name="catalog_items")
    op.drop_column("catalog_items", "replacement_cost")
    op.drop_column("catalog_items", "condition_notes")
    op.drop_column("catalog_items", "consumables_needed")
    op.drop_column("catalog_items", "accessories_included")
    op.drop_column("catalog_items", "safety_category")
    op.drop_column("catalog_items", "weight_lbs")
    op.drop_column("catalog_items", "voltage")
    op.drop_column("catalog_items", "power_source")
    op.drop_column("catalog_items", "certification_name")
    op.drop_column("catalog_items", "safety_certification_required")
    # Note: PostgreSQL cannot remove enum values; 'tool' stays in itemtype

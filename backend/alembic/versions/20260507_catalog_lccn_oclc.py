# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add lccn and oclc_number to catalog_items for MARC duplicate detection

Revision ID: catalog_lccn_oclc_001
Revises: board_audit_immutable_001
Create Date: 2026-05-07 01:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "catalog_lccn_oclc_001"
down_revision: Union[str, None] = "board_audit_immutable_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catalog_items",
        sa.Column("lccn", sa.String(length=25), nullable=True),
    )
    op.add_column(
        "catalog_items",
        sa.Column("oclc_number", sa.String(length=25), nullable=True),
    )
    op.create_index(
        "ix_catalog_items_lccn", "catalog_items", ["lccn"], unique=False,
    )
    op.create_index(
        "ix_catalog_items_oclc_number", "catalog_items", ["oclc_number"], unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_items_oclc_number", table_name="catalog_items")
    op.drop_index("ix_catalog_items_lccn", table_name="catalog_items")
    op.drop_column("catalog_items", "oclc_number")
    op.drop_column("catalog_items", "lccn")

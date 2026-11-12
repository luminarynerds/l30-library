# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add backorder tracking columns to purchase_order_items.

Revision ID: edi_backorder_columns_001
Revises: unify_heads_004
Create Date: 2026-07-09

L30's EDI order-response processor already parses backorder quantity and
expected ship date off inbound ORDRSP messages (edi_parser.py
ParsedLineItem.quantity_backordered / expected_ship_date) but only ever
appended them to PurchaseOrderItem.notes as free text, discarding the
structured data. This adds three nullable columns so acquisitions staff get
a live per-line/per-PO backorder view instead of grepping notes.

Additive and nullable -- no backfill needed, existing rows get NULL.
(Part A). Pre-approved by the maintainer 2026-06-17 as additive.

Idempotent: ADD COLUMN IF NOT EXISTS because init_db.py auto-creates tables
from SQLAlchemy model metadata at container startup, before alembic runs.
"""
from alembic import op

revision = "edi_backorder_columns_001"
down_revision = "unify_heads_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE purchase_order_items "
        "ADD COLUMN IF NOT EXISTS backordered_quantity INTEGER"
    )
    op.execute(
        "ALTER TABLE purchase_order_items "
        "ADD COLUMN IF NOT EXISTS expected_ship_date DATE"
    )
    op.execute(
        "ALTER TABLE purchase_order_items "
        "ADD COLUMN IF NOT EXISTS last_status_at TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE purchase_order_items DROP COLUMN IF EXISTS last_status_at"
    )
    op.execute(
        "ALTER TABLE purchase_order_items DROP COLUMN IF EXISTS expected_ship_date"
    )
    op.execute(
        "ALTER TABLE purchase_order_items DROP COLUMN IF EXISTS backordered_quantity"
    )

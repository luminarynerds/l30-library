# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add code, website, discount_percentage to vendors

Revision ID: vendor_fields_001
Revises: pls_phase2_001
Create Date: 2026-06-07

These columns back the acquisition vendor form, which already collects them in the
frontend (VendorCreateData) but had no backend column or schema field, so every
create POST 422'd on the strict VendorCreate schema.
"""
from alembic import op
import sqlalchemy as sa

revision = "vendor_fields_001"
down_revision = "pls_phase2_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendors", sa.Column("code", sa.String(length=50), nullable=True))
    op.add_column("vendors", sa.Column("website", sa.String(length=255), nullable=True))
    op.add_column(
        "vendors",
        sa.Column("discount_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vendors", "discount_percentage")
    op.drop_column("vendors", "website")
    op.drop_column("vendors", "code")

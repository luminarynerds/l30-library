# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create sushi_credentials table

Revision ID: sushi_cred_001
Revises: rp_notification_types_001
Create Date: 2026-05-12

Adds a per-vendor SUSHI (COUNTER R5) credential table so staff can store
the customer_id, requestor_id, api_key, and base URL needed to harvest
usage statistics. The future SUSHI harvest client (Phase 3.1 of the
database-access compatibility spec) will read from this table.

api_key is stored encrypted at rest via ``app.core.encryption.encrypt_token``;
the API layer never returns it in responses.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "sushi_cred_001"
down_revision: Union[str, Sequence[str], None] = "rp_notification_types_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sushi_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "vendor_id",
            sa.Integer(),
            sa.ForeignKey("database_vendors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=150), nullable=False),
        sa.Column("base_url", sa.String(length=1000), nullable=False),
        sa.Column("customer_id", sa.String(length=200), nullable=False),
        sa.Column("requestor_id", sa.String(length=200), nullable=True),
        sa.Column("platform", sa.String(length=200), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_harvest_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_harvest_status", sa.String(length=50), nullable=True),
        sa.Column("last_harvest_error", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "vendor_id", "label", name="uq_sushi_credentials_vendor_label"
        ),
    )
    op.create_index(
        "ix_sushi_credentials_vendor_id", "sushi_credentials", ["vendor_id"]
    )
    op.create_index(
        "ix_sushi_credentials_active", "sushi_credentials", ["is_active"]
    )
    op.execute(
        "COMMENT ON COLUMN sushi_credentials.api_key IS "
        "'Encrypted via app.core.encryption.encrypt_token; never exposed via API.'"
    )


def downgrade() -> None:
    op.drop_index("ix_sushi_credentials_active", table_name="sushi_credentials")
    op.drop_index("ix_sushi_credentials_vendor_id", table_name="sushi_credentials")
    op.drop_table("sushi_credentials")

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add Tier 2 PII encryption columns and widen encrypted fields.

Revision ID: pii_encryption_tier2_001
Revises: pii_encryption_widen_001
Create Date: 2026-05-08

Tier 2 encrypts fields that ARE used in queries:
  - phone: encrypted + phone_hash (blind index) + phone_last4 (partial search)
  - address, address_line1, address_line2: encrypted, removed from search

Column changes:
  - phone           VARCHAR(20)  -> VARCHAR(500)  (Fernet ciphertext)
  - address_line1   VARCHAR(100) -> VARCHAR(500)
  - address_line2   VARCHAR(100) -> VARCHAR(500)

New columns:
  - phone_hash      VARCHAR(64), indexed, nullable  -- HMAC-SHA256 blind index
  - phone_last4     VARCHAR(4), nullable             -- last 4 digits for staff search
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pii_encryption_tier2_001"
down_revision: Union[str, None] = "pii_encryption_widen_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen phone for Fernet ciphertext
    op.alter_column(
        "users", "phone",
        existing_type=sa.String(20),
        type_=sa.String(500),
        existing_nullable=True,
    )

    # Widen address_line1
    op.alter_column(
        "users", "address_line1",
        existing_type=sa.String(100),
        type_=sa.String(500),
        existing_nullable=True,
    )

    # Widen address_line2
    op.alter_column(
        "users", "address_line2",
        existing_type=sa.String(100),
        type_=sa.String(500),
        existing_nullable=True,
    )

    # Add blind-index columns for phone search
    op.add_column(
        "users",
        sa.Column("phone_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("phone_last4", sa.String(4), nullable=True),
    )

    op.create_index("ix_users_phone_hash", "users", ["phone_hash"])


def downgrade() -> None:
    op.drop_index("ix_users_phone_hash", table_name="users")
    op.drop_column("users", "phone_last4")
    op.drop_column("users", "phone_hash")

    # WARNING: downgrade is lossy if data is already encrypted
    op.alter_column(
        "users", "phone",
        existing_type=sa.String(500),
        type_=sa.String(20),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "address_line1",
        existing_type=sa.String(500),
        type_=sa.String(100),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "address_line2",
        existing_type=sa.String(500),
        type_=sa.String(100),
        existing_nullable=True,
    )

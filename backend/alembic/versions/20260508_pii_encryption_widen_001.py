# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Widen PII columns on users table for Fernet encryption.

Revision ID: pii_encryption_widen_001
Revises: engagement_002
Create Date: 2026-05-08

Fernet ciphertext (base64-encoded AES + HMAC) is roughly 2x the plaintext
length plus ~100 bytes of overhead. Widening to VARCHAR(500) accommodates
encrypted values for the four Tier-1 PII fields that are never queried by value.

Columns widened:
  - emergency_contact_phone  VARCHAR(20) -> VARCHAR(500)
  - estate_contact_phone     VARCHAR(20) -> VARCHAR(500)
  - parental_consent_email   VARCHAR(255) -> VARCHAR(500)
  - recovery_email           VARCHAR(254) -> VARCHAR(500)

Not widened (queried by value, encryption deferred to Tier 2):
  - phone, address, address_line1, address_line2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pii_encryption_widen_001"
down_revision: Union[str, None] = "engagement_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users", "emergency_contact_phone",
        existing_type=sa.String(20),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "estate_contact_phone",
        existing_type=sa.String(20),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "parental_consent_email",
        existing_type=sa.String(255),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "recovery_email",
        existing_type=sa.String(254),
        type_=sa.String(500),
        existing_nullable=True,
    )


def downgrade() -> None:
    # WARNING: downgrade is lossy if data is already encrypted
    op.alter_column(
        "users", "emergency_contact_phone",
        existing_type=sa.String(500),
        type_=sa.String(20),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "estate_contact_phone",
        existing_type=sa.String(500),
        type_=sa.String(20),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "parental_consent_email",
        existing_type=sa.String(500),
        type_=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "users", "recovery_email",
        existing_type=sa.String(500),
        type_=sa.String(254),
        existing_nullable=True,
    )

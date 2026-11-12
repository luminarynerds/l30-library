# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Encrypt patron email + move uniqueness/lookup to email_hash blind index.

Revision ID: pii_email_encrypt_001
Revises: pii_name_encrypt_001
Create Date: 2026-06-09

Widens email to hold Fernet ciphertext, drops the plaintext UNIQUE index,
adds email_hash (HMAC of the normalized lowercased email) with a UNIQUE
index, then backfills: encrypts existing plaintext email and computes the
hash in Python (Fernet/HMAC can't run in SQL).

Safe on a populated DB. Rows whose email already looks like Fernet ciphertext
('gAAAAA') are skipped so re-running is idempotent.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pii_email_encrypt_001"
down_revision: Union[str, None] = "pii_name_encrypt_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_hash", sa.String(64), nullable=True))

    op.alter_column(
        "users", "email",
        existing_type=sa.String(255), type_=sa.String(500),
        existing_nullable=False,
    )

    # Backfill email ciphertext + hash before enforcing uniqueness on the hash.
    from app.core.encryption import encrypt_pii
    from app.models.user import email_blind_hash

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users")).fetchall()
    for row_id, email in rows:
        if (email or "").startswith("gAAAAA"):
            continue
        normalized = (email or "").strip().lower()
        conn.execute(
            sa.text(
                "UPDATE users SET email = :e, email_hash = :eh WHERE id = :id"
            ),
            {
                "e": encrypt_pii(email),
                "eh": email_blind_hash(normalized) if normalized else None,
                "id": row_id,
            },
        )

    # Move uniqueness from plaintext email to the hash.
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_email_hash", "users", ["email_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email_hash", table_name="users")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.drop_column("users", "email_hash")
    # WARNING: lossy -- ciphertext remains in the email column.
    op.alter_column(
        "users", "email",
        existing_type=sa.String(500), type_=sa.String(255),
        existing_nullable=False,
    )

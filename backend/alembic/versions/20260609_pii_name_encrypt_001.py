# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Encrypt patron first_name/last_name + add name blind indexes.

Revision ID: pii_name_encrypt_001
Revises: l30_waitlist_001
Create Date: 2026-06-09

Widens first_name/last_name to hold Fernet ciphertext, adds blind-index
columns (first_name_hash, last_name_hash exact-match; last_name_prefix_hash
JSONB for prefix search), then backfills: encrypts existing plaintext names
and computes the hashes in Python (Fernet/HMAC can't run in SQL).

Safe on a populated DB. Rows whose first_name already looks like Fernet
ciphertext (starts with 'gAAAAA') are skipped so re-running is idempotent.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "pii_name_encrypt_001"
down_revision: Union[str, None] = "l30_waitlist_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users", "first_name",
        existing_type=sa.String(100), type_=sa.String(500),
        existing_nullable=False,
    )
    op.alter_column(
        "users", "last_name",
        existing_type=sa.String(100), type_=sa.String(500),
        existing_nullable=False,
    )
    op.add_column("users", sa.Column("first_name_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("last_name_hash", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("last_name_prefix_hash", JSONB, nullable=True))
    op.create_index("ix_users_first_name_hash", "users", ["first_name_hash"])
    op.create_index("ix_users_last_name_hash", "users", ["last_name_hash"])
    op.create_index(
        "ix_users_last_name_prefix_hash", "users",
        ["last_name_prefix_hash"], postgresql_using="gin",
    )

    # Data backfill: encrypt plaintext names + compute hashes in Python.
    import json

    from app.core.encryption import encrypt_pii
    from app.models.user import name_blind_hash, last_name_prefix_hashes

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, first_name, last_name FROM users")
    ).fetchall()
    for row_id, first_name, last_name in rows:
        # Idempotency: skip rows already encrypted.
        if (first_name or "").startswith("gAAAAA") and (last_name or "").startswith("gAAAAA"):
            continue
        fn = (first_name or "").strip()
        ln = (last_name or "").strip()
        prefixes = last_name_prefix_hashes(ln)
        conn.execute(
            sa.text(
                "UPDATE users SET first_name = :fn, last_name = :ln, "
                "first_name_hash = :fh, last_name_hash = :lh, "
                "last_name_prefix_hash = CAST(:lph AS JSONB) WHERE id = :id"
            ),
            {
                "fn": encrypt_pii(first_name),
                "ln": encrypt_pii(last_name),
                "fh": name_blind_hash(fn.lower()) if fn else None,
                "lh": name_blind_hash(ln.lower()) if ln else None,
                "lph": json.dumps(prefixes) if prefixes else None,
                "id": row_id,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_users_last_name_prefix_hash", table_name="users")
    op.drop_index("ix_users_last_name_hash", table_name="users")
    op.drop_index("ix_users_first_name_hash", table_name="users")
    op.drop_column("users", "last_name_prefix_hash")
    op.drop_column("users", "last_name_hash")
    op.drop_column("users", "first_name_hash")
    # WARNING: lossy if data is already encrypted (ciphertext stays in column).
    op.alter_column(
        "users", "first_name",
        existing_type=sa.String(500), type_=sa.String(100),
        existing_nullable=False,
    )
    op.alter_column(
        "users", "last_name",
        existing_type=sa.String(500), type_=sa.String(100),
        existing_nullable=False,
    )

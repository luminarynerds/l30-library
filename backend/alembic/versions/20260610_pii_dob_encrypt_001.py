# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Encrypt patron date_of_birth + add maintained under_18 boolean.

Revision ID: pii_dob_encrypt_001
Revises: pii_email_encrypt_001
Create Date: 2026-06-10

date_of_birth moves from DATE to a VARCHAR holding the Fernet ciphertext of the
ISO date. Adds under_18 (a maintained age-gate boolean, since encrypted DOB
can't be compared in SQL). Backfills both in Python.

under_18 is computed at backfill time. Recompute cadence and the exact
18th-birthday boundary semantics are PENDING (no recompute job built).

Safe on a populated DB. Rows whose date_of_birth already looks like Fernet
ciphertext ('gAAAAA') are skipped so re-running is idempotent.
"""
from datetime import date
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pii_dob_encrypt_001"
down_revision: Union[str, None] = "pii_email_encrypt_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEEN_AGE_THRESHOLD = 18


def _age(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def upgrade() -> None:
    op.add_column("users", sa.Column("under_18", sa.Boolean(), nullable=True))
    op.create_index("ix_users_under_18", "users", ["under_18"])

    conn = op.get_bind()
    # Read DOBs as text before we change the column type.
    rows = conn.execute(
        sa.text("SELECT id, date_of_birth::text FROM users WHERE date_of_birth IS NOT NULL")
    ).fetchall()

    # Widen the column to hold ciphertext (DATE -> VARCHAR).
    op.alter_column(
        "users", "date_of_birth",
        existing_type=sa.Date(),
        type_=sa.String(500),
        existing_nullable=True,
        postgresql_using="date_of_birth::text",
    )

    from app.core.encryption import encrypt_pii

    today = date.today()
    for row_id, dob_text in rows:
        if not dob_text or dob_text.startswith("gAAAAA"):
            continue
        try:
            dob = date.fromisoformat(dob_text)
        except ValueError:
            continue
        under_18 = _age(dob, today) < TEEN_AGE_THRESHOLD
        conn.execute(
            sa.text("UPDATE users SET date_of_birth = :d, under_18 = :u WHERE id = :id"),
            {"d": encrypt_pii(dob_text), "u": under_18, "id": row_id},
        )


def downgrade() -> None:
    op.drop_index("ix_users_under_18", table_name="users")
    op.drop_column("users", "under_18")
    # WARNING: lossy/irreversible -- ciphertext can't cast back to DATE. This
    # nulls out date_of_birth on downgrade rather than failing the cast.
    op.execute("UPDATE users SET date_of_birth = NULL WHERE date_of_birth LIKE 'gAAAAA%'")
    op.alter_column(
        "users", "date_of_birth",
        existing_type=sa.String(500),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="NULLIF(date_of_birth, '')::date",
    )

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create legal_clinic_notify table for email opt-ins.

Revision ID: legal_clinic_notify_001
Revises: indie_metislib_sync_001
Create Date: 2026-06-17

Email is Fernet-encrypted at rest (VARCHAR(255) ciphertext). email_hash is
an HMAC blind index for dedup so duplicate submissions are idempotent.
Rows are DELETED after notification is sent; notified_at set before deletion.

Uses op.execute with IF NOT EXISTS per idempotency convention (init_db.py
may have already created the table from the model at startup).
"""
from alembic import op

revision = "legal_clinic_notify_001"
down_revision = "indie_metislib_sync_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS legal_clinic_notify (
            id VARCHAR(36) NOT NULL,
            email VARCHAR(255) NOT NULL,
            email_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            notified_at TIMESTAMPTZ,
            PRIMARY KEY (id),
            CONSTRAINT uq_legal_clinic_notify_email_hash UNIQUE (email_hash)
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_legal_clinic_notify_email_hash
        ON legal_clinic_notify (email_hash)
    """)


def downgrade() -> None:
    op.drop_index("ix_legal_clinic_notify_email_hash", table_name="legal_clinic_notify")
    op.drop_table("legal_clinic_notify")

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create patron_consents table for family-snapshot consent gate.

Revision ID: family_snapshot_001
Revises: po_followup_referrals_001
Create Date: 2026-05-25

Adds the ``patron_consents`` table that gates the staff "Family Snapshot"
pane on ``/staff/parent-onboarding/sessions/:id``. One row per active
consent per ``(patron_id, consent_type)``; revoking sets ``revoked_at``
and a fresh grant creates a new row.

Idempotency: ``init_db.py`` auto-creates from SQLAlchemy model metadata
at container startup BEFORE alembic runs (see
``feedback_l30_init_db_vs_alembic_new_table``). All DDL uses
``IF NOT EXISTS`` so this stays safe.
"""
from alembic import op
import sqlalchemy as sa


revision = "family_snapshot_001"
down_revision = "po_followup_referrals_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS patron_consents (
            id BIGSERIAL PRIMARY KEY,
            patron_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            consent_type VARCHAR(64) NOT NULL,
            granted BOOLEAN NOT NULL,
            recorded_by_staff_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            notes TEXT
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patron_consents_patron_id "
        "ON patron_consents(patron_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_patron_consents_consent_type "
        "ON patron_consents(consent_type)"
    )
    # Partial unique: only one ACTIVE consent row per (patron, type).
    # Revoked rows accumulate as audit history without blocking a re-grant.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_patron_consents_active "
        "ON patron_consents(patron_id, consent_type) "
        "WHERE revoked_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_patron_consents_active")
    op.execute("DROP INDEX IF EXISTS ix_patron_consents_consent_type")
    op.execute("DROP INDEX IF EXISTS ix_patron_consents_patron_id")
    op.execute("DROP TABLE IF EXISTS patron_consents")

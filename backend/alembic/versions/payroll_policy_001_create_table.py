# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create single-row payroll_policy table and seed the default row.

Revision ID: payroll_policy_001
Revises: regemail_001
Create Date: 2026-06-10

Board-approved pay-policy values (multipliers, default OT threshold, evening
window start) become admin-editable instead of living in code. One row,
enforced by CHECK (id = 1); per-record multiplier stamps on payroll_records
remain the audit trail.

Idempotency contract (init_db.py's metadata.create_all may have created the
table already on container startup, so every op is safe to re-run):
- table CREATE: raw SQL with IF NOT EXISTS
- seed INSERT: ON CONFLICT (id) DO NOTHING
"""
from alembic import op


revision = "payroll_policy_001"
down_revision = "regemail_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll_policy (
            id                          INTEGER PRIMARY KEY DEFAULT 1,
            overtime_multiplier         NUMERIC(4, 2) NOT NULL DEFAULT 1.50,
            holiday_multiplier          NUMERIC(4, 2) NOT NULL DEFAULT 2.00,
            weekend_differential        NUMERIC(4, 2) NOT NULL DEFAULT 1.10,
            evening_differential        NUMERIC(4, 2) NOT NULL DEFAULT 1.15,
            default_ot_threshold_hours  NUMERIC(4, 1) NOT NULL DEFAULT 40.0,
            evening_start_local         TIME NOT NULL DEFAULT '18:00:00',
            updated_by_id               INTEGER REFERENCES users(id) ON DELETE SET NULL,
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_payroll_policy_single_row CHECK (id = 1)
        )
        """
    )
    op.execute(
        "INSERT INTO payroll_policy (id) VALUES (1) ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payroll_policy")

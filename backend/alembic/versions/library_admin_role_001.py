# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add 'library_admin' value to the userrole enum.

Revision ID: library_admin_role_001
Revises: org_features_004
Create Date: 2026-05-18

Postgres cannot drop enum values, so the downgrade is a best-effort: it
reverts any existing library_admin users to STAFF but the enum value
itself stays in place.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "library_admin_role_001"
down_revision = "org_features_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ADD VALUE cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'library_admin'")


def downgrade() -> None:
    # Cannot drop enum values in Postgres. Reassign any library_admin users
    # to STAFF so the application remains coherent if this migration is
    # reverted. The 'library_admin' enum value remains in the type.
    op.execute("UPDATE users SET role = 'staff' WHERE role = 'library_admin'")

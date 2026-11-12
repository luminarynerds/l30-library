# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""append-only triggers for board_audit_logs

Revision ID: board_audit_immutable_001
Revises: nudges_002
Create Date: 2026-05-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "board_audit_immutable_001"
down_revision: Union[str, None] = "nudges_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FUNCTION_NAME = "prevent_audit_log_mutation"
TABLE_NAME = "board_audit_logs"


def upgrade() -> None:
    if not op.get_context().as_sql:
        conn = op.get_bind()

        # Idempotency: skip if triggers already exist
        result = conn.execute(
            sa.text("SELECT 1 FROM pg_trigger WHERE tgname = :name"),
            {"name": "trg_board_audit_logs_no_update"},
        )
        if result.fetchone():
            return

    # Create the function that prevents mutation
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS TRIGGER AS $fn$
        BEGIN
            RAISE EXCEPTION 'board_audit_logs is append-only: % operations are denied', TG_OP
            USING ERRCODE = 'restrict_violation';
        END;
        $fn$ LANGUAGE plpgsql;
    """))

    # BEFORE UPDATE trigger
    op.execute(sa.text("""
        CREATE TRIGGER trg_board_audit_logs_no_update
            BEFORE UPDATE ON board_audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation();
    """))

    # BEFORE DELETE trigger
    op.execute(sa.text("""
        CREATE TRIGGER trg_board_audit_logs_no_delete
            BEFORE DELETE ON board_audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_mutation();
    """))


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_board_audit_logs_no_update ON board_audit_logs"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_board_audit_logs_no_delete ON board_audit_logs"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()"))

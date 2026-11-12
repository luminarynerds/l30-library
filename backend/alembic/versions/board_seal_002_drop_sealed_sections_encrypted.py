# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""drop dead board_minutes.sealed_sections_encrypted column

Revision ID: board_seal_002
Revises: unify_heads_003
Create Date: 2026-07-07

sealed_sections_encrypted was added in board_seal_001 for a per-section
executive-session redaction feature that was never built: grep confirms it
is never read or written anywhere in the app, and its "Fernet-encrypted
JSON" comment falsely implied protection that doesn't exist. Whole-document
is_sealed (checked in app/api/v1/board/public.py) is the intended and
sufficient protection (maintainer call, 2026-07-04 Fernet/PII audit finding C4).

Idempotent: uses IF EXISTS/IF NOT EXISTS because init_db.py auto-creates
tables from SQLAlchemy model metadata at container startup -- a fresh
install's board_minutes table never had this column (the model no longer
declares it), so DROP COLUMN without IF EXISTS would fail there.

NOTE: this migration needs a manual `alembic upgrade head` post-deploy on
already-running installs (standard L30 migration policy -- migrations don't
auto-run).
"""
from alembic import op


revision = "board_seal_002"
down_revision = "unify_heads_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE board_minutes DROP COLUMN IF EXISTS sealed_sections_encrypted"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE board_minutes ADD COLUMN IF NOT EXISTS sealed_sections_encrypted TEXT"
    )

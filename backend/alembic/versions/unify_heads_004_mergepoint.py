# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""mergepoint: unify board_seal_002 and hour_log_reject_audit_001 heads

Revision ID: unify_heads_004
Revises: board_seal_002, hour_log_reject_audit_001
Create Date: 2026-07-09
"""
from typing import Sequence, Union


revision = "unify_heads_004"
down_revision: Union[str, Sequence[str], None] = (
    "board_seal_002",
    "hour_log_reject_audit_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

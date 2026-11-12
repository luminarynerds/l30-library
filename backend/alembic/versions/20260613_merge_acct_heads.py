# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Merge divergent alembic heads.

Revision ID: merge_acct_heads_001
Revises: event_reg_user_id_001, lesson_preview_001
Create Date: 2026-06-13

No-op mergepoint joining two heads that developed in parallel:
  - event_reg_user_id_001 (events registration user_id FK, PR #1575)
  - lesson_preview_001 (free preview lessons, deploy bundle)
Both are already independently applied/applicable; this only reunifies the
revision tree to a single head. No schema changes.
"""
from typing import Sequence, Union

revision: str = "merge_acct_heads_001"
down_revision: Union[str, Sequence[str], None] = (
    "event_reg_user_id_001",
    "lesson_preview_001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

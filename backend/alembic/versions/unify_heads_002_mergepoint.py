# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""mergepoint: unify collection_memory_view_001 and pii_access_log_001 heads

Revision ID: unify_heads_002
Revises: collection_memory_view_001, pii_access_log_001
Create Date: 2026-05-17
"""
from typing import Sequence, Union


revision = "unify_heads_002"
down_revision: Union[str, Sequence[str], None] = (
    "collection_memory_view_001",
    "pii_access_log_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

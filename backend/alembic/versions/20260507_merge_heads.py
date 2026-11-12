# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""merge all heads into single lineage

Revision ID: merge_heads_20260507
Revises: checkin_exception_001, rooms_accom_buffers_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op


revision: str = "merge_heads_20260507"
down_revision: Union[str, Sequence[str], None] = ("checkin_exception_001", "rooms_accom_buffers_001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""merge computer_map and sushi_cred heads

Revision ID: 61c88bd60a72
Revises: computer_map_001, sushi_cred_001
Create Date: 2026-05-13 21:29:00.172556+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61c88bd60a72'
down_revision: Union[str, None] = ('computer_map_001', 'sushi_cred_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

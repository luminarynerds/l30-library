"""merge schema_sync_007 and dashboard_profile_001

Revision ID: merge_001
Revises: schema_sync_007, dashboard_profile_001
Create Date: 2026-05-10
"""
from typing import Sequence, Union

revision: str = "merge_001"
down_revision: tuple[str, ...] = ("schema_sync_007", "dashboard_profile_001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass

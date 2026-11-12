"""merge all heads into single lineage

Revision ID: f8509872ebab
Revises: board_term_tracking_001, drop_staff_role_001, ff652f229687, marc_macros_001, panic_alert_sound_pref_001, pii_encryption_tier2_001
Create Date: 2026-05-08 19:04:42.232427+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8509872ebab'
down_revision: Union[str, None] = ('board_term_tracking_001', 'drop_staff_role_001', 'ff652f229687', 'marc_macros_001', 'panic_alert_sound_pref_001', 'pii_encryption_tier2_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""merge 8 heads after 2026-05-20 PR sweep

Revision ID: mergepoint_20260520
Revises: discover_trending_001, event_waitlist_001, if_seed_001, impact_phase1_001, indie_seeded_001, library_admin_role_001, pii_access_log_002, ra_shelves_001
Create Date: 2026-05-20 17:00:00.000000+00:00

Collapses the 8 heads accumulated during the 2026-05-20 PR sweep into a
single lineage so subsequent migrations have one unambiguous parent.

See [[feedback_l30_alembic_multi_head_deploy]].
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "mergepoint_20260520"
down_revision: Union[str, None] = (
    "discover_trending_001",
    "event_waitlist_001",
    "if_seed_001",
    "impact_phase1_001",
    "indie_seeded_001",
    "library_admin_role_001",
    "pii_access_log_002",
    "ra_shelves_001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

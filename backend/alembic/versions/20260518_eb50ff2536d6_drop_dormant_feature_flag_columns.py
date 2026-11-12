"""drop dormant feature flag columns

Revision ID: eb50ff2536d6
Revises: d99fa3f4a50d
Create Date: 2026-05-18

Drops two organization_features boolean columns that were togglable in the
admin UI but enforced nothing:

* reading_challenges_enabled — never referenced; reading challenges live
  under reading_programs.py which is already gated by
  reading_programs_enabled at the router-registry level.
* shelf_recommendations_enabled — no consumer anywhere in backend or
  frontend.

Removing eliminates the 'I disabled it but the feature still works'
footgun in the admin feature-flags page.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'eb50ff2536d6'
down_revision: Union[str, None] = 'd99fa3f4a50d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('organization_features', 'reading_challenges_enabled')
    op.drop_column('organization_features', 'shelf_recommendations_enabled')


def downgrade() -> None:
    op.add_column(
        'organization_features',
        sa.Column(
            'shelf_recommendations_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'organization_features',
        sa.Column(
            'reading_challenges_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )

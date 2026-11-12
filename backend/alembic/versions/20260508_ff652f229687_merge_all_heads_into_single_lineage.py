"""merge all heads into single lineage

Revision ID: ff652f229687
Revises: dbsub_session_ttl_001, ai_minor_gating_001, archival_collections_001, collection_archival_001, enum_cleanup_001, local_authorities_001, sidebar_flags_001, vote_immutability_001, authority_terms_001, api_keys_001, engagement_002
Create Date: 2026-05-08 16:02:15.889150+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff652f229687'
down_revision: Union[str, None] = ('dbsub_session_ttl_001', 'ai_minor_gating_001', 'archival_collections_001', 'collection_archival_001', 'enum_cleanup_001', 'local_authorities_001', 'sidebar_flags_001', 'vote_immutability_001', 'authority_terms_001', 'api_keys_001', 'engagement_002')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

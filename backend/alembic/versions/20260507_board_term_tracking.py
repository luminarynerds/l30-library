"""Add term tracking columns to board_members

Revision ID: board_term_tracking_001
Revises: dbsub_session_ttl_001, ai_minor_gating_001, collection_archival_001, enum_cleanup_001, local_authorities_001, multipart_sets_001, vote_immutability_001, authority_terms_001, api_keys_001, engagement_002
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "board_term_tracking_001"
down_revision = (
    "dbsub_session_ttl_001",
    "ai_minor_gating_001",
    "collection_archival_001",
    "enum_cleanup_001",
    "local_authorities_001",
    "multipart_sets_001",
    "vote_immutability_001",
    "authority_terms_001",
    "api_keys_001",
    "engagement_002",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("board_members", sa.Column("term_number", sa.Integer(), nullable=True))
    op.add_column("board_members", sa.Column("max_consecutive_terms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("board_members", "max_consecutive_terms")
    op.drop_column("board_members", "term_number")

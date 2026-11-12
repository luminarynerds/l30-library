"""create legal eligibility thresholds

Revision ID: legal_002
Revises: legal_001
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "legal_002"
down_revision: Union[str, None] = "legal_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legal_eligibility_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("legal_service_providers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("household_size", sa.Integer(), nullable=False),
        sa.Column("income_limit", sa.Integer(), nullable=False),
        sa.Column("percentage_of_fpl", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expires_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("legal_eligibility_thresholds")

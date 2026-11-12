"""add catalog_state_events table

Revision ID: catalog_state_events_001
Revises: makerspace_tools_001
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "catalog_state_events_001"
down_revision: Union[str, None] = "makerspace_tools_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Reference the existing itemstatus enum without creating it.
itemstatus = ENUM(
    "available", "checked_out", "on_hold", "in_transit", "on_order",
    "in_processing", "missing", "lost", "damaged", "withdrawn",
    "reference", "restricted", "lost_by_patron", "lost_in_transit",
    "claims_returned", "damaged_repairable", "damaged_withdrawn", "in_mending",
    name="itemstatus", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "catalog_state_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("catalog_item_id", sa.Integer(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("old_status", itemstatus, nullable=True),
        sa.Column("new_status", itemstatus, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_catalog_state_events_item_created",
        "catalog_state_events",
        ["catalog_item_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_state_events_item_created", table_name="catalog_state_events")
    op.drop_table("catalog_state_events")

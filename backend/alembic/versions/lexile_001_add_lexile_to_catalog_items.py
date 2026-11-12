"""Add lexile_measure and lexile_number to catalog_items

Revision ID: lexile_001
Revises: widen_version_num_001
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = "lexile_001"
down_revision = "widen_version_num_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalog_items", sa.Column("lexile_measure", sa.String(length=10), nullable=True))
    op.add_column("catalog_items", sa.Column("lexile_number", sa.Integer(), nullable=True))
    op.create_index(
        "ix_catalog_items_lexile_number",
        "catalog_items",
        ["lexile_number"],
    )
    op.create_check_constraint(
        "ck_catalog_item_lexile_range",
        "catalog_items",
        "lexile_number IS NULL OR (lexile_number >= -400 AND lexile_number <= 2000)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_catalog_item_lexile_range", "catalog_items", type_="check")
    op.drop_index("ix_catalog_items_lexile_number", table_name="catalog_items")
    op.drop_column("catalog_items", "lexile_number")
    op.drop_column("catalog_items", "lexile_measure")

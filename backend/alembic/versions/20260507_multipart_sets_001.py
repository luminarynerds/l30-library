# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""multi-volume / multi-part set support

Adds:
  - multipart_sets table for grouping volumes of a multi-volume work,
    monographic series, or numbered set
  - catalog_items.multipart_set_id, volume_number, volume_label,
    sequence_in_set
  - item_copies.volume_override for copies that diverge from the parent
    item's volume designation (omnibus bindings, missing volumes, etc.)

Revision ID: multipart_sets_001
Revises: sip2_created_at_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "multipart_sets_001"
down_revision: Union[str, None] = "sip2_created_at_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MULTIPART_SET_TYPE = postgresql.ENUM(
    "multivolume",
    "monographic_series",
    "numbered_set",
    name="multipartsettype",
    create_type=False,
)


def upgrade() -> None:
    MULTIPART_SET_TYPE.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "multipart_sets",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column(
            "set_type",
            MULTIPART_SET_TYPE,
            nullable=False,
            server_default="multivolume",
        ),
        sa.Column("total_parts", sa.Integer(), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("editor", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "total_parts IS NULL OR total_parts > 0",
            name="ck_multipart_set_total_parts_positive",
        ),
    )
    op.create_index(
        "ix_multipart_sets_title", "multipart_sets", ["title"], unique=False
    )
    op.create_index(
        "ix_multipart_sets_set_type", "multipart_sets", ["set_type"], unique=False
    )

    op.add_column(
        "catalog_items",
        sa.Column("multipart_set_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "catalog_items",
        sa.Column("volume_number", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "catalog_items",
        sa.Column("volume_label", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "catalog_items",
        sa.Column("sequence_in_set", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_catalog_items_multipart_set_id",
        "catalog_items",
        "multipart_sets",
        ["multipart_set_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_catalog_items_multipart_set_id",
        "catalog_items",
        ["multipart_set_id"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_items_sequence_in_set",
        "catalog_items",
        ["sequence_in_set"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_items_multipart_sequence",
        "catalog_items",
        ["multipart_set_id", "sequence_in_set"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_catalog_item_sequence_in_set_positive",
        "catalog_items",
        "sequence_in_set IS NULL OR sequence_in_set > 0",
    )

    op.add_column(
        "item_copies",
        sa.Column("volume_override", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("item_copies", "volume_override")

    op.drop_constraint(
        "ck_catalog_item_sequence_in_set_positive",
        "catalog_items",
        type_="check",
    )
    op.drop_index("ix_catalog_items_multipart_sequence", table_name="catalog_items")
    op.drop_index("ix_catalog_items_sequence_in_set", table_name="catalog_items")
    op.drop_index("ix_catalog_items_multipart_set_id", table_name="catalog_items")
    op.drop_constraint(
        "fk_catalog_items_multipart_set_id",
        "catalog_items",
        type_="foreignkey",
    )
    op.drop_column("catalog_items", "sequence_in_set")
    op.drop_column("catalog_items", "volume_label")
    op.drop_column("catalog_items", "volume_number")
    op.drop_column("catalog_items", "multipart_set_id")

    op.drop_index("ix_multipart_sets_set_type", table_name="multipart_sets")
    op.drop_index("ix_multipart_sets_title", table_name="multipart_sets")
    op.drop_table("multipart_sets")

    MULTIPART_SET_TYPE.drop(op.get_bind(), checkfirst=True)

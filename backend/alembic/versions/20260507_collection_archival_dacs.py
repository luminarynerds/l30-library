# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""extend collection with DACS archival description and add collection_items

Revision ID: collection_archival_001
Revises: merge_heads_20260507
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "collection_archival_001"
down_revision: Union[str, None] = "merge_heads_20260507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARCHIVAL_LEVEL_VALUES = (
    "collection",
    "fonds",
    "record_group",
    "subgroup",
    "series",
    "subseries",
    "file",
    "item",
)


def upgrade() -> None:
    archival_level = postgresql.ENUM(
        *ARCHIVAL_LEVEL_VALUES, name="archivallevel", create_type=False
    )
    archival_level.create(op.get_bind(), checkfirst=True)

    # --- Hierarchy ---
    op.add_column(
        "collection",
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("collection.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "collection",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "collection",
        sa.Column(
            "level",
            archival_level,
            nullable=True,
        ),
    )
    op.create_index("ix_collection_parent_id", "collection", ["parent_id"])
    op.create_index("ix_collection_level", "collection", ["level"])
    op.create_index(
        "ix_collection_parent_position", "collection", ["parent_id", "position"]
    )

    # --- DACS Identity & Context ---
    op.add_column(
        "collection", sa.Column("reference_code", sa.String(length=100), nullable=True)
    )
    op.add_column("collection", sa.Column("title", sa.String(length=500), nullable=True))
    op.add_column(
        "collection", sa.Column("date_creation", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "collection",
        sa.Column("date_accumulation", sa.String(length=255), nullable=True),
    )
    op.add_column("collection", sa.Column("extent", sa.String(length=255), nullable=True))
    op.add_column(
        "collection", sa.Column("creator", sa.String(length=500), nullable=True)
    )
    op.create_index(
        "ix_collection_reference_code",
        "collection",
        ["reference_code"],
        unique=True,
    )
    op.create_index("ix_collection_creator", "collection", ["creator"])

    # --- DACS Administrative / Biographical / Custodial ---
    op.add_column("collection", sa.Column("biographical_history", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("archival_history", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("acquisition_source", sa.Text(), nullable=True))

    # --- DACS Content & Structure ---
    op.add_column("collection", sa.Column("scope_content", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("appraisal", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("accruals", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("arrangement", sa.Text(), nullable=True))

    # --- DACS Access & Use ---
    op.add_column("collection", sa.Column("access_conditions", sa.Text(), nullable=True))
    op.add_column(
        "collection", sa.Column("reproduction_conditions", sa.Text(), nullable=True)
    )
    op.add_column(
        "collection", sa.Column("languages", sa.String(length=255), nullable=True)
    )
    op.add_column("collection", sa.Column("physical_access", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("technical_access", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("finding_aids", sa.Text(), nullable=True))

    # --- DACS Allied Materials ---
    op.add_column("collection", sa.Column("originals_location", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("copies_location", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("related_materials", sa.Text(), nullable=True))
    op.add_column("collection", sa.Column("publication_note", sa.Text(), nullable=True))

    # --- DACS Notes ---
    op.add_column("collection", sa.Column("notes", sa.Text(), nullable=True))

    # --- DACS Description Control ---
    op.add_column(
        "collection",
        sa.Column("description_rules", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "collection",
        sa.Column("description_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "collection", sa.Column("described_by", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "collection",
        sa.Column("described_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Junction table ---
    op.create_table(
        "collection_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collection.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "catalog_item_id",
            sa.Integer(),
            sa.ForeignKey("catalog_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("component_label", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "collection_id",
            "catalog_item_id",
            name="uq_collection_items_collection_catalog",
        ),
    )
    op.create_index(
        "ix_collection_items_collection_id", "collection_items", ["collection_id"]
    )
    op.create_index(
        "ix_collection_items_catalog_item_id",
        "collection_items",
        ["catalog_item_id"],
    )
    op.create_index(
        "ix_collection_items_collection_position",
        "collection_items",
        ["collection_id", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_collection_items_collection_position", table_name="collection_items")
    op.drop_index("ix_collection_items_catalog_item_id", table_name="collection_items")
    op.drop_index("ix_collection_items_collection_id", table_name="collection_items")
    op.drop_table("collection_items")

    for col in (
        "described_at",
        "described_by",
        "description_status",
        "description_rules",
        "notes",
        "publication_note",
        "related_materials",
        "copies_location",
        "originals_location",
        "finding_aids",
        "technical_access",
        "physical_access",
        "languages",
        "reproduction_conditions",
        "access_conditions",
        "arrangement",
        "accruals",
        "appraisal",
        "scope_content",
        "acquisition_source",
        "archival_history",
        "biographical_history",
    ):
        op.drop_column("collection", col)

    op.drop_index("ix_collection_creator", table_name="collection")
    op.drop_index("ix_collection_reference_code", table_name="collection")
    for col in ("creator", "extent", "date_accumulation", "date_creation", "title", "reference_code"):
        op.drop_column("collection", col)

    op.drop_index("ix_collection_parent_position", table_name="collection")
    op.drop_index("ix_collection_level", table_name="collection")
    op.drop_index("ix_collection_parent_id", table_name="collection")
    op.drop_column("collection", "level")
    op.drop_column("collection", "position")
    op.drop_column("collection", "parent_id")

    archival_level = postgresql.ENUM(*ARCHIVAL_LEVEL_VALUES, name="archivallevel")
    archival_level.drop(op.get_bind(), checkfirst=True)

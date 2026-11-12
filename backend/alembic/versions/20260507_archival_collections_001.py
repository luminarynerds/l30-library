# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""archival collection-level cataloging

Adds:
  - archival_collections: top-level finding-aid records (DACS-aligned)
  - archival_components: hierarchical components (series, subseries, file, item)
  - findingaidstatus and archivallevel postgres enums

Revision ID: archival_collections_001
Revises: multipart_sets_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "archival_collections_001"
down_revision: Union[str, None] = "multipart_sets_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FINDING_AID_STATUS = postgresql.ENUM(
    "draft", "in_progress", "published", "revised",
    name="findingaidstatus",
    create_type=False,
)

ARCHIVAL_LEVEL = postgresql.ENUM(
    "collection", "fonds", "recordgrp", "subgrp",
    "series", "subseries", "file", "item", "otherlevel",
    name="archivallevel",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    FINDING_AID_STATUS.create(bind, checkfirst=True)
    ARCHIVAL_LEVEL.create(bind, checkfirst=True)

    op.create_table(
        "archival_collections",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("identifier", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("creator", sa.String(length=500), nullable=True),
        sa.Column("repository", sa.String(length=255), nullable=True),
        sa.Column("date_inclusive_start", sa.Date(), nullable=True),
        sa.Column("date_inclusive_end", sa.Date(), nullable=True),
        sa.Column("date_inclusive_text", sa.String(length=255), nullable=True),
        sa.Column("date_bulk_start", sa.Date(), nullable=True),
        sa.Column("date_bulk_end", sa.Date(), nullable=True),
        sa.Column("extent", sa.String(length=255), nullable=True),
        sa.Column("languages", sa.String(length=255), nullable=True),
        sa.Column("scope_and_content", sa.Text(), nullable=True),
        sa.Column("biographical_historical", sa.Text(), nullable=True),
        sa.Column("arrangement", sa.Text(), nullable=True),
        sa.Column("processing_info", sa.Text(), nullable=True),
        sa.Column("acquisition_info", sa.Text(), nullable=True),
        sa.Column("custodial_history", sa.Text(), nullable=True),
        sa.Column("access_restrictions", sa.Text(), nullable=True),
        sa.Column("use_restrictions", sa.Text(), nullable=True),
        sa.Column("preferred_citation", sa.Text(), nullable=True),
        sa.Column("related_materials", sa.Text(), nullable=True),
        sa.Column("finding_aid_url", sa.String(length=500), nullable=True),
        sa.Column(
            "finding_aid_status",
            FINDING_AID_STATUS,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.UniqueConstraint("identifier", name="uq_archival_collections_identifier"),
        sa.CheckConstraint(
            "date_inclusive_end IS NULL OR date_inclusive_start IS NULL "
            "OR date_inclusive_end >= date_inclusive_start",
            name="ck_archival_collection_inclusive_date_order",
        ),
        sa.CheckConstraint(
            "date_bulk_end IS NULL OR date_bulk_start IS NULL "
            "OR date_bulk_end >= date_bulk_start",
            name="ck_archival_collection_bulk_date_order",
        ),
    )
    op.create_index(
        "ix_archival_collections_identifier",
        "archival_collections", ["identifier"], unique=True,
    )
    op.create_index(
        "ix_archival_collections_title",
        "archival_collections", ["title"], unique=False,
    )
    op.create_index(
        "ix_archival_collections_creator",
        "archival_collections", ["creator"], unique=False,
    )
    op.create_index(
        "ix_archival_collections_finding_aid_status",
        "archival_collections", ["finding_aid_status"], unique=False,
    )
    op.create_index(
        "ix_archival_collections_created_by_id",
        "archival_collections", ["created_by_id"], unique=False,
    )

    op.create_table(
        "archival_components",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "collection_id", sa.Integer(),
            sa.ForeignKey("archival_collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id", sa.Integer(),
            sa.ForeignKey("archival_components.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "level",
            ARCHIVAL_LEVEL,
            nullable=False,
            server_default="series",
        ),
        sa.Column("identifier", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("date_inclusive_start", sa.Date(), nullable=True),
        sa.Column("date_inclusive_end", sa.Date(), nullable=True),
        sa.Column("date_inclusive_text", sa.String(length=255), nullable=True),
        sa.Column("extent", sa.String(length=255), nullable=True),
        sa.Column("scope_and_content", sa.Text(), nullable=True),
        sa.Column("arrangement", sa.Text(), nullable=True),
        sa.Column("access_restrictions", sa.Text(), nullable=True),
        sa.Column("container_summary", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "catalog_item_id", sa.Integer(),
            sa.ForeignKey("catalog_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.CheckConstraint(
            "date_inclusive_end IS NULL OR date_inclusive_start IS NULL "
            "OR date_inclusive_end >= date_inclusive_start",
            name="ck_archival_component_inclusive_date_order",
        ),
    )
    op.create_index(
        "ix_archival_components_collection_id",
        "archival_components", ["collection_id"], unique=False,
    )
    op.create_index(
        "ix_archival_components_parent_id",
        "archival_components", ["parent_id"], unique=False,
    )
    op.create_index(
        "ix_archival_components_level",
        "archival_components", ["level"], unique=False,
    )
    op.create_index(
        "ix_archival_components_identifier",
        "archival_components", ["identifier"], unique=False,
    )
    op.create_index(
        "ix_archival_components_catalog_item_id",
        "archival_components", ["catalog_item_id"], unique=False,
    )
    op.create_index(
        "ix_archival_components_collection_parent",
        "archival_components", ["collection_id", "parent_id"], unique=False,
    )
    op.create_index(
        "ix_archival_components_collection_sort",
        "archival_components", ["collection_id", "sort_order"], unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_archival_components_collection_sort", table_name="archival_components",
    )
    op.drop_index(
        "ix_archival_components_collection_parent", table_name="archival_components",
    )
    op.drop_index(
        "ix_archival_components_catalog_item_id", table_name="archival_components",
    )
    op.drop_index(
        "ix_archival_components_identifier", table_name="archival_components",
    )
    op.drop_index("ix_archival_components_level", table_name="archival_components")
    op.drop_index("ix_archival_components_parent_id", table_name="archival_components")
    op.drop_index("ix_archival_components_collection_id", table_name="archival_components")
    op.drop_table("archival_components")

    op.drop_index(
        "ix_archival_collections_created_by_id", table_name="archival_collections",
    )
    op.drop_index(
        "ix_archival_collections_finding_aid_status",
        table_name="archival_collections",
    )
    op.drop_index("ix_archival_collections_creator", table_name="archival_collections")
    op.drop_index("ix_archival_collections_title", table_name="archival_collections")
    op.drop_index(
        "ix_archival_collections_identifier", table_name="archival_collections",
    )
    op.drop_table("archival_collections")

    bind = op.get_bind()
    ARCHIVAL_LEVEL.drop(bind, checkfirst=True)
    FINDING_AID_STATUS.drop(bind, checkfirst=True)

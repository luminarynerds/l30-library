# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create home_hero_picks, home_shelves, home_page_config + catalog_items.staff_pick/featured_at

Revision ID: home_page_001
Revises: saved_searches_002
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "home_page_001"
down_revision: Union[str, Sequence[str], None] = "saved_searches_002"
branch_labels = None
depends_on = None


# Lowercase enum values per [[feedback_l30_enum_case]].
HOME_SHELF_QUERY_KINDS = (
    "new_arrivals",
    "staff_picks",
    "subject",
    "format",
    "circulation_top",
    "manual_list",
)


def upgrade() -> None:
    # --- catalog_items new columns (additive, nullable/defaulted) ---
    op.add_column(
        "catalog_items",
        sa.Column("staff_pick", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "catalog_items",
        sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_catalog_items_staff_pick",
        "catalog_items",
        ["staff_pick"],
        postgresql_where=sa.text("staff_pick = true"),
    )
    op.create_index("ix_catalog_items_featured_at", "catalog_items", ["featured_at"])

    # --- home_shelves query_kind enum ---
    home_shelf_query_kind = sa.Enum(
        *HOME_SHELF_QUERY_KINDS,
        name="homeshelfquerykind",
        create_type=True,
    )
    home_shelf_query_kind.create(op.get_bind(), checkfirst=True)

    # --- home_hero_picks ---
    op.create_table(
        "home_hero_picks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "item_id",
            sa.Integer(),
            sa.ForeignKey("catalog_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("annotation_md", sa.Text(), nullable=False),
        sa.Column("cta_label", sa.String(120), nullable=False),
        sa.Column("cta_href", sa.String(500), nullable=True),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_home_hero_picks_active_from", "home_hero_picks", ["active_from"]
    )

    # --- home_shelves ---
    op.create_table(
        "home_shelves",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("heading", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "query_kind",
            sa.Enum(
                *HOME_SHELF_QUERY_KINDS,
                name="homeshelfquerykind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "query_params",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("max_items", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("view_all_href", sa.String(500), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_home_shelves_sort_active",
        "home_shelves",
        ["sort_order", "is_active"],
    )

    # --- home_page_config (singleton) ---
    op.create_table(
        "home_page_config",
        sa.Column("id", sa.Integer(), primary_key=True, server_default="1"),
        sa.Column("eyebrow", sa.String(280), nullable=True),
        sa.Column(
            "hero_visible", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("picks_link_label", sa.String(120), nullable=True),
        sa.Column("picks_link_href", sa.String(500), nullable=True),
        sa.Column("empty_state_message", sa.Text(), nullable=True),
        sa.Column(
            "updated_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="ck_home_page_config_singleton"),
    )


def downgrade() -> None:
    op.drop_table("home_page_config")
    op.drop_index("ix_home_shelves_sort_active", table_name="home_shelves")
    op.drop_table("home_shelves")
    op.drop_index("ix_home_hero_picks_active_from", table_name="home_hero_picks")
    op.drop_table("home_hero_picks")
    sa.Enum(name="homeshelfquerykind").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_catalog_items_featured_at", table_name="catalog_items")
    op.drop_index("ix_catalog_items_staff_pick", table_name="catalog_items")
    op.drop_column("catalog_items", "featured_at")
    op.drop_column("catalog_items", "staff_pick")

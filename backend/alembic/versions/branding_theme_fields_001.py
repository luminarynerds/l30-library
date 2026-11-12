# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add theme fields (logo, fonts, palette, nav style) to library_branding.

Revision ID: branding_theme_fields_001
Revises: drop_title_active_idx_001
Create Date: 2026-07-05

Adds seven nullable columns to library_branding (the singleton settings
table) so a theme can carry a logo, display/body fonts, a fuller palette,
and a nav-style switch. All default to empty string / "default" so existing
rows are unaffected and unset tenants keep today's look.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "branding_theme_fields_001"
down_revision: Union[str, Sequence[str], None] = "drop_title_active_idx_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "library_branding",
        sa.Column("logo_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("display_font", sa.String(120), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("body_font", sa.String(120), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("secondary_color", sa.String(7), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("surface_color", sa.String(7), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("ink_color", sa.String(7), nullable=True),
    )
    op.add_column(
        "library_branding",
        sa.Column("nav_style", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("library_branding", "nav_style")
    op.drop_column("library_branding", "ink_color")
    op.drop_column("library_branding", "surface_color")
    op.drop_column("library_branding", "secondary_color")
    op.drop_column("library_branding", "body_font")
    op.drop_column("library_branding", "display_font")
    op.drop_column("library_branding", "logo_url")

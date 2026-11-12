# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add hero_image_url to library_branding.

Revision ID: branding_hero_image_002
Revises: branding_theme_fields_001
Create Date: 2026-07-05

Adds a single nullable column so a tenant can set a hero background image
(e.g. a photo of their building). Defaults to empty -> unset tenants keep the
plain editorial hero, unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "branding_hero_image_002"
down_revision: Union[str, Sequence[str], None] = "branding_theme_fields_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "library_branding",
        sa.Column("hero_image_url", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("library_branding", "hero_image_url")

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add about_story to library_branding.

Revision ID: branding_about_story_003
Revises: branding_hero_image_002
Create Date: 2026-07-06

One nullable JSON column holding the About page's "Our Story" timeline
({"timeline": [{"year", "title", "description"}]}). Unset tenants keep the
stock i18n timeline, unaffected. Same per-tenant-content pattern as
donate_config.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "branding_about_story_003"
down_revision: Union[str, Sequence[str], None] = "branding_hero_image_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "library_branding",
        sa.Column("about_story", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("library_branding", "about_story")

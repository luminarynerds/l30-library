# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""backfill tech_quick_links.section_icon with kebab-case lucide names

Existing rows seeded before the section_icon column was populated have
section_icon = NULL, which silently falls back to a generic ExternalLink
glyph in ExternalResourcesSection.tsx. Backfill the four known sections
so prod patrons see the intended icons immediately, without having to
re-run the seeder.

Idempotent: each UPDATE is gated on section_icon IS NULL OR section_icon = ''
so re-running this migration on a partially-populated DB is safe.

Revision ID: tech_quick_links_seed_icons_002
Revises: tech_facilities_001
Create Date: 2026-05-22
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text as sa_text

revision: str = "tech_quick_links_seed_icons_002"
down_revision: Union[str, None] = "tech_facilities_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (section_title, kebab-case lucide icon name)
SECTION_ICON_BACKFILL = [
    ("Internet & WiFi", "wifi"),
    ("Devices", "laptop"),
    ("Learning", "book-open"),
    ("Printing & Scanning", "printer"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for section_title, icon in SECTION_ICON_BACKFILL:
        bind.execute(
            sa_text(
                "UPDATE tech_quick_links SET section_icon = :icon "
                "WHERE section_title = :title "
                "AND (section_icon IS NULL OR section_icon = '')"
            ),
            {"icon": icon, "title": section_title},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for section_title, icon in SECTION_ICON_BACKFILL:
        bind.execute(
            sa_text(
                "UPDATE tech_quick_links SET section_icon = NULL "
                "WHERE section_title = :title AND section_icon = :icon"
            ),
            {"icon": icon, "title": section_title},
        )

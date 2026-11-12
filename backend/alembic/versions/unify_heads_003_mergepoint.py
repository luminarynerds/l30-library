# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""mergepoint: unify branding_about_story_003 and content_translations_001 heads

Revision ID: unify_heads_003
Revises: branding_about_story_003, content_translations_001
Create Date: 2026-07-07
"""
from typing import Sequence, Union


revision = "unify_heads_003"
down_revision: Union[str, Sequence[str], None] = (
    "branding_about_story_003",
    "content_translations_001",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

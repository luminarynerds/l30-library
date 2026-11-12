"""Add library_branding.donate_config (structured donate-page content)

Revision ID: donate_config_001
Revises: series_position_001
Create Date: 2026-06-11

Moves the donate page's library-specific content (giving tiers, impact areas,
monthly amounts, ways-to-give cards, intro/claims, testimonials, tax note) out
of the React component and into per-library config. The content now lives in
this JSON column on the singleton library_branding row and is served via
GET /branding; a fresh install with no row (or an empty column) ships no
donate content and the page hides its configurable sections.

Idempotent ALTER pattern (see series_position_001): L30's init_db.py
auto-creates tables from the SQLAlchemy models at startup, so the column may
already exist by the time alembic runs. ADD COLUMN IF NOT EXISTS makes re-runs
safe. Column-only -- no tenant content is seeded here; demo content is applied
to the demo's library_branding row as a separate data step.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "donate_config_001"
down_revision: Union[str, None] = "series_position_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE library_branding "
        "ADD COLUMN IF NOT EXISTS donate_config JSON"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE library_branding DROP COLUMN IF EXISTS donate_config")

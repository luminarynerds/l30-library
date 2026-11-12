# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create library_branding table

Revision ID: branding_001
Revises: rpt_sched_001
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "branding_001"
down_revision = "rpt_sched_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "library_branding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("library_name", sa.String(255), nullable=False, server_default="My Library"),
        sa.Column("library_short_name", sa.String(50), server_default=""),
        sa.Column("domain", sa.String(255), server_default=""),
        sa.Column("contact_email", sa.String(255), server_default=""),
        sa.Column("privacy_email", sa.String(255), server_default=""),
        sa.Column("indie_email", sa.String(255), server_default=""),
        sa.Column("giving_email", sa.String(255), server_default=""),
        sa.Column("phone", sa.String(50), server_default=""),
        sa.Column("address_line1", sa.String(255), server_default=""),
        sa.Column("address_line2", sa.String(255), server_default=""),
        sa.Column("primary_color", sa.String(7), server_default="#E89B44"),
        sa.Column("accent_color", sa.String(7), server_default="#8B5E5E"),
        sa.Column("card_prefix", sa.String(10), server_default="LIB"),
        sa.Column("hero_title", sa.String(500), server_default=""),
        sa.Column("hero_subtitle", sa.String(500), server_default="You belong here."),
        sa.Column("tagline", sa.String(255), server_default=""),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="singleton_branding"),
    )
    # Seed the singleton row so GET /branding works immediately.
    op.execute(
        "INSERT INTO library_branding (id, library_name) VALUES (1, 'My Library')"
    )


def downgrade() -> None:
    op.drop_table("library_branding")

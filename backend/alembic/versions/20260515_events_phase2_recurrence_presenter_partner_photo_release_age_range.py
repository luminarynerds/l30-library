# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""events phase 2: recurrence, presenters, partner organizations, photo release, age range

Adds:
  - Table `partner_organizations` (id, name unique, slug unique, website,
    contact_email, contact_phone, notes, is_active, created_at, updated_at).
    Indexes: ix_event_partner_organizations_is_active on is_active.
  - events.recurrence_rule TEXT NULL — RFC 5545 RRULE.
  - events.parent_event_id INTEGER NULL — self-FK ON DELETE CASCADE.
    Index: ix_events_parent_event_id.
  - events.presenters JSONB NULL — array of {name, bio?, fee?, partner_organization_id?}.
  - events.partner_organization_id INTEGER NULL — FK to event_partner_organizations.id ON DELETE SET NULL.
  - events.photos_will_be_taken BOOLEAN NOT NULL DEFAULT false.
  - events.min_age, events.max_age INTEGER NULL.
  - events.caregiver_required BOOLEAN NOT NULL DEFAULT false.
  - CHECK constraint ck_events_age_range_valid.
  - event_registrations.photo_release_granted BOOLEAN NULL (three-valued).

Revision ID: events_phase2_001
Revises: 7cfe9045127a
Create Date: 2026-05-15 18:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "events_phase2_001"
down_revision: Union[str, None] = "event_reminder_sent_at_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. partner_organizations table
    #
    # Uses CREATE TABLE IF NOT EXISTS because init_db.py
    # (scripts/init_schema_async_raw_sql.py) auto-creates new tables from
    # SQLAlchemy models at backend startup. By the time alembic runs, the
    # table may already exist. Plain op.create_table() would then raise
    # DuplicateTableError. See backend/scripts/check_alembic_idempotent.py.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS event_partner_organizations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            slug VARCHAR(200) NOT NULL,
            website VARCHAR(500),
            contact_email VARCHAR(255),
            contact_phone VARCHAR(50),
            notes TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_event_partner_organizations_name UNIQUE (name),
            CONSTRAINT uq_event_partner_organizations_slug UNIQUE (slug)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_event_partner_organizations_is_active "
        "ON event_partner_organizations(is_active)"
    )

    # ------------------------------------------------------------------
    # 2. events: new columns
    # ------------------------------------------------------------------
    op.add_column("events", sa.Column("recurrence_rule", sa.Text(), nullable=True))
    op.add_column(
        "events", sa.Column("parent_event_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_events_parent_event_id_events",
        "events",
        "events",
        ["parent_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_events_parent_event_id", "events", ["parent_event_id"]
    )

    op.add_column(
        "events",
        sa.Column("presenters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.add_column(
        "events", sa.Column("partner_organization_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_events_partner_organization_id_event_partner_organizations",
        "events",
        "event_partner_organizations",
        ["partner_organization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "events",
        sa.Column(
            "photos_will_be_taken",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.add_column("events", sa.Column("min_age", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("max_age", sa.Integer(), nullable=True))
    op.add_column(
        "events",
        sa.Column(
            "caregiver_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # CHECK constraint mirrors the DB-side enforcement of the schema validator.
    op.create_check_constraint(
        "ck_events_age_range_valid",
        "events",
        "min_age IS NULL OR max_age IS NULL OR min_age <= max_age",
    )

    # ------------------------------------------------------------------
    # 3. event_registrations: photo_release_granted (three-valued)
    # ------------------------------------------------------------------
    op.add_column(
        "event_registrations",
        sa.Column("photo_release_granted", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_registrations", "photo_release_granted")

    op.drop_constraint("ck_events_age_range_valid", "events", type_="check")
    op.drop_column("events", "caregiver_required")
    op.drop_column("events", "max_age")
    op.drop_column("events", "min_age")
    op.drop_column("events", "photos_will_be_taken")

    op.drop_constraint(
        "fk_events_partner_organization_id_event_partner_organizations",
        "events",
        type_="foreignkey",
    )
    op.drop_column("events", "partner_organization_id")

    op.drop_column("events", "presenters")

    op.drop_index("ix_events_parent_event_id", table_name="events")
    op.drop_constraint(
        "fk_events_parent_event_id_events", "events", type_="foreignkey"
    )
    op.drop_column("events", "parent_event_id")
    op.drop_column("events", "recurrence_rule")

    op.drop_index(
        "ix_event_partner_organizations_is_active", table_name="event_partner_organizations"
    )
    op.drop_table("event_partner_organizations")

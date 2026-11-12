# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""rename event_partner_organizations to event_program_partners

Clean-break rename to remove the name collision with
immigrant_services.partner_organizations (a wholly separate concept).

Operations:
  - Rename table event_partner_organizations -> event_program_partners.
  - Rename events.partner_organization_id -> events.program_partner_id.
  - Rename unique constraints uq_event_partner_organizations_* -> uq_event_program_partners_*.
  - Rename index ix_event_partner_organizations_is_active -> ix_event_program_partners_is_active.
  - Rename FK fk_events_partner_organization_id_event_partner_organizations
    -> fk_events_program_partner_id_event_program_partners.

Revision ID: rename_event_program_partners_001
Revises: attendance_preregistered_001
Create Date: 2026-05-15 23:50:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "rename_event_program_partners_001"
down_revision: Union[str, None] = "attendance_preregistered_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename the table.
    op.rename_table("event_partner_organizations", "event_program_partners")

    # 2. Rename the FK column on events.
    op.alter_column(
        "events",
        "partner_organization_id",
        new_column_name="program_partner_id",
    )

    # 3. Rename explicitly-named unique constraints.
    op.execute(
        "ALTER TABLE event_program_partners "
        "RENAME CONSTRAINT uq_event_partner_organizations_name "
        "TO uq_event_program_partners_name"
    )
    op.execute(
        "ALTER TABLE event_program_partners "
        "RENAME CONSTRAINT uq_event_partner_organizations_slug "
        "TO uq_event_program_partners_slug"
    )

    # 4. Rename the FK on events.program_partner_id.
    op.execute(
        "ALTER TABLE events "
        "RENAME CONSTRAINT fk_events_partner_organization_id_event_partner_organizations "
        "TO fk_events_program_partner_id_event_program_partners"
    )

    # 5. Rename the is_active index.
    op.execute(
        "ALTER INDEX ix_event_partner_organizations_is_active "
        "RENAME TO ix_event_program_partners_is_active"
    )


def downgrade() -> None:
    # Reverse of upgrade() in reverse order.
    op.execute(
        "ALTER INDEX ix_event_program_partners_is_active "
        "RENAME TO ix_event_partner_organizations_is_active"
    )
    op.execute(
        "ALTER TABLE events "
        "RENAME CONSTRAINT fk_events_program_partner_id_event_program_partners "
        "TO fk_events_partner_organization_id_event_partner_organizations"
    )
    op.execute(
        "ALTER TABLE event_program_partners "
        "RENAME CONSTRAINT uq_event_program_partners_slug "
        "TO uq_event_partner_organizations_slug"
    )
    op.execute(
        "ALTER TABLE event_program_partners "
        "RENAME CONSTRAINT uq_event_program_partners_name "
        "TO uq_event_partner_organizations_name"
    )
    op.alter_column(
        "events",
        "program_partner_id",
        new_column_name="partner_organization_id",
    )
    op.rename_table("event_program_partners", "event_partner_organizations")

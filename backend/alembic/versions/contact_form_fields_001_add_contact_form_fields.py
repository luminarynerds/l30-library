"""add contact form fields to support_tickets

Revision ID: contact_form_fields_001
Revises: staff_support_triage_001
Create Date: 2026-05-18

Adds the patron-contact-page fields on top of the staff triage scaffolding
introduced in staff_support_triage_001 (which already added the
``category`` column + index, and the ``support_ticket_events`` table).

Net additions here:
  - ``subject_line`` (short patron-supplied subject)
  - ``is_anonymous`` (server-enforced; nulls identifying fields on insert)
  - ``response_route`` (routing destination string, e.g. "ada_coordinator")

Plus: relax ``name`` and ``email`` to nullable. Anonymous + COPPA-safe
under-13 + "no reply needed" paths legitimately have no identifying data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "contact_form_fields_001"
down_revision: Union[str, None] = "staff_support_triage_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New patron-contact-page columns. IF NOT EXISTS guards keep us idempotent
    # if prod was hand-advanced (per feedback_l30_alembic_multi_head_deploy).
    op.execute(
        "ALTER TABLE support_tickets "
        "ADD COLUMN IF NOT EXISTS subject_line VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE support_tickets "
        "ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE support_tickets "
        "ADD COLUMN IF NOT EXISTS response_route VARCHAR(64)"
    )

    # Relax NOT NULL on name + email so anonymous / under-13 / "no reply"
    # submissions can land without placeholder strings.
    op.alter_column("support_tickets", "name", existing_type=sa.String(255), nullable=True)
    op.alter_column("support_tickets", "email", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Best-effort downgrade. If any rows have NULL name/email we must
    # backfill before flipping to NOT NULL.
    op.execute("UPDATE support_tickets SET name = COALESCE(name, '') WHERE name IS NULL")
    op.execute("UPDATE support_tickets SET email = COALESCE(email, '') WHERE email IS NULL")
    op.alter_column("support_tickets", "email", existing_type=sa.String(255), nullable=False)
    op.alter_column("support_tickets", "name", existing_type=sa.String(255), nullable=False)
    op.execute("ALTER TABLE support_tickets DROP COLUMN IF EXISTS response_route")
    op.execute("ALTER TABLE support_tickets DROP COLUMN IF EXISTS is_anonymous")
    op.execute("ALTER TABLE support_tickets DROP COLUMN IF EXISTS subject_line")

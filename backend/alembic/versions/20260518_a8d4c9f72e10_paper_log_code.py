"""paper log code on reading_registrations + reading_programs_paper_log_enabled flag

Revision ID: a8d4c9f72e10
Revises: c3a17e9d44b1
Create Date: 2026-05-18 20:00:00.000000+00:00

Adds patron paper-log / kiosk claim-code support:

* ``reading_registrations.paper_log_code`` -- 8-char unique claim code
  (NULL until first PDF generated). Partial unique index so multiple
  rows can sit at NULL.
* ``reading_registrations.paper_log_code_generated_at``
* ``reading_registrations.paper_log_code_redeemed_at``
* ``organization_features.reading_programs_paper_log_enabled`` -- feature
  flag gating the paper-log UI/API surface. Default OFF.

Wrap CREATE/ALTER in IF NOT EXISTS / IF EXISTS NOT to stay idempotent
across init_db model-create + alembic upgrade.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a8d4c9f72e10"
down_revision: Union[str, None] = "c3a17e9d44b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE reading_registrations
        ADD COLUMN IF NOT EXISTS paper_log_code VARCHAR(8)
        """
    )
    op.execute(
        """
        ALTER TABLE reading_registrations
        ADD COLUMN IF NOT EXISTS paper_log_code_generated_at TIMESTAMP WITH TIME ZONE
        """
    )
    op.execute(
        """
        ALTER TABLE reading_registrations
        ADD COLUMN IF NOT EXISTS paper_log_code_redeemed_at TIMESTAMP WITH TIME ZONE
        """
    )
    # Partial unique index: only enforces uniqueness where code is set.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_reading_registrations_paper_log_code
        ON reading_registrations (paper_log_code)
        WHERE paper_log_code IS NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE organization_features
        ADD COLUMN IF NOT EXISTS reading_programs_paper_log_enabled
            BOOLEAN NOT NULL DEFAULT FALSE
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE organization_features "
        "DROP COLUMN IF EXISTS reading_programs_paper_log_enabled"
    )
    op.execute("DROP INDEX IF EXISTS ix_reading_registrations_paper_log_code")
    op.execute(
        "ALTER TABLE reading_registrations "
        "DROP COLUMN IF EXISTS paper_log_code_redeemed_at"
    )
    op.execute(
        "ALTER TABLE reading_registrations "
        "DROP COLUMN IF EXISTS paper_log_code_generated_at"
    )
    op.execute(
        "ALTER TABLE reading_registrations DROP COLUMN IF EXISTS paper_log_code"
    )

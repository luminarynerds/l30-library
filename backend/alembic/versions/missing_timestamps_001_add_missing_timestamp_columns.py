# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add missing timestamp columns read by the API layer

Three models were missing timestamp columns that their API handlers/response
schemas already read unconditionally, so those endpoints 500'd on every call:

  rfid_readers                        + updated_at  (RFIDReaderResponse requires it)
  rfid_tags                           + updated_at  (RFIDTagResponse requires it)
  strategic_comments                  + updated_at  (create_comment reads it)
  law_enforcement_response_templates  + created_at, updated_at (create_template reads both)

All three models now use TimestampMixin. created_at on the first two already
existed with an identical definition and is untouched.

Backfill: existing rows get now() via the NOT NULL server_default, which is the
same thing TimestampMixin would have written had the column always been there.

Revision ID: missing_timestamps_001
Revises: makerspace_payment_created_at_001
"""

import sqlalchemy as sa
from alembic import op

revision = "missing_timestamps_001"
down_revision = "makerspace_payment_created_at_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rfid_readers",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "rfid_tags",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "strategic_comments",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "law_enforcement_response_templates",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "law_enforcement_response_templates",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("law_enforcement_response_templates", "updated_at")
    op.drop_column("law_enforcement_response_templates", "created_at")
    op.drop_column("strategic_comments", "updated_at")
    op.drop_column("rfid_tags", "updated_at")
    op.drop_column("rfid_readers", "updated_at")

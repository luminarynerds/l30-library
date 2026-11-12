# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""widen alembic_version.version_num to varchar(64)

Alembic defaults ``alembic_version.version_num`` to VARCHAR(32). Revision
slugs longer than 32 chars (e.g. ``rename_event_program_partners_001`` =
33 chars) cause the UPDATE that records the new head to fail with
``StringDataRightTruncationError``, which rolls back the entire migration
transaction. Today's prod was patched out-of-band with
``ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)``;
this migration carries the same change into fresh installs / dev DBs.

Idempotent in practice: PostgreSQL's ``ALTER COLUMN ... TYPE VARCHAR(64)``
is a no-op if the column is already that width, so re-running on prod
(already widened) has no effect beyond recording this revision.

Going forward we still cap new revision slugs under 32 chars where
practical; this migration just removes the foot-gun.

Revision ID: widen_version_num_001
Revises: rename_event_program_partners_001
Create Date: 2026-05-16 00:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "widen_version_num_001"
down_revision: Union[str, None] = "rename_event_program_partners_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(length=64),
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        type_=sa.String(length=32),
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )

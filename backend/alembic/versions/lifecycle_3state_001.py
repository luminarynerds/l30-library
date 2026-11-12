# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Collapse course lifecycle from 5 stages to 3 (draft / published / archived).

Prod data: all 12 courses are 'published'; zero rows in 'in_review' or
'needs_revision'. The defensive UPDATE below is a no-op in practice but
guards against any pre-prod data that never made it to prod.

No DDL: lifecycle_stage is VARCHAR with no DB-level CHECK constraint (native_enum=False),
so removing enum members requires only a data migration, not a schema change.

Downgrade is a deliberate no-op: restoring the old stage names for
already-migrated rows isn't possible without out-of-band knowledge of which
rows were previously in_review vs draft.

Revision ID: lifecycle_3state_001
Revises: ai_tools_staff_pilot_001
Create Date: 2026-06-22
"""
from __future__ import annotations

from typing import Union

from alembic import op


revision: str = "lifecycle_3state_001"
down_revision: Union[str, None] = "ai_tools_staff_pilot_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Coerce any lingering in_review / needs_revision rows to 'draft'.
    # In prod today there are none (confirmed), so these are safety nets.
    op.execute(
        """
        UPDATE courses
        SET lifecycle_stage = 'draft'
        WHERE lifecycle_stage IN ('in_review', 'needs_revision')
        """
    )
    op.execute(
        """
        UPDATE course_stage_transitions
        SET from_stage = 'draft'
        WHERE from_stage IN ('in_review', 'needs_revision')
        """
    )
    op.execute(
        """
        UPDATE course_stage_transitions
        SET to_stage = 'draft'
        WHERE to_stage IN ('in_review', 'needs_revision')
        """
    )


def downgrade() -> None:
    # Intentional no-op: stage names for migrated rows cannot be
    # reconstructed without out-of-band history.
    pass

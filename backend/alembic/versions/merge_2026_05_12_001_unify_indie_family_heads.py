# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""unify indie_events_001 and program_family_001 heads

Revision ID: merge_2026_05_12_001
Revises: indie_events_001, program_family_001
Create Date: 2026-05-12

Empty migration that joins the two branches that opened up on 2026-05-11
(``indie_events_001`` adding ``events.indie_author_id`` and the
``indie_prefs_progress_001`` -> ``program_family_001`` lineage adding the
indie engagement and family/household tables). No schema change.

Production note: prod was at orphan revision ``d6b0b9bf0b8d`` (not in git;
left over from a pre-squash chain on 2026-05-01). Its schema already has
both ``events.indie_author_id`` and the indie engagement tables, but does
not yet have ``program_family_groups`` / ``program_family_members``. The
correct recovery sequence is:

    alembic stamp indie_events_001 indie_prefs_progress_001
    alembic upgrade head

That discards the orphan version row, marks both real branches as applied,
then runs ``program_family_001`` (which actually creates the family tables)
and this merge.
"""

from typing import Sequence, Union

revision: str = "merge_2026_05_12_001"
down_revision: Union[str, Sequence[str], None] = (
    "indie_events_001",
    "program_family_001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

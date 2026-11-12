# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""make transit_requests.requested_by_id nullable

BranchService.update_item_location auto-creates a TransitRequest when a non-floating
copy is checked in away from its home branch, and hardcoded requested_by_id=1
("system-generated"). No user need have id 1 -- on a fresh install ids may be
anything, and the first user may have been deleted -- so every such check-in tripped
transit_requests_requested_by_id_fkey.

The column was also declared nullable=False with ondelete="SET NULL", which is
self-contradictory: deleting the requesting user would have tried to NULL a NOT NULL
column. Making it nullable fixes both. System-generated transits now carry NULL,
which is the truth: no user requested them.

Revision ID: transit_requested_by_nullable_001
Revises: missing_timestamps_001
"""

import sqlalchemy as sa
from alembic import op

revision = "transit_requested_by_nullable_001"
down_revision = "missing_timestamps_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "transit_requests",
        "requested_by_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Rows written by the system carry NULL and have no user to attribute them to;
    # point them at nothing rather than inventing an id. Downgrade will fail if any
    # NULLs remain, which is the honest outcome.
    op.alter_column(
        "transit_requests",
        "requested_by_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

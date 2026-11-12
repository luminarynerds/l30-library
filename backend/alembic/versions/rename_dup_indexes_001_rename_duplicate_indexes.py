# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""rename duplicate indexes to follow ix_<table>_<col> convention

Revision ID: rename_dup_indexes_001
Revises: family_challenge_register_001, for_teachers_backfill_001, library_visits_001, pd_modules_001
Create Date: 2026-05-15

PR #523 surfaced model-side index name collisions where newer tables
(computer_reservations, computer_waitlist, guest_passes,
general_volunteer_hour_logs, policies) declared indexes with the same name
as indexes already present on older tables (room_reservations, room_waitlist,
computer_reservations.guest_pass_code, volunteer_hour_logs, policy_reviews).

On prod the colliding name landed on the OLDER table (verified per-name); the
NEWER tables silently lost those indexes during create_all/migration. This
migration creates the indexes under the new, table-prefixed names. It uses
CREATE INDEX IF NOT EXISTS so it is safe regardless of whether the new
indexes are already present (they should not be, but the migration is
idempotent).

It also drops the redundant unique constraint on blog_post_tags whose
post_id/tag_id composite is already enforced by the composite primary key.

This migration also acts as a merge across the four live heads on main
(family_challenge_register_001, for_teachers_backfill_001,
library_visits_001, pd_modules_001).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "rename_dup_indexes_001"
down_revision: Union[str, Sequence[str], None] = (
    "family_challenge_register_001",
    "for_teachers_backfill_001",
    "library_visits_001",
    "pd_modules_001",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create renamed indexes on the newer tables. CREATE INDEX IF NOT EXISTS
    # makes this a no-op if the index is already present under the new name.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_computer_reservations_patron_status "
        "ON computer_reservations (patron_id, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_computer_reservations_start_status "
        "ON computer_reservations (reserved_start_time, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_computer_reservations_guest_pass_code "
        "ON computer_reservations (guest_pass_code);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_computer_waitlist_patron_status "
        "ON computer_waitlist (patron_id, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_computer_waitlist_expires "
        "ON computer_waitlist (expires_at, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_guest_passes_pass_code "
        "ON guest_passes (pass_code);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_general_volunteer_hour_logs_volunteer_date "
        "ON general_volunteer_hour_logs (volunteer_id, log_date);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policies_category "
        "ON policies (category);"
    )

    # Drop the redundant unique constraint on blog_post_tags (composite PK
    # already enforces uniqueness on (post_id, tag_id)). Prod has it named
    # uq_blog_post_tags_post_tag; an autogenerate run on a different env may
    # have produced a slightly different name. Drop both variants if present.
    op.execute(
        "ALTER TABLE blog_post_tags DROP CONSTRAINT IF EXISTS uq_blog_post_tags_post_tag;"
    )
    op.execute(
        "ALTER TABLE blog_post_tags DROP CONSTRAINT IF EXISTS uq_blog_post_tags_post_id_tag_id;"
    )

    # Drop the old orphaned indexes that the renames replace. These existed on
    # prod under the colliding name (which originally lived on the new table
    # for ix_guest_pass_code; the room/policy/volunteer collisions resolved
    # in favor of the older tables so no orphans there).
    op.execute("DROP INDEX IF EXISTS ix_guest_pass_code;")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_policies_category;")
    op.execute("DROP INDEX IF EXISTS ix_general_volunteer_hour_logs_volunteer_date;")
    op.execute("DROP INDEX IF EXISTS ix_guest_passes_pass_code;")
    op.execute("DROP INDEX IF EXISTS ix_computer_waitlist_expires;")
    op.execute("DROP INDEX IF EXISTS ix_computer_waitlist_patron_status;")
    op.execute("DROP INDEX IF EXISTS ix_computer_reservations_guest_pass_code;")
    op.execute("DROP INDEX IF EXISTS ix_computer_reservations_start_status;")
    op.execute("DROP INDEX IF EXISTS ix_computer_reservations_patron_status;")
    # Not recreating the redundant unique constraint on downgrade.

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add reading-program values to notificationtype enum

Revision ID: rp_notification_types_001
Revises: rp_event_credit_001
Create Date: 2026-05-12

Adds three values to the ``notificationtype`` PostgreSQL enum so the new
reading-program notifications service can write Notification rows. The
service stays a feature-flagged no-op at the email layer until the
follow-up PR adds SendGrid templates; this migration only widens the
enum.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "rp_notification_types_001"
down_revision: Union[str, Sequence[str], None] = "rp_event_credit_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUES = (
    "reading_program_progress_nudge",
    "reading_program_streak_alert",
    "reading_program_prize_unlocked",
)


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in older
    # PostgreSQL releases; alembic's default migration env opens one, so
    # we COMMIT first, then ADD VALUE IF NOT EXISTS for each new tag.
    op.execute("COMMIT")
    for value in _NEW_VALUES:
        op.execute(
            f"ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE on an enum type. The clean
    # downgrade would be: create a new enum without the values, swap the
    # column type, drop the old type. That's destructive (any row using
    # one of the new values would error). We refuse rather than silently
    # dropping data.
    raise NotImplementedError(
        "ALTER TYPE ... DROP VALUE is not supported by PostgreSQL. To roll "
        "back, manually rewrite the column to a new enum that omits the "
        "reading_program_* values, after deleting or relabeling any "
        "Notification rows that use them."
    )

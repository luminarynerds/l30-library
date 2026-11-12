# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add event_registration_cancelled to notificationtype enum

Revision ID: event_registration_cancelled_001
Revises: notification_digest_queue_001
Create Date: 2026-05-23

Adds ``event_registration_cancelled`` to the ``notificationtype`` PostgreSQL
enum so the patron event-cancellation transactional email can be labeled
correctly in the notifications table.

Without this, the ``_map_to_db_type`` mapping falls back to
``checkout_receipt`` and the historical record is misclassified.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "event_registration_cancelled_001"
down_revision: Union[str, Sequence[str], None] = "notification_digest_queue_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUE = "event_registration_cancelled"


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in older
    # PostgreSQL releases; alembic's default migration env opens one, so
    # we COMMIT first, then ADD VALUE IF NOT EXISTS.
    op.execute("COMMIT")
    op.execute(
        f"ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS '{_NEW_VALUE}'"
    )


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE on an enum type. To roll
    # back, manually rewrite the column to a new enum that omits the
    # value, after deleting or relabeling any Notification rows that
    # use it.
    raise NotImplementedError(
        "ALTER TYPE ... DROP VALUE is not supported by PostgreSQL."
    )

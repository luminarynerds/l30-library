# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add seen_by_patron_at and patron_followup_email to agent_conversations.

Also expands patronnotificationcategory and notificationtype enums with
REFERENCE_CHAT_REPLY for staff-reply delivery to patrons.

Revision ID: ref_chat_unread_001
Create Date: 2026-05-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "ref_chat_unread_001"
down_revision: Union[str, Sequence[str], None] = "rename_dup_indexes_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_conversations",
        sa.Column("seen_by_patron_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_conversations",
        sa.Column("patron_followup_email", sa.String(length=255), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_conversations_session_unread "
        "ON agent_conversations (session_id) WHERE seen_by_patron_at IS NULL"
    )
    op.execute("ALTER TYPE patronnotificationcategory ADD VALUE IF NOT EXISTS 'reference_chat_reply'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'reference_chat_reply'")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agent_conversations_session_unread")
    op.drop_column("agent_conversations", "patron_followup_email")
    op.drop_column("agent_conversations", "seen_by_patron_at")
    # postgres does not support removing enum values without rebuilding the type;
    # leaving the enum values in place on downgrade is acceptable.

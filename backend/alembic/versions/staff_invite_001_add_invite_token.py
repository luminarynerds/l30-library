# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add users.invite_token + invite_token_expires for staff email-invite flow."""
import sqlalchemy as sa
from alembic import op

revision = "staff_invite_001"
down_revision = "23f6d49cf33a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("invite_token", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("invite_token_expires", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_invite_token", "users", ["invite_token"])


def downgrade() -> None:
    op.drop_index("ix_users_invite_token", table_name="users")
    op.drop_column("users", "invite_token_expires")
    op.drop_column("users", "invite_token")

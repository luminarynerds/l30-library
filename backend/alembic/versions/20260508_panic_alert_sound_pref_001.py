# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add sound_preference to panic_alert_notification_preferences

Revision ID: panic_alert_sound_pref_001
Revises: authority_terms_001
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "panic_alert_sound_pref_001"
down_revision: Union[str, Sequence[str], None] = "authority_terms_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "panic_alert_notification_preferences",
        sa.Column(
            "sound_preference",
            sa.String(length=32),
            server_default="gentle_chime",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("panic_alert_notification_preferences", "sound_preference")

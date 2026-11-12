# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Add catalog_saved_search_match to patronnotificationcategory enum.

Lets the saved-search nightly notifier (Task 4 of the saved-searches
plan) write its in-app PatronNotification rows with a dedicated
category, so the notification center can filter / theme them
separately from holds and overdues.

Revision ID: saved_searches_002
Revises: org_features_002
Create Date: 2026-05-16
"""
from typing import Sequence, Union

from alembic import op


revision = "saved_searches_002"
down_revision: Union[str, Sequence[str], None] = "org_features_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE IF NOT EXISTS is idempotent and safe to re-run on prods
    # where an operator might have already added the value by hand.
    op.execute(
        "ALTER TYPE patronnotificationcategory "
        "ADD VALUE IF NOT EXISTS 'catalog_saved_search_match'"
    )


def downgrade() -> None:
    # Postgres does not support removing a single enum value without
    # rebuilding the type and rewriting every column that uses it.
    # Leaving the value in place on downgrade is the standard pattern
    # here (see ref_chat_unread_001_add_seen_and_followup_email.py).
    pass

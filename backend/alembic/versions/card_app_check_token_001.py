# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add check_token to library_card_applications

Adds a unique, nullable check_token column so patrons can view their
application status via a tokenized public link emailed to them. Legacy
rows stay NULL — they have no public link and must contact the library
directly.

Revision ID: card_app_check_token_001
Revises: mergepoint_20260520
Create Date: 2026-05-20 19:00:00.000000+00:00

See Issue #1028.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "card_app_check_token_001"
down_revision: Union[str, None] = "mergepoint_20260520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "library_card_applications",
        sa.Column("check_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_library_card_applications_check_token",
        "library_card_applications",
        ["check_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_library_card_applications_check_token",
        table_name="library_card_applications",
    )
    op.drop_column("library_card_applications", "check_token")

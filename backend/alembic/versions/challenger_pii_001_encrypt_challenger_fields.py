# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Widen challenger PII columns to hold Fernet ciphertext.

Revision ID: challenger_pii_001
Revises: library_agent_minor_gating_001
Create Date: 2026-08-05

challenger_name and challenger_contact become EncryptedString(500);
challenger_complaint becomes EncryptedText and needs no change, because TEXT
has no length to widen.

Deliberately NO backfill, unlike pii_name_encrypt_001. The three rows in
production are seeded demo data, not real submissions, and encryption applies
to writes from here on, which is where every real submission lands. Those rows
keep reading correctly through the tolerant decrypt path in
core/encryption.py.

Worth knowing if you revisit this: BookChallengeUpdate carries no challenger
fields, so nothing in the app ever re-writes these columns. A lazy on-write
strategy would therefore never encrypt a pre-existing row. If this ever ships
somewhere that has accumulated real submissions, an explicit backfill becomes
necessary and pii_name_encrypt_001 is the precedent to copy.

Reversible: downgrade narrows back to 255. That will fail if any ciphertext is
already longer than 255 characters, which is the correct outcome -- silently
truncating a patron's encrypted contact detail would destroy it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "challenger_pii_001"
down_revision: Union[str, None] = "library_agent_minor_gating_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "book_challenges",
        "challenger_name",
        existing_type=sa.String(255),
        type_=sa.String(500),
        existing_nullable=True,
    )
    op.alter_column(
        "book_challenges",
        "challenger_contact",
        existing_type=sa.String(255),
        type_=sa.String(500),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "book_challenges",
        "challenger_contact",
        existing_type=sa.String(500),
        type_=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "book_challenges",
        "challenger_name",
        existing_type=sa.String(500),
        type_=sa.String(255),
        existing_nullable=True,
    )

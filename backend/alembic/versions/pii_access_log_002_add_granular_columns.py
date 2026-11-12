# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add granular access columns to pii_access_log

Adds five nullable columns so the same table can record per-record,
client-driven PII access events alongside the existing
middleware-batched rows:

* ``patron_id``       -- single patron subject of the access (FK users.id)
* ``subject_type``    -- free-text resource type (e.g. "patron_profile",
  "home_address", "session_intake", "minor_data")
* ``subject_id``      -- FK-loose row id for the resource accessed; nullable
  because the meaning varies by ``subject_type``
* ``action``          -- intent label ("read", "reveal", "export", "print");
  enum-validated at the service layer, not in the database, so new actions
  can ship without a migration
* ``reason``          -- free-text reason captured at the point of access

The existing middleware path that writes ``patron_ids_accessed`` keeps
working unchanged -- the new columns are nullable and the existing
rows have NULL in them.

Two composite indexes mirror the most-common review queries:

* ``(patron_id, timestamp DESC)`` -- "show me everyone who looked at
  patron 42, newest first"
* ``(user_id, timestamp DESC)``   -- "show me what staff member 17
  looked at, newest first"

Revision ID: pii_access_log_002
Revises: org_features_004
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "pii_access_log_002"
down_revision: Union[str, None] = "org_features_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
        existing_indexes: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)

        # If the table itself is missing (fresh install where 001 hasn't run
        # yet -- shouldn't happen, but be defensive), skip.
        if "pii_access_log" not in inspector.get_table_names():
            return

        existing_cols = {c["name"] for c in inspector.get_columns("pii_access_log")}
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("pii_access_log")}

    if "patron_id" not in existing_cols:
        op.add_column(
            "pii_access_log",
            sa.Column(
                "patron_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "subject_type" not in existing_cols:
        op.add_column(
            "pii_access_log",
            sa.Column("subject_type", sa.String(length=64), nullable=True),
        )
    if "subject_id" not in existing_cols:
        op.add_column(
            "pii_access_log",
            sa.Column("subject_id", sa.Integer(), nullable=True),
        )
    if "action" not in existing_cols:
        op.add_column(
            "pii_access_log",
            sa.Column("action", sa.String(length=32), nullable=True),
        )
    if "reason" not in existing_cols:
        op.add_column(
            "pii_access_log",
            sa.Column("reason", sa.Text(), nullable=True),
        )

    if "ix_pii_access_log_patron_timestamp" not in existing_indexes:
        op.create_index(
            "ix_pii_access_log_patron_timestamp",
            "pii_access_log",
            ["patron_id", sa.text("timestamp DESC")],
        )
    if "ix_pii_access_log_user_timestamp" not in existing_indexes:
        op.create_index(
            "ix_pii_access_log_user_timestamp",
            "pii_access_log",
            ["user_id", sa.text("timestamp DESC")],
        )


def downgrade() -> None:
    if op.get_context().as_sql:
        existing_indexes = {
            "ix_pii_access_log_user_timestamp",
            "ix_pii_access_log_patron_timestamp",
        }
        existing_cols = {"reason", "action", "subject_id", "subject_type", "patron_id"}
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        if "pii_access_log" not in inspector.get_table_names():
            return
        existing_indexes = {ix["name"] for ix in inspector.get_indexes("pii_access_log")}
        existing_cols = {c["name"] for c in inspector.get_columns("pii_access_log")}

    if "ix_pii_access_log_user_timestamp" in existing_indexes:
        op.drop_index(
            "ix_pii_access_log_user_timestamp", table_name="pii_access_log"
        )
    if "ix_pii_access_log_patron_timestamp" in existing_indexes:
        op.drop_index(
            "ix_pii_access_log_patron_timestamp", table_name="pii_access_log"
        )

    for col in ("reason", "action", "subject_id", "subject_type", "patron_id"):
        if col in existing_cols:
            op.drop_column("pii_access_log", col)

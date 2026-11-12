# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add created_at/updated_at to 8 professional-judgment tables (merge heads)

Eight tables in the professional-judgment namespace were originally created
via init_db.py / create_all() rather than alembic, and their model classes
did not inherit TimestampMixin. This adds the columns that the now-fixed
models declare. PolicyOverride already had the mixin and is skipped.

Revision ID: pj_timestamps_001
Revises: pii_access_log_001, collection_memory_view_001
Create Date: 2026-05-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "pj_timestamps_001"
down_revision: Union[str, Sequence[str], None] = (
    "pii_access_log_001",
    "collection_memory_view_001",
)
branch_labels = None
depends_on = None


PJ_TABLES = (
    "committees",
    "committee_members",
    "staff_projects",
    "policy_feedback",
    "staff_expertise",
    "expertise_recognitions",
    "professional_development_plans",
    "professional_development_activities",
)


def _existing_columns(inspector, table_name: str) -> set:
    return {c["name"] for c in inspector.get_columns(table_name)}


def upgrade() -> None:
    offline = op.get_context().as_sql
    if offline:
        inspector = None
        existing_tables = set(PJ_TABLES)
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_tables = set(inspector.get_table_names())

    for table_name in PJ_TABLES:
        if table_name not in existing_tables:
            continue
        cols = set() if offline else _existing_columns(inspector, table_name)
        if "created_at" not in cols:
            op.add_column(
                table_name,
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )
        if "updated_at" not in cols:
            op.add_column(
                table_name,
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                    nullable=False,
                ),
            )


def downgrade() -> None:
    offline = op.get_context().as_sql
    if offline:
        inspector = None
        existing_tables = set(PJ_TABLES)
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_tables = set(inspector.get_table_names())

    for table_name in PJ_TABLES:
        if table_name not in existing_tables:
            continue
        cols = {"created_at", "updated_at"} if offline else _existing_columns(inspector, table_name)
        if "updated_at" in cols:
            op.drop_column(table_name, "updated_at")
        if "created_at" in cols:
            op.drop_column(table_name, "created_at")

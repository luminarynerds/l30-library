# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create marc_macros table

Revision ID: marc_macros_001
Revises: authority_terms_001
Create Date: 2026-05-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "marc_macros_001"
down_revision: Union[str, None] = "authority_terms_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VISIBILITY_VALUES = ("private", "shared")


def upgrade() -> None:
    visibility_enum = postgresql.ENUM(
        *VISIBILITY_VALUES,
        name="marcmacrovisibility",
        create_type=False,
    )
    visibility_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "marc_macros",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "visibility",
            visibility_enum,
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "steps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_marc_macros_visibility", "marc_macros", ["visibility"])
    op.create_index("ix_marc_macros_owner_id", "marc_macros", ["owner_id"])
    op.create_index(
        "ix_marc_macros_visibility_name",
        "marc_macros",
        ["visibility", "name"],
    )


def downgrade() -> None:
    op.drop_index("ix_marc_macros_visibility_name", table_name="marc_macros")
    op.drop_index("ix_marc_macros_owner_id", table_name="marc_macros")
    op.drop_index("ix_marc_macros_visibility", table_name="marc_macros")
    op.drop_table("marc_macros")
    op.execute("DROP TYPE IF EXISTS marcmacrovisibility")

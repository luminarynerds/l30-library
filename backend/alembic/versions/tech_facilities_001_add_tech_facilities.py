# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add tech_facilities table + seed computer-lab and printer facts

Moves Computer Lab + printer facts off the Tech Support page, where they
were hardcoded as JSX literals, into the database so a wrong price or count
can be corrected without a frontend redeploy.

L30 init_db.py auto-creates tables from SQLAlchemy models at backend
startup, so on a deployed Postgres instance the tech_facilities table (and
its enum type) may already exist before this migration runs. Apply this
migration on a fresh DB, or `alembic stamp` it if init_db already created
the table. See [[feedback_l30_init_db_vs_alembic_new_table]].

Revision ID: tech_facilities_001
Revises: events_sensory_fields_001
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "tech_facilities_001"
down_revision: Union[str, None] = "events_sensory_fields_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (kind, label, value, sort_order) — migrated verbatim from the prior
# hardcoded JSX literals in frontend/src/pages/TechSupportPage.tsx.
SEED_FACILITIES = [
    ("computer_lab", "Computers available", "12", 1),
    ("computer_lab", "B&W printing", "$0.10/page", 2),
    ("computer_lab", "Color printing", "$0.25/page", 3),
    ("computer_lab", "WiFi", "Free throughout building", 4),
    (
        "printer",
        "Main Floor Computer Lab",
        "B&W and color printing available. Use library computers or "
        "bring your own device via WiFi.",
        1,
    ),
    ("printer", "Second Floor Reference Area", "B&W printing only.", 2),
]


def upgrade() -> None:
    facility_kind = sa.Enum(
        "computer_lab", "printer", name="techfacilitykind"
    )

    op.create_table(
        "tech_facilities",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("kind", facility_kind, nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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

    facilities_table = sa.table(
        "tech_facilities",
        sa.column("kind", facility_kind),
        sa.column("label", sa.String),
        sa.column("value", sa.Text),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        facilities_table,
        [
            {
                "kind": kind,
                "label": label,
                "value": value,
                "sort_order": sort_order,
                "is_active": True,
            }
            for kind, label, value, sort_order in SEED_FACILITIES
        ],
    )


def downgrade() -> None:
    op.drop_table("tech_facilities")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="techfacilitykind").drop(bind, checkfirst=True)

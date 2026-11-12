# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""PLS Phase 2: catalog audience enum, user has_mls, annual_report childrens_circ + mls FTE."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "pls_phase2_001"
down_revision = "pls_circulation_fields_001"
branch_labels = None
depends_on = None

# Model uses SQLEnum(create_type=False), so the migration owns the PG type.
catalogaudience = postgresql.ENUM(
    "children", "young_adult", "adult", "all_ages", name="catalogaudience"
)


def upgrade() -> None:
    bind = op.get_bind()
    catalogaudience.create(bind, checkfirst=True)

    op.add_column(
        "catalog_items",
        sa.Column(
            "audience",
            postgresql.ENUM(name="catalogaudience", create_type=False),
            nullable=True,
        ),
    )
    op.create_index("ix_catalog_items_audience", "catalog_items", ["audience"])

    op.add_column(
        "users",
        sa.Column("has_mls", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column(
        "annual_reports",
        sa.Column("childrens_circulation", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "annual_reports",
        sa.Column("mls_librarian_fte", sa.Numeric(8, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("annual_reports", "mls_librarian_fte")
    op.drop_column("annual_reports", "childrens_circulation")
    op.drop_column("users", "has_mls")
    op.drop_index("ix_catalog_items_audience", table_name="catalog_items")
    op.drop_column("catalog_items", "audience")
    catalogaudience.drop(op.get_bind(), checkfirst=True)

# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""pto_balance: replace per-user unique with (user_id, pto_type, year) composite

The old UNIQUE index on user_id alone allowed exactly one balance row per staff
member, which contradicts the model's own design (pto_type + year columns) and
makes pto_service's year-rollover row insert crash. Data precondition verified
2026-07-07: 15 rows, no (user_id, pto_type, year) duplicates possible.

Revision ID: pto_balance_composite_001
Revises: unify_heads_003
"""
from alembic import op

revision = "pto_balance_composite_001"
down_revision = "unify_heads_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_pto_balance_user_id", table_name="pto_balance")
    op.create_index("ix_pto_balance_user_id", "pto_balance", ["user_id"], unique=False)
    op.create_unique_constraint(
        "uq_pto_balance_user_type_year", "pto_balance", ["user_id", "pto_type", "year"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_pto_balance_user_type_year", "pto_balance", type_="unique")
    op.drop_index("ix_pto_balance_user_id", table_name="pto_balance")
    op.create_index("ix_pto_balance_user_id", "pto_balance", ["user_id"], unique=True)

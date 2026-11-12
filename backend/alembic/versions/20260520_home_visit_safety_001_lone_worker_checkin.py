"""home visit lone-worker safety check-in fields

Revision ID: home_visit_safety_001
Revises: mergepoint_20260520
Create Date: 2026-05-20 18:00:00.000000+00:00

Adds the five new safety columns + one FK to `parent_home_visits` for
the lone-worker check-in mechanic. All columns nullable so existing
rows survive unmodified.

  - safety_checkin_at           DateTime(tz)  nullable
  - safety_checkout_at          DateTime(tz)  nullable
  - safety_checkout_due_at      DateTime(tz)  nullable, indexed
  - safety_buddy_user_id        Integer FK -> users.id, ON DELETE SET NULL, indexed
  - safety_overdue_flagged_at   DateTime(tz)  nullable

Also adds `home_visit_safety_enabled` boolean column on
`organization_features` (default false -- opt-in per library).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "home_visit_safety_001"
down_revision: Union[str, None] = "mergepoint_20260520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "parent_home_visits",
        sa.Column("safety_checkin_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("safety_checkout_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("safety_checkout_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("safety_buddy_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "parent_home_visits",
        sa.Column("safety_overdue_flagged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_parent_home_visits_safety_buddy_user_id",
        "parent_home_visits",
        "users",
        ["safety_buddy_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_parent_home_visits_safety_checkout_due_at",
        "parent_home_visits",
        ["safety_checkout_due_at"],
    )
    op.create_index(
        "ix_parent_home_visits_safety_buddy_user_id",
        "parent_home_visits",
        ["safety_buddy_user_id"],
    )

    op.add_column(
        "organization_features",
        sa.Column(
            "home_visit_safety_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("organization_features", "home_visit_safety_enabled")
    op.drop_index("ix_parent_home_visits_safety_buddy_user_id", table_name="parent_home_visits")
    op.drop_index("ix_parent_home_visits_safety_checkout_due_at", table_name="parent_home_visits")
    op.drop_constraint(
        "fk_parent_home_visits_safety_buddy_user_id",
        "parent_home_visits",
        type_="foreignkey",
    )
    op.drop_column("parent_home_visits", "safety_overdue_flagged_at")
    op.drop_column("parent_home_visits", "safety_buddy_user_id")
    op.drop_column("parent_home_visits", "safety_checkout_due_at")
    op.drop_column("parent_home_visits", "safety_checkout_at")
    op.drop_column("parent_home_visits", "safety_checkin_at")

"""Add circulation_hold_trap_card_enabled column to organization_features.

Revision ID: org_features_003
Revises: org_features_003
Create Date: 2026-05-18

Feature flag for the staff check-in hold-trap card. Default true so the
card appears on the success path without requiring per-library opt-in.
Idempotent via has_column guard to tolerate prods that were ALTER-fixed
by hand or stamped forward.
"""
from alembic import op
import sqlalchemy as sa

revision = "org_features_004"
down_revision = "org_features_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("organization_features")}
    if "circulation_hold_trap_card_enabled" not in existing_cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "circulation_hold_trap_card_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    op.drop_column("organization_features", "circulation_hold_trap_card_enabled")

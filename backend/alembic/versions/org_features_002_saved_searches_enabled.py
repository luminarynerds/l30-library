"""Add saved_searches_enabled column to organization_features.

Revision ID: org_features_002
Revises: 575b17141b44
Create Date: 2026-05-16

PR #611 added a saved_searches_enabled ORM column but only created a
new saved_searches TABLE in alembic. The column needed to land on the
existing organization_features table too. Idempotent via has_column
guard so prods that were ALTER-fixed by hand do not collide.
"""
from alembic import op
import sqlalchemy as sa

revision = "org_features_002"
down_revision = "575b17141b44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        existing_cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing_cols = {c["name"] for c in inspector.get_columns("organization_features")}
    if "saved_searches_enabled" not in existing_cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "saved_searches_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    op.drop_column("organization_features", "saved_searches_enabled")

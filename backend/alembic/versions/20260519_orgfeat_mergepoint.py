"""Mergepoint: unite org_features_005 with 75bb25c1889c.

Two heads diverged from org_features_004:
  - org_features_005 (adds organization_features.customer_display_enabled)
  - 75bb25c1889c (adds public_records_requests columns)

Prod was stamped to 75bb25c1889c, so org_features_005 never ran and the
customer_display_enabled column is missing on prod. The model selects it
unconditionally, so every GET /api/v1/organization-features falls into
the ProgrammingError fallback path and 500s on Pydantic validation.

This mergepoint:
  1. Unites both heads into a single linear history.
  2. Idempotently ensures customer_display_enabled exists on
     organization_features (in case org_features_005 still has not run on
     a given environment by the time this revision is reached).

Revision ID: orgfeat_mergepoint_20260519
Revises: org_features_005, 75bb25c1889c
"""
from alembic import op
import sqlalchemy as sa


revision = "orgfeat_mergepoint_20260519"
down_revision = ("org_features_005", "75bb25c1889c")
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().as_sql:
        cols: set[str] = set()
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        cols = {c["name"] for c in inspector.get_columns("organization_features")}
    if "customer_display_enabled" not in cols:
        op.add_column(
            "organization_features",
            sa.Column(
                "customer_display_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    # No-op: this is a mergepoint. Each parent owns its own column drop.
    pass

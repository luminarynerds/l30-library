"""makerspace_payments: add created_at

The revenue report (MakerspaceReportsService.get_revenue_report) filters
payments by MakerspacePayment.created_at, but the column never existed, so
GET /staff/makerspace/reports/revenue 500'd. Add it with a now() server
default so existing rows (if any) get a value and the NOT NULL holds.

Revision ID: makerspace_payment_created_at_001
Revises: bundle_dist_student_001
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa

revision = "makerspace_payment_created_at_001"
down_revision = "bundle_dist_student_001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "makerspace_payments",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_makerspace_payments_created_at", "makerspace_payments", ["created_at"])


def downgrade():
    op.drop_index("ix_makerspace_payments_created_at", table_name="makerspace_payments")
    op.drop_column("makerspace_payments", "created_at")

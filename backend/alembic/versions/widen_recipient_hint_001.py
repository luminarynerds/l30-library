"""widen failed_notification_records.recipient_hint to 100

Revision ID: widen_recipient_hint_001
Revises: integration_probe_audit_001
Create Date: 2026-05-14

VARCHAR(20) was too tight -- masked addresses like "***@luminarynerds.com"
are 21 chars and were overflowing on insert with a
StringDataRightTruncationError, blocking the audit-failure record write
when a real send fails.
"""
from alembic import op
import sqlalchemy as sa

revision = "widen_recipient_hint_001"
down_revision = "integration_probe_audit_001"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "failed_notification_records",
        "recipient_hint",
        type_=sa.String(100),
        existing_type=sa.String(20),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "failed_notification_records",
        "recipient_hint",
        type_=sa.String(20),
        existing_type=sa.String(100),
        existing_nullable=True,
    )

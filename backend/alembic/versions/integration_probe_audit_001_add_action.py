"""add integration_probe to AuditAction enum

Revision ID: integration_probe_audit_001
Revises: bibframe_ts_001
"""
from alembic import op


revision = "integration_probe_audit_001"
down_revision = "bibframe_ts_001"
branch_labels = None
depends_on = None

# ``ALTER TYPE ... ADD VALUE`` cannot run inside a transaction on some PG
# versions. PG 16 handles it fine, but flip this off if alembic complains.
# transactional_ddl = False


def upgrade():
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'integration_probe'")


def downgrade():
    # postgres can't remove enum values cleanly without recreating the type
    pass

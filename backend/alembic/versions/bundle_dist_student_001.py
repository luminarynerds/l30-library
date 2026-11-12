"""bundle_distributions: add student_name/class_name, user_id nullable

Take-home reading bundles are handed to schoolchildren who are usually not
library patrons, so a distribution needs to record a free-text student name +
class rather than requiring a patron account. Adds two nullable columns and
relaxes the user_id FK to nullable (a patron account becomes optional).

Revision ID: bundle_dist_student_001
Revises: edi_backorder_columns_001
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "bundle_dist_student_001"
down_revision = "edi_backorder_columns_001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bundle_distributions",
        sa.Column("student_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "bundle_distributions",
        sa.Column("class_name", sa.String(length=100), nullable=True),
    )
    op.alter_column(
        "bundle_distributions",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "bundle_distributions",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("bundle_distributions", "class_name")
    op.drop_column("bundle_distributions", "student_name")

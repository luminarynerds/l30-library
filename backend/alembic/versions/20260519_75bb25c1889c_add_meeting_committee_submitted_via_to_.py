"""add meeting_committee_submitted_via to public_records_requests

Revision ID: 75bb25c1889c
Revises: org_features_004
Create Date: 2026-05-19 00:51:52.171484+00:00

"""
# NOTE: When adding new tables, use
#   op.execute("CREATE TABLE IF NOT EXISTS ...")
# instead of op.create_table(). L30's init_db.py auto-creates tables from
# SQLAlchemy models at backend startup, so by the time alembic runs the
# table may already exist and op.create_table() raises DuplicateTableError.
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "75bb25c1889c"
down_revision: Union[str, None] = "org_features_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "public_records_requests",
        sa.Column("meeting_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "public_records_requests",
        sa.Column("committee_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "public_records_requests",
        sa.Column("submitted_via", sa.String(length=30), nullable=True),
    )
    op.create_foreign_key(
        "fk_prr_meeting_id",
        "public_records_requests",
        "board_meetings",
        ["meeting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_prr_committee_id",
        "public_records_requests",
        "board_committees",
        ["committee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_prr_meeting_id", "public_records_requests", ["meeting_id"]
    )
    op.create_index(
        "ix_prr_committee_id", "public_records_requests", ["committee_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_prr_committee_id", table_name="public_records_requests")
    op.drop_index("ix_prr_meeting_id", table_name="public_records_requests")
    op.drop_constraint(
        "fk_prr_committee_id", "public_records_requests", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_prr_meeting_id", "public_records_requests", type_="foreignkey"
    )
    op.drop_column("public_records_requests", "submitted_via")
    op.drop_column("public_records_requests", "committee_id")
    op.drop_column("public_records_requests", "meeting_id")
